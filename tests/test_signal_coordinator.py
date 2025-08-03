#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for SignalCoordinator
Tests cross-page signal coordination and state synchronization
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QWidget, QTabWidget
from PySide6.QtTest import QSignalSpy

from src.gui.components.signal_coordinator import (
    SignalCoordinator, FilterStateManager, SignalDebugger, retry_on_error
)


class MockPage(QWidget):
    """Mock page widget for testing"""
    
    # Signals that pages might have
    request_navigate_to_artifact = Signal(str)
    request_navigate_to_project = Signal(str)
    request_navigate_to_note = Signal(str)
    request_navigate_to_event = Signal(str)
    project_filter_requested = Signal(str)
    artifact_project_changed = Signal(str, str, str)
    artifact_unlinked_from_project = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self.navigate_to_artifact = Mock()
        self.navigate_to_project = Mock()
        self.navigate_to_note = Mock()
        self.navigate_to_event = Mock()
        self.apply_project_filter = Mock()
        
        # Mock project combo
        self.project_combo = Mock()
        self.project_combo.project_changed = Signal(str)


class MockTabbedContent(QObject):
    """Mock tabbed content widget"""
    
    def __init__(self):
        super().__init__()
        self.tab_widget = Mock(spec=QTabWidget)
        self.tab_widget.setCurrentIndex = Mock()
        self.tabs = [
            {'id': 'artifacts', 'widget': MockPage()},
            {'id': 'project', 'widget': MockPage()},
            {'id': 'notes', 'widget': MockPage()},
            {'id': 'appointments', 'widget': MockPage()},
        ]


class TestFilterStateManager:
    """Test FilterStateManager functionality"""
    
    def test_initialization(self):
        """Test FilterStateManager initialization"""
        manager = FilterStateManager()
        assert manager.current_project_id is None
        assert len(manager.subscribers) == 0
        assert manager._updating is False
    
    def test_set_project_filter(self):
        """Test setting project filter"""
        manager = FilterStateManager()
        
        # Set filter
        manager.set_project_filter("project123", "test_source")
        assert manager.current_project_id == "project123"
        
        # Setting same filter should not trigger updates
        manager.set_project_filter("project123", "test_source")
        assert manager.current_project_id == "project123"
    
    def test_subscribe_unsubscribe(self):
        """Test widget subscription/unsubscription"""
        manager = FilterStateManager()
        widget = MockPage()
        
        # Subscribe
        manager.subscribe(widget, "test_widget")
        assert len(manager.subscribers) == 1
        
        # Duplicate subscription should be ignored
        manager.subscribe(widget, "test_widget")
        assert len(manager.subscribers) == 1
        
        # Unsubscribe
        manager.unsubscribe("test_widget")
        assert len(manager.subscribers) == 0
    
    def test_notify_subscribers(self):
        """Test subscriber notification"""
        manager = FilterStateManager()
        widget1 = MockPage()
        widget2 = MockPage()
        
        # Subscribe widgets
        manager.subscribe(widget1, "widget1")
        manager.subscribe(widget2, "widget2")
        
        # Set filter (should notify both)
        manager.set_project_filter("project123", "widget1")
        
        # Widget2 should be notified, widget1 should not (it's the source)
        widget1.apply_project_filter.assert_not_called()
        widget2.apply_project_filter.assert_called_once_with("project123")
    
    def test_circular_update_prevention(self):
        """Test prevention of circular updates"""
        manager = FilterStateManager()
        widget = MockPage()
        
        manager.subscribe(widget, "widget1")
        
        # Simulate being in an update cycle
        manager._updating = True
        manager.set_project_filter("project123", "widget1")
        
        # Should not call apply_project_filter when updating
        widget.apply_project_filter.assert_not_called()


