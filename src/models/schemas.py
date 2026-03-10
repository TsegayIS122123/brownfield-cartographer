"""Pydantic models for the knowledge graph."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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
