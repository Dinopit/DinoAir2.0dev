"""
Unit tests for the parser module
"""

import pytest
from typing import List
from pseudocode_translator.parser import ParserModule
from pseudocode_translator.models import BlockType, CodeBlock, ParseResult


class TestParserModule:
    """Test the ParserModule class"""
    
    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing"""
        return ParserModule()
    
    def test_empty_input(self, parser):
        """Test parsing empty input"""
        blocks = parser.parse("")
        assert blocks == []
        
        blocks = parser.parse("   \n  \n  ")
        assert blocks == []
    
    def test_single_python_block(self, parser):
        """Test parsing a single Python block"""
        code = """def hello():
    print("Hello, World!")"""
        
        blocks = parser.parse(code)
        
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.PYTHON
        assert blocks[0].content == code
        assert blocks[0].line_numbers == (1, 2)
        assert blocks[0].metadata.get('has_functions') is True
    
    def test_single_english_block(self, parser):
        """Test parsing a single English instruction block"""
        instruction = "Create a function that adds two numbers together"
        
        blocks = parser.parse(instruction)
        
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.ENGLISH
        assert blocks[0].content == instruction
        assert blocks[0].line_numbers == (1, 1)
    
    def test_mixed_english_python(self, parser):
        """Test parsing mixed English and Python content"""
        code = """Create a function to calculate factorial

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

Now create a function to test it"""
        
        blocks = parser.parse(code)
        
        assert len(blocks) >= 2
        
        # First block should be English
        assert blocks[0].type == BlockType.ENGLISH
        assert "factorial" in blocks[0].content.lower()
        
        # Should have a Python block with the function
        python_blocks = [b for b in blocks if b.type == BlockType.PYTHON]
        assert len(python_blocks) >= 1
        assert any("def factorial" in b.content for b in python_blocks)
    
    def test_comments_classification(self, parser):
        """Test that comments are properly classified"""
        code = """# This is a comment
# Another comment line

def func():
    # Inline comment
    pass"""
        
        blocks = parser.parse(code)
        
        # Comments should be part of Python blocks or separate comment blocks
        assert all(b.type in [BlockType.PYTHON, BlockType.COMMENT] for b in blocks)
    
    def test_mixed_block_detection(self, parser):
        """Test detection of mixed English/Python blocks"""
        code = """# Create a simple calculator
def add(a, b):  # This adds two numbers
    return a + b  # Return the sum"""
        
        blocks = parser.parse(code)
        
        # This could be classified as either PYTHON or MIXED depending on thresholds
        assert len(blocks) >= 1
        assert blocks[0].type in [BlockType.PYTHON, BlockType.MIXED]
    
    def test_indentation_handling(self, parser):
        """Test proper handling of indented blocks"""
        code = """def outer():
    def inner():
        return 42
    
    result = inner()
    return result

print(outer())"""
        
        blocks = parser.parse(code)
        
        # Should properly handle nested indentation
        assert len(blocks) >= 1
        main_block = blocks[0]
        assert main_block.metadata.get('max_indent_level', 0) >= 2
    
    def test_multiline_strings(self, parser):
        """Test handling of multiline strings"""
        code = '''def get_doc():
    """
    This is a multiline
    docstring that spans
    multiple lines
    """
    return "done"'''
        
        blocks = parser.parse(code)
        
        assert len(blocks) >= 1
        assert blocks[0].type == BlockType.PYTHON
        assert blocks[0].metadata.get('has_docstring') is True
    
    def test_class_detection(self, parser):
        """Test detection of class definitions"""
        code = """class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b"""
        
        blocks = parser.parse(code)
        
        assert len(blocks) >= 1
        assert blocks[0].type == BlockType.PYTHON
        assert blocks[0].metadata.get('has_classes') is True
        assert blocks[0].metadata.get('has_functions') is True
    
    def test_import_detection(self, parser):
        """Test detection of import statements"""
        code = """import math
from typing import List, Dict
import numpy as np

def calculate():
    return math.pi"""
        
        blocks = parser.parse(code)
        
        # Could be one or more blocks
        python_blocks = [b for b in blocks if b.type == BlockType.PYTHON]
        assert any(b.metadata.get('has_imports') for b in python_blocks)
    
    def test_mixed_indentation_warning(self, parser):
        """Test warning for mixed tabs and spaces"""
        code = "def func():\n\tif True:\n        return 1  # Mixed!"
        
        result = parser.get_parse_result(code)
        
        # Should have a warning about mixed indentation
        assert any("mixed" in w.lower() and "indentation" in w.lower() 
                  for w in result.warnings)
    
    def test_incomplete_block_detection(self, parser):
        """Test detection of incomplete blocks"""
        code = """def incomplete_function():
    # TODO: implement this"""
        
        blocks = parser.parse(code)
        
        assert len(blocks) >= 1
        # Metadata might indicate this is incomplete
        assert blocks[0].metadata.get('likely_complete') is not None
    
    def test_error_handling(self, parser):
        """Test error handling in parsing"""
        # Very long line that might cause issues
        code = "x = " + "1 + " * 1000 + "1"
        
        result = parser.get_parse_result(code)
        
        # Should still parse without crashing
        assert result is not None
        assert len(result.blocks) >= 0
    
    def test_context_extraction(self, parser):
        """Test context extraction for blocks"""
        code = """# Previous code
x = 10
y = 20

# Target block
def add():
    return x + y

# Following code
result = add()"""
        
        blocks = parser.parse(code)
        
        # Find the function block
        func_blocks = [b for b in blocks if "def add" in b.content]
        assert len(func_blocks) > 0
        
        func_block = func_blocks[0]
        assert func_block.context is not None
        # Context should include surrounding code
        assert "x = 10" in func_block.context or "result = add()" in func_block.context


