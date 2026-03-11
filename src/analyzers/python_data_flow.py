"""Python Data Flow Analyzer - Extracts data operations from Python code."""

import os
import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_python

logger = logging.getLogger(__name__)


class PythonDataFlowAnalyzer:
    """Analyzes Python files for data operations (pandas, PySpark, SQLAlchemy)."""
    
    # Enhanced patterns for data operations with classification
    DATA_PATTERNS = {
        # ============ READ OPERATIONS ============
        # pandas reads
        "read_csv": r'pd\.read_csv\(([^)]+)\)',
        "read_sql": r'pd\.read_sql\(([^)]+)\)',
        "read_sql_query": r'pd\.read_sql_query\(([^)]+)\)',
        "read_sql_table": r'pd\.read_sql_table\(([^)]+)\)',
        "read_parquet": r'pd\.read_parquet\(([^)]+)\)',
        "read_json": r'pd\.read_json\(([^)]+)\)',
        "read_excel": r'pd\.read_excel\(([^)]+)\)',
        "read_table": r'pd\.read_table\(([^)]+)\)',
        "read_hdf": r'pd\.read_hdf\(([^)]+)\)',
        "read_feather": r'pd\.read_feather\(([^)]+)\)',
        "read_orc": r'pd\.read_orc\(([^)]+)\)',
        "read_sas": r'pd\.read_sas\(([^)]+)\)',
        "read_spss": r'pd\.read_spss\(([^)]+)\)',
        "read_fwf": r'pd\.read_fwf\(([^)]+)\)',
        "read_gbq": r'pd\.read_gbq\(([^)]+)\)',
        
        # Spark reads
        "spark_read_csv": r'spark\.read\.(?:format\("csv"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*load\(([^)]+)\)|spark\.read\.csv\(([^)]+)\)',
        "spark_read_parquet": r'spark\.read\.(?:format\("parquet"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*load\(([^)]+)\)|spark\.read\.parquet\(([^)]+)\)',
        "spark_read_json": r'spark\.read\.(?:format\("json"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*load\(([^)]+)\)|spark\.read\.json\(([^)]+)\)',
        "spark_read_table": r'spark\.read\.table\(([^)]+)\)',
        "spark_read_jdbc": r'spark\.read\.jdbc\(([^)]+)\)',
        "spark_read_orc": r'spark\.read\.orc\(([^)]+)\)',
        "spark_read_delta": r'spark\.read\.format\("delta"\)\.load\(([^)]+)\)',
        
        # Spark SQL (both read and transform)
        "spark_sql": r'spark\.sql\(([^)]+)\)',
        
        # SQLAlchemy reads
        "engine_execute": r'engine\.execute\(([^)]+)\)',
        "session_execute": r'session\.execute\(([^)]+)\)',
        "connection_execute": r'connection\.execute\(([^)]+)\)',
        "cursor_execute": r'cursor\.execute\(([^)]+)\)',
        "db_execute": r'execute\(([^)]+)\)',
        
        # ============ WRITE OPERATIONS ============
        # pandas writes
        "to_csv": r'\.to_csv\(([^)]+)\)',
        "to_sql": r'\.to_sql\(([^)]+)\)',
        "to_parquet": r'\.to_parquet\(([^)]+)\)',
        "to_json": r'\.to_json\(([^)]+)\)',
        "to_excel": r'\.to_excel\(([^)]+)\)',
        "to_hdf": r'\.to_hdf\(([^)]+)\)',
        "to_feather": r'\.to_feather\(([^)]+)\)',
        "to_orc": r'\.to_orc\(([^)]+)\)',
        "to_string": r'\.to_string\(([^)]+)\)',
        "to_markdown": r'\.to_markdown\(([^)]+)\)',
        "to_clipboard": r'\.to_clipboard\(([^)]+)\)',
        "to_latex": r'\.to_latex\(([^)]+)\)',
        "to_html": r'\.to_html\(([^)]+)\)',
        "to_dict": r'\.to_dict\(([^)]+)\)',
        "to_numpy": r'\.to_numpy\(([^)]+)\)',
        
        # Spark writes
        "spark_write_csv": r'\.write\.(?:format\("csv"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*save\(([^)]+)\)|\.write\.csv\(([^)]+)\)',
        "spark_write_parquet": r'\.write\.(?:format\("parquet"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*save\(([^)]+)\)|\.write\.parquet\(([^)]+)\)',
        "spark_write_json": r'\.write\.(?:format\("json"\)\.)?(?:option\("[^"]+",\s*"[^"]+"\)\.)*save\(([^)]+)\)|\.write\.json\(([^)]+)\)',
        "spark_write_table": r'\.write\.saveAsTable\(([^)]+)\)',
        "spark_write_jdbc": r'\.write\.jdbc\(([^)]+)\)',
        "spark_write_orc": r'\.write\.orc\(([^)]+)\)',
        "spark_write_delta": r'\.write\.format\("delta"\)\.save\(([^)]+)\)',
        "spark_insert_into": r'\.write\.insertInto\(([^)]+)\)',
        
        # ============ TRANSFORM OPERATIONS ============
        # pandas transforms
        "merge": r'\.merge\(([^)]+)\)',
        "join": r'\.join\(([^)]+)\)',
        "concat": r'pd\.concat\(([^)]+)\)',
        "groupby": r'\.groupby\(([^)]+)\)',
        "pivot": r'\.pivot\(([^)]+)\)',
        "pivot_table": r'\.pivot_table\(([^)]+)\)',
        "melt": r'\.melt\(([^)]+)\)',
        "stack": r'\.stack\(([^)]+)\)',
        "unstack": r'\.unstack\(([^)]+)\)',
        "query": r'\.query\(([^)]+)\)',
        "eval": r'\.eval\(([^)]+)\)',
        "assign": r'\.assign\(([^)]+)\)',
        "apply": r'\.apply\(([^)]+)\)',
        "applymap": r'\.applymap\(([^)]+)\)',
        "pipe": r'\.pipe\(([^)]+)\)',
        "agg": r'\.agg\(([^)]+)\)',
        "aggregate": r'\.aggregate\(([^)]+)\)',
        "transform": r'\.transform\(([^)]+)\)',
        "filter": r'\.filter\(([^)]+)\)',
        "where": r'\.where\(([^)]+)\)',
        "mask": r'\.mask\(([^)]+)\)',
        "drop": r'\.drop\(([^)]+)\)',
        "dropna": r'\.dropna\(([^)]+)\)',
        "fillna": r'\.fillna\(([^)]+)\)',
        "replace": r'\.replace\(([^)]+)\)',
        "rename": r'\.rename\(([^)]+)\)',
        "sort_values": r'\.sort_values\(([^)]+)\)',
        "sort_index": r'\.sort_index\(([^)]+)\)',
        "sample": r'\.sample\(([^)]+)\)',
        "nlargest": r'\.nlargest\(([^)]+)\)',
        "nsmallest": r'\.nsmallest\(([^)]+)\)',
        
        # Spark transforms
        "spark_filter": r'\.filter\(([^)]+)\)',
        "spark_where": r'\.where\(([^)]+)\)',
        "spark_select": r'\.select\(([^)]+)\)',
        "spark_selectExpr": r'\.selectExpr\(([^)]+)\)',
        "spark_withColumn": r'\.withColumn\(([^)]+)\)',
        "spark_withColumnRenamed": r'\.withColumnRenamed\(([^)]+)\)',
        "spark_groupBy": r'\.groupBy\(([^)]+)\)',
        "spark_agg": r'\.agg\(([^)]+)\)',
        "spark_join": r'\.join\(([^)]+)\)',
        "spark_union": r'\.union\(([^)]+)\)',
        "spark_unionByName": r'\.unionByName\(([^)]+)\)',
        "spark_intersect": r'\.intersect\(([^)]+)\)',
        "spark_except": r'\.except\(([^)]+)\)',
        "spark_drop": r'\.drop\(([^)]+)\)',
        "spark_dropDuplicates": r'\.dropDuplicates\(([^)]+)\)',
        "spark_distinct": r'\.distinct\(([^)]+)\)',
        "spark_limit": r'\.limit\(([^)]+)\)',
        "spark_orderBy": r'\.orderBy\(([^)]+)\)',
        "spark_sort": r'\.sort\(([^)]+)\)',
        "spark_repartition": r'\.repartition\(([^)]+)\)',
        "spark_coalesce": r'\.coalesce\(([^)]+)\)',
        
        # SQLAlchemy transforms
        "sqlalchemy_select": r'select\(([^)]+)\)',
        "sqlalchemy_insert": r'insert\(([^)]+)\)',
        "sqlalchemy_update": r'update\(([^)]+)\)',
        "sqlalchemy_delete": r'delete\(([^)]+)\)',
        "sqlalchemy_join": r'join\(([^)]+)\)',
        "sqlalchemy_outerjoin": r'outerjoin\(([^)]+)\)',
        
        # ============ GENERAL ============
        "variable_assignment": r'(\w+)\s*=\s*(.+)',
        
        # ============ DBT CLOUD SCRIPT PATTERNS ============
        "requests_post": r'requests\.post\(([^)]+)\)',
        "requests_get": r'requests\.get\(([^)]+)\)',
        "os_getenv": r'os\.getenv\(([^)]+)\)',
        "os_environ_get": r'os\.environ\.get\(([^)]+)\)',
        "os_environ_item": r'os\.environ\[([^\]]+)\]',
        "print_statement": r'print\(([^)]+)\)',
        "time_sleep": r'time\.sleep\(([^)]+)\)',
        "f_string": r'f["\'].*?\{.*?\}.*?["\']',
        "environment_variable": r'os\.environ\[[\'"]([^\'"]+)[\'"]\]',
        
        # Function definitions and calls
        "function_def": r'def (\w+)\(([^)]*)\):',
        "function_call": r'(\w+)\(([^)]*)\)',
        "method_call": r'(\w+)\.(\w+)\(([^)]*)\)',
        
        # Custom function calls in the script
        "run_job_call": r'run_job\(([^)]+)\)',
        "get_run_status_call": r'get_run_status\(([^)]+)\)',
        "main_function": r'if __name__ == ["\']__main__["\']:',
        
        # Exception handling
        "try_except": r'try:',
        "except_block": r'except (\w+) as (\w+):',
        "raise_exception": r'raise (\w+)\(([^)]*)\)',
        
        # Logging
        "logging_info": r'logging\.info\(([^)]+)\)',
        "logging_debug": r'logging\.debug\(([^)]+)\)',
        "logging_error": r'logging\.error\(([^)]+)\)',
        
        # Type hints
        "type_hint": r':\s*(\w+(?:\[.*?\])?)',
        
        # Additional patterns for dbt Cloud script
        "dict_access": r'\[\s*[\'"](\w+)[\'"]\s*\]',
        "format_string": r'\.format\(([^)]+)\)',
        "join_method": r'\.join\(([^)]+)\)',
        "replace_method": r'\.replace\(([^)]+)\)',
        "strip_method": r'\.strip\(\)',
    }
    
    # Operation type classification - expanded for better detection
    READ_KEYWORDS = ['read', 'load', 'get', 'fetch', 'query', 'select', 'retrieve', 'download']
    WRITE_KEYWORDS = ['write', 'save', 'to_', 'insert', 'update', 'delete', 'drop', 'post', 'put', 'send', 'upload']
    TRANSFORM_KEYWORDS = ['merge', 'join', 'concat', 'group', 'pivot', 'melt', 'stack', 
                          'apply', 'pipe', 'agg', 'filter', 'where', 'drop', 'fill', 
                          'replace', 'rename', 'sort', 'sample', 'process', 'parse', 
                          'convert', 'format', 'build', 'prepare']
    
    def __init__(self):
        """Initialize the Python parser."""
        try:
            py_language = Language(tree_sitter_python.language())
            self.parser = Parser(py_language)
            logger.info("✅ Python parser initialized for data flow analysis")
        except Exception as e:
            logger.error(f"Failed to initialize Python parser: {e}")
            self.parser = None
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file for data operations."""
        if not self.parser:
            return {"error": "Parser not initialized"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # DEBUG: Print first few lines to see what we're analyzing
            logger.debug(f"Analyzing file: {file_path}")
            lines = code.split('\n')
            logger.debug(f"First 5 lines: {lines[:5]}")
            
            # Extract data operations
            operations = self._extract_operations(code, file_path)
            
            # DEBUG: Print what we found
            logger.debug(f"Found {len(operations)} raw operations")
            for op in operations[:5]:  # Print first 5
                logger.debug(f"  Operation: {op['type']} at line {op['line']}: {op['code'][:50]}")
            
            # Extract embedded SQL
            sql_queries = self.extract_sql_from_python(file_path)
            
            # Classify operations with enhanced detection
            reads, writes, transforms = self._classify_operations(operations)
            
            # DEBUG: Print classification results
            logger.debug(f"Classified: {len(reads)} reads, {len(writes)} writes, {len(transforms)} transforms")
            
            # Build data flow within the file
            flow = self._build_file_flow(reads, writes, transforms)
            
            # Get file summary stats
            stats = {
                "total_ops": len(operations),
                "total_reads": len(reads),
                "total_writes": len(writes),
                "total_transforms": len(transforms),
                "total_sql": len(sql_queries),
            }
            
            return {
                "file": file_path,
                "operations": operations,
                "sql_queries": sql_queries,
                "flow": flow,
                "reads": reads,
                "writes": writes,
                "transforms": transforms,
                "stats": stats,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {"error": str(e), "file": file_path}
    
    def _extract_operations(self, code: str, file_path: str) -> List[Dict]:
        """Extract data operations using regex patterns."""
        operations = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Check each pattern
            for op_type, pattern in self.DATA_PATTERNS.items():
                try:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Get the captured argument (handle multiple capture groups)
                        args = None
                        groups = match.groups()
                        
                        if groups:
                            # Take the first non-None group
                            for group in groups:
                                if group is not None:
                                    args = group
                                    break
                        
                        # Special handling for function definitions
                        if op_type == "function_def" and not args and len(groups) >= 2:
                            args = f"{groups[0]}({groups[1] if groups[1] else ''})"
                        
                        # Try to extract dataset name/path
                        dataset = self._extract_dataset_name(args) if args else None
                        
                        # For function calls without args, use the function name
                        if not dataset and "function" in op_type and groups and groups[0]:
                            dataset = f"function:{groups[0]}"
                        
                        operations.append({
                            "type": op_type,
                            "line": line_num,
                            "code": line.strip(),
                            "dataset": dataset,
                            "args": args.strip() if args else "",
                            "file": file_path,
                            "is_dynamic": self._is_dynamic(args) if args else False,
                            "context": self._get_context(lines, i, 2),
                        })
                except Exception as e:
                    logger.debug(f"Error matching pattern {op_type}: {e}")
                    continue
        
        return operations
    
    def _get_context(self, lines: List[str], line_idx: int, context_lines: int = 2) -> Dict:
        """Get surrounding context for an operation."""
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        
        return {
            "before": lines[start:line_idx],
            "after": lines[line_idx+1:end],
            "line": line_idx + 1
        }
    
    def _get_operation_category(self, op_type: str) -> str:
        """Determine if operation is read, write, or transform."""
        op_lower = op_type.lower()
        
        if any(keyword in op_lower for keyword in self.READ_KEYWORDS):
            return "read"
        elif any(keyword in op_lower for keyword in self.WRITE_KEYWORDS):
            return "write"
        elif any(keyword in op_lower for keyword in self.TRANSFORM_KEYWORDS):
            return "transform"
        else:
            return "unknown"
    
    def _classify_operations(self, operations: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Classify operations into reads, writes, and transforms."""
        reads = []
        writes = []
        transforms = []
        
        # Extended keywords for better detection
        READ_KEYWORDS_EXTENDED = self.READ_KEYWORDS + [
            'get_run_status', 'request_get', 'poll', 'check'
        ]
        
        WRITE_KEYWORDS_EXTENDED = self.WRITE_KEYWORDS + [
            'run_job', 'request_post', 'trigger', 'execute', 'invoke'
        ]
        
        TRANSFORM_KEYWORDS_EXTENDED = self.TRANSFORM_KEYWORDS + [
            'build_payload', 'format_url', 'prepare_request', 'construct'
        ]
        
        for op in operations:
            category = op.get("category", "unknown")
            
            # If already categorized, use that
            if category == "read":
                reads.append(op)
                continue
            elif category == "write":
                writes.append(op)
                continue
            elif category == "transform":
                transforms.append(op)
                continue
            
            # Try to classify based on type and code content
            op_type = op["type"].lower()
            code = op.get("code", "").lower()
            args = op.get("args", "").lower()
            
            # Check for read operations
            if any(k in op_type for k in READ_KEYWORDS_EXTENDED):
                reads.append(op)
                op["category"] = "read"
            elif 'get_run_status' in code or 'requests.get' in code:
                reads.append(op)
                op["category"] = "read"
            elif 'getenv' in op_type or 'environ' in op_type:
                reads.append(op)
                op["category"] = "read"
            
            # Check for write operations
            elif any(k in op_type for k in WRITE_KEYWORDS_EXTENDED):
                writes.append(op)
                op["category"] = "write"
            elif 'run_job' in code or 'requests.post' in code:
                writes.append(op)
                op["category"] = "write"
            elif 'print' in op_type:
                writes.append(op)  # Print outputs data to console
                op["category"] = "write"
            
            # Check for transform operations
            elif any(k in op_type for k in TRANSFORM_KEYWORDS_EXTENDED):
                transforms.append(op)
                op["category"] = "transform"
            elif any(k in code for k in ['build_payload', 'format', 'prepare']):
                transforms.append(op)
                op["category"] = "transform"
            elif 'replace' in op_type or 'strip' in op_type:
                transforms.append(op)
                op["category"] = "transform"
            
            # Check for main function (control flow)
            elif 'main_function' in op_type:
                transforms.append(op)
                op["category"] = "transform"
            
            # Default to unknown but log for debugging
            else:
                logger.debug(f"Unclassified operation: {op_type} - {code[:50]}")
        
        logger.debug(f"Classified: {len(reads)} reads, {len(writes)} writes, {len(transforms)} transforms")
        return reads, writes, transforms
    
    def _extract_dataset_name(self, args: str) -> Optional[str]:
        """Extract dataset name from function arguments."""
        if not args:
            return None
        
        args = args.strip()
        
        # Handle f-strings and complex expressions
        if 'f"' in args or "f'" in args:
            # Try to extract string literals from f-string
            string_match = re.search(r'[\'"]([^\'"]+)[\'"]', args)
            if string_match:
                return f"[FSTRING:{string_match.group(1)}]"
            return "[DYNAMIC_F_STRING]"
        
        # Try to extract string literal
        string_match = re.search(r'[\'"]([^\'"]+)[\'"]', args)
        if string_match:
            return string_match.group(1)
        
        # Check for variable
        var_match = re.search(r'(\w+)', args)
        if var_match and len(var_match.group(1)) > 1:
            # Check if it looks like a URL or path
            if 'http' in args or '://' in args:
                return "[URL]"
            return f"${{{var_match.group(1)}}}"
        
        return "[UNKNOWN]"
    
    def _is_dynamic(self, args: str) -> bool:
        """Check if the dataset reference is dynamic (f-string or variable)."""
        if not args:
            return False
        return ('f"' in args or "f'" in args or '${' in args or 
                (re.search(r'\b\w+\b', args) and not re.search(r'[\'"][^\'"]+[\'"]', args)))
    
    def _build_file_flow(self, reads: List[Dict], writes: List[Dict], transforms: List[Dict]) -> Dict:
        """Build data flow within a single file."""
        return {
            "reads": reads,
            "writes": writes,
            "transforms": transforms,
            "read_count": len(reads),
            "write_count": len(writes),
            "transform_count": len(transforms),
        }
    
    def extract_table_dependencies(self, file_path: str) -> List[Dict]:
        """Extract table dependencies from SQL operations."""
        result = self.analyze_file(file_path)
        dependencies = []
        
        for op in result.get("operations", []):
            if "sql" in op["type"].lower() and op.get("dataset"):
                dependencies.append({
                    "source_file": file_path,
                    "table": op["dataset"],
                    "operation": op["type"],
                    "category": op.get("category", "unknown"),
                    "line": op["line"],
                    "is_dynamic": op.get("is_dynamic", False),
                })
        
        return dependencies
    
    def find_dataframe_operations(self, file_path: str) -> Dict:
        """Find pandas DataFrame operations and transformations."""
        result = self.analyze_file(file_path)
        
        df_ops = []
        for op in result.get("operations", []):
            if "pandas" in op["type"] or "dataframe" in op["code"].lower():
                df_ops.append(op)
        
        return {
            "file": file_path,
            "dataframe_operations": df_ops,
            "count": len(df_ops),
        }
    
    def extract_sql_from_python(self, file_path: str) -> List[Dict]:
        """Extract SQL queries from Python strings."""
        sql_queries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Enhanced SQL patterns
            sql_patterns = [
                # Triple-quoted strings with SQL keywords
                (r'"""(.*?SELECT.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?SELECT.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?FROM.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?FROM.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?WHERE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?WHERE.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?JOIN.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?JOIN.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?GROUP BY.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?GROUP BY.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?ORDER BY.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?ORDER BY.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?INSERT INTO.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?INSERT INTO.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?UPDATE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?UPDATE.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?DELETE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?DELETE.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?CREATE TABLE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?CREATE TABLE.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?ALTER TABLE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?ALTER TABLE.*?)'''", re.DOTALL | re.IGNORECASE),
                (r'"""(.*?DROP TABLE.*?)"""', re.DOTALL | re.IGNORECASE),
                (r"'''(.*?DROP TABLE.*?)'''", re.DOTALL | re.IGNORECASE),
                
                # Variable assignments containing SQL
                (r'sql\s*=\s*["\'](.*?SELECT.*?)["\']', re.IGNORECASE),
                (r'query\s*=\s*["\'](.*?SELECT.*?)["\']', re.IGNORECASE),
                (r'sql_query\s*=\s*["\'](.*?SELECT.*?)["\']', re.IGNORECASE),
                (r'statement\s*=\s*["\'](.*?SELECT.*?)["\']', re.IGNORECASE),
                (r'sql\s*=\s*["\'](.*?FROM.*?)["\']', re.IGNORECASE),
                (r'query\s*=\s*["\'](.*?FROM.*?)["\']', re.IGNORECASE),
                
                # Multi-line string building
                (r'\(\s*["\'](.*?SELECT.*?)["\']\s*\+\s*["\'](.*?)["\']\s*\)', re.DOTALL | re.IGNORECASE),
                
                # SQLAlchemy text() constructs
                (r'text\(["\'](.*?SELECT.*?)["\']\)', re.IGNORECASE),
                (r'text\(["\'](.*?FROM.*?)["\']\)', re.IGNORECASE),
                
                # f-string SQL patterns
                (r'f["\'](.*?SELECT.*?\{.*?\}.*?)["\']', re.DOTALL | re.IGNORECASE),
                (r'f["\'](.*?FROM.*?\{.*?\}.*?)["\']', re.DOTALL | re.IGNORECASE),
            ]
            
            for pattern, flags in sql_patterns:
                try:
                    matches = re.findall(pattern, content, flags)
                    for match in matches:
                        # Handle tuple results from multiple capture groups
                        if isinstance(match, tuple):
                            sql_text = ' '.join([m for m in match if m and len(m) > 5])
                        else:
                            sql_text = match
                        
                        if not sql_text or len(sql_text) < 10:
                            continue
                        
                        # Clean up the SQL
                        sql_text = sql_text.strip()
                        
                        # Validate it's likely SQL (has keywords and reasonable length)
                        if (len(sql_text) > 20 and 
                            any(keyword in sql_text.upper() for keyword in 
                                ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY',
                                 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])):
                            
                            # Try to extract table names
                            tables = self._extract_tables_from_sql(sql_text)
                            
                            sql_queries.append({
                                "file": file_path,
                                "sql": sql_text[:200] + "..." if len(sql_text) > 200 else sql_text,
                                "full_sql": sql_text if len(sql_text) < 1000 else sql_text[:1000] + "...",
                                "type": "embedded_sql",
                                "tables": tables,
                                "length": len(sql_text),
                            })
                except Exception as e:
                    logger.debug(f"Error with SQL pattern {pattern[:30]}: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"Error extracting SQL from {file_path}: {e}")
        
        return sql_queries
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL string."""
        tables = []
        try:
            # Simple regex to find table names after FROM or JOIN
            from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            into_pattern = r'INTO\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            update_pattern = r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            table_pattern = r'table\s*=\s*[\'"]([^\'"]+)[\'"]'
            
            for pattern in [from_pattern, join_pattern, into_pattern, update_pattern, table_pattern]:
                matches = re.findall(pattern, sql, re.IGNORECASE)
                tables.extend(matches)
            
            # Remove duplicates and clean up
            tables = list(set(tables))
            
        except Exception:
            pass
        
        return tables
    
    def get_file_summary(self, file_path: str) -> Dict:
        """Get a summary of data operations in a file."""
        result = self.analyze_file(file_path)
        
        if "error" in result:
            return {"file": file_path, "error": result["error"]}
        
        return {
            "file": file_path,
            "stats": result.get("stats", {}),
            "has_reads": len(result.get("reads", [])) > 0,
            "has_writes": len(result.get("writes", [])) > 0,
            "has_transforms": len(result.get("transforms", [])) > 0,
            "has_sql": len(result.get("sql_queries", [])) > 0,
            "operations_by_category": {
                "read": len(result.get("reads", [])),
                "write": len(result.get("writes", [])),
                "transform": len(result.get("transforms", [])),
                "sql": len(result.get("sql_queries", [])),
            }
        }