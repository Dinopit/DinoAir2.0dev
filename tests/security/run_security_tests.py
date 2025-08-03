"""
Security Test Runner for DinoAir

Orchestrates all security tests and generates comprehensive reports.
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.security.red_team_tests import RedTeamTester


class SecurityTestRunner:
    """Orchestrates security testing and reporting."""
    
    def __init__(self, output_dir: str = "tests/security/reports"):
        """Initialize test runner.
        
        Args:
            output_dir: Directory for test reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {}
        }
    
    def load_payloads(self) -> Dict[str, Any]:
        """Load attack payloads from JSON."""
        payload_file = Path(__file__).parent / "payloads" / "attack_payloads.json"
        
        if payload_file.exists():
            with open(payload_file, 'r') as f:
                return json.load(f)
        else:
            print(f"⚠️ Payload file not found: {payload_file}")
            return {}
    
    def run_red_team_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run red team security tests.
        
        Args:
            verbose: Whether to show detailed output
            
        Returns:
            Test results dictionary
        """
        print("\n🚀 Running Red Team Tests...")
        tester = RedTeamTester(verbose=verbose)
        return tester.run_all_tests()
    
    def run_focused_test(self, category: str) -> Dict[str, Any]:
        """Run tests for a specific category.
        
        Args:
            category: Test category to run
            
        Returns:
            Test results
        """
        payloads = self.load_payloads()
        
        if category not in payloads:
            print(f"❌ Unknown category: {category}")
            print(f"Available: {', '.join(payloads.keys())}")
            return {}
        
        print(f"\n🎯 Running {category} tests...")
        tester = RedTeamTester(verbose=True)
        
        # Run specific category
        category_payloads = [
            (p['vector'], p['description']) 
            for p in payloads[category]['payloads']
        ]
        
        tester._run_payload_tests(category_payloads, category)
        return tester.results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate HTML security report.
        
        Args:
            results: Test results
            
        Returns:
            Path to generated report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"security_report_{timestamp}.html"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>DinoAir Security Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #333; color: white; padding: 20px; }}
        .summary {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        .bypass {{ background: #ffcccc; }}
        .grade {{ font-size: 48px; font-weight: bold; text-align: center; }}
        .grade-a {{ color: #4CAF50; }}
        .grade-b {{ color: #8BC34A; }}
        .grade-c {{ color: #FFC107; }}
        .grade-d {{ color: #FF9800; }}
        .grade-f {{ color: #F44336; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ DinoAir Security Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {results.get('total_tests', 0)}</p>
        <p class="pass">Blocked: {results.get('blocked', 0)}</p>
        <p class="fail">Bypassed: {results.get('passed', 0)}</p>
        <p class="warning">Errors: {results.get('errors', 0)}</p>
    </div>
    
    <div class="grade grade-{self._calculate_grade(results).lower()}">
        Security Grade: {self._calculate_grade(results)}
    </div>
    
    <h2>Security Bypasses</h2>
    {self._generate_bypass_table(results.get('bypasses', []))}
    
    <h2>Recommendations</h2>
    {self._generate_recommendations(results)}
</body>
</html>
"""
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def _calculate_grade(self, results: Dict[str, Any]) -> str:
        """Calculate security grade from results."""
        total = results.get('total_tests', 0)
        blocked = results.get('blocked', 0)
        
        if total == 0:
            return "N/A"
        
        block_rate = (blocked / total) * 100
        
        if block_rate >= 99:
            return "A"
        elif block_rate >= 95:
            return "B"
        elif block_rate >= 90:
            return "C"
        elif block_rate >= 80:
            return "D"
        else:
            return "F"
    
    def _generate_bypass_table(self, bypasses: List[Dict[str, Any]]) -> str:
        """Generate HTML table of bypasses."""
        if not bypasses:
            return "<p class='pass'>✅ No security bypasses detected!</p>"
        
        html = "<table><tr><th>Category</th><th>Description</th><th>Payload</th></tr>"
        
        for bypass in bypasses[:20]:  # Show first 20
            html += f"""
            <tr class='bypass'>
                <td>{bypass.get('category', 'Unknown')}</td>
                <td>{bypass.get('description', '')}</td>
                <td><code>{self._escape_html(bypass.get('payload', ''))}</code></td>
            </tr>
            """
        
        if len(bypasses) > 20:
            html += f"<tr><td colspan='3'>... and {len(bypasses) - 20} more</td></tr>"
        
        html += "</table>"
        return html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters."""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate security recommendations."""
        recommendations = ["<ul>"]
        
        bypasses = results.get('bypasses', [])
        
        # Analyze bypass categories
        categories = {}
        for bypass in bypasses:
            cat = bypass.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        # Generate specific recommendations
        if 'Path Traversal' in categories:
            recommendations.append(
                "<li><strong>Path Traversal:</strong> Strengthen path validation "
                "and canonicalization. Consider using a whitelist approach.</li>"
            )
        
        if 'Command Injection' in categories:
            recommendations.append(
                "<li><strong>Command Injection:</strong> Implement strict input "
                "validation and avoid shell command execution.</li>"
            )
        
        if 'XSS' in categories:
            recommendations.append(
                "<li><strong>XSS:</strong> Enhance HTML escaping and implement "
                "Content Security Policy (CSP).</li>"
            )
        
        if 'Unicode' in categories:
            recommendations.append(
                "<li><strong>Unicode:</strong> Normalize Unicode input and "
                "implement homoglyph detection.</li>"
            )
        
        if not categories:
            recommendations.append(
                "<li class='pass'>Excellent security posture! Continue regular "
                "security testing and updates.</li>"
            )
        
        recommendations.append("</ul>")
        return "\n".join(recommendations)
    
    def run_all(self, categories: List[str] = None) -> None:
        """Run all security tests and generate report.
        
        Args:
            categories: Specific categories to test (None for all)
        """
        print("🛡️ DinoAir Security Testing Suite")
        print("=" * 60)
        
        if categories:
            # Run specific categories
            combined_results = {
                'total_tests': 0,
                'blocked': 0,
                'passed': 0,
                'errors': 0,
                'bypasses': []
            }
            
            for category in categories:
                results = self.run_focused_test(category)
                combined_results['total_tests'] += results.get('total_tests', 0)
                combined_results['blocked'] += results.get('blocked', 0)
                combined_results['passed'] += results.get('passed', 0)
                combined_results['errors'] += results.get('errors', 0)
                combined_results['bypasses'].extend(results.get('bypasses', []))
            
            results = combined_results
        else:
            # Run all tests
            results = self.run_red_team_tests()
        
        # Generate report
        report_path = self.generate_report(results)
        print(f"\n📄 Report generated: {report_path}")
        
        # Exit with appropriate code
        if results.get('bypasses'):
            print("\n❌ Security vulnerabilities detected!")
            sys.exit(1)
        else:
            print("\n✅ All security tests passed!")
            sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DinoAir Security Testing Suite"
    )
    parser.add_argument(
        '--categories', '-c',
        nargs='+',
        help='Specific categories to test'
    )
    parser.add_argument(
        '--output', '-o',
        default='tests/security/reports',
        help='Output directory for reports'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available test categories'
    )
    
    args = parser.parse_args()
    
    runner = SecurityTestRunner(output_dir=args.output)
    
    if args.list:
        payloads = runner.load_payloads()
        print("Available test categories:")
        for category in payloads.keys():
            print(f"  - {category}")
    else:
        runner.run_all(categories=args.categories)


if __name__ == "__main__":
    main()