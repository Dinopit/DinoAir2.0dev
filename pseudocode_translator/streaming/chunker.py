"""
Smart code chunking module for streaming support

This module provides intelligent code chunking that respects code boundaries,
ensuring that functions, classes, and other code structures are not split
in the middle during streaming processing.
"""

import ast
from typing import List, Iterator, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for code chunking"""
    max_chunk_size: int = 4096  # Maximum size in bytes
    min_chunk_size: int = 512   # Minimum size in bytes
    overlap_size: int = 256     # Overlap between chunks for context
    respect_boundaries: bool = True  # Respect code boundaries
    max_lines_per_chunk: int = 100  # Maximum lines per chunk
    preserve_indentation: bool = True
    chunk_by_blocks: bool = True  # Chunk by logical blocks


@dataclass
class CodeChunk:
    """Represents a single chunk of code"""
    content: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    chunk_index: int
    total_chunks: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    
    @property
    def size(self) -> int:
        """Get chunk size in bytes"""
        return len(self.content.encode('utf-8'))
    
    @property
    def line_count(self) -> int:
        """Get number of lines in chunk"""
        return self.content.count('\n') + 1


class CodeChunker:
    """
    Intelligent code chunker that splits code while respecting boundaries
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize the code chunker
        
        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkConfig()
        self._ast_cache = {}
        
    def chunk_code(self, code: str,
                   filename: Optional[str] = None) -> List[CodeChunk]:
        """
        Split code into chunks while respecting boundaries
        
        Args:
            code: Source code to chunk
            filename: Optional filename for better error reporting
            
        Returns:
            List of code chunks
        """
        if not code:
            return []
        
        # For small code, return as single chunk
        if len(code.encode('utf-8')) <= self.config.max_chunk_size:
            return [CodeChunk(
                content=code,
                start_line=1,
                end_line=code.count('\n') + 1,
                start_byte=0,
                end_byte=len(code.encode('utf-8')),
                chunk_index=0,
                total_chunks=1,
                metadata={'single_chunk': True}
            )]
        
        # Try AST-based chunking first if enabled
        if self.config.respect_boundaries and self.config.chunk_by_blocks:
            try:
                return self._chunk_by_ast(code, filename)
            except SyntaxError as e:
                logger.warning(
                    f"AST parsing failed, falling back to line-based "
                    f"chunking: {e}"
                )
        
        # Fall back to line-based chunking
        return self._chunk_by_lines(code)
    
    def stream_chunks(self, code: str,
                      filename: Optional[str] = None) -> Iterator[CodeChunk]:
        """
        Stream code chunks as they are generated
        
        Args:
            code: Source code to chunk
            filename: Optional filename for better error reporting
            
        Yields:
            Code chunks
        """
        chunks = self.chunk_code(code, filename)
        total_chunks = len(chunks)
        
        for chunk in chunks:
            chunk.total_chunks = total_chunks
            yield chunk
    
    def _chunk_by_ast(self, code: str,
                      filename: Optional[str] = None) -> List[CodeChunk]:
        """
        Chunk code using AST analysis to find safe split points
        
        Args:
            code: Source code to chunk
            filename: Optional filename
            
        Returns:
            List of code chunks
        """
        # Parse the code
        tree = ast.parse(code, filename or '<string>')
        lines = code.splitlines(keepends=True)
        
        # Find all top-level nodes
        boundaries = self._find_ast_boundaries(tree, lines)
        
        # Group nodes into chunks
        chunks = []
        current_chunk_nodes = []
        current_size = 0
        
        for boundary in boundaries:
            node_size = boundary['size']
            
            # Check if adding this node would exceed max chunk size
            if (current_size + node_size > self.config.max_chunk_size and 
                current_chunk_nodes and 
                    current_size >= self.config.min_chunk_size):
                
                # Create chunk from current nodes
                chunk = self._create_chunk_from_boundaries(
                    current_chunk_nodes, lines, len(chunks)
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk_nodes = [boundary]
                current_size = node_size
            else:
                # Add to current chunk
                current_chunk_nodes.append(boundary)
                current_size += node_size
        
        # Don't forget the last chunk
        if current_chunk_nodes:
            chunk = self._create_chunk_from_boundaries(
                current_chunk_nodes, lines, len(chunks)
            )
            chunks.append(chunk)
        
        # Add overlap between chunks if configured
        if self.config.overlap_size > 0:
            chunks = self._add_overlap(chunks, lines)
        
        return chunks
    
    def _find_ast_boundaries(self, tree: ast.AST,
                             lines: List[str]) -> List[Dict[str, Any]]:
        """
        Find safe boundaries for splitting based on AST nodes
        
        Args:
            tree: AST tree
            lines: Source code lines
            
        Returns:
            List of boundary information
        """
        boundaries = []
        
        if hasattr(tree, 'body'):
            body = getattr(tree, 'body', [])
        else:
            return boundaries
            
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, 
                                   ast.ClassDef, ast.Import, ast.ImportFrom)):
                # These are safe to split between
                start_line = node.lineno - 1
                end_line = node.end_lineno or node.lineno
                
                # Include decorators if present
                if hasattr(node, 'decorator_list'):
                    decorators = getattr(node, 'decorator_list', [])
                    for decorator in decorators:
                        start_line = min(start_line, decorator.lineno - 1)
                
                # Include any preceding comments or docstrings
                start_line = self._find_block_start(lines, start_line)
                
                # Calculate size
                block_lines = lines[start_line:end_line]
                size = sum(len(line.encode('utf-8')) for line in block_lines)
                
                boundaries.append({
                    'type': type(node).__name__,
                    'name': getattr(node, 'name', None),
                    'start_line': start_line,
                    'end_line': end_line,
                    'size': size,
                    'node': node
                })
            
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Str)):
                # Module-level docstring
                boundaries.append({
                    'type': 'ModuleDocstring',
                    'name': None,
                    'start_line': node.lineno - 1,
                    'end_line': node.end_lineno or node.lineno,
                    'size': self._get_node_size(''.join(lines), node),
                    'node': node
                })
            
            else:
                # Other top-level code
                boundaries.append({
                    'type': 'TopLevelCode',
                    'name': None,
                    'start_line': node.lineno - 1,
                    'end_line': node.end_lineno or node.lineno,
                    'size': self._get_node_size(''.join(lines), node),
                    'node': node
                })
        
        return boundaries
    
    def _find_block_start(self, lines: List[str], start_line: int) -> int:
        """
        Find the actual start of a code block including comments
        
        Args:
            lines: Source code lines
            start_line: Initial start line
            
        Returns:
            Adjusted start line
        """
        # Look backwards for comments or blank lines that belong to this block
        current_line = start_line - 1
        
        while current_line >= 0:
            line = lines[current_line].strip()
            
            # Stop if we hit code
            if line and not line.startswith('#'):
                break
            
            # This is a comment or blank line, include it
            if line.startswith('#') or not line:
                start_line = current_line
            
            current_line -= 1
        
        return start_line
    
    def _create_chunk_from_boundaries(self,
                                      boundaries: List[Dict[str, Any]],
                                      lines: List[str],
                                      chunk_index: int) -> CodeChunk:
        """
        Create a code chunk from boundary information
        
        Args:
            boundaries: List of boundary info
            lines: Source code lines
            chunk_index: Index of this chunk
            
        Returns:
            CodeChunk object
        """
        start_line = boundaries[0]['start_line']
        end_line = boundaries[-1]['end_line']
        
        # Extract content
        chunk_lines = lines[start_line:end_line]
        content = ''.join(chunk_lines)
        
        # Calculate byte positions
        start_byte = sum(
            len(line.encode('utf-8')) for line in lines[:start_line]
        )
        end_byte = start_byte + len(content.encode('utf-8'))
        
        # Build metadata
        metadata = {
            'boundary_types': [b['type'] for b in boundaries],
            'contains': [b['name'] for b in boundaries if b['name']],
            'ast_based': True
        }
        
        return CodeChunk(
            content=content,
            start_line=start_line + 1,  # Convert to 1-based
            end_line=end_line,
            start_byte=start_byte,
            end_byte=end_byte,
            chunk_index=chunk_index,
            metadata=metadata
        )
    
    def _chunk_by_lines(self, code: str) -> List[CodeChunk]:
        """
        Fall back to simple line-based chunking
        
        Args:
            code: Source code to chunk
            
        Returns:
            List of code chunks
        """
        lines = code.splitlines(keepends=True)
        chunks = []
        current_chunk_lines = []
        current_size = 0
        chunk_start_line = 0
        chunk_start_byte = 0
        
        for i, line in enumerate(lines):
            line_size = len(line.encode('utf-8'))
            
            # Check if adding this line would exceed limits
            if (current_size + line_size > self.config.max_chunk_size or
                len(current_chunk_lines) >=
                self.config.max_lines_per_chunk) and \
               current_chunk_lines and \
               current_size >= self.config.min_chunk_size:
                
                # Try to find a good split point
                if self.config.respect_boundaries:
                    split_point = self._find_line_split_point(
                        current_chunk_lines
                    )
                    if split_point < len(current_chunk_lines) - 1:
                        # Split at the found point
                        chunk_content = ''.join(
                            current_chunk_lines[:split_point + 1]
                        )
                        remaining_lines = current_chunk_lines[split_point + 1:]
                        
                        chunks.append(CodeChunk(
                            content=chunk_content,
                            start_line=chunk_start_line + 1,
                            end_line=chunk_start_line + split_point + 1,
                            start_byte=chunk_start_byte,
                            end_byte=chunk_start_byte +
                                   len(chunk_content.encode('utf-8')),
                            chunk_index=len(chunks),
                            metadata={'line_based': True}
                        ))
                        
                        # Start new chunk with remaining lines
                        chunk_start_line += split_point + 1
                        chunk_start_byte += len(chunk_content.encode('utf-8'))
                        current_chunk_lines = remaining_lines + [line]
                        current_size = sum(
                            len(line.encode('utf-8'))
                            for line in current_chunk_lines
                        )
                        continue
                
                # No good split point found, create chunk as is
                chunk_content = ''.join(current_chunk_lines)
                chunks.append(CodeChunk(
                    content=chunk_content,
                    start_line=chunk_start_line + 1,
                    end_line=chunk_start_line + len(current_chunk_lines),
                    start_byte=chunk_start_byte,
                    end_byte=chunk_start_byte +
                             len(chunk_content.encode('utf-8')),
                    chunk_index=len(chunks),
                    metadata={'line_based': True}
                ))
                
                # Start new chunk
                chunk_start_line = i
                chunk_start_byte += len(chunk_content.encode('utf-8'))
                current_chunk_lines = [line]
                current_size = line_size
            else:
                # Add line to current chunk
                current_chunk_lines.append(line)
                current_size += line_size
        
        # Don't forget the last chunk
        if current_chunk_lines:
            chunk_content = ''.join(current_chunk_lines)
            chunks.append(CodeChunk(
                content=chunk_content,
                start_line=chunk_start_line + 1,
                end_line=chunk_start_line + len(current_chunk_lines),
                start_byte=chunk_start_byte,
                end_byte=chunk_start_byte + len(chunk_content.encode('utf-8')),
                chunk_index=len(chunks),
                metadata={'line_based': True}
            ))
        
        return chunks
    
    def _find_line_split_point(self, lines: List[str]) -> int:
        """
        Find a good split point in a list of lines
        
        Args:
            lines: List of code lines
            
        Returns:
            Index of the best split point
        """
        # Look for natural boundaries from the end
        for i in range(len(lines) - 1, max(len(lines) // 2, 0), -1):
            line = lines[i].strip()
            
            # Good split points:
            # - Empty lines
            # - Lines that complete a block (dedented)
            # - Import statements
            # - Function/class definitions
            if (not line or
                (i > 0 and
                 self._get_indent_level(lines[i]) <
                 self._get_indent_level(lines[i-1])) or
                    line.startswith(('import ', 'from ', 'def ', 'class '))):
                return i
        
        # No good split point found
        return len(lines) - 1
    
    def _get_indent_level(self, line: str) -> int:
        """Get indentation level of a line"""
        return len(line) - len(line.lstrip())
    
    def _add_overlap(self, chunks: List[CodeChunk],
                     lines: List[str]) -> List[CodeChunk]:
        """
        Add overlap between chunks for better context
        
        Args:
            chunks: List of chunks
            lines: Original source lines
            
        Returns:
            Chunks with overlap added
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            new_content = chunk.content
            new_start_line = chunk.start_line
            new_start_byte = chunk.start_byte
            
            # Add overlap from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap_lines = (
                    prev_chunk.content.splitlines(keepends=True)
                    [-self.config.overlap_size:]
                )
                if overlap_lines:
                    new_content = ''.join(overlap_lines) + new_content
                    new_start_line = max(
                        1, chunk.start_line - len(overlap_lines)
                    )
                    new_start_byte = max(
                        0, chunk.start_byte - sum(
                            len(line.encode('utf-8'))
                            for line in overlap_lines
                        )
                    )
            
            overlapped_chunks.append(CodeChunk(
                content=new_content,
                start_line=new_start_line,
                end_line=chunk.end_line,
                start_byte=new_start_byte,
                end_byte=chunk.end_byte,
                chunk_index=chunk.chunk_index,
                total_chunks=chunk.total_chunks,
                metadata={**chunk.metadata, 'has_overlap': i > 0}
            ))
        
        return overlapped_chunks
    
    def validate_chunks(self, chunks: List[CodeChunk],
                        original_code: str) -> bool:
        """
        Validate that chunks can be reassembled to the original code
        
        Args:
            chunks: List of chunks to validate
            original_code: Original source code
            
        Returns:
            True if chunks are valid
        """
        # Remove any overlap for validation
        reassembled = ''
        for chunk in chunks:
            if chunk.metadata.get('has_overlap'):
                # Skip overlap portion
                lines = chunk.content.splitlines(keepends=True)
                overlap_size = self.config.overlap_size
                reassembled += ''.join(lines[overlap_size:])
            else:
                reassembled += chunk.content
        
        return reassembled.strip() == original_code.strip()
    
    def _get_node_size(self, source: str, node: ast.AST) -> int:
        """Get the size of an AST node in bytes"""
        try:
            segment = ast.get_source_segment(source, node)
            if segment:
                return len(segment.encode('utf-8'))
        except Exception:
            pass
        return 0