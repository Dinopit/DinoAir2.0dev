"""
Signal Coordination System for DinoAir 2.0
Manages cross-page communication and state synchronization
"""

from typing import Dict, Optional, Any, List, Tuple, Set, Callable
from datetime import datetime
from functools import wraps
from PySide6.QtCore import QObject, Signal, QTimer, Slot
from PySide6.QtWidgets import QWidget

from ...utils.logger import Logger


def retry_on_error(max_retries: int = 3, delay_ms: int = 100):
    """Decorator to retry operations on error with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_ms: Initial delay between retries in milliseconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= max_retries:
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    retries += 1
                    
                    if retries <= max_retries:
                        # Exponential backoff
                        delay = delay_ms * (2 ** (retries - 1))
                        self.logger.warning(
                            f"Error in {func.__name__}, retry {retries}/{max_retries} "
                            f"after {delay}ms: {str(e)}"
                        )
                        # Use QTimer for non-blocking delay
                        timer = QTimer()
                        timer.setSingleShot(True)
                        timer.timeout.connect(lambda: None)
                        timer.start(delay)
                    else:
                        self.logger.error(
                            f"Failed after {max_retries} retries in {func.__name__}: "
                            f"{str(e)}"
                        )
                        # Re-raise the last error
                        raise last_error
            
        return wrapper
    return decorator


class FilterStateManager:
    """Manages synchronized filter state across pages"""
    
    def __init__(self):
        self.current_project_id: Optional[str] = None
        # List of (widget, widget_id) tuples
        self.subscribers: List[Tuple[QWidget, str]] = []
        self.logger = Logger()
        self._updating = False  # Prevent circular updates
        
    def set_project_filter(self, project_id: Optional[str],
                           source: Optional[str] = None):
        """Update project filter and notify subscribers
        
        Args:
            project_id: The project ID to filter by, or None for no filter
            source: The widget ID that triggered the change
        """
        if self._updating:
            return
            
        if self.current_project_id != project_id:
            old_id = self.current_project_id
            self.current_project_id = project_id
            self.logger.info(
                f"Project filter changed: {old_id} -> {project_id} "
                f"(source: {source})"
            )
            self._notify_subscribers(project_id, source)
    
    def subscribe(self, widget: QWidget, widget_id: str):
        """Subscribe a widget to filter state changes
        
        Args:
            widget: The widget to subscribe
            widget_id: Unique identifier for the widget
        """
        # Check if already subscribed
        for existing_widget, existing_id in self.subscribers:
            if existing_id == widget_id:
                self.logger.warning(f"Widget {widget_id} already subscribed")
                return
                
        self.subscribers.append((widget, widget_id))
        self.logger.info(f"Widget {widget_id} subscribed to filter state")
        
        # Apply current filter immediately if widget supports it
        if (hasattr(widget, 'apply_project_filter') and
                self.current_project_id is not None):
            # type: ignore
            widget.apply_project_filter(self.current_project_id)
            
    def unsubscribe(self, widget_id: str):
        """Unsubscribe a widget from filter state changes
        
        Args:
            widget_id: The widget ID to unsubscribe
        """
        self.subscribers = [(w, wid) for w, wid in self.subscribers
                            if wid != widget_id]
        self.logger.info(f"Widget {widget_id} unsubscribed from filter state")
        
    def _notify_subscribers(self, project_id: Optional[str],
                            source: Optional[str] = None):
        """Notify all subscribers of filter change
        
        Args:
            project_id: The new project filter ID
            source: The widget that triggered the change
        """
        self._updating = True
        try:
            for widget, widget_id in self.subscribers:
                # Skip the source widget to prevent circular updates
                if widget_id == source:
                    continue
                    
                try:
                    if hasattr(widget, 'apply_project_filter'):
                        widget.apply_project_filter(project_id)  # type: ignore
                    else:
                        self.logger.warning(
                            f"Widget {widget_id} has no "
                            "apply_project_filter method"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error notifying widget {widget_id}: {str(e)}"
                    )
        finally:
            self._updating = False
            
    def get_current_filter(self) -> Optional[str]:
        """Get the current project filter
        
        Returns:
            The current project ID filter or None
        """
        return self.current_project_id
        
    def clear_filter(self, source: Optional[str] = None):
        """Clear the current project filter
        
        Args:
            source: The widget ID that triggered the clear
        """
        self.set_project_filter(None, source)


class SignalCoordinator(QObject):
    """Central coordinator for cross-page signals and state synchronization"""
    
    # Cross-page navigation signals
    navigate_to_artifact = Signal(str)  # artifact_id
    navigate_to_project = Signal(str)   # project_id
    navigate_to_note = Signal(str)      # note_id
    navigate_to_event = Signal(str)     # event_id
    
    # Project filter synchronization
    # project_id or None (emitted as empty string)
    project_filter_changed = Signal(str)
    
    # Real-time update signals
    artifact_linked_to_project = Signal(str, str)    # artifact_id, project_id
    # artifact_id, project_id
    artifact_unlinked_from_project = Signal(str, str)
    project_updated = Signal(str)                     # project_id
    artifact_updated = Signal(str)                    # artifact_id
    note_updated = Signal(str)                        # note_id
    event_updated = Signal(str)                       # event_id
    
    # Batch update signals for performance
    artifacts_batch_updated = Signal(list)  # List of artifact_ids
    projects_batch_updated = Signal(list)   # List of project_ids
    notes_batch_updated = Signal(list)      # List of note_ids
    
    # Status signals
    coordination_error = Signal(str, str)  # error_type, error_message
    coordination_disabled = Signal(str)  # reason
    coordination_enabled = Signal()
    
    def __init__(self, tabbed_content):
        """Initialize the signal coordinator
        
        Args:
            tabbed_content: The TabbedContentWidget instance
        """
        super().__init__()
        self.logger = Logger()
        self.tabbed_content = tabbed_content
        self.pages: Dict[str, QWidget] = {}  # Registered pages
        self.filter_state_manager = FilterStateManager()
        self._blocked_signals: Set[str] = set()  # Prevent circular updates
        self._pending_batch_updates: Dict[str, List[str]] = {
            'artifacts': [],
            'projects': [],
            'notes': []
        }
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._process_batch_updates)
        self._batch_timer.setInterval(100)  # 100ms delay for batching
        
        # Error handling and circuit breaker
        self._error_count = 0
        self._max_errors = 10  # Maximum errors before disabling
        self._error_window_ms = 60000  # 1 minute window for error counting
        self._error_timestamps: List[datetime] = []
        self._coordination_enabled = True
        
        # Connect internal signals
        self.project_filter_changed.connect(self._on_project_filter_changed)
        
        self.logger.info("SignalCoordinator initialized")
        
    def register_page(self, page_id: str, page_widget: QWidget):
        """Register a page for signal coordination
        
        Args:
            page_id: Unique identifier for the page
            page_widget: The page widget instance
        """
        if page_id in self.pages:
            self.logger.warning(
                f"Page {page_id} already registered, replacing"
            )
            
        self.pages[page_id] = page_widget
        self._connect_page_signals(page_id, page_widget)
        
        # Subscribe to filter state if supported
        if hasattr(page_widget, 'apply_project_filter'):
            self.filter_state_manager.subscribe(page_widget, page_id)
            
        self.logger.info(f"Page {page_id} registered with coordinator")
        
    def unregister_page(self, page_id: str):
        """Unregister a page from signal coordination
        
        Args:
            page_id: The page ID to unregister
        """
        if page_id in self.pages:
            # Unsubscribe from filter state
            self.filter_state_manager.unsubscribe(page_id)
            
            # Remove from pages dict
            del self.pages[page_id]
            self.logger.info(f"Page {page_id} unregistered from coordinator")
            
    @retry_on_error(max_retries=2, delay_ms=50)
    def _connect_page_signals(self, page_id: str, page_widget: QWidget):
        """Connect signals from a specific page with error handling
        
        Args:
            page_id: The page identifier
            page_widget: The page widget
        """
        if not self._check_coordination_enabled():
            return
            
        try:
            # Map of signal names to handler methods
            signal_handlers = {
                'request_navigate_to_artifact':
                    lambda aid: self._safe_handler(
                        lambda: self._route_navigation('artifacts', aid),
                        'navigation'
                    ),
                'request_navigate_to_project':
                    lambda pid: self._safe_handler(
                        lambda: self._route_navigation('projects', pid),
                        'navigation'
                    ),
                'request_navigate_to_note':
                    lambda nid: self._safe_handler(
                        lambda: self._route_navigation('notes', nid),
                        'navigation'
                    ),
                'request_navigate_to_event':
                    lambda eid: self._safe_handler(
                        lambda: self._route_navigation('appointments', eid),
                        'navigation'
                    ),
                'project_filter_requested':
                    lambda pid: self._safe_handler(
                        lambda: self.filter_state_manager.set_project_filter(
                            pid, page_id),
                        'filter'
                    ),
                'artifact_project_changed':
                    lambda *args: self._safe_handler(
                        lambda: self._handle_artifact_project_changed(*args),
                        'update'
                    ),
                'artifact_unlinked_from_project':
                    lambda aid, pid: self._safe_handler(
                        lambda: self.emit_artifact_unlinked(aid, pid),
                        'update'
                    ),
                'note_unlinked_from_project':
                    lambda nid, pid: self._safe_handler(
                        lambda: self.note_updated.emit(nid),
                        'update'
                    ),
                'event_unlinked_from_project':
                    lambda eid, pid: self._safe_handler(
                        lambda: self.event_updated.emit(eid),
                        'update'
                    ),
            }
            
            # Connect available signals
            for signal_name, handler in signal_handlers.items():
                if hasattr(page_widget, signal_name):
                    signal = getattr(page_widget, signal_name)
                    signal.connect(handler)
                    self.logger.debug(f"Connected {signal_name} from {page_id}")
                    
            # Special handling for project combo box changes
            if hasattr(page_widget, 'project_combo'):
                combo = getattr(page_widget, 'project_combo')
                if hasattr(combo, 'project_changed'):
                    combo.project_changed.connect(
                        lambda pid: self._safe_handler(
                            lambda: self._handle_project_combo_changed(pid, page_id),
                            'filter'
                        )
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to connect signals for {page_id}: {str(e)}")
            self._record_error('signal_connection', str(e))
            
    @Slot(str)
    def _on_project_filter_changed(self, project_id: str):
        """Handle project filter change signal
        
        Args:
            project_id: The new project filter (empty string for None)
        """
        # Convert empty string back to None
        actual_id = project_id if project_id else None
        self.filter_state_manager.set_project_filter(actual_id, "signal")
        
    def _handle_project_combo_changed(self, project_id: Optional[str],
                                      source_page: str):
        """Handle project combo box change from a page
        
        Args:
            project_id: The selected project ID
            source_page: The page that triggered the change
        """
        self.filter_state_manager.set_project_filter(project_id, source_page)
        # Emit signal for other components (empty string for None)
        self.project_filter_changed.emit(project_id or "")
        
    @retry_on_error(max_retries=2, delay_ms=100)
    def _route_navigation(self, target_page: str, item_id: str):
        """Route navigation request to appropriate page with retry
        
        Args:
            target_page: The target page ID
            item_id: The item ID to navigate to
        """
        if not self._check_coordination_enabled():
            return
            
        try:
            # Find the tab index for the target page
            tab_index = self._find_tab_index(target_page)
            if tab_index is None:
                error_msg = f"Target page {target_page} not found in tabs"
                self.logger.error(error_msg)
                self._record_error('navigation', error_msg)
                return
                
            # Switch to the target tab
            self.tabbed_content.tab_widget.setCurrentIndex(tab_index)
            
            # Call navigation method on target page
            if target_page in self.pages:
                page_widget = self.pages[target_page]
                navigation_methods = {
                    'artifacts': 'navigate_to_artifact',
                    'projects': 'navigate_to_project',
                    'notes': 'navigate_to_note',
                    'appointments': 'navigate_to_event'
                }
                
                method_name = navigation_methods.get(target_page)
                if method_name and hasattr(page_widget, method_name):
                    method = getattr(page_widget, method_name)
                    method(item_id)
                    self.logger.info(
                        f"Navigated to {item_id} in {target_page}"
                    )
                else:
                    self.logger.warning(
                        f"Page {target_page} has no {method_name} method"
                    )
                    
        except Exception as e:
            self.logger.error(f"Navigation error: {str(e)}")
            self._record_error('navigation', str(e))
            
    def _find_tab_index(self, page_id: str) -> Optional[int]:
        """Find the tab index for a given page ID
        
        Args:
            page_id: The page ID to find
            
        Returns:
            The tab index or None if not found
        """
        # Map page IDs to tab IDs
        page_to_tab = {
            'artifacts': 'artifacts',
            'projects': 'project',  # Note: tab ID is 'project', not 'projects'
            'notes': 'notes',
            'appointments': 'appointments',
            'file_search': 'file_search'
        }
        
        tab_id = page_to_tab.get(page_id, page_id)
        
        # Find the tab index
        for i, tab in enumerate(self.tabbed_content.tabs):
            if tab['id'] == tab_id:
                return i
                
        return None
        
    def _handle_artifact_project_changed(self, artifact_id: str,
                                         old_project_id: str,
                                         new_project_id: str):
        """Handle artifact project change
        
        Args:
            artifact_id: The artifact that changed
            old_project_id: The previous project ID
            new_project_id: The new project ID
        """
        if old_project_id:
            self.artifact_unlinked_from_project.emit(
                artifact_id, old_project_id
            )
        if new_project_id:
            self.artifact_linked_to_project.emit(artifact_id, new_project_id)
            
        # Queue batch update
        self._queue_batch_update('artifacts', artifact_id)
        
    def _queue_batch_update(self, update_type: str, item_id: str):
        """Queue an item for batch update
        
        Args:
            update_type: Type of update ('artifacts', 'projects', 'notes')
            item_id: The item ID to update
        """
        if update_type in self._pending_batch_updates:
            if item_id not in self._pending_batch_updates[update_type]:
                self._pending_batch_updates[update_type].append(item_id)
                
            # Start timer if not already running
            if not self._batch_timer.isActive():
                self._batch_timer.start()
                
    @Slot()
    @retry_on_error(max_retries=1, delay_ms=50)
    def _process_batch_updates(self):
        """Process pending batch updates with error handling"""
        try:
            self._batch_timer.stop()
            
            # Process each type
            if self._pending_batch_updates['artifacts']:
                unique_ids = list(set(self._pending_batch_updates['artifacts']))
                self.artifacts_batch_updated.emit(unique_ids)
                self._pending_batch_updates['artifacts'] = []
                
            if self._pending_batch_updates['projects']:
                unique_ids = list(set(self._pending_batch_updates['projects']))
                self.projects_batch_updated.emit(unique_ids)
                self._pending_batch_updates['projects'] = []
                
            if self._pending_batch_updates['notes']:
                unique_ids = list(set(self._pending_batch_updates['notes']))
                self.notes_batch_updated.emit(unique_ids)
                self._pending_batch_updates['notes'] = []
                
        except Exception as e:
            self.logger.error(f"Batch update processing failed: {str(e)}")
            self._record_error('batch_update', str(e))
            
    def emit_artifact_linked(self, artifact_id: str, project_id: str):
        """Emit artifact linked signal
        
        Args:
            artifact_id: The artifact ID
            project_id: The project ID
        """
        self.artifact_linked_to_project.emit(artifact_id, project_id)
        self._queue_batch_update('artifacts', artifact_id)
        self._queue_batch_update('projects', project_id)
        
    def emit_artifact_unlinked(self, artifact_id: str, project_id: str):
        """Emit artifact unlinked signal
        
        Args:
            artifact_id: The artifact ID
            project_id: The project ID
        """
        self.artifact_unlinked_from_project.emit(artifact_id, project_id)
        self._queue_batch_update('artifacts', artifact_id)
        self._queue_batch_update('projects', project_id)
        
    def block_signal(self, signal_name: str):
        """Temporarily block a signal to prevent circular updates
        
        Args:
            signal_name: The signal name to block
        """
        self._blocked_signals.add(signal_name)
        
    def unblock_signal(self, signal_name: str):
        """Unblock a previously blocked signal
        
        Args:
            signal_name: The signal name to unblock
        """
        self._blocked_signals.discard(signal_name)
        
    def is_signal_blocked(self, signal_name: str) -> bool:
        """Check if a signal is currently blocked
        
        Args:
            signal_name: The signal name to check
            
        Returns:
            True if the signal is blocked
        """
        return signal_name in self._blocked_signals
    
    def _safe_handler(self, handler_func: Callable, error_type: str):
        """Wrap handler functions with error handling
        
        Args:
            handler_func: The function to execute safely
            error_type: Type of error for categorization
        """
        try:
            handler_func()
        except Exception as e:
            self.logger.error(f"Handler error ({error_type}): {str(e)}")
            self._record_error(error_type, str(e))
    
    def _record_error(self, error_type: str, error_msg: str):
        """Record an error and check circuit breaker
        
        Args:
            error_type: Type of error
            error_msg: Error message
        """
        # Add timestamp
        now = datetime.now()
        self._error_timestamps.append(now)
        
        # Remove old timestamps outside window
        cutoff = now.timestamp() - (self._error_window_ms / 1000)
        self._error_timestamps = [
            ts for ts in self._error_timestamps
            if ts.timestamp() > cutoff
        ]
        
        # Update error count
        self._error_count = len(self._error_timestamps)
        
        # Emit error signal
        self.coordination_error.emit(error_type, error_msg)
        
        # Check circuit breaker
        if self._error_count >= self._max_errors and self._coordination_enabled:
            self._coordination_enabled = False
            self.logger.error(
                f"Maximum errors ({self._max_errors}) reached in "
                f"{self._error_window_ms}ms window, disabling coordination"
            )
            self.coordination_disabled.emit(
                f"Too many errors ({self._error_count})"
            )
    
    def _check_coordination_enabled(self) -> bool:
        """Check if coordination is enabled
        
        Returns:
            True if coordination is enabled
        """
        if not self._coordination_enabled:
            self.logger.warning("Coordination disabled due to errors")
        return self._coordination_enabled
    
    def reset_error_count(self):
        """Reset error count and re-enable coordination"""
        self._error_count = 0
        self._error_timestamps.clear()
        self._coordination_enabled = True
        self.logger.info("Error count reset, coordination re-enabled")
        self.coordination_enabled.emit()
    
    def get_error_status(self) -> Dict[str, Any]:
        """Get current error status
        
        Returns:
            Dictionary with error status information
        """
        return {
            'enabled': self._coordination_enabled,
            'error_count': self._error_count,
            'max_errors': self._max_errors,
            'error_window_ms': self._error_window_ms,
            'recent_errors': len(self._error_timestamps)
        }


class SignalDebugger:
    """Debug and monitor signal flow"""
    
    def __init__(self, coordinator: SignalCoordinator):
        """Initialize the signal debugger
        
        Args:
            coordinator: The SignalCoordinator instance to debug
        """
        self.coordinator = coordinator
        self.signal_log: List[Dict[str, Any]] = []
        self.debug_mode = False
        self.max_log_entries = 1000
        self._connect_debug_slots()
        
    def _connect_debug_slots(self):
        """Connect to all signals for debugging"""
        signals = [
            ('navigate_to_artifact',
             self.coordinator.navigate_to_artifact),
            ('navigate_to_project',
             self.coordinator.navigate_to_project),
            ('navigate_to_note',
             self.coordinator.navigate_to_note),
            ('navigate_to_event',
             self.coordinator.navigate_to_event),
            ('project_filter_changed',
             self.coordinator.project_filter_changed),
            ('artifact_linked_to_project',
             self.coordinator.artifact_linked_to_project),
            ('artifact_unlinked_from_project',
             self.coordinator.artifact_unlinked_from_project),
            ('project_updated',
             self.coordinator.project_updated),
            ('artifact_updated',
             self.coordinator.artifact_updated),
            ('artifacts_batch_updated',
             self.coordinator.artifacts_batch_updated),
            ('projects_batch_updated',
             self.coordinator.projects_batch_updated),
            ('coordination_error',
             self.coordinator.coordination_error),
        ]
        
        for signal_name, signal in signals:
            signal.connect(
                lambda *args, name=signal_name: self.log_signal(name, args)
            )
            
    def log_signal(self, signal_name: str, args: tuple):
        """
        Record a signal emission in the internal signal log and optionally emit a debug entry.
        
        Appends a log entry containing a timestamp, the signal name, provided arguments, and a short stack trace to self.signal_log (kept to at most self.max_log_entries). When debug_mode is True, emits a one-line debug message to the coordinator's logger describing the signal and its arguments.
        
        Parameters:
            signal_name (str): The identifier of the emitted signal.
            args (tuple): The positional arguments passed with the signal; these are stored and joined for the debug message.
        
        Returns:
            None
        """
        import traceback
        
        entry = {
            'timestamp': datetime.now(),
            'signal': signal_name,
            'args': args,
            'stack_trace': traceback.extract_stack(limit=10)
        }
        
        self.signal_log.append(entry)
        
        # Limit log size
        if len(self.signal_log) > self.max_log_entries:
            self.signal_log.pop(0)
            
        if self.debug_mode:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            args_str = ', '.join(str(arg) for arg in args)
            self.coordinator.logger.debug(f"[SIGNAL] {timestamp} - {signal_name}({args_str})")
            
    def enable_debug_mode(self):
        """
        Enable verbose signal logging for the associated SignalCoordinator.
        
        When enabled, the SignalDebugger will emit detailed debug entries to the coordinator's logger for each observed signal. This toggles internal debug_mode to True and records an informational message via the coordinator logger.
        """
        self.debug_mode = True
        self.coordinator.logger.info("Signal debug mode enabled")
        
    def disable_debug_mode(self):
        """Disable debug output to console"""
        self.debug_mode = False
        self.coordinator.logger.info("Signal debug mode disabled")
        
    def get_signal_history(self, signal_name: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get signal history
        
        Args:
            signal_name: Filter by signal name (optional)
            limit: Maximum number of entries to return
            
        Returns:
            List of signal log entries
        """
        if signal_name:
            filtered_log = [entry for entry in self.signal_log
                            if entry['signal'] == signal_name]
        else:
            filtered_log = self.signal_log
            
        return filtered_log[-limit:]
        
    def clear_log(self):
        """Clear the signal log"""
        self.signal_log.clear()
        
    def print_summary(self):
        """
        Log an informational summary of recorded signal activity.
        
        Produces an info-level summary (via self.coordinator.logger) that includes the total number of logged signals and a count per signal name derived from self.signal_log. Does not return a value.
        """
        from collections import Counter
        
        signal_counts = Counter(entry['signal'] for entry in self.signal_log)
        
        logger = self.coordinator.logger
        logger.info("\n=== Signal Activity Summary ===")
        logger.info(f"Total signals logged: {len(self.signal_log)}")
        logger.info("\nSignal counts:")
        for signal_name, count in signal_counts.most_common():
            logger.info(f"  {signal_name}: {count}")
        logger.info("==============================\n")