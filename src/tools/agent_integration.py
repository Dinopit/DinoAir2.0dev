"""
Agent Integration Module for Hardened Tool Execution

This module provides integration patches and enhancements for OllamaAgent
to use the hardened tool execution pipeline with comprehensive error handling
and validation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .enhanced_ai_adapter import EnhancedToolAIAdapter, create_enhanced_adapter
from .hardened_tool_dispatcher import ToolExecutionConfig
from .registry import ToolRegistry
from .control.tool_context import ExecutionContext, UserContext, TaskContext, EnvironmentContext

logger = logging.getLogger(__name__)


class HardenedToolExecutionMixin:
    """
    Mixin to add hardened tool execution capabilities to agents
    
    This mixin can be applied to any agent class to enhance it with
    bulletproof tool execution, comprehensive error handling, and
    advanced analytics.
    """
    
    def __init_hardened_tools__(
        self,
        execution_timeout: float = 30.0,
        max_retries: int = 2,
        enable_analytics: bool = True,
        registry: Optional[ToolRegistry] = None
    ):
        """
        Initialize hardened tool execution system
        
        Args:
            execution_timeout: Maximum execution time per tool
            max_retries: Maximum retry attempts
            enable_analytics: Whether to enable usage analytics
            registry: Tool registry instance
        """
        self.enhanced_tool_adapter = create_enhanced_adapter(
            registry=registry or ToolRegistry(),
            execution_timeout=execution_timeout,
            max_retries=max_retries,
            enable_analytics=enable_analytics
        )
        
        # Override standard tool adapter if it exists
        if hasattr(self, 'tool_adapter'):
            self._original_tool_adapter = self.tool_adapter
            
        logger.info("Hardened tool execution system initialized")
    
    def execute_tool_hardened(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        invocation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool using the hardened execution pipeline
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Execution context
            invocation_id: Unique invocation identifier
            
        Returns:
            Enhanced execution result
        """
        # Create invocation dict
        invocation = {
            "name": tool_name,
            "parameters": parameters
        }
        
        # Create execution context
        execution_context = self._create_execution_context_from_dict(context)
        
        # Execute using enhanced adapter
        return self.enhanced_tool_adapter.execute_tool_enhanced(
            invocation=invocation,
            context=execution_context,
            invocation_id=invocation_id
        )
    
    def _create_execution_context_from_dict(
        self, 
        context_dict: Optional[Dict[str, Any]]
    ) -> Optional[ExecutionContext]:
        """
        Create ExecutionContext from dictionary
        
        Args:
            context_dict: Context dictionary
            
        Returns:
            ExecutionContext instance or None
        """
        if not context_dict:
            return None
            
        try:
            # Extract context components
            user_info = context_dict.get('user', {})
            task_info = context_dict.get('task', {})
            env_info = context_dict.get('environment', {})
            
            # Create context objects
            user_context = UserContext(
                user_id=user_info.get('user_id', 'default'),
                role=user_info.get('role', 'user'),
                preferences=user_info.get('preferences', {})
            )
            
            task_context = TaskContext(
                task_id=task_info.get('task_id', f"task_{int(datetime.now().timestamp())}"),
                task_type=task_info.get('task_type', 'general'),
                description=task_info.get('description', 'General task'),
                priority=task_info.get('priority', 5),
                metadata=task_info.get('metadata', {})
            )
            
            environment_context = EnvironmentContext(
                environment=env_info.get('environment', 'local'),
                resources=env_info.get('resources', {}),
                restrictions=set(env_info.get('restrictions', [])),
                capabilities=set(env_info.get('capabilities', [])),
                metadata=env_info.get('metadata', {})
            )
            
            return ExecutionContext(
                user=user_context,
                task=task_context,
                environment=environment_context
            )
            
        except Exception as e:
            logger.warning(f"Failed to create execution context: {e}")
            return None
    
    def get_hardened_tool_stats(self) -> Dict[str, Any]:
        """Get comprehensive tool execution statistics"""
        return {
            "analytics": self.enhanced_tool_adapter.get_tool_analytics(),
            "dispatcher_stats": self.enhanced_tool_adapter.get_dispatcher_stats(),
            "available_tools": len(self.enhanced_tool_adapter.list_available_tools())
        }
    
    def list_available_tools_enhanced(self) -> List[Dict[str, Any]]:
        """Get enhanced list of available tools with analytics"""
        return self.enhanced_tool_adapter.dispatcher.list_available_tools()
    
    def refresh_tool_system(self):
        """Refresh the entire tool system"""
        self.enhanced_tool_adapter.refresh_tool_registry()
        logger.info("Tool system refreshed")


