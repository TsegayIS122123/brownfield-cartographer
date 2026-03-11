
"""Multi-language AST parsing using tree-sitter."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import tree_sitter
from tree_sitter import Language, Parser

# Import grammars
import tree_sitter_python
import tree_sitter_sql
import tree_sitter_yaml
import tree_sitter_javascript
import tree_sitter_typescript

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validates if a string is actually SQL."""
    
    # SQL keywords that indicate a real query
    SQL_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
        'INNER JOIN', 'OUTER JOIN', 'GROUP BY', 'ORDER BY', 'HAVING',
        'INSERT INTO', 'UPDATE', 'DELETE FROM', 'CREATE TABLE',
        'ALTER TABLE', 'DROP TABLE', 'WITH', 'UNION', 'UNION ALL',
        'VALUES', 'SET', 'AS', 'DISTINCT', 'COUNT(', 'SUM(', 'AVG(',
        'MIN(', 'MAX(', 'CASE WHEN', 'OVER(', 'PARTITION BY'
    ]
    
    # Patterns that indicate test strings or comments
    TEST_PATTERNS = [
        r'Test that',
        r'Tests? for',
        r'Integration test',
        r'Unit test',
        r'Check that',
        r'Verify that',
        r'Should ',
        r'Expected ',
        r'assert ',
        r'pytest',
        r'unittest',
    ]
    
    @classmethod
    def is_likely_sql(cls, text: str) -> bool:
        """Determine if a string is likely SQL."""
        if not text or len(text) < 10:
            return False
        
        upper_text = text.upper()
        
        # Check for test patterns
        for pattern in cls.TEST_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Must have at least 2 SQL keywords
        keyword_count = 0
        for keyword in cls.SQL_KEYWORDS:
            if keyword in upper_text:
                keyword_count += 1
                if keyword_count >= 2:
                    return True
        
        return False


class LanguageRouter:
    """Routes files to appropriate language parsers based on extension."""
    
    # Language to file extension mapping
    LANGUAGE_EXTENSIONS = {
        "python": [".py", ".pyi", ".pyx"],
        "sql": [".sql", ".psql"],
        "yaml": [".yml", ".yaml"],
        "javascript": [".js", ".jsx", ".mjs"],
        "typescript": [".ts", ".tsx"],
    }
    
    # Reverse mapping for quick lookup
    EXTENSION_TO_LANGUAGE = {}
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        for ext in exts:
            EXTENSION_TO_LANGUAGE[ext] = lang
    
    def __init__(self):
        """Initialize parsers for all supported languages."""
        self.parsers = {}
        self.languages = {}
        
        try:
            # Initialize Python parser
            py_language = Language(tree_sitter_python.language())
            py_parser = Parser(py_language)
            self.parsers["python"] = py_parser
            self.languages["python"] = py_language
            logger.info("✅ Python parser initialized")
            
            # Initialize SQL parser
            sql_language = Language(tree_sitter_sql.language())
            sql_parser = Parser(sql_language)
            self.parsers["sql"] = sql_parser
            self.languages["sql"] = sql_language
            logger.info("✅ SQL parser initialized")
            
            # Initialize YAML parser
            yaml_language = Language(tree_sitter_yaml.language())
            yaml_parser = Parser(yaml_language)
            self.parsers["yaml"] = yaml_parser
            self.languages["yaml"] = yaml_language
            logger.info("✅ YAML parser initialized")
            
            # Initialize JavaScript parser
            js_language = Language(tree_sitter_javascript.language())
            js_parser = Parser(js_language)
            self.parsers["javascript"] = js_parser
            self.languages["javascript"] = js_language
            logger.info("✅ JavaScript parser initialized")
            
            # Initialize TypeScript parser
            ts_language = Language(tree_sitter_typescript.language_typescript())
            ts_parser = Parser(ts_language)
            self.parsers["typescript"] = ts_parser
            self.languages["typescript"] = ts_language
            logger.info("✅ TypeScript parser initialized")
            
        except Exception as e:
            logger.error(f"Error initializing parsers: {e}")
    
    def get_language(self, file_path: str) -> Optional[str]:
        """Determine language based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        return self.EXTENSION_TO_LANGUAGE.get(ext)
    
    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a file and extract structural information."""
        language = self.get_language(file_path)
        if not language:
            logger.debug(f"Unsupported language for {file_path}")
            return None
        
        parser = self.parsers.get(language)
        if not parser:
            logger.warning(f"No parser available for {language}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = parser.parse(bytes(code, 'utf8'))
            
            # Extract based on language
            if language == "python":
                return self._extract_python(tree, code, file_path)
            elif language == "sql":
                return self._extract_sql(tree, code, file_path)
            elif language == "yaml":
                return self._extract_yaml(tree, code, file_path)
            elif language in ["javascript", "typescript"]:
                return self._extract_js_ts(tree, code, file_path, language)
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_python(self, tree, code: str, file_path: str) -> Dict[str, Any]:
        """Extract Python-specific information."""
        root = tree.root_node
        
        imports = []
        functions = []
        classes = []
        class_inheritance = {}
        
        # Walk the tree to find imports
        def visit_node(node):
            if node.type == 'import_statement':
                # import x, y
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(code[child.start_byte:child.end_byte])
                    elif child.type == 'aliased_import':
                        for subchild in child.children:
                            if subchild.type == 'dotted_name':
                                imports.append(code[subchild.start_byte:subchild.end_byte])
            
            elif node.type == 'import_from_statement':
                # from x import y
                module_name = None
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = code[child.start_byte:child.end_byte]
                    elif child.type == 'import_list':
                        for imp in child.children:
                            if imp.type == 'dotted_name':
                                imports.append(f"from {module_name} import {code[imp.start_byte:imp.end_byte]}")
                            elif imp.type == 'aliased_import':
                                for subchild in imp.children:
                                    if subchild.type == 'dotted_name':
                                        imports.append(f"from {module_name} import {code[subchild.start_byte:subchild.end_byte]}")
            
            elif node.type == 'function_definition':
                for child in node.children:
                    if child.type == 'identifier':
                        functions.append({
                            'name': code[child.start_byte:child.end_byte],
                            'line_start': node.start_point[0] + 1,
                            'line_end': node.end_point[0] + 1
                        })
            
            elif node.type == 'class_definition':
                class_name = None
                bases = []
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = code[child.start_byte:child.end_byte]
                    elif child.type == 'argument_list':
                        # Extract base classes
                        for base in child.children:
                            if base.type == 'identifier':
                                bases.append(code[base.start_byte:base.end_byte])
                
                if class_name:
                    classes.append({
                        'name': class_name,
                        'line_start': node.start_point[0] + 1,
                        'line_end': node.end_point[0] + 1
                    })
                    if bases:
                        class_inheritance[class_name] = bases
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root)
        
        # DEBUG: Print found imports
        if imports:
            logger.debug(f"Found imports in {file_path}: {imports}")
        
        return {
            "language": "python",
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "class_inheritance": class_inheritance,
            "loc": len(code.splitlines()),
        }
    
    def _extract_sql(self, tree, code: str, file_path: str) -> Dict[str, Any]:
        """Extract SQL-specific information."""
        return {
            "language": "sql",
            "queries": [],
            "tables": [],
            "views": [],
            "loc": len(code.splitlines()),
        }
    
    def _extract_yaml(self, tree, code: str, file_path: str) -> Dict[str, Any]:
        """Extract YAML-specific information."""
        return {
            "language": "yaml",
            "has_config": True,
            "loc": len(code.splitlines()),
        }
    
    def _extract_js_ts(self, tree, code: str, file_path: str, language: str) -> Dict[str, Any]:
        """Extract JavaScript/TypeScript information."""
        return {
            "language": language,
            "imports": [],
            "functions": [],
            "classes": [],
            "loc": len(code.splitlines()),
        }


