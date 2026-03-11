"""Data Lineage Graph - NetworkX-based lineage tracking."""

import json
import networkx as nx
from pathlib import Path  # ��� ADD THIS IMPORT
from typing import Dict, List, Optional, Set, Any
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


class LineageGraph:
    """Graph for tracking data lineage across Python, SQL, and YAML."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "sources": [],
            "sinks": [],
        }
    
    def add_dataset(self, dataset_id: str, **attrs):
        """Add a dataset node (table, file, etc.)."""
        attrs["type"] = "dataset"
        self.graph.add_node(dataset_id, **attrs)
    
    def add_transformation(self, transform_id: str, **attrs):
        """Add a transformation node (SQL file, Python script, etc.)."""
        attrs["type"] = "transformation"
        self.graph.add_node(transform_id, **attrs)
    
    def add_edge(self, from_node: str, to_node: str, **attrs):
        """Add a lineage edge."""
        self.graph.add_edge(from_node, to_node, **attrs)
    
    def add_read_edge(self, transform: str, dataset: str, **attrs):
        """Add a read operation (transformation reads dataset)."""
        attrs["operation"] = "reads"
        self.add_edge(dataset, transform, **attrs)
    
    def add_write_edge(self, transform: str, dataset: str, **attrs):
        """Add a write operation (transformation writes dataset)."""
        attrs["operation"] = "writes"
        self.add_edge(transform, dataset, **attrs)
    
    def blast_radius(self, node: str) -> Dict[str, Any]:
        """Find all downstream dependents of a node."""
        if node not in self.graph:
            return {"error": f"Node {node} not found in graph"}
        
        # Find all descendants (downstream)
        descendants = list(nx.descendants(self.graph, node))
        
        # Find all nodes that depend on this node
        dependents = []
        for descendant in descendants:
            try:
                path = nx.shortest_path(self.graph, node, descendant)
                dependents.append({
                    "node": descendant,
                    "path": path,
                    "path_length": len(path) - 1,
                    "node_type": self.graph.nodes[descendant].get("type", "unknown"),
                })
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        # Also find direct dependents (immediate successors)
        direct = list(self.graph.successors(node))
        
        return {
            "node": node,
            "node_type": self.graph.nodes[node].get("type", "unknown"),
            "direct_dependents": direct,
            "all_dependents": descendants,
            "dependent_count": len(descendants),
            "dependents_detail": dependents,
        }
    
    def find_sources(self) -> List[str]:
        """Find source datasets (in-degree = 0, out-degree > 0)."""
        sources = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) > 0:
                if self.graph.nodes[node].get("type") == "dataset":
                    sources.append(node)
        return sources
    
    def find_sinks(self) -> List[str]:
        """Find sink datasets (out-degree = 0, in-degree > 0)."""
        sinks = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get("type", "")
            
            # Check if node is a dataset or model
            if node_type == "dataset" or node.startswith("dataset:") or node.startswith("model:"):
                # If it has incoming edges but no outgoing edges, it's a sink
                if self.graph.in_degree(node) > 0 and self.graph.out_degree(node) == 0:
                    sinks.append(node)
                # Also check for mart models that are final outputs
                elif "model:" in node and self.graph.out_degree(node) == 0:
                    sinks.append(node)
        
        return list(set(sinks))  # Remove duplicates
    
    def find_upstream(self, node: str, depth: int = -1) -> List[str]:
        """Find all upstream dependencies of a node."""
        if node not in self.graph:
            return []
        
        # Get all ancestors (upstream)
        ancestors = list(nx.ancestors(self.graph, node))
        
        if depth > 0:
            # Limit by depth
            ancestors = [a for a in ancestors if nx.shortest_path_length(self.graph, a, node) <= depth]
        
        return ancestors
    
    def find_downstream(self, node: str, depth: int = -1) -> List[str]:
        """Find all downstream dependents of a node."""
        if node not in self.graph:
            return []
        
        # Get all descendants (downstream)
        descendants = list(nx.descendants(self.graph, node))
        
        if depth > 0:
            # Limit by depth
            descendants = [d for d in descendants if nx.shortest_path_length(self.graph, node, d) <= depth]
        
        return descendants
    
    def trace_lineage(self, dataset: str, direction: str = "both") -> Dict:
        """Trace full lineage of a dataset."""
        if dataset not in self.graph:
            return {"error": f"Dataset {dataset} not found"}
        
        result = {
            "dataset": dataset,
            "upstream": [],
            "downstream": [],
            "transformations": [],
        }
        
        if direction in ["upstream", "both"]:
            upstream = self.find_upstream(dataset)
            result["upstream"] = upstream
        
        if direction in ["downstream", "both"]:
            downstream = self.find_downstream(dataset)
            result["downstream"] = downstream
        
        # Find transformations that use this dataset
        for node in self.graph.predecessors(dataset):
            if self.graph.nodes[node].get("type") == "transformation":
                result["transformations"].append({
                    "name": node,
                    "operation": self.graph.edges[node, dataset].get("operation", "unknown"),
                })
        
        return result
    
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
        nodes = []
        for node, attrs in self.graph.nodes(data=True):
            nodes.append({"id": node, **self._serialize_attrs(attrs)})
        
        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, **self._serialize_attrs(attrs)})
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                **self.metadata,
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(),
                "sources": self.find_sources(),
                "sinks": self.find_sinks(),
                "serialized_at": datetime.now().isoformat(),
            }
        }
    
    def save_json(self, filepath: str):
        """Save graph to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, indent=2, cls=DateTimeEncoder)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'LineageGraph':
        """Load graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lg = cls()
        
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            node_type = node.pop("type", "dataset")
            if node_type == "dataset":
                lg.add_dataset(node_id, **node)
            else:
                lg.add_transformation(node_id, **node)
        
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            lg.add_edge(source, target, **edge)
        
        lg.metadata = data.get("metadata", {})
        
        return lg
