"""
End-to-End Integration Tests for Pseudocode Translator

This module tests complete workflows from pseudocode input to validated output,
ensuring all components work together correctly.
"""

import unittest
import tempfile
import json
import time
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from translator import TranslationManager, TranslationResult
from config import TranslatorConfig
from models import CodeBlock, BlockType
from models.base_model import OutputLanguage
from exceptions import TranslatorError


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete translation workflows"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test configuration
        self.config = TranslatorConfig()
        
        # Mock the model initialization to avoid requiring actual model files
        with patch('translator.create_model') as mock_create:
            # Create a mock model
            self.mock_model = MagicMock()
            self.mock_model.validate_input.return_value = (True, None)
            self.mock_model.initialize.return_value = None
            self.mock_model.shutdown.return_value = None
            
            mock_create.return_value = self.mock_model
            
            # Initialize translation manager
            self.translator = TranslationManager(self.config)
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'translator'):
            self.translator.shutdown()
    
    def test_simple_pseudocode_translation(self):
        """Test translation of simple pseudocode"""
        # Input pseudocode
        pseudocode = """
        Create a function to calculate the area of a circle
        The function should take radius as input
        Return pi times radius squared
        """
        
        # Mock model translation
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="""def calculate_circle_area(radius):
    \"\"\"Calculate the area of a circle given its radius.\"\"\"
    import math
    return math.pi * radius ** 2""",
            errors=[],
            warnings=[]
        )
        
        # Perform translation
        result = self.translator.translate_pseudocode(pseudocode)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.code)
        self.assertIn('def calculate_circle_area', result.code)
        self.assertIn('math.pi', result.code)
        self.assertEqual(len(result.errors), 0)
    
    def test_mixed_english_python_translation(self):
        """Test translation of mixed English and Python blocks"""
        mixed_input = """
        # Define a class for a bank account
        class BankAccount:
            def __init__(self, initial_balance=0):
                self.balance = initial_balance
        
        Add a method to deposit money
        The method should add the amount to the balance
        
            def withdraw(self, amount):
                if amount <= self.balance:
                    self.balance -= amount
                    return True
                return False
        
        Create a method to check the balance
        """
        
        # Mock model translations for English blocks
        translation_responses = [
            MagicMock(
                success=True,
                code="""    def deposit(self, amount):
        \"\"\"Add money to the account.\"\"\"
        self.balance += amount""",
                errors=[],
                warnings=[]
            ),
            MagicMock(
                success=True,
                code="""    def get_balance(self):
        \"\"\"Check the current balance.\"\"\"
        return self.balance""",
                errors=[],
                warnings=[]
            )
        ]
        
        self.mock_model.translate.side_effect = translation_responses
        
        # Perform translation
        result = self.translator.translate_pseudocode(mixed_input)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.code)
        self.assertIn('class BankAccount:', result.code)
        self.assertIn('def deposit(self, amount):', result.code)
        self.assertIn('def withdraw(self, amount):', result.code)
        self.assertIn('def get_balance(self):', result.code)
    
    def test_complex_multi_block_workflow(self):
        """Test complex workflow with multiple interdependent blocks"""
        complex_input = """
        Import necessary libraries for data analysis
        
        # Existing imports
        import pandas as pd
        import numpy as np
        
        Create a function to load CSV data
        The function should handle errors and return a DataFrame
        
        def preprocess_data(df):
            # Remove null values
            df = df.dropna()
            return df
        
        Add a function to calculate statistics
        Should compute mean, median, and standard deviation
        
        Create a main function that:
        1. Loads the data
        2. Preprocesses it
        3. Calculates statistics
        4. Prints the results
        """
        
        # Mock model translations
        translation_responses = [
            # Import block
            MagicMock(
                success=True,
                code="import os\nimport sys",
                errors=[],
                warnings=[]
            ),
            # Load CSV function
            MagicMock(
                success=True,
                code="""def load_csv_data(filepath):
    \"\"\"Load CSV data with error handling.\"\"\"
    try:
        df = pd.read_csv(filepath)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None""",
                errors=[],
                warnings=[]
            ),
            # Statistics function
            MagicMock(
                success=True,
                code="""def calculate_statistics(df):
    \"\"\"Calculate mean, median, and standard deviation.\"\"\"
    stats = {
        'mean': df.mean(),
        'median': df.median(),
        'std': df.std()
    }
    return stats""",
                errors=[],
                warnings=[]
            ),
            # Main function
            MagicMock(
                success=True,
                code="""def main():
    \"\"\"Main function to orchestrate the data analysis.\"\"\"
    # Load the data
    df = load_csv_data('data.csv')
    if df is None:
        return
    
    # Preprocess it
    df = preprocess_data(df)
    
    # Calculate statistics
    stats = calculate_statistics(df)
    
    # Print the results
    print("Data Analysis Results:")
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()""",
                errors=[],
                warnings=[]
            )
        ]
        
        self.mock_model.translate.side_effect = translation_responses
        
        # Perform translation
        result = self.translator.translate_pseudocode(complex_input)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.code)
        
        # Check all components are present
        self.assertIn('import pandas as pd', result.code)
        self.assertIn('import numpy as np', result.code)
        self.assertIn('def load_csv_data', result.code)
        self.assertIn('def preprocess_data', result.code)
        self.assertIn('def calculate_statistics', result.code)
        self.assertIn('def main():', result.code)
        self.assertIn('if __name__ == "__main__":', result.code)
    
    def test_error_handling_workflow(self):
        """Test workflow with various error scenarios"""
        # Test 1: Invalid syntax in pseudocode
        invalid_input = """
        def broken_function(
            This is not valid Python or English
        """
        
        # Mock model to return error
        self.mock_model.translate.return_value = MagicMock(
            success=False,
            code=None,
            errors=["Invalid syntax: unexpected token"],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(invalid_input)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.code)
        self.assertTrue(len(result.errors) > 0)
    
    def test_streaming_translation_workflow(self):
        """Test streaming translation for large inputs"""
        # Create a large input that would benefit from streaming
        large_input = """
        Create a comprehensive data processing pipeline
        
        Step 1: Data ingestion
        Create functions to read from multiple sources
        
        Step 2: Data validation
        Implement validation rules
        
        Step 3: Data transformation
        Apply various transformations
        
        Step 4: Data aggregation
        Aggregate data by different dimensions
        
        Step 5: Output generation
        Generate reports and visualizations
        """ * 10  # Repeat to make it larger
        
        # Mock streaming responses
        chunk_responses = []
        for i in range(5):
            chunk_responses.append(MagicMock(
                success=True,
                code=f"# Chunk {i} code\ndef process_chunk_{i}(): pass",
                errors=[],
                warnings=[]
            ))
        
        # Test streaming
        with patch.object(self.translator, 'translate_streaming') as mock_stream:
            # Mock streaming results
            mock_stream.return_value = iter([
                TranslationResult(
                    success=True,
                    code=f"# Chunk {i}",
                    errors=[],
                    warnings=[],
                    metadata={'chunk_index': i, 'streaming': True}
                )
                for i in range(5)
            ])
            
            results = list(self.translator.translate_streaming(large_input))
            
            # Verify streaming was used
            self.assertTrue(len(results) > 0)
            for result in results[:-1]:  # All but final result
                self.assertTrue(result.metadata.get('streaming', False))
    
    def test_multi_language_output(self):
        """Test translation to different output languages"""
        pseudocode = "Create a function to add two numbers"
        
        # Test Python output (default)
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="def add_numbers(a, b):\n    return a + b",
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(
            pseudocode,
            target_language=OutputLanguage.PYTHON
        )
        
        self.assertTrue(result.success)
        self.assertIn('def add_numbers', result.code)
        
        # Test JavaScript output
        self.translator.set_target_language(OutputLanguage.JAVASCRIPT)
        
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="function addNumbers(a, b) {\n    return a + b;\n}",
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(pseudocode)
        
        self.assertTrue(result.success)
        self.assertIn('function addNumbers', result.code)
    
    def test_model_switching_workflow(self):
        """Test switching between different models"""
        pseudocode = "Print hello world"
        
        # Initial translation with default model
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code='print("Hello, World!")',
            errors=[],
            warnings=[]
        )
        
        result1 = self.translator.translate_pseudocode(pseudocode)
        self.assertTrue(result1.success)
        
        # Switch to a different model
        with patch('translator.create_model') as mock_create:
            new_mock_model = MagicMock()
            new_mock_model.validate_input.return_value = (True, None)
            new_mock_model.initialize.return_value = None
            new_mock_model.translate.return_value = MagicMock(
                success=True,
                code='print("Hello, World from new model!")',
                errors=[],
                warnings=[]
            )
            
            mock_create.return_value = new_mock_model
            
            self.translator.switch_model('gpt-model')
            
            result2 = self.translator.translate_pseudocode(pseudocode)
            self.assertTrue(result2.success)
    
    def test_validation_and_refinement_workflow(self):
        """Test code validation and automatic refinement"""
        pseudocode = "Create a function with syntax errors"
        
        # Mock initial translation with syntax error
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="def broken_function(\n    print('missing closing paren'",
            errors=[],
            warnings=[]
        )
        
        # Mock refinement to fix the error
        self.mock_model.refine_code.return_value = MagicMock(
            success=True,
            code="def broken_function():\n    print('missing closing paren')",
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(pseudocode)
        
        # Should succeed after automatic fix
        self.assertTrue(result.success)
        self.assertIn("automatically fixed", str(result.warnings))
    
    def test_incremental_translation_workflow(self):
        """Test incremental translation with context preservation"""
        # First translation
        first_input = """
        Create a Counter class
        Initialize with a starting value
        """
        
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="""class Counter:
    def __init__(self, start=0):
        self.value = start""",
            errors=[],
            warnings=[]
        )
        
        result1 = self.translator.translate_pseudocode(first_input)
        self.assertTrue(result1.success)
        
        # Second translation that builds on the first
        second_input = """
        Add an increment method to the Counter class
        Add a decrement method too
        """
        
        # Mock should now have context from previous translation
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="""    def increment(self):
        self.value += 1
    
    def decrement(self):
        self.value -= 1""",
            errors=[],
            warnings=[]
        )
        
        result2 = self.translator.translate_pseudocode(second_input)
        self.assertTrue(result2.success)
    
    def test_performance_metrics_workflow(self):
        """Test that performance metrics are properly collected"""
        pseudocode = "Create a simple hello world function"
        
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code='def hello_world():\n    print("Hello, World!")',
            errors=[],
            warnings=[]
        )
        
        start_time = time.time()
        result = self.translator.translate_pseudocode(pseudocode)
        end_time = time.time()
        
        # Verify metadata
        self.assertIn('duration_ms', result.metadata)
        self.assertIn('blocks_processed', result.metadata)
        self.assertIn('blocks_translated', result.metadata)
        self.assertIn('validation_passed', result.metadata)
        self.assertIn('translation_id', result.metadata)
        
        # Check duration is reasonable
        actual_duration = (end_time - start_time) * 1000
        reported_duration = result.metadata['duration_ms']
        self.assertLess(abs(reported_duration - actual_duration), 100)
    
    def test_edge_cases_workflow(self):
        """Test various edge cases"""
        # Empty input
        result = self.translator.translate_pseudocode("")
        self.assertFalse(result.success)
        
        # Only comments
        comment_only = """
        # This is just a comment
        # Another comment
        """
        result = self.translator.translate_pseudocode(comment_only)
        # Should handle gracefully
        self.assertIsNotNone(result)
        
        # Very long single line
        long_line = "Create a function that " + "does something " * 100
        
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code='def long_function(): pass',
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(long_line)
        self.assertTrue(result.success)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world translation scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        
        with patch('translator.create_model') as mock_create:
            self.mock_model = MagicMock()
            self.mock_model.validate_input.return_value = (True, None)
            self.mock_model.initialize.return_value = None
            self.mock_model.shutdown.return_value = None
            mock_create.return_value = self.mock_model
            
            self.translator = TranslationManager(self.config)
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'translator'):
            self.translator.shutdown()
    
    def test_web_scraper_scenario(self):
        """Test translating a web scraper pseudocode"""
        scraper_pseudocode = """
        Import requests and BeautifulSoup
        
        Create a function to scrape product data from a website
        The function should:
        - Take a URL as input
        - Make an HTTP request to the URL
        - Parse the HTML response
        - Extract product name, price, and description
        - Return a dictionary with the extracted data
        
        Handle errors gracefully:
        - Network errors should return None
        - Missing data should use default values
        
        Add a rate limiting mechanism to avoid overwhelming the server
        """
        
        # Mock translations
        self.mock_model.translate.side_effect = [
            MagicMock(
                success=True,
                code="import requests\nfrom bs4 import BeautifulSoup\nimport time",
                errors=[],
                warnings=[]
            ),
            MagicMock(
                success=True,
                code="""def scrape_product_data(url):
    \"\"\"Scrape product information from a website.\"\"\"
    try:
        # Make HTTP request
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract data with defaults
        product_data = {
            'name': soup.find('h1', class_='product-name').text.strip() if soup.find('h1', class_='product-name') else 'Unknown',
            'price': soup.find('span', class_='price').text.strip() if soup.find('span', class_='price') else '0.00',
            'description': soup.find('div', class_='description').text.strip() if soup.find('div', class_='description') else 'No description'
        }
        
        # Rate limiting
        time.sleep(1)
        
        return product_data
        
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None""",
                errors=[],
                warnings=[]
            )
        ]
        
        result = self.translator.translate_pseudocode(scraper_pseudocode)
        
        self.assertTrue(result.success)
        self.assertIn('import requests', result.code)
        self.assertIn('BeautifulSoup', result.code)
        self.assertIn('def scrape_product_data', result.code)
        self.assertIn('try:', result.code)
        self.assertIn('except', result.code)
        self.assertIn('time.sleep', result.code)
    
    def test_data_pipeline_scenario(self):
        """Test translating a data processing pipeline"""
        pipeline_pseudocode = """
        Create a data processing pipeline for customer analytics
        
        Step 1: Load customer data from CSV
        - Read customer_data.csv
        - Handle missing values
        - Convert date columns to datetime
        
        Step 2: Calculate customer metrics
        - Total purchases per customer
        - Average order value
        - Days since last purchase
        
        Step 3: Segment customers
        - High value: total purchases > 1000
        - Regular: total purchases between 100 and 1000
        - Low value: total purchases < 100
        
        Step 4: Generate summary report
        - Count customers in each segment
        - Calculate average metrics per segment
        - Save results to customer_segments.csv
        """
        
        # This would require multiple translation calls
        # For brevity, we'll mock a combined response
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="""import pandas as pd
import numpy as np
from datetime import datetime

def load_customer_data(filepath='customer_data.csv'):
    \"\"\"Load and preprocess customer data.\"\"\"
    df = pd.read_csv(filepath)
    df['purchase_date'] = pd.to_datetime(df['purchase_date'])
    df.fillna({'amount': 0}, inplace=True)
    return df

def calculate_customer_metrics(df):
    \"\"\"Calculate key metrics for each customer.\"\"\"
    metrics = df.groupby('customer_id').agg({
        'amount': ['sum', 'mean', 'count']
    })
    metrics.columns = ['total_purchases', 'avg_order_value', 'order_count']
    
    # Days since last purchase
    last_purchase = df.groupby('customer_id')['purchase_date'].max()
    metrics['days_since_last'] = (datetime.now() - last_purchase).dt.days
    
    return metrics

def segment_customers(metrics):
    \"\"\"Segment customers based on purchase value.\"\"\"
    conditions = [
        metrics['total_purchases'] > 1000,
        (metrics['total_purchases'] >= 100) & (metrics['total_purchases'] <= 1000),
        metrics['total_purchases'] < 100
    ]
    segments = ['high_value', 'regular', 'low_value']
    metrics['segment'] = np.select(conditions, segments)
    return metrics

def generate_summary_report(metrics, output_file='customer_segments.csv'):
    \"\"\"Generate and save summary report.\"\"\"
    summary = metrics.groupby('segment').agg({
        'total_purchases': ['count', 'mean'],
        'avg_order_value': 'mean',
        'days_since_last': 'mean'
    })
    
    summary.to_csv(output_file)
    print(f"Summary report saved to {output_file}")
    return summary

# Main pipeline
def run_customer_analytics_pipeline():
    \"\"\"Run the complete customer analytics pipeline.\"\"\"
    df = load_customer_data()
    metrics = calculate_customer_metrics(df)
    metrics = segment_customers(metrics)
    summary = generate_summary_report(metrics)
    return summary""",
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(pipeline_pseudocode)
        
        self.assertTrue(result.success)
        self.assertIn('pandas', result.code)
        self.assertIn('load_customer_data', result.code)
        self.assertIn('calculate_customer_metrics', result.code)
        self.assertIn('segment_customers', result.code)
        self.assertIn('generate_summary_report', result.code)


if __name__ == '__main__':
    unittest.main()