"""
Tool orchestration system for managing complex workflows.

This module provides high-level orchestration capabilities for
coordinating multiple tools in complex workflows with dependencies,
parallel execution, and conditional logic.
"""

from __future__ import annotations
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any, Dict, List, Optional, Set, Union, Callable
)
import uuid

from ..base import BaseTool, ToolResult
from ..engine.executor import ToolExecutor, ExecutionMode
from ..engine.result_processor import ResultProcessor, StandardProcessor
from ..engine.error_recovery import ErrorRecovery, RetryStrategy


logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()
    CANCELLED = auto()


class ConditionType(Enum):
    """Types of conditions for workflow steps."""
    ALWAYS = auto()
    ON_SUCCESS = auto()
    ON_FAILURE = auto()
    CUSTOM = auto()


@dataclass
class StepCondition:
    """Condition for executing a workflow step."""
    condition_type: ConditionType
    custom_evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None
    depends_on: List[str] = field(default_factory=list)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if condition is met."""
        if self.condition_type == ConditionType.ALWAYS:
            return True
            
        if self.condition_type == ConditionType.ON_SUCCESS:
            return all(
                context.get(f"step_{dep}_status") == StepStatus.COMPLETED
                for dep in self.depends_on
            )
            
        if self.condition_type == ConditionType.ON_FAILURE:
            return any(
                context.get(f"step_{dep}_status") == StepStatus.FAILED
                for dep in self.depends_on
            )
            
        if (self.condition_type == ConditionType.CUSTOM and
                self.custom_evaluator):
            return self.custom_evaluator(context)
            
        return True


@dataclass
class WorkflowStep:
    """Individual step in a workflow."""
    id: str
    tool: Union[BaseTool, str]  # Tool instance or tool name
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: StepCondition = field(
        default_factory=lambda: StepCondition(ConditionType.ALWAYS)
    )
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    retry_count: int = 0
    execution_mode: ExecutionMode = ExecutionMode.STANDALONE
    
    def __post_init__(self):
        """Initialize step ID if not provided."""
        if not self.id:
            self.id = f"step_{uuid.uuid4().hex[:8]}"


@dataclass
class ParallelGroup:
    """Group of steps to execute in parallel."""
    id: str
    steps: List[WorkflowStep]
    name: str = ""
    description: str = ""
    max_workers: int = 4
    
    def __post_init__(self):
        """Initialize group ID if not provided."""
        if not self.id:
            self.id = f"group_{uuid.uuid4().hex[:8]}"


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow."""
    name: str
    description: str = ""
    steps: List[Union[WorkflowStep, ParallelGroup]] = field(
        default_factory=list
    )
    context: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    on_error: str = "stop"  # "stop", "continue", "rollback"
    
    def add_step(self, step: WorkflowStep) -> WorkflowDefinition:
        """Add a step to the workflow."""
        self.steps.append(step)
        return self
        
    def add_parallel_group(self, group: ParallelGroup) -> WorkflowDefinition:
        """Add a parallel group to the workflow."""
        self.steps.append(group)
        return self
        
    def validate(self) -> bool:
        """Validate workflow definition."""
        # Check for circular dependencies
        step_ids = set()
        for item in self.steps:
            if isinstance(item, WorkflowStep):
                step_ids.add(item.id)
            else:  # ParallelGroup
                for step in item.steps:
                    step_ids.add(step.id)
                    
        # Verify all dependencies exist
        for item in self.steps:
            if isinstance(item, WorkflowStep):
                for dep in item.dependencies:
                    if dep not in step_ids:
                        logger.error(f"Unknown dependency: {dep}")
                        return False
            else:  # ParallelGroup
                for step in item.steps:
                    for dep in step.dependencies:
                        if dep not in step_ids:
                            logger.error(f"Unknown dependency: {dep}")
                            return False
                            
        return True


