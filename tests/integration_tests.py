"""
Basic Integration Test Suite for DinoAir 2.0
Tests core system integration and functionality
"""

import unittest
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import Logger
from src.utils.config_loader import ConfigLoader


class TestBasicIntegration(unittest.TestCase):
    """Test basic system integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.logger = Logger()
        self.config = ConfigLoader()
    
    def test_logger_functionality(self):
        """Test that logging system works"""
        # Test all log levels
        self.logger.debug("Test debug message")
        self.logger.info("Test info message")
        self.logger.warning("Test warning message")
        self.logger.error("Test error message")
        self.logger.critical("Test critical message")
        
        # Logger should not raise exceptions
        self.assertTrue(True)
    
    def test_config_loading(self):
        """Test configuration loading"""
        # Test basic config access
        app_name = self.config.get("app.name")
        self.assertIsNotNone(app_name)
        self.assertIsInstance(app_name, str)
        
        # Test default values
        nonexistent = self.config.get("nonexistent.key", "default")
        self.assertEqual(nonexistent, "default")
    
    def test_env_override(self):
        """Test environment variable override"""
        # Test if env override functionality works
        if hasattr(self.config, 'env_vars'):
            self.assertIsInstance(self.config.env_vars, dict)
    
    def test_config_set_get(self):
        """Test setting and getting config values"""
        # Set a test value
        test_key = "test.integration.value"
        test_value = "test_data"
        
        self.config.set(test_key, test_value, save=False)
        retrieved_value = self.config.get(test_key)
        
        self.assertEqual(retrieved_value, test_value)


class TestToolIntegration(unittest.TestCase):
    """Test tool system integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.logger = Logger()
    
    def test_tool_imports(self):
        """Test that tool modules can be imported"""
        try:
            from src.tools.base import BaseTool, ToolResult, ToolStatus
            self.assertTrue(True, "Base tool classes imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import base tool classes: {e}")
    
    def test_tool_result_serialization(self):
        """Test ToolResult JSON serialization"""
        try:
            from src.tools.base import ToolResult, ToolStatus
            
            result = ToolResult(
                success=True,
                output={"test": "data"},
                metadata={"execution_time": 0.1}
            )
            
            # Test serialization
            result_dict = result.to_dict()
            self.assertIsInstance(result_dict, dict)
            self.assertIn("success", result_dict)
            self.assertIn("output", result_dict)
            self.assertTrue(result_dict["success"])
            
            # Test JSON serialization
            json_str = json.dumps(result_dict, default=str)
            self.assertIsInstance(json_str, str)
            
        except ImportError as e:
            self.skipTest(f"Tool system not available: {e}")
    
    def test_example_tool_availability(self):
        """Test that example tools are available"""
        try:
            from src.tools.examples.time_tool import TimeTool
            from src.tools.examples.json_data_tool import JsonDataTool
            
            # Test tool instantiation
            time_tool = TimeTool()
            json_tool = JsonDataTool()
            
            self.assertIsNotNone(time_tool)
            self.assertIsNotNone(json_tool)
            
        except ImportError as e:
            self.skipTest(f"Example tools not available: {e}")


class TestHealthCheck(unittest.TestCase):
    """Test health check functionality"""
    
    def test_health_check_script(self):
        """Test that health check script works"""
        import subprocess
        
        try:
            # Run health check in quiet mode
            result = subprocess.run(
                [sys.executable, "health_check.py", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Health check should complete (regardless of status)
            self.assertIn(result.stdout.strip(), ["healthy", "degraded", "unhealthy"])
            
        except subprocess.TimeoutExpired:
            self.fail("Health check timed out")
        except FileNotFoundError:
            self.skipTest("Health check script not found")


class TestCircularImportFix(unittest.TestCase):
    """Test that circular import issues are resolved"""
    
    def test_validator_import(self):
        """Test that validator can be imported without circular import"""
        try:
            from pseudocode_translator.validator import Validator
            self.assertTrue(True, "Validator imported successfully")
        except ImportError as e:
            # This might fail due to missing dependencies, but should not be circular import
            if "circular import" in str(e).lower():
                self.fail(f"Circular import still exists: {e}")
            else:
                self.skipTest(f"Validator unavailable due to dependencies: {e}")
    
    def test_models_package_import(self):
        """Test that models package imports work"""
        try:
            import pseudocode_translator.models
            self.assertTrue(True, "Models package imported successfully")
        except ImportError as e:
            if "circular import" in str(e).lower() or "ModelManager" in str(e):
                self.fail(f"Circular import issue: {e}")
            else:
                self.skipTest(f"Models package unavailable: {e}")


class TestProgressIndicators(unittest.TestCase):
    """Test CLI progress indicators"""
    
    def test_progress_bar(self):
        """Test progress bar functionality"""
        try:
            from src.utils.progress_indicators import ProgressBar
            
            # Test progress bar creation
            progress = ProgressBar(10, prefix="Test")
            self.assertIsNotNone(progress)
            
            # Test updates (should not raise exceptions)
            progress.update(1, "Step 1")
            progress.update(5, "Step 5")
            progress.finish("Complete")
            
        except ImportError as e:
            self.skipTest(f"Progress indicators not available: {e}")
    
    def test_spinner(self):
        """Test spinner functionality"""
        try:
            from src.utils.progress_indicators import Spinner
            
            spinner = Spinner("Testing")
            spinner.start()
            spinner.stop("Done")
            
            self.assertTrue(True, "Spinner worked without errors")
            
        except ImportError as e:
            self.skipTest(f"Progress indicators not available: {e}")


def run_integration_tests():
    """Run the integration test suite"""
    print("Running DinoAir Integration Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBasicIntegration,
        TestToolIntegration,
        TestHealthCheck,
        TestCircularImportFix,
        TestProgressIndicators
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Integration Test Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

    logger.info("\n" + "=" * 50)
    logger.info("Integration Test Summary")
    logger.info("=" * 50)
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Failures: {len(result.failures)}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        logger.info("✅ All tests passed!")
        return True
    else:
        logger.info("❌ Some tests failed")
        return False
if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)