def patch_ollama_agent(agent_class):
    """
    Class decorator to patch OllamaAgent with hardened tool execution
    
    This decorator adds hardened tool execution capabilities to the
    OllamaAgent class while maintaining backward compatibility.
    
    Args:
        agent_class: OllamaAgent class to patch
        
    Returns:
        Enhanced OllamaAgent class
    """
    class HardenedOllamaAgent(agent_class, HardenedToolExecutionMixin):
        """
        Enhanced OllamaAgent with hardened tool execution pipeline
        """
        
        def __init__(self, *args, **kwargs):
            # Extract hardened tool configuration
            execution_timeout = kwargs.pop('execution_timeout', 30.0)
            max_retries = kwargs.pop('max_retries', 2)
            enable_analytics = kwargs.pop('enable_analytics', True)
            
            # Initialize base agent
            super().__init__(*args, **kwargs)
            
            # Initialize hardened tools
            self.__init_hardened_tools__(
                execution_timeout=execution_timeout,
                max_retries=max_retries,
                enable_analytics=enable_analytics,
                registry=getattr(self, 'tool_registry', None)
            )
        
        async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            """
            Override the tool execution method with hardened execution
            
            This method replaces the original _execute_tool method to use
            the hardened execution pipeline while maintaining the same interface.
            """
            try:
                # Create invocation ID for tracking
                invocation_id = f"ollama_{int(datetime.now().timestamp() * 1000)}"
                
                # Use hardened execution
                result = self.execute_tool_hardened(
                    tool_name=tool_name,
                    parameters=parameters,
                    context=self._get_current_context_dict(),
                    invocation_id=invocation_id
                )
                
                # Convert enhanced result to expected format
                if result.get("success", False):
                    return {
                        "success": True,
                        "result": result.get("output", {}),
                        "metadata": result.get("enhanced_metadata", {}),
                        "execution_time": result.get("execution_time_ms", 0) / 1000.0
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                        "error_type": result.get("error_type", "execution_error"),
                        "recommendations": result.get("enhanced_metadata", {}).get("recommendations", []),
                        "metadata": result.get("enhanced_metadata", {})
                    }
                    
            except Exception as e:
                logger.error(f"Hardened tool execution failed: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Tool execution failed: {str(e)}",
                    "error_type": "system_error"
                }
        
        def _get_current_context_dict(self) -> Dict[str, Any]:
            """
            Get current execution context as dictionary
            
            Returns:
                Context dictionary for tool execution
            """
            return {
                "user": {
                    "user_id": "ollama_user",
                    "role": "user",
                    "preferences": {}
                },
                "task": {
                    "task_id": f"ollama_task_{int(datetime.now().timestamp())}",
                    "task_type": "general",
                    "description": "Ollama agent tool execution",
                    "priority": 5,
                    "metadata": {}
                },
                "environment": {
                    "environment": "local",
                    "resources": {},
                    "restrictions": [],
                    "capabilities": ["tool_execution", "local_access"],
                    "metadata": {"agent_type": "ollama"}
                }
            }
        
        def get_tool_execution_stats(self) -> Dict[str, Any]:
            """Get comprehensive tool execution statistics"""
            return self.get_hardened_tool_stats()
        
        def validate_all_tools(self) -> Dict[str, Any]:
            """
            Validate that all 31 tools are properly mapped and executable
            
            Returns:
                Validation results for all tools
            """
            logger.info("Starting comprehensive tool validation...")
            
            available_tools = self.list_available_tools_enhanced()
            validation_results = {
                "total_tools": len(available_tools),
                "validated_tools": [],
                "failed_tools": [],
                "validation_summary": {}
            }
            
            for tool_info in available_tools:
                tool_name = tool_info["name"]
                
                try:
                    # Test basic tool metadata access
                    if not tool_info.get("description"):
                        raise ValueError("Missing tool description")
                    
                    # Test tool instantiation
                    tool_instance = self.enhanced_tool_adapter.registry.get_tool(tool_name)
                    if not tool_instance:
                        raise ValueError("Tool not instantiable")
                    
                    # Test tool readiness
                    if not tool_instance.is_ready:
                        raise ValueError(f"Tool not ready: {tool_instance.status}")
                    
                    validation_results["validated_tools"].append({
                        "name": tool_name,
                        "status": "valid",
                        "description": tool_info.get("description", ""),
                        "category": tool_info.get("category", "unknown"),
                        "usage_stats": {
                            "total_calls": tool_info.get("total_calls", 0),
                            "success_rate": tool_info.get("success_rate", 0.0)
                        }
                    })
                    
                except Exception as e:
                    validation_results["failed_tools"].append({
                        "name": tool_name,
                        "status": "failed",
                        "error": str(e)
                    })
                    logger.warning(f"Tool validation failed for '{tool_name}': {e}")
            
            # Generate summary
            validation_results["validation_summary"] = {
                "total_tools": len(available_tools),
                "valid_tools": len(validation_results["validated_tools"]),
                "failed_tools": len(validation_results["failed_tools"]),
                "success_rate": (
                    len(validation_results["validated_tools"]) / len(available_tools)
                    if available_tools else 0.0
                ),
                "validation_timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"Tool validation completed: {validation_results['validation_summary']['valid_tools']}"
                f"/{validation_results['validation_summary']['total_tools']} tools valid"
            )
            
            return validation_results
    
    return HardenedOllamaAgent