@dataclass
class StepResult:
    """Result of executing a workflow step."""
    step_id: str
    status: StepStatus
    result: Optional[ToolResult] = None
    error: Optional[Exception] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    
    @property
    def is_success(self) -> bool:
        """Check if step was successful."""
        return self.status == StepStatus.COMPLETED


@dataclass
class WorkflowResult:
    """Result of executing a complete workflow."""
    workflow_name: str
    status: StepStatus
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    
    @property
    def is_success(self) -> bool:
        """Check if workflow was successful."""
        return self.status == StepStatus.COMPLETED
        
    def get_failed_steps(self) -> List[StepResult]:
        """Get all failed steps."""
        return [
            result for result in self.step_results.values()
            if result.status == StepStatus.FAILED
        ]


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""
    pass


class DependencyResolver:
    """Resolves dependencies between workflow steps."""
    
    def __init__(self, workflow: WorkflowDefinition):
        self.workflow = workflow
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._build_dependency_graph()
        
    def _build_dependency_graph(self):
        """Build dependency graph from workflow definition."""
        for item in self.workflow.steps:
            if isinstance(item, WorkflowStep):
                self._dependency_graph[item.id] = set(item.dependencies)
            else:  # ParallelGroup
                for step in item.steps:
                    self._dependency_graph[step.id] = set(step.dependencies)
                    
    def get_ready_steps(
        self,
        completed_steps: Set[str]
    ) -> List[Union[WorkflowStep, ParallelGroup]]:
        """Get steps that are ready to execute."""
        ready_items = []
        
        for item in self.workflow.steps:
            if isinstance(item, WorkflowStep):
                if (item.id not in completed_steps and
                    all(dep in completed_steps
                        for dep in item.dependencies)):
                    ready_items.append(item)
            else:  # ParallelGroup
                # Check if all steps in group are ready
                group_ready = True
                for step in item.steps:
                    if (step.id in completed_steps or
                        not all(dep in completed_steps
                                for dep in step.dependencies)):
                        group_ready = False
                        break
                        
                if group_ready:
                    ready_items.append(item)
                    
        return ready_items
        
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the workflow."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def _dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._dependency_graph.get(node, set()):
                if neighbor not in visited:
                    if _dfs(neighbor, path[:]):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])
                    
            path.pop()
            rec_stack.remove(node)
            return False
            
        for node in self._dependency_graph:
            if node not in visited:
                _dfs(node, [])
                
        return cycles


