"""
Tool Executor Module

This module provides the core execution engine for tools,
enabling them to function independently of AI models.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from src.tools.base import BaseTool
from src.tools.registry import ToolRegistry
from src.tools.abstraction.model_interface import (
    ModelInterface, ModelRequest
)

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Modes of tool execution"""
    STANDALONE = auto()      # Execute without AI assistance
    AI_ASSISTED = auto()     # Execute with AI parameter enhancement
    AI_GUIDED = auto()       # AI determines execution strategy
    HYBRID = auto()          # Mix of standalone and AI-assisted


@dataclass
class ExecutionResult:
    """Result of a tool execution"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    mode: ExecutionMode = ExecutionMode.STANDALONE
    ai_assistance_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "mode": self.mode.name,
            "ai_assistance_used": self.ai_assistance_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PipelineStep:
    """A step in an execution pipeline"""
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: Optional[List[str]] = None
    error_handler: Optional[str] = None
    retry_count: int = 0
    timeout: Optional[float] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    transform: Optional[Callable[[Any], Any]] = None


class ToolExecutor:
    """
    Model-independent tool executor
    
    This class executes tools without requiring AI models,
    but can optionally use models for enhanced functionality.
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        model: Optional[ModelInterface] = None,
        max_workers: int = 4,
        default_timeout: float = 30.0
    ):
        """
        Initialize the executor
        
        Args:
            registry: Tool registry
            model: Optional AI model for assistance
            max_workers: Maximum concurrent workers
            default_timeout: Default execution timeout
        """
        self.registry = registry or ToolRegistry()
        self.model = model
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        
        # Thread pool for async execution
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, Future] = {}
        self._execution_history: List[ExecutionResult] = []
        self._lock = threading.RLock()
        
    def execute(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.STANDALONE,
        timeout: Optional[float] = None,
        validate: bool = True
    ) -> ExecutionResult:
        """
        Execute a tool synchronously
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            mode: Execution mode
            timeout: Execution timeout
            validate: Whether to validate parameters
            
        Returns:
            Execution result
        """
        start_time = time.time()
        parameters = parameters or {}
        
        # Get the tool
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found"
            )
            
        # Check if tool is ready
        if not tool.is_ready:
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' is not ready"
            )
            
        try:
            # Enhance parameters with AI if requested
            if mode in [ExecutionMode.AI_ASSISTED, ExecutionMode.AI_GUIDED]:
                if self.model and self.model.is_available():
                    parameters = self._enhance_parameters(
                        tool, parameters, mode
                    )
                    
            # Validate parameters
            if validate:
                is_valid, errors = tool.validate_parameters(parameters)
                if not is_valid:
                    return ExecutionResult(
                        tool_name=tool_name,
                        success=False,
                        result=None,
                        error=(
                            f"Parameter validation failed: "
                            f"{', '.join(errors)}"
                        )
                    )
                    
            # Execute the tool
            result = tool.execute(**parameters)
            
            # Process result
            execution_time = time.time() - start_time
            
            execution_result = ExecutionResult(
                tool_name=tool_name,
                success=result.success if hasattr(result, 'success') else True,
                result=result,
                error=(
                    result.errors[0]
                    if hasattr(result, 'errors') and result.errors
                    else None
                ),
                execution_time=execution_time,
                mode=mode,
                ai_assistance_used=mode != ExecutionMode.STANDALONE,
                metadata={
                    "parameters_used": parameters,
                    "tool_status": (
                        result.status.value
                        if hasattr(result, 'status')
                        else None
                    )
                }
            )
            
            # Record execution
            self._record_execution(execution_result)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            execution_time = time.time() - start_time
            
            error_result = ExecutionResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
                mode=mode,
                metadata={"parameters_attempted": parameters}
            )
            
            self._record_execution(error_result)
            return error_result
            
    async def execute_async(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.STANDALONE,
        timeout: Optional[float] = None,
        validate: bool = True
    ) -> ExecutionResult:
        """Execute a tool asynchronously"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run in executor
        future = loop.run_in_executor(
            self._executor,
            self.execute,
            tool_name,
            parameters,
            mode,
            timeout,
            validate
        )
        
        # Apply timeout if specified
        if timeout:
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                return ExecutionResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    error=f"Execution timed out after {timeout} seconds"
                )
        else:
            result = await future
            
        return result
        
    def execute_batch(
        self,
        executions: List[Dict[str, Any]],
        parallel: bool = True,
        stop_on_error: bool = False
    ) -> List[ExecutionResult]:
        """
        Execute multiple tools
        
        Args:
            executions: List of execution specifications
            parallel: Whether to execute in parallel
            stop_on_error: Whether to stop on first error
            
        Returns:
            List of execution results
        """
        results = []
        
        if parallel:
            # Execute in parallel using thread pool
            futures = []
            
            for exec_spec in executions:
                tool_name = exec_spec.get("tool_name")
                if not tool_name:
                    continue
                    
                future = self._executor.submit(
                    self.execute,
                    tool_name,
                    exec_spec.get("parameters"),
                    exec_spec.get("mode", ExecutionMode.STANDALONE),
                    exec_spec.get("timeout"),
                    exec_spec.get("validate", True)
                )
                futures.append(future)
                
            # Collect results
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                    
                    if not result.success and stop_on_error:
                        # Cancel remaining futures
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break
                        
                except Exception as e:
                    logger.error(f"Batch execution error: {e}")
                    results.append(ExecutionResult(
                        tool_name="unknown",
                        success=False,
                        result=None,
                        error=str(e)
                    ))
                    
                    if stop_on_error:
                        break
                        
        else:
            # Execute sequentially
            for exec_spec in executions:
                tool_name = exec_spec.get("tool_name")
                if not tool_name:
                    continue
                    
                result = self.execute(
                    tool_name,
                    exec_spec.get("parameters"),
                    exec_spec.get("mode", ExecutionMode.STANDALONE),
                    exec_spec.get("timeout"),
                    exec_spec.get("validate", True)
                )
                results.append(result)
                
                if not result.success and stop_on_error:
                    break
                    
        return results
        
    def _enhance_parameters(
        self,
        tool: BaseTool,
        parameters: Dict[str, Any],
        mode: ExecutionMode
    ) -> Dict[str, Any]:
        """Enhance parameters using AI"""
        if not self.model or not self.model.is_available():
            return parameters
            
        try:
            # Build prompt for parameter enhancement
            prompt = self._build_enhancement_prompt(tool, parameters, mode)
            
            # Get AI assistance synchronously
            # (We'll run this in an async context if needed)
            import asyncio
            
            async def get_ai_response():
                request = ModelRequest(
                    prompt=prompt,
                    system_prompt=(
                        "You are a helpful assistant that enhances "
                        "tool parameters."
                    ),
                    temperature=0.3,
                    max_tokens=500
                )
                if self.model:
                    return await self.model.generate(request)
                else:
                    # This shouldn't happen due to earlier check
                    raise RuntimeError("Model not available")
                
            # Run async function
            try:
                try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
                if loop.is_running():
                    # We're already in an async context
                    coro = get_ai_response()
                    response = asyncio.run_coroutine_threadsafe(
                        coro, loop
                    ).result()
                else:
                    # Create new event loop
                    response = asyncio.run(get_ai_response())
            except Exception:
                # Fallback to original parameters
                return parameters
                
            if response.success:
                # Parse enhanced parameters
                enhanced = self._parse_enhanced_parameters(
                    response.content, parameters
                )
                return enhanced
                
        except Exception as e:
            logger.warning(f"Parameter enhancement failed: {e}")
            
        return parameters
        
    def _build_enhancement_prompt(
        self,
        tool: BaseTool,
        parameters: Dict[str, Any],
        mode: ExecutionMode
    ) -> str:
        """Build prompt for parameter enhancement"""
        import json
        
        prompt = f"""Tool: {tool.name}