def create_hardened_ollama_agent(*args, **kwargs):
    """
    Factory function to create a hardened OllamaAgent
    
    This function creates an OllamaAgent with hardened tool execution
    capabilities enabled by default.
    """
    # Import here to avoid circular imports
    from ..agents.ollama_agent import OllamaAgent
    
    # Patch the agent class
    HardenedOllamaAgent = patch_ollama_agent(OllamaAgent)
    
    # Create and return the enhanced agent
    return HardenedOllamaAgent(*args, **kwargs)


# Utility functions for tool system validation
def validate_tool_registry_mapping() -> Dict[str, Any]:
    """
    Validate that all tools in AVAILABLE_TOOLS are properly mapped
    
    Returns:
        Validation results for tool registry mapping
    """
    logger.info("Validating tool registry mapping...")
    
    try:
        # Import required modules
        from .basic_tools import AVAILABLE_TOOLS
        from .registry import ToolRegistry
        
        registry = ToolRegistry()
        results = {
            "available_tools_count": len(AVAILABLE_TOOLS),
            "registry_tools_count": len(registry.list_tools()),
            "mapping_status": {},
            "missing_tools": [],
            "extra_tools": [],
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Get tools from registry
        registry_tools = {tool["name"] for tool in registry.list_tools()}
        available_tool_names = set(AVAILABLE_TOOLS.keys())
        
        # Check for missing tools
        missing_tools = available_tool_names - registry_tools
        results["missing_tools"] = list(missing_tools)
        
        # Check for extra tools
        extra_tools = registry_tools - available_tool_names
        results["extra_tools"] = list(extra_tools)
        
        # Validate each tool mapping
        for tool_name in AVAILABLE_TOOLS:
            try:
                tool_instance = registry.get_tool(tool_name)
                if tool_instance:
                    results["mapping_status"][tool_name] = {
                        "status": "mapped",
                        "ready": tool_instance.is_ready,
                        "metadata_available": tool_instance.metadata is not None
                    }
                else:
                    results["mapping_status"][tool_name] = {
                        "status": "not_mapped",
                        "ready": False,
                        "metadata_available": False
                    }
            except Exception as e:
                results["mapping_status"][tool_name] = {
                    "status": "error",
                    "error": str(e),
                    "ready": False,
                    "metadata_available": False
                }
        
        # Calculate summary statistics
        mapped_tools = sum(1 for status in results["mapping_status"].values() 
                          if status["status"] == "mapped")
        ready_tools = sum(1 for status in results["mapping_status"].values() 
                         if status.get("ready", False))
        
        results["summary"] = {
            "total_available_tools": len(AVAILABLE_TOOLS),
            "mapped_tools": mapped_tools,
            "ready_tools": ready_tools,
            "mapping_success_rate": mapped_tools / len(AVAILABLE_TOOLS),
            "readiness_rate": ready_tools / len(AVAILABLE_TOOLS)
        }
        
        logger.info(f"Tool registry validation completed: {mapped_tools}/{len(AVAILABLE_TOOLS)} tools mapped")
        return results
        
    except Exception as e:
        logger.error(f"Tool registry validation failed: {e}")
        return {
            "error": str(e),
            "validation_timestamp": datetime.now().isoformat()
        }


def run_comprehensive_tool_test() -> Dict[str, Any]:
    """
    Run comprehensive test of the hardened tool execution pipeline
    
    Returns:
        Comprehensive test results
    """
    logger.info("Starting comprehensive tool execution test...")
    
    try:
        # Create test agent
        agent = create_hardened_ollama_agent()
        
        # Initialize agent
        init_success = False
        try:
            # Try async initialization
            import asyncio
            init_success = asyncio.run(agent.initialize())
        except:
            # Fallback to sync initialization if available
            if hasattr(agent, 'initialize_sync'):
                init_success = agent.initialize_sync()
            else:
                init_success = True  # Assume success if no explicit init
        
        if not init_success:
            return {
                "error": "Failed to initialize test agent",
                "test_timestamp": datetime.now().isoformat()
            }
        
        # Validate all tools
        validation_results = agent.validate_all_tools()
        
        # Test tool execution pipeline
        test_results = {
            "pipeline_test": _test_tool_execution_pipeline(agent),
            "validation_results": validation_results,
            "registry_mapping": validate_tool_registry_mapping(),
            "execution_stats": agent.get_tool_execution_stats(),
            "test_timestamp": datetime.now().isoformat()
        }
        
        logger.info("Comprehensive tool test completed successfully")
        return test_results
        
    except Exception as e:
        logger.error(f"Comprehensive tool test failed: {e}")
        return {
            "error": str(e),
            "test_timestamp": datetime.now().isoformat()
        }


def _test_tool_execution_pipeline(agent) -> Dict[str, Any]:
    """Test the tool execution pipeline with sample tools"""
    logger.info("Testing tool execution pipeline...")
    
    # Test cases for different types of tools
    test_cases = [
        {
            "name": "add_two_numbers",
            "parameters": {"a": 5.0, "b": 3.0},
            "expected_success": True
        },
        {
            "name": "get_current_time", 
            "parameters": {},
            "expected_success": True
        },
        {
            "name": "nonexistent_tool",
            "parameters": {},
            "expected_success": False
        }
    ]
    
    results = {
        "test_cases": [],
        "summary": {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "error_handling_working": True
        }
    }
    
    for test_case in test_cases:
        try:
            result = agent.execute_tool_hardened(
                tool_name=test_case["name"],
                parameters=test_case["parameters"]
            )
            
            test_passed = (
                result.get("success", False) == test_case["expected_success"]
            )
            
            results["test_cases"].append({
                "tool_name": test_case["name"],
                "expected_success": test_case["expected_success"],
                "actual_success": result.get("success", False),
                "test_passed": test_passed,
                "execution_time": result.get("enhanced_metadata", {}).get("total_execution_time", 0),
                "error": result.get("error") if not result.get("success") else None
            })
            
            if test_passed:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
                
        except Exception as e:
            results["test_cases"].append({
                "tool_name": test_case["name"],
                "expected_success": test_case["expected_success"],
                "actual_success": False,
                "test_passed": False,
                "error": str(e)
            })
            results["summary"]["failed"] += 1
            results["summary"]["error_handling_working"] = False
    
    logger.info(f"Pipeline test completed: {results['summary']['passed']}/{results['summary']['total_tests']} passed")
    return results