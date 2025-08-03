# Signal Coordination System - Implementation Guide

## Overview
This guide provides detailed implementation instructions for the signal-based coordination system between Artifacts and Projects pages in DinoAir 2.0.

## Implementation Order and Dependencies

### Phase 1: Core Infrastructure (Tasks 1-5)
These tasks establish the foundation and must be completed first.

#### Task 1: Create SignalCoordinator class
**File**: `src/gui/components/signal_coordinator.py`

```python
from PySide6.QtCore import QObject, Signal
from typing import Dict, Optional, Any
from ..utils.logger import Logger

class SignalCoordinator(QObject):
    """Central coordinator for cross-page signals and state synchronization"""
    
    # Cross-page navigation signals
    navigate_to_artifact = Signal(str)  # artifact_id
    navigate_to_project = Signal(str)   # project_id
    navigate_to_note = Signal(str)      # note_id
    navigate_to_event = Signal(str)     # event_id
    
    # Project filter synchronization
    project_filter_changed = Signal(str)  # project_id or None
    
    # Real-time update signals
    artifact_linked_to_project = Signal(str, str)    # artifact_id, project_id
    artifact_unlinked_from_project = Signal(str, str) # artifact_id, project_id
    project_updated = Signal(str)                     # project_id
    artifact_updated = Signal(str)                    # artifact_id
    
    # Batch update signals
    artifacts_batch_updated = Signal(list)  # List of artifact_ids
    projects_batch_updated = Signal(list)   # List of project_ids
    
    def __init__(self, tabbed_content):
        super().__init__()
        self.logger = Logger()
        self.tabbed_content = tabbed_content
        self.pages = {}  # Dict[str, QWidget]
        self.filter_state_manager = None
        self._blocked_signals = set()  # Prevent circular updates
```

#### Task 2: Create FilterStateManager class
**Add to**: `src/gui/components/signal_coordinator.py`

```python
class FilterStateManager:
    """Manages synchronized filter state across pages"""
    
    def __init__(self):
        self.current_project_id = None
        self.subscribers = []  # List of pages/widgets
        self.logger = Logger()
    
    def set_project_filter(self, project_id: Optional[str], source: str = None):
        """Update project filter and notify subscribers"""
        if self.current_project_id != project_id:
            old_id = self.current_project_id
            self.current_project_id = project_id
            self.logger.info(f"Project filter changed: {old_id} -> {project_id} (source: {source})")
            self._notify_subscribers(project_id, source)
    
    def subscribe(self, widget: QWidget, widget_id: str):
        """Subscribe a widget to filter state changes"""
        self.subscribers.append((widget, widget_id))
        # Apply current filter immediately
        if hasattr(widget, 'apply_project_filter'):
            widget.apply_project_filter(self.current_project_id)
```

#### Task 3-5: Integration with TabbedContentWidget
**File**: `src/gui/components/tabbed_content.py`

Add these imports and initialization:
```python
from .signal_coordinator import SignalCoordinator

# In __init__ method, after creating tab_widget:
self.signal_coordinator = SignalCoordinator(self)
self.signal_coordinator.filter_state_manager = FilterStateManager()

# Add page registration method:
def register_page_with_coordinator(self, page_id: str, page_widget: QWidget):
    """Register a page with the signal coordinator"""
    self.signal_coordinator.register_page(page_id, page_widget)
    
    # Subscribe to filter state if applicable
    if hasattr(page_widget, 'apply_project_filter'):
        self.signal_coordinator.filter_state_manager.subscribe(page_widget, page_id)
```

### Phase 2: Cross-Page Navigation (Tasks 6-9)

#### Task 6: Update ArtifactsPage
**File**: `src/gui/pages/artifacts_page.py`

Add new signals:
```python
# Add to class definition
request_navigate_to_project = Signal(str)  # project_id
project_filter_requested = Signal(str)     # project_id
artifact_project_changed = Signal(str, str, str)  # artifact_id, old_project_id, new_project_id

# Add navigation methods
def navigate_to_artifact(self, artifact_id: str):
    """Navigate to and select a specific artifact"""
    # Find artifact in tree
    # Select it
    # Show details
    
def handle_view_project_request(self):
    """Handle request to view artifact's project"""
    if self._current_artifact and self._current_artifact.project_id:
        self.request_navigate_to_project.emit(self._current_artifact.project_id)
```

#### Task 7: Update ProjectsPage
**File**: `src/gui/pages/tasks_page.py`

Add new signals and methods:
```python
# Add to class definition
request_navigate_to_artifact = Signal(str)  # artifact_id
request_navigate_to_note = Signal(str)      # note_id
request_navigate_to_event = Signal(str)     # event_id

# Update existing view methods to emit signals
def _view_artifact(self):
    """View the selected artifact"""
    current_item = self.artifacts_list.currentItem()
    if current_item and current_item.data(Qt.ItemDataRole.UserRole):
        artifact_id = current_item.data(Qt.ItemDataRole.UserRole)
        self.request_navigate_to_artifact.emit(artifact_id)

def navigate_to_project(self, project_id: str):
    """Navigate to and select a specific project"""
    self._select_project_in_tree(project_id)
```

### Phase 3: Filter Synchronization (Tasks 10-14)

#### Task 10: Update ProjectComboBox
**File**: `src/gui/components/project_combo_box.py`

Add synchronization support:
```python
def set_project_id_silent(self, project_id: Optional[str]):
    """Set project without emitting signals (for sync)"""
    self.blockSignals(True)
    self.set_project_id(project_id)
    self.blockSignals(False)

def is_syncing(self) -> bool:
    """Check if currently syncing to prevent circular updates"""
    return self.signalsBlocked()
```