class TestSignalCoordinator:
    """Test SignalCoordinator functionality"""
    
    @pytest.fixture
    def coordinator(self):
        """Create a SignalCoordinator instance for testing"""
        tabbed_content = MockTabbedContent()
        return SignalCoordinator(tabbed_content)
    
    def test_initialization(self, coordinator):
        """Test SignalCoordinator initialization"""
        assert coordinator.tabbed_content is not None
        assert isinstance(coordinator.filter_state_manager, FilterStateManager)
        assert len(coordinator.pages) == 0
        assert coordinator._coordination_enabled is True
        assert coordinator._error_count == 0
    
    def test_register_page(self, coordinator):
        """Test page registration"""
        page = MockPage()
        
        # Register page
        coordinator.register_page("test_page", page)
        
        assert "test_page" in coordinator.pages
        assert coordinator.pages["test_page"] == page
        
        # Filter state should be subscribed
        assert len(coordinator.filter_state_manager.subscribers) == 1
    
    def test_unregister_page(self, coordinator):
        """Test page unregistration"""
        page = MockPage()
        
        # Register then unregister
        coordinator.register_page("test_page", page)
        coordinator.unregister_page("test_page")
        
        assert "test_page" not in coordinator.pages
        assert len(coordinator.filter_state_manager.subscribers) == 0
    
    def test_route_navigation(self, coordinator):
        """Test navigation routing"""
        # Register pages
        artifacts_page = MockPage()
        projects_page = MockPage()
        
        coordinator.register_page("artifacts", artifacts_page)
        coordinator.register_page("projects", projects_page)
        
        # Test navigation to artifacts
        coordinator._route_navigation("artifacts", "artifact123")
        
        # Should switch tab and call navigation method
        coordinator.tabbed_content.tab_widget.setCurrentIndex.assert_called_with(0)
        artifacts_page.navigate_to_artifact.assert_called_once_with("artifact123")
    
    def test_project_filter_change(self, coordinator):
        """Test project filter change handling"""
        page1 = MockPage()
        page2 = MockPage()
        
        coordinator.register_page("page1", page1)
        coordinator.register_page("page2", page2)
        
        # Change filter from page1
        coordinator._handle_project_combo_changed("project123", "page1")
        
        # Both pages should be updated (through FilterStateManager)
        assert coordinator.filter_state_manager.current_project_id == "project123"
    
    def test_batch_updates(self, coordinator):
        """Test batch update processing"""
        # Queue some updates
        coordinator._queue_batch_update('artifacts', 'artifact1')
        coordinator._queue_batch_update('artifacts', 'artifact2')
        coordinator._queue_batch_update('projects', 'project1')
        
        # Should have pending updates
        assert len(coordinator._pending_batch_updates['artifacts']) == 2
        assert len(coordinator._pending_batch_updates['projects']) == 1
        
        # Process batch updates
        spy_artifacts = QSignalSpy(coordinator.artifacts_batch_updated)
        spy_projects = QSignalSpy(coordinator.projects_batch_updated)
        
        coordinator._process_batch_updates()
        
        # Signals should be emitted
        assert spy_artifacts.count() == 1
        assert spy_projects.count() == 1
        
        # Pending updates should be cleared
        assert len(coordinator._pending_batch_updates['artifacts']) == 0
        assert len(coordinator._pending_batch_updates['projects']) == 0
    
    def test_error_handling(self, coordinator):
        """Test error handling and recording"""
        # Record some errors
        coordinator._record_error("test_error", "Error message 1")
        coordinator._record_error("test_error", "Error message 2")
        
        assert coordinator._error_count == 2
        assert coordinator._coordination_enabled is True
        
        # Record more errors to trigger circuit breaker
        for i in range(8):
            coordinator._record_error("test_error", f"Error {i+3}")
        
        # Should disable coordination
        assert coordinator._error_count == 10
        assert coordinator._coordination_enabled is False
    
    def test_error_reset(self, coordinator):
        """Test error count reset"""
        # Generate errors
        for i in range(5):
            coordinator._record_error("test_error", f"Error {i}")
        
        assert coordinator._error_count == 5
        
        # Reset
        coordinator.reset_error_count()
        
        assert coordinator._error_count == 0
        assert coordinator._coordination_enabled is True
        assert len(coordinator._error_timestamps) == 0
    
    def test_safe_handler(self, coordinator):
        """Test safe handler wrapper"""
        # Mock a failing handler
        def failing_handler():
            raise Exception("Test error")
        
        # Should not raise exception
        coordinator._safe_handler(failing_handler, "test")
        
        # Error should be recorded
        assert coordinator._error_count == 1
    
    def test_signal_blocking(self, coordinator):
        """Test signal blocking mechanism"""
        # Block a signal
        coordinator.block_signal("test_signal")
        assert coordinator.is_signal_blocked("test_signal")
        
        # Unblock
        coordinator.unblock_signal("test_signal")
        assert not coordinator.is_signal_blocked("test_signal")


