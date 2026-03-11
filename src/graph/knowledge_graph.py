"""NetworkX graph wrapper with serialization."""

import json
import networkx as nx
from pathlib import Path  # 👈 ADD THIS IMPORT
from typing import Any, Dict, List, Optional
from datetime import datetime


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


class KnowledgeGraph:
    """Wrapper for NetworkX graph with serialization."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.metadata = {}
    
    def add_node(self, node_id: str, **attrs):
        """Add a node with attributes."""
        self.graph.add_node(node_id, **attrs)
    
    def add_edge(self, source: str, target: str, **attrs):
        """Add an edge with attributes."""
        self.graph.add_edge(source, target, **attrs)
    
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
        """Serialize a single value."""
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
        """Save graph to JSON file using custom encoder."""
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