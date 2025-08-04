"""
Test Fixtures Package

This package contains test data, sample files, and fixtures used across
all test modules in the pseudocode translator test suite.
"""

import os
from pathlib import Path

# Get the fixtures directory path
FIXTURES_DIR = Path(__file__).parent

# Define subdirectories
PSEUDOCODE_DIR = FIXTURES_DIR / 'pseudocode'
EXPECTED_OUTPUT_DIR = FIXTURES_DIR / 'expected_output'
CONFIG_DIR = FIXTURES_DIR / 'configs'
ERROR_CASES_DIR = FIXTURES_DIR / 'error_cases'


def get_fixture_path(category: str, filename: str) -> Path:
    """
    Get the full path to a fixture file.
    
    Args:
        category: Category of fixture ('pseudocode', 'expected_output', 'configs', 'error_cases')
        filename: Name of the fixture file
        
    Returns:
        Full path to the fixture file
    """
    category_map = {
        'pseudocode': PSEUDOCODE_DIR,
        'expected_output': EXPECTED_OUTPUT_DIR,
        'configs': CONFIG_DIR,
        'error_cases': ERROR_CASES_DIR,
    }
    
    base_dir = category_map.get(category)
    if not base_dir:
        raise ValueError(f"Unknown fixture category: {category}")
    
    return base_dir / filename


def load_fixture(category: str, filename: str) -> str:
    """
    Load the content of a fixture file.
    
    Args:
        category: Category of fixture
        filename: Name of the fixture file
        
    Returns:
        Content of the fixture file
    """
    path = get_fixture_path(category, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def list_fixtures(category: str) -> list:
    """
    List all fixture files in a category.
    
    Args:
        category: Category to list fixtures from
        
    Returns:
        List of fixture filenames
    """
    path = get_fixture_path(category, '')
    if path.exists():
        return [f.name for f in path.iterdir() if f.is_file() and f.name != '__init__.py']
    return []


# Common test data that can be imported directly
SIMPLE_PSEUDOCODE = """
Create a function to calculate factorial
It should take a number n as input
If n is 0 or 1, return 1
Otherwise return n times factorial of n-1
"""

MIXED_PSEUDOCODE = """
# Python imports
import math

Create a class called Circle
It should have a radius attribute

def __init__(self, radius):
    self.radius = radius

Add a method to calculate area
The area should be pi times radius squared

Add a method to calculate circumference
"""

COMPLEX_PSEUDOCODE = """
Import necessary libraries for data processing

Create a DataProcessor class with the following:
- Initialize with a data source path
- Add a method to load data from CSV
- Add a method to clean the data:
  * Remove null values
  * Convert dates to proper format
  * Normalize numeric columns
- Add a method to analyze the data:
  * Calculate basic statistics
  * Find correlations
  * Generate summary report
- Add a method to visualize results

Create a main function that:
1. Creates a DataProcessor instance
2. Loads and cleans the data
3. Performs analysis
4. Saves results to output file
"""

EXPECTED_FACTORIAL_OUTPUT = '''def calculate_factorial(n):
    """Calculate factorial of a number."""
    if n == 0 or n == 1:
        return 1
    else:
        return n * calculate_factorial(n - 1)'''

EXPECTED_CIRCLE_OUTPUT = '''import math


class Circle:
    """A class to represent a circle."""
    
    def __init__(self, radius):
        self.radius = radius
    
    def calculate_area(self):
        """Calculate the area of the circle."""
        return math.pi * self.radius ** 2
    
    def calculate_circumference(self):
        """Calculate the circumference of the circle."""
        return 2 * math.pi * self.radius'''

# Sample configuration data
SAMPLE_CONFIG_VALID = {
    '_version': '3.0',
    'llm': {
        'model_type': 'qwen',
        'model_path': 'models/qwen-7b.gguf',
        'temperature': 0.7,
        'top_p': 0.9,
        'top_k': 40,
        'max_tokens': 2048,
        'n_ctx': 4096,
        'n_batch': 512,
        'n_threads': 4,
        'n_gpu_layers': 20,
        'models': {
            'qwen': {
                'enabled': True,
                'name': 'qwen',
                'path': 'models/qwen-7b.gguf',
                'config': {}
            }
        }
    },
    'streaming': {
        'enabled': True,
        'chunk_size': 4096,
        'overlap_size': 200,
        'min_chunk_size': 1000,
        'max_chunks': 10,
        'parallel_chunks': False,
        'memory_limit_mb': 1000
    },
    'parser': {
        'min_confidence': 0.3,
        'context_lines': 5,
        'max_block_size': 1000,
        'merge_small_blocks': True,
        'preserve_empty_lines': False
    },
    'assembler': {
        'indent_size': 4,
        'max_line_length': 88,
        'preserve_comments': True,
        'preserve_docstrings': True,
        'organize_imports': True,
        'auto_import_common': True,
        'fix_indentation': True,
        'ensure_final_newline': True
    },
    'validator': {
        'check_syntax': True,
        'check_undefined_vars': True,
        'check_unused_imports': True,
        'check_style': False,
        'max_complexity': 15,
        'forbidden_patterns': []
    },
    'error_handling': {
        'max_retries': 3,
        'retry_delay': 1.0,
        'fallback_to_basic': True,
        'collect_diagnostics': True,
        'error_recovery': True
    },
    'performance': {
        'enable_caching': True,
        'cache_ttl': 3600,
        'max_cache_size_mb': 500,
        'enable_parallel': True,
        'batch_size': 10,
        'profile_enabled': False
    },
    'output': {
        'default_language': 'python',
        'include_comments': True,
        'include_docstrings': True,
        'include_type_hints': True,
        'follow_conventions': True
    },
    'advanced': {
        'enable_plugins': True,
        'plugin_directory': 'plugins',
        'enable_telemetry': False,
        'debug_mode': False,
        'log_level': 'INFO'
    },
    'validate_imports': True,
    'check_undefined_vars': True,
    'allow_unsafe_operations': False,
    'indent_size': 4,
    'max_line_length': 88,
    'preserve_comments': True,
    'preserve_docstrings': True,
    'auto_import_common': True
}

SAMPLE_CONFIG_INVALID = {
    '_version': '3.0',
    'llm': {
        # Missing required fields
        'temperature': 0.7
    },
    'streaming': {
        'enabled': 'yes'  # Should be boolean
    }
}

# Error test cases
SYNTAX_ERROR_PSEUDOCODE = """
def broken_function(
    This is not valid syntax
    print("Hello")
"""

UNDEFINED_VAR_PSEUDOCODE = """
Create a function to process data
Use the undefined_variable in calculations
Return the result
"""

IMPORT_ERROR_PSEUDOCODE = """
Import a non-existent module called fake_module
Use functions from fake_module
"""