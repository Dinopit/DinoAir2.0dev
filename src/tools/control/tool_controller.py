"""
Tool Selection Controller

This module provides the main controller for tool selection and
policy enforcement. It integrates policies, context, and tool
registry to make intelligent tool selections.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ..base import BaseTool, ToolCategory

if TYPE_CHECKING:
    from ..registry import ToolRegistry
from ..policies.tool_policy import (
    BaseToolPolicy, PolicyResult, PolicyDecision,
    AllowListPolicy, DenyListPolicy, CategoryPolicy,
    CapabilityPolicy
)


logger = logging.getLogger(__name__)


@dataclass
class ToolScore:
    """Score for a tool based on various factors"""
    tool_name: str
    base_score: float
    policy_score: float
    context_score: float
    capability_score: float
    total_score: float
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSelectionResult:
    """Result of tool selection process"""
    selected_tools: List[str]
    scores: Dict[str, ToolScore]
    filtered_out: Dict[str, str]  # tool_name -> reason
    selection_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ToolController:
    """
    Main controller for tool selection and policy enforcement
    
    This controller manages:
    - Policy evaluation and enforcement
    - Tool filtering based on context
    - Tool recommendation and scoring
    - Usage tracking and logging
    """
    
    def __init__(
        self,
        registry: Optional['ToolRegistry'] = None,
        default_policies: Optional[List[BaseToolPolicy]] = None
    ):
        """
        Initialize the tool controller
        
        Args:
            registry: Tool registry instance
            default_policies: Default policies to apply
        """
        if registry is None:
            from ..registry import ToolRegistry
            registry = ToolRegistry()
        self.registry = registry
        self._policies: List[BaseToolPolicy] = default_policies or []
        self._policy_cache: Dict[str, PolicyResult] = {}
        self._selection_history: List[ToolSelectionResult] = []
        self._usage_stats: Dict[str, int] = defaultdict(int)
        self._enabled = True
        
    def add_policy(self, policy: BaseToolPolicy):
        """Add a policy to the controller"""
        if policy not in self._policies:
            self._policies.append(policy)
            self._clear_policy_cache()
            logger.info(f"Added policy: {policy.name}")
            
    def remove_policy(self, policy: BaseToolPolicy):
        """Remove a policy from the controller"""
        if policy in self._policies:
            self._policies.remove(policy)
            self._clear_policy_cache()
            logger.info(f"Removed policy: {policy.name}")
            
    def set_policies(self, policies: List[BaseToolPolicy]):
        """Replace all policies"""
        self._policies = policies.copy()
        self._clear_policy_cache()
        logger.info(f"Set {len(policies)} policies")
        
    def _clear_policy_cache(self):
        """Clear the policy evaluation cache"""
        self._policy_cache.clear()
        
    def evaluate_tool(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Tuple[bool, List[PolicyResult]]:
        """
        Evaluate a tool against all policies
        
        Args:
            tool: Tool to evaluate
            context: Evaluation context
            use_cache: Whether to use cached results
            
        Returns:
            Tuple of (is_allowed, policy_results)
        """
        if not self._enabled:
            return True, []
            
        cache_key = f"{tool.name}:{hash(str(context))}"
        
        # Check cache
        if use_cache and cache_key in self._policy_cache:
            cached_result = self._policy_cache[cache_key]
            return cached_result.is_allowed, [cached_result]
            
        # Evaluate all policies
        results = []
        for policy in self._policies:
            if policy.is_enabled:
                result = policy.evaluate(tool, context)
                results.append(result)
                
                # Early exit on deny for efficiency
                if result.is_denied:
                    logger.debug(
                        f"Tool '{tool.name}' denied by policy "
                        f"'{policy.name}': {result.reason}"
                    )
                    # Cache the denial
                    if use_cache:
                        self._policy_cache[cache_key] = result
                    return False, results
                    
        # All policies passed
        is_allowed = all(
            r.is_allowed or r.decision == PolicyDecision.NEUTRAL
            for r in results
        )
        
        # Cache the final result
        if use_cache and results:
            self._policy_cache[cache_key] = results[-1]
            
        return is_allowed, results
        
    def filter_tools(
        self,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, BaseTool]:
        """
        Filter available tools based on policies and criteria
        
        Args:
            context: Evaluation context
            category: Filter by category
            tags: Filter by tags
            
        Returns:
            Dictionary of allowed tools
        """
        # Get tools from registry
        tool_infos = self.registry.list_tools(
            category=category,
            tags=tags,
            enabled_only=True
        )
        
        allowed_tools = {}
        
        for info in tool_infos:
            tool = self.registry.get_tool(info["name"])
            if tool:
                is_allowed, _ = self.evaluate_tool(tool, context)
                if is_allowed:
                    allowed_tools[tool.name] = tool
                    
        logger.info(
            f"Filtered {len(allowed_tools)} allowed tools from "
            f"{len(tool_infos)} available"
        )
        
        return allowed_tools
        
    def recommend_tools(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        max_recommendations: int = 5,
        min_score: float = 0.0
    ) -> ToolSelectionResult:
        """
        Recommend tools based on task and context
        
        Args:
            task_description: Description of the task
            context: Task context
            max_recommendations: Maximum number of recommendations
            min_score: Minimum score threshold
            
        Returns:
            Tool selection result with recommendations
        """
        start_time = datetime.now()
        
        # Get filtered tools
        allowed_tools = self.filter_tools(context)
        
        # Score each tool
        scores = {}
        filtered_out = {}
        
        for tool_name, tool in allowed_tools.items():
            # Calculate score
            score = self._calculate_tool_score(
                tool, task_description, context
            )
            
            if score.total_score >= min_score:
                scores[tool_name] = score
            else:
                filtered_out[tool_name] = (
                    f"Score too low: {score.total_score:.2f}"
                )
                
        # Sort by score
        sorted_tools = sorted(
            scores.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )[:max_recommendations]
        
        # Create result
        result = ToolSelectionResult(
            selected_tools=[name for name, _ in sorted_tools],
            scores=scores,
            filtered_out=filtered_out,
            selection_time=(
                datetime.now() - start_time
            ).total_seconds(),
            metadata={
                "task_description": task_description,
                "context": context,
                "total_evaluated": len(allowed_tools),
                "max_recommendations": max_recommendations,
                "min_score": min_score
            }
        )
        
        # Track selection
        self._selection_history.append(result)
        for tool_name in result.selected_tools:
            self._usage_stats[tool_name] += 1
            
        return result
        
    def _calculate_tool_score(
        self,
        tool: BaseTool,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolScore:
        """Calculate score for a tool"""
        reasons = []
        
        # Base score from metadata
        base_score = 0.5
        if tool.metadata:
            # Check description relevance
            task_lower = task_description.lower()
            desc_lower = tool.metadata.description.lower()
            name_lower = tool.name.lower()
            
            # Name match
            if name_lower in task_lower:
                base_score += 0.3
                reasons.append("Tool name matches task")
                
            # Description keywords
            desc_words = set(desc_lower.split())
            task_words = set(task_lower.split())
            common_words = desc_words & task_words
            if common_words:
                base_score += min(0.2 * len(common_words), 0.4)
                reasons.append(
                    f"Description matches: {', '.join(common_words)}"
                )
                
        # Policy score (based on evaluation confidence)
        policy_score = 0.5
        is_allowed, results = self.evaluate_tool(tool, context)
        if is_allowed:
            # Strong allow decisions boost score
            allow_count = sum(
                1 for r in results
                if r.decision == PolicyDecision.ALLOW
            )
            policy_score += 0.1 * allow_count
            if allow_count > 0:
                reasons.append(f"{allow_count} policies explicitly allow")
                
        # Context score
        context_score = 0.5
        if context:
            # Check for context-specific requirements
            required_capabilities = context.get(
                "required_capabilities", []
            )
            if required_capabilities and tool.metadata:
                tool_caps = set(tool.metadata.capabilities.keys())
                required_caps = set(required_capabilities)
                matched = tool_caps & required_caps
                if matched:
                    context_score += 0.2 * len(matched)
                    reasons.append(
                        f"Matches capabilities: {', '.join(matched)}"
                    )
                    
            # Previous usage in similar context
            if "user" in context and tool.name in self._usage_stats:
                context_score += min(
                    0.1 * self._usage_stats[tool.name] / 10, 0.3
                )
                reasons.append("Previously used successfully")
                
        # Capability score
        capability_score = 0.5
        if tool.metadata and tool.metadata.capabilities:
            # More capabilities generally means more versatile
            cap_count = len(tool.metadata.capabilities)
            capability_score += min(0.05 * cap_count, 0.3)
            
            # Specific high-value capabilities
            high_value_caps = {
                "async", "batch", "streaming", "caching"
            }
            tool_caps = set(tool.metadata.capabilities.keys())
            valuable = tool_caps & high_value_caps
            if valuable:
                capability_score += 0.1 * len(valuable)
                reasons.append(
                    f"High-value capabilities: {', '.join(valuable)}"
                )
                
        # Calculate total score
        total_score = (
            base_score * 0.4 +
            policy_score * 0.3 +
            context_score * 0.2 +
            capability_score * 0.1
        )
        
        return ToolScore(
            tool_name=tool.name,
            base_score=base_score,
            policy_score=policy_score,
            context_score=context_score,
            capability_score=capability_score,
            total_score=total_score,
            reasons=reasons,
            metadata={
                "category": (
                    tool.metadata.category.value
                    if tool.metadata else None
                ),
                "tags": (
                    tool.metadata.tags
                    if tool.metadata else []
                )
            }
        )
        
    def select_tool(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Select a single best tool for a task
        
        Args:
            task_description: Task description
            context: Task context
            
        Returns:
            Selected tool name or None
        """
        result = self.recommend_tools(
            task_description,
            context,
            max_recommendations=1
        )
        
        if result.selected_tools:
            return result.selected_tools[0]
        return None
        
    def can_use_tool(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Check if a specific tool can be used
        
        Args:
            tool_name: Name of the tool
            context: Usage context
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
            
        is_allowed, results = self.evaluate_tool(tool, context)
        
        if is_allowed:
            return True, "Tool usage allowed"
        else:
            # Find first denial reason
            for result in results:
                if result.is_denied:
                    return False, result.reason
            return False, "Tool usage denied"
            
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of active policies"""
        return {
            "total_policies": len(self._policies),
            "enabled_policies": sum(
                1 for p in self._policies if p.is_enabled
            ),
            "policies": [
                {
                    "name": p.name,
                    "description": p.description,
                    "enabled": p.is_enabled,
                    "stats": p.get_statistics()
                }
                for p in self._policies
            ]
        }
        
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        return {
            "total_selections": len(self._selection_history),
            "unique_tools_used": len(self._usage_stats),
            "most_used_tools": sorted(
                self._usage_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "recent_selections": [
                {
                    "timestamp": sel.timestamp.isoformat(),
                    "selected": sel.selected_tools,
                    "selection_time": sel.selection_time
                }
                for sel in self._selection_history[-10:]
            ]
        }
        
    def clear_cache(self):
        """Clear all caches"""
        self._policy_cache.clear()
        logger.info("Cleared policy cache")
        
    def reset_statistics(self):
        """Reset usage statistics"""
        self._selection_history.clear()
        self._usage_stats.clear()
        logger.info("Reset usage statistics")
        
    def enable(self):
        """Enable the controller"""
        self._enabled = True
        
    def disable(self):
        """Disable the controller (allows all tools)"""
        self._enabled = False
        
    @property
    def is_enabled(self) -> bool:
        """Check if controller is enabled"""
        return self._enabled


class PolicyBasedToolController(ToolController):
    """
    Tool controller with built-in common policies
    
    This controller includes pre-configured policies for
    common use cases.
    """
    
    def __init__(
        self,
        registry: Optional['ToolRegistry'] = None,
        safe_mode: bool = True,
        allowed_tools: Optional[List[str]] = None,
        denied_tools: Optional[List[str]] = None
    ):
        """
        Initialize with common policies
        
        Args:
            registry: Tool registry
            safe_mode: Enable safe mode policies
            allowed_tools: Explicit allow list
            denied_tools: Explicit deny list
        """
        super().__init__(registry)
        
        # Add common policies
        if safe_mode:
            self._add_safe_mode_policies()
            
        if allowed_tools:
            self.add_policy(
                AllowListPolicy(allowed_tools, "ExplicitAllowList")
            )
            
        if denied_tools:
            self.add_policy(
                DenyListPolicy(denied_tools, "ExplicitDenyList")
            )
            
    def _add_safe_mode_policies(self):
        """Add safe mode policies"""
        # Deny dangerous categories
        self.add_policy(CategoryPolicy(
            denied_categories=[
                ToolCategory.SYSTEM,
                ToolCategory.DEBUG
            ],
            name="SafeModeCategoryPolicy"
        ))
        
        # Deny dangerous capabilities
        self.add_policy(CapabilityPolicy(
            forbidden_capabilities=[
                "file_delete",
                "system_execute",
                "network_access"
            ],
            name="SafeModeCapabilityPolicy"
        ))
        
    def enable_developer_mode(self):
        """Enable developer mode (relaxed policies)"""
        # Remove safe mode policies
        self._policies = [
            p for p in self._policies
            if not p.name.startswith("SafeMode")
        ]
        self._clear_policy_cache()
        logger.info("Enabled developer mode")
        
    def enable_production_mode(self):
        """Enable production mode (strict policies)"""
        self._add_safe_mode_policies()
        
        # Add additional production policies
        self.add_policy(CapabilityPolicy(
            forbidden_capabilities=[
                "debug",
                "test",
                "mock"
            ],
            name="ProductionCapabilityPolicy"
        ))
        
        logger.info("Enabled production mode")