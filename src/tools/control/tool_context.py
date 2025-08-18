"""
Context-Aware Tool Selection

This module provides context management for intelligent tool selection
based on user, task, and environment information.
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..base import BaseTool, ToolCategory

if TYPE_CHECKING:
    from ..registry import ToolRegistry
    from .tool_controller import ToolController, ToolScore
else:
    ToolScore = Any  # Fallback to avoid runtime NameError


logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    GUEST = "guest"


class TaskType(Enum):
    """Task type enumeration"""
    DATA_PROCESSING = "data_processing"
    FILE_OPERATION = "file_operation"
    NETWORK_OPERATION = "network_operation"
    COMPUTATION = "computation"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    INTEGRATION = "integration"
    DEBUGGING = "debugging"
    TESTING = "testing"
    GENERAL = "general"


class Environment(Enum):
    """Execution environment"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"
    LOCAL = "local"


@dataclass
class UserContext:
    """User-specific context information"""
    user_id: str
    role: UserRole
    permissions: Set[str] = field(default_factory=set)
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)  # Recent tool usage
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    """Task-specific context information"""
    task_id: str
    task_type: TaskType
    description: str
    requirements: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, higher is more important
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentContext:
    """Environment-specific context information"""
    environment: Environment
    resources: Dict[str, Any] = field(default_factory=dict)
    restrictions: Set[str] = field(default_factory=set)
    capabilities: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """
    Complete execution context for tool selection
    
    This combines user, task, and environment contexts to provide
    comprehensive information for intelligent tool selection.
    """
    user: Optional[UserContext] = None
    task: Optional[TaskContext] = None
    environment: Optional[EnvironmentContext] = None
    session_id: str = field(default_factory=lambda: f"session_{datetime.now().timestamp()}")
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        result = {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if self.user:
            result["user"] = {
                "user_id": self.user.user_id,
                "role": self.user.role.value,
                "permissions": list(self.user.permissions),
                "preferences": self.user.preferences,
                "recent_tools": self.user.history[-10:],
                "metadata": self.user.metadata
            }
            
        if self.task:
            result["task"] = {
                "task_id": self.task.task_id,
                "type": self.task.task_type.value,
                "description": self.task.description,
                "requirements": self.task.requirements,
                "constraints": self.task.constraints,
                "priority": self.task.priority,
                "deadline": (
                    self.task.deadline.isoformat()
                    if self.task.deadline else None
                ),
                "metadata": self.task.metadata
            }
            
        if self.environment:
            result["environment"] = {
                "type": self.environment.environment.value,
                "resources": self.environment.resources,
                "restrictions": list(self.environment.restrictions),
                "capabilities": list(self.environment.capabilities),
                "metadata": self.environment.metadata
            }
            
        return result
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if not self.user:
            return False
        return permission in self.user.permissions
    
    def has_capability(self, capability: str) -> bool:
        """Check if environment has a specific capability"""
        if not self.environment:
            return True  # Assume all capabilities if no env specified
        return capability in self.environment.capabilities
    
    def is_restricted(self, restriction: str) -> bool:
        """Check if environment has a specific restriction"""
        if not self.environment:
            return False
        return restriction in self.environment.restrictions


class ContextualToolSelector:
    """
    Tool selector that uses context for intelligent selection
    
    This selector enhances the base tool controller with
    context-aware scoring and filtering.
    """
    
    def __init__(
        self,
        controller: Optional['ToolController'] = None,
        registry: Optional['ToolRegistry'] = None
    ):
        """
        Initialize the contextual selector
        
        Args:
            controller: Tool controller instance
            registry: Tool registry instance
        """
        # Avoid import cycle by importing at runtime if needed
        if controller is None:
            try:
                from .tool_controller import ToolController as _ToolController
                self.controller = _ToolController(registry)
            except Exception as e:
                logger.error(f"Failed to initialize ToolController: {e}")
                raise
        else:
            self.controller = controller

        if registry is None:
            try:
                from ..registry import ToolRegistry as _ToolRegistry
                registry = _ToolRegistry()
            except Exception as e:
                logger.error(f"Failed to initialize ToolRegistry: {e}")
                raise
        self.registry = registry
        self._context_weights = {
            "user_preference": 0.25,
            "task_relevance": 0.35,
            "environment_fit": 0.20,
            "historical_success": 0.20
        }
        
    def select_tools(
        self,
        context: ExecutionContext,
        max_tools: int = 5,
        min_score: float = 0.6
    ) -> List[Tuple[str, float]]:
        """
        Select tools based on context
        
        Args:
            context: Execution context
            max_tools: Maximum tools to return
            min_score: Minimum score threshold
            
        Returns:
            List of (tool_name, score) tuples
        """
        # Convert context to dict for controller
        context_dict = context.to_dict()
        
        # Get task description
        task_desc = ""
        if context.task:
            task_desc = context.task.description
            
        # Get initial recommendations from controller
        result = self.controller.recommend_tools(
            task_desc,
            context_dict,
            max_recommendations=max_tools * 2,  # Get more for filtering
            min_score=0  # We'll apply our own threshold
        )
        
        # Re-score with context awareness
        contextual_scores = {}
        for tool_name in result.selected_tools:
            tool = self.registry.get_tool(tool_name)
            if tool:
                score = self._calculate_contextual_score(
                    tool, context, result.scores.get(tool_name)
                )
                if score >= min_score:
                    contextual_scores[tool_name] = score
                    
        # Sort by score and return top tools
        sorted_tools = sorted(
            contextual_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_tools]
        
        logger.info(
            f"Selected {len(sorted_tools)} tools from "
            f"{len(result.selected_tools)} candidates"
        )
        
        return sorted_tools
    
    def _calculate_contextual_score(
        self,
        tool: BaseTool,
        context: ExecutionContext,
        base_score: Optional[ToolScore] = None
    ) -> float:
        """Calculate context-aware score for a tool"""
        scores = {}
        
        # Start with base score if available
        if base_score:
            scores["base"] = base_score.total_score
        else:
            scores["base"] = 0.5
            
        # User preference score
        scores["user_preference"] = self._score_user_preference(
            tool, context
        )
        
        # Task relevance score
        scores["task_relevance"] = self._score_task_relevance(
            tool, context
        )
        
        # Environment fit score
        scores["environment_fit"] = self._score_environment_fit(
            tool, context
        )
        
        # Historical success score
        scores["historical_success"] = self._score_historical_success(
            tool, context
        )
        
        # Calculate weighted total
        total = 0.0
        for key, weight in self._context_weights.items():
            total += scores.get(key, 0.5) * weight
            
        # Add base score weight
        total += scores["base"] * (1 - sum(self._context_weights.values()))
        
        return total
    
    def _score_user_preference(
        self,
        tool: BaseTool,
        context: ExecutionContext
    ) -> float:
        """Score based on user preferences"""
        if not context.user:
            return 0.5
            
        score = 0.5
        
        # Check if tool was recently used
        if tool.name in context.user.history:
            # More recent = higher score
            try:
                index = context.user.history.index(tool.name)
                recency_score = 1.0 - (index / len(context.user.history))
                score += 0.3 * recency_score
            except ValueError:
                pass
                
        # Check user preferences
        preferences = context.user.preferences
        
        # Preferred categories
        if "preferred_categories" in preferences and tool.metadata:
            if tool.metadata.category.value in preferences["preferred_categories"]:
                score += 0.2
                
        # Preferred tools
        if "preferred_tools" in preferences:
            if tool.name in preferences["preferred_tools"]:
                score += 0.3
                
        # Avoided tools
        if "avoided_tools" in preferences:
            if tool.name in preferences["avoided_tools"]:
                score -= 0.4
                
        return max(0.0, min(1.0, score))
    
    def _score_task_relevance(
        self,
        tool: BaseTool,
        context: ExecutionContext
    ) -> float:
        """Score based on task relevance"""
        if not context.task or not tool.metadata:
            return 0.5
            
        score = 0.5
        
        # Task type matching
        task_type = context.task.task_type
        category = tool.metadata.category
        
        # Direct mappings
        type_category_map = {
            TaskType.DATA_PROCESSING: [
                ToolCategory.TRANSFORMATION,
                ToolCategory.ANALYSIS
            ],
            TaskType.FILE_OPERATION: [
                ToolCategory.UTILITY,
                ToolCategory.SYSTEM
            ],
            TaskType.NETWORK_OPERATION: [
                ToolCategory.INTEGRATION,
                ToolCategory.SYSTEM
            ],
            TaskType.COMPUTATION: [
                ToolCategory.ANALYSIS,
                ToolCategory.TRANSFORMATION
            ],
            TaskType.ANALYSIS: [
                ToolCategory.ANALYSIS
            ],
            TaskType.GENERATION: [
                ToolCategory.GENERATION
            ],
            TaskType.TRANSFORMATION: [
                ToolCategory.TRANSFORMATION
            ],
            TaskType.INTEGRATION: [
                ToolCategory.INTEGRATION
            ],
            TaskType.DEBUGGING: [
                ToolCategory.DEBUG,
                ToolCategory.ANALYSIS
            ],
            TaskType.TESTING: [
                ToolCategory.DEBUG,
                ToolCategory.UTILITY
            ]
        }
        
        if task_type in type_category_map:
            if category in type_category_map[task_type]:
                score += 0.3
                
        # Requirements matching
        requirements = context.task.requirements
        capabilities = tool.metadata.capabilities
        
        if "required_capabilities" in requirements:
            required = set(requirements["required_capabilities"])
            provided = set(capabilities.keys())
            if required:
                match_ratio = len(required & provided) / len(required)
                score += 0.2 * match_ratio
                
        # Priority adjustment
        priority = context.task.priority
        if priority >= 8:  # High priority
            # Prefer reliable, well-tested tools
            if capabilities.get("stable", False):
                score += 0.1
            if capabilities.get("tested", False):
                score += 0.1
                
        return max(0.0, min(1.0, score))
    
    def _score_environment_fit(
        self,
        tool: BaseTool,
        context: ExecutionContext
    ) -> float:
        """Score based on environment fit"""
        if not context.environment or not tool.metadata:
            return 0.5
            
        score = 0.5
        env_type = context.environment.environment
        capabilities = tool.metadata.capabilities
        
        # Environment-specific scoring
        if env_type == Environment.PRODUCTION:
            # Production prefers stable, secure tools
            if capabilities.get("stable", False):
                score += 0.2
            if capabilities.get("secure", False):
                score += 0.2
            if capabilities.get("debug", False):
                score -= 0.3  # Avoid debug tools in production
                
        elif env_type == Environment.DEVELOPMENT:
            # Development is more permissive
            if capabilities.get("debug", False):
                score += 0.1
            if capabilities.get("experimental", False):
                score += 0.1
                
        elif env_type == Environment.TESTING:
            # Testing prefers mock and test tools
            if capabilities.get("mock", False):
                score += 0.2
            if capabilities.get("test", False):
                score += 0.2
                
        # Check restrictions
        restrictions = context.environment.restrictions
        if restrictions:
            # Penalty for tools that might violate restrictions
            if "no_network" in restrictions and capabilities.get("network", False):
                score -= 0.4
            if "no_filesystem" in restrictions and capabilities.get("filesystem", False):
                score -= 0.4
                
        # Check required capabilities
        env_capabilities = context.environment.capabilities
        if env_capabilities:
            # Bonus for tools that use available capabilities
            for cap in env_capabilities:
                if capabilities.get(cap, False):
                    score += 0.05
                    
        return max(0.0, min(1.0, score))
    
    def _score_historical_success(
        self,
        tool: BaseTool,
        context: ExecutionContext
    ) -> float:
        """Score based on historical success"""
        if not context.user:
            return 0.5
            
        # Get usage statistics from controller
        stats = self.controller.get_usage_statistics()
        usage_counts = dict(stats.get("most_used_tools", []))
        
        if tool.name not in usage_counts:
            return 0.5
            
        # Normalize usage count (assume 100+ uses is very successful)
        usage = usage_counts[tool.name]
        normalized = min(usage / 100, 1.0)
        
        # Combine with user-specific history
        score = 0.3 + (0.4 * normalized)
        
        # Bonus if in user's recent history
        if tool.name in context.user.history[-5:]:
            score += 0.3
            
        return max(0.0, min(1.0, score))
    
    def recommend_for_task_type(
        self,
        task_type: TaskType,
        user_role: Optional[UserRole] = None,
        environment: Optional[Environment] = None
    ) -> List[str]:
        """
        Get tool recommendations for a specific task type
        
        Args:
            task_type: Type of task
            user_role: Optional user role
            environment: Optional environment
            
        Returns:
            List of recommended tool names
        """
        # Create context
        context = ExecutionContext(
            task=TaskContext(
                task_id=f"recommendation_{task_type.value}",
                task_type=task_type,
                description=f"Recommendations for {task_type.value}"
            )
        )
        
        if user_role:
            context.user = UserContext(
                user_id="recommendation_user",
                role=user_role
            )
            
        if environment:
            context.environment = EnvironmentContext(
                environment=environment
            )
            
        # Get recommendations
        tools = self.select_tools(context, max_tools=10)
        return [name for name, _ in tools]
    
    def create_context_from_dict(
        self,
        data: Dict[str, Any]
    ) -> ExecutionContext:
        """
        Create execution context from dictionary
        
        Args:
            data: Dictionary with context data
            
        Returns:
            ExecutionContext instance
        """
        context = ExecutionContext(
            session_id=data.get("session_id", f"session_{datetime.now().timestamp()}"),
            metadata=data.get("metadata", {})
        )
        
        # Parse user context
        if "user" in data:
            user_data = data["user"]
            context.user = UserContext(
                user_id=user_data.get("user_id", "unknown"),
                role=UserRole(user_data.get("role", "user")),
                permissions=set(user_data.get("permissions", [])),
                preferences=user_data.get("preferences", {}),
                history=user_data.get("history", []),
                metadata=user_data.get("metadata", {})
            )
            
        # Parse task context
        if "task" in data:
            task_data = data["task"]
            context.task = TaskContext(
                task_id=task_data.get("task_id", "unknown"),
                task_type=TaskType(task_data.get("type", "general")),
                description=task_data.get("description", ""),
                requirements=task_data.get("requirements", {}),
                constraints=task_data.get("constraints", {}),
                priority=task_data.get("priority", 5),
                metadata=task_data.get("metadata", {})
            )
            
        # Parse environment context
        if "environment" in data:
            env_data = data["environment"]
            context.environment = EnvironmentContext(
                environment=Environment(env_data.get("type", "local")),
                resources=env_data.get("resources", {}),
                restrictions=set(env_data.get("restrictions", [])),
                capabilities=set(env_data.get("capabilities", [])),
                metadata=env_data.get("metadata", {})
            )
            
        return context


# Convenience functions

def create_user_context(
    user_id: str,
    role: UserRole = UserRole.USER,
    permissions: Optional[List[str]] = None,
    preferences: Optional[Dict[str, Any]] = None
) -> UserContext:
    """Create a user context"""
    return UserContext(
        user_id=user_id,
        role=role,
        permissions=set(permissions or []),
        preferences=preferences or {}
    )


def create_task_context(
    task_type: TaskType,
    description: str,
    priority: int = 5
) -> TaskContext:
    """Create a task context"""
    return TaskContext(
        task_id=f"task_{datetime.now().timestamp()}",
        task_type=task_type,
        description=description,
        priority=priority
    )


def create_environment_context(
    environment: Environment = Environment.LOCAL,
    restrictions: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None
) -> EnvironmentContext:
    """Create an environment context"""
    return EnvironmentContext(
        environment=environment,
        restrictions=set(restrictions or []),
        capabilities=set(capabilities or [])
    )