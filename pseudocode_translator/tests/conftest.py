"""
Pytest configuration and shared fixtures for pseudocode_translator tests
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))


# Shared fixtures for all tests

@pytest.fixture
def mock_config():
    """Create a mock TranslatorConfig"""
    config = Mock()
    
    # LLM config
    config.llm = Mock()
    config.llm.model_type = "qwen-7b"
    config.llm.model_name = "qwen-7b-q4_k_m.gguf"
    config.llm.models_dir = "./models"
    config.llm.n_ctx = 2048
    config.llm.n_batch = 512
    config.llm.n_threads = 4
    config.llm.n_gpu_layers = 0
    config.llm.max_tokens = 1024
    config.llm.temperature = 0.7
    config.llm.top_p = 0.95
    config.llm.top_k = 40
    config.llm.repeat_penalty = 1.1
    config.llm.cache_enabled = True
    config.llm.cache_ttl_hours = 24
    config.llm.validation_level = "normal"
    config.llm.validate.return_value = []
    config.llm.get_model_path = Mock(return_value=Path("./models/qwen-7b/model.gguf"))
    
    # General config
    config.validate_imports = True
    config.check_undefined_vars = True
    config.allow_unsafe_operations = False
    config.max_line_length = 79
    config.preserve_comments = True
    config.organize_imports = True
    config.add_type_hints = False
    config.code_style = "pep8"
    
    return config


@pytest.fixture
def sample_code_blocks():
    """Create sample code blocks for testing"""
    from pseudocode_translator.models import CodeBlock, BlockType
    
    blocks = [
        CodeBlock(
            type=BlockType.PYTHON,
            content="import math\nimport sys",
            line_numbers=(1, 2),
            metadata={"has_imports": True}
        ),
        CodeBlock(
            type=BlockType.ENGLISH,
            content="Create a function to calculate the area of a circle",
            line_numbers=(4, 4),
            metadata={}
        ),
        CodeBlock(
            type=BlockType.PYTHON,
            content="def calculate_circle_area(radius):\n    return math.pi * radius ** 2",
            line_numbers=(5, 6),
            metadata={"has_functions": True}
        ),
        CodeBlock(
            type=BlockType.MIXED,
            content="# Now test the function\nresult = calculate_circle_area(5)\nprint the result",
            line_numbers=(8, 10),
            metadata={}
        )
    ]
    
    return blocks


@pytest.fixture
def sample_parse_result(sample_code_blocks):
    """Create a sample ParseResult"""
    from pseudocode_translator.models import ParseResult
    
    return ParseResult(
        blocks=sample_code_blocks,
        errors=[],
        warnings=[]
    )


@pytest.fixture
def mock_llm_model():
    """Create a mock LLM model"""
    model = Mock()
    
    # Default response
    model.return_value = {
        'choices': [{
            'text': 'def example():\n    return "Hello, World!"'
        }]
    }
    
    return model


@pytest.fixture
def mock_llm_interface(mock_config, mock_llm_model):
    """Create a mock LLM interface"""
    from unittest.mock import patch
    
    with patch('pseudocode_translator.llm_interface.Llama') as mock_llama:
        mock_llama.return_value = mock_llm_model
        
        from pseudocode_translator.llm_interface import LLMInterface
        interface = LLMInterface(mock_config.llm)
        interface._initialized = True
        interface.model = mock_llm_model
        
        return interface


# Test configuration

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_model: marks tests that require the LLM model"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add unit marker to all tests by default
        if "integration" not in item.keywords and "slow" not in item.keywords:
            item.add_marker(pytest.mark.unit)
        
        # Add markers based on test file names
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)


# Test utilities

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def sample_pseudocode():
    """Sample pseudocode for testing"""
    return """
# Import necessary modules
import math

Create a function called calculate_circle_area that:
- Takes radius as parameter
- Returns the area using formula pi * r^2

def calculate_rectangle_area(length, width):
    return length * width

Create a main function that:
- Asks user for shape type
- Gets dimensions
- Calculates and prints area
"""


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing"""
    return """
import math

def calculate_circle_area(radius):
    \"\"\"Calculate the area of a circle given its radius.\"\"\"
    return math.pi * radius ** 2

def calculate_rectangle_area(length, width):
    return length * width

def main():
    shape_type = input("Enter shape type (circle/rectangle): ")
    
    if shape_type == "circle":
        radius = float(input("Enter radius: "))
        area = calculate_circle_area(radius)
    elif shape_type == "rectangle":
        length = float(input("Enter length: "))
        width = float(input("Enter width: "))
        area = calculate_rectangle_area(length, width)
    else:
        print("Unknown shape type")
        return
    
    print(f"The area is: {area}")

if __name__ == "__main__":
    main()
"""


@pytest.fixture
def mock_assembler_config():
    """Configuration for CodeAssembler mock"""
    config = Mock()
    config.preserve_comments = True
    config.organize_imports = True
    config.add_type_hints = False
    config.code_style = "pep8"
    return config


# Error and warning fixtures

@pytest.fixture
def sample_syntax_error():
    """Sample code with syntax error"""
    return """
def broken_function(
    print("Missing closing parenthesis")
    
x = [1, 2, 3
"""


@pytest.fixture
def sample_validation_warnings():
    """Sample code that should generate warnings"""
    return """
def risky_function(data=[]):  # Mutable default argument
    data.append(1)
    return data

try:
    risky_operation()
except:  # Bare except
    pass

from module import *  # Wildcard import
"""


# Performance test fixtures

@pytest.fixture
def large_pseudocode():
    """Generate large pseudocode for performance testing"""
    lines = []
    for i in range(100):
        if i % 10 == 0:
            lines.append(f"# Section {i//10}")
        if i % 3 == 0:
            lines.append(f"Create function func_{i} that returns {i}")
        else:
            lines.append(f"x_{i} = {i} * 2")
    return "\n".join(lines)


# Cleanup fixtures

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test"""
    yield
    # Any cleanup code here


# Helper functions for tests

def create_mock_code_block(block_type, content, line_start=1):
    """Helper to create a mock code block"""
    from pseudocode_translator.models import CodeBlock, BlockType
    
    line_count = content.count('\n') + 1
    return CodeBlock(
        type=BlockType[block_type.upper()],
        content=content,
        line_numbers=(line_start, line_start + line_count - 1),
        metadata={}
    )


def assert_code_valid(code):
    """Helper to assert that code is syntactically valid"""
    try:
        compile(code, '<test>', 'exec')
        return True
    except SyntaxError as e:
        pytest.fail(f"Invalid syntax in generated code: {e}")
        return False


def assert_contains_all(text, substrings):
    """Helper to assert text contains all substrings"""
    for substring in substrings:
        assert substring in text, f"Expected '{substring}' in text"


def assert_contains_none(text, substrings):
    """Helper to assert text contains none of the substrings"""
    for substring in substrings:
        assert substring not in text, f"Unexpected '{substring}' in text"