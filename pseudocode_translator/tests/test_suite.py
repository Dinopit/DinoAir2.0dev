"""
Comprehensive Test Suite Runner for Pseudocode Translator

This module provides a unified test runner with coverage reporting,
test categorization, and multiple execution profiles.
"""

import os
import sys
import time
import json
import argparse
import unittest
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import coverage
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False
    print("Warning: coverage module not available. Install with: pip install coverage")


@dataclass
class TestCategory:
    """Represents a category of tests"""
    name: str
    pattern: str
    description: str
    modules: List[str]


@dataclass
class TestProfile:
    """Represents a test execution profile"""
    name: str
    categories: List[str]
    timeout: Optional[int]
    parallel: bool
    coverage: bool
    verbosity: int


@dataclass
class TestResult:
    """Enhanced test result with metadata"""
    test_name: str
    category: str
    status: str  # 'pass', 'fail', 'error', 'skip'
    duration: float
    message: Optional[str] = None


class TestSuiteRunner:
    """Comprehensive test suite runner with advanced features"""
    
    # Define test categories
    CATEGORIES = {
        'unit': TestCategory(
            name='unit',
            pattern='test_*.py',
            description='Unit tests for individual components',
            modules=[
                'test_validator_modern_syntax',
                'test_parser_ast_based',
                'test_models',
                'test_config_validator',
                'test_assembler',
                'test_utils',
                'test_prompts',
                'test_llm_interface',
                'test_ast_cache',
            ]
        ),
        'integration': TestCategory(
            name='integration',
            pattern='test_integration_*.py',
            description='Integration tests for component interactions',
            modules=[
                'test_integration_modern_syntax',
                'test_streaming',
                'test_configuration',
                'test_end_to_end',
            ]
        ),
        'performance': TestCategory(
            name='performance',
            pattern='test_performance*.py',
            description='Performance and optimization tests',
            modules=[
                'test_performance',
                'test_parallel_processor',
            ]
        ),
        'error_handling': TestCategory(
            name='error_handling',
            pattern='test_error*.py',
            description='Error handling and recovery tests',
            modules=[
                'test_error_handling',
                'test_regression',
            ]
        ),
        'cli': TestCategory(
            name='cli',
            pattern='test_cli*.py',
            description='Command-line interface tests',
            modules=[
                'test_cli',
            ]
        ),
    }
    
    # Define test profiles
    PROFILES = {
        'quick': TestProfile(
            name='quick',
            categories=['unit'],
            timeout=60,
            parallel=True,
            coverage=False,
            verbosity=1
        ),
        'full': TestProfile(
            name='full',
            categories=['unit', 'integration', 'error_handling', 'cli'],
            timeout=300,
            parallel=False,
            coverage=True,
            verbosity=2
        ),
        'ci': TestProfile(
            name='ci',
            categories=['unit', 'integration', 'error_handling'],
            timeout=180,
            parallel=True,
            coverage=True,
            verbosity=2
        ),
        'performance': TestProfile(
            name='performance',
            categories=['performance'],
            timeout=600,
            parallel=False,
            coverage=False,
            verbosity=2
        ),
        'all': TestProfile(
            name='all',
            categories=['unit', 'integration', 'performance', 'error_handling', 'cli'],
            timeout=None,
            parallel=False,
            coverage=True,
            verbosity=2
        ),
    }
    
    def __init__(self, profile: str = 'full', output_format: str = 'console'):
        """
        Initialize the test suite runner
        
        Args:
            profile: Test execution profile
            output_format: Output format ('console', 'json', 'html')
        """
        self.profile = self.PROFILES.get(profile, self.PROFILES['full'])
        self.output_format = output_format
        self.test_dir = Path(__file__).parent
        self.results: List[TestResult] = []
        self.coverage_data = None
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging for test runs"""
        log_level = logging.DEBUG if self.profile.verbosity > 1 else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('test_suite.log', mode='w')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def discover_tests(self) -> Dict[str, unittest.TestSuite]:
        """
        Discover tests based on the current profile
        
        Returns:
            Dictionary mapping category names to test suites
        """
        self.logger.info(f"Discovering tests for profile: {self.profile.name}")
        category_suites = {}
        
        for category_name in self.profile.categories:
            category = self.CATEGORIES.get(category_name)
            if not category:
                self.logger.warning(f"Unknown category: {category_name}")
                continue
                
            # Create test suite for this category
            suite = unittest.TestSuite()
            
            # Load tests from specified modules
            for module_name in category.modules:
                try:
                    # Try to import the module
                    module_path = self.test_dir / f"{module_name}.py"
                    if module_path.exists():
                        # Use unittest's test discovery
                        loader = unittest.TestLoader()
                        module_suite = loader.discover(
                            str(self.test_dir),
                            pattern=f"{module_name}.py"
                        )
                        suite.addTests(module_suite)
                        self.logger.debug(f"Loaded tests from {module_name}")
                    else:
                        self.logger.warning(f"Test module not found: {module_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load {module_name}: {e}")
                    
            category_suites[category_name] = suite
            
        return category_suites
        
    def run_tests(self) -> Tuple[int, int, int]:
        """
        Run all discovered tests
        
        Returns:
            Tuple of (passed, failed, errors)
        """
        start_time = time.time()
        
        # Start coverage if enabled
        if self.profile.coverage and COVERAGE_AVAILABLE:
            self.coverage_data = coverage.Coverage(
                source=['pseudocode_translator'],
                omit=['*/tests/*', '*/test_*']
            )
            self.coverage_data.start()
            
        # Discover tests
        category_suites = self.discover_tests()
        
        # Run tests by category
        total_passed = 0
        total_failed = 0
        total_errors = 0
        
        for category_name, suite in category_suites.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Running {category_name} tests")
            self.logger.info(f"{'='*60}")
            
            # Create test runner with appropriate verbosity
            runner = unittest.TextTestRunner(
                verbosity=self.profile.verbosity,
                stream=sys.stdout
            )
            
            # Run the test suite
            result = runner.run(suite)
            
            # Process results
            passed = result.testsRun - len(result.failures) - len(result.errors)
            failed = len(result.failures)
            errors = len(result.errors)
            
            total_passed += passed
            total_failed += failed
            total_errors += errors
            
            # Store detailed results
            self._process_test_results(result, category_name)
            
        # Stop coverage and generate report
        if self.profile.coverage and COVERAGE_AVAILABLE and self.coverage_data:
            self.coverage_data.stop()
            self._generate_coverage_report()
            
        # Generate test report
        duration = time.time() - start_time
        self._generate_test_report(total_passed, total_failed, total_errors, duration)
        
        return total_passed, total_failed, total_errors
        
    def _process_test_results(self, result: unittest.TestResult, category: str):
        """Process and store test results"""
        # Process successful tests
        for test in result.testsRun:
            if test not in [t[0] for t in result.failures + result.errors]:
                self.results.append(TestResult(
                    test_name=str(test),
                    category=category,
                    status='pass',
                    duration=0.0  # unittest doesn't provide individual test duration
                ))
                
        # Process failures
        for test, traceback in result.failures:
            self.results.append(TestResult(
                test_name=str(test),
                category=category,
                status='fail',
                duration=0.0,
                message=traceback
            ))
            
        # Process errors
        for test, traceback in result.errors:
            self.results.append(TestResult(
                test_name=str(test),
                category=category,
                status='error',
                duration=0.0,
                message=traceback
            ))
            
        # Process skipped tests
        for test, reason in result.skipped:
            self.results.append(TestResult(
                test_name=str(test),
                category=category,
                status='skip',
                duration=0.0,
                message=reason
            ))
            
    def _generate_coverage_report(self):
        """Generate coverage report"""
        if not self.coverage_data:
            return
            
        self.logger.info("\n" + "="*60)
        self.logger.info("Coverage Report")
        self.logger.info("="*60)
        
        # Generate console report
        self.coverage_data.report()
        
        # Generate HTML report
        html_dir = self.test_dir / 'coverage_html'
        self.coverage_data.html_report(directory=str(html_dir))
        self.logger.info(f"HTML coverage report generated in: {html_dir}")
        
        # Get coverage percentage
        coverage_percent = self.coverage_data.report(show_missing=False)
        self.logger.info(f"Overall coverage: {coverage_percent:.1f}%")
        
    def _generate_test_report(self, passed: int, failed: int, errors: int, duration: float):
        """Generate comprehensive test report"""
        total = passed + failed + errors
        
        # Console report
        if self.output_format == 'console':
            print("\n" + "="*60)
            print("Test Suite Summary")
            print("="*60)
            print(f"Profile: {self.profile.name}")
            print(f"Total tests: {total}")
            print(f"Passed: {passed} ({passed/total*100:.1f}%)")
            print(f"Failed: {failed}")
            print(f"Errors: {errors}")
            print(f"Duration: {duration:.2f}s")
            print("="*60)
            
            # Category breakdown
            category_stats = defaultdict(lambda: {'pass': 0, 'fail': 0, 'error': 0, 'skip': 0})
            for result in self.results:
                category_stats[result.category][result.status] += 1
                
            print("\nCategory Breakdown:")
            for category, stats in category_stats.items():
                total_cat = sum(stats.values())
                print(f"\n{category}:")
                print(f"  Total: {total_cat}")
                print(f"  Passed: {stats['pass']} ({stats['pass']/total_cat*100:.1f}%)")
                print(f"  Failed: {stats['fail']}")
                print(f"  Errors: {stats['error']}")
                print(f"  Skipped: {stats['skip']}")
                
        # JSON report
        elif self.output_format == 'json':
            report = {
                'profile': self.profile.name,
                'duration': duration,
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'errors': errors,
                },
                'categories': {},
                'tests': []
            }
            
            # Add category stats
            category_stats = defaultdict(lambda: {'pass': 0, 'fail': 0, 'error': 0, 'skip': 0})
            for result in self.results:
                category_stats[result.category][result.status] += 1
                report['tests'].append({
                    'name': result.test_name,
                    'category': result.category,
                    'status': result.status,
                    'duration': result.duration,
                    'message': result.message
                })
                
            report['categories'] = dict(category_stats)
            
            # Write JSON report
            report_path = self.test_dir / 'test_report.json'
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"JSON report written to: {report_path}")
            
    def run_single_test(self, test_path: str):
        """Run a single test file or test method"""
        self.logger.info(f"Running single test: {test_path}")
        
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(test_path)
        
        runner = unittest.TextTestRunner(verbosity=self.profile.verbosity)
        result = runner.run(suite)
        
        return result.wasSuccessful()


def main():
    """Main entry point for the test suite runner"""
    parser = argparse.ArgumentParser(
        description='Comprehensive test suite runner for Pseudocode Translator'
    )
    parser.add_argument(
        '--profile', '-p',
        choices=list(TestSuiteRunner.PROFILES.keys()),
        default='full',
        help='Test execution profile'
    )
    parser.add_argument(
        '--output', '-o',
        choices=['console', 'json', 'html'],
        default='console',
        help='Output format for test results'
    )
    parser.add_argument(
        '--test', '-t',
        help='Run a single test file or test method'
    )
    parser.add_argument(
        '--list-categories', '-l',
        action='store_true',
        help='List available test categories'
    )
    parser.add_argument(
        '--category', '-c',
        help='Run only tests from a specific category'
    )
    
    args = parser.parse_args()
    
    # List categories if requested
    if args.list_categories:
        print("Available test categories:")
        for name, category in TestSuiteRunner.CATEGORIES.items():
            print(f"\n{name}:")
            print(f"  Description: {category.description}")
            print(f"  Modules: {', '.join(category.modules)}")
        return
        
    # Create custom profile if category specified
    if args.category:
        if args.category not in TestSuiteRunner.CATEGORIES:
            print(f"Error: Unknown category '{args.category}'")
            print(f"Available categories: {', '.join(TestSuiteRunner.CATEGORIES.keys())}")
            return
            
        # Create custom profile for single category
        profile = TestProfile(
            name=f'custom_{args.category}',
            categories=[args.category],
            timeout=300,
            parallel=False,
            coverage=True,
            verbosity=2
        )
        TestSuiteRunner.PROFILES['custom'] = profile
        args.profile = 'custom'
        
    # Create and run test suite
    runner = TestSuiteRunner(profile=args.profile, output_format=args.output)
    
    if args.test:
        # Run single test
        success = runner.run_single_test(args.test)
        sys.exit(0 if success else 1)
    else:
        # Run full test suite
        passed, failed, errors = runner.run_tests()
        
        # Exit with appropriate code
        sys.exit(0 if (failed == 0 and errors == 0) else 1)


if __name__ == '__main__':
    main()