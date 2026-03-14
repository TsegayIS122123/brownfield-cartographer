"""Orchestrator for Surveyor, Hydrologist, Semanticist, and Archivist agents."""

import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

import networkx as nx

from src.agents.surveyor import SurveyorAgent
from src.agents.hydrologist import HydrologistAgent
from src.agents.semanticist import SemanticistAgent
from src.agents.archivist import ArchivistAgent           # NEW
from src.agents.navigator import NavigatorAgent          # NEW
from src.graph.knowledge_graph import KnowledgeGraph
from src.utils.git_utils import GitChangeDetector        # NEW

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
    """Orchestrates Phase 1-4 analysis (Surveyor + Hydrologist + Semanticist + Archivist)."""
    
    def __init__(self, repo_path: str, output_dir: str = ".cartography"):
        self.repo_path = repo_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.surveyor = SurveyorAgent(repo_path)
        self.hydrologist = HydrologistAgent(repo_path)
        self.semanticist = None
        self.archivist = None
        self.navigator = None
        
        self.knowledge_graph = KnowledgeGraph()
    
    def run(self) -> Dict:
        """Run the complete Phase 1-4 analysis."""
        logger.info(f"Starting analysis of {self.repo_path}")
        
        # ========== PHASE 1: SURVEYOR ==========
        logger.info("=" * 50)
        logger.info("🔍 PHASE 1: Running Surveyor Agent...")
        logger.info("=" * 50)
        
        surveyor_results = self.surveyor.analyze()
        
        # Build knowledge graph from Surveyor results
        self._build_knowledge_graph(surveyor_results)
        
        # ========== PHASE 2: HYDROLOGIST ==========
        logger.info("=" * 50)
        logger.info("💧 PHASE 2: Running Hydrologist Agent...")
        logger.info("=" * 50)
        
        hydrologist_results = self.hydrologist.analyze()
        
        # Merge Hydrologist results into knowledge graph
        self._merge_lineage_results(hydrologist_results)
        
        # ========== PHASE 3: SEMANTICIST ==========
        logger.info("=" * 50)
        logger.info("🧠 PHASE 3: Running Semanticist Agent...")
        logger.info("=" * 50)
        
        # Initialize Semanticist with budget limit
        self.semanticist = SemanticistAgent(
            repo_path=self.repo_path, 
            budget_limit=5.0  # $5 budget for LLM calls
        )
        
        semanticist_results = self.semanticist.analyze(
            surveyor_results=surveyor_results,
            hydrologist_results=hydrologist_results
        )
        
        # Merge Semanticist results into knowledge graph
        self._merge_semantic_results(semanticist_results)
        
        # ========== PHASE 4: ARCHIVIST ==========
        logger.info("=" * 50)
        logger.info("📚 PHASE 4: Running Archivist Agent...")
        logger.info("=" * 50)

        self.archivist = ArchivistAgent(output_dir=self.output_dir)
        archivist_results = self.archivist.generate_all(
            surveyor_results=surveyor_results,
            hydrologist_results=hydrologist_results,
            semanticist_results=semanticist_results,
            knowledge_graph=self.knowledge_graph
        )

        # Initialize Navigator
        self.navigator = NavigatorAgent(
            knowledge_graph=self.knowledge_graph,
            lineage_graph=hydrologist_results.get("lineage_graph") if hydrologist_results else None,
            semanticist_results=semanticist_results,
            archivist=self.archivist
        )

        # Check for incremental updates
        git_detector = GitChangeDetector(self.repo_path)
        changed_files, needs_full = git_detector.get_changed_files()
        if changed_files:
            logger.info(f"📝 {len(changed_files)} files changed since last analysis")
            # Store for potential incremental update (can be used later)
            self.changed_files = changed_files
        
        # ========== SAVE ARTIFACTS ==========
        logger.info("=" * 50)
        logger.info("💾 Saving artifacts...")
        logger.info("=" * 50)
        
        self._save_artifacts(surveyor_results, hydrologist_results, semanticist_results, archivist_results)
        
        # ========== GENERATE SUMMARY ==========
        summary = self._generate_summary(
            surveyor_results, 
            hydrologist_results, 
            semanticist_results,
            archivist_results
        )
        
        logger.info("=" * 50)
        logger.info("✅ Analysis Complete!")
        logger.info("=" * 50)
        
        return {
            "surveyor": surveyor_results,
            "hydrologist": hydrologist_results,
            "semanticist": semanticist_results,
            "archivist": archivist_results,
            "navigator": self.navigator,
            "knowledge_graph": self.knowledge_graph,
            "summary": summary,
        }
    
    def _build_knowledge_graph(self, surveyor_results: Dict):
        """Build knowledge graph from Surveyor results."""
        logger.info("Building knowledge graph from Surveyor results...")
        
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
        
        logger.info(f"Knowledge graph: {self.knowledge_graph.graph.number_of_nodes()} nodes, {edge_count} edges")
    
    def _merge_lineage_results(self, hydrologist_results: Dict):
        """Merge Hydrologist lineage results into knowledge graph."""
        if not hydrologist_results:
            return
        
        lineage_graph = hydrologist_results.get("lineage_graph")
        if lineage_graph and hasattr(lineage_graph, 'graph'):
            # Add lineage nodes and edges to main knowledge graph
            for node, attrs in lineage_graph.graph.nodes(data=True):
                self.knowledge_graph.add_node(node, **attrs)
            
            for u, v, attrs in lineage_graph.graph.edges(data=True):
                # Create a clean copy of attrs without 'source' or 'target'
                edge_attrs = {}
                for key, value in attrs.items():
                    if key not in ['source', 'target']:
                        edge_attrs[key] = value
                self.knowledge_graph.add_edge(u, v, **edge_attrs)
            
            logger.info(f"Merged {lineage_graph.graph.number_of_nodes()} lineage nodes and "
                    f"{lineage_graph.graph.number_of_edges()} lineage edges")
    
    def _merge_semantic_results(self, semanticist_results: Dict):
        """Merge Semanticist results into knowledge graph."""
        if not semanticist_results:
            return
        
        # Add purpose statements to module nodes
        purpose_statements = semanticist_results.get("purpose_statements", {})
        for module_path, purpose_data in purpose_statements.items():
            if module_path in self.knowledge_graph.graph:
                # Update node with purpose statement
                self.knowledge_graph.graph.nodes[module_path]["purpose_statement"] = purpose_data["purpose"]
                self.knowledge_graph.graph.nodes[module_path]["purpose_model"] = purpose_data.get("model")
        
        # Add domain clusters
        domain_clusters = semanticist_results.get("domain_clusters", {})
        labels = domain_clusters.get("labels", {})
        for module_path, label in labels.items():
            if module_path in self.knowledge_graph.graph:
                cluster_name = domain_clusters.get("cluster_names", {}).get(label, f"Domain_{label}")
                self.knowledge_graph.graph.nodes[module_path]["domain_cluster"] = cluster_name
                self.knowledge_graph.graph.nodes[module_path]["domain_label"] = label
        
        # Add docstring drift flags
        docstring_drift = semanticist_results.get("docstring_drift", {})
        for module_path, drift_data in docstring_drift.items():
            if module_path in self.knowledge_graph.graph:
                self.knowledge_graph.graph.nodes[module_path]["docstring_drift"] = drift_data
        
        logger.info(f"Merged semantic data for {len(purpose_statements)} modules")
    
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
    
    def _save_artifacts(self, 
                        surveyor_results: Dict, 
                        hydrologist_results: Dict, 
                        semanticist_results: Dict,
                        archivist_results: Dict):
        """Save all analysis artifacts to disk."""
        logger.info(f"Saving artifacts to {self.output_dir}")
        
        # Save module graph
        module_graph_path = self.output_dir / "module_graph.json"
        self.knowledge_graph.save_json(str(module_graph_path))
        logger.info(f"✅ Module graph saved to {module_graph_path}")
        
        # Save surveyor results
        surveyor_path = self.output_dir / "surveyor_results.json"
        with open(surveyor_path, 'w', encoding='utf-8') as f:
            metadata = surveyor_results.get("metadata", {})
            if hasattr(metadata, 'dict'):
                metadata_dict = metadata.dict()
            else:
                metadata_dict = metadata
            
            serializable = {
                "metadata": self._serialize_for_json(metadata_dict),
                "file_changes": self._serialize_for_json(surveyor_results.get("file_changes", {})),
                "high_velocity": self._serialize_for_json(surveyor_results.get("high_velocity", [])),
            }
            json.dump(serializable, f, indent=2, cls=DateTimeEncoder)
        logger.info(f"✅ Surveyor results saved to {surveyor_path}")
        
        # Save lineage graph and stats
        if hydrologist_results:
            lineage_graph = hydrologist_results.get("lineage_graph")
            if lineage_graph:
                lineage_path = self.output_dir / "lineage_graph.json"
                lineage_graph.save_json(str(lineage_path))
                logger.info(f"✅ Lineage graph saved to {lineage_path}")
            
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
        
        # Save semanticist results
        if semanticist_results:
            semanticist_path = self.output_dir / "semanticist_results.json"
            
            # Prepare semantic results for serialization
            semantic_serializable = {
                "purpose_statements": self._serialize_for_json(semanticist_results.get("purpose_statements", {})),
                "docstring_drift": self._serialize_for_json(semanticist_results.get("docstring_drift", {})),
                "domain_clusters": self._serialize_for_json(semanticist_results.get("domain_clusters", {})),
                "day_one_answers": self._serialize_for_json(semanticist_results.get("day_one_answers", {})),
                "budget_summary": self._serialize_for_json(semanticist_results.get("budget_summary", {})),
            }
            
            with open(semanticist_path, 'w', encoding='utf-8') as f:
                json.dump(semantic_serializable, f, indent=2, cls=DateTimeEncoder)
            logger.info(f"✅ Semanticist results saved to {semanticist_path}")
        
        # Archivist artifacts are already saved by generate_all()
        if archivist_results:
            for name, path in archivist_results.items():
                logger.info(f"✅ {name} saved to {path}")
    
    def _get_actual_import_count(self, surveyor_results: Dict) -> int:
        """Calculate actual import count from module data."""
        import_count = 0
        modules = surveyor_results.get("modules", {})
        for module in modules.values():
            if hasattr(module, 'imports'):
                import_count += len(module.imports)
            elif isinstance(module, dict) and 'imports' in module:
                import_count += len(module['imports'])
        return import_count
    
    def _generate_summary(self, 
                          surveyor_results: Dict, 
                          hydrologist_results: Dict, 
                          semanticist_results: Dict,
                          archivist_results: Dict) -> Dict:
        """Generate a comprehensive summary of the analysis."""
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
        
        # Get actual import count
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
        
        # Get semantic stats
        semantic_stats = {}
        if semanticist_results:
            semantic_stats = {
                "purpose_statements": len(semanticist_results.get("purpose_statements", {})),
                "docstring_drift": len([d for d in semanticist_results.get("docstring_drift", {}).values() if d.get("has_drift")]),
                "domain_clusters": len(semanticist_results.get("domain_clusters", {}).get("cluster_names", {})),
                "total_cost": semanticist_results.get("budget_summary", {}).get("total_cost", 0),
            }
        
        # Get archivist stats
        archivist_stats = {}
        if archivist_results:
            archivist_stats = {
                "codebase_md": str(archivist_results.get("codebase_md", "")),
                "onboarding_brief": str(archivist_results.get("onboarding_brief", "")),
                "trace_log": str(archivist_results.get("trace_log", "")),
            }
        
        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "repository": str(self.repo_path),
            "surveyor": {
                "total_modules": total_modules,
                "total_imports": actual_imports,
                "languages": languages,
                "top_modules": top_modules[:5] if top_modules else [],
                "circular_dependencies": len(circular_deps),
                "dead_code_candidates": len(dead_code),
                "high_velocity_modules": high_velocity[:5] if high_velocity else [],
            },
            "hydrologist": lineage_stats,
            "semanticist": semantic_stats,
            "archivist": archivist_stats,
            "has_lineage": bool(hydrologist_results),
            "has_semantic": bool(semanticist_results),
            "has_archivist": bool(archivist_results),
        }
        
        # Print comprehensive summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Repository: {self.repo_path}")
        
        print(f"\n🔍 SURVEYOR (Phase 1):")
        print(f"  • Modules analyzed: {total_modules}")
        print(f"  • Imports found: {actual_imports}")
        print(f"  • Languages: {languages}")
        
        if top_modules:
            print(f"\n  🏆 Top modules by PageRank:")
            for i, mod in enumerate(top_modules[:3], 1):
                path = mod.get('path', 'unknown') if isinstance(mod, dict) else getattr(mod, 'path', 'unknown')
                score = mod.get('pagerank', 0) if isinstance(mod, dict) else getattr(mod, 'pagerank', 0)
                print(f"     {i}. {path} (score: {score:.4f})")
        
        print(f"\n💧 HYDROLOGIST (Phase 2):")
        print(f"  • Source datasets: {lineage_stats.get('sources', 0)}")
        print(f"  • Sink datasets: {lineage_stats.get('sinks', 0)}")
        print(f"  • Python operations: {lineage_stats.get('python_ops', 0)}")
        print(f"  • SQL queries: {lineage_stats.get('sql_queries', 0)}")
        
        print(f"\n🧠 SEMANTICIST (Phase 3):")
        print(f"  • Purpose statements: {semantic_stats.get('purpose_statements', 0)}")
        print(f"  • Documentation drift: {semantic_stats.get('docstring_drift', 0)} files")
        print(f"  • Domain clusters: {semantic_stats.get('domain_clusters', 0)}")
        print(f"  • LLM cost: ${semantic_stats.get('total_cost', 0):.4f}")
        
        print(f"\n📚 ARCHIVIST (Phase 4):")
        print(f"  • CODEBASE.md: {archivist_stats.get('codebase_md', 'N/A')}")
        print(f"  • onboarding_brief.md: {archivist_stats.get('onboarding_brief', 'N/A')}")
        print(f"  • cartography_trace.jsonl: {archivist_stats.get('trace_log', 'N/A')}")
        
        print("\n" + "=" * 70)
        
        return summary