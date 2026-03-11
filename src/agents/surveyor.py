"""Surveyor Agent - Static structure analysis."""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
import re
import networkx as nx
from git import Repo, InvalidGitRepositoryError
from src.models.schemas import ModuleNode, ImportEdge, GraphMetadata
from src.analyzers.tree_sitter_analyzer import ModuleAnalyzer

logger = logging.getLogger(__name__)


class GitVelocityAnalyzer:
    """Analyzes git history to compute change frequency."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            logger.error(f"Not a git repository: {repo_path}")
            self.repo = None
    
    def get_change_frequency(self, days: int = 30) -> Dict[str, int]:
        """Get change frequency for all files in the last N days."""
        if not self.repo:
            return {}
        
        since_date = datetime.now() - timedelta(days=days)
        commits = list(self.repo.iter_commits(since=since_date.isoformat()))
        
        file_changes = {}
        for commit in commits:
            for file in commit.stats.files:
                file_changes[file] = file_changes.get(file, 0) + 1
        
        return file_changes
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get git metadata for a specific file."""
        if not self.repo:
            return {}
        
        try:
            # Get relative path from repo root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            rel_path = rel_path.replace('\\', '/')
            
            commits = list(self.repo.iter_commits(paths=rel_path))
            if not commits:
                return {}
            
            authors = set()
            for commit in commits:
                authors.add(commit.author.email)
            
            return {
                "commit_count": len(commits),
                "last_modified": commits[0].committed_datetime,
                "authors": list(authors),
            }
        except Exception as e:
            logger.error(f"Error getting git metadata for {file_path}: {e}")
            return {}
    
    def find_high_velocity_core(self, file_changes: Dict[str, int]) -> List[Dict[str, Any]]:
        """Identify the 20% of files responsible for 80% of changes."""
        if not file_changes:
            return []
        
        # Sort by change count descending
        sorted_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)
        total_changes = sum(file_changes.values())
        
        if total_changes == 0:
            return []
        
        # Calculate 80% threshold
        threshold_80 = total_changes * 0.8
        
        cumulative = 0
        high_velocity = []
        
        for file, changes in sorted_files:
            cumulative += changes
            high_velocity.append({
                "file": file,
                "changes": changes,
                "cumulative_percentage": (cumulative / total_changes) * 100
            })
            if cumulative >= threshold_80:
                break
        
        return high_velocity


