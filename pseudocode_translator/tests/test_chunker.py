"""
Tests for the smart code chunker
"""

import pytest
import ast

from pseudocode_translator.streaming.chunker import (
    CodeChunker, ChunkConfig, CodeChunk
)


class TestCodeChunker:
    """Test cases for CodeChunker"""
    
    @pytest.fixture
    def default_config(self):
        """Create default chunk configuration"""
        return ChunkConfig(
            max_chunk_size=1024,
            min_chunk_size=256,
            overlap_size=50,
            respect_boundaries=True,
            max_lines_per_chunk=50
        )
    
    @pytest.fixture
    def chunker(self, default_config):
        """Create test chunker"""
        return CodeChunker(default_config)
    
    def test_small_code_single_chunk(self, chunker):
        """Test that small code returns single chunk"""
        small_code = """
def hello():
    print("Hello, World!")

hello()
"""
        chunks = chunker.chunk_code(small_code)
        
        assert len(chunks) == 1
        assert chunks[0].content == small_code
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1
        assert chunks[0].metadata['single_chunk'] is True
    
    def test_chunk_respects_function_boundaries(self, chunker):
        """Test that chunking respects function boundaries"""
        code = """
def function1():
    # This is function 1
    x = 1
    y = 2
    return x + y

def function2():
    # This is function 2
    a = 10
    b = 20
    return a * b

def function3():
    # This is function 3
    result = function1() + function2()
    return result
"""
        
        # Make chunk size small to force splitting
        chunker.config.max_chunk_size = 200
        chunks = chunker.chunk_code(code)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should contain complete functions
        for chunk in chunks:
            # Try to parse each chunk - should be valid Python
            try:
                ast.parse(chunk.content)
            except SyntaxError:
                # If it's not valid, it might be due to overlap
                # Check if it has overlap metadata
                assert chunk.metadata.get('has_overlap', False)
    
    def test_chunk_respects_class_boundaries(self, chunker):
        """Test that chunking respects class boundaries"""
        code = """
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        self.result = x + y
        return self.result
    
    def multiply(self, x, y):
        self.result = x * y
        return self.result

class AdvancedCalculator(Calculator):
    def power(self, x, y):
        self.result = x ** y
        return self.result
"""
        
        chunker.config.max_chunk_size = 300
        chunks = chunker.chunk_code(code)
        
        # Each chunk should try to keep classes intact
        for chunk in chunks:
            content = chunk.content.strip()
            if content.startswith('class'):
                # Should contain the complete class definition
                assert 'class' in content
                # Basic check that it's not cut off mid-class
                assert content.count('class') <= 2  # Max 2 classes per chunk
    
    def test_chunk_line_numbers(self, chunker):
        """Test that line numbers are correctly tracked"""
        code = """line1
line2
line3
line4
line5
line6
line7
line8
line9
line10"""
        
        chunker.config.max_chunk_size = 30  # Force multiple chunks
        chunks = chunker.chunk_code(code)
        
        # Check line numbers
        for i, chunk in enumerate(chunks):
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
            
            # Line count should match content
            actual_lines = chunk.content.count('\n') + 1
            expected_lines = chunk.end_line - chunk.start_line + 1
            
            # Allow for some difference due to trailing newlines
            assert abs(actual_lines - expected_lines) <= 1
    
    def test_chunk_size_limits(self, chunker):
        """Test that chunks respect size limits"""
        # Create code that will require chunking
        large_code = "\n".join([f"x{i} = {i}" for i in range(1000)])
        
        chunks = chunker.chunk_code(large_code)
        
        for chunk in chunks:
            # Check size constraints
            assert chunk.size <= chunker.config.max_chunk_size
            
            # Check line count constraints
            line_count = chunk.content.count('\n') + 1
            assert line_count <= chunker.config.max_lines_per_chunk
    
    def test_streaming_chunks(self, chunker):
        """Test streaming chunk generation"""
        code = """
def func1():
    pass

def func2():
    pass

def func3():
    pass
"""
        
        # Test streaming
        chunk_list = list(chunker.stream_chunks(code))
        
        # Should get same results as non-streaming
        regular_chunks = chunker.chunk_code(code)
        
        assert len(chunk_list) == len(regular_chunks)
        for streamed, regular in zip(chunk_list, regular_chunks):
            assert streamed.content == regular.content
            assert streamed.chunk_index == regular.chunk_index
    
    def test_overlap_between_chunks(self, chunker):
        """Test overlap functionality between chunks"""
        code = "\n".join([f"line{i}" for i in range(100)])
        
        chunker.config.max_chunk_size = 200
        chunker.config.overlap_size = 5
        
        chunks = chunker.chunk_code(code)
        
        if len(chunks) > 1:
            # Check that chunks have overlap
            for i in range(1, len(chunks)):
                assert chunks[i].metadata.get('has_overlap', False)
                
                # The beginning of chunk i should overlap with end of chunk i-1
                # This is a simplified check
                assert chunks[i].start_line < chunks[i-1].end_line
    
    def test_chunk_validation(self, chunker):
        """Test chunk validation"""
        original_code = """
def test():
    x = 1
    y = 2
    return x + y

result = test()
print(result)
"""
        
        chunks = chunker.chunk_code(original_code)
        
        # Validate chunks can be reassembled
        assert chunker.validate_chunks(chunks, original_code)
    
    def test_mixed_content_chunking(self, chunker):
        """Test chunking with mixed content (comments, strings, etc.)"""
        code = '''
"""
This is a module docstring
that spans multiple lines
"""

# Import section
import os
import sys

# Constants
CONSTANT_VALUE = 42

def function_with_docstring():
    """
    This function has a docstring
    that spans multiple lines
    """
    # Multi-line string
    text = """
    This is a long string
    that spans multiple lines
    and should be kept together
    """
    return text

# Another function
def another_function():
    # This has inline comments
    x = 1  # Initialize x
    y = 2  # Initialize y
    return x + y  # Return sum
'''
        
        chunker.config.max_chunk_size = 400
        chunks = chunker.chunk_code(code)
        
        # Should handle mixed content gracefully
        assert len(chunks) >= 1
        
        # Each chunk should be parseable
        for chunk in chunks:
            try:
                ast.parse(chunk.content)
            except SyntaxError as e:
                # Only allow syntax errors in overlap regions
                if not chunk.metadata.get('has_overlap', False):
                    pytest.fail(f"Chunk {chunk.chunk_index} has syntax error: {e}")
    
    def test_empty_code(self, chunker):
        """Test handling of empty code"""
        chunks = chunker.chunk_code("")
        assert len(chunks) == 0
        
        chunks = chunker.chunk_code("   \n  \n  ")
        assert len(chunks) == 0
    
    def test_chunk_metadata(self, chunker):
        """Test that chunks contain proper metadata"""
        code = """
def func1():
    pass

class MyClass:
    pass

import os
"""
        
        chunks = chunker.chunk_code(code)
        
        for chunk in chunks:
            assert 'ast_based' in chunk.metadata or 'line_based' in chunk.metadata
            
            if chunk.metadata.get('ast_based'):
                # AST-based chunks should have boundary information
                assert 'boundary_types' in chunk.metadata
                assert isinstance(chunk.metadata['boundary_types'], list)
    
    def test_edge_cases(self, chunker):
        """Test various edge cases"""
        # Very long single line
        long_line = "x = " + " + ".join([str(i) for i in range(1000)])
        chunks = chunker.chunk_code(long_line)
        assert len(chunks) >= 1
        
        # Code with only comments
        comment_code = """
# Comment 1
# Comment 2
# Comment 3
# Comment 4
"""
        chunks = chunker.chunk_code(comment_code)
        assert len(chunks) >= 1
        
        # Code with syntax errors (should still chunk)
        invalid_code = """
def incomplete_function(
    # Missing closing parenthesis and body
    
another_line = 42
"""
        chunks = chunker.chunk_code(invalid_code)
        assert len(chunks) >= 1  # Should fall back to line-based chunking


