#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for Signal Coordination System
Tests end-to-end workflows for cross-page navigation and state synchronization
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtCore import QObject, Signal, QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from src.gui.components.signal_coordinator import SignalCoordinator, FilterStateManager
from src.gui.components.tabbed_content import TabbedContentWidget
from src.gui.pages.artifacts_page import ArtifactsPage
from src.gui.pages.tasks_page import ProjectsPage
from src.gui.pages.notes_page import NotesPage


class TestSignalCoordinationIntegration:
    """Integration tests for signal coordination across pages"""
    
    @pytest.fixture(scope="class")
    def qapp(self):
        """Create QApplication for tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        
    @pytest.fixture
    def mock_tabbed_content(self, qapp):
        """Create a mock TabbedContentWidget with real pages"""
        # Create mock tabbed content
        tabbed = Mock(spec=TabbedContentWidget)
        tabbed.tab_widget = Mock()
        tabbed.tab_widget.setCurrentIndex = Mock()
        
        # Create real page instances (mocked databases)
        with patch('src.gui.pages.artifacts_page.ArtifactsDatabase'), \
             patch('src.gui.pages.artifacts_page.ProjectsDatabase'), \
             patch('src.gui.pages.tasks_page.ProjectsDatabase'), \
             patch('src.gui.pages.tasks_page.NotesDatabase'), \
             patch('src.gui.pages.tasks_page.ArtifactsDatabase'), \
             patch('src.gui.pages.tasks_page.AppointmentsDatabase'), \
             patch('src.gui.pages.notes_page.NotesDatabase'):
            
            artifacts_page = ArtifactsPage()
            projects_page = ProjectsPage()
            notes_page = NotesPage()
            
        # Set up tab structure
        tabbed.tabs = [
            {'id': 'artifacts', 'widget': artifacts_page},
            {'id': 'project', 'widget': projects_page},
            {'id': 'notes', 'widget': notes_page},
        ]
        
        # Create coordinator
        coordinator = SignalCoordinator(tabbed)
        tabbed.signal_coordinator = coordinator
        
        # Register pages
        coordinator.register_page('artifacts', artifacts_page)
        coordinator.register_page('projects', projects_page)
        coordinator.register_page('notes', notes_page)
        
        return tabbed
    
    def test_cross_page_navigation_workflow(self, mock_tabbed_content):
        """Test navigation from ProjectsPage to ArtifactsPage"""
        coordinator = mock_tabbed_content.signal_coordinator
        projects_page = mock_tabbed_content.tabs[1]['widget']
        artifacts_page = mock_tabbed_content.tabs[0]['widget']
        
        # Mock the navigation method
        artifacts_page.navigate_to_artifact = Mock()
        
        # Emit navigation request from projects page
        projects_page.request_navigate_to_artifact.emit("artifact123")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Verify tab switch
        mock_tabbed_content.tab_widget.setCurrentIndex.assert_called_with(0)
        
        # Verify navigation method called
        artifacts_page.navigate_to_artifact.assert_called_once_with("artifact123")
    
    def test_project_filter_synchronization_workflow(self, mock_tabbed_content):
        """Test project filter synchronization across pages"""
        coordinator = mock_tabbed_content.signal_coordinator
        artifacts_page = mock_tabbed_content.tabs[0]['widget']
        projects_page = mock_tabbed_content.tabs[1]['widget']
        
        # Mock filter application methods
        artifacts_page.apply_project_filter = Mock()
        projects_page.apply_project_filter = Mock()
        
        # Change filter from artifacts page
        artifacts_page.project_filter_requested.emit("project456")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Projects page should be updated, artifacts page should not
        artifacts_page.apply_project_filter.assert_not_called()
        projects_page.apply_project_filter.assert_called_once_with("project456")
        
        # Verify filter state
        assert coordinator.filter_state_manager.current_project_id == "project456"
    
    def test_artifact_project_link_workflow(self, mock_tabbed_content):
        """Test artifact-project linking workflow"""
        coordinator = mock_tabbed_content.signal_coordinator
        artifacts_page = mock_tabbed_content.tabs[0]['widget']
        
        # Connect spy to batch update signal
        batch_updates = []
        coordinator.artifacts_batch_updated.connect(
            lambda ids: batch_updates.extend(ids)
        )
        
        # Emit project change
        artifacts_page.artifact_project_changed.emit(
            "artifact789", "old_project", "new_project"
        )
        
        # Let batch timer fire
        QTimer.singleShot(150, lambda: None)  # Wait for batch delay
        QCoreApplication.processEvents()
        
        # Should have queued the artifact for batch update
        assert "artifact789" in batch_updates
    
    def test_error_recovery_workflow(self, mock_tabbed_content):
        """Test error handling and recovery in navigation"""
        coordinator = mock_tabbed_content.signal_coordinator
        projects_page = mock_tabbed_content.tabs[1]['widget']
        
        # Track errors
        errors = []
        coordinator.coordination_error.connect(
            lambda err_type, msg: errors.append((err_type, msg))
        )
        
        # Force an error by requesting navigation to non-existent page
        coordinator._route_navigation("non_existent", "item123")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Should have recorded an error
        assert len(errors) > 0
        assert errors[0][0] == "navigation"
        
        # Coordination should still be enabled
        assert coordinator._coordination_enabled
    
    def test_circular_update_prevention(self, mock_tabbed_content):
        """Test prevention of circular updates in filter synchronization"""
        coordinator = mock_tabbed_content.signal_coordinator
        artifacts_page = mock_tabbed_content.tabs[0]['widget']
        projects_page = mock_tabbed_content.tabs[1]['widget']
        
        # Track filter changes
        filter_changes = []
        
        def track_filter(project_id):
            filter_changes.append(project_id)
            # Simulate triggering another filter change
            if len(filter_changes) < 10:  # Prevent infinite loop in test
                artifacts_page.project_filter_requested.emit(project_id)
        
        artifacts_page.apply_project_filter = Mock(side_effect=track_filter)
        projects_page.apply_project_filter = Mock(side_effect=track_filter)
        
        # Trigger initial filter change
        artifacts_page.project_filter_requested.emit("project_circular")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Should not cause infinite loop
        assert len(filter_changes) < 10
    
    def test_multi_page_update_workflow(self, mock_tabbed_content):
        """Test updates affecting multiple pages"""
        coordinator = mock_tabbed_content.signal_coordinator
        projects_page = mock_tabbed_content.tabs[1]['widget']
        
        # Track batch updates
        artifact_updates = []
        project_updates = []
        
        coordinator.artifacts_batch_updated.connect(
            lambda ids: artifact_updates.extend(ids)
        )
        coordinator.projects_batch_updated.connect(
            lambda ids: project_updates.extend(ids)
        )
        
        # Unlink artifact from project
        projects_page.artifact_unlinked_from_project.emit(
            "artifact_unlink", "project_unlink"
        )
        
        # Process batch updates
        QTimer.singleShot(150, lambda: None)
        QCoreApplication.processEvents()
        
        # Both artifact and project should be updated
        assert "artifact_unlink" in artifact_updates
        assert "project_unlink" in project_updates
    
    def test_page_registration_deregistration(self, mock_tabbed_content):
        """Test dynamic page registration and deregistration"""
        coordinator = mock_tabbed_content.signal_coordinator
        
        # Create a new page
        with patch('src.gui.pages.notes_page.NotesDatabase'):
            new_page = NotesPage()
        
        # Register the page
        coordinator.register_page("new_notes", new_page)
        assert "new_notes" in coordinator.pages
        
        # Mock navigation method
        new_page.navigate_to_note = Mock()
        
        # Test navigation to new page
        coordinator._route_navigation("notes", "note123")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Unregister the page
        coordinator.unregister_page("new_notes")
        assert "new_notes" not in coordinator.pages
    
    def test_signal_debugger_integration(self, mock_tabbed_content):
        """Test signal debugger in real workflow"""
        from src.gui.components.signal_coordinator import SignalDebugger
        
        coordinator = mock_tabbed_content.signal_coordinator
        debugger = SignalDebugger(coordinator)
        
        # Enable debug mode
        debugger.enable_debug_mode()
        
        # Perform some operations
        artifacts_page = mock_tabbed_content.tabs[0]['widget']
        artifacts_page.project_filter_requested.emit("debug_project")
        
        # Process events
        QCoreApplication.processEvents()
        
        # Check debug log
        history = debugger.get_signal_history("project_filter_changed")
        assert len(history) > 0
        
        # Disable debug mode
        debugger.disable_debug_mode()
    
    def test_performance_batch_processing(self, mock_tabbed_content):
        """Test performance of batch processing multiple updates"""
        coordinator = mock_tabbed_content.signal_coordinator
        
        # Track batch emissions
        batch_count = 0
        
        def count_batch():
            nonlocal batch_count
            batch_count += 1
        
        coordinator.artifacts_batch_updated.connect(lambda _: count_batch())
        
        # Queue many updates rapidly
        for i in range(100):
            coordinator._queue_batch_update('artifacts', f'artifact_{i}')
        
        # Process events with delay for batch timer
        QTimer.singleShot(150, lambda: None)
        QCoreApplication.processEvents()
        
        # Should batch into single emission
        assert batch_count == 1
    
    def test_error_threshold_circuit_breaker(self, mock_tabbed_content):
        """Test circuit breaker activation after error threshold"""
        coordinator = mock_tabbed_content.signal_coordinator
        
        # Track circuit breaker
        disabled = False
        
        def on_disabled(reason):
            nonlocal disabled
            disabled = True
        
        coordinator.coordination_disabled.connect(on_disabled)
        
        # Generate many errors quickly
        for i in range(15):
            coordinator._record_error("test_error", f"Error {i}")
        
        # Should disable coordination
        assert disabled
        assert not coordinator._coordination_enabled
        
        # Reset and verify re-enabled
        coordinator.reset_error_count()
        assert coordinator._coordination_enabled


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @pytest.fixture(scope="class")
    def qapp(self):
        """Create QApplication for tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    
    def test_project_context_switch_scenario(self, qapp):
        """Test switching project context across application"""
        # This would test:
        # 1. User selects project in ProjectsPage
        # 2. ArtifactsPage filters to show only that project's artifacts
        # 3. NotesPage filters to show only that project's notes
        # 4. User navigates to artifact from project
        # 5. Artifact view shows correct project association
        pass  # Placeholder for full implementation
    
    def test_artifact_lifecycle_scenario(self, qapp):
        """Test complete artifact lifecycle with project associations"""
        # This would test:
        # 1. Create artifact without project
        # 2. Link artifact to project
        # 3. Navigate to project from artifact
        # 4. Unlink artifact from project
        # 5. Verify all pages update correctly
        pass  # Placeholder for full implementation
    
    def test_concurrent_operations_scenario(self, qapp):
        """Test handling concurrent operations from multiple pages"""
        # This would test:
        # 1. Multiple pages updating simultaneously
        # 2. Batch processing efficiency
        # 3. No race conditions or lost updates
        # 4. Consistent state across all pages
        pass  # Placeholder for full implementation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])