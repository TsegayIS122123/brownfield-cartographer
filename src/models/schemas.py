"""Pydantic models for the knowledge graph."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ModuleNode(BaseModel):
    """Represents a code module/file."""

    path: str
    language: str
    purpose_statement: Optional[str] = None
    complexity_score: float = 0.0
    change_velocity_30d: int = 0
    is_dead_code_candidate: bool = False
    last_modified: Optional[datetime] = None


class DatasetNode(BaseModel):
    """Represents a data dataset/table."""

    name: str
    storage_type: str  # table, file, stream, api
    schema_snapshot: Optional[Dict[str, str]] = None
    owner: Optional[str] = None
    is_source_of_truth: bool = False


class FunctionNode(BaseModel):
    """Represents a function or method."""

    qualified_name: str
    parent_module: str
    signature: str
    purpose_statement: Optional[str] = None
    call_count_within_repo: int = 0
    is_public_api: bool = False


class TransformationNode(BaseModel):
    """Represents a data transformation."""

    source_datasets: List[str]
    target_datasets: List[str]
    transformation_type: str  # sql, python, config
    source_file: str
    line_range: tuple[int, int]
    sql_query_if_applicable: Optional[str] = None
"""Pydantic models for the knowledge graph."""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel, Field


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
    is_dead_code_candidate: bool = False
    pagerank_score: float = 0.0
    in_circular_dependency: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


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


class ClassNode(BaseModel):
    """Represents a class."""
    
    qualified_name: str
    parent_module: str
    bases: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    line_start: int
    line_end: int
    is_public: bool = True


class ImportEdge(BaseModel):
    """Represents an import relationship between modules."""
    
    source: str  # Module that imports
    target: str  # Module being imported
    import_type: str  # "absolute", "relative", "wildcard"
    line_number: int


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