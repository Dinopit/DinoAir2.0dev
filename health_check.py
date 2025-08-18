#!/usr/bin/env python3
"""
DinoAir Health Check CLI
Simple command-line health check for DinoAir components
"""

import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import Logger
from src.utils.config_loader import ConfigLoader


def check_basic_components() -> Dict[str, Any]:
    """Check basic DinoAir components"""
    results = {
        "timestamp": time.time(),
        "status": "healthy",
        "checks": {}
    }
    
    logger = Logger()
    
    # Check logger
    try:
        logger.info("Health check: Testing logger")
        results["checks"]["logger"] = {
            "status": "healthy",
            "message": "Logger working correctly"
        }
    except Exception as e:
        results["checks"]["logger"] = {
            "status": "unhealthy", 
            "message": f"Logger error: {e}"
        }
        results["status"] = "unhealthy"
    
    # Check configuration
    try:
        config = ConfigLoader()
        app_name = config.get("app.name", "Unknown")
        results["checks"]["config"] = {
            "status": "healthy",
            "message": f"Config loaded: {app_name}"
        }
    except Exception as e:
        results["checks"]["config"] = {
            "status": "unhealthy",
            "message": f"Config error: {e}"
        }
        results["status"] = "unhealthy"
    
    # Check database directories
    try:
        db_path = Path("src/user_data/default/databases")
        if db_path.exists():
            results["checks"]["database_path"] = {
                "status": "healthy",
                "message": f"Database path exists: {db_path}"
            }
        else:
            results["checks"]["database_path"] = {
                "status": "degraded",
                "message": f"Database path missing: {db_path}"
            }
    except Exception as e:
        results["checks"]["database_path"] = {
            "status": "unhealthy",
            "message": f"Database check error: {e}"
        }
        if results["status"] == "healthy":
            results["status"] = "degraded"
    
    # Check imports
    import_checks = [
        ("PySide6", "GUI framework"),
        ("src.utils.logger", "Logger utility"),
        ("src.gui.components.signal_coordinator", "Signal coordinator")
    ]
    
    for module_name, description in import_checks:
        try:
            __import__(module_name)
            results["checks"][f"import_{module_name.replace('.', '_')}"] = {
                "status": "healthy",
                "message": f"{description} import successful"
            }
        except ImportError as e:
            results["checks"][f"import_{module_name.replace('.', '_')}"] = {
                "status": "unhealthy",
                "message": f"{description} import failed: {e}"
            }
            results["status"] = "unhealthy"
    
    return results


def print_health_report(results: Dict[str, Any]) -> None:
    """Print formatted health report"""
    status = results["status"]
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(results["timestamp"]))
    
    print("=" * 60)
    print("DinoAir Health Check Report")
    print("=" * 60)
    print(f"Timestamp: {timestamp}")
    print(f"Overall Status: {status.upper()}")
    print()
    
    status_symbols = {
        "healthy": "✅",
        "degraded": "⚠️ ",
        "unhealthy": "❌",
        "unknown": "❓"
    }
    
    print("Component Checks:")
    print("-" * 40)
    
    for check_name, check_result in results["checks"].items():
        symbol = status_symbols.get(check_result["status"], "❓")
        print(f"{symbol} {check_name.replace('_', ' ').title()}")
        print(f"   {check_result['message']}")
        print()
    
    print("=" * 60)
    
    if status == "healthy":
        print("🎉 All systems operational!")
    elif status == "degraded":
        print("⚠️  Some issues detected but system functional")
    else:
        print("🚨 Critical issues found - system may not function properly")


def main():
    """Main health check function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DinoAir Health Check")
    parser.add_argument("--json", action="store_true", 
                       help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true",
                       help="Only show overall status")
    
    args = parser.parse_args()
    
    try:
        # Suppress logging noise in quiet mode to output only the status
        if args.quiet:
            logging.disable(logging.CRITICAL)
        results = check_basic_components()
        
        if args.json:
            print(json.dumps(results, indent=2))
        elif args.quiet:
            print(results["status"])
        else:
            print_health_report(results)
        
        # Exit with appropriate code
        if results["status"] == "healthy":
            sys.exit(0)
        elif results["status"] == "degraded":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        error_result = {
            "timestamp": time.time(),
            "status": "critical",
            "error": str(e)
        }
        
        if args.json:
            print(json.dumps(error_result, indent=2))
        else:
            print(f"❌ Health check failed: {e}")
        
        sys.exit(3)


if __name__ == "__main__":
    main()