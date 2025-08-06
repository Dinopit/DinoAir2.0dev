"""
State Machine Implementation for DinoAir 2.0
Manages application states and transitions with validation and events
"""

import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from .logger import Logger

logger = Logger()


class ApplicationState(Enum):
    """Core application states."""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TransitionResult(Enum):
    """Results of state transitions."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    INVALID = "invalid"


@dataclass
class StateTransition:
    """Information about a state transition."""
    from_state: ApplicationState
    to_state: ApplicationState
    timestamp: datetime
    duration_ms: int
    result: TransitionResult
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateInfo:
    """Information about a state."""
    state: ApplicationState
    entry_time: datetime
    duration_ms: int = 0
    entry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateValidator(ABC):
    """Abstract base class for state validators."""
    
    @abstractmethod
    def can_transition(self, 
                      from_state: ApplicationState, 
                      to_state: ApplicationState,
                      context: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if transition is valid.
        
        Returns:
            (is_valid, error_message)
        """
        pass


class DefaultStateValidator(StateValidator):
    """Default state validator with basic transition rules."""
    
    def __init__(self):
        # Define valid transitions
        self._valid_transitions = {
            ApplicationState.INITIALIZING: {
                ApplicationState.STARTING,
                ApplicationState.ERROR,
                ApplicationState.SHUTDOWN
            },
            ApplicationState.STARTING: {
                ApplicationState.RUNNING,
                ApplicationState.ERROR,
                ApplicationState.SHUTTING_DOWN
            },
            ApplicationState.RUNNING: {
                ApplicationState.PAUSING,
                ApplicationState.SHUTTING_DOWN,
                ApplicationState.ERROR,
                ApplicationState.MAINTENANCE
            },
            ApplicationState.PAUSING: {
                ApplicationState.PAUSED,
                ApplicationState.ERROR,
                ApplicationState.SHUTTING_DOWN
            },
            ApplicationState.PAUSED: {
                ApplicationState.RESUMING,
                ApplicationState.SHUTTING_DOWN,
                ApplicationState.ERROR
            },
            ApplicationState.RESUMING: {
                ApplicationState.RUNNING,
                ApplicationState.ERROR,
                ApplicationState.SHUTTING_DOWN
            },
            ApplicationState.MAINTENANCE: {
                ApplicationState.RUNNING,
                ApplicationState.SHUTTING_DOWN,
                ApplicationState.ERROR
            },
            ApplicationState.ERROR: {
                ApplicationState.SHUTTING_DOWN,
                ApplicationState.SHUTDOWN,
                ApplicationState.MAINTENANCE
            },
            ApplicationState.SHUTTING_DOWN: {
                ApplicationState.SHUTDOWN,
                ApplicationState.ERROR
            },
            ApplicationState.SHUTDOWN: set()  # Terminal state
        }
        
    def can_transition(self, 
                      from_state: ApplicationState, 
                      to_state: ApplicationState,
                      context: Dict[str, Any]) -> tuple[bool, str]:
        """Check if transition is valid according to state machine rules."""
        valid_targets = self._valid_transitions.get(from_state, set())
        
        if to_state in valid_targets:
            return True, ""
        else:
            return False, f"Invalid transition from {from_state.value} to {to_state.value}"


