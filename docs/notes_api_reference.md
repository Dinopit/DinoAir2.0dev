# Notes Feature API Reference

This document provides detailed API documentation for all classes and methods in the Notes feature of DinoAir 2.0.

## Table of Contents

1. [Database Layer](#database-layer)
   - [NotesDatabase](#notesdatabase)
2. [GUI Components](#gui-components)
   - [NotesPage](#notespage)
   - [NoteEditor](#noteeditor)
   - [NoteListWidget](#notelistwidget)
   - [NotesSearchWidget](#notessearchwidget)
   - [TagManager](#tagmanager)
   - [NotesExporter](#notesexporter)
3. [Security Components](#security-components)
   - [NotesSecurity](#notessecurity)
   - [HTMLSanitizer](#htmlsanitizer)
   - [RateLimiter](#ratelimiter)
4. [Models](#models)
   - [Note](#note)

---

## Database Layer

### NotesDatabase

**Location**: `src/database/notes_db.py`

**Description**: Handles all database operations for notes, including CRUD operations, search, and tag management.

#### Constructor

```python
def __init__(self, user_name: Optional[str] = None):
    """
    Initialize the Notes database manager.
    
    Args:
        user_name: Optional username for multi-user support
    """
```

#### Methods

##### create_note

```python
def create_note(
    self, 
    note: Note, 
    content_html: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new note in the database.
    
    Args:
        note: Note object containing title, content, and tags
        content_html: Optional HTML content for rich text
        
    Returns:
        Dict with keys:
        - success (bool): Whether operation succeeded
        - note_id (str): ID of created note (if successful)
        - error (str): Error message (if failed)
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### get_note

```python
def get_note(self, note_id: str) -> Optional[Note]:
    """
    Retrieve a single note by ID.
    
    Args:
        note_id: Unique identifier of the note
        
    Returns:
        Note object if found, None otherwise
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### get_all_notes

```python
def get_all_notes(self) -> List[Note]:
    """
    Retrieve all active (non-deleted) notes.
    
    Returns:
        List of Note objects, sorted by updated_at descending
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### update_note

```python
def update_note(
    self, 
    note_id: str, 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing note.
    
    Args:
        note_id: Unique identifier of the note
        updates: Dictionary of fields to update:
            - title (str): New title
            - content (str): New content
            - content_html (str): New HTML content
            - tags (List[str]): New tags list
            
    Returns:
        Dict with keys:
        - success (bool): Whether operation succeeded
        - error (str): Error message (if failed)
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### delete_note

```python
def delete_note(
    self, 
    note_id: str, 
    hard_delete: bool = False
) -> Dict[str, Any]:
    """
    Delete a note (soft delete by default).
    
    Args:
        note_id: Unique identifier of the note
        hard_delete: If True, permanently delete; if False, soft delete
        
    Returns:
        Dict with keys:
        - success (bool): Whether operation succeeded
        - error (str): Error message (if failed)
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### search_notes

```python
def search_notes(
    self, 
    query: str, 
    filter_option: str = "All"
) -> List[Note]:
    """
    Search notes based on query and filter.
    
    Args:
        query: Search query (already sanitized)
        filter_option: One of "All", "Title Only", "Content Only", "Tags Only"
        
    Returns:
        List of Note objects matching the search criteria
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### get_notes_by_tag

```python
def get_notes_by_tag(self, tag: str) -> List[Note]:
    """
    Get all notes containing a specific tag.
    
    Args:
        tag: Tag name to search for
        
    Returns:
        List of Note objects containing the tag
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### get_all_tags

```python
def get_all_tags(self) -> Dict[str, int]:
    """
    Get all unique tags with their usage counts.
    
    Returns:
        Dictionary mapping tag names to usage counts
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### rename_tag

```python
def rename_tag(self, old_tag: str, new_tag: str) -> Dict[str, Any]:
    """
    Rename a tag across all notes.
    
    Args:
        old_tag: Current tag name
        new_tag: New tag name
        
    Returns:
        Dict with keys:
        - success (bool): Whether operation succeeded
        - affected_notes (int): Number of notes updated
        - error (str): Error message (if failed)
        
    Raises:
        DatabaseError: If database operation fails
    """
```

##### delete_tag

```python
def delete_tag(self, tag_to_delete: str) -> Dict[str, Any]:
    """
    Remove a tag from all notes.
    
    Args:
        tag_to_delete: Tag name to remove
        
    Returns:
        Dict with keys:
        - success (bool): Whether operation succeeded
        - affected_notes (int): Number of notes updated
        - error (str): Error message (if failed)
        
    Raises:
        DatabaseError: If database operation fails
    """
```

---

## GUI Components

### NotesPage

**Location**: `src/gui/pages/notes_page.py`

**Description**: Main notes interface widget with full functionality.

#### Signals

```python
# No public signals - internal communication only
```

#### Constructor

```python
def __init__(self):
    """Initialize the notes page with all components."""
```

#### Public Methods

```python
def closeEvent(self, event):
    """
    Handle close event to check for unsaved changes.
    
    Args:
        event: QCloseEvent to accept or ignore
    """
```

### NoteEditor

**Location**: `src/gui/components/note_editor.py`

**Description**: Rich text editor widget for note content.

#### Signals

```python
note_changed = Signal()  # Emitted when content changes
note_saved = Signal(str, str, str)  # Emitted with (title, content, tags)
auto_save_requested = Signal()  # Emitted when auto-save timer triggers
```

#### Constructor

```python
def __init__(self):
    """Initialize the note editor with rich text support."""
```

#### Public Methods

##### load_note

```python
def load_note(
    self, 
    note_id: str, 
    title: str, 
    content: str, 
    tags: list,
    content_html: Optional[str] = None
):
    """
    Load a note into the editor.
    
    Args:
        note_id: Note's unique identifier
        title: Note title
        content: Plain text content
        tags: List of tag strings
        content_html: Optional HTML content for rich text
    """
```

##### get_note_data

```python
def get_note_data(self) -> tuple:
    """
    Get current note data with sanitization.
    
    Returns:
        Tuple of (note_id, title, content, tags, content_html)
        All values are sanitized for security
    """
```

##### clear_editor

```python
def clear_editor(self):
    """Clear all editor fields."""
```

##### set_focus

```python
def set_focus(self):
    """Set focus to the title input field."""
```

##### has_content

```python
def has_content(self) -> bool:
    """
    Check if editor has any content.
    
    Returns:
        True if title or content is non-empty
    """
```

##### set_auto_save_enabled

```python
def set_auto_save_enabled(self, enabled: bool):
    """
    Enable or disable auto-save.
    
    Args:
        enabled: Whether auto-save should be enabled
    """
```

##### set_auto_save_interval

```python
def set_auto_save_interval(self, seconds: int):
    """
    Set auto-save interval.
    
    Args:
        seconds: Auto-save interval in seconds (1-10)
    """
```

##### set_available_tags

```python
def set_available_tags(self, tags: List[str]):
    """
    Set available tags for autocomplete.
    
    Args:
        tags: List of available tag names
    """
```

##### set_save_status_saved

```python
def set_save_status_saved(self):
    """Set save status to saved with timestamp."""
```

##### set_save_status_error

```python
def set_save_status_error(self, error_msg: str = "Save failed"):
    """
    Set save status to error.
    
    Args:
        error_msg: Error message to display
    """
```

### NoteListWidget

**Location**: `src/gui/components/note_list_widget.py`

**Description**: Custom list widget for displaying notes.

#### Signals

```python
note_selected = Signal(Note)  # Emitted when a note is selected
```

#### Constructor

```python
def __init__(self):
    """Initialize the note list widget."""
```

#### Public Methods

##### load_notes

```python
def load_notes(self, notes: List[Note]):
    """
    Load notes into the list widget.
    
    Args:
        notes: List of Note objects to display
    """
```

##### refresh_notes

```python
def refresh_notes(self, notes: List[Note]):
    """
    Refresh the notes list while maintaining selection.
    
    Args:
        notes: Updated list of Note objects
    """
```

##### get_selected_note

```python
def get_selected_note(self) -> Optional[Note]:
    """
    Get the currently selected note.
    
    Returns:
        The selected Note object or None
    """
```

##### select_first_note

```python
def select_first_note(self):
    """Select the first note in the list."""
```

##### clear_selection

```python
def clear_selection(self):
    """Clear the current selection."""
```

##### get_note_count

```python
def get_note_count(self) -> int:
    """
    Get the total number of notes in the list.
    
    Returns:
        Number of notes (filtered or total based on mode)
    """
```

##### filter_notes

```python
def filter_notes(self, search_results: List[Note], search_query: str):
    """
    Filter displayed notes based on search results.
    
    Args:
        search_results: List of notes matching the search
        search_query: The search query used (for highlighting)
    """
```

##### clear_filter

```python
def clear_filter(self):
    """Clear search filter and show all notes."""
```

### NotesSearchWidget

**Location**: `src/gui/components/notes_search.py`

**Description**: Search widget with debouncing and filter options.

#### Signals

```python
search_requested = Signal(str, str)  # Emitted with (query, filter_option)
clear_requested = Signal()  # Emitted when search is cleared
```

#### Constructor

```python
def __init__(self):
    """Initialize the search widget with debouncing."""
```

#### Public Methods

##### focus_search

```python
def focus_search(self):
    """Set focus to the search input and select all text."""
```

##### get_search_query

```python
def get_search_query(self) -> str:
    """
    Get the current search query.
    
    Returns:
        Current search query text
    """
```

##### get_filter_option

```python
def get_filter_option(self) -> str:
    """
    Get the current filter option.
    
    Returns:
        One of: "All", "Title Only", "Content Only", "Tags Only"
    """
```

##### set_search_query

```python
def set_search_query(self, query: str):
    """
    Set the search query programmatically.
    
    Args:
        query: Search query (will be sanitized)
    """
```

##### is_searching

```python
def is_searching(self) -> bool:
    """
    Check if currently in search mode.
    
    Returns:
        True if search query is non-empty
    """
```

### TagManager

**Location**: `src/gui/components/tag_manager.py`

**Description**: Tag cloud visualization and management widget.

#### Signals

```python
tag_clicked = Signal(str)  # Emitted when a tag is clicked
tags_updated = Signal()    # Emitted when tags are modified
```

#### Constructor

```python
def __init__(self, parent=None):
    """Initialize the tag manager with tag cloud display."""
```

#### Public Methods

##### refresh_tags

```python
def refresh_tags(self):
    """Refresh the tag list from database."""
```

##### get_selected_tags

```python
def get_selected_tags(self) -> list:
    """
    Get list of currently selected tags.
    
    Returns:
        List of selected tag names
    """
```

##### clear_selection

```python
def clear_selection(self):
    """Clear all tag selections."""
```

### NotesExporter

**Location**: `src/gui/components/notes_exporter.py`

**Description**: Handles exporting notes in various formats.

#### Signals

```python
export_started = Signal()
export_progress = Signal(int, int)  # current, total
export_completed = Signal(str)  # export path
export_failed = Signal(str)  # error message
```

#### Constructor

```python
def __init__(self, parent=None):
    """Initialize the notes exporter."""
```

#### Public Methods

##### export_note_as_html

```python
def export_note_as_html(
    self, 
    note: Note, 
    parent_widget=None
) -> Optional[str]:
    """
    Export a single note as HTML file.
    
    Args:
        note: The note to export
        parent_widget: Parent widget for file dialog
        
    Returns:
        Path to exported file or None if cancelled/failed
    """
```

##### export_note_as_txt

```python
def export_note_as_txt(
    self, 
    note: Note, 
    parent_widget=None
) -> Optional[str]:
    """
    Export a single note as plain text file.
    
    Args:
        note: The note to export
        parent_widget: Parent widget for file dialog
        
    Returns:
        Path to exported file or None if cancelled/failed
    """
```

##### export_note_as_pdf

```python
def export_note_as_pdf(
    self, 
    note: Note, 
    parent_widget=None
) -> Optional[str]:
    """
    Export a single note as PDF file.
    
    Args:
        note: The note to export
        parent_widget: Parent widget for file dialog
        
    Returns:
        Path to exported file or None if cancelled/failed
    """
```

##### export_all_notes

```python
def export_all_notes(
    self, 
    notes: List[Note], 
    parent_widget=None
) -> Optional[str]:
    """
    Export all notes as a ZIP archive.
    
    Args:
        notes: List of notes to export
        parent_widget: Parent widget for file dialog
        
    Returns:
        Path to exported ZIP file or None if cancelled/failed
    """
```

---

## Security Components

### NotesSecurity

**Location**: `src/gui/components/notes_security.py`

**Description**: Centralized security utilities for the Notes feature.

#### Constructor

```python
def __init__(self):
    """Initialize Notes security utilities with sanitizer and rate limiter."""
```

#### Public Methods

##### sanitize_note_title

```python
def sanitize_note_title(self, title: str) -> str:
    """
    Sanitize note title.
    
    Args:
        title: Raw title input
        
    Returns:
        Sanitized title (max 255 chars, HTML entities escaped)
    """
```

##### sanitize_note_content

```python
def sanitize_note_content(self, content: str) -> str:
    """
    Sanitize note content.
    
    Args:
        content: Raw content input
        
    Returns:
        Sanitized content (max 10KB, special chars filtered)
    """
```

##### sanitize_tag

```python
def sanitize_tag(self, tag: str) -> Optional[str]:
    """
    Sanitize a single tag.
    
    Args:
        tag: Raw tag input
        
    Returns:
        Sanitized tag or None if invalid
    """
```

##### sanitize_tags

```python
def sanitize_tags(self, tags: List[str]) -> List[str]:
    """
    Sanitize a list of tags.
    
    Args:
        tags: List of raw tag inputs
        
    Returns:
        List of sanitized tags (max 20 tags)
    """
```

##### sanitize_search_query

```python
def sanitize_search_query(self, query: str) -> str:
    """
    Sanitize search query for SQL safety.
    
    Args:
        query: Raw search query
        
    Returns:
        Sanitized search query with escaped wildcards
    """
```

##### sanitize_note_data

```python
def sanitize_note_data(
    self, 
    title: str, 
    content: str, 
    tags: List[str],
    content_html: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sanitize all note data.
    
    Args:
        title: Raw title
        content: Raw content
        tags: Raw tags list
        content_html: Raw HTML content
        
    Returns:
        Dictionary with keys:
        - title: Sanitized title
        - content: Sanitized content
        - tags: Sanitized tags list
        - content_html: Sanitized HTML (if provided)
        - valid: Whether data passed validation
        - errors: List of validation errors
        - modified: Whether any data was modified
    """
```

##### validate_note_data

```python
def validate_note_data(
    self, 
    title: str, 
    content: str, 
    tags: List[str]
) -> Dict[str, Any]:
    """
    Validate note data before saving.
    
    Args:
        title: Note title
        content: Note content
        tags: Note tags
        
    Returns:
        Dictionary with keys:
        - valid: Whether all data is valid
        - errors: List of validation error messages
    """
```

##### get_security_summary

```python
def get_security_summary(self) -> Dict[str, Any]:
    """
    Get security monitoring summary.
    
    Returns:
        Dictionary with security statistics
    """
```

##### reset_rate_limiter

```python
def reset_rate_limiter(self):
    """Reset the rate limiter (useful for testing)."""
```

### HTMLSanitizer

**Location**: `src/gui/components/notes_security.py`

**Description**: Custom HTML parser for sanitizing rich text content.

#### Constructor

```python
def __init__(self):
    """Initialize HTML sanitizer with whitelist rules."""
```

#### Public Methods

##### get_sanitized_html

```python
def get_sanitized_html(self) -> str:
    """
    Get the sanitized HTML string.
    
    Returns:
        Sanitized HTML with only safe tags and attributes
    """
```

##### get_stripped_tags

```python
def get_stripped_tags(self) -> List[str]:
    """
    Get list of tags that were stripped.
    
    Returns:
        List of stripped tag names
    """
```

##### reset

```python
def reset(self):
    """Reset the sanitizer for reuse."""
```

### RateLimiter

**Location**: `src/gui/components/notes_security.py`

**Description**: Simple rate limiter for auto-save operations.

#### Constructor

```python
def __init__(self, max_calls: int, window_seconds: int):
    """
    Initialize rate limiter.
    
    Args:
        max_calls: Maximum number of calls allowed in the window
        window_seconds: Time window in seconds
    """
```

#### Public Methods

##### is_allowed

```python
def is_allowed(self) -> bool:
    """
    Check if a call is allowed under the rate limit.
    
    Returns:
        True if call is allowed, False if rate limit exceeded
    """
```

##### reset

```python
def reset(self):
    """Reset the rate limiter call history."""
```

---

## Models

### Note

**Location**: `src/models/note.py`

**Description**: Data model for a note.

#### Properties

```python
id: str  # Unique identifier (UUID)
title: str  # Note title
content: str  # Note content (plain text)
tags: List[str]  # List of associated tags
created_at: str  # ISO format timestamp
updated_at: str  # ISO format timestamp
is_deleted: bool  # Soft delete flag
content_html: Optional[str]  # Rich text HTML content
```

#### Constructor

```python
def __init__(
    self,
    title: str = "",
    content: str = "",
    tags: Optional[List[str]] = None,
    id: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    is_deleted: bool = False
):
    """
    Initialize a Note object.
    
    Args:
        title: Note title
        content: Note content
        tags: List of tags (defaults to empty list)
        id: Optional ID (generates UUID if not provided)
        created_at: Optional creation timestamp
        updated_at: Optional update timestamp
        is_deleted: Soft delete flag
    """
```

#### Methods

```python
def to_dict(self) -> dict:
    """
    Convert note to dictionary representation.
    
    Returns:
        Dictionary with all note properties
    """

def from_dict(cls, data: dict) -> 'Note':
    """
    Create Note instance from dictionary.
    
    Args:
        data: Dictionary with note properties
        
    Returns:
        Note instance
    """
```

---

## Configuration Constants

### NotesSecurityConfig

**Location**: `src/gui/components/notes_security.py`

```python
class NotesSecurityConfig:
    # Maximum lengths
    MAX_TITLE_LENGTH = 255
    MAX_CONTENT_LENGTH = 10 * 1024  # 10KB
    MAX_TAG_LENGTH = 50
    MAX_TAGS_PER_NOTE = 20
    MAX_SEARCH_QUERY_LENGTH = 200
    
    # Rate limiting
    MAX_SAVES_PER_MINUTE = 60
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # HTML sanitization
    ALLOWED_HTML_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 's', 'span',
        'ul', 'ol', 'li', 'div'
    }
    
    ALLOWED_ATTRIBUTES = {
        'span': ['style'],
        'p': ['style'],
        'div': ['style']
    }
    
    ALLOWED_STYLE_PROPERTIES = {
        'color', 'background-color', 'text-align',
        'font-family', 'font-size', 'font-weight',
        'font-style', 'text-decoration'
    }
```

---

## Usage Examples

### Creating a New Note

```python
from src.database.notes_db import NotesDatabase
from src.models.note import Note

# Initialize database
db = NotesDatabase()

# Create new note
note = Note(
    title="My First Note",
    content="This is the content of my note.",
    tags=["personal", "important"]
)

# Save to database
result = db.create_note(note)
if result["success"]:
    print(f"Note created with ID: {result['note_id']}")
else:
    print(f"Error: {result['error']}")
```

### Searching Notes

```python
# Search in all fields
results = db.search_notes("important", "All")

# Search only in titles
title_results = db.search_notes("First", "Title Only")

# Search only in tags
tag_results = db.search_notes("personal", "Tags Only")
```

### Managing Tags

```python
# Get all tags with counts
tags = db.get_all_tags()
# Returns: {"personal": 5, "work": 12, "important": 3}

# Rename a tag
result = db.rename_tag("personal", "private")
print(f"Updated {result['affected_notes']} notes")

# Delete a tag from all notes
result = db.delete_tag("temporary")
print(f"Removed tag from {result['affected_notes']} notes")
```

### Exporting Notes

```python
from src.gui.components.notes_exporter import NotesExporter

exporter = NotesExporter()

# Export single note as HTML
note = db.get_note(note_id)
html_path = exporter.export_note_as_html(note)

# Export all notes as ZIP
all_notes = db.get_all_notes()
zip_path = exporter.export_all_notes(all_notes)
```

### Security Example

```python
from src.gui.components.notes_security import get_notes_security

security = get_notes_security()

# Sanitize user input
safe_title = security.sanitize_note_title(user_title)
safe_content = security.sanitize_note_content(user_content)
safe_tags = security.sanitize_tags(user_tags)

# Validate before saving
validation = security.validate_note_data(safe_title, safe_content, safe_tags)
if validation['valid']:
    # Save note
    pass
else:
    # Show errors
    for error in validation['errors']:
        print(f"Validation error: {error}")
```

---

## Error Handling

All methods that interact with the database or perform I/O operations may raise exceptions. Common exceptions include:

- `DatabaseError`: Database operation failed
- `ValueError`: Invalid input parameters
- `FileNotFoundError`: Export directory not found
- `PermissionError`: No write permission for export

Always wrap database operations in try-except blocks:

```python
try:
    note = db.get_note(note_id)
    if note:
        # Process note
        pass
    else:
        # Handle not found
        pass
except DatabaseError as e:
    logger.error(f"Database error: {str(e)}")
    # Handle error appropriately
```

---

## Thread Safety

The Notes feature is designed for single-threaded GUI operation. Database operations are not thread-safe by default. If you need concurrent access:

1. Use separate database connections per thread
2. Implement proper locking mechanisms
3. Consider using Qt's signal/slot mechanism for cross-thread communication

---

## Performance Considerations

1. **Large Numbers of Notes**: Search and tag operations may slow down with thousands of notes. Consider implementing pagination.

2. **Auto-save Frequency**: The default 2-second interval balances responsiveness with performance. Adjust based on your needs.

3. **Export Operations**: Large exports run in the main thread. For very large collections, consider implementing background export.

4. **Tag Cloud Rendering**: With hundreds of tags, the tag cloud may become slow. Consider limiting displayed tags or implementing virtualization.