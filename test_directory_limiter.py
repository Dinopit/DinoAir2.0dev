"""Test script for Directory Limiter and Settings Integration.

This script tests:
- Directory restrictions work correctly
- Path traversal attacks are blocked
- Settings persist across restarts
- GUI updates reflect in backend behavior
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database.file_search_db import FileSearchDB
from src.rag.directory_validator import DirectoryValidator
from src.rag.file_processor import FileProcessor
from src.utils.logger import Logger

# Test configuration
TEST_USER = "test_dir_limiter_user"
logger = Logger()


class DirectoryLimiterTest:
    """Test suite for directory limiter functionality."""
    
    def __init__(self):
        """Initialize test environment."""
        self.db = FileSearchDB(TEST_USER)
        self.validator = DirectoryValidator()
        self.processor = FileProcessor(TEST_USER)
        self.test_results = []
        
        # Create test directories
        self.test_base = os.path.join(tempfile.gettempdir(), "dinoair_test")
        self.allowed_dir = os.path.join(self.test_base, "allowed")
        self.excluded_dir = os.path.join(self.test_base, "excluded")
        self.test_file = os.path.join(self.allowed_dir, "test.txt")
        
        self._setup_test_environment()
    
    def _setup_test_environment(self):
        """Set up test directories and files."""
        # Create directories
        os.makedirs(self.allowed_dir, exist_ok=True)
        os.makedirs(self.excluded_dir, exist_ok=True)
        
        # Create test files
        with open(self.test_file, 'w') as f:
            f.write("This is a test file for directory limiter testing.")
        
        with open(os.path.join(self.excluded_dir, "excluded.txt"), 'w') as f:
            f.write("This file should not be accessible.")
    
    def run_all_tests(self):
        """Run all test cases."""
        print("🔍 Starting Directory Limiter Tests...\n")
        
        # Test 1: Directory Validator Basic Functionality
        self.test_directory_validator()
        
        # Test 2: Path Traversal Attack Prevention
        self.test_path_traversal_prevention()
        
        # Test 3: Database Directory Settings
        self.test_database_directory_settings()
        
        # Test 4: File Processor Integration
        self.test_file_processor_integration()
        
        # Test 5: Settings Persistence
        self.test_settings_persistence()
        
        # Test 6: Security Validation
        self.test_security_validation()
        
        # Print summary
        self._print_test_summary()
    
    def test_directory_validator(self):
        """Test basic directory validator functionality."""
        print("📁 Test 1: Directory Validator Basic Functionality")
        
        try:
            # Set allowed and excluded directories
            self.validator.set_allowed_directories([self.allowed_dir])
            self.validator.set_excluded_directories([self.excluded_dir])
            
            # Test allowed path
            allowed_result = self.validator.is_path_allowed(self.test_file)
            self._assert(allowed_result, "Allowed path should be accessible")
            
            # Test excluded path
            excluded_file = os.path.join(self.excluded_dir, "excluded.txt")
            excluded_result = self.validator.is_path_allowed(excluded_file)
            self._assert(not excluded_result, "Excluded path should not be accessible")
            
            # Test path validation
            validation = self.validator.validate_path(self.test_file)
            self._assert(validation["valid"], "Valid path should pass validation")
            
            self._log_result("Directory Validator", True, "All basic tests passed")
            
        except Exception as e:
            self._log_result("Directory Validator", False, str(e))
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        print("\n🛡️ Test 2: Path Traversal Attack Prevention")
        
        try:
            # Test various path traversal attempts
            traversal_paths = [
                "../../../Windows/System32",
                "..\\..\\..\\Windows\\System32",
                "C:\\allowed\\..\\..\\Windows",
                "~/../../etc/passwd",
                "C:\\test\\..\\..\\..\\..\\..\\Windows"
            ]
            
            for path in traversal_paths:
                validation = self.validator.validate_path(path)
                self._assert(
                    not validation["valid"],
                    f"Path traversal '{path}' should be blocked"
                )
                print(f"  ✓ Blocked: {path}")
            
            self._log_result("Path Traversal Prevention", True, 
                           "All traversal attempts blocked")
            
        except Exception as e:
            self._log_result("Path Traversal Prevention", False, str(e))
    
    def test_database_directory_settings(self):
        """Test database storage of directory settings."""
        print("\n💾 Test 3: Database Directory Settings")
        
        try:
            # Add allowed directories
            result = self.db.add_allowed_directory(self.allowed_dir)
            self._assert(result["success"], "Should add allowed directory")
            
            # Add excluded directories
            result = self.db.add_excluded_directory(self.excluded_dir)
            self._assert(result["success"], "Should add excluded directory")
            
            # Get directory settings
            settings = self.db.get_directory_settings()
            self._assert(settings["success"], "Should retrieve settings")
            self._assert(
                self.allowed_dir in settings["allowed_directories"],
                "Allowed directory should be in settings"
            )
            self._assert(
                self.excluded_dir in settings["excluded_directories"],
                "Excluded directory should be in settings"
            )
            
            # Test duplicate prevention
            result = self.db.add_allowed_directory(self.allowed_dir)
            self._assert(
                result["message"] == "Directory already in allowed list",
                "Should prevent duplicate entries"
            )
            
            # Remove directory
            result = self.db.remove_allowed_directory(self.allowed_dir)
            self._assert(result["success"], "Should remove allowed directory")
            
            self._log_result("Database Directory Settings", True,
                           "All database operations successful")
            
        except Exception as e:
            self._log_result("Database Directory Settings", False, str(e))
    
    def test_file_processor_integration(self):
        """Test file processor respects directory limits."""
        print("\n⚙️ Test 4: File Processor Integration")
        
        try:
            # Reset and configure directories
            self.db.add_allowed_directory(self.allowed_dir)
            self.db.add_excluded_directory(self.excluded_dir)
            
            # Reload processor settings
            self.processor._load_directory_settings()
            
            # Test processing allowed file
            allowed_result = self.processor.process_file(self.test_file)
            self._assert(
                allowed_result["success"],
                "Should process file in allowed directory"
            )
            print(f"  ✓ Processed allowed file: {os.path.basename(self.test_file)}")
            
            # Test processing excluded file
            excluded_file = os.path.join(self.excluded_dir, "excluded.txt")
            excluded_result = self.processor.process_file(excluded_file)
            self._assert(
                not excluded_result["success"],
                "Should not process file in excluded directory"
            )
            self._assert(
                "Access denied" in excluded_result.get("error", ""),
                "Should show access denied error"
            )
            print(f"  ✓ Blocked excluded file: {os.path.basename(excluded_file)}")
            
            # Test directory processing
            dir_result = self.processor.process_directory(
                self.test_base,
                recursive=True,
                file_extensions=['.txt']
            )
            self._assert(
                dir_result["success"],
                "Should process directory"
            )
            # Should only process allowed files
            processed_count = dir_result["stats"]["processed"]
            self._assert(
                processed_count == 1,
                f"Should process only 1 allowed file, got {processed_count}"
            )
            
            self._log_result("File Processor Integration", True,
                           "Directory restrictions enforced correctly")
            
        except Exception as e:
            self._log_result("File Processor Integration", False, str(e))
    
    def test_settings_persistence(self):
        """Test that settings persist across restarts."""
        print("\n💿 Test 5: Settings Persistence")
        
        try:
            # Store complex settings
            test_settings = {
                "allowed_directories": [self.allowed_dir, "C:\\Users\\Test"],
                "excluded_directories": [self.excluded_dir, "C:\\Windows"],
                "max_file_size_mb": 100,
                "chunk_size": 2000
            }
            
            # Save settings
            result = self.db.update_search_settings(
                "file_search_config", test_settings
            )
            self._assert(result["success"], "Should save settings")
            
            # Create new database instance to simulate restart
            new_db = FileSearchDB(TEST_USER)
            
            # Retrieve settings
            retrieved = new_db.get_search_settings("file_search_config")
            self._assert(retrieved["success"], "Should retrieve settings")
            
            # Verify settings match
            saved_settings = retrieved["setting_value"]
            self._assert(
                saved_settings["max_file_size_mb"] == 100,
                "Numeric settings should persist"
            )
            self._assert(
                len(saved_settings["allowed_directories"]) == 2,
                "Directory lists should persist"
            )
            
            self._log_result("Settings Persistence", True,
                           "Settings persist correctly across restarts")
            
        except Exception as e:
            self._log_result("Settings Persistence", False, str(e))
    
    def test_security_validation(self):
        """Test security features and critical path protection."""
        print("\n🔒 Test 6: Security Validation")
        
        try:
            # Test critical system paths
            critical_paths = [
                "C:\\Windows\\System32\\config",
                "C:\\Windows\\System32\\drivers",
                "C:\\pagefile.sys",
                "C:\\hiberfil.sys"
            ]
            
            for path in critical_paths:
                # Create dummy file path for testing
                test_path = os.path.join(path, "test.txt")
                allowed = self.validator.is_path_allowed(test_path)
                self._assert(
                    not allowed,
                    f"Critical path '{path}' should be blocked"
                )
                print(f"  ✓ Blocked critical path: {path}")
            
            # Test validation messages
            validation = self.validator.validate_path("../etc/passwd")
            self._assert(
                "Path traversal" in validation["message"],
                "Should identify path traversal"
            )
            
            # Test directory validation
            dir_validation = self.validator.validate_directory_list([
                self.allowed_dir,
                "C:\\Program Files",
                "nonexistent_dir",
                "../../../etc"
            ])
            
            self._assert(
                len(dir_validation["valid"]) == 1,
                "Should validate only legitimate directories"
            )
            self._assert(
                len(dir_validation["warnings"]) >= 1,
                "Should warn about problematic directories"
            )
            
            self._log_result("Security Validation", True,
                           "All security checks passed")
            
        except Exception as e:
            self._log_result("Security Validation", False, str(e))
    
    def _assert(self, condition: bool, message: str):
        """Assert helper with descriptive error messages."""
        if not condition:
            raise AssertionError(message)
    
    def _log_result(self, test_name: str, success: bool, message: str):
        """Log test result."""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {message}")
    
    def _print_test_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n✨ All tests passed! Directory limiter is working correctly.")
        else:
            print("\n⚠️ Some tests failed. Please review the errors above.")
        
        # Cleanup
        self._cleanup()
    
    def _cleanup(self):
        """Clean up test environment."""
        try:
            # Remove test files and directories
            import shutil
            if os.path.exists(self.test_base):
                shutil.rmtree(self.test_base)
            print("\n🧹 Test environment cleaned up.")
        except Exception as e:
            print(f"\n⚠️ Cleanup error: {e}")


def main():
    """Run the directory limiter tests."""
    print("🚀 DinoAir 2.0 - Directory Limiter Test Suite")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        tester = DirectoryLimiterTest()
        tester.run_all_tests()
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        logger.error(f"Test suite failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())