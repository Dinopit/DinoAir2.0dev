# Signal Coordination System Documentation

## Overview

The Signal Coordination System in DinoAir 2.0 provides a centralized mechanism for managing cross-page communication and state synchronization. It enables seamless navigation between different sections of the application while maintaining consistent state across all pages.

## Architecture

### Core Components

#### 1. SignalCoordinator
The central hub that manages all cross-page signals and coordinates communication between different parts of the application.

```python
from src.gui.components.signal_coordinator import SignalCoordinator

# Created automatically by TabbedContentWidget
coordinator = SignalCoordinator(tabbed_content)
```

#### 2. FilterStateManager
Manages synchronized filter state (e.g., project filters) across multiple pages.

```python
# Access through coordinator
filter_manager = coordinator.filter_state_manager
current_project = filter_manager.get_current_filter()
```

#### 3. SignalDebugger
Provides debugging capabilities for monitoring signal flow in development.

```python
from src.gui.components.signal_coordinator import SignalDebugger

debugger = SignalDebugger(coordinator)
debugger.enable_debug_mode()  # Enables console output
```

## Usage Examples

### 1. Basic Cross-Page Navigation

Navigate from one page to another with context:

```python
# In ArtifactsPage, navigate to a specific project
class ArtifactsPage(QWidget):
    request_navigate_to_project = Signal(str)  # project_id
    
    def view_project(self, project_id):
        # Emit navigation request
        self.request_navigate_to_project.emit(project_id)
```

The SignalCoordinator automatically:
- Switches to the Projects tab
- Calls `navigate_to_project(project_id)` on ProjectsPage
- Handles any errors gracefully

### 2. Project Filter Synchronization

Synchronize project filters across all pages:

```python
# In any page with project filtering
class MyPage(QWidget):
    project_filter_requested = Signal(str)
    
    def __init__(self):
        super().__init__()
        # Add project combo box
        self.project_combo = ProjectComboBox(self)
        self.project_combo.project_changed.connect(self._on_project_changed)
    
    def _on_project_changed(self, project_id):
        # This will sync across all pages
        self.project_filter_requested.emit(project_id)
    
    def apply_project_filter(self, project_id):
        """Called by coordinator when filter changes"""
        # Update your page's display
        self._filter_by_project(project_id)
```

### 3. Real-Time Updates

Notify other pages when data changes:

```python
# When linking an artifact to a project
class ArtifactsPage(QWidget):
    artifact_project_changed = Signal(str, str, str)  # artifact_id, old_proj, new_proj
    
    def link_to_project(self, artifact_id, project_id):
        old_project = self.get_artifact_project(artifact_id)
        
        # Update database
        self.artifacts_db.update_artifact_project(artifact_id, project_id)
        
        # Notify other pages
        self.artifact_project_changed.emit(
            artifact_id, 
            old_project or "", 
            project_id or ""
        )
```

### 4. Batch Updates for Performance

Queue multiple updates for efficient processing:

```python
# SignalCoordinator automatically batches updates
for artifact_id in large_artifact_list:
    self.artifact_updated.emit(artifact_id)
    # These will be batched and processed together
```

### 5. Error Handling

The system includes automatic retry and circuit breaker patterns:

```python
# Monitor errors
coordinator.coordination_error.connect(self.on_coordination_error)
coordinator.coordination_disabled.connect(self.on_coordination_disabled)

def on_coordination_error(self, error_type, message):
    self.logger.warning(f"Coordination error: {error_type} - {message}")

def on_coordination_disabled(self, reason):
    # Show user notification
    QMessageBox.warning(self, "System Notice", 
                        "Cross-page updates temporarily disabled due to errors")
    
    # Can manually reset when issues are resolved
    coordinator.reset_error_count()
```

## Page Integration Guide

### Step 1: Define Signals

Add appropriate signals to your page class:

```python
class MyCustomPage(QWidget):
    # Navigation requests
    request_navigate_to_artifact = Signal(str)
    request_navigate_to_project = Signal(str)
    request_navigate_to_note = Signal(str)
    request_navigate_to_event = Signal(str)
    
    # Filter synchronization
    project_filter_requested = Signal(str)
    
    # Data updates
    my_data_updated = Signal(str)  # item_id
```

### Step 2: Implement Navigation Methods

Add methods that the coordinator will call:

```python
def navigate_to_my_item(self, item_id):
    """Called by coordinator when navigating to this page"""
    # Find and select the item
    self._select_item_in_view(item_id)
    # Scroll to make it visible
    self._scroll_to_item(item_id)
    # Load details
    self._load_item_details(item_id)
```

### Step 3: Implement Filter Methods