Description: {tool.metadata.description if tool.metadata else 'No description'}

Current Parameters:
{json.dumps(parameters, indent=2)}

"""
        
        if mode == ExecutionMode.AI_ASSISTED:
            prompt += """Please enhance these parameters by:
1. Filling in any missing optional parameters with sensible defaults
2. Correcting any obvious errors
3. Optimizing values for better results

Return the enhanced parameters as valid JSON."""
            
        elif mode == ExecutionMode.AI_GUIDED:
            prompt += """Please analyze this tool execution and:
1. Determine the best parameters to use
2. Suggest any alternative approaches
3. Identify potential issues

Return the recommended parameters as valid JSON."""
            
        return prompt
        
    def _parse_enhanced_parameters(
        self,
        ai_response: str,
        original: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse enhanced parameters from AI response"""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                enhanced = json.loads(json_match.group())
                # Merge with original
                original.update(enhanced)
                return original
        except Exception:
            pass
            
        return original
        
    def _record_execution(self, result: ExecutionResult):
        """Record execution in history"""
        with self._lock:
            self._execution_history.append(result)
            
            # Limit history size
            if len(self._execution_history) > 1000:
                self._execution_history = self._execution_history[-500:]
                
    def get_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionResult]:
        """Get execution history"""
        with self._lock:
            history = self._execution_history.copy()
            
        if tool_name:
            history = [r for r in history if r.tool_name == tool_name]
            
        return history[-limit:]
        
    def clear_history(self):
        """Clear execution history"""
        with self._lock:
            self._execution_history.clear()
            
    def shutdown(self):
        """Shutdown the executor"""
        # Cancel running tasks
        for future in self._running_tasks.values():
            if not future.done():
                future.cancel()
                
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        

