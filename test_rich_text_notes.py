"""
Test script for rich text notes functionality in DinoAir 2.0

This script tests:
1. Rich text formatting capabilities
2. HTML sanitization security
3. Backward compatibility with plain text notes
4. Database operations with HTML content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.notes_db import NotesDatabase
from src.models.note import Note
from src.gui.components.notes_security import get_notes_security
from datetime import datetime


def test_rich_text_features():
    """Test the rich text editing features."""
    print("🧪 Testing Rich Text Notes Features\n")
    
    # Initialize components
    db = NotesDatabase("test_rich_text_user")
    security = get_notes_security()
    
    print("1️⃣ Testing HTML Sanitization...")
    test_html_sanitization(security)
    
    print("\n2️⃣ Testing Database Operations with HTML...")
    test_database_html_operations(db)
    
    print("\n3️⃣ Testing Backward Compatibility...")
    test_backward_compatibility(db)
    
    print("\n4️⃣ Testing Security Against XSS...")
    test_xss_protection(security)
    
    print("\n✅ All tests completed!")


def test_html_sanitization(security):
    """Test HTML sanitization functionality."""
    
    # Test case 1: Safe HTML
    safe_html = """
    <p>This is a <strong>bold</strong> and <em>italic</em> text.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <p style="color: red; text-align: center;">Colored and centered text</p>
    """
    
    result = security.sanitize_html_content(safe_html)
    assert result['modified'] == False, "Safe HTML should not be modified"
    print("  ✅ Safe HTML passed through correctly")
    
    # Test case 2: Dangerous HTML with scripts
    dangerous_html = """
    <p>Normal text</p>
    <script>alert('XSS')</script>
    <p onclick="alert('XSS')">Click me</p>
    <iframe src="evil.com"></iframe>
    """
    
    result = security.sanitize_html_content(dangerous_html)
    assert result['modified'] == True, "Dangerous HTML should be modified"
    assert '<script>' not in result['html'], "Script tags should be removed"
    assert 'onclick' not in result['html'], "Event handlers should be removed"
    assert '<iframe>' not in result['html'], "Iframe tags should be removed"
    print("  ✅ Dangerous HTML sanitized correctly")
    print(f"    - Stripped tags: {result['stripped_tags']}")
    
    # Test case 3: Style attribute sanitization
    style_html = """
    <p style="color: red; background-color: yellow; position: absolute;">
        Styled text
    </p>
    <span style="font-size: 16px; font-family: Arial; display: none;">
        More styled text
    </span>
    """
    
    result = security.sanitize_html_content(style_html)
    assert 'position: absolute' not in result['html'], "Dangerous CSS should be removed"
    assert 'display: none' not in result['html'], "Dangerous CSS should be removed"
    assert 'color: red' in result['html'], "Safe CSS should be preserved"
    print("  ✅ CSS properties filtered correctly")


def test_database_html_operations(db):
    """Test database operations with HTML content."""
    
    # Create a note with HTML content
    html_content = """
    <p><strong>Meeting Notes</strong></p>
    <ul>
        <li>Discussed <em>project timeline</em></li>
        <li>Budget: <span style="color: green;">$50,000</span></li>
    </ul>
    <p style="text-align: right;">- John Doe</p>
    """
    
    plain_content = "Meeting Notes\n- Discussed project timeline\n- Budget: $50,000\n- John Doe"
    
    note = Note(
        title="Rich Text Test Note",
        content=plain_content,
        tags=["meeting", "budget"]
    )
    
    # Create note with HTML
    result = db.create_note(note, html_content)
    assert result['success'], f"Failed to create note: {result.get('error')}"
    print(f"  ✅ Created note with HTML content: {note.id}")
    
    # Retrieve note and verify HTML content
    retrieved_note = db.get_note(note.id)
    assert retrieved_note is not None, "Failed to retrieve note"
    assert hasattr(retrieved_note, 'content_html'), "Note should have content_html attribute"
    assert retrieved_note.content_html == html_content, "HTML content should be preserved"
    print("  ✅ Retrieved note with HTML content intact")
    
    # Update note with new HTML
    new_html = """
    <p><strong>Updated Meeting Notes</strong></p>
    <p>Meeting <u>cancelled</u> due to weather.</p>
    """
    
    updates = {
        'title': 'Updated Rich Text Note',
        'content': 'Updated Meeting Notes\nMeeting cancelled due to weather.',
        'content_html': new_html
    }
    
    result = db.update_note(note.id, updates)
    assert result['success'], f"Failed to update note: {result.get('error')}"
    print("  ✅ Updated note with new HTML content")
    
    # Verify update
    updated_note = db.get_note(note.id)
    assert updated_note.content_html == new_html, "HTML content should be updated"
    print("  ✅ Verified HTML content update")
    
    # Search functionality with HTML content
    search_results = db.search_notes("Meeting")
    assert len(search_results) > 0, "Search should find the note"
    assert any(n.id == note.id for n in search_results), "Search should find our note"
    print("  ✅ Search works with HTML content notes")
    
    # Clean up
    db.delete_note(note.id, hard_delete=True)
    print("  ✅ Cleaned up test note")


def test_backward_compatibility(db):
    """Test backward compatibility with plain text notes."""
    
    # Create a plain text note (no HTML)
    plain_note = Note(
        title="Plain Text Note",
        content="This is a simple plain text note without any formatting.",
        tags=["plain", "simple"]
    )
    
    # Create note without HTML (backward compatibility)
    result = db.create_note(plain_note)
    assert result['success'], f"Failed to create plain note: {result.get('error')}"
    print(f"  ✅ Created plain text note: {plain_note.id}")
    
    # Retrieve and verify
    retrieved = db.get_note(plain_note.id)
    assert retrieved is not None, "Failed to retrieve plain note"
    assert retrieved.content == plain_note.content, "Plain content should be preserved"
    
    # Check that content_html is None or empty for plain notes
    content_html = getattr(retrieved, 'content_html', None)
    assert content_html is None or content_html == '', "Plain notes should not have HTML"
    print("  ✅ Plain text notes work without HTML")
    
    # Update plain note to add HTML
    updates = {
        'content_html': '<p>Now with <strong>formatting</strong>!</p>'
    }
    
    result = db.update_note(plain_note.id, updates)
    assert result['success'], "Failed to add HTML to plain note"
    print("  ✅ Successfully upgraded plain note to rich text")
    
    # Clean up
    db.delete_note(plain_note.id, hard_delete=True)


def test_xss_protection(security):
    """Test protection against XSS attacks."""
    
    xss_attempts = [
        # Script injection
        '<img src=x onerror="alert(\'XSS\')">',
        '<svg onload="alert(\'XSS\')"></svg>',
        
        # JavaScript URL
        '<a href="javascript:alert(\'XSS\')">Click</a>',
        
        # Data URL with script
        '<a href="data:text/html,<script>alert(\'XSS\')</script>">Click</a>',
        
        # Style attribute with expression
        '<p style="background:url(javascript:alert(\'XSS\'))">Text</p>',
        
        # Event handlers
        '<div onmouseover="alert(\'XSS\')">Hover me</div>',
        '<input onfocus="alert(\'XSS\')" value="Focus me">',
        
        # Meta refresh
        '<meta http-equiv="refresh" content="0;url=data:text/html,<script>alert(\'XSS\')</script>">',
    ]
    
    for i, xss in enumerate(xss_attempts):
        result = security.sanitize_html_content(xss)
        
        # Check that dangerous content was removed
        assert 'alert' not in result['html'].lower(), f"XSS attempt {i+1} not fully sanitized"
        assert 'javascript:' not in result['html'].lower(), f"JavaScript URL in attempt {i+1}"
        assert 'onerror' not in result['html'].lower(), f"Event handler in attempt {i+1}"
        assert 'onload' not in result['html'].lower(), f"Event handler in attempt {i+1}"
        assert 'onmouseover' not in result['html'].lower(), f"Event handler in attempt {i+1}"
        assert 'onfocus' not in result['html'].lower(), f"Event handler in attempt {i+1}"
        
        print(f"  ✅ XSS attempt {i+1} blocked successfully")
    
    print("  ✅ All XSS protection tests passed")


def test_rich_text_complete_workflow():
    """Test a complete workflow with rich text."""
    print("\n5️⃣ Testing Complete Rich Text Workflow...")
    
    db = NotesDatabase("test_workflow_user")
    security = get_notes_security()
    
    # Simulate user creating a rich text note
    user_input = {
        'title': 'My Rich Text Note',
        'content': 'My Rich Text Note\nThis has formatting!',
        'tags': ['test', 'rich-text'],
        'content_html': '''
            <h1>My Rich Text Note</h1>
            <p>This has <strong>bold</strong>, <em>italic</em>, and <u>underline</u>!</p>
            <ul>
                <li style="color: blue;">Blue item</li>
                <li style="color: red;">Red item</li>
            </ul>
            <script>alert("hack")</script>
        '''
    }
    
    # Sanitize the input
    sanitized = security.sanitize_note_data(
        user_input['title'],
        user_input['content'],
        user_input['tags'],
        user_input['content_html']
    )
    
    assert sanitized['valid'], f"Validation failed: {sanitized['errors']}"
    assert '<script>' not in sanitized['content_html'], "Script should be removed"
    print("  ✅ User input sanitized successfully")
    
    # Create note with sanitized content
    note = Note(
        title=sanitized['title'],
        content=sanitized['content'],
        tags=sanitized['tags']
    )
    
    result = db.create_note(note, sanitized['content_html'])
    assert result['success'], f"Failed to create workflow note: {result.get('error')}"
    print("  ✅ Note created with sanitized HTML")
    
    # Simulate loading the note
    loaded = db.get_note(note.id)
    assert loaded is not None, "Failed to load note"
    assert '<strong>bold</strong>' in loaded.content_html, "Formatting should be preserved"
    assert '<script>' not in loaded.content_html, "Dangerous content should remain removed"
    print("  ✅ Note loaded with safe HTML intact")
    
    # Clean up
    db.delete_note(note.id, hard_delete=True)
    print("  ✅ Workflow test completed successfully")


if __name__ == "__main__":
    try:
        test_rich_text_features()
        test_rich_text_complete_workflow()
        
        print("\n🎉 All rich text tests passed successfully!")
        print("\n📝 Summary:")
        print("  - Rich text formatting works correctly")
        print("  - HTML content is properly sanitized for security")
        print("  - Backward compatibility with plain text notes maintained")
        print("  - XSS protection is effective")
        print("  - Database operations handle HTML content properly")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)