"""Orchestrator for Surveyor and Hydrologist agents."""

import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

import networkx as nx

from src.agents.surveyor import SurveyorAgent
from src.agents.hydrologist import HydrologistAgent
from src.graph.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class Phase1Orchestrator:
    """Orchestrates Phase 1 analysis (Surveyor + Hydrologist)."""
    
    def __init__(self, repo_path: str, output_dir: str = ".cartography"):
        self.repo_path = repo_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.surveyor = SurveyorAgent(repo_path)
        # Initialize Hydrologist with the new full implementation
        self.hydrologist = HydrologistAgent(repo_path)
        
        self.knowledge_graph = KnowledgeGraph()
    
    def run(self) -> Dict:
        """Run the complete Phase 1 analysis."""
        logger.info(f"Starting Phase 1 analysis of {self.repo_path}")
        
        # Step 1: Run Surveyor
        logger.info("=" * 50)
        logger.info("Running Surveyor Agent...")
        logger.info("=" * 50)
        
        surveyor_results = self.surveyor.analyze()
        
        # Step 2: Build knowledge graph from Surveyor results
        self._build_knowledge_graph(surveyor_results)
        
        # Step 3: Run Hydrologist (full lineage analysis)
        logger.info("=" * 50)
        logger.info("Running Hydrologist Agent (Full Lineage)...")
        logger.info("=" * 50)
        
        # Use the new analyze() method instead of extract_sql_lineage()
        hydrologist_results = self.hydrologist.analyze()
        
        # Step 4: Merge Hydrologist results into knowledge graph
        self._merge_lineage_results(hydrologist_results)
        
        # Step 5: Save artifacts
        self._save_artifacts(surveyor_results, hydrologist_results)
        
        # Step 6: Generate summary with CORRECT import count
        summary = self._generate_summary(surveyor_results, hydrologist_results)
        
        logger.info("=" * 50)
        logger.info("Phase 1 Analysis Complete!")
        logger.info("=" * 50)
        
        return {
            "surveyor": surveyor_results,
            "hydrologist": hydrologist_results,
            "knowledge_graph": self.knowledge_graph,
            "summary": summary,
        }
    
    def _build_knowledge_graph(self, surveyor_results: Dict):
        """Build knowledge graph from Surveyor results."""
        logger.info("Building knowledge graph...")
        
        # Add module nodes
        for path, module in surveyor_results.get("modules", {}).items():
            self.knowledge_graph.add_node(
                path,
                type="module",
                **module.dict()
            )
        
        # Add import edges from the graph
        edge_count = 0
        graph = surveyor_results.get("graph")
        if graph is not None and hasattr(graph, 'edges'):
            for u, v, data in graph.edges(data=True):
                edge_attrs = {"type": "imports"}
                edge_attrs.update(data)
                self.knowledge_graph.add_edge(u, v, **edge_attrs)
                edge_count += 1
        
        logger.info(f"Knowledge graph built: {self.knowledge_graph.graph.number_of_nodes()} nodes, {edge_count} edges")
    
    def _merge_lineage_results(self, hydrologist_results: Dict):
        """Merge Hydrologist lineage results into knowledge graph."""
        if not hydrologist_results:
            return
        
        # Get the lineage graph from hydrologist results
        lineage_graph = hydrologist_results.get("lineage_graph")
        if lineage_graph and hasattr(lineage_graph, 'graph'):
            # Add lineage nodes and edges to main knowledge graph
            for node, attrs in lineage_graph.graph.nodes(data=True):
                self.knowledge_graph.add_node(node, **attrs)
            
            for u, v, attrs in lineage_graph.graph.edges(data=True):
                self.knowledge_graph.add_edge(u, v, **attrs)
            
            logger.info(f"Merged {lineage_graph.graph.number_of_nodes()} lineage nodes and {lineage_graph.graph.number_of_edges()} lineage edges")
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Recursively serialize objects for JSON."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(item) for item in obj]
        elif hasattr(obj, 'dict'):  # Pydantic model
            return self._serialize_for_json(obj.dict())
        elif hasattr(obj, '__dict__'):  # Other objects
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    def _save_artifacts(self, surveyor_results: Dict, hydrologist_results: Dict):
        """Save analysis artifacts to disk."""
        logger.info(f"Saving artifacts to {self.output_dir}")
        
        # Save module graph (already handles datetime via KnowledgeGraph.save_json)
        module_graph_path = self.output_dir / "module_graph.json"
        self.knowledge_graph.save_json(str(module_graph_path))
        logger.info(f"✅ Module graph saved to {module_graph_path}")
        
        # Save surveyor results with proper datetime handling
        surveyor_path = self.output_dir / "surveyor_results.json"
        
        # Prepare surveyor results for JSON serialization
        metadata = surveyor_results.get("metadata", {})
        
        # Convert metadata to dict if it's a Pydantic model
        if hasattr(metadata, 'dict'):
            metadata_dict = metadata.dict()
        else:
            metadata_dict = metadata
        
        # Serialize everything
        serializable = {
            "metadata": self._serialize_for_json(metadata_dict),
            "file_changes": self._serialize_for_json(surveyor_results.get("file_changes", {})),
            "high_velocity": self._serialize_for_json(surveyor_results.get("high_velocity", [])),
        }
        
        with open(surveyor_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, cls=DateTimeEncoder)
        logger.info(f"✅ Surveyor results saved to {surveyor_path}")
        
        # Save lineage graph
        if hydrologist_results:
            lineage_graph = hydrologist_results.get("lineage_graph")
            if lineage_graph:
                lineage_path = self.output_dir / "lineage_graph.json"
                lineage_graph.save_json(str(lineage_path))
                logger.info(f"✅ Lineage graph saved to {lineage_path}")
            
            # Save lineage stats (simple dict, no datetime issues)
            stats_path = self.output_dir / "lineage_stats.json"
            stats = {
                "sources": self._serialize_for_json(hydrologist_results.get("sources", [])),
                "sinks": self._serialize_for_json(hydrologist_results.get("sinks", [])),
                "python_operations": len(hydrologist_results.get("python_lineage", {}).get("operations", [])),
                "sql_queries": hydrologist_results.get("sql_lineage", {}).get("total_queries", 0),
                "dag_configs": hydrologist_results.get("dag_lineage", {}).get("total_configs", 0),
            }
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, cls=DateTimeEncoder)
            logger.info(f"✅ Lineage stats saved to {stats_path}")
    
    def _get_actual_import_count(self, surveyor_results: Dict) -> int:
        """Calculate actual import count from module data."""
        import_count = 0
        modules = surveyor_results.get("modules", {})
        for module in modules.values():
            # Count imports from module.imports list
            if hasattr(module, 'imports'):
                import_count += len(module.imports)
            elif isinstance(module, dict) and 'imports' in module:
                import_count += len(module['imports'])
        return import_count
    
    def _generate_summary(self, surveyor_results: Dict, hydrologist_results: Dict) -> Dict:
        """Generate a summary of the analysis."""
        metadata = surveyor_results.get("metadata", {})
        
        # Handle both object and dict metadata
        if hasattr(metadata, 'total_modules'):
            total_modules = metadata.total_modules
            languages = metadata.languages
            top_modules = metadata.top_modules_by_pagerank
            circular_deps = metadata.circular_dependencies
            dead_code = metadata.dead_code_candidates
            high_velocity = metadata.high_velocity_modules
        else:
            total_modules = metadata.get('total_modules', 0)
            languages = metadata.get('languages', {})
            top_modules = metadata.get('top_modules_by_pagerank', [])
            circular_deps = metadata.get('circular_dependencies', [])
            dead_code = metadata.get('dead_code_candidates', [])
            high_velocity = metadata.get('high_velocity_modules', [])
        
        # Get ACTUAL import count from modules, not metadata
        actual_imports = self._get_actual_import_count(surveyor_results)
        
        # Get lineage stats
        lineage_stats = {}
        if hydrologist_results:
            lineage_stats = {
                "sources": len(hydrologist_results.get("sources", [])),
                "sinks": len(hydrologist_results.get("sinks", [])),
                "python_ops": len(hydrologist_results.get("python_lineage", {}).get("operations", [])),
                "sql_queries": hydrologist_results.get("sql_lineage", {}).get("total_queries", 0),
            }
        
        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "repository": str(self.repo_path),
            "surveyor": {
                "total_modules": total_modules,
                "total_imports": actual_imports,  # Use actual count!
                "languages": languages,
                "top_modules": top_modules[:5] if top_modules else [],
                "circular_dependencies": len(circular_deps),
                "dead_code_candidates": len(dead_code),
                "high_velocity_modules": high_velocity[:5] if high_velocity else [],
            },
            "hydrologist": lineage_stats,
            "has_lineage": bool(hydrologist_results),
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("PHASE 1 ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Repository: {self.repo_path}")
        print(f"\n📊 SURVEYOR:")
        print(f"  • Modules analyzed: {total_modules}")
        print(f"  • Imports found: {actual_imports}")  # This will now show the correct number!
        print(f"  • Languages: {languages}")
        
        if top_modules:
            print(f"\n  🏆 Top modules by PageRank:")
            for i, mod in enumerate(top_modules[:3], 1):
                path = mod.get('path', 'unknown') if isinstance(mod, dict) else getattr(mod, 'path', 'unknown')
                score = mod.get('pagerank', 0) if isinstance(mod, dict) else getattr(mod, 'pagerank', 0)
                print(f"     {i}. {path} (score: {score:.4f})")
        
        print(f"\n💧 HYDROLOGIST:")
        print(f"  • Source datasets: {lineage_stats.get('sources', 0)}")
        print(f"  • Sink datasets: {lineage_stats.get('sinks', 0)}")
        print(f"  • Python operations: {lineage_stats.get('python_ops', 0)}")
        print(f"  • SQL queries: {lineage_stats.get('sql_queries', 0)}")
        
        print("\n" + "=" * 60)
        
        return summary