class TestChunkConfig:
    """Test cases for ChunkConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ChunkConfig()
        
        assert config.max_chunk_size == 4096
        assert config.min_chunk_size == 512
        assert config.overlap_size == 256
        assert config.respect_boundaries is True
        assert config.max_lines_per_chunk == 100
        assert config.preserve_indentation is True
        assert config.chunk_by_blocks is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ChunkConfig(
            max_chunk_size=8192,
            min_chunk_size=1024,
            overlap_size=512,
            respect_boundaries=False,
            max_lines_per_chunk=200
        )
        
        assert config.max_chunk_size == 8192
        assert config.min_chunk_size == 1024
        assert config.overlap_size == 512
        assert config.respect_boundaries is False
        assert config.max_lines_per_chunk == 200


class TestCodeChunk:
    """Test cases for CodeChunk dataclass"""
    
    def test_chunk_properties(self):
        """Test CodeChunk properties"""
        chunk = CodeChunk(
            content="def test():\n    pass\n",
            start_line=1,
            end_line=2,
            start_byte=0,
            end_byte=22,
            chunk_index=0,
            total_chunks=1
        )
        
        assert chunk.size == 22  # Based on UTF-8 encoding
        assert chunk.line_count == 2
        
        # Test metadata initialization
        assert chunk.metadata is not None
        assert isinstance(chunk.metadata, dict)
    
    def test_chunk_with_metadata(self):
        """Test CodeChunk with custom metadata"""
        metadata = {
            'boundary_types': ['FunctionDef'],
            'contains': ['test_function'],
            'ast_based': True
        }
        
        chunk = CodeChunk(
            content="def test_function():\n    return 42\n",
            start_line=5,
            end_line=6,
            start_byte=100,
            end_byte=136,
            chunk_index=2,
            total_chunks=5,
            metadata=metadata
        )
        
        assert chunk.metadata == metadata
        assert chunk.metadata['boundary_types'] == ['FunctionDef']
        assert chunk.metadata['ast_based'] is True