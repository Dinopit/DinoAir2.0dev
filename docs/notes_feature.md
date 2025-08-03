# Notes Feature Documentation

## Table of Contents

1. [Overview](#overview)
   - [Feature Description](#feature-description)
   - [Key Capabilities](#key-capabilities)
   - [Architecture Diagram](#architecture-diagram)
2. [User Guide](#user-guide)
   - [Getting Started](#getting-started)
   - [Basic Operations](#basic-operations)
   - [Advanced Features](#advanced-features)
   - [Exporting Notes](#exporting-notes)
3. [Developer Guide](#developer-guide)
   - [Architecture](#architecture)
   - [Key Components](#key-components)
   - [API Reference](#api-reference)
4. [Security Implementation](#security-implementation)
   - [Input Sanitization](#input-sanitization)
   - [XSS Protection](#xss-protection)
   - [SQL Injection Prevention](#sql-injection-prevention)
   - [Rate Limiting](#rate-limiting)
5. [Configuration](#configuration)
   - [Auto-save Settings](#auto-save-settings)
   - [Export Preferences](#export-preferences)
   - [Security Settings](#security-settings)
6. [Testing](#testing)
   - [Unit Test Coverage](#unit-test-coverage)
   - [Integration Tests](#integration-tests)
   - [Security Tests](#security-tests)
7. [Troubleshooting](#troubleshooting)
   - [Common Issues](#common-issues)
   - [Performance Tips](#performance-tips)
   - [Debug Logging](#debug-logging)

## Overview

### Feature Description

The Notes feature in DinoAir 2.0 is a comprehensive note-taking system that provides users with a secure, feature-rich environment for creating, organizing, and managing their notes. Built with a focus on user experience and data security, it offers advanced capabilities like rich text editing, auto-save with conflict detection, tag-based organization, and multiple export formats.

### Key Capabilities

- **Rich Text Editing**: Full formatting support including bold, italic, underline, strikethrough, and color customization
- **Auto-save**: Intelligent auto-save with configurable intervals and conflict detection
- **Tag Management**: Organize notes with tags, featuring a visual tag cloud interface
- **Advanced Search**: Search across titles, content, and tags with real-time filtering
- **Export Options**: Export individual notes or entire collections as HTML, TXT, PDF, or ZIP archives
- **Security-First Design**: Comprehensive input sanitization, XSS protection, and rate limiting
- **Keyboard Shortcuts**: Efficient navigation with keyboard shortcuts (Ctrl+F for search, etc.)
- **Responsive UI**: Clean, modern interface with the DinoAir color scheme

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Notes Feature                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐        ┌─────────────────┐                │
│  │   GUI Layer     │        │  Security Layer │                │
│  │                 │        │                 │                │
│  │ • NotesPage     │        │ • NotesSecurity │                │
│  │ • NoteEditor    │◄───────┤ • HTMLSanitizer │                │
│  │ • NoteListWidget│        │ • RateLimiter   │                │
│  │ • TagManager    │        │                 │                │
│  │ • NotesExporter │        └────────┬────────┘                │
│  │ • NotesSearch   │                 │                         │
│  └────────┬────────┘                 │                         │
│           │                           │                         │
│           ▼                           ▼                         │
│  ┌──────────────────────────────────────────────┐              │
│  │            Database Layer                     │              │
│  │                                               │              │
│  │  • NotesDatabase                              │              │
│  │  • CRUD Operations                            │              │
│  │  • Tag Management                             │              │
│  │  • Search & Filter                            │              │
│  │  • Soft Delete/Restore                        │              │
│  └───────────────────┬──────────────────────────┘              │
│                      │                                          │
│                      ▼                                          │
│           ┌──────────────────┐                                 │
│           │   SQLite DB      │                                 │
│           │   notes.db       │                                 │
│           └──────────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
```

## User Guide

### Getting Started

#### Accessing the Notes Tab

1. Launch DinoAir 2.0
2. Click on the "Notes" tab in the main navigation
3. The Notes interface will load with your existing notes or an empty state

#### Creating Your First Note

1. Click the "✚ New Note" button in the toolbar
2. Enter a title in the title field (optional but recommended)
3. Start typing your note content in the editor
4. Your note will auto-save after 2 seconds of inactivity (if auto-save is enabled)

### Basic Operations

#### Creating Notes

- Click "✚ New Note" or start typing with no note selected
- Add a title for easy identification
- Use the rich text toolbar for formatting
- Add tags by typing in the tag input field

#### Editing Notes

- Select a note from the list on the left
- Modify the title, content, or tags
- Changes are automatically saved (with visual indicator)
- Look for "All changes saved" status at the bottom

#### Deleting Notes

- Select the note you want to delete
- Click the "🗑️ Delete" button in the toolbar
- Confirm the deletion in the dialog
- Deleted notes can be recovered from the database if needed

#### Auto-save Functionality

- Auto-save is enabled by default
- Saves occur 2 seconds after you stop typing
- Visual indicators show save status:
  - Yellow: "Changes not saved"
  - Orange: "Saving..."
  - Cyan: "All changes saved"
  - Red: "Save failed" or "Conflict detected"
- Toggle auto-save with the "⚡ Auto-save" button

### Advanced Features

#### Rich Text Formatting

The rich text toolbar provides the following formatting options:

| Button | Function | Keyboard Shortcut |
|--------|----------|-------------------|
| **B** | Bold | Ctrl+B |
| *I* | Italic | Ctrl+I |
| U | Underline | Ctrl+U |
| ~~S~~ | Strikethrough | - |
| Color | Text color | - |
| Highlight | Background color | - |
| Align | Text alignment | - |
| • List | Bullet list | - |
| 1. List | Numbered list | - |

#### Search and Filtering

1. **Quick Search**: 
   - Press Ctrl+F to focus the search box
   - Type your search query
   - Results appear instantly with highlighting

2. **Filter Options**:
   - All: Search in title, content, and tags
   - Title Only: Search only in note titles
   - Content Only: Search only in note content
   - Tags Only: Search only in tags

3. **Search Features**:
   - Case-insensitive by default
   - Automatic highlighting of matches
   - Real-time results as you type
   - Press Escape to clear search

#### Tag Management

1. **Adding Tags**:
   - Type tag names in the tag input field
   - Press Enter or comma to add each tag
   - Tags are auto-completed from existing tags

2. **Tag Cloud**:
   - Click "🏷️ Tags" to show/hide the tag panel
   - Tags are displayed with size based on frequency
   - Click tags to filter notes
   - Right-click for tag management options

3. **Tag Operations**:
   - Rename: Right-click → "✏️ Rename Tag"
   - Delete: Right-click → "🗑️ Delete Tag"
   - Changes apply to all notes with that tag

#### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+F | Focus search box |
| Escape | Clear search (when in search box) |
| Ctrl+S | Save note (when auto-save is disabled) |
| Ctrl+N | Create new note |
| Ctrl+B | Bold text |
| Ctrl+I | Italic text |
| Ctrl+U | Underline text |

### Exporting Notes

#### Export Single Note

1. Select the note you want to export
2. Click the "📤 Export" dropdown button
3. Choose your format:
   - **📄 Export as HTML**: Styled HTML with formatting preserved
   - **📝 Export as Text**: Plain text format
   - **📑 Export as PDF**: PDF document with formatting

#### Export All Notes

1. Click "📤 Export" → "📦 Export All Notes (ZIP)"
2. Choose save location
3. The ZIP archive will contain:
   - `index.html`: Browseable index of all notes
   - `html/`: Folder with all notes in HTML format
   - `txt/`: Folder with all notes in plain text
   - `manifest.json`: Metadata about the export

#### Export Features

- Sanitized filenames prevent path traversal
- Preserves formatting in HTML/PDF exports
- Includes creation/modification dates
- Tags are included in all export formats
- Progress dialog for large exports

## Developer Guide

### Architecture

The Notes feature follows a layered architecture:

1. **GUI Layer**: User interface components built with PySide6
2. **Security Layer**: Input sanitization and validation
3. **Database Layer**: Data persistence with SQLite
4. **Model Layer**: Data structures (Note class)

### Key Components

#### NotesDatabase Class

Located in `src/database/notes_db.py`, handles all database operations:

```python
# Key methods:
- create_note(note: Note, content_html: Optional[str]) -> Dict[str, Any]
- get_note(note_id: str) -> Optional[Note]
- update_note(note_id: str, updates: Dict[str, Any]) -> Dict[str, Any]
- delete_note(note_id: str) -> Dict[str, Any]
- search_notes(query: str, filter_option: str) -> List[Note]
- get_all_tags() -> Dict[str, int]
- rename_tag(old_tag: str, new_tag: str) -> Dict[str, Any]
```

#### NotesPage Widget

The main interface (`src/gui/pages/notes_page.py`):

```python
# Key features:
- Auto-save with conflict detection
- Tag filtering and management
- Export functionality
- Keyboard shortcut handling
```

#### NoteEditor Component

Rich text editor (`src/gui/components/note_editor.py`):

```python
# Signals:
- note_changed: Emitted when content changes
- auto_save_requested: Triggers auto-save
- note_saved: Emitted after successful save

# Key methods:
- load_note(note_id, title, content, tags, content_html)
- get_note_data() -> tuple
- set_auto_save_enabled(enabled: bool)
```

#### NotesSecurity Module

Centralized security (`src/gui/components/notes_security.py`):

```python
# Key features:
- Input sanitization for all fields
- HTML content sanitization
- SQL injection prevention
- Rate limiting for auto-save
- XSS protection
```

### API Reference

See [notes_api_reference.md](notes_api_reference.md) for detailed API documentation.

## Security Implementation

### Input Sanitization

All user inputs are sanitized through the `NotesSecurity` class:

1. **Title Sanitization**:
   - Max length: 255 characters
   - HTML entities escaped
   - Special characters filtered

2. **Content Sanitization**:
   - Max length: 10KB
   - Preserves safe formatting
   - Removes potentially harmful content

3. **Tag Sanitization**:
   - Max length: 50 characters per tag
   - Max tags: 20 per note
   - Special characters filtered

### XSS Protection

Rich text content is sanitized using a custom HTML parser:

- Whitelist of allowed tags: `p`, `br`, `strong`, `em`, `u`, `s`, `span`, `ul`, `ol`, `li`, `div`
- Whitelist of allowed attributes: `style` (with restricted properties)
- All other tags and attributes are stripped
- JavaScript and event handlers are removed

### SQL Injection Prevention

- All database queries use parameterized statements
- SQL wildcards are escaped for LIKE queries
- Input validation before database operations

### Rate Limiting

Auto-save operations are rate-limited to prevent abuse:

- Default: 60 saves per minute (1 per second average)
- Configurable window and limits
- Visual feedback when rate limit is exceeded

## Configuration

Configuration is stored in `config/app_config.json`:

### Auto-save Settings

```json
"notes": {
    "auto_save": {
        "enabled": true,
        "interval_seconds": 2,
        "conflict_check_interval_seconds": 5,
        "show_save_status": true,
        "save_on_blur": true,
        "min_content_length": 1,
        "require_title_for_new_notes": true
    }
}
```

### Export Preferences

- Default export directory: User's home folder
- Supported formats: HTML, TXT, PDF, ZIP
- Filename sanitization enabled

### Security Settings

```json
"input_processing": {
    "enable_profanity_filter": true,
    "enable_pattern_detection": true,
    "enable_auto_translation": false,
    "default_language": "en"
}
```

## Testing

### Unit Test Coverage

Test files are located in the `tests/` directory:

1. **Database Tests** (`tests/test_notes_db.py`):
   - CRUD operations
   - Tag management
   - Search functionality
   - Error handling

2. **GUI Tests** (`tests/test_notes_gui.py`):
   - Widget creation
   - Signal emission
   - User interactions
   - State management

3. **Security Tests** (`tests/security/test_notes_security.py`):
   - Input sanitization
   - XSS prevention
   - Rate limiting
   - SQL injection prevention

### Integration Tests

- Full workflow tests (create, edit, save, export)
- Auto-save and conflict detection
- Tag management operations
- Search and filter combinations

### Security Tests

Comprehensive security testing includes:

- Malicious input attempts
- XSS payload testing
- SQL injection attempts
- Rate limit verification
- Path traversal prevention

## Troubleshooting

### Common Issues

#### Auto-save Not Working

**Symptoms**: Changes not saving automatically

**Solutions**:
1. Check if auto-save is enabled (⚡ button should be highlighted)
2. Verify rate limit hasn't been exceeded (check status bar)
3. Ensure note has a title (required for new notes)
4. Check application logs for errors

#### Search Not Finding Notes

**Symptoms**: Known notes don't appear in search results

**Solutions**:
1. Check filter setting (should be "All" for comprehensive search)
2. Clear search and try again
3. Verify notes aren't filtered by tags
4. Check for special characters in search query

#### Export Failing

**Symptoms**: Export doesn't complete or creates empty files

**Solutions**:
1. Check disk space availability
2. Verify write permissions in export directory
3. Try exporting to a different location
4. Check for special characters in note titles

#### Tag Cloud Not Updating

**Symptoms**: New tags don't appear or deleted tags persist

**Solutions**:
1. Click the refresh button (🔄) in tag panel
2. Close and reopen the tag panel
3. Restart the application if issue persists

### Performance Tips

1. **Large Number of Notes**:
   - Use search to filter displayed notes
   - Consider archiving old notes
   - Disable auto-save for bulk editing

2. **Slow Search**:
   - Use specific filters (Title Only, etc.)
   - Avoid very short search terms
   - Clear search when not needed

3. **Memory Usage**:
   - Export and remove very old notes
   - Limit number of notes open simultaneously
   - Restart application periodically

### Debug Logging

Enable debug logging for troubleshooting:

1. Set log level to DEBUG in `config/app_config.json`:
   ```json
   "logging": {
       "level": "DEBUG"
   }
   ```

2. Check logs in `logs/dinoair_YYYYMMDD.log`

3. Look for entries with:
   - `[NotesDatabase]` for database operations
   - `[NotesPage]` for UI interactions
   - `[NotesSecurity]` for security events
   - `[NotesExporter]` for export operations

Common log patterns:
- "Note sanitized" - Input was modified for security
- "Rate limit exceeded" - Too many save attempts
- "Tag rejected after sanitization" - Invalid tag input
- "Conflict detected" - Note modified elsewhere