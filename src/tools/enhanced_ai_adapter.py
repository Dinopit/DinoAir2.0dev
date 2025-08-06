"""
Enhanced Tool AI Adapter with Hardened Execution Pipeline

This module provides an enhanced adapter that integrates the hardened tool
dispatcher for bulletproof tool execution with comprehensive error handling
and validation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .ai_adapter import ToolAIAdapter, ToolFormatter, StandardToolFormatter
from .hardened_tool_dispatcher import (
    HardenedToolDispatcher, ToolExecutionConfig
)
from .registry import ToolRegistry
from .control.tool_context import ExecutionContext

logger = logging.getLogger(__name__)


class EnhancedToolAIAdapter(ToolAIAdapter):
    """
    Enhanced Tool AI Adapter with hardened execution pipeline
    
    This adapter extends the standard ToolAIAdapter with:
    - Hardened tool execution with comprehensive error handling
    - Advanced parameter validation and sanitization
    - Execution timeouts and resource limits
    - Detailed logging and metrics
    - Fallback mechanisms for failed tools
    - Tool usage analytics and recommendations
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        formatter: Optional[ToolFormatter] = None,
        execution_config: Optional[ToolExecutionConfig] = None,
        enable_analytics: bool = True
    ):
        """
        Initialize the enhanced adapter
        
        Args:
            registry: Tool registry instance
            formatter: Tool formatter
            execution_config: Execution configuration
            enable_analytics: Whether to enable usage analytics
        """
        # Initialize base adapter
        super().__init__(
            registry=registry,
            formatter=formatter or StandardToolFormatter(),
            enable_policies=False,  # Handled by dispatcher
            enable_restrictions=False  # Handled by dispatcher
        )
        
        # Initialize hardened dispatcher
        self.dispatcher = HardenedToolDispatcher(
            registry=self.registry,
            config=execution_config or ToolExecutionConfig()
        )
        
        self.enable_analytics = enable_analytics
        self._tool_analytics: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            "EnhancedToolAIAdapter initialized with hardened execution"
        )
    
    def execute_tool_enhanced(
        self,
        invocation: Dict[str, Any],
        track_history: bool = True,
        validate_params: bool = True,
        context: Optional[ExecutionContext] = None,
        invocation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool using the hardened execution pipeline
        
        Args:
            invocation: Tool invocation data
            track_history: Whether to track in execution history
            validate_params: Whether to validate parameters
            context: Execution context
            invocation_id: Unique invocation identifier
            
        Returns:
            Enhanced execution result with comprehensive metadata
        """
        start_time = datetime.now()
        
        try:
            # Parse invocation
            parsed = self.formatter.parse_invocation(invocation)
            tool_name = parsed["tool_name"]
            parameters = parsed["parameters"]
            metadata = parsed.get("metadata", {})
            
            # Generate invocation ID if not provided
            if not invocation_id:
                invocation_id = f"enhanced_{int(start_time.timestamp() * 1000)}"
            
            logger.info(
                f"[{invocation_id}] Enhanced tool execution: {tool_name}"
            )
            
            # Update analytics (pre-execution)
            if self.enable_analytics:
                self._update_analytics_pre_execution(tool_name)
            
            # Execute using hardened dispatcher
            result = self.dispatcher.execute_tool(
                tool_name=tool_name,
                parameters=parameters,
                context=context,
                invocation_id=invocation_id
            )
            
            # Enhance result with additional metadata
            enhanced_result = self._enhance_execution_result(
                result, tool_name, invocation_id, start_time, metadata
            )
            
            # Update analytics (post-execution)
            if self.enable_analytics:
                self._update_analytics_post_execution(
                    tool_name, enhanced_result["success"]
                )
            
            # Track history if requested
            if track_history:
                self._track_enhanced_history(
                    invocation, enhanced_result, context, invocation_id
                )
            
            logger.info(
                f"[{invocation_id}] Enhanced execution completed: "
                f"{tool_name} -> {enhanced_result['success']}"
            )
            
            return enhanced_result
            
        except Exception as e:
            error_msg = f"Enhanced tool execution failed: {str(e)}"
            logger.error(f"[{invocation_id}] {error_msg}", exc_info=True)
            
            # Update analytics for error
            tool_name_for_analytics = None
            try:
                parsed = self.formatter.parse_invocation(invocation)
                tool_name_for_analytics = parsed["tool_name"]
            except:
                pass
            
            if self.enable_analytics and tool_name_for_analytics:
                self._update_analytics_post_execution(tool_name_for_analytics, False)
            
            return self._create_enhanced_error_response(
                error_msg, invocation_id or "unknown", start_time
            )
    
    def _enhance_execution_result(
        self,
        result: Dict[str, Any],
        tool_name: str,
        invocation_id: str,
        start_time: datetime,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance execution result with additional metadata
        
        Args:
            result: Original execution result
            tool_name: Tool name
            invocation_id: Invocation identifier
            start_time: Execution start time
            metadata: Additional metadata
            
        Returns:
            Enhanced execution result
        """
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()
        
        # Base enhanced result
        enhanced = {
            **result,
            "enhanced_metadata": {
                "invocation_id": invocation_id,
                "tool_name": tool_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_execution_time": execution_duration,
                "adapter_version": "enhanced_v1.0",
                "original_metadata": metadata
            }
        }
        
        # Add tool recommendations if execution failed
        if not result.get("success", False):
            enhanced["enhanced_metadata"]["recommendations"] = (
                self._generate_failure_recommendations(tool_name, result)
            )
        
        # Add analytics insights
        if self.enable_analytics and tool_name in self._tool_analytics:
            analytics = self._tool_analytics[tool_name]
            enhanced["enhanced_metadata"]["analytics"] = {
                "usage_count": analytics.get("usage_count", 0),
                "success_rate": analytics.get("success_rate", 0.0),
                "avg_execution_time": analytics.get("avg_execution_time", 0.0),
                "last_success": analytics.get("last_success"),
                "trending": self._calculate_tool_trend(tool_name)
            }
        
        return enhanced
    
    def _generate_failure_recommendations(
        self, 
        tool_name: str, 
        result: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for failed tool executions
        
        Args:
            tool_name: Tool name
            result: Execution result
            
        Returns:
            List of recommendations
        """
        recommendations = []
        error_type = result.get("error_type", "unknown")
        
        if error_type == "tool_not_found":
            # Suggest similar tools
            available_tools = self.dispatcher.list_available_tools()
            tool_names = [t["name"] for t in available_tools]
            suggestion = self.dispatcher._suggest_similar_tool(
                tool_name, tool_names
            )
            if suggestion:
                recommendations.append(f"Try using '{suggestion}' instead")
            recommendations.append("Use list_available_tools to see all options")
            
        elif error_type == "parameter_error":
            recommendations.append(
                f"Check the parameter requirements for '{tool_name}'"
            )
            recommendations.append("Verify all required parameters are provided")
            recommendations.append("Check parameter types and formats")
            
        elif error_type == "timeout_error":
            recommendations.append("Try breaking the request into smaller parts")
            recommendations.append("Reduce the complexity of the operation")
            recommendations.append("Check if the tool is experiencing issues")
            
        elif error_type == "execution_error":
            recommendations.append("Verify the input data is valid")
            recommendations.append("Check if required resources are available")
            recommendations.append("Try again after a short delay")
        
        return recommendations
    
    def _update_analytics_pre_execution(self, tool_name: str):
        """Update analytics before tool execution"""
        if tool_name not in self._tool_analytics:
            self._tool_analytics[tool_name] = {
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "last_used": None,
                "last_success": None,
                "last_failure": None,
                "execution_history": []
            }
        
        analytics = self._tool_analytics[tool_name]
        analytics["usage_count"] += 1
        analytics["last_used"] = datetime.now().isoformat()
    
    def _update_analytics_post_execution(self, tool_name: str, success: bool):
        """Update analytics after tool execution"""
        if tool_name not in self._tool_analytics:
            return
        
        analytics = self._tool_analytics[tool_name]
        
        if success:
            analytics["success_count"] += 1
            analytics["last_success"] = datetime.now().isoformat()
        else:
            analytics["failure_count"] += 1
            analytics["last_failure"] = datetime.now().isoformat()
        
        # Update success rate
        total_attempts = analytics["success_count"] + analytics["failure_count"]
        analytics["success_rate"] = analytics["success_count"] / total_attempts
        
        # Keep execution history (last 10 attempts)
        analytics["execution_history"].append({
            "timestamp": datetime.now().isoformat(),
            "success": success
        })
        if len(analytics["execution_history"]) > 10:
            analytics["execution_history"] = analytics["execution_history"][-10:]
    
    def _calculate_tool_trend(self, tool_name: str) -> str:
        """
        Calculate tool usage trend
        
        Args:
            tool_name: Tool name
            
        Returns:
            Trend indicator: "improving", "declining", "stable"
        """
        if tool_name not in self._tool_analytics:
            return "stable"
        
        history = self._tool_analytics[tool_name].get("execution_history", [])
        if len(history) < 5:
            return "stable"
        
        # Analyze recent success rate vs overall
        recent_successes = sum(1 for h in history[-5:] if h["success"])
        recent_rate = recent_successes / 5
        overall_rate = self._tool_analytics[tool_name]["success_rate"]
        
        if recent_rate > overall_rate + 0.1:
            return "improving"
        elif recent_rate < overall_rate - 0.1:
            return "declining"
        else:
            return "stable"
    
    def _track_enhanced_history(
        self,
        invocation: Dict[str, Any],
        result: Dict[str, Any],
        context: Optional[ExecutionContext],
        invocation_id: str
    ):
        """Track enhanced execution history"""
        history_entry = {
            "invocation_id": invocation_id,
            "invocation": invocation,
            "result": result,
            "context": context.to_dict() if context else None,
            "timestamp": datetime.now().isoformat(),
            "enhanced": True
        }
        
        self._execution_history.append(history_entry)
        
        # Keep only last 100 entries
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
    
    def _create_enhanced_error_response(
        self,
        error_msg: str,
        invocation_id: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Create enhanced error response"""
        end_time = datetime.now()
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": "adapter_error",
            "enhanced_metadata": {
                "invocation_id": invocation_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_execution_time": (end_time - start_time).total_seconds(),
                "adapter_version": "enhanced_v1.0",
                "recommendations": [
                    "Check the tool invocation format",
                    "Verify tool name and parameters",
                    "Review system logs for details"
                ]
            }
        }
    
    def get_tool_analytics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get tool usage analytics
        
        Args:
            tool_name: Specific tool name (None for all tools)
            
        Returns:
            Analytics data
        """
        if tool_name:
            return self._tool_analytics.get(tool_name, {})
        else:
            return {
                "total_tools_used": len(self._tool_analytics),
                "tool_analytics": self._tool_analytics,
                "summary": self._generate_analytics_summary()
            }
    
    def _generate_analytics_summary(self) -> Dict[str, Any]:
        """Generate summary analytics"""
        if not self._tool_analytics:
            return {"message": "No analytics data available"}
        
        total_usage = sum(
            analytics["usage_count"] 
            for analytics in self._tool_analytics.values()
        )
        
        most_used = max(
            self._tool_analytics.items(),
            key=lambda x: x[1]["usage_count"]
        )
        
        highest_success_rate = max(
            self._tool_analytics.items(),
            key=lambda x: x[1]["success_rate"]
        )
        
        return {
            "total_executions": total_usage,
            "unique_tools_used": len(self._tool_analytics),
            "most_used_tool": {
                "name": most_used[0],
                "usage_count": most_used[1]["usage_count"]
            },
            "most_reliable_tool": {
                "name": highest_success_rate[0],
                "success_rate": highest_success_rate[1]["success_rate"]
            }
        }
    
    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get dispatcher execution statistics"""
        return self.dispatcher.get_execution_stats()
    
    def refresh_tool_registry(self):
        """Refresh the tool registry and cache"""
        self.dispatcher.refresh_tool_cache()
        logger.info("Tool registry refreshed")
    
    def recommend_tools_enhanced(
        self,
        task_description: str,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get enhanced tool recommendations with analytics
        
        Args:
            task_description: Description of the task
            max_recommendations: Maximum recommendations to return
            
        Returns:
            Enhanced tool recommendations
        """
        # Get base recommendations
        base_recommendations = super().recommend_tools_for_task(
            task_description, 
            max_recommendations=max_recommendations
        )
        
        # Enhance with analytics
        for rec in base_recommendations:
            tool_name = rec["name"]
            if tool_name in self._tool_analytics:
                analytics = self._tool_analytics[tool_name]
                rec["enhanced_score"] = (
                    rec.get("score", 0.5) * 0.7 +  # Base score weight
                    analytics["success_rate"] * 0.3   # Success rate weight
                )
                rec["analytics"] = {
                    "usage_count": analytics["usage_count"],
                    "success_rate": analytics["success_rate"],
                    "trending": self._calculate_tool_trend(tool_name)
                }
            else:
                rec["enhanced_score"] = rec.get("score", 0.5)
                rec["analytics"] = {"status": "no_usage_data"}
        
        # Re-sort by enhanced score
        base_recommendations.sort(
            key=lambda x: x["enhanced_score"], 
            reverse=True
        )
        
        return base_recommendations


def create_enhanced_adapter(
    registry: Optional[ToolRegistry] = None,
    execution_timeout: float = 30.0,
    max_retries: int = 2,
    enable_analytics: bool = True
) -> EnhancedToolAIAdapter:
    """
    Factory function to create an enhanced tool adapter
    
    Args:
        registry: Tool registry instance
        execution_timeout: Maximum execution time per tool
        max_retries: Maximum retry attempts
        enable_analytics: Whether to enable usage analytics
        
    Returns:
        Configured enhanced adapter
    """
    config = ToolExecutionConfig(
        max_execution_time=execution_timeout,
        max_retries=max_retries,
        enable_parameter_validation=True,
        enable_error_recovery=True,
        enable_detailed_logging=True,
        fallback_response_enabled=True
    )
    
    return EnhancedToolAIAdapter(
        registry=registry,
        execution_config=config,
        enable_analytics=enable_analytics
    )