class TestBlockIdentification:
    """Test the block identification logic"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_function_boundary_detection(self, parser):
        """Test that function boundaries are properly detected"""
        code = """def first():
    return 1

def second():
    return 2"""
        
        blocks = parser._identify_blocks(code)
        
        # Should identify separate blocks for each function
        assert len(blocks) >= 2
        assert "def first" in blocks[0]
        assert "def second" in blocks[-1]
    
    def test_class_boundary_detection(self, parser):
        """Test that class boundaries are properly detected"""
        code = """class First:
    pass

class Second:
    pass"""
        
        blocks = parser._identify_blocks(code)
        
        assert len(blocks) >= 2
        assert "class First" in blocks[0]
        assert "class Second" in blocks[-1]
    
    def test_english_python_transition(self, parser):
        """Test transition detection between English and Python"""
        code = """Calculate the sum of two numbers

x = 10
y = 20
sum = x + y

Display the result

print(f"The sum is {sum}")"""
        
        blocks = parser._identify_blocks(code)
        
        # Should detect transitions between English and Python
        assert len(blocks) >= 3


class TestBlockClassification:
    """Test the block classification logic"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_pure_python_classification(self, parser):
        """Test classification of pure Python code"""
        python_code = """import math
def calculate_circle_area(radius):
    return math.pi * radius ** 2"""
        
        block_type = parser._classify_block(python_code)
        assert block_type == BlockType.PYTHON
    
    def test_pure_english_classification(self, parser):
        """Test classification of pure English text"""
        english_text = """Create a function that takes a list of numbers and returns
        the average. Make sure to handle empty lists appropriately."""
        
        block_type = parser._classify_block(english_text)
        assert block_type == BlockType.ENGLISH
    
    def test_mixed_classification(self, parser):
        """Test classification of mixed content"""
        mixed_content = """Create a function called calculate_average
def calculate_average(numbers):
    # Calculate and return the average
    return sum(numbers) / len(numbers)"""
        
        block_type = parser._classify_block(mixed_content)
        # Could be MIXED or lean towards one type
        assert block_type in [BlockType.MIXED, BlockType.PYTHON, BlockType.ENGLISH]
    
    def test_comment_classification(self, parser):
        """Test classification of comment-only blocks"""
        comment_block = """# This is a comment
# Another comment
# More comments"""
        
        block_type = parser._classify_block(comment_block)
        # Comments might be classified as COMMENT or PYTHON
        assert block_type in [BlockType.COMMENT, BlockType.PYTHON]


