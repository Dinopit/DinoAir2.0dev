"""
Tool Policy System

This module provides policy classes for controlling tool selection and usage.
Policies can be used to restrict, allow, or filter tools based on various criteria.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..base import BaseTool, ToolCategory, ToolMetadata

if TYPE_CHECKING:
    from ..registry import ToolRegistry


logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
    """Decision types for policy evaluation"""
    ALLOW = "allow"
    DENY = "deny"
    NEUTRAL = "neutral"


@dataclass
class PolicyResult:
    """Result of a policy evaluation"""
    decision: PolicyDecision
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_allowed(self) -> bool:
        """Check if the decision allows the action"""
        return self.decision == PolicyDecision.ALLOW
    
    @property
    def is_denied(self) -> bool:
        """Check if the decision denies the action"""
        return self.decision == PolicyDecision.DENY


class BaseToolPolicy(ABC):
    """
    Abstract base class for tool policies
    
    This class provides the foundation for implementing various
    tool control policies that can be used to restrict or allow
    tool usage based on different criteria.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the base policy
        
        Args:
            name: Policy name
            description: Policy description
        """
        self.name = name
        self.description = description
        self._enabled = True
        self._evaluation_count = 0
        self._last_evaluation = None
        
    @abstractmethod
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """
        Evaluate the policy for a given tool
        
        Args:
            tool: The tool to evaluate
            context: Optional context for evaluation
            
        Returns:
            PolicyResult indicating the decision
        """
        pass
    
    def can_use_tool(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Convenience method to check if a tool can be used
        
        Args:
            tool: The tool to check
            context: Optional context
            
        Returns:
            True if tool usage is allowed
        """
        if not self._enabled:
            return True
            
        result = self.evaluate(tool, context)
        self._evaluation_count += 1
        self._last_evaluation = result
        
        return result.is_allowed
    
    def enable(self):
        """Enable the policy"""
        self._enabled = True
        
    def disable(self):
        """Disable the policy"""
        self._enabled = False
        
    @property
    def is_enabled(self) -> bool:
        """Check if policy is enabled"""
        return self._enabled
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get policy statistics"""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self._enabled,
            "evaluation_count": self._evaluation_count,
            "last_evaluation": (
                self._last_evaluation.timestamp.isoformat()
                if self._last_evaluation else None
            )
        }


class AllowListPolicy(BaseToolPolicy):
    """
    Policy that only allows specific tools
    
    This policy maintains a list of allowed tool names and
    only permits usage of tools in that list.
    """
    
    def __init__(
        self,
        allowed_tools: List[str],
        name: str = "AllowListPolicy"
    ):
        """
        Initialize the allow list policy
        
        Args:
            allowed_tools: List of allowed tool names
            name: Policy name
        """
        super().__init__(
            name,
            f"Only allows tools: {', '.join(allowed_tools)}"
        )
        self._allowed_tools = set(allowed_tools)
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate if tool is in allow list"""
        if tool.name in self._allowed_tools:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason=f"Tool '{tool.name}' is in allow list",
                metadata={"allowed_tools": list(self._allowed_tools)}
            )
        else:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Tool '{tool.name}' is not in allow list",
                metadata={"allowed_tools": list(self._allowed_tools)}
            )
    
    def add_tool(self, tool_name: str):
        """Add a tool to the allow list"""
        self._allowed_tools.add(tool_name)
        self.description = f"Only allows tools: {', '.join(self._allowed_tools)}"
        
    def remove_tool(self, tool_name: str):
        """Remove a tool from the allow list"""
        self._allowed_tools.discard(tool_name)
        self.description = f"Only allows tools: {', '.join(self._allowed_tools)}"
        
    @property
    def allowed_tools(self) -> Set[str]:
        """Get the set of allowed tools"""
        return self._allowed_tools.copy()