class StateMachine:
    """
    Thread-safe state machine for managing application states.
    
    Features:
    - State validation and transition rules
    - Event callbacks for state changes
    - State history and metrics
    - Concurrent access protection
    """
    
    def __init__(self, 
                 initial_state: ApplicationState = ApplicationState.INITIALIZING,
                 validator: Optional[StateValidator] = None):
        self._current_state = initial_state
        self._previous_state: Optional[ApplicationState] = None
        self._lock = threading.RLock()
        
        # State management
        self._validator = validator or DefaultStateValidator()
        self._state_history: List[StateTransition] = []
        self._state_info: Dict[ApplicationState, StateInfo] = {}
        self._state_entry_time = datetime.now()
        
        # Event callbacks
        self._enter_callbacks: Dict[ApplicationState, List[Callable]] = {}
        self._exit_callbacks: Dict[ApplicationState, List[Callable]] = {}
        self._transition_callbacks: List[Callable] = []
        
        # Initialize current state info
        self._state_info[initial_state] = StateInfo(
            state=initial_state,
            entry_time=self._state_entry_time,
            entry_count=1
        )
        
        logger.info(f"State machine initialized in state: {initial_state.value}")
        
    def get_current_state(self) -> ApplicationState:
        """Get the current state."""
        with self._lock:
            return self._current_state
            
    def get_previous_state(self) -> Optional[ApplicationState]:
        """Get the previous state."""
        with self._lock:
            return self._previous_state
            
    def transition_to(self, 
                     new_state: ApplicationState,
                     context: Optional[Dict[str, Any]] = None,
                     force: bool = False) -> TransitionResult:
        """
        Transition to a new state.
        
        Args:
            new_state: Target state
            context: Additional context for the transition
            force: Skip validation if True
            
        Returns:
            Result of the transition
        """
        context = context or {}
        start_time = datetime.now()
        
        with self._lock:
            current = self._current_state
            
            # Skip if already in target state
            if current == new_state:
                logger.debug(f"Already in state: {new_state.value}")
                return TransitionResult.SUCCESS
                
            # Validate transition unless forced
            if not force:
                can_transition, error_msg = self._validator.can_transition(
                    current, new_state, context
                )
                if not can_transition:
                    logger.warning(f"Transition blocked: {error_msg}")
                    self._record_transition(
                        current, new_state, start_time, 
                        TransitionResult.BLOCKED, error_msg, context
                    )
                    return TransitionResult.BLOCKED
                    
            try:
                # Call exit callbacks for current state
                self._call_exit_callbacks(current, new_state, context)
                
                # Update state info for current state
                if current in self._state_info:
                    state_info = self._state_info[current]
                    state_info.duration_ms = int(
                        (start_time - self._state_entry_time).total_seconds() * 1000
                    )
                
                # Transition to new state
                self._previous_state = current
                self._current_state = new_state
                self._state_entry_time = start_time
                
                # Update state info for new state
                if new_state not in self._state_info:
                    self._state_info[new_state] = StateInfo(
                        state=new_state,
                        entry_time=start_time,
                        entry_count=1
                    )
                else:
                    info = self._state_info[new_state]
                    info.entry_time = start_time
                    info.entry_count += 1
                    
                # Call enter callbacks for new state
                self._call_enter_callbacks(new_state, current, context)
                
                # Call transition callbacks
                self._call_transition_callbacks(current, new_state, context)
                
                # Record successful transition
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self._record_transition(
                    current, new_state, start_time, 
                    TransitionResult.SUCCESS, None, context, duration_ms
                )
                
                logger.info(f"State transition: {current.value} -> {new_state.value}")
                return TransitionResult.SUCCESS
                
            except Exception as e:
                logger.error(f"Error during state transition: {e}")
                
                # Record failed transition
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self._record_transition(
                    current, new_state, start_time,
                    TransitionResult.FAILED, str(e), context, duration_ms
                )
                
                return TransitionResult.FAILED
                
    def _record_transition(self,
                          from_state: ApplicationState,
                          to_state: ApplicationState,
                          timestamp: datetime,
                          result: TransitionResult,
                          error_message: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None,
                          duration_ms: int = 0):
        """Record a state transition in history."""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=timestamp,
            duration_ms=duration_ms,
            result=result,
            error_message=error_message,
            metadata=context.copy() if context else {}
        )
        
        self._state_history.append(transition)
        
        # Keep history size manageable
        if len(self._state_history) > 1000:
            self._state_history = self._state_history[-500:]
            
    def on_enter(self, state: ApplicationState, callback: Callable):
        """Register callback for state entry."""
        with self._lock:
            if state not in self._enter_callbacks:
                self._enter_callbacks[state] = []
            self._enter_callbacks[state].append(callback)
            
    def on_exit(self, state: ApplicationState, callback: Callable):
        """Register callback for state exit."""
        with self._lock:
            if state not in self._exit_callbacks:
                self._exit_callbacks[state] = []
            self._exit_callbacks[state].append(callback)
            
    def on_transition(self, callback: Callable):
        """Register callback for any state transition."""
        with self._lock:
            self._transition_callbacks.append(callback)
            
    def _call_enter_callbacks(self, 
                             state: ApplicationState,
                             from_state: ApplicationState,
                             context: Dict[str, Any]):
        """Call enter callbacks for a state."""
        callbacks = self._enter_callbacks.get(state, [])
        for callback in callbacks:
            try:
                callback(state, from_state, context)
            except Exception as e:
                logger.error(f"Error in enter callback for {state.value}: {e}")
                
    def _call_exit_callbacks(self,
                            state: ApplicationState,
                            to_state: ApplicationState,
                            context: Dict[str, Any]):
        """Call exit callbacks for a state."""
        callbacks = self._exit_callbacks.get(state, [])
        for callback in callbacks:
            try:
                callback(state, to_state, context)
            except Exception as e:
                logger.error(f"Error in exit callback for {state.value}: {e}")
                
    def _call_transition_callbacks(self,
                                  from_state: ApplicationState,
                                  to_state: ApplicationState,
                                  context: Dict[str, Any]):
        """Call transition callbacks."""
        for callback in self._transition_callbacks:
            try:
                callback(from_state, to_state, context)
            except Exception as e:
                logger.error(f"Error in transition callback: {e}")
                
    def get_state_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get state transition history."""
        with self._lock:
            history = self._state_history.copy()
            if limit:
                history = history[-limit:]
            return history
            
    def get_state_info(self, state: ApplicationState) -> Optional[StateInfo]:
        """Get information about a specific state."""
        with self._lock:
            return self._state_info.get(state)
            
    def get_all_state_info(self) -> Dict[ApplicationState, StateInfo]:
        """Get information about all states."""
        with self._lock:
            return self._state_info.copy()
            
    def get_current_state_duration(self) -> int:
        """Get duration in current state (milliseconds)."""
        with self._lock:
            return int((datetime.now() - self._state_entry_time).total_seconds() * 1000)
            
    def is_in_state(self, *states: ApplicationState) -> bool:
        """Check if current state is one of the specified states."""
        with self._lock:
            return self._current_state in states
            
    def wait_for_state(self, 
                      target_state: ApplicationState,
                      timeout: float = 10.0) -> bool:
        """
        Wait for the state machine to reach a specific state.
        
        Args:
            target_state: State to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if state was reached, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.get_current_state() == target_state:
                return True
            time.sleep(0.1)
            
        return False
        
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        with self._lock:
            current_duration = self.get_current_state_duration()
            
            # Calculate state statistics
            state_stats = {}
            total_transitions = len(self._state_history)
            successful_transitions = sum(
                1 for t in self._state_history 
                if t.result == TransitionResult.SUCCESS
            )
            
            for state, info in self._state_info.items():
                state_stats[state.value] = {
                    'entry_count': info.entry_count,
                    'last_entry': info.entry_time.isoformat(),
                    'last_duration_ms': info.duration_ms
                }
                
            return {
                'current_state': self._current_state.value,
                'previous_state': self._previous_state.value if self._previous_state else None,
                'current_state_duration_ms': current_duration,
                'total_transitions': total_transitions,
                'successful_transitions': successful_transitions,
                'success_rate': (successful_transitions / total_transitions * 100) if total_transitions > 0 else 100,
                'state_statistics': state_stats,
                'recent_transitions': [
                    {
                        'from': t.from_state.value,
                        'to': t.to_state.value,
                        'timestamp': t.timestamp.isoformat(),
                        'result': t.result.value,
                        'duration_ms': t.duration_ms,
                        'error': t.error_message
                    }
                    for t in self._state_history[-10:]  # Last 10 transitions
                ]
            }
            
    def reset(self, initial_state: ApplicationState = ApplicationState.INITIALIZING):
        """Reset the state machine to initial state."""
        with self._lock:
            logger.info("Resetting state machine")
            
            old_state = self._current_state
            self._current_state = initial_state
            self._previous_state = None
            self._state_entry_time = datetime.now()
            self._state_history.clear()
            self._state_info.clear()
            
            # Initialize new state info
            self._state_info[initial_state] = StateInfo(
                state=initial_state,
                entry_time=self._state_entry_time,
                entry_count=1
            )
            
            # Record reset transition
            self._record_transition(
                old_state, initial_state, self._state_entry_time,
                TransitionResult.SUCCESS, "State machine reset"
            )


# Global state machine instance
_state_machine = None
_state_machine_lock = threading.Lock()


def get_state_machine() -> StateMachine:
    """Get the global state machine instance."""
    global _state_machine
    
    if _state_machine is None:
        with _state_machine_lock:
            if _state_machine is None:
                _state_machine = StateMachine()
                
    return _state_machine


def get_current_state() -> ApplicationState:
    """Convenience function to get current state."""
    return get_state_machine().get_current_state()


def transition_to_state(state: ApplicationState, 
                       context: Optional[Dict[str, Any]] = None,
                       force: bool = False) -> TransitionResult:
    """Convenience function to transition state."""
    return get_state_machine().transition_to(state, context, force)