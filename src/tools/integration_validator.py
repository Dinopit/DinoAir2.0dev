"""
Tool Integration Validator

This module provides comprehensive validation and diagnostic tools to verify
that AI models can properly discover and use the 31 tools from basic_tools.py
through the registry and AI adapter integration.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .registry import ToolRegistry
from .ai_adapter import ToolAIAdapter
from .basic_tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class ToolIntegrationValidator:
    """
    Comprehensive validator for tool integration pipeline
    
    This class validates:
    1. Tool registry auto-population
    2. AI adapter tool discovery
    3. Tool context injection
    4. AI model tool awareness
    """
    
    def __init__(self):
        """Initialize the validator"""
        self.registry = ToolRegistry()
        self.ai_adapter = ToolAIAdapter(registry=self.registry)
        self.validation_results: Dict[str, Any] = {}
        
    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run complete validation of tool integration pipeline
        
        Returns:
            Comprehensive validation results
        """
        logger.info("Starting full tool integration validation...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "basic_tools_count": len(AVAILABLE_TOOLS),
            "validations": {}
        }
        
        # 1. Validate registry auto-population
        results["validations"]["registry_population"] = (
            self._validate_registry_population()
        )
        
        # 2. Validate AI adapter tool discovery
        results["validations"]["ai_adapter_discovery"] = (
            self._validate_ai_adapter_discovery()
        )
        
        # 3. Validate tool context injection
        results["validations"]["context_injection"] = (
            self._validate_context_injection()
        )
        
        # 4. Validate tool execution pipeline
        results["validations"]["execution_pipeline"] = (
            self._validate_execution_pipeline()
        )
        
        # 5. Generate AI model awareness test
        results["validations"]["ai_model_awareness"] = (
            self._generate_ai_awareness_test()
        )
        
        # Calculate overall success
        validations = results["validations"]
        successful_validations = sum(
            1 for v in validations.values() if v.get("success", False)
        )
        total_validations = len(validations)
        
        results["overall_success"] = successful_validations == total_validations
        results["success_rate"] = successful_validations / total_validations
        
        self.validation_results = results
        
        # Log summary
        if results["overall_success"]:
            logger.info("✓ All tool integration validations passed!")
        else:
            logger.warning(
                f"⚠ {total_validations - successful_validations}/"
                f"{total_validations} validations failed"
            )
        
        return results
    
    def _validate_registry_population(self) -> Dict[str, Any]:
        """
        Validate that the registry is properly populated with basic tools
        
        Returns:
            Validation results for registry population
        """
        try:
            # Get all registered tools
            registered_tools = self.registry.list_tools()
            registered_names = {tool["name"] for tool in registered_tools}
            
            # Check if basic tools are registered
            expected_tools = set(AVAILABLE_TOOLS.keys())
            missing_tools = expected_tools - registered_names
            extra_tools = registered_names - expected_tools
            
            success = len(missing_tools) == 0
            
            return {
                "success": success,
                "expected_count": len(expected_tools),
                "registered_count": len(registered_names),
                "missing_tools": list(missing_tools),
                "extra_tools": list(extra_tools),
                "correctly_registered": list(expected_tools & registered_names),
                "message": (
                    "All basic tools successfully registered" if success
                    else f"Missing {len(missing_tools)} tools from registry"
                )
            }
            
        except Exception as e:
            logger.error(f"Registry population validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to validate registry population"
            }
    
    def _validate_ai_adapter_discovery(self) -> Dict[str, Any]:
        """
        Validate that AI adapter can discover tools from registry
        
        Returns:
            Validation results for AI adapter discovery
        """
        try:
            # Get available tools through AI adapter
            available_tools = self.ai_adapter.get_available_tools()
            discovered_names = {tool["name"] for tool in available_tools}
            
            # Check discovery completeness
            expected_tools = set(AVAILABLE_TOOLS.keys())
            missing_from_adapter = expected_tools - discovered_names
            
            success = len(missing_from_adapter) == 0
            
            # Test different format types
            format_tests = {}
            for format_type in ["standard", "function_calling"]:
                try:
                    formatted_tools = self.ai_adapter.get_available_tools(
                        format_type=format_type
                    )
                    format_tests[format_type] = {
                        "success": True,
                        "count": len(formatted_tools)
                    }
                except Exception as e:
                    format_tests[format_type] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "success": success,
                "discovered_count": len(discovered_names),
                "missing_from_adapter": list(missing_from_adapter),
                "discovered_tools": list(discovered_names),
                "format_tests": format_tests,
                "message": (
                    "AI adapter successfully discovered all tools" if success
                    else f"AI adapter missing {len(missing_from_adapter)} tools"
                )
            }
            
        except Exception as e:
            logger.error(f"AI adapter discovery validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to validate AI adapter discovery"
            }
    
    def _validate_context_injection(self) -> Dict[str, Any]:
        """
        Validate tool context injection for AI models
        
        Returns:
            Validation results for context injection
        """
        try:
            # Test context prompt generation
            context_prompt = self.ai_adapter.get_context_prompt(
                include_tools=True,
                include_history=True
            )
            
            # Verify prompt contains tool information
            expected_tools = list(AVAILABLE_TOOLS.keys())
            tools_in_prompt = []
            
            for tool_name in expected_tools:
                if tool_name in context_prompt:
                    tools_in_prompt.append(tool_name)
            
            tools_missing_from_prompt = set(expected_tools) - set(tools_in_prompt)
            
            # Test comprehensive context generation
            comprehensive_context = (
                self.ai_adapter.generate_tool_context_prompt(
                    include_categories=True,
                    include_capabilities=True,
                    include_examples=True
                )
            )
            
            success = len(tools_missing_from_prompt) == 0
            
            return {
                "success": success,
                "context_prompt_length": len(context_prompt),
                "comprehensive_context_length": len(comprehensive_context),
                "tools_in_prompt": len(tools_in_prompt),
                "tools_missing_from_prompt": list(tools_missing_from_prompt),
                "prompt_contains_tools": len(tools_in_prompt) > 0,
                "message": (
                    "Context injection working correctly" if success
                    else f"{len(tools_missing_from_prompt)} tools missing from context"
                )
            }
            
        except Exception as e:
            logger.error(f"Context injection validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to validate context injection"
            }
    
    def _validate_execution_pipeline(self) -> Dict[str, Any]:
        """
        Validate tool execution through AI adapter
        
        Returns:
            Validation results for execution pipeline
        """
        try:
            # Test execution of a simple tool
            test_execution = {
                "name": "add_two_numbers",
                "parameters": {"a": 5.0, "b": 3.0}
            }
            
            result = self.ai_adapter.execute_tool(test_execution)
            
            execution_success = result.get("success", False)
            
            # Test parameter validation
            validation_test = {
                "name": "add_two_numbers",
                "parameters": {"a": "invalid", "b": 3.0}
            }
            
            validation_result = self.ai_adapter.execute_tool(validation_test)
            validation_correctly_failed = not validation_result.get("success", True)
            
            success = execution_success and validation_correctly_failed
            
            return {
                "success": success,
                "test_execution_success": execution_success,
                "validation_correctly_failed": validation_correctly_failed,
                "test_result": result,
                "validation_result": validation_result,
                "message": (
                    "Execution pipeline working correctly" if success
                    else "Issues with tool execution pipeline"
                )
            }
            
        except Exception as e:
            logger.error(f"Execution pipeline validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to validate execution pipeline"
            }
    
    def _generate_ai_awareness_test(self) -> Dict[str, Any]:
        """
        Generate comprehensive AI model awareness test data
        
        Returns:
            Test data for validating AI model tool awareness
        """
        try:
            # Generate formatted tool descriptions for AI models
            available_tools = self.ai_adapter.get_available_tools()
            
            # Create different format tests
            formats = {
                "standard": self.ai_adapter.get_available_tools(
                    format_type="standard"
                ),
                "function_calling": self.ai_adapter.get_available_tools(
                    format_type="function_calling"
                )
            }
            
            # Generate context prompts
            context_prompts = {
                "basic": self.ai_adapter.get_context_prompt(),
                "comprehensive": self.ai_adapter.generate_tool_context_prompt()
            }
            
            # Create sample tool invocations
            sample_invocations = self._create_sample_invocations()
            
            return {
                "success": True,
                "available_tools_count": len(available_tools),
                "format_tests": {
                    name: {"count": len(tools), "sample": tools[:2]}
                    for name, tools in formats.items()
                },
                "context_prompt_lengths": {
                    name: len(prompt)
                    for name, prompt in context_prompts.items()
                },
                "sample_invocations": sample_invocations,
                "tool_categories": self._get_tool_categories(),
                "message": "AI awareness test data generated successfully"
            }
            
        except Exception as e:
            logger.error(f"AI awareness test generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate AI awareness test"
            }
    
    def _create_sample_invocations(self) -> List[Dict[str, Any]]:
        """
        Create sample tool invocations for testing AI model understanding
        
        Returns:
            List of sample invocations
        """
        samples = [
            {
                "name": "add_two_numbers",
                "parameters": {"a": 10.0, "b": 5.0},
                "description": "Basic math operation"
            },
            {
                "name": "get_current_time",
                "parameters": {},
                "description": "Get current timestamp"
            },
            {
                "name": "list_directory_contents",
                "parameters": {"path": "."},
                "description": "List current directory"
            },
            {
                "name": "create_json_data",
                "parameters": {
                    "data": {"test": True, "value": 42}
                },
                "description": "Create JSON data structure"
            }
        ]
        
        return samples
    
    def _get_tool_categories(self) -> Dict[str, List[str]]:
        """
        Get tools grouped by category
        
        Returns:
            Dictionary mapping categories to tool lists
        """
        tools = self.ai_adapter.get_available_tools()
        categories = {}
        
        for tool in tools:
            category = tool.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool["name"])
        
        return categories
    
    def print_validation_report(self):
        """Print a human-readable validation report"""
        if not self.validation_results:
            print("No validation results available. Run run_full_validation() first.")
            return
        
        results = self.validation_results
        
        print("\n" + "=" * 60)
        print("TOOL INTEGRATION VALIDATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Basic Tools Count: {results['basic_tools_count']}")
        print(f"Overall Success: {'✓' if results['overall_success'] else '✗'}")
        print(f"Success Rate: {results['success_rate']:.1%}")
        print()
        
        for validation_name, validation_result in results["validations"].items():
            status = "✓" if validation_result.get("success", False) else "✗"
            message = validation_result.get("message", "No message")
            
            print(f"{status} {validation_name.replace('_', ' ').title()}")
            print(f"   {message}")
            
            if not validation_result.get("success", False) and "error" in validation_result:
                print(f"   Error: {validation_result['error']}")
            print()
        
        print("=" * 60)
    
    def save_validation_results(self, filepath: str):
        """
        Save validation results to JSON file
        
        Args:
            filepath: Path to save results
        """
        if not self.validation_results:
            logger.warning("No validation results to save")
            return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, default=str)
            logger.info(f"Validation results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save validation results: {e}")


