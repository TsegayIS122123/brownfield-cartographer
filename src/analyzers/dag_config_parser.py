"""DAG Config Analyzer - Parses Airflow/dbt/Prefect YAML configs for pipeline topology."""

import os
import yaml
import re
import logging
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DAGConfigAnalyzer:
    """Analyzes DAG configuration files (Airflow, dbt, Prefect) for pipeline structure."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.dag_files = []
        self.dbt_projects = []
        self.airflow_dags = []
        self.prefect_flows = []
        self.all_sql_files = []
        
    def analyze(self) -> Dict[str, Any]:
        """Analyze all DAG configuration files in the repository."""
        logger.info("Analyzing DAG configuration files...")
        
        # First, find all SQL files in the repo (for dbt models)
        self._find_all_sql_files()
        
        # Find all YAML files that might be DAG configs
        for root, _, files in os.walk(self.repo_path):
            if '.git' in root or '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith(('.yml', '.yaml')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.repo_path)
                    
                    # Check if it's a dbt project
                    if file == 'dbt_project.yml':
                        self._parse_dbt_project(full_path, rel_path)
                    
                    # Check if it's a dbt package config
                    if file == 'packages.yml':
                        self._parse_dbt_packages(full_path, rel_path)
                    
                    # Check if it's a dbt source definition
                    if file == '__sources.yml' or file.endswith('_sources.yml'):
                        self._parse_dbt_sources(full_path, rel_path)
                    
                    # Check if it's a Prefect flow
                    if 'flow' in file.lower() or 'prefect' in file.lower():
                        self._parse_prefect_config(full_path, rel_path)
        
        # Also look for Airflow DAG Python files
        self._find_airflow_dags()
        
        return {
            "dbt_projects": self.dbt_projects,
            "airflow_dags": self.airflow_dags,
            "prefect_flows": self.prefect_flows,
            "total_configs": len(self.dbt_projects) + len(self.airflow_dags) + len(self.prefect_flows),
            "total_sql_files": len(self.all_sql_files),
        }
    
    def _find_all_sql_files(self):
        """Find all SQL files in the repository."""
        for root, _, files in os.walk(self.repo_path):
            if '.git' in root or '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith('.sql'):
                    rel_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                    self.all_sql_files.append(rel_path)
        
        logger.info(f"Found {len(self.all_sql_files)} total SQL files in repository")
    
    def _parse_dbt_project(self, file_path: str, rel_path: str):
        """Parse a dbt_project.yml file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            project_name = config.get('name', 'unknown')
            
            # Extract models configuration
            models_config = config.get('models', {})
            
            # Find all model files
            project_dir = os.path.dirname(file_path)
            model_files = []
            
            # Look in standard dbt directories
            model_dirs = ['models', 'analyses', 'marts', 'staging', 'intermediate']
            for model_dir in model_dirs:
                potential_path = os.path.join(project_dir, model_dir)
                if os.path.exists(potential_path):
                    for root, _, files in os.walk(potential_path):
                        for file in files:
                            if file.endswith('.sql'):
                                rel_model_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                                model_files.append(rel_model_path)
            
            # If no models found in standard dirs, look in all subdirs
            if not model_files:
                for root, _, files in os.walk(project_dir):
                    if '.git' in root or '__pycache__' in root:
                        continue
                    for file in files:
                        if file.endswith('.sql'):
                            rel_model_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                            model_files.append(rel_model_path)
            
            self.dbt_projects.append({
                "type": "dbt",
                "path": rel_path,
                "project_name": project_name,
                "config": {
                    "profile": config.get('profile'),
                    "version": config.get('version'),
                    "require_dbt_version": config.get('require-dbt-version'),
                },
                "models": model_files,
                "model_count": len(model_files),
                "model_directories": model_dirs,
            })
            
            logger.info(f"Found dbt project: {project_name} with {len(model_files)} models")
            
        except Exception as e:
            logger.error(f"Error parsing dbt project {file_path}: {e}")
    
    def _parse_dbt_packages(self, file_path: str, rel_path: str):
        """Parse a dbt packages.yml file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            packages = config.get('packages', [])
            logger.info(f"Found dbt packages.yml with {len(packages)} packages")
            
        except Exception as e:
            logger.error(f"Error parsing dbt packages {file_path}: {e}")
    
    def _parse_dbt_sources(self, file_path: str, rel_path: str):
        """Parse a dbt sources YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if config and 'sources' in config:
                for source in config['sources']:
                    source_name = source.get('name', 'unknown')
                    tables = source.get('tables', [])
                    logger.debug(f"Found dbt source: {source_name} with {len(tables)} tables")
                    
        except Exception as e:
            logger.error(f"Error parsing dbt sources {file_path}: {e}")
    
    def _find_airflow_dags(self):
        """Find Airflow DAG files (Python files with 'DAG' in them)."""
        for root, _, files in os.walk(self.repo_path):
            if '.git' in root or '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.repo_path)
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check if it's an Airflow DAG
                        if 'DAG(' in content and 'airflow' in content.lower():
                            self.airflow_dags.append({
                                "type": "airflow",
                                "path": rel_path,
                                "size": len(content.splitlines()),
                            })
                            
                    except Exception:
                        continue
    
    def _parse_prefect_config(self, file_path: str, rel_path: str):
        """Parse a Prefect flow configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.prefect_flows.append({
                "type": "prefect",
                "path": rel_path,
                "config": config,
            })
            
        except Exception as e:
            logger.error(f"Error parsing Prefect config {file_path}: {e}")
    
    def extract_dbt_lineage(self) -> Dict[str, Any]:
        """Extract lineage from dbt projects using ref() and source() calls."""
        lineage = {
            "nodes": set(),
            "edges": [],
            "sources": set(),
            "models": set(),
            "model_details": {},
        }
        
        # First, collect all models from dbt projects
        all_models = set()
        for project in self.dbt_projects:
            for model_path in project.get("models", []):
                model_name = os.path.basename(model_path).replace('.sql', '')
                all_models.add(model_name)
                lineage["models"].add(model_name)
                
                # Store model details
                lineage["model_details"][model_name] = {
                    "path": model_path,
                    "project": project.get("project_name"),
                    "refs": [],
                    "sources": [],
                }
        
        # Parse each model file for dependencies
        for project in self.dbt_projects:
            for model_path in project.get("models", []):
                full_path = os.path.join(self.repo_path, model_path)
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    model_name = os.path.basename(model_path).replace('.sql', '')
                    
                    # Extract refs
                    refs = re.findall(r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}", content)
                    # Extract sources
                    sources = re.findall(r"\{\{\s*source\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\)\s*\}\}", content)
                    
                    # Update model details
                    if model_name in lineage["model_details"]:
                        lineage["model_details"][model_name]["refs"] = refs
                        lineage["model_details"][model_name]["sources"] = sources
                    
                    lineage["nodes"].add(f"model:{model_name}")
                    
                    # Add ref edges
                    for ref in refs:
                        if ref in all_models:
                            lineage["nodes"].add(f"model:{ref}")
                            lineage["edges"].append({
                                "from": f"model:{ref}",
                                "to": f"model:{model_name}",
                                "type": "depends_on",
                                "via": "ref",
                            })
                        else:
                            # Reference to model not in this project (could be package)
                            lineage["nodes"].add(f"model:{ref}")
                            lineage["edges"].append({
                                "from": f"model:{ref}",
                                "to": f"model:{model_name}",
                                "type": "depends_on",
                                "via": "ref_external",
                            })
                    
                    # Add source edges
                    for source in sources:
                        source_name = f"{source[0]}.{source[1]}"
                        source_node = f"source:{source_name}"
                        lineage["nodes"].add(source_node)
                        lineage["sources"].add(source_name)
                        lineage["edges"].append({
                            "from": source_node,
                            "to": f"model:{model_name}",
                            "type": "depends_on",
                            "via": "source",
                            "source_name": source[0],
                            "table_name": source[1],
                        })
                        
                except Exception as e:
                    logger.error(f"Error parsing dbt model {model_path}: {e}")
        
        # Identify root models (no incoming refs) and leaf models (no outgoing refs)
        incoming_edges = {}
        outgoing_edges = {}
        
        for edge in lineage["edges"]:
            from_node = edge["from"]
            to_node = edge["to"]
            
            outgoing_edges[from_node] = outgoing_edges.get(from_node, 0) + 1
            incoming_edges[to_node] = incoming_edges.get(to_node, 0) + 1
        
        root_models = []
        leaf_models = []
        
        for model in lineage["models"]:
            model_node = f"model:{model}"
            if incoming_edges.get(model_node, 0) == 0:
                root_models.append(model)
            if outgoing_edges.get(model_node, 0) == 0:
                leaf_models.append(model)
        
        return {
            "nodes": list(lineage["nodes"]),
            "edges": lineage["edges"],
            "sources": list(lineage["sources"]),
            "models": list(lineage["models"]),
            "root_models": root_models,
            "leaf_models": leaf_models,
            "model_details": lineage["model_details"],
            "node_count": len(lineage["nodes"]),
            "edge_count": len(lineage["edges"]),
            "source_count": len(lineage["sources"]),
            "model_count": len(lineage["models"]),
        }
    
    def extract_airflow_lineage(self) -> Dict[str, Any]:
        """Extract lineage from Airflow DAGs (simplified)."""
        # This would require parsing Python AST for Airflow operators
        # For Phase 2, we'll return a simplified version
        return {
            "nodes": [],
            "edges": [],
            "dags": self.airflow_dags,
            "node_count": 0,
            "edge_count": 0,
        }
    
    def get_dbt_summary(self) -> Dict:
        """Get a summary of dbt projects."""
        summary = {
            "total_projects": len(self.dbt_projects),
            "total_models": sum(p.get("model_count", 0) for p in self.dbt_projects),
            "total_sql_files": len(self.all_sql_files),
            "projects": []
        }
        
        for project in self.dbt_projects:
            summary["projects"].append({
                "name": project.get("project_name"),
                "models": project.get("model_count", 0),
                "path": project.get("path"),
            })
        
        return summary