class ModuleAnalyzer:
    """Analyzes modules using tree-sitter."""
    
    def __init__(self):
        self.router = LanguageRouter()
        self.sql_validator = SQLValidator()
    
    def analyze_module(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a single module/file."""
        return self.router.parse_file(file_path)
    
    def extract_imports(self, file_path: str) -> List[str]:
        """Extract import statements from a file."""
        result = self.analyze_module(file_path)
        if result and "imports" in result:
            return result["imports"]
        return []
    
    def extract_sql_from_python(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract SQL strings from Python files."""
        sql_queries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Look for multi-line strings that contain SQL
            lines = code.split('\n')
            in_sql_string = False
            current_sql = []
            start_line = 0
            
            for i, line in enumerate(lines):
                # Check for triple-quoted strings
                if '"""' in line or "'''" in line:
                    quote_count = line.count('"""') + line.count("'''")
                    
                    if not in_sql_string and quote_count % 2 == 1:
                        # Starting a multi-line string
                        in_sql_string = True
                        start_line = i + 1
                        # Get content after the quotes
                        quote_pos = line.find('"""') if '"""' in line else line.find("'''")
                        current_sql = [line[quote_pos+3:]]
                    elif in_sql_string and quote_count % 2 == 1:
                        # Ending a multi-line string
                        in_sql_string = False
                        # Get content before the quotes
                        quote_pos = line.find('"""') if '"""' in line else line.find("'''")
                        current_sql.append(line[:quote_pos])
                        full_sql = '\n'.join(current_sql)
                        
                        # Validate if it's actually SQL
                        if self.sql_validator.is_likely_sql(full_sql):
                            sql_queries.append({
                                'file': file_path,
                                'line_start': start_line,
                                'line_end': i + 1,
                                'sql': full_sql.strip()
                            })
                        current_sql = []
                elif in_sql_string:
                    current_sql.append(line)
            
        except Exception as e:
            logger.debug(f"Error extracting SQL from {file_path}: {e}")
        
        return sql_queries
