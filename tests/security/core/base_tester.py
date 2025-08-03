"""
Base security tester class for DinoAir red team testing.

Provides common functionality for all security test modules.
"""

import sys
import os
from typing import List, Dict, Tuple, Any
from datetime import datetime
from abc import ABC, abstractmethod

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.input_processing.input_sanitizer import InputPipeline, InputPipelineError
from src.input_processing.stages import (
    InputValidator, ThreatLevel, ValidationError
)


class BaseSecurityTester(ABC):
    """Abstract base class for security testing modules."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the base tester.
        
        Args:
            verbose: Whether to print detailed results
        """
        self.verbose = verbose
        self.results = {
            'total_tests': 0,
            'blocked': 0,
            'passed': 0,
            'errors': 0,
            'bypasses': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Initialize test pipeline
        self.pipeline = InputPipeline(
            gui_feedback_hook=self._mock_gui_feedback,
            skip_empty_feedback=False,
            model_type="claude"
        )
        
        # Direct validator for focused testing
        self.validator = InputValidator()
        
        self.gui_feedback_log = []
    
    def _mock_gui_feedback(self, message: str):
        """Mock GUI feedback for testing."""
        self.gui_feedback_log.append(message)
        if self.verbose:
            print(f"[GUI] {message}")
    
    @abstractmethod
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        pass
    
    @abstractmethod
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get test payloads for this category.
        
        Returns:
            List of (payload, description) tuples
        """
        pass
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all tests for this category."""
        print(f"\n🔍 Testing {self.get_test_name()}...")
        payloads = self.get_payloads()
        self._run_payload_tests(payloads, self.get_test_name())
        return self.results
    
    def _run_payload_tests(self, payloads: List[Tuple[str, str]], 
                           category: str):
        """Run a set of payload tests.
        
        Args:
            payloads: List of (payload, description) tuples
            category: Category name for reporting
        """
        category_blocked = 0
        category_passed = 0
        
        for payload, description in payloads:
            self.results['total_tests'] += 1
            
            try:
                # Test through full pipeline
                result, intent = self.pipeline.run(payload)
                
                # Also test validator directly
                validation = self.validator.validate(payload)
                
                # Check if payload was modified/sanitized
                if (result != payload or 
                    validation.threat_level.value >= 
                    ThreatLevel.MEDIUM.value):
                    self.results['blocked'] += 1
                    category_blocked += 1
                    if self.verbose:
                        print(f"  ✓ Blocked: {description}")
                else:
                    self.results['passed'] += 1
                    category_passed += 1
                    self.results['bypasses'].append({
                        'category': category,
                        'payload': payload,
                        'description': description,
                        'threat_level': validation.threat_level.name
                    })
                    print(f"  ✗ BYPASS: {description}")
                    print(f"    Payload: {repr(payload)}")
                    
            except (InputPipelineError, ValidationError) as e:
                self.results['blocked'] += 1
                category_blocked += 1
                if self.verbose:
                    print(f"  ✓ Blocked: {description} - {str(e)}")
            except Exception as e:
                self.results['errors'] += 1
                print(f"  ⚠️ ERROR: {description} - "
                      f"{type(e).__name__}: {str(e)}")
        
        print(f"  {category} Summary: {category_blocked} blocked, "
              f"{category_passed} passed")