class TestRetryDecorator:
    """Test retry_on_error decorator"""
    
    def test_successful_execution(self):
        """Test successful execution without retries"""
        call_count = 0
        
        class TestClass:
            logger = Mock()
            
            @retry_on_error(max_retries=3)
            def test_method(self):
                nonlocal call_count
                call_count += 1
                return "success"
        
        obj = TestClass()
        result = obj.test_method()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """Test retry on failure"""
        call_count = 0
        
        class TestClass:
            logger = Mock()
            
            @retry_on_error(max_retries=3, delay_ms=10)
            def test_method(self):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Test error")
                return "success"
        
        obj = TestClass()
        result = obj.test_method()
        
        assert result == "success"
        assert call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test when max retries are exceeded"""
        call_count = 0
        
        class TestClass:
            logger = Mock()
            
            @retry_on_error(max_retries=2, delay_ms=10)
            def test_method(self):
                nonlocal call_count
                call_count += 1
                raise Exception("Always fails")
        
        obj = TestClass()
        
        with pytest.raises(Exception, match="Always fails"):
            obj.test_method()
        
        assert call_count == 3  # Initial + 2 retries


class TestSignalDebugger:
    """Test SignalDebugger functionality"""
    
    @pytest.fixture
    def debugger(self):
        """Create a SignalDebugger instance"""
        tabbed_content = MockTabbedContent()
        coordinator = SignalCoordinator(tabbed_content)
        return SignalDebugger(coordinator)
    
    def test_initialization(self, debugger):
        """Test SignalDebugger initialization"""
        assert debugger.coordinator is not None
        assert len(debugger.signal_log) == 0
        assert debugger.debug_mode is False
    
    def test_signal_logging(self, debugger):
        """Test signal logging"""
        # Enable debug mode
        debugger.enable_debug_mode()
        assert debugger.debug_mode is True
        
        # Log a signal
        debugger.log_signal("test_signal", ("arg1", "arg2"))
        
        assert len(debugger.signal_log) == 1
        entry = debugger.signal_log[0]
        assert entry['signal'] == "test_signal"
        assert entry['args'] == ("arg1", "arg2")
        assert isinstance(entry['timestamp'], datetime)
    
    def test_log_size_limit(self, debugger):
        """Test log size limiting"""
        # Set small limit for testing
        debugger.max_log_entries = 5
        
        # Log more than limit
        for i in range(10):
            debugger.log_signal(f"signal_{i}", ())
        
        # Should only keep last 5
        assert len(debugger.signal_log) == 5
        assert debugger.signal_log[0]['signal'] == "signal_5"
        assert debugger.signal_log[-1]['signal'] == "signal_9"
    
    def test_get_signal_history(self, debugger):
        """Test getting signal history"""
        # Log various signals
        debugger.log_signal("signal_a", ())
        debugger.log_signal("signal_b", ())
        debugger.log_signal("signal_a", ())
        
        # Get all history
        all_history = debugger.get_signal_history()
        assert len(all_history) == 3
        
        # Get filtered history
        signal_a_history = debugger.get_signal_history("signal_a")
        assert len(signal_a_history) == 2
        assert all(entry['signal'] == "signal_a" for entry in signal_a_history)
    
    def test_clear_log(self, debugger):
        """Test clearing the log"""
        # Add some entries
        debugger.log_signal("test1", ())
        debugger.log_signal("test2", ())
        
        assert len(debugger.signal_log) > 0
        
        # Clear
        debugger.clear_log()
        assert len(debugger.signal_log) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])