Add filter synchronization support:

```python
def apply_project_filter(self, project_id):
    """Called by coordinator when project filter changes"""
    if hasattr(self, 'project_combo'):
        # Update combo without triggering signals
        self.project_combo.set_project_id_silent(project_id)
    
    # Filter your data
    self._filter_items_by_project(project_id)
```

### Step 4: Connect Update Signals

Emit signals when data changes:

```python
def update_item(self, item_id, changes):
    # Update in database
    self.db.update_item(item_id, changes)
    
    # Notify other pages
    self.my_data_updated.emit(item_id)
    
    # If project changed
    if 'project_id' in changes:
        self.item_project_changed.emit(
            item_id,
            old_project_id,
            changes['project_id']
        )
```

## Best Practices

### 1. Signal Naming Convention

Use consistent signal names:
- Navigation: `request_navigate_to_<target>`
- Filters: `<filter_type>_filter_requested`
- Updates: `<item_type>_<action>` (e.g., `artifact_linked_to_project`)

### 2. Avoid Circular Updates

The system prevents circular updates automatically, but design your code to minimize them:

```python
def apply_project_filter(self, project_id):
    # Check if already filtered
    if self.current_filter == project_id:
        return
    
    self.current_filter = project_id
    self._update_display()
```

### 3. Use Batch Updates

For multiple updates, let the coordinator batch them:

```python
# Good - coordinator will batch
for item in items:
    self.item_updated.emit(item.id)

# Less efficient - immediate updates
for item in items:
    self.force_immediate_update(item.id)
```

### 4. Handle Errors Gracefully

Always provide fallbacks for navigation:

```python
def navigate_to_artifact(self, artifact_id):
    try:
        artifact = self.get_artifact(artifact_id)
        if artifact:
            self._select_artifact(artifact)
        else:
            self.logger.warning(f"Artifact {artifact_id} not found")
            # Optionally show user message
    except Exception as e:
        self.logger.error(f"Navigation failed: {e}")
        # Don't crash - coordinator will handle
```

## Debugging

### Enable Debug Mode

```python
# In development
debugger = SignalDebugger(coordinator)
debugger.enable_debug_mode()

# View signal history
history = debugger.get_signal_history('project_filter_changed')
for entry in history:
    print(f"{entry['timestamp']}: {entry['args']}")

# Print summary
debugger.print_summary()
```

### Monitor Errors

```python
# Check error status
status = coordinator.get_error_status()
print(f"Errors: {status['error_count']}/{status['max_errors']}")
print(f"Enabled: {status['enabled']}")

# Reset if needed
if not status['enabled']:
    coordinator.reset_error_count()
```

### Common Issues

1. **Page not receiving updates**
   - Ensure page is registered with coordinator
   - Check signal names match exactly
   - Verify `apply_project_filter` method exists

2. **Navigation not working**
   - Check tab ID mapping in coordinator
   - Ensure navigation method exists on target page
   - Look for errors in coordination_error signal

3. **Filter updates causing loops**
   - Use `set_project_id_silent` on combo boxes
   - Check for `_updating` flags in filter manager
   - Verify source page filtering in notifications

## Advanced Features

### Custom Signal Routing

Add custom signal routing for specialized workflows:

```python
# In your page
special_signal = Signal(str, dict)

# Connect with custom handler
coordinator._connect_page_signals(page_id, page_widget)
# Then add custom connection
page_widget.special_signal.connect(
    lambda data, params: coordinator._safe_handler(
        lambda: self.handle_special(data, params),
        'special'
    )
)
```

### Performance Optimization

Configure batch processing:

```python
# Adjust batch timer delay (default 100ms)
coordinator._batch_timer.setInterval(200)  # 200ms for larger batches

# Monitor batch sizes
coordinator.artifacts_batch_updated.connect(
    lambda ids: print(f"Batch size: {len(ids)}")
)
```

### Integration Testing

Test signal coordination in your workflows:

```python
def test_my_workflow():
    # Create pages
    page1 = MyPage1()
    page2 = MyPage2()
    
    # Register with coordinator
    coordinator.register_page('page1', page1)
    coordinator.register_page('page2', page2)
    
    # Test signal flow
    page1.request_navigate_to_item.emit('item123')
    
    # Verify navigation
    assert page2.current_item == 'item123'
```

## Conclusion

The Signal Coordination System provides a robust foundation for building interconnected, responsive user interfaces. By following these patterns and best practices, you can create seamless user experiences with proper state management and error handling.

For more examples, see the test files:
- `tests/test_signal_coordinator.py` - Unit tests
- `tests/test_signal_coordination_integration.py` - Integration tests