class ModuleGraphBuilder:
    """Builds and analyzes module import graphs."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()
        self.module_analyzer = ModuleAnalyzer()
        self.modules: Dict[str, ModuleNode] = {}
    
    def resolve_import_path(self, imp: str, current_file: str) -> Optional[str]:
        """Resolve an import statement to a file path."""
        # Clean the import
        imp_clean = imp.strip()
        
        # Handle standard library imports - THESE SHOULD BE COUNTED!
        std_libs = [
            'os', 'sys', 'time', 'json', 're', 'logging', 'datetime', 'pathlib', 
            'typing', 'requests', 'yaml', 'click', 'subprocess', 'tempfile', 'uuid',
            'dataclasses', 'enum', 'functools', 'itertools', 'collections', 'math'
        ]
        
        # Check if it's a standard library - return a special marker but COUNT IT!
        for lib in std_libs:
            if imp_clean == lib or imp_clean.startswith(lib + '.'):
                # Still count as an import even though we can't resolve the file
                return f"stdlib:{lib}"
        
        # Handle 'from x import y' format
        if ' from ' in imp_clean:
            parts = imp_clean.split(' from ')
            if len(parts) == 2:
                imp_clean = parts[1]
        
        # Handle 'import x' format
        if imp_clean.startswith('import '):
            imp_clean = imp_clean[7:]
        
        # Handle 'as' aliases
        if ' as ' in imp_clean:
            imp_clean = imp_clean.split(' as ')[0]
        
        # Handle commas (multiple imports on one line)
        if ',' in imp_clean:
            # Take the first one for resolution
            imp_clean = imp_clean.split(',')[0].strip()
        
        # If it's a simple name, it might be a local module
        if '.' not in imp_clean and imp_clean.isidentifier():
            # Check if there's a matching .py file in the same directory
            current_dir = os.path.dirname(current_file)
            local_path = os.path.join(current_dir, imp_clean + '.py')
            if os.path.exists(local_path):
                return os.path.relpath(local_path, self.repo_path)
        
        return None

    def add_imports(self, file_path: str, imports: List[str]) -> List[ImportEdge]:
        """Add import edges to the graph."""
        rel_path = os.path.relpath(file_path, self.repo_path).replace('\\', '/')
        edges = []
        
        for imp in imports:
            logger.debug(f"Processing import: '{imp}' from {rel_path}")
            
            # Try to extract the actual module name
            module_name = imp
            if imp.startswith('from '):
                # Handle "from x import y" format
                parts = imp.split()
                if len(parts) >= 2:
                    module_name = parts[1]
            elif imp.startswith('import '):
                # Handle "import x" format
                module_name = imp[7:]
            
            # Remove any aliases
            if ' as ' in module_name:
                module_name = module_name.split(' as ')[0]
            
            # Take first if multiple imports
            if ',' in module_name:
                module_name = module_name.split(',')[0].strip()
            
            logger.debug(f"Extracted module name: {module_name}")
            
            # Resolve import path
            target = self.resolve_import_path(imp, file_path)
            
            # In add_imports method:

            if target:
                if target in self.modules:
                    # Create typed import edge
                    edge = ImportEdge(
                        source=rel_path,
                        target=target,
                        import_type="absolute",
                        line_number=0,  # You can extract actual line number from AST if available
                        is_dynamic=False,
                        alias=None
                    )
                    # Add to knowledge graph using typed method
                    self.knowledge_graph.add_import_edge(edge)
                    edges.append(edge)
                    
                    # Update imported_by lists
                    if target in self.modules:
                        if rel_path not in self.modules[target].imported_by:
                            self.modules[target].imported_by.append(rel_path)
                            logger.debug(f"Added import: {rel_path} -> {target}")
            else:
                # Create virtual node for external import
                virtual_target = f"external:{imp}"
                if virtual_target not in self.modules:
                    from src.models.schemas import ModuleNode
                    virtual_module = ModuleNode(
                        path=virtual_target,
                        language="external",
                        loc=0,
                        imports=[],
                        change_velocity_30d=0,
                        is_dead_code_candidate=False,
                        pagerank_score=0.0,
                        in_circular_dependency=False
                    )
                    self.modules[virtual_target] = virtual_module
                    self.graph.add_node(virtual_target, **virtual_module.dict())
                
                # Create typed import edge for external
                edge = ImportEdge(
                    source=rel_path,
                    target=virtual_target,
                    import_type="external",
                    line_number=0,
                    is_dynamic=False,
                    alias=None
                )
                self.knowledge_graph.add_import_edge(edge)
                edges.append(edge)
                logger.debug(f"Added external import: {rel_path} -> {virtual_target}")
        
        return edges
    
    def add_module(self, file_path: str, analysis_result: Dict[str, Any]) -> ModuleNode:
        """Add a module to the graph."""
        rel_path = os.path.relpath(file_path, self.repo_path).replace('\\', '/')
        
        # Create module node
        module = ModuleNode(
            path=rel_path,
            language=analysis_result.get("language", "unknown"),
            loc=analysis_result.get("loc", 0),
            imports=analysis_result.get("imports", []),
            public_functions=[f.get('name') for f in analysis_result.get("functions", [])],
            public_classes=[c.get('name') for c in analysis_result.get("classes", [])],
            class_inheritance=analysis_result.get("class_inheritance", {}),
        )
        
        self.modules[rel_path] = module
        self.graph.add_node(rel_path, **module.dict())
        
        return module
    
    def compute_pagerank(self) -> Dict[str, float]:
        """Compute PageRank scores for all modules."""
        try:
            if self.graph.number_of_nodes() == 0:
                return {}
            
            pagerank = nx.pagerank(self.graph)
            
            # Update module nodes with scores
            for node, score in pagerank.items():
                if node in self.modules:
                    self.modules[node].pagerank_score = score
            
            return pagerank
        except Exception as e:
            logger.error(f"Error computing PageRank: {e}")
            return {}
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find strongly connected components (circular dependencies)."""
        try:
            cycles = []
            for component in nx.strongly_connected_components(self.graph):
                if len(component) > 1:
                    cycles.append(list(component))
                    # Mark modules in circular dependencies
                    for node in component:
                        if node in self.modules:
                            self.modules[node].in_circular_dependency = True
            return cycles
        except Exception as e:
            logger.error(f"Error finding circular dependencies: {e}")
            return []
    
    def find_dead_code_candidates(self) -> List[str]:
        """Find modules with no incoming imports (potential dead code)."""
        dead = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) > 0:
                # Module is imported by nothing but imports others
                if node in self.modules:
                    self.modules[node].is_dead_code_candidate = True
                    dead.append(node)
        return dead
    
    def get_top_modules(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top modules by PageRank score."""
        sorted_modules = sorted(
            self.modules.items(),
            key=lambda x: x[1].pagerank_score,
            reverse=True
        )[:n]
        
        return [
            {
                "path": path,
                "pagerank": module.pagerank_score,
                "language": module.language,
                "imports": len(module.imports),
                "imported_by": len(module.imported_by),
            }
            for path, module in sorted_modules
        ]


class SurveyorAgent:
    """Main Surveyor Agent orchestrator."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.git_analyzer = GitVelocityAnalyzer(repo_path)
        self.graph_builder = ModuleGraphBuilder(repo_path)
        self.results = {}
    
    def analyze(self) -> Dict[str, Any]:
        """Run complete surveyor analysis."""
        logger.info(f"Starting Surveyor analysis of {self.repo_path}")
        
        # Step 1: Find all Python files
        python_files = []
        for root, _, files in os.walk(self.repo_path):
            # Don't exclude .github - that's where the Python script is!
            if '__pycache__' in root or 'node_modules' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(python_files)} Python files")
        
        # Step 2: Analyze each file
        total_imports_found = 0
        for file_path in python_files:
            try:
                # Use tree-sitter to parse the file
                analysis = self.graph_builder.module_analyzer.analyze_module(file_path)
                if analysis:
                    module = self.graph_builder.add_module(file_path, analysis)
                    
                    # DEBUG: Print what imports were found
                    if analysis.get("imports"):
                        logger.debug(f"Raw imports from AST: {analysis['imports']}")
                        
                        # Extract imports properly - CRITICAL FIX!
                        edges = self.graph_builder.add_imports(file_path, analysis["imports"])
                        logger.debug(f"Added {len(edges)} import edges from {file_path}")
                        total_imports_found += len(edges)
                    else:
                        logger.debug(f"No imports found in AST for {file_path}")
                    
                    # Also count imports using regex method for verification
                    import_count = self._count_imports(file_path)
                    if import_count > 0:
                        logger.debug(f"Regex found {import_count} import statements in {file_path}")
                        
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
        
        logger.info(f"Built graph with {self.graph_builder.graph.number_of_nodes()} nodes and {self.graph_builder.graph.number_of_edges()} edges")
        logger.info(f"Total imports found across all files: {total_imports_found}")
        
        # Step 3: Compute git velocity
        logger.info("Computing git velocity...")
        file_changes = self.git_analyzer.get_change_frequency(days=30)
        high_velocity = self.git_analyzer.find_high_velocity_core(file_changes)
        
        # Update modules with git metadata
        for file, changes in file_changes.items():
            # Normalize path separators
            file_norm = file.replace('\\', '/')
            
            # Try to find matching module
            for module_path, module in self.graph_builder.modules.items():
                if file_norm.endswith(module_path) or module_path.endswith(file_norm):
                    module.change_velocity_30d = changes
                    
                    # Get detailed git metadata
                    full_path = os.path.join(self.repo_path, file)
                    if os.path.exists(full_path):
                        metadata = self.git_analyzer.get_file_metadata(full_path)
                        if metadata:
                            module.commit_count = metadata.get("commit_count", 0)
                            module.authors = metadata.get("authors", [])
                            if metadata.get("last_modified"):
                                module.last_modified = metadata["last_modified"]
                    break
        
        # Step 4: Graph analysis
        logger.info("Computing PageRank...")
        pagerank = self.graph_builder.compute_pagerank()
        
        logger.info("Finding circular dependencies...")
        cycles = self.graph_builder.find_circular_dependencies()
        
        logger.info("Finding dead code candidates...")
        dead_code = self.graph_builder.find_dead_code_candidates()
        
        # Step 5: Compile results
        metadata = GraphMetadata(
            repository=self.repo_path,
            analysis_timestamp=datetime.now(),
            total_modules=len(self.graph_builder.modules),
            total_imports=self.graph_builder.graph.number_of_edges(),
            languages=self._count_languages(),
            top_modules_by_pagerank=self.graph_builder.get_top_modules(10),
            circular_dependencies=cycles,
            dead_code_candidates=dead_code,
            high_velocity_modules=high_velocity,
        )
        
        self.results = {
            "metadata": metadata,
            "modules": self.graph_builder.modules,
            "graph": self.graph_builder.graph,
            "file_changes": file_changes,
            "high_velocity": high_velocity,
            "total_imports_found": total_imports_found,  # Add this for verification
        }
        
        logger.info("Surveyor analysis complete")
        logger.info(f"Final import count: {total_imports_found}")
        return self.results
    
    def _count_imports(self, file_path: str) -> int:
        """Count imports in a Python file (including stdlib)."""
        import_count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex to find import statements
            import_patterns = [
                r'^import\s+(\w+)',
                r'^from\s+(\w+)\s+import',
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                import_count += len(matches)
                
        except Exception as e:
            logger.debug(f"Error counting imports in {file_path}: {e}")
        
        return import_count
    
    def _count_languages(self) -> Dict[str, int]:
        """Count modules by language."""
        counts = {}
        for module in self.graph_builder.modules.values():
            lang = module.language
            counts[lang] = counts.get(lang, 0) + 1
        return counts