class DenyListPolicy(BaseToolPolicy):
    """
    Policy that blocks specific tools
    
    This policy maintains a list of denied tool names and
    blocks usage of tools in that list.
    """
    
    def __init__(
        self,
        denied_tools: List[str],
        name: str = "DenyListPolicy"
    ):
        """
        Initialize the deny list policy
        
        Args:
            denied_tools: List of denied tool names
            name: Policy name
        """
        super().__init__(
            name,
            f"Blocks tools: {', '.join(denied_tools)}"
        )
        self._denied_tools = set(denied_tools)
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate if tool is in deny list"""
        if tool.name in self._denied_tools:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Tool '{tool.name}' is in deny list",
                metadata={"denied_tools": list(self._denied_tools)}
            )
        else:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason=f"Tool '{tool.name}' is not in deny list",
                metadata={"denied_tools": list(self._denied_tools)}
            )
    
    def add_tool(self, tool_name: str):
        """Add a tool to the deny list"""
        self._denied_tools.add(tool_name)
        self.description = f"Blocks tools: {', '.join(self._denied_tools)}"
        
    def remove_tool(self, tool_name: str):
        """Remove a tool from the deny list"""
        self._denied_tools.discard(tool_name)
        self.description = f"Blocks tools: {', '.join(self._denied_tools)}"
        
    @property
    def denied_tools(self) -> Set[str]:
        """Get the set of denied tools"""
        return self._denied_tools.copy()


class CategoryPolicy(BaseToolPolicy):
    """
    Policy that controls tools by category
    
    This policy allows or denies tools based on their category
    classification.
    """
    
    def __init__(
        self,
        allowed_categories: Optional[List[ToolCategory]] = None,
        denied_categories: Optional[List[ToolCategory]] = None,
        name: str = "CategoryPolicy"
    ):
        """
        Initialize the category policy
        
        Args:
            allowed_categories: Categories to allow (if None, all allowed)
            denied_categories: Categories to deny
            name: Policy name
        """
        super().__init__(name, "Controls tools by category")
        self._allowed_categories = (
            set(allowed_categories) if allowed_categories else None
        )
        self._denied_categories = (
            set(denied_categories) if denied_categories else set()
        )
        self._update_description()
        
    def _update_description(self):
        """Update policy description"""
        parts = []
        if self._allowed_categories:
            allowed = [cat.value for cat in self._allowed_categories]
            parts.append(f"Allows: {', '.join(allowed)}")
        if self._denied_categories:
            denied = [cat.value for cat in self._denied_categories]
            parts.append(f"Denies: {', '.join(denied)}")
        self.description = " | ".join(parts) if parts else "No category restrictions"
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate based on tool category"""
        if not tool.metadata:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Tool has no metadata",
                metadata={}
            )
            
        category = tool.metadata.category
        
        # Check deny list first
        if category in self._denied_categories:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Category '{category.value}' is denied",
                metadata={
                    "category": category.value,
                    "denied_categories": [c.value for c in self._denied_categories]
                }
            )
        
        # Check allow list if specified
        if self._allowed_categories:
            if category in self._allowed_categories:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    reason=f"Category '{category.value}' is allowed",
                    metadata={
                        "category": category.value,
                        "allowed_categories": [c.value for c in self._allowed_categories]
                    }
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Category '{category.value}' is not in allowed list",
                    metadata={
                        "category": category.value,
                        "allowed_categories": [c.value for c in self._allowed_categories]
                    }
                )
        
        # If no allow list and not denied, allow
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason=f"Category '{category.value}' is not restricted",
            metadata={"category": category.value}
        )
    
    def allow_category(self, category: ToolCategory):
        """Add a category to allowed list"""
        if self._allowed_categories is None:
            self._allowed_categories = set()
        self._allowed_categories.add(category)
        self._update_description()
        
    def deny_category(self, category: ToolCategory):
        """Add a category to denied list"""
        self._denied_categories.add(category)
        self._update_description()
        
    def remove_category_restriction(self, category: ToolCategory):
        """Remove category from both lists"""
        if self._allowed_categories:
            self._allowed_categories.discard(category)
        self._denied_categories.discard(category)
        self._update_description()


