"""NetworkX graph wrapper with serialization."""

import json
import networkx as nx
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from src.models.schemas import (
    ModuleNode, DatasetNode, FunctionNode, TransformationNode,
    ImportEdge, ProducesEdge, ConsumesEdge, CallsEdge, ConfiguresEdge,
    GraphMetadata, KnowledgeGraphSchema
)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


class KnowledgeGraph:
    """Wrapper for NetworkX graph with serialization and typed methods."""
    
    # Edge type constants
    EDGE_IMPORTS = "imports"
    EDGE_PRODUCES = "produces"
    EDGE_CONSUMES = "consumes"
    EDGE_CALLS = "calls"
    EDGE_CONFIGURES = "configures"
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.metadata = {}
    
    # ============ BASIC NODE/EDGE METHODS ============
    
    def add_node(self, node_id: str, **attrs):
        """Add a node with attributes."""
        self.graph.add_node(node_id, **attrs)
    
    def add_edge(self, source: str, target: str, **attrs):
        """Add an edge with attributes.
        
        Args:
            source: Source node ID
            target: Target node ID
            **attrs: Additional edge attributes
        """
        # Create a clean copy of attributes without duplicate keys
        clean_attrs = {}
        for key, value in attrs.items():
            # Skip if key is 'source' or 'target' since we already have them as positional args
            if key in ['source', 'target']:
                continue
            clean_attrs[key] = value
        
        # Handle MultiDiGraph key separately if present
        if 'key' in clean_attrs:
            key = clean_attrs.pop('key')
            self.graph.add_edge(source, target, key=key, **clean_attrs)
        else:
            self.graph.add_edge(source, target, **clean_attrs)
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node attributes."""
        if node_id in self.graph:
            return self.graph.nodes[node_id]
        return None
    
    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """Get neighbors of a node."""
        if direction == "out":
            return list(self.graph.successors(node_id))
        elif direction == "in":
            return list(self.graph.predecessors(node_id))
        else:
            return list(self.graph.neighbors(node_id))
    
    # ============ TYPED NODE ADDITION METHODS ============
    
    def add_module_node(self, node_id: str, module_data: ModuleNode):
        """Add a typed module node."""
        attrs = module_data.dict()
        attrs["node_type"] = "module"
        attrs["schema_version"] = "1.0"
        self.add_node(node_id, **attrs)
    
    def add_dataset_node(self, node_id: str, dataset_data: DatasetNode):
        """Add a typed dataset node."""
        attrs = dataset_data.dict()
        attrs["node_type"] = "dataset"
        self.add_node(node_id, **attrs)
    
    def add_function_node(self, node_id: str, function_data: FunctionNode):
        """Add a typed function node."""
        attrs = function_data.dict()
        attrs["node_type"] = "function"
        self.add_node(node_id, **attrs)
    
    def add_transformation_node(self, node_id: str, transform_data: TransformationNode):
        """Add a typed transformation node."""
        attrs = transform_data.dict()
        attrs["node_type"] = "transformation"
        self.add_node(node_id, **attrs)
    
    # ============ TYPED EDGE ADDITION METHODS ============
    
    def add_import_edge(self, edge_data: ImportEdge):
        """Add a typed import edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_IMPORTS
        self.add_edge(edge_data.source, edge_data.target, **attrs)
    
    def add_produces_edge(self, edge_data: ProducesEdge):
        """Add a typed produces edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_PRODUCES
        self.add_edge(edge_data.source, edge_data.target, **attrs)
    
    def add_consumes_edge(self, edge_data: ConsumesEdge):
        """Add a typed consumes edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CONSUMES
        self.add_edge(edge_data.source, edge_data.target, **attrs)
    
    def add_calls_edge(self, edge_data: CallsEdge):
        """Add a typed calls edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CALLS
        self.add_edge(edge_data.source, edge_data.target, **attrs)
    
    def add_configures_edge(self, edge_data: ConfiguresEdge):
        """Add a typed configures edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CONFIGURES
        self.add_edge(edge_data.source, edge_data.target, **attrs)
    
    # ============ GRAPH ANALYSIS ============
    
    def get_pagerank(self) -> Dict[str, float]:
        """Compute PageRank scores."""
        return nx.pagerank(self.graph)
    
    def get_strongly_connected_components(self) -> List[List[str]]:
        """Get strongly connected components."""
        return [list(comp) for comp in nx.strongly_connected_components(self.graph)]
    
    def get_modules_with_no_incoming(self) -> List[str]:
        """Get nodes with in-degree 0."""
        return [node for node in self.graph.nodes() if self.graph.in_degree(node) == 0]
    
    def get_modules_with_no_outgoing(self) -> List[str]:
        """Get nodes with out-degree 0."""
        return [node for node in self.graph.nodes() if self.graph.out_degree(node) == 0]
    
    # ============ SERIALIZATION ============
    
    def _serialize_attrs(self, attrs: Dict) -> Dict:
        """Convert non-serializable attributes to serializable format."""
        serialized = {}
        for key, value in attrs.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, Path):
                serialized[key] = str(value)
            elif isinstance(value, (list, tuple)):
                serialized[key] = [self._serialize_value(v) for v in value]
            elif isinstance(value, dict):
                serialized[key] = self._serialize_attrs(value)
            else:
                serialized[key] = value
        return serialized
    
    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        return value
    
    def to_json(self) -> Dict:
        """Convert graph to JSON-serializable dict."""
        return {
            "nodes": [
                {
                    "id": node,
                    **self._serialize_attrs(attrs)
                }
                for node, attrs in self.graph.nodes(data=True)
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    **self._serialize_attrs(attrs)
                }
                for u, v, attrs in self.graph.edges(data=True)
            ],
            "metadata": {
                **self.metadata,
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(),
                "serialized_at": datetime.now().isoformat(),
            }
        }
    
    def save_json(self, filepath: str):
        """Save graph to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, indent=2, cls=DateTimeEncoder)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'KnowledgeGraph':
        """Load graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        kg = cls()
        
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            kg.add_node(node_id, **node)
        
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            kg.add_edge(source, target, **edge)
        
        kg.metadata = data.get("metadata", {})
        
        return kg


# Explicitly export the class
__all__ = ['KnowledgeGraph', 'DateTimeEncoder']