#!/usr/bin/env python3
"""
DinoAir Health Check CLI
Simple command-line health check for DinoAir components
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import Logger
from src.utils.config_loader import ConfigLoader


def check_basic_components() -> Dict[str, Any]:
    """
    Perform a set of basic health checks for core DinoAir components and return an aggregated result.
    
    Checks performed:
    - Logger: attempts to emit a test log entry.
    - Configuration: attempts to load application configuration and read `app.name`.
    - Database path: verifies existence of `src/user_data/default/databases` (missing path is considered "degraded").
    - Imports: attempts to import key modules (PySide6, src.utils.logger, src.gui.components.signal_coordinator).
    
    Returns:
        Dict[str, Any]: A dictionary with the following keys:
            - timestamp (float): Epoch time when the checks were run.
            - status (str): Aggregate status ("healthy", "degraded", or "unhealthy").
            - checks (dict): Per-check results mapping check names to objects with:
                - status (str): Check-level status ("healthy", "degraded", or "unhealthy").
                - message (str): Human-readable summary or error message.
    
    Notes:
    - The overall `status` starts as "healthy" and may be changed to "degraded" or "unhealthy" depending on individual check outcomes:
      - Import failures and configuration/logger exceptions mark the overall status "unhealthy".
      - Errors while inspecting the database path downgrade the overall status to "degraded" if it was still "healthy".
    - The function does not raise on individual check failures; errors are captured and reported in the returned structure.
    """
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
    """
    Print a human-readable DinoAir health report to stdout.
    
    Parameters:
        results (dict): Health result dictionary with the following keys:
            - timestamp (int|float): Epoch seconds used to display the report time.
            - status (str): Overall status (e.g., "healthy", "degraded", "unhealthy").
            - checks (dict): Mapping of check name -> dict with keys:
                - status (str): Check status.
                - message (str): Human-readable message describing the check result.
    
    The function formats the timestamp, prints the overall status and a list of component checks
    (each shown with a status icon and its message). This function only writes to stdout and
    does not return a value.
    """
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
    """
    Run the CLI health check, output results, and exit with an appropriate status code.
    
    This function parses command-line flags and executes the basic health checks (via check_basic_components()).
    - Flags:
      - --json: print the full results as pretty JSON.
      - --quiet: print only the overall status string.
    - Output behavior:
      - If --json, prints JSON; elif --quiet, prints results["status"]; otherwise prints a human-readable report using print_health_report().
    - Exit codes:
      - 0: overall status "healthy"
      - 1: overall status "degraded"
      - 2: any other non-exception status (e.g., "unhealthy")
      - 3: an unexpected exception occurred (prints a brief error message or JSON error object)
    
    The function terminates the process with the chosen exit code; it does not return.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="DinoAir Health Check")
    parser.add_argument("--json", action="store_true", 
                       help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true",
                       help="Only show overall status")
    
    args = parser.parse_args()
    
    try:
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