class CapabilityPolicy(BaseToolPolicy):
    """
    Policy that controls tools by their capabilities
    
    This policy checks tool capabilities and allows/denies
    based on required or forbidden capabilities.
    """
    
    def __init__(
        self,
        required_capabilities: Optional[List[str]] = None,
        forbidden_capabilities: Optional[List[str]] = None,
        require_all: bool = True,
        name: str = "CapabilityPolicy"
    ):
        """
        Initialize the capability policy
        
        Args:
            required_capabilities: Capabilities that must be present
            forbidden_capabilities: Capabilities that must not be present
            require_all: If True, all required capabilities must be present
            name: Policy name
        """
        super().__init__(name, "Controls tools by capabilities")
        self._required_capabilities = set(required_capabilities or [])
        self._forbidden_capabilities = set(forbidden_capabilities or [])
        self._require_all = require_all
        self._update_description()
        
    def _update_description(self):
        """Update policy description"""
        parts = []
        if self._required_capabilities:
            mode = "all" if self._require_all else "any"
            parts.append(f"Requires {mode}: {', '.join(self._required_capabilities)}")
        if self._forbidden_capabilities:
            parts.append(f"Forbids: {', '.join(self._forbidden_capabilities)}")
        self.description = " | ".join(parts) if parts else "No capability restrictions"
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate based on tool capabilities"""
        if not tool.metadata:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Tool has no metadata",
                metadata={}
            )
            
        capabilities = set(tool.metadata.capabilities.keys())
        
        # Check forbidden capabilities
        forbidden_found = self._forbidden_capabilities & capabilities
        if forbidden_found:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Tool has forbidden capabilities: {', '.join(forbidden_found)}",
                metadata={
                    "forbidden_found": list(forbidden_found),
                    "tool_capabilities": list(capabilities)
                }
            )
        
        # Check required capabilities
        if self._required_capabilities:
            if self._require_all:
                missing = self._required_capabilities - capabilities
                if missing:
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Tool missing required capabilities: {', '.join(missing)}",
                        metadata={
                            "missing_capabilities": list(missing),
                            "required_capabilities": list(self._required_capabilities),
                            "tool_capabilities": list(capabilities)
                        }
                    )
            else:
                # Require any
                if not (self._required_capabilities & capabilities):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason="Tool has none of the required capabilities",
                        metadata={
                            "required_capabilities": list(self._required_capabilities),
                            "tool_capabilities": list(capabilities)
                        }
                    )
        
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Tool capabilities meet policy requirements",
            metadata={
                "tool_capabilities": list(capabilities),
                "required_capabilities": list(self._required_capabilities),
                "forbidden_capabilities": list(self._forbidden_capabilities)
            }
        )
    
    def add_required_capability(self, capability: str):
        """Add a required capability"""
        self._required_capabilities.add(capability)
        self._update_description()
        
    def add_forbidden_capability(self, capability: str):
        """Add a forbidden capability"""
        self._forbidden_capabilities.add(capability)
        self._update_description()
        
    def remove_capability_requirement(self, capability: str):
        """Remove capability from both lists"""
        self._required_capabilities.discard(capability)
        self._forbidden_capabilities.discard(capability)
        self._update_description()


class CompositePolicy(BaseToolPolicy):
    """
    Policy that combines multiple policies
    
    This policy allows combining multiple policies with
    different logical operators (AND, OR).
    """
    
    class CombineMode(Enum):
        """How to combine policy results"""
        ALL = "all"  # All must allow (AND)
        ANY = "any"  # Any must allow (OR)
        MAJORITY = "majority"  # Majority must allow
        
    def __init__(
        self,
        policies: List[BaseToolPolicy],
        mode: CombineMode = CombineMode.ALL,
        name: str = "CompositePolicy"
    ):
        """
        Initialize the composite policy
        
        Args:
            policies: List of policies to combine
            mode: How to combine the policies
            name: Policy name
        """
        super().__init__(
            name,
            f"Combines {len(policies)} policies with {mode.value} logic"
        )
        self._policies = policies
        self._mode = mode
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate all sub-policies and combine results"""
        results = []
        for policy in self._policies:
            if policy.is_enabled:
                results.append(policy.evaluate(tool, context))
        
        if not results:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason="No enabled policies to evaluate",
                metadata={}
            )
        
        # Count decisions
        allow_count = sum(1 for r in results if r.is_allowed)
        deny_count = sum(1 for r in results if r.is_denied)
        
        # Apply combination logic
        if self._mode == self.CombineMode.ALL:
            if deny_count > 0:
                # Find first deny reason
                deny_result = next(r for r in results if r.is_denied)
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Policy '{deny_result.reason}' denied (ALL mode)",
                    metadata={
                        "mode": self._mode.value,
                        "allow_count": allow_count,
                        "deny_count": deny_count,
                        "total_policies": len(results)
                    }
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    reason="All policies allowed",
                    metadata={
                        "mode": self._mode.value,
                        "allow_count": allow_count,
                        "total_policies": len(results)
                    }
                )
                
        elif self._mode == self.CombineMode.ANY:
            if allow_count > 0:
                # Find first allow reason
                allow_result = next(r for r in results if r.is_allowed)
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    reason=f"Policy '{allow_result.reason}' allowed (ANY mode)",
                    metadata={
                        "mode": self._mode.value,
                        "allow_count": allow_count,
                        "deny_count": deny_count,
                        "total_policies": len(results)
                    }
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason="No policies allowed",
                    metadata={
                        "mode": self._mode.value,
                        "deny_count": deny_count,
                        "total_policies": len(results)
                    }
                )
                
        elif self._mode == self.CombineMode.MAJORITY:
            if allow_count > deny_count:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    reason=f"Majority allowed ({allow_count}/{len(results)})",
                    metadata={
                        "mode": self._mode.value,
                        "allow_count": allow_count,
                        "deny_count": deny_count,
                        "total_policies": len(results)
                    }
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Majority denied ({deny_count}/{len(results)})",
                    metadata={
                        "mode": self._mode.value,
                        "allow_count": allow_count,
                        "deny_count": deny_count,
                        "total_policies": len(results)
                    }
                )
        
        # Should not reach here
        return PolicyResult(
            decision=PolicyDecision.NEUTRAL,
            reason="Unknown combination mode",
            metadata={}
        )
    
    def add_policy(self, policy: BaseToolPolicy):
        """Add a policy to the composite"""
        self._policies.append(policy)
        self.description = (
            f"Combines {len(self._policies)} policies with {self._mode.value} logic"
        )
        
    def remove_policy(self, policy: BaseToolPolicy):
        """Remove a policy from the composite"""
        if policy in self._policies:
            self._policies.remove(policy)
            self.description = (
                f"Combines {len(self._policies)} policies with {self._mode.value} logic"
            )
    
    @property
    def policies(self) -> List[BaseToolPolicy]:
        """Get the list of sub-policies"""
        return self._policies.copy()
    
    @property
    def mode(self) -> CombineMode:
        """Get the combination mode"""
        return self._mode
    
    @mode.setter
    def mode(self, value: CombineMode):
        """Set the combination mode"""
        self._mode = value
        self.description = (
            f"Combines {len(self._policies)} policies with {self._mode.value} logic"
        )


