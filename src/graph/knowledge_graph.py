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
        self.graph = nx.MultiDiGraph()  # Use MultiDiGraph to allow multiple edge types
        self.metadata = {}
    
    # ============ TYPED NODE ADDITION METHODS ============
    
    def add_module_node(self, node_id: str, module_data: ModuleNode):
        """Add a typed module node."""
        attrs = module_data.dict()
        attrs["node_type"] = "module"
        attrs["schema_version"] = "1.0"
        self.graph.add_node(node_id, **attrs)
    
    def add_dataset_node(self, node_id: str, dataset_data: DatasetNode):
        """Add a typed dataset node."""
        attrs = dataset_data.dict()
        attrs["node_type"] = "dataset"
        self.graph.add_node(node_id, **attrs)
    
    def add_function_node(self, node_id: str, function_data: FunctionNode):
        """Add a typed function node."""
        attrs = function_data.dict()
        attrs["node_type"] = "function"
        self.graph.add_node(node_id, **attrs)
    
    def add_transformation_node(self, node_id: str, transform_data: TransformationNode):
        """Add a typed transformation node."""
        attrs = transform_data.dict()
        attrs["node_type"] = "transformation"
        self.graph.add_node(node_id, **attrs)
    
    # ============ TYPED EDGE ADDITION METHODS ============
    
    def add_import_edge(self, edge_data: ImportEdge):
        """Add a typed import edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_IMPORTS
        self.graph.add_edge(
            edge_data.source, 
            edge_data.target, 
            key=self.EDGE_IMPORTS,
            **attrs
        )
    
    def add_produces_edge(self, edge_data: ProducesEdge):
        """Add a typed produces edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_PRODUCES
        self.graph.add_edge(
            edge_data.source,
            edge_data.target,
            key=self.EDGE_PRODUCES,
            **attrs
        )
    
    def add_consumes_edge(self, edge_data: ConsumesEdge):
        """Add a typed consumes edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CONSUMES
        self.graph.add_edge(
            edge_data.source,
            edge_data.target,
            key=self.EDGE_CONSUMES,
            **attrs
        )
    
    def add_calls_edge(self, edge_data: CallsEdge):
        """Add a typed calls edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CALLS
        self.graph.add_edge(
            edge_data.source,
            edge_data.target,
            key=self.EDGE_CALLS,
            **attrs
        )
    
    def add_configures_edge(self, edge_data: ConfiguresEdge):
        """Add a typed configures edge."""
        attrs = edge_data.dict()
        attrs["edge_type"] = self.EDGE_CONFIGURES
        self.graph.add_edge(
            edge_data.source,
            edge_data.target,
            key=self.EDGE_CONFIGURES,
            **attrs
        )
    
    # ============ EDGE QUERY METHODS ============
    
    def get_imports(self, node_id: str) -> List[Dict]:
        """Get all import edges from a node."""
        edges = []
        for _, target, data in self.graph.out_edges(node_id, data=True, keys=True):
            if data.get("edge_type") == self.EDGE_IMPORTS:
                edges.append({"target": target, **data})
        return edges
    
    def get_imported_by(self, node_id: str) -> List[Dict]:
        """Get all nodes that import this node."""
        edges = []
        for source, _, data in self.graph.in_edges(node_id, data=True, keys=True):
            if data.get("edge_type") == self.EDGE_IMPORTS:
                edges.append({"source": source, **data})
        return edges
    
    def get_downstream_datasets(self, node_id: str) -> List[Dict]:
        """Get all datasets produced downstream from this node."""
        downstream = []
        for _, target, data in self.graph.out_edges(node_id, data=True, keys=True):
            if data.get("edge_type") == self.EDGE_PRODUCES:
                downstream.append({"dataset": target, **data})
        return downstream
    
    def get_upstream_datasets(self, node_id: str) -> List[Dict]:
        """Get all datasets consumed by this node."""
        upstream = []
        for source, _, data in self.graph.in_edges(node_id, data=True, keys=True):
            if data.get("edge_type") == self.EDGE_CONSUMES:
                upstream.append({"dataset": source, **data})
        return upstream
    
    # ============ SERIALIZATION ============
    
    def to_schema(self) -> KnowledgeGraphSchema:
        """Convert graph to typed schema."""
        nodes = []
        for node, attrs in self.graph.nodes(data=True):
            node_dict = {"id": node, **self._serialize_attrs(attrs)}
            nodes.append(node_dict)
        
        edges = []
        for u, v, key, attrs in self.graph.edges(data=True, keys=True):
            edge_dict = {
                "source": u,
                "target": v,
                "key": key,
                **self._serialize_attrs(attrs)
            }
            edges.append(edge_dict)
        
        return KnowledgeGraphSchema(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(**self.metadata)
        )
    
    def _serialize_attrs(self, attrs: Dict) -> Dict:
        """Convert non-serializable attributes."""
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
    
    def save_json(self, filepath: str):
        """Save graph to JSON file."""
        schema = self.to_schema()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(schema.dict(), f, indent=2, cls=DateTimeEncoder)
    
    @classmethod
    def load_json(cls, filepath: str) -> 'KnowledgeGraph':
        """Load graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        kg = cls()
        
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            node_type = node.pop("node_type", "unknown")
            kg.graph.add_node(node_id, **node)
        
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            key = edge.pop("key", None)
            kg.graph.add_edge(source, target, key=key, **edge)
        
        kg.metadata = data.get("metadata", {})
        
        return kg