def run_integration_validation() -> Dict[str, Any]:
    """
    Convenience function to run full integration validation
    
    Returns:
        Validation results
    """
    validator = ToolIntegrationValidator()
    results = validator.run_full_validation()
    validator.print_validation_report()
    return results


def create_ai_awareness_diagnostic() -> str:
    """
    Create diagnostic information for AI model tool awareness
    
    Returns:
        Formatted diagnostic string for AI models
    """
    validator = ToolIntegrationValidator()
    
    # Get available tools
    tools = validator.ai_adapter.get_available_tools()
    
    diagnostic = f"""
# AI Model Tool Awareness Diagnostic

## System Status
- Registry Tools: {len(validator.registry.list_tools())}
- Available Tools: {len(tools)}
- Expected Tools: {len(AVAILABLE_TOOLS)}

## Available Tool Categories
"""
    
    categories = validator._get_tool_categories()
    for category, tool_list in categories.items():
        diagnostic += f"\n### {category.title()}\n"
        for tool in tool_list:
            diagnostic += f"- {tool}\n"
    
    diagnostic += "\n## Sample Tool Descriptions\n"
    
    for tool in tools[:5]:  # Show first 5 tools
        diagnostic += f"\n### {tool['name']}\n"
        diagnostic += f"**Description**: {tool['description']}\n"
        diagnostic += f"**Category**: {tool.get('category', 'unknown')}\n"
        
        if tool.get('parameters'):
            diagnostic += "**Parameters**:\n"
            for param_name, param_info in tool['parameters'].items():
                required = param_name in tool.get('required', [])
                req_str = " (required)" if required else " (optional)"
                diagnostic += f"- {param_name}{req_str}: {param_info.get('description', 'No description')}\n"
    
    return diagnostic


if __name__ == "__main__":
    # Run validation when script is executed directly
    run_integration_validation()