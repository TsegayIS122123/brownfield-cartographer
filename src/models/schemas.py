"""Pydantic models for the knowledge graph."""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel, Field, validator


class ModuleNode(BaseModel):
    """Represents a code module/file."""
    
    # Core identifiers
    path: str
    language: str  # python, sql, yaml, javascript, typescript
    
    # Static analysis
    imports: List[str] = Field(default_factory=list)
    imported_by: List[str] = Field(default_factory=list)
    public_functions: List[str] = Field(default_factory=list)
    public_classes: List[str] = Field(default_factory=list)
    class_inheritance: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Metrics
    loc: int = 0  # Lines of code
    complexity_score: float = 0.0
    comment_ratio: float = 0.0
    
    # Git analysis
    change_velocity_30d: int = 0
    last_modified: Optional[datetime] = None
    authors: List[str] = Field(default_factory=list)
    commit_count: int = 0
    
    # Analysis results
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None  # Added missing field
    is_dead_code_candidate: bool = False
    pagerank_score: float = 0.0
    in_circular_dependency: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('complexity_score', pre=True, always=True)
    def validate_complexity(cls, v):
        return float(v) if v else 0.0


class DatasetNode(BaseModel):
    """Represents a data dataset/table."""
    
    name: str
    storage_type: str  # table, file, stream, api
    schema_snapshot: Optional[Dict[str, str]] = Field(default_factory=dict)
    freshness_sla: Optional[str] = None  # Added missing field
    owner: Optional[str] = None
    is_source_of_truth: bool = False
    row_count: Optional[int] = None  # Additional useful field
    format: Optional[str] = None  # csv, parquet, json, etc.


class FunctionNode(BaseModel):
    """Represents a function or method."""
    
    qualified_name: str
    parent_module: str
    signature: str
    docstring: Optional[str] = None
    line_start: int
    line_end: int
    is_public: bool = True
    calls: List[str] = Field(default_factory=list)
    called_by: List[str] = Field(default_factory=list)
    complexity: Optional[int] = None  # Cyclomatic complexity


class TransformationNode(BaseModel):
    """Represents a data transformation."""
    
    source_datasets: List[str]
    target_datasets: List[str]
    transformation_type: str  # sql, python, config, dbt
    source_file: str
    line_range: tuple[int, int]
    sql_query_if_applicable: Optional[str] = None
    transformation_logic: Optional[str] = None  # Description of what it does
    framework: Optional[str] = None  # pandas, spark, dbt, etc.


# ============ EDGE TYPES - EXPLICITLY DEFINED ============

class ImportEdge(BaseModel):
    """Represents an import relationship between modules (edge type 1)."""
    
    source: str  # Module that imports
    target: str  # Module being imported
    import_type: str  # "absolute", "relative", "wildcard", "stdlib", "external"
    line_number: int
    is_dynamic: bool = False  # Dynamic import (__import__)
    alias: Optional[str] = None  # Import alias (import x as y)


class ProducesEdge(BaseModel):
    """Represents a transformation producing a dataset (edge type 2)."""
    
    source: str  # Transformation node
    target: str  # Dataset node being produced
    transformation_type: str  # sql, python, config
    source_file: str
    line_range: tuple[int, int]
    timestamp: Optional[datetime] = None
    is_incremental: bool = False


class ConsumesEdge(BaseModel):
    """Represents a transformation consuming a dataset (edge type 3)."""
    
    source: str  # Dataset node being consumed
    target: str  # Transformation node
    transformation_type: str  # sql, python, config
    source_file: str
    line_range: tuple[int, int]
    is_filter: bool = False  # Whether it's a filter operation
    join_type: Optional[str] = None  # inner, left, right, full


class CallsEdge(BaseModel):
    """Represents a function calling another function (edge type 4)."""
    
    source: str  # Caller function
    target: str  # Callee function
    line_number: int
    call_type: str  # "direct", "method", "constructor"
    within_module: bool  # Whether call is within same module


class ConfiguresEdge(BaseModel):
    """Represents a configuration file configuring a module/pipeline (edge type 5)."""
    
    source: str  # Config file (YAML, JSON, etc.)
    target: str  # Module or pipeline being configured
    config_type: str  # "dbt_project", "airflow_dag", "prefect_flow", "environment"
    parameter_count: int = 0
    parameters: List[str] = Field(default_factory=list)


# ============ GRAPH CONTAINER MODELS ============

class GraphMetadata(BaseModel):
    """Metadata for the entire knowledge graph."""
    
    repository: str
    analysis_timestamp: datetime
    total_modules: int
    total_imports: int
    languages: Dict[str, int]
    top_modules_by_pagerank: List[Dict[str, Any]]
    circular_dependencies: List[List[str]]
    dead_code_candidates: List[str]
    high_velocity_modules: List[Dict[str, Any]]
    graph_version: str = "1.0"


class KnowledgeGraphSchema(BaseModel):
    """Complete knowledge graph schema with typed nodes and edges."""
    
    nodes: List[Dict[str, Any]]  # Will contain typed nodes
    edges: List[Dict[str, Any]]  # Will contain typed edges
    metadata: GraphMetadata
    
    @validator('nodes')
    def validate_nodes(cls, v):
        """Ensure nodes have required fields."""
        for node in v:
            if 'type' not in node:
                raise ValueError(f"Node missing type field: {node}")
        return v
    
    @validator('edges')
    def validate_edges(cls, v):
        """Ensure edges have required fields."""
        for edge in v:
            if 'type' not in edge:
                raise ValueError(f"Edge missing type field: {edge}")
            if edge['type'] not in ['imports', 'produces', 'consumes', 'calls', 'configures']:
                raise ValueError(f"Invalid edge type: {edge['type']}")
        return v