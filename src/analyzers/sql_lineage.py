"""SQL Lineage Analyzer - Extracts table dependencies from SQL files."""

import os
import re
import logging
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

import sqlglot
from sqlglot import parse_one, exp
from sqlglot.optimizer import optimize
from sqlglot.dialects import Dialect

logger = logging.getLogger(__name__)


class SQLLineageAnalyzer:
    """Analyzes SQL files for table dependencies and lineage."""
    
    # Supported SQL dialects
    SUPPORTED_DIALECTS = {
        "postgres": "postgres",
        "postgresql": "postgres",
        "bigquery": "bigquery",
        "snowflake": "snowflake",
        "duckdb": "duckdb",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "redshift": "redshift",
        "presto": "presto",
        "trino": "trino",
        "spark": "spark",
        "hive": "hive",
        "oracle": "oracle",
        "mssql": "mssql",
    }
    
    def __init__(self, dialect: str = "postgres"):
        """Initialize with specified SQL dialect."""
        self.dialect = self.SUPPORTED_DIALECTS.get(dialect.lower(), "postgres")
        logger.info(f"✅ SQL Lineage Analyzer initialized with dialect: {self.dialect}")
    
    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a SQL file and extract full lineage."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            return self.parse_sql(sql, file_path)
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    def preprocess_dbt_sql(self, sql: str) -> str:
        """Remove dbt Jinja templating for SQL parsing."""
        # Replace {{ ref('model_name') }} with just the model name
        sql = re.sub(r'\{\{\s*ref\([\'"]([^\'"]+)[\'"]\)\s*\}\}', r'\1', sql)
        
        # Replace {{ source('source_name', 'table_name') }} with table name
        sql = re.sub(r'\{\{\s*source\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"]\)\s*\}\}', r'\2', sql)
        
        # Remove other Jinja tags
        sql = re.sub(r'\{\{.*?\}\}', '', sql)
        sql = re.sub(r'\{%.*?%\}', '', sql)
        sql = re.sub(r'{#.*?#}', '', sql)
        
        return sql
    
    def extract_dbt_refs(self, sql: str) -> List[str]:
        """Extract dbt ref() calls from SQL."""
        refs = re.findall(r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}", sql)
        return list(set(refs))  # Remove duplicates
    
    def extract_dbt_sources(self, sql: str) -> List[Dict]:
        """Extract dbt source() calls from SQL."""
        sources = re.findall(r"\{\{\s*source\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\)\s*\}\}", sql)
        # Return as list of dicts with source_name and table_name
        return [{"source": s[0], "table": s[1], "full": f"{s[0]}.{s[1]}"} for s in sources]
    
    def extract_dbt_config(self, sql: str) -> Dict:
        """Extract dbt config() calls from SQL."""
        configs = re.findall(r"\{\{\s*config\(([^}]+)\)\s*\}\}", sql)
        config_dict = {}
        for config in configs:
            # Parse key=value pairs
            pairs = re.findall(r'([a-zA-Z_]+)\s*=\s*[\'"]([^\'"]+)[\'"]', config)
            for key, value in pairs:
                config_dict[key] = value
        return config_dict
    
    def parse_sql(self, sql: str, source: str = "<string>") -> Dict[str, Any]:
        """Parse SQL string and extract lineage information."""
        try:
            # Extract dbt-specific information first
            dbt_refs = self.extract_dbt_refs(sql)
            dbt_sources = self.extract_dbt_sources(sql)
            dbt_config = self.extract_dbt_config(sql)
            
            # Pre-process dbt templates for SQL parsing
            clean_sql = self.preprocess_dbt_sql(sql)
            
            # Check if it's a macro or non-SQL file
            if len(clean_sql.strip()) < 10 or '{%' in sql or '{#' in sql:
                return {
                    "source": source,
                    "is_macro": True,
                    "sql": sql[:100] + "..." if len(sql) > 100 else sql,
                    "tables_read": [],
                    "tables_written": [],
                    "dbt": {
                        "refs": dbt_refs,
                        "sources": dbt_sources,
                        "config": dbt_config,
                        "has_dbt": len(dbt_refs) > 0 or len(dbt_sources) > 0
                    },
                    "parse_success": False
                }
            
            # Try to parse with sqlglot, but be forgiving
            try:
                parsed = parse_one(clean_sql, dialect=self.dialect)
                
                # Extract tables (sources)
                tables = self._extract_tables(parsed)
                
                # Extract CTEs (intermediate)
                ctes = self._extract_ctes(parsed)
                
                # Extract targets (for CREATE/INSERT)
                targets = self._extract_targets(parsed)
                
                result = {
                    "source": source,
                    "sql": sql[:200] + "..." if len(sql) > 200 else sql,
                    "tables_read": tables,
                    "tables_written": targets,
                    "ctes": ctes,
                    "dbt": {
                        "refs": dbt_refs,
                        "sources": dbt_sources,
                        "config": dbt_config,
                        "has_dbt": len(dbt_refs) > 0 or len(dbt_sources) > 0
                    },
                    "parse_success": True
                }
                
                return result
                
            except Exception as parse_err:
                # If parsing fails, still return dbt info
                logger.debug(f"SQL parsing failed for {source}: {parse_err}")
                return {
                    "source": source,
                    "error": str(parse_err),
                    "sql": sql[:100] + "..." if len(sql) > 100 else sql,
                    "tables_read": [],
                    "tables_written": [],
                    "dbt": {
                        "refs": dbt_refs,
                        "sources": dbt_sources,
                        "config": dbt_config,
                        "has_dbt": len(dbt_refs) > 0 or len(dbt_sources) > 0
                    },
                    "parse_success": False
                }
                
        except Exception as e:
            logger.debug(f"Could not process SQL from {source}: {e}")
            return {
                "source": source,
                "error": str(e),
                "sql": sql[:100] + "..." if len(sql) > 100 else sql,
                "tables_read": [],
                "tables_written": [],
                "dbt": {
                    "refs": self.extract_dbt_refs(sql),
                    "sources": self.extract_dbt_sources(sql),
                    "has_dbt": "{{" in sql
                },
                "parse_success": False
            }
    
    def _extract_tables(self, parsed) -> List[Dict]:
        """Extract tables referenced in the query."""
        tables = []
        for table in parsed.find_all(exp.Table):
            # Get catalog, schema, table name
            catalog = table.catalog or None
            db = table.db or None
            name = table.name
            
            tables.append({
                "catalog": catalog,
                "database": db,
                "table": name,
                "full_name": table.sql(),
                "alias": table.alias or name,
            })
        
        # Remove duplicates
        unique_tables = []
        seen = set()
        for t in tables:
            key = f"{t['catalog']}.{t['database']}.{t['table']}"
            if key not in seen:
                seen.add(key)
                unique_tables.append(t)
        
        return unique_tables
    
    def _extract_ctes(self, parsed) -> List[Dict]:
        """Extract Common Table Expressions."""
        ctes = []
        for cte in parsed.find_all(exp.CTE):
            ctes.append({
                "alias": cte.alias,
                "sql": cte.this.sql(),
                "tables": self._extract_tables(cte.this),
            })
        return ctes
    
    def _extract_columns(self, parsed) -> List[Dict]:
        """Extract columns referenced in the query."""
        columns = []
        for column in parsed.find_all(exp.Column):
            columns.append({
                "table": column.table,
                "name": column.name,
                "full_name": column.sql(),
            })
        return columns
    
    def _extract_joins(self, parsed) -> List[Dict]:
        """Extract join information."""
        joins = []
        for join in parsed.find_all(exp.Join):
            joins.append({
                "side": join.side,
                "kind": join.kind,
                "table": join.this.sql(),
                "on": join.args.get("on").sql() if join.args.get("on") else None,
            })
        return joins
    
    def _get_operation_type(self, parsed) -> str:
        """Determine the type of SQL operation."""
        if isinstance(parsed, exp.Select):
            return "SELECT"
        elif isinstance(parsed, exp.Insert):
            return "INSERT"
        elif isinstance(parsed, exp.Update):
            return "UPDATE"
        elif isinstance(parsed, exp.Delete):
            return "DELETE"
        elif isinstance(parsed, exp.Create):
            return "CREATE"
        elif isinstance(parsed, exp.Alter):
            return "ALTER"
        elif isinstance(parsed, exp.Drop):
            return "DROP"
        else:
            return parsed.__class__.__name__
    
    def _extract_targets(self, parsed) -> List[Dict]:
        """Extract target tables (for writes)."""
        targets = []
        
        if isinstance(parsed, exp.Insert):
            if hasattr(parsed, 'this') and hasattr(parsed.this, 'this'):
                targets.append({
                    "type": "INSERT",
                    "table": parsed.this.this.sql(),
                })
        elif isinstance(parsed, exp.Update):
            if hasattr(parsed, 'this'):
                targets.append({
                    "type": "UPDATE",
                    "table": parsed.this.sql(),
                })
        elif isinstance(parsed, exp.Create):
            if hasattr(parsed, 'this') and hasattr(parsed.this, 'this'):
                targets.append({
                    "type": "CREATE",
                    "table": parsed.this.this.sql(),
                })
        
        return targets
    
    def _build_dependencies(self, tables: List[Dict], ctes: List[Dict], targets: List[Dict]) -> Dict:
        """Build dependency graph for this query."""
        return {
            "reads": [t["full_name"] for t in tables],
            "writes": [t["table"] for t in targets],
            "intermediate": [cte["alias"] for cte in ctes],
        }
    
    def extract_dbt_model_lineage(self, model_file: str) -> Dict:
        """Extract lineage from a dbt model file."""
        result = self.parse_file(model_file)
        
        if result and "dbt" in result:
            # Already have dbt info from parse_sql
            return result
        
        return result
    
    def build_dbt_lineage_graph(self, sql_files: List[str]) -> Dict:
        """Build a lineage graph specifically for dbt projects."""
        nodes = set()
        edges = []
        sources = set()
        models = set()
        
        for file in sql_files:
            lineage = self.parse_file(file)
            if not lineage:
                continue
            
            file_name = os.path.basename(file).replace('.sql', '')
            nodes.add(f"model:{file_name}")
            models.add(file_name)
            
            # Add dbt refs as edges
            for ref in lineage.get("dbt", {}).get("refs", []):
                nodes.add(f"model:{ref}")
                edges.append({
                    "from": f"model:{ref}",
                    "to": f"model:{file_name}",
                    "type": "depends_on",
                    "source": "dbt_ref"
                })
            
            # Add dbt sources as source nodes
            for source in lineage.get("dbt", {}).get("sources", []):
                source_node = f"source:{source['full']}"
                nodes.add(source_node)
                sources.add(source['full'])
                edges.append({
                    "from": source_node,
                    "to": f"model:{file_name}",
                    "type": "depends_on",
                    "source": "dbt_source"
                })
        
        return {
            "nodes": list(nodes),
            "edges": edges,
            "sources": list(sources),
            "models": list(models),
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def build_lineage_graph(self, sql_files: List[str]) -> Dict:
        """Build a complete lineage graph from multiple SQL files."""
        graph = {
            "nodes": set(),
            "edges": [],
            "sources": set(),
            "sinks": set(),
        }
        
        all_tables_read = set()
        all_tables_written = set()
        
        for file in sql_files:
            lineage = self.parse_file(file)
            if not lineage:
                continue
            
            # Add nodes
            graph["nodes"].add(file)
            for table in lineage.get("tables_read", []):
                node = f"table:{table['full_name']}"
                graph["nodes"].add(node)
                all_tables_read.add(table['full_name'])
                
                # Add edge: file reads table
                graph["edges"].append({
                    "from": file,
                    "to": node,
                    "type": "reads",
                })
            
            for target in lineage.get("tables_written", []):
                node = f"table:{target['table']}"
                graph["nodes"].add(node)
                all_tables_written.add(target['table'])
                
                # Add edge: file writes table
                graph["edges"].append({
                    "from": file,
                    "to": node,
                    "type": "writes",
                })
        
        # Identify sources (tables only read, never written)
        graph["sources"] = all_tables_read - all_tables_written
        
        # Identify sinks (tables only written, never read)
        graph["sinks"] = all_tables_written - all_tables_read
        
        return {
            "nodes": list(graph["nodes"]),
            "edges": graph["edges"],
            "sources": list(graph["sources"]),
            "sinks": list(graph["sinks"]),
        }