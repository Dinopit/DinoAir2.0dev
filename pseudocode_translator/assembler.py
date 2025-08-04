"""
Code Assembler module for the Pseudocode Translator

This module handles the intelligent assembly of code blocks into cohesive
Python scripts, including import organization, function merging, and
consistency checks.
"""

import ast
import re
import logging
from typing import List, Dict, Set
from collections import defaultdict, OrderedDict

from .models import CodeBlock, BlockType
from .config import TranslatorConfig
from .ast_cache import parse_cached
from .exceptions import AssemblyError, ErrorContext


logger = logging.getLogger(__name__)


class CodeAssembler:
    """
    Intelligently combines code segments into complete Python scripts
    """
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize the Code Assembler
        
        Args:
            config: Translator configuration object
        """
        self.config = config
        self.indent_size = config.indent_size
        self.max_line_length = config.max_line_length
        self.preserve_comments = config.preserve_comments
        self.preserve_docstrings = config.preserve_docstrings
        self.auto_import_common = config.auto_import_common
        
        # Common imports that might be auto-added
        self.common_imports = {
            'math': ['sin', 'cos', 'sqrt', 'pi', 'tan', 'log', 'exp'],
            'os': ['path', 'getcwd', 'listdir', 'mkdir', 'remove'],
            'sys': ['argv', 'exit', 'path', 'platform'],
            'datetime': ['datetime', 'date', 'time', 'timedelta'],
            'json': ['dumps', 'loads', 'dump', 'load'],
            're': ['match', 'search', 'findall', 'sub', 'compile'],
            'typing': ['List', 'Dict', 'Tuple', 'Optional', 'Union', 'Any'],
        }
    
    def assemble(self, blocks: List[CodeBlock]) -> str:
        """
        Combines segments while handling:
        - Import deduplication
        - Variable scope resolution
        - Function organization
        - Proper indentation
        
        Args:
            blocks: List of processed code blocks
            
        Returns:
            Complete assembled Python code
        """
        if not blocks:
            return ""
        
        logger.info(f"Assembling {len(blocks)} code blocks")
        
        try:
            # Filter out non-Python blocks
            python_blocks = [b for b in blocks if b.type == BlockType.PYTHON]
            # comment_blocks for future use
            # comment_blocks for future use
            # comment_blocks = [
            #     b for b in blocks if b.type == BlockType.COMMENT
            # ]
            
            if not python_blocks:
                logger.warning("No Python blocks to assemble")
                error = AssemblyError(
                    "No Python code blocks found to assemble",
                    blocks_info=[{
                        'type': b.type.value,
                        'lines': b.line_numbers
                    } for b in blocks],
                    assembly_stage="filtering"
                )
                error.add_suggestion(
                    "Ensure pseudocode was translated to Python"
                )
                error.add_suggestion(
                    "Check that block types are correctly identified"
                )
                logger.warning(error.format_error())
                return ""
        except Exception as e:
            error = AssemblyError(
                "Failed to filter code blocks",
                assembly_stage="filtering",
                cause=e
            )
            raise error
        
        # Step 1: Organize imports
        try:
            imports_section = self._organize_imports(python_blocks)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize imports",
                assembly_stage="imports",
                cause=e
            )
            error.add_suggestion("Check import statement syntax")
            error.add_suggestion("Verify module names are valid")
            raise error
        
        # Step 2: Extract and organize top-level code
        try:
            main_code_sections = self._organize_code_sections(python_blocks)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize code sections",
                assembly_stage="sections",
                cause=e
            )
            error.add_suggestion("Check code block structure")
            error.add_suggestion("Ensure valid Python syntax in all blocks")
            raise error
        
        # Step 3: Merge functions and classes
        try:
            merged_functions = self._merge_functions(
                main_code_sections['functions']
            )
            merged_classes = self._merge_classes(
                main_code_sections['classes']
            )
        except Exception as e:
            error = AssemblyError(
                "Failed to merge functions and classes",
                assembly_stage="merging",
                cause=e
            )
            error.add_suggestion("Check for naming conflicts")
            error.add_suggestion("Ensure function/class definitions are valid")
            raise error
        
        # Step 4: Organize global variables and constants
        try:
            globals_section = self._organize_globals(
                main_code_sections['globals']
            )
        except Exception as e:
            error = AssemblyError(
                "Failed to organize global variables",
                assembly_stage="globals",
                cause=e
            )
            raise error
        
        # Step 5: Organize main execution code
        try:
            main_section = self._organize_main_code(main_code_sections['main'])
        except Exception as e:
            error = AssemblyError(
                "Failed to organize main execution code",
                assembly_stage="main",
                cause=e
            )
            raise error
        
        # Step 6: Preserve comments if configured (future enhancement)
        # if self.preserve_comments and comment_blocks:
        #     comments_section = self._organize_comments(comment_blocks)
        
        # Step 7: Assemble final code
        final_sections = []
        
        # Add module docstring if present
        if main_code_sections.get('module_docstring'):
            final_sections.append(main_code_sections['module_docstring'])
        
        # Add imports
        if imports_section:
            final_sections.append(imports_section)
        
        # Add globals and constants
        if globals_section:
            final_sections.append(globals_section)
        
        # Add functions
        if merged_functions:
            final_sections.append(merged_functions)
        
        # Add classes
        if merged_classes:
            final_sections.append(merged_classes)
        
        # Add main execution code
        if main_section:
            final_sections.append(main_section)
        
        # Join sections with appropriate spacing
        assembled_code = '\n\n\n'.join(final_sections)
        
        # Step 8: Ensure consistency
        try:
            final_code = self._ensure_consistency(assembled_code)
        except Exception as e:
            error = AssemblyError(
                "Failed to ensure code consistency",
                assembly_stage="consistency",
                cause=e
            )
            error.add_suggestion("Check indentation throughout the code")
            error.add_suggestion("Verify consistent coding style")
            raise error
        
        # Step 9: Final validation and cleanup
        try:
            final_code = self._final_cleanup(final_code)
        except Exception as e:
            error = AssemblyError(
                "Failed during final cleanup",
                assembly_stage="cleanup",
                cause=e
            )
            raise error
        
        logger.info("Code assembly complete")
        return final_code
    
    def assemble_streaming(self, block_iterator):
        """
        Assemble code from a streaming iterator of blocks
        
        Args:
            block_iterator: Iterator yielding CodeBlock objects
            
        Returns:
            Complete assembled Python code
        """
        # Collect blocks from iterator
        blocks = list(block_iterator)
        
        # Use regular assemble method
        return self.assemble(blocks)
    
    def assemble_incremental(
        self, previous_code: str,
        new_blocks: List[CodeBlock]
    ) -> str:
        """
        Incrementally assemble code by adding new blocks to existing code
        
        Args:
            previous_code: Previously assembled code
            new_blocks: New blocks to add
            
        Returns:
            Updated assembled code
        """
        if not new_blocks:
            return previous_code
        
        if not previous_code:
            return self.assemble(new_blocks)
        
        # Parse the previous code to extract structure
        try:
            tree = parse_cached(previous_code)
            
            # Extract existing imports and definitions
            existing_imports = set()
            existing_functions = set()
            existing_classes = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        existing_imports.add(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        existing_imports.add(
                            f"from {module} import {alias.name}"
                        )
                elif isinstance(node, ast.FunctionDef):
                    existing_functions.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    existing_classes.add(node.name)
        except SyntaxError:
            # If we can't parse previous code, just append new blocks
            new_code = self.assemble(new_blocks)
            return f"{previous_code}\n\n{new_code}"
        
        # Process new blocks
        python_blocks = [b for b in new_blocks if b.type == BlockType.PYTHON]
        
        # Organize new imports
        new_imports = self._organize_imports(python_blocks)
        
        # Filter out already existing imports
        import_lines = new_imports.splitlines()
        unique_imports = []
        for line in import_lines:
            if line.strip() and line.strip() not in existing_imports:
                unique_imports.append(line)
        
        # Assemble new non-import code
        new_code_sections = self._organize_code_sections(python_blocks)
        
        # Filter out duplicate functions/classes
        filtered_functions = []
        for func_code in new_code_sections['functions']:
            try:
                func_tree = parse_cached(func_code)
                if (func_tree.body and
                        isinstance(func_tree.body[0], ast.FunctionDef)):
                    func_name = func_tree.body[0].name
                    if func_name not in existing_functions:
                        filtered_functions.append(func_code)
            except Exception:
                filtered_functions.append(func_code)
        
        filtered_classes = []
        for class_code in new_code_sections['classes']:
            try:
                class_tree = parse_cached(class_code)
                if (class_tree.body and
                        isinstance(class_tree.body[0], ast.ClassDef)):
                    class_name = class_tree.body[0].name
                    if class_name not in existing_classes:
                        filtered_classes.append(class_code)
            except Exception:
                filtered_classes.append(class_code)
        
        # Build incremental code
        incremental_parts = []
        
        if unique_imports:
            incremental_parts.append('\n'.join(unique_imports))
        
        if filtered_functions:
            incremental_parts.append('\n\n'.join(filtered_functions))
        
        if filtered_classes:
            incremental_parts.append('\n\n'.join(filtered_classes))
        
        if new_code_sections['main']:
            incremental_parts.append('\n\n'.join(new_code_sections['main']))
        
        if not incremental_parts:
            return previous_code
        
        # Combine with previous code
        incremental_code = '\n\n'.join(incremental_parts)
        return f"{previous_code}\n\n{incremental_code}"
    
    def _organize_imports(self, blocks: List[CodeBlock]) -> str:
        """
        Organize and deduplicate imports from all blocks
        
        Args:
            blocks: List of Python code blocks
            
        Returns:
            Organized import section
        """
        imports = {
            'standard': set(),  # Standard library imports
            'third_party': set(),  # Third-party imports
            'local': set(),  # Local imports
        }
        
        from_imports = {
            'standard': defaultdict(set),
            'third_party': defaultdict(set),
            'local': defaultdict(set),
        }
        
        # Extract imports from each block
        for block in blocks:
            try:
                tree = parse_cached(block.content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_name = alias.name
                            category = self._categorize_import(import_name)
                            imports[category].add(import_name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        category = self._categorize_import(module)
                        
                        for alias in node.names:
                            from_imports[category][module].add(alias.name)
                            
            except SyntaxError as e:
                logger.warning(
                    f"Could not parse block for imports: {block.line_numbers}"
                )
                # Create context for error
                context = ErrorContext(
                    line_number=block.line_numbers[0],
                    code_snippet=block.content[:100],
                    metadata={'error': str(e)}
                )
                
                error = AssemblyError(
                    "Invalid syntax in code block",
                    assembly_stage="imports",
                    context=context
                )
                error.add_suggestion("Fix syntax errors before assembly")
                # Continue with other blocks instead of failing
                logger.warning(error.format_error())
        
        # Auto-add common imports if configured
        if self.auto_import_common:
            self._add_common_imports(blocks, imports, from_imports)
        
        # Build import section
        import_lines = []
        
        # Standard library imports
        if imports['standard'] or from_imports['standard']:
            if imports['standard']:
                for imp in sorted(imports['standard']):
                    import_lines.append(f"import {imp}")
            
            if from_imports['standard']:
                for module, names in sorted(from_imports['standard'].items()):
                    if names:
                        names_str = ', '.join(sorted(names))
                        import_lines.append(
                            f"from {module} import {names_str}"
                        )
            
            import_lines.append("")  # Blank line after standard imports
        
        # Third-party imports
        if imports['third_party'] or from_imports['third_party']:
            if imports['third_party']:
                for imp in sorted(imports['third_party']):
                    import_lines.append(f"import {imp}")
            
            if from_imports['third_party']:
                for module, names in sorted(
                        from_imports['third_party'].items()
                ):
                    if names:
                        names_str = ', '.join(sorted(names))
                        import_lines.append(
                            f"from {module} import {names_str}"
                        )
            
            import_lines.append("")  # Blank line after third-party imports
        
        # Local imports
        if imports['local'] or from_imports['local']:
            if imports['local']:
                for imp in sorted(imports['local']):
                    import_lines.append(f"import {imp}")
            
            if from_imports['local']:
                for module, names in sorted(from_imports['local'].items()):
                    if names:
                        names_str = ', '.join(sorted(names))
                        import_lines.append(
                            f"from {module} import {names_str}"
                        )
        
        # Remove trailing empty lines
        while import_lines and import_lines[-1] == "":
            import_lines.pop()
        
        return '\n'.join(import_lines)
    
    def _organize_code_sections(
        self, blocks: List[CodeBlock]
    ) -> Dict[str, List[str]]:
        """
        Organize code into sections (functions, classes, globals, main)
        
        Args:
            blocks: List of Python code blocks
            
        Returns:
            Dictionary with categorized code sections
        """
        sections = {
            'module_docstring': None,
            'functions': [],
            'classes': [],
            'globals': [],
            'main': [],
        }
        
        for block in blocks:
            try:
                tree = parse_cached(block.content)
                
                # Check for module docstring
                if (isinstance(tree.body[0], ast.Expr) and
                        isinstance(tree.body[0].value, ast.Str) and
                        sections['module_docstring'] is None):
                    sections['module_docstring'] = ast.get_docstring(
                        tree, clean=True
                    )
                
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        # Extract function definition
                        func_code = ast.get_source_segment(block.content, node)
                        if func_code:
                            sections['functions'].append(func_code)
                    
                    elif isinstance(node, ast.ClassDef):
                        # Extract class definition
                        class_code = ast.get_source_segment(
                            block.content, node
                        )
                        if class_code:
                            sections['classes'].append(class_code)
                    
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                        # Global variables/constants
                        var_code = ast.get_source_segment(block.content, node)
                        if (var_code and
                                self._is_top_level_assignment(node, tree)):
                            sections['globals'].append(var_code)
                    
                    elif not isinstance(node, (ast.Import, ast.ImportFrom)):
                        # Other top-level code (main execution)
                        main_code = ast.get_source_segment(
                            block.content, node
                        )
                        if main_code:
                            sections['main'].append(main_code)
                            
            except SyntaxError:
                # If we can't parse, treat entire block as main code
                logger.warning(
                    f"Could not parse block: {block.line_numbers}"
                )
                # Create warning with context
                context = ErrorContext(
                    line_number=block.line_numbers[0],
                    code_snippet=block.content[:100],
                    metadata={'fallback': 'treating as main code'}
                )
                
                error = AssemblyError(
                    "Could not parse code block structure",
                    assembly_stage="sections",
                    context=context
                )
                error.add_suggestion("Check syntax in this block")
                error.add_suggestion("Ensure proper Python formatting")
                logger.warning(error.format_error())
                
                sections['main'].append(block.content)
        
        return sections
    
    def _merge_functions(self, functions: List[str]) -> str:
        """
        Merge function definitions, handling duplicates
        
        Args:
            functions: List of function code strings
            
        Returns:
            Merged functions section
        """
        if not functions:
            return ""
        
        # Use OrderedDict to maintain order and handle duplicates
        unique_functions = OrderedDict()
        
        for func_code in functions:
            try:
                # Parse function to get its name
                tree = parse_cached(func_code)
                if tree.body and isinstance(tree.body[0], ast.FunctionDef):
                    func_name = tree.body[0].name
                    
                    # If duplicate, keep the later definition
                    # (assumed to be more complete)
                    unique_functions[func_name] = func_code
                else:
                    # If we can't parse, use the code as-is with a unique key
                    unique_key = f"func_{len(unique_functions)}"
                    unique_functions[unique_key] = func_code
                    
            except SyntaxError as e:
                # If parsing fails, include anyway
                logger.warning(f"Could not parse function: {str(e)}")
                unique_functions[f"func_{len(unique_functions)}"] = func_code
        
        return '\n\n'.join(unique_functions.values())
    
    def _merge_classes(self, classes: List[str]) -> str:
        """
        Merge class definitions, handling duplicates
        
        Args:
            classes: List of class code strings
            
        Returns:
            Merged classes section
        """
        if not classes:
            return ""
        
        unique_classes = OrderedDict()
        
        for class_code in classes:
            try:
                tree = parse_cached(class_code)
                if tree.body and isinstance(tree.body[0], ast.ClassDef):
                    class_name = tree.body[0].name
                    unique_classes[class_name] = class_code
                else:
                    unique_classes[f"class_{len(unique_classes)}"] = class_code
                    
            except SyntaxError as e:
                logger.warning(f"Could not parse class: {str(e)}")
                unique_classes[f"class_{len(unique_classes)}"] = class_code
        
        return '\n\n'.join(unique_classes.values())
    
    def _organize_globals(self, globals_list: List[str]) -> str:
        """
        Organize global variables and constants
        
        Args:
            globals_list: List of global assignment strings
            
        Returns:
            Organized globals section
        """
        if not globals_list:
            return ""
        
        # Separate constants (UPPER_CASE) from variables
        constants = []
        variables = []
        
        for global_code in globals_list:
            # Simple heuristic: if variable name is uppercase, it's a constant
            if re.search(r'^[A-Z_]+\s*=', global_code.strip()):
                constants.append(global_code.strip())
            else:
                variables.append(global_code.strip())
        
        # Build section with constants first
        globals_section = []
        
        if constants:
            globals_section.append("# Constants")
            globals_section.extend(constants)
            
        if variables:
            if constants:
                globals_section.append("")  # Blank line
            globals_section.append("# Global variables")
            globals_section.extend(variables)
        
        return '\n'.join(globals_section)
    
    def _organize_main_code(self, main_sections: List[str]) -> str:
        """
        Organize main execution code
        
        Args:
            main_sections: List of main code sections
            
        Returns:
            Organized main code section
        """
        if not main_sections:
            return ""
        
        # Check if we should wrap in if __name__ == "__main__":
        needs_main_guard = any(
            'print(' in code or 
            'input(' in code or
            re.search(r'\b(main|run|execute)\s*\(', code)
            for code in main_sections
        )
        
        main_code = '\n\n'.join(main_sections)
        
        if needs_main_guard:
            # Indent the main code
            indented_code = '\n'.join(
                f"{' ' * self.indent_size}{line}" if line.strip() else line
                for line in main_code.splitlines()
            )
            return f'if __name__ == "__main__":\n{indented_code}'
        
        return main_code
    
    def _ensure_consistency(self, code: str) -> str:
        """
        Ensure consistency in the assembled code
        
        Args:
            code: Assembled code
            
        Returns:
            Code with ensured consistency
        """
        # Fix indentation
        code = self._fix_indentation(code)
        
        # Ensure consistent line endings
        code = code.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines
        code = re.sub(r'\n{4,}', '\n\n\n', code)
        
        # Ensure newline at end of file
        if code and not code.endswith('\n'):
            code += '\n'
        
        return code
    
    def _fix_indentation(self, code: str) -> str:
        """
        Fix and standardize indentation in the code
        
        Args:
            code: Code with potential indentation issues
            
        Returns:
            Code with fixed indentation
        """
        try:
            lines = code.splitlines()
            fixed_lines = []
            
            # Detect current indentation style
            indent_char = ' '
            for line in lines:
                if line.startswith('\t'):
                    indent_char = '\t'
                    break
            
            # Convert all indentation to spaces if configured
            if self.config.indent_size and indent_char == '\t':
                lines = [
                    line.replace('\t', ' ' * self.indent_size)
                    for line in lines
                ]
            
            # Fix indentation levels
            indent_stack = [0]
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                if not stripped:
                    fixed_lines.append('')
                    continue
                
                # Calculate current indentation
                current_indent = len(line) - len(line.lstrip())
                
                # Check for dedent keywords
                dedent_keywords = (
                    'else:', 'elif ', 'except:', 'except ',
                    'finally:', 'case '
                )
                if stripped.startswith(dedent_keywords):
                    # These should be at the same level as their
                    # matching statement
                    if len(indent_stack) > 1:
                        indent_stack.pop()
                        current_indent = indent_stack[-1]
                
                # Check for block start
                if stripped.endswith(':') and not stripped.startswith('#'):
                    fixed_lines.append(' ' * current_indent + stripped)
                    indent_stack.append(current_indent + self.indent_size)
                else:
                    # Adjust indentation based on context
                    if (current_indent < indent_stack[-1] and
                            len(indent_stack) > 1):
                        # Dedent detected
                        while (len(indent_stack) > 1 and
                               current_indent < indent_stack[-1]):
                            indent_stack.pop()
                        current_indent = indent_stack[-1]
                    
                    fixed_lines.append(' ' * current_indent + stripped)
            
            return '\n'.join(fixed_lines)
            
        except Exception as e:
            error = AssemblyError(
                "Failed to fix indentation",
                assembly_stage="indentation",
                cause=e
            )
            error.add_suggestion("Check for severe indentation errors")
            error.add_suggestion("Ensure consistent use of spaces or tabs")
            raise error
    
    def _categorize_import(self, module_name: str) -> str:
        """
        Categorize an import as standard, third-party, or local
        
        Args:
            module_name: Name of the module
            
        Returns:
            Category: 'standard', 'third_party', or 'local'
        """
        # Standard library modules (Python 3.8+)
        standard_lib = {
            'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat',
            'asyncio', 'asyncore', 'atexit', 'audioop', 'base64',
            'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2',
            'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd',
            'code', 'codecs', 'codeop', 'collections', 'colorsys',
            'compileall', 'concurrent', 'configparser', 'contextlib',
            'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt',
            'csv', 'ctypes', 'curses', 'dataclasses', 'datetime',
            'dbm', 'decimal', 'difflib', 'dis', 'distutils', 'doctest',
            'email', 'encodings', 'ensurepip', 'enum', 'errno',
            'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
            'formatter', 'fractions', 'ftplib', 'functools', 'gc',
            'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip',
            'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib',
            'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress',
            'itertools', 'json', 'keyword', 'lib2to3', 'linecache',
            'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
            'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
            'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis',
            'nntplib', 'numbers', 'operator', 'optparse', 'os',
            'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle',
            'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib',
            'poplib', 'posix', 'posixpath', 'pprint', 'profile',
            'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc',
            'queue', 'quopri', 'random', 're', 'readline', 'reprlib',
            'resource', 'rlcompleter', 'runpy', 'sched', 'secrets',
            'select', 'selectors', 'shelve', 'shlex', 'shutil',
            'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket',
            'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat',
            'statistics', 'string', 'stringprep', 'struct',
            'subprocess', 'sunau', 'symbol', 'symtable', 'sys',
            'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib',
            'tempfile', 'termios', 'test', 'textwrap', 'threading',
            'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace',
            'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo',
            'types', 'typing', 'unicodedata', 'unittest', 'urllib',
            'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref',
            'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
            'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport',
            'zlib', 'zoneinfo'
        }
        
        # Get top-level module name
        top_level = module_name.split('.')[0]
        
        if top_level in standard_lib:
            return 'standard'
        elif module_name.startswith('.') or not module_name:
            return 'local'
        else:
            return 'third_party'
    
    def _is_top_level_assignment(
        self, node: ast.stmt, tree: ast.AST
    ) -> bool:
        """
        Check if an assignment is at the top level
        (not inside a function/class)
        
        Args:
            node: AST node to check
            tree: Full AST tree for context
            
        Returns:
            True if top-level assignment
        """
        # Check if the node is directly in the module body
        if hasattr(tree, 'body') and node in tree.body:
            return True
            
        # Walk the tree to find the node's parent
        for parent_node in ast.walk(tree):
            # Check if node is inside a function or class
            if isinstance(parent_node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef)):
                # Check if our node is within this function/class
                for child in ast.walk(parent_node):
                    if child is node:
                        return False
                        
        # If we get here, it's likely top-level
        return True
    
    def _add_common_imports(
        self, blocks: List[CodeBlock],
        imports: Dict[str, Set[str]],
        from_imports: Dict[str, Dict[str, Set[str]]]
    ):
        """
        Auto-add common imports based on code usage
        
        Args:
            blocks: List of code blocks
            imports: Current imports dictionary
            from_imports: Current from-imports dictionary
        """
        # Combine all code for analysis
        all_code = '\n'.join(block.content for block in blocks)
        
        for module, common_names in self.common_imports.items():
            for name in common_names:
                # Check if the name is used in the code
                pattern = rf'\b{name}\s*\('
                if re.search(pattern, all_code):
                    # Check if already imported
                    already_imported = (
                        module in imports['standard'] or
                        name in from_imports['standard'].get(module, set())
                    )
                    
                    if not already_imported:
                        # Add the import
                        if module not in from_imports['standard']:
                            from_imports['standard'][module] = set()
                        from_imports['standard'][module].add(name)
                        logger.debug(
                            f"Auto-adding import: from {module} "
                            f"import {name}"
                        )
    
    def _organize_comments(self, comment_blocks: List[CodeBlock]) -> str:
        """
        Organize comment blocks
        
        Args:
            comment_blocks: List of comment blocks
            
        Returns:
            Organized comments section
        """
        comments = []
        
        for block in comment_blocks:
            content = block.content.strip()
            if content:
                comments.append(content)
        
        return '\n'.join(comments)
    
    def _final_cleanup(self, code: str) -> str:
        """
        Perform final cleanup on the assembled code
        
        Args:
            code: Assembled code
            
        Returns:
            Cleaned up code
        """
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in code.splitlines()]
        
        # Ensure proper spacing around top-level definitions
        cleaned_lines = []
        prev_was_definition = False
        
        for i, line in enumerate(lines):
            # Check if this is a top-level definition
            is_definition = (
                line.startswith('def ') or 
                line.startswith('class ') or
                (i > 0 and not lines[i-1].strip() and
                 line and not line[0].isspace())
            )
            
            # Add spacing before definitions (except the first)
            if is_definition and prev_was_definition and cleaned_lines:
                # Ensure two blank lines before definition
                while (len(cleaned_lines) >= 2 and
                       not cleaned_lines[-1] and not cleaned_lines[-2]):
                    cleaned_lines.pop()
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append('')
                if len(cleaned_lines) < 2 or cleaned_lines[-2]:
                    cleaned_lines.append('')
            
            cleaned_lines.append(line)
            prev_was_definition = is_definition and line.strip()
        
        # Join and ensure single newline at end
        final_code = '\n'.join(cleaned_lines)
        if final_code and not final_code.endswith('\n'):
            final_code += '\n'
        
        return final_code