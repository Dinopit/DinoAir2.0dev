"""
Run red team security tests with enhanced security enabled.
Tests the actual InputSanitizer with all security modules active.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Import the real InputPipeline
from src.input_processing.input_sanitizer import InputPipeline
from src.utils.logger import Logger

def run_security_tests():
    """Run security tests with actual InputSanitizer and enhanced security."""
    
    print("=" * 60)
    print("DinoAir Red Team Security Testing (Enhanced)")
    print("=" * 60)
    
    # Initialize components with enhanced security enabled
    logger = Logger()
    # Use InputPipeline instead of InputSanitizer
    pipeline = InputPipeline(
        gui_feedback_hook=lambda message: print(f"[GUI] {message}"),
        enable_enhanced_security=True,
        watchdog_ref=None,
        main_window_ref=None
    )
    
    # Test payloads
    test_categories = {
        "Path Traversal": [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\cmd.exe",
            "....//....//etc/passwd"
        ],
        "Command Injection": [
            "; whoami",
            "&& ls -la",
            "| cat /etc/passwd"
        ],
        "XSS": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src='javascript:alert(1)'>",
            "<input onfocus=alert(1) autofocus>",
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;"
        ],
        "SQL Injection": [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1' UNION SELECT * FROM passwords--",
            "admin'--",
            "' OR 1=1--",
            "1' ORDER BY 1--+",
            "' WAITFOR DELAY '00:00:10'--"
        ],
        "Unicode": [
            "admin\u200b",  # Zero-width space
            "ad\u200cmin",  # Zero-width non-joiner
            "admin\ufeff",  # Zero-width no-break space
            "аdmin",  # Cyrillic 'а'
            "аdmіn",  # Multiple Cyrillic
            "ɑdmin",  # IPA Latin alpha
            "\u202eadmin",  # Right-to-left override
            "admin\u202d",  # Left-to-right override
            "𝖺𝖽𝗆𝗂𝗇",  # Mathematical alphanumeric
            "ａｄｍｉｎ"  # Full-width
        ]
    }
    
    # Run tests
    total_tests = 0
    total_blocked = 0
    results = {}
    
    for category, payloads in test_categories.items():
        print(f"\nTesting {category}...")
        print("-" * 40)
        blocked = 0
        
        for payload in payloads:
            total_tests += 1
            try:
                # Get sanitized result using pipeline
                result, intent = pipeline.run(payload)
                
                # Check if attack was blocked
                # For enhanced security, attacks are detected and neutralized
                # The result should be different from the original payload
                if result != payload:
                    # Also check if dangerous patterns are removed
                    attack_blocked = False
                    
                    if category == "Path Traversal":
                        attack_blocked = '../' not in result and '..\\' not in result
                    elif category == "Command Injection":
                        attack_blocked = all(char not in result for char in [';', '&', '|'])
                    elif category == "XSS":
                        attack_blocked = '<script' not in result.lower() and 'javascript:' not in result.lower()
                    elif category == "SQL Injection":
                        attack_blocked = "'" in payload and ("''" in result or "'" not in result)
                    elif category == "Unicode":
                        # Check if dangerous unicode chars are removed
                        attack_blocked = all(ord(c) < 127 or c.isalnum() for c in result)
                    
                    if attack_blocked:
                        blocked += 1
                        display_payload = payload[:30] + "..." if len(payload) > 30 else payload
                        display_result = result[:30] + "..." if len(result) > 30 else result
                        print(f"  ✓ Blocked: {display_payload} → {display_result}")
                    else:
                        print(f"  ✗ Passed: {payload[:30]}...")
                else:
                    print(f"  ✗ Passed: {payload[:30]}... (unchanged)")
                    
            except Exception as e:
                print(f"  ! Error testing {payload}: {e}")
                
        total_blocked += blocked
        results[category] = {
            "total": len(payloads),
            "blocked": blocked,
            "success_rate": (blocked / len(payloads) * 100) if payloads else 0
        }
        
        print(f"\n  Summary: {blocked}/{len(payloads)} blocked ({results[category]['success_rate']:.1f}%)")
        
    # Calculate security score
    security_score = (total_blocked / total_tests * 100) if total_tests > 0 else 0
    
    # Generate report
    report = {
        "test_date": datetime.now().isoformat(),
        "total_tests": total_tests,
        "total_blocked": total_blocked,
        "security_score": round(security_score, 2),
        "categories": results,
        "enhanced_security": True,
        "recommendation": "Consider implementing more sophisticated sanitization"
        if security_score < 90 else "Excellent security posture with enhanced protection"
    }
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Enhanced Security Test Results Summary")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Blocked: {total_blocked}")
    print(f"Security Score: {security_score:.1f}%")
    print(f"\nCategory Breakdown:")
    
    for category, result in results.items():
        print(f"\n{category}:")
        print(f"  Tests: {result['total']}")
        print(f"  Blocked: {result['blocked']}")
        print(f"  Success Rate: {result['success_rate']:.1f}%")
        
    # Save report
    report_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(report_dir, f"enhanced_security_report_{timestamp}.json")
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n{'='*60}")
    print(f"Report saved to: {report_file}")
    print(f"{'='*60}")
    
    # Compare with original results if available
    print(f"\nComparison with Original Security Test:")
    print(f"{'='*60}")
    print(f"Original Results (MockInputSanitizer):")
    print(f"  - Path Traversal: 100%")
    print(f"  - Command Injection: 100%")
    print(f"  - XSS: 33.3%")
    print(f"  - SQL Injection: 66.7%")
    print(f"  - Unicode: 0%")
    print(f"  - Overall: 60%")
    print(f"\nEnhanced Results (Real InputSanitizer with Enhanced Security):")
    print(f"  - Path Traversal: {results['Path Traversal']['success_rate']:.1f}%")
    print(f"  - Command Injection: {results['Command Injection']['success_rate']:.1f}%")
    print(f"  - XSS: {results['XSS']['success_rate']:.1f}%")
    print(f"  - SQL Injection: {results['SQL Injection']['success_rate']:.1f}%")
    print(f"  - Unicode: {results['Unicode']['success_rate']:.1f}%")
    print(f"  - Overall: {security_score:.1f}%")
    print(f"{'='*60}")
    
    if security_score >= 90:
        print(f"\n✅ SUCCESS: Enhanced security implementation achieved target (>90%)")
    else:
        print(f"\n⚠️  Current score: {security_score:.1f}% (Target: >90%)")
    
    return report

if __name__ == "__main__":
    run_security_tests()