class CustomPolicy(BaseToolPolicy):
    """
    Policy that uses a custom evaluation function
    
    This allows creating policies with custom logic without
    creating a new class.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        evaluator: Callable[[BaseTool, Optional[Dict[str, Any]]], PolicyResult]
    ):
        """
        Initialize the custom policy
        
        Args:
            name: Policy name
            description: Policy description
            evaluator: Function that evaluates the policy
        """
        super().__init__(name, description)
        self._evaluator = evaluator
        
    def evaluate(
        self,
        tool: BaseTool,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Evaluate using custom function"""
        try:
            return self._evaluator(tool, context)
        except Exception as e:
            logger.error(f"Error in custom policy '{self.name}': {e}")
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Policy evaluation error: {str(e)}",
                metadata={"error": str(e)}
            )


# Convenience functions for creating common policies

def create_safe_tools_policy() -> CompositePolicy:
    """Create a policy that only allows safe tools"""
    return CompositePolicy([
        CategoryPolicy(
            denied_categories=[
                ToolCategory.SYSTEM,
                ToolCategory.DEBUG
            ]
        ),
        CapabilityPolicy(
            forbidden_capabilities=[
                "file_write",
                "file_delete",
                "system_execute"
            ]
        )
    ], CompositePolicy.CombineMode.ALL, "SafeToolsPolicy")


def create_read_only_policy() -> CapabilityPolicy:
    """Create a policy that only allows read operations"""
    return CapabilityPolicy(
        forbidden_capabilities=[
            "write",
            "delete",
            "modify",
            "execute"
        ],
        name="ReadOnlyPolicy"
    )


def create_user_tools_policy(allowed_tools: List[str]) -> AllowListPolicy:
    """Create a policy for user-specific tools"""
    return AllowListPolicy(
        allowed_tools,
        name="UserToolsPolicy"
    )