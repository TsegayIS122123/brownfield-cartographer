"""Hydrologist Agent - Full data lineage analysis for Phase 2."""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.analyzers.python_data_flow import PythonDataFlowAnalyzer
from src.analyzers.sql_lineage import SQLLineageAnalyzer
from src.analyzers.dag_config_parser import DAGConfigAnalyzer
from src.graph.lineage_graph import LineageGraph
from src.models.schemas import ProducesEdge, ConsumesEdge, DatasetNode, TransformationNode

logger = logging.getLogger(__name__)


class HydrologistAgent:
    """Hydrologist Agent - Full data lineage analysis."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.python_analyzer = PythonDataFlowAnalyzer()
        self.sql_analyzer = SQLLineageAnalyzer()
        self.dag_analyzer = DAGConfigAnalyzer(repo_path)
        
        self.lineage_graph = LineageGraph()
        self.results = {}
    
    def analyze(self) -> Dict[str, Any]:
        """Run complete data lineage analysis."""
        logger.info("=" * 60)
        logger.info("HYDROLOGIST AGENT - Full Data Lineage Analysis")
        logger.info("=" * 60)
        
        # Step 1: Analyze Python data flows
        logger.info("\n📊 Analyzing Python data flows...")
        python_lineage = self._analyze_python_flows()
        
        # Step 2: Analyze SQL lineage
        logger.info("\n🔍 Analyzing SQL lineage...")
        sql_lineage = self._analyze_sql_lineage()
        
        # Step 3: Analyze DAG configs
        logger.info("\n⚙️ Analyzing DAG configurations...")
        dag_lineage = self._analyze_dag_configs()  # This method name must match!
        
        # Step 4: Merge all into lineage graph
        logger.info("\n🔄 Building complete lineage graph...")
        self._merge_lineage(python_lineage, sql_lineage, dag_lineage)
        
        # Step 5: Find sources and sinks
        sources = self.lineage_graph.find_sources()
        sinks = self.lineage_graph.find_sinks()
        
        logger.info(f"\n📦 Found {len(sources)} source datasets")
        logger.info(f"📦 Found {len(sinks)} sink datasets")
        logger.info(f"📊 Graph built with {self.lineage_graph.graph.number_of_nodes()} nodes, {self.lineage_graph.graph.number_of_edges()} edges")
        
        self.results = {
            "python_lineage": python_lineage,
            "sql_lineage": sql_lineage,
            "dag_lineage": dag_lineage,
            "lineage_graph": self.lineage_graph,
            "sources": sources,
            "sinks": sinks,
        }
        
        return self.results
    
    def _analyze_python_flows(self) -> Dict:
        """Analyze Python files for data operations."""
        python_files = []
        
        # IMPORTANT: Look in ALL directories including .github!
        for root, _, files in os.walk(self.repo_path):
            # Don't exclude .github - that's where the Python script is!
            if '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    python_files.append(full_path)
                    logger.debug(f"Found Python file: {full_path}")
        
        logger.info(f"Found {len(python_files)} Python files to analyze")
        
        if not python_files:
            logger.warning("No Python files found! Check path and exclusions.")
            return {
                "files_analyzed": 0,
                "operations": [],
                "reads": [],
                "writes": [],
                "total_operations": 0,
            }
        
        operations = []
        reads = []
        writes = []
        
        for i, file_path in enumerate(python_files):
            if i % 10 == 0 and i > 0:
                logger.info(f"  Progress: {i}/{len(python_files)} files")
            
            analysis = self.python_analyzer.analyze_file(file_path)
            if analysis and "operations" in analysis:
                ops = analysis.get("operations", [])
                operations.extend(ops)
                
                # Count reads and writes
                file_reads = [op for op in ops if op.get("category") == "read"]
                file_writes = [op for op in ops if op.get("category") == "write"]
                reads.extend(file_reads)
                writes.extend(file_writes)
                
                logger.debug(f"File {file_path}: {len(ops)} ops, {len(file_reads)} reads, {len(file_writes)} writes")
        
        logger.info(f"  Found {len(reads)} read operations")
        logger.info(f"  Found {len(writes)} write operations")
        logger.info(f"  Found {len(operations)} total operations")
        
        return {
            "files_analyzed": len(python_files),
            "operations": operations[:50] if len(operations) > 50 else operations,
            "reads": reads,
            "writes": writes,
            "total_operations": len(operations),
        }
    
    def _analyze_sql_lineage(self) -> Dict:
        """Analyze SQL files for lineage."""
        sql_files = []
        for root, _, files in os.walk(self.repo_path):
            if '.git' in root or '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith('.sql'):
                    sql_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(sql_files)} SQL files to analyze")
        
        lineage_results = []
        all_tables = set()
        all_targets = set()
        successful_parses = 0
        
        for file_path in sql_files:
            rel_path = os.path.relpath(file_path, self.repo_path)
            lineage = self.sql_analyzer.parse_file(file_path)
            
            if lineage and "tables_read" in lineage:
                lineage["file"] = rel_path
                lineage_results.append(lineage)
                successful_parses += 1
                
                for table in lineage.get("tables_read", []):
                    all_tables.add(table["full_name"])
                for target in lineage.get("tables_written", []):
                    all_targets.add(target["table"])
            elif lineage and "dbt" in lineage and lineage["dbt"].get("has_dbt"):
                logger.debug(f"dbt-only lineage for {rel_path}: {lineage['dbt'].get('refs', [])}")
        
        logger.info(f"  Successfully parsed {successful_parses}/{len(sql_files)} SQL files")
        logger.info(f"  Found {len(all_tables)} unique tables referenced")
        logger.info(f"  Found {len(all_targets)} unique tables written")
        
        return {
            "files_analyzed": len(sql_files),
            "successful_parses": successful_parses,
            "lineage_results": lineage_results[:20] if len(lineage_results) > 20 else lineage_results,
            "unique_tables_read": list(all_tables)[:50],
            "unique_tables_written": list(all_targets)[:50],
            "total_queries": len(lineage_results),
        }
    
    def _analyze_dag_configs(self) -> Dict:  # Make sure this method name matches!
        """Analyze DAG configuration files."""
        dag_results = self.dag_analyzer.analyze()
        
        logger.info(f"  Found {dag_results['total_configs']} DAG configurations")
        logger.info(f"  Found {dag_results.get('total_sql_files', 0)} total SQL files")
        
        if dag_results['dbt_projects']:
            dbt_lineage = self.dag_analyzer.extract_dbt_lineage()
            dag_results['dbt_lineage'] = dbt_lineage
            logger.info(f"  dbt: {dbt_lineage.get('node_count', 0)} nodes, {dbt_lineage.get('edge_count', 0)} edges")
            logger.info(f"  dbt root models: {len(dbt_lineage.get('root_models', []))}")
            logger.info(f"  dbt leaf models: {len(dbt_lineage.get('leaf_models', []))}")
            
            # Get summary
            dag_results['dbt_summary'] = self.dag_analyzer.get_dbt_summary()
        
        return dag_results
    
    def _merge_lineage(self, python: Dict, sql: Dict, dag: Dict):
        """Merge all lineage sources into a single graph."""
        
        # Add Python operations
        for op in python.get("reads", []):
            if op.get("dataset"):
                transform_id = f"python:{op['file']}:L{op['line']}"
                dataset_id = f"dataset:{op['dataset']}"
                
                # Add transformation node
                transform_node = TransformationNode(
                    source_datasets=[dataset_id],
                    target_datasets=[],
                    transformation_type=op.get("type", "unknown"),
                    source_file=op['file'],
                    line_range=(op['line'], op['line']),
                    framework="python",
                    transformation_logic=op.get("code", "")
                )
                self.lineage_graph.add_transformation_node(transform_id, transform_node)
                
                # Add dataset node
                dataset_node = DatasetNode(
                    name=op['dataset'],
                    storage_type="unknown",
                    is_source_of_truth=False
                )
                self.lineage_graph.add_dataset_node(dataset_id, dataset_node)
                
                # Create typed consumes edge (dataset → transformation)
                edge = ConsumesEdge(
                    source=dataset_id,
                    target=transform_id,
                    transformation_type=op.get("type", "unknown"),
                    source_file=op['file'],
                    line_range=(op['line'], op['line']),
                    is_filter="filter" in op.get("type", "").lower(),
                    join_type=None
                )
                self.lineage_graph.add_consumes_edge(edge)
        
        for op in python.get("writes", []):
            if op.get("dataset"):
                transform_id = f"python:{op['file']}:L{op['line']}"
                dataset_id = f"dataset:{op['dataset']}"
                
                # Add transformation node
                transform_node = TransformationNode(
                    source_datasets=[],
                    target_datasets=[dataset_id],
                    transformation_type=op.get("type", "unknown"),
                    source_file=op['file'],
                    line_range=(op['line'], op['line']),
                    framework="python",
                    transformation_logic=op.get("code", "")
                )
                self.lineage_graph.add_transformation_node(transform_id, transform_node)
                
                # Add dataset node
                dataset_node = DatasetNode(
                    name=op['dataset'],
                    storage_type="unknown",
                    is_source_of_truth=False
                )
                self.lineage_graph.add_dataset_node(dataset_id, dataset_node)
                
                # Create typed produces edge (transformation → dataset)
                edge = ProducesEdge(
                    source=transform_id,
                    target=dataset_id,
                    transformation_type=op.get("type", "unknown"),
                    source_file=op['file'],
                    line_range=(op['line'], op['line']),
                    is_incremental=False
                )
                self.lineage_graph.add_produces_edge(edge)
        
        # Add SQL operations from successful parses
        for lineage in sql.get("lineage_results", []):
            file = lineage.get("file", "unknown")
            
            for table in lineage.get("tables_read", []):
                transform_id = f"sql:{file}"
                dataset_id = f"dataset:{table['full_name']}"
                
                self.lineage_graph.add_transformation(transform_id, file=file)
                self.lineage_graph.add_dataset(dataset_id)
                self.lineage_graph.add_read_edge(transform_id, dataset_id)
            
            for target in lineage.get("tables_written", []):
                transform_id = f"sql:{file}"
                dataset_id = f"dataset:{target['table']}"
                
                self.lineage_graph.add_transformation(transform_id, file=file)
                self.lineage_graph.add_dataset(dataset_id)
                self.lineage_graph.add_write_edge(transform_id, dataset_id)
        
        # Add dbt lineage from DAG configs
        if dag.get("dbt_lineage"):
            for edge in dag["dbt_lineage"].get("edges", []):
                from_node = edge["from"]
                to_node = edge["to"]
                
                self.lineage_graph.add_transformation(from_node)
                self.lineage_graph.add_transformation(to_node)
                self.lineage_graph.add_edge(from_node, to_node, type="depends_on", via=edge.get("via", "ref"))
    
    def blast_radius(self, node: str) -> Dict:
        """Calculate blast radius for a node."""
        return self.lineage_graph.blast_radius(node)
    
    def trace_lineage(self, dataset: str, direction: str = "both") -> Dict:
        """Trace lineage for a dataset."""
        return self.lineage_graph.trace_lineage(dataset, direction)
    
    def find_sources(self) -> List[str]:
        """Find source datasets."""
        return self.lineage_graph.find_sources()
    
    def find_sinks(self) -> List[str]:
        """Find sink datasets."""
        return self.lineage_graph.find_sinks()
    
    def get_lineage_graph(self) -> LineageGraph:
        """Get the lineage graph."""
        return self.lineage_graph