class TestMetadataExtraction:
    """Test metadata extraction functionality"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_basic_metadata(self, parser):
        """Test extraction of basic metadata"""
        code = """def hello():
    print("Hello")"""
        
        metadata = parser._extract_metadata(code)
        
        assert metadata['has_functions'] is True
        assert metadata['has_imports'] is False
        assert metadata['has_classes'] is False
        assert metadata['line_count'] == 2
    
    def test_indentation_metadata(self, parser):
        """Test indentation type detection"""
        spaces_code = """def func():
    if True:
        return 1"""
        
        metadata = parser._extract_metadata(spaces_code)
        assert metadata['indentation_type'] == 'spaces'
        assert metadata['max_indent_level'] >= 2
    
    def test_completeness_metadata(self, parser):
        """Test detection of incomplete blocks"""
        incomplete_code = """def incomplete():
    """
        
        metadata = parser._extract_metadata(incomplete_code)
        assert metadata['likely_complete'] is False


class TestScoring:
    """Test the scoring functions"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_python_scoring(self, parser):
        """Test Python score calculation"""
        # High Python score
        python_line = "def calculate(x, y): return x + y"
        score = parser._calculate_python_score(python_line)
        assert score > 0.5
        
        # Low Python score
        english_line = "Create a function to calculate the sum"
        score = parser._calculate_python_score(english_line)
        assert score < 0.5
    
    def test_english_scoring(self, parser):
        """Test English score calculation"""
        # High English score
        english_line = "Create a function that calculates the average of numbers"
        score = parser._calculate_english_score(english_line)
        assert score > 0.5
        
        # Low English score
        python_line = "result = sum(numbers) / len(numbers)"
        score = parser._calculate_english_score(python_line)
        assert score < 0.5


class TestParseResult:
    """Test the ParseResult generation"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_successful_parse_result(self, parser):
        """Test generation of successful parse result"""
        code = """def add(a, b):
    return a + b"""
        
        result = parser.get_parse_result(code)
        
        assert result.success is True
        assert len(result.blocks) > 0
        assert len(result.errors) == 0
    
    def test_parse_result_with_warnings(self, parser):
        """Test parse result with warnings"""
        code = """def func():
\tif True:  # Mixed indentation
        return 1"""
        
        result = parser.get_parse_result(code)
        
        # Should have warnings but still be successful
        assert len(result.warnings) > 0
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def parser(self):
        return ParserModule()
    
    def test_unicode_handling(self, parser):
        """Test handling of Unicode content"""
        code = """def greet():
    return "Hello, 世界! 🌍"
    
# Comment with émojis 😊"""
        
        blocks = parser.parse(code)
        assert len(blocks) > 0
        # Should handle Unicode without errors
    
    def test_very_long_lines(self, parser):
        """Test handling of very long lines"""
        long_line = "x = " + " + ".join([str(i) for i in range(100)])
        
        blocks = parser.parse(long_line)
        assert len(blocks) == 1
        assert blocks[0].line_numbers == (1, 1)
    
    def test_windows_line_endings(self, parser):
        """Test handling of Windows line endings"""
        code = "def func():\r\n    return 42\r\n"
        
        blocks = parser.parse(code)
        assert len(blocks) >= 1
        assert blocks[0].type == BlockType.PYTHON
    
    def test_no_newline_at_end(self, parser):
        """Test code without trailing newline"""
        code = "def func(): return 42"
        
        blocks = parser.parse(code)
        assert len(blocks) == 1
        assert blocks[0].content == code


@pytest.mark.parametrize("input_text,expected_min_blocks", [
    ("", 0),
    ("x = 1", 1),
    ("Create a function\ndef func(): pass", 2),
    ("import os\n\nclass Test:\n    pass\n\ndef main():\n    pass", 1),
])
def test_various_inputs(input_text, expected_min_blocks):
    """Parametrized test for various input types"""
    parser = ParserModule()
    blocks = parser.parse(input_text)
    assert len(blocks) >= expected_min_blocks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])