#### Task 13-14: Add apply_project_filter methods
Both pages need this method:
```python
def apply_project_filter(self, project_id: Optional[str]):
    """Apply project filter from external source"""
    # Update combo box without triggering signals
    if hasattr(self, 'project_combo'):
        self.project_combo.set_project_id_silent(project_id)
    
    # Update view
    self._current_project_filter = project_id
    self._load_artifacts()  # or _load_projects() for ProjectsPage
```

### Phase 4: Real-Time Updates (Tasks 15-17)

#### Task 15-17: Implement real-time update handling
Add to SignalCoordinator:
```python
def handle_artifact_linked(self, artifact_id: str, project_id: str):
    """Handle artifact being linked to a project"""
    # Emit to all pages
    self.artifact_linked_to_project.emit(artifact_id, project_id)
    
    # Update affected pages
    if 'artifacts' in self.pages:
        self.pages['artifacts'].refresh_artifact_item(artifact_id)
    if 'projects' in self.pages:
        self.pages['projects'].refresh_project_statistics(project_id)
```

### Phase 5: Visual Enhancements (Tasks 18-19)

#### Task 18-19: Project Badge Implementation
**File**: Create `src/gui/components/project_badge_delegate.py`

```python
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont

class ProjectBadgeDelegate(QStyledItemDelegate):
    """Custom delegate for showing project badges in artifact tree"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects_cache = {}  # Cache project info for badges
    
    def paint(self, painter: QPainter, option, index):
        # Draw standard item first
        super().paint(painter, option, index)
        
        # Get artifact data
        artifact = index.data(Qt.ItemDataRole.UserRole)
        if not artifact or not hasattr(artifact, 'project_id'):
            return
            
        # Draw project badge
        if artifact.project_id and artifact.project_id in self.projects_cache:
            project = self.projects_cache[artifact.project_id]
            self._draw_project_badge(painter, option.rect, project)
    
    def _draw_project_badge(self, painter: QPainter, item_rect: QRect, project):
        """Draw the project badge"""
        # Calculate badge position (right side)
        badge_width = 100
        badge_height = 20
        badge_x = item_rect.right() - badge_width - 10
        badge_y = item_rect.center().y() - badge_height // 2
        
        badge_rect = QRect(badge_x, badge_y, badge_width, badge_height)
        
        # Draw background
        color = QColor(project.color) if project.color else QColor("#FF6B35")
        painter.fillRect(badge_rect, color)
        
        # Draw text
        painter.setPen(Qt.white)
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        text = f"{project.icon} {project.name[:10]}"
        painter.drawText(badge_rect, Qt.AlignCenter, text)
```

### Phase 6: Error Handling and Debugging (Tasks 20-22)

#### Task 21: SignalDebugger
Add to `src/gui/components/signal_coordinator.py`:

```python
class SignalDebugger:
    """Debug and monitor signal flow"""
    
    def __init__(self, coordinator: SignalCoordinator):
        self.coordinator = coordinator
        self.signal_log = []
        self.debug_mode = False
        self._connect_debug_slots()
    
    def _connect_debug_slots(self):
        """Connect to all signals for debugging"""
        signals = [
            ('navigate_to_artifact', self.coordinator.navigate_to_artifact),
            ('navigate_to_project', self.coordinator.navigate_to_project),
            ('project_filter_changed', self.coordinator.project_filter_changed),
            # ... add all signals
        ]
        
        for signal_name, signal in signals:
            signal.connect(lambda *args, name=signal_name: self.log_signal(name, args))
```

## Key Implementation Details

### 1. Preventing Circular Updates
- Use `blockSignals()` when updating UI programmatically
- Track signal sources to prevent loops
- Implement `_blocked_signals` set in SignalCoordinator

### 2. Thread Safety
- All signals are automatically thread-safe in Qt
- Use `QTimer.singleShot()` for delayed updates
- Batch updates to prevent UI freezing

### 3. Performance Optimization
- Cache project information for badges
- Batch refresh operations
- Use lazy loading for tree updates

### 4. Error Recovery
- Wrap all signal handlers in try/except
- Log errors but don't crash
- Provide user feedback for failures

## Testing Approach

### Unit Tests
- Test SignalCoordinator in isolation
- Mock page widgets
- Verify signal emission and handling

### Integration Tests
- Test complete workflows
- Verify cross-page navigation
- Test filter synchronization

### Example Test:
```python
def test_cross_page_navigation():
    # Create coordinator
    coordinator = SignalCoordinator(mock_tabbed_content)
    
    # Register pages
    artifacts_page = Mock(spec=ArtifactsPage)
    projects_page = Mock(spec=ProjectsPage)
    
    coordinator.register_page('artifacts', artifacts_page)
    coordinator.register_page('projects', projects_page)
    
    # Test navigation
    coordinator.navigate_to_project.emit('project-123')
    
    # Verify
    projects_page.navigate_to_project.assert_called_with('project-123')
```

## Configuration

Add to `config/app_config.json`:
```json
{
    "signal_coordination": {
        "enable_debug_mode": false,
        "signal_timeout_ms": 5000,
        "batch_update_delay_ms": 100,
        "max_signal_retries": 3
    }
}
```

## Common Pitfalls to Avoid

1. **Don't connect signals in loops** - This creates multiple connections
2. **Always disconnect signals when widgets are destroyed**
3. **Use `Qt.QueuedConnection` for cross-thread signals**
4. **Test with multiple rapid updates to ensure performance**
5. **Handle the case where pages might not be initialized yet**

## Success Criteria

- [ ] Project filter changes in one page update all pages
- [ ] Clicking "View" on artifact opens it in artifacts page
- [ ] Unlinking artifact in projects page updates artifacts page instantly
- [ ] No circular update loops
- [ ] Performance remains smooth with 1000+ artifacts
- [ ] Error recovery works without crashing