class ExecutionPipeline:
    """
    Pipeline for executing multiple tools in sequence or parallel
    
    This class enables complex workflows by orchestrating multiple
    tool executions with dependencies and error handling.
    """
    
    def __init__(
        self,
        executor: ToolExecutor,
        name: str = "unnamed_pipeline"
    ):
        """
        Initialize the pipeline
        
        Args:
            executor: Tool executor
            name: Pipeline name
        """
        self.executor = executor
        self.name = name
        self.steps: List[PipelineStep] = []
        self.results: Dict[str, ExecutionResult] = {}
        self._context: Dict[str, Any] = {}
        
    def add_step(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        **kwargs
    ) -> 'ExecutionPipeline':
        """Add a step to the pipeline"""
        step = PipelineStep(
            tool_name=tool_name,
            parameters=parameters or {},
            depends_on=depends_on,
            **kwargs
        )
        self.steps.append(step)
        return self
        
    def set_context(self, key: str, value: Any):
        """Set context value"""
        self._context[key] = value
        
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value"""
        return self._context.get(key, default)
        
    async def execute(
        self,
        mode: ExecutionMode = ExecutionMode.STANDALONE,
        parallel: bool = True
    ) -> Dict[str, ExecutionResult]:
        """
        Execute the pipeline
        
        Args:
            mode: Execution mode for all steps
            parallel: Whether to execute independent steps in parallel
            
        Returns:
            Dictionary of step results
        """
        self.results.clear()
        
        # Build execution graph
        graph = self._build_execution_graph()
        
        # Execute based on dependencies
        if parallel:
            await self._execute_parallel(graph, mode)
        else:
            await self._execute_sequential(graph, mode)
            
        return self.results
        
    def _build_execution_graph(self) -> Dict[str, List[str]]:
        """Build execution dependency graph"""
        graph = {}
        
        for i, step in enumerate(self.steps):
            step_id = f"{step.tool_name}_{i}"
            graph[step_id] = step.depends_on or []
            
        return graph
        
    async def _execute_parallel(
        self,
        graph: Dict[str, List[str]],
        mode: ExecutionMode
    ):
        """Execute pipeline steps in parallel where possible"""
        completed = set()
        
        while len(completed) < len(self.steps):
            # Find steps ready to execute
            ready_steps = []
            
            for i, step in enumerate(self.steps):
                step_id = f"{step.tool_name}_{i}"
                
                if step_id in completed:
                    continue
                    
                # Check dependencies
                deps_met = True
                if step.depends_on:
                    for dep in step.depends_on:
                        if dep not in completed:
                            deps_met = False
                            break
                            
                if deps_met:
                    ready_steps.append((step_id, step))
                    
            # Execute ready steps
            if ready_steps:
                step_tasks = []
                
                for step_id, step in ready_steps:
                    # Check condition
                    if step.condition and not step.condition(self._context):
                        # Skip this step
                        self.results[step_id] = ExecutionResult(
                            tool_name=step.tool_name,
                            success=True,
                            result=None,
                            metadata={"skipped": True}
                        )
                        completed.add(step_id)
                        continue
                        
                    # Resolve parameters
                    params = self._resolve_parameters(step.parameters)
                    
                    # Create execution task
                    task = asyncio.create_task(
                        self._execute_step(step_id, step, params, mode)
                    )
                    step_tasks.append(task)
                    
                # Wait for step completion
                if step_tasks:
                    await asyncio.gather(*step_tasks)
                    
                # Mark as completed
                for step_id, _ in ready_steps:
                    if step_id not in completed:
                        completed.add(step_id)
                        
            else:
                # No steps ready - might be circular dependency
                logger.error(
                    "Pipeline execution stalled - possible circular dependency"
                )
                break
                
    async def _execute_sequential(
        self,
        graph: Dict[str, List[str]],
        mode: ExecutionMode
    ):
        """Execute pipeline steps sequentially"""
        for i, step in enumerate(self.steps):
            step_id = f"{step.tool_name}_{i}"
            
            # Check condition
            if step.condition and not step.condition(self._context):
                # Skip this step
                self.results[step_id] = ExecutionResult(
                    tool_name=step.tool_name,
                    success=True,
                    result=None,
                    metadata={"skipped": True}
                )
                continue
                
            # Resolve parameters
            params = self._resolve_parameters(step.parameters)
            
            # Execute step
            await self._execute_step(step_id, step, params, mode)
            
    async def _execute_step(
        self,
        step_id: str,
        step: PipelineStep,
        parameters: Dict[str, Any],
        mode: ExecutionMode
    ):
        """Execute a single pipeline step"""
        # Execute with retries
        last_error = None
        
        for attempt in range(step.retry_count + 1):
            result = await self.executor.execute_async(
                step.tool_name,
                parameters,
                mode,
                step.timeout
            )
            
            if result.success:
                # Apply transformation if specified
                if step.transform:
                    try:
                        result.result = step.transform(result.result)
                    except Exception as e:
                        logger.error(f"Transform failed: {e}")
                        
                # Store result
                self.results[step_id] = result
                
                # Update context with result
                self._context[step_id] = result.result
                
                return
            else:
                last_error = result.error
                
                # Try error handler if specified
                if step.error_handler and attempt < step.retry_count:
                    handler_result = await self.executor.execute_async(
                        step.error_handler,
                        {"error": last_error, "parameters": parameters},
                        mode
                    )
                    
                    if handler_result.success:
                        # Update parameters from handler
                        if isinstance(handler_result.result, dict):
                            parameters.update(handler_result.result)
                            
            # Wait before retry
            if attempt < step.retry_count:
                await asyncio.sleep(2 ** attempt)
                
        # All attempts failed
        self.results[step_id] = ExecutionResult(
            tool_name=step.tool_name,
            success=False,
            result=None,
            error=f"Failed after {step.retry_count + 1} attempts: {last_error}"
        )
        
    def _resolve_parameters(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter placeholders from context"""
        import re
        
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # Look for placeholders like ${step_id.field}
                matches = re.findall(r'\$\{([^}]+)\}', value)
                
                for match in matches:
                    parts = match.split('.')
                    
                    if len(parts) == 1:
                        # Simple context lookup
                        context_value = self._context.get(parts[0], match)
                        value = value.replace(
                            f"${{{match}}}", str(context_value)
                        )
                    elif len(parts) == 2:
                        # Step result lookup
                        step_id, field = parts
                        if step_id in self.results:
                            result = self.results[step_id].result
                            if hasattr(result, field):
                                field_value = getattr(result, field)
                            elif isinstance(result, dict):
                                field_value = result.get(field, match)
                            else:
                                field_value = match
                            value = value.replace(
                                f"${{{match}}}", str(field_value)
                            )
                            
            resolved[key] = value
            
        return resolved