class ToolOrchestrator:
    """
    Orchestrates complex tool workflows with dependencies and parallel exec.
    """
    
    def __init__(
        self,
        tool_registry: Optional[Dict[str, BaseTool]] = None,
        executor: Optional[ToolExecutor] = None,
        result_processor: Optional[ResultProcessor] = None,
        error_recovery: Optional[ErrorRecovery] = None,
        max_parallel_steps: int = 4
    ):
        self.tool_registry = tool_registry or {}
        self.executor = executor or ToolExecutor()
        self.result_processor = result_processor or StandardProcessor()
        self.error_recovery = error_recovery or ErrorRecovery(
            [RetryStrategy(max_retries=3)]
        )
        self.max_parallel_steps = max_parallel_steps
        self._executor_pool = ThreadPoolExecutor(
            max_workers=max_parallel_steps
        )
        
    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool for use in workflows."""
        self.tool_registry[name] = tool
        
    def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute a complete workflow."""
        # Validate workflow
        if not workflow.validate():
            raise OrchestrationError("Invalid workflow definition")
            
        # Check for circular dependencies
        resolver = DependencyResolver(workflow)
        cycles = resolver.detect_circular_dependencies()
        if cycles:
            raise OrchestrationError(
                f"Circular dependencies detected: {cycles}"
            )
            
        # Initialize result
        result = WorkflowResult(
            workflow_name=workflow.name,
            status=StepStatus.RUNNING,
            started_at=datetime.now(),
            context={**workflow.context, **(initial_context or {})}
        )
        
        try:
            # Execute workflow
            completed_steps = set()
            failed_steps = set()
            
            while (len(completed_steps) + len(failed_steps) <
                   self._count_steps(workflow)):
                # Get ready steps
                ready_items = resolver.get_ready_steps(completed_steps)
                
                if not ready_items:
                    # No more steps can execute
                    break
                    
                # Execute ready items
                for item in ready_items:
                    if isinstance(item, WorkflowStep):
                        step_result = self._execute_step(item, result.context)
                        result.step_results[item.id] = step_result
                        
                        if step_result.is_success:
                            completed_steps.add(item.id)
                        else:
                            failed_steps.add(item.id)
                            if workflow.on_error == "stop":
                                raise OrchestrationError(
                                    f"Step {item.id} failed: "
                                    f"{step_result.error}"
                                )
                    else:  # ParallelGroup
                        group_results = self._execute_parallel_group(
                            item,
                            result.context
                        )
                        
                        for step_id, step_result in group_results.items():
                            result.step_results[step_id] = step_result
                            if step_result.is_success:
                                completed_steps.add(step_id)
                            else:
                                failed_steps.add(step_id)
                                if workflow.on_error == "stop":
                                    raise OrchestrationError(
                                        f"Step {step_id} failed: "
                                        f"{step_result.error}"
                                    )
                                    
            # Determine final status
            if failed_steps:
                result.status = StepStatus.FAILED
            elif len(completed_steps) == self._count_steps(workflow):
                result.status = StepStatus.COMPLETED
            else:
                result.status = StepStatus.CANCELLED
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            result.status = StepStatus.FAILED
            raise
        finally:
            result.completed_at = datetime.now()
            if result.completed_at and result.started_at:
                result.duration = (
                    result.completed_at - result.started_at
                ).total_seconds()
            
        return result
        
    async def execute_workflow_async(
        self,
        workflow: WorkflowDefinition,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute a workflow asynchronously."""
        # Similar to execute_workflow but using async/await
        # Implementation would use asyncio for parallel execution
        raise NotImplementedError(
            "Async workflow execution not yet implemented"
        )
        
    def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> StepResult:
        """Execute a single workflow step."""
        result = StepResult(
            step_id=step.id,
            status=StepStatus.RUNNING,
            started_at=datetime.now()
        )
        
        try:
            # Check condition
            if not step.condition.evaluate(context):
                result.status = StepStatus.SKIPPED
                return result
                
            # Get tool
            if isinstance(step.tool, str):
                tool = self.tool_registry.get(step.tool)
                if not tool:
                    raise OrchestrationError(f"Tool not found: {step.tool}")
            else:
                tool = step.tool
                
            # Prepare parameters
            params = self._resolve_parameters(step.parameters, context)
            
            # Execute tool
            tool_name = step.tool if isinstance(step.tool, str) else tool.name
            
            # Execute with retries if needed
            execution_result = None
            last_error = None
            
            for attempt in range(1, step.retry_count + 2):
                try:
                    execution_result = self.executor.execute(
                        tool_name,
                        params,
                        mode=step.execution_mode,
                        timeout=step.timeout
                    )
                    
                    if execution_result.success:
                        break
                        
                    last_error = Exception(
                        execution_result.error or "Unknown error"
                    )
                    
                except Exception as exec_error:
                    last_error = exec_error
                    
                # If we have retries left, use error recovery
                if attempt <= step.retry_count and last_error:
                    recovery_result = self.error_recovery.recover(
                        error=last_error,
                        tool_name=tool_name,
                        parameters=params,
                        attempt=attempt,
                        metadata={"step_id": step.id}
                    )
                    
                    if recovery_result.should_retry:
                        # Wait and retry
                        time.sleep(recovery_result.retry_delay)
                        continue
                    else:
                        break
                        
            # Create ToolResult from ExecutionResult
            if execution_result and execution_result.success:
                tool_result = ToolResult(
                    success=True,
                    output=execution_result.result,
                    metadata=execution_result.metadata
                )
            else:
                tool_result = ToolResult(
                    success=False,
                    output=None,
                    errors=(
                        [str(last_error)] if last_error
                        else ["Unknown error"]
                    )
                )
                
            # Process result if successful
            if tool_result.success:
                processed_result = self.result_processor.process(tool_result)
                
                # Update context
                context[f"step_{step.id}_result"] = processed_result.processed
                context[f"step_{step.id}_status"] = StepStatus.COMPLETED
                
                result.result = tool_result
                result.status = StepStatus.COMPLETED
            else:
                result.result = tool_result
                result.status = StepStatus.FAILED
                context[f"step_{step.id}_status"] = StepStatus.FAILED
            
        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            result.status = StepStatus.FAILED
            result.error = e
            context[f"step_{step.id}_status"] = StepStatus.FAILED
            
        finally:
            result.completed_at = datetime.now()
            if result.completed_at and result.started_at:
                result.duration = (
                    result.completed_at - result.started_at
                ).total_seconds()
            
        return result
        
    def _execute_parallel_group(
        self,
        group: ParallelGroup,
        context: Dict[str, Any]
    ) -> Dict[str, StepResult]:
        """Execute a group of steps in parallel."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=group.max_workers) as executor:
            # Submit all steps
            future_to_step = {
                executor.submit(
                    self._execute_step,
                    step,
                    context.copy()  # Each step gets its own context copy
                ): step
                for step in group.steps
            }
            
            # Collect results
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                try:
                    step_result = future.result()
                    results[step.id] = step_result
                    
                    # Update shared context
                    if step_result.is_success and step_result.result:
                        context[f"step_{step.id}_result"] = (
                            step_result.result.output
                            if hasattr(step_result.result, 'output')
                            else step_result.result
                        )
                        
                except Exception as e:
                    logger.error(f"Parallel step {step.id} failed: {e}")
                    results[step.id] = StepResult(
                        step_id=step.id,
                        status=StepStatus.FAILED,
                        error=e
                    )
                    
        return results
        
    def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter references from context."""
        resolved = {}
        
        for key, value in parameters.items():
            if (isinstance(value, str) and value.startswith("${") and
                    value.endswith("}")):
                # Context reference
                ref_key = value[2:-1]
                resolved[key] = context.get(ref_key, value)
            elif isinstance(value, dict):
                # Recursively resolve nested parameters
                resolved[key] = self._resolve_parameters(value, context)
            else:
                resolved[key] = value
                
        return resolved
        
    def _count_steps(self, workflow: WorkflowDefinition) -> int:
        """Count total number of steps in workflow."""
        count = 0
        for item in workflow.steps:
            if isinstance(item, WorkflowStep):
                count += 1
            else:  # ParallelGroup
                count += len(item.steps)
        return count
        
    def visualize_workflow(self, workflow: WorkflowDefinition) -> str:
        """Generate a text visualization of the workflow."""
        lines = [f"Workflow: {workflow.name}"]
        if workflow.description:
            lines.append(f"Description: {workflow.description}")
        lines.append("-" * 50)
        
        for i, item in enumerate(workflow.steps):
            if isinstance(item, WorkflowStep):
                lines.append(f"{i+1}. Step: {item.name} (ID: {item.id})")
                if item.description:
                    lines.append(f"   Description: {item.description}")
                if item.dependencies:
                    lines.append(
                        f"   Dependencies: {', '.join(item.dependencies)}"
                    )
                lines.append(f"   Tool: {item.tool}")
                lines.append(f"   Mode: {item.execution_mode.name}")
            else:  # ParallelGroup
                lines.append(
                    f"{i+1}. Parallel Group: {item.name} (ID: {item.id})"
                )
                if item.description:
                    lines.append(f"   Description: {item.description}")
                lines.append(f"   Max Workers: {item.max_workers}")
                for j, step in enumerate(item.steps):
                    lines.append(f"   {j+1}. {step.name} (ID: {step.id})")
                    if step.dependencies:
                        lines.append(
                            f"      Dependencies: "
                            f"{', '.join(step.dependencies)}"
                        )
                        
        return "\n".join(lines)