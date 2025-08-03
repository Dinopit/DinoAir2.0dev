"""
Comprehensive unit tests for NotesDatabase operations.
Tests all CRUD operations, edge cases, and database integrity.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.models.note import Note
from src.database.notes_db import NotesDatabase


class TestNotesDatabase:
    """Test suite for NotesDatabase class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        # Create test database structure
        test_user_dir = (Path(temp_dir) / "user_data" /
                         "test_user" / "databases")
        test_user_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the path to the proper location
        test_db_path = test_user_dir / "notes.db"
        
        yield test_db_path
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def notes_db(self, temp_db, monkeypatch):
        """Create a NotesDatabase instance with test database."""
        # Mock the database path
        monkeypatch.setattr(
            'src.database.notes_db.NotesDatabase._get_database_path',
            lambda self: temp_db
        )
        
        # Create instance
        db = NotesDatabase(user_name="test_user")
        
        return db
    
    # CREATE TESTS
    def test_create_note_success(self, notes_db):
        """Test successful note creation."""
        note = Note(
            title="Test Note",
            content="This is test content",
            tags=["test", "sample"]
        )
        
        result = notes_db.create_note(note)
        
        assert result["success"] is True
        assert "id" in result
        assert result["message"] == "Note created successfully"
        
        # Verify note was saved
        saved_note = notes_db.get_note(note.id)
        assert saved_note is not None
        assert saved_note.title == "Test Note"
        assert saved_note.content == "This is test content"
        assert saved_note.tags == ["test", "sample"]
    
    def test_create_note_empty_title(self, notes_db):
        """Test creating note with empty title."""
        note = Note(
            title="",
            content="Content without title",
            tags=[]
        )
        
        result = notes_db.create_note(note)
        
        assert result["success"] is True
        
        # Should default to "Untitled Note"
        saved_note = notes_db.get_note(note.id)
        assert saved_note.title == "Untitled Note"
    
    def test_create_note_special_characters(self, notes_db):
        """Test creating note with special characters."""
        note = Note(
            title="Test <script>alert('XSS')</script>",
            content="Content with 'quotes' and \"double quotes\"",
            tags=["tag/with/slashes", "tag;with;semicolons"]
        )
        
        result = notes_db.create_note(note)
        
        assert result["success"] is True
        
        saved_note = notes_db.get_note(note.id)
        assert saved_note.title == note.title
        assert saved_note.content == note.content
        assert saved_note.tags == note.tags
    
    def test_create_note_database_error(self, notes_db, monkeypatch):
        """Test handling database errors during creation."""
        # Mock execute to raise an error
        def mock_execute(*args, **kwargs):
            raise sqlite3.Error("Database error")
        
        monkeypatch.setattr(sqlite3.Cursor, "execute", mock_execute)
        
        note = Note(title="Test", content="Test")
        result = notes_db.create_note(note)
        
        assert result["success"] is False
        assert "error" in result
    
    # READ TESTS
    def test_get_note_success(self, notes_db):
        """Test retrieving an existing note."""
        # Create a note first
        note = Note(title="Get Test", content="Content to retrieve")
        notes_db.create_note(note)
        
        # Retrieve it
        retrieved_note = notes_db.get_note(note.id)
        
        assert retrieved_note is not None
        assert retrieved_note.id == note.id
        assert retrieved_note.title == "Get Test"
        assert retrieved_note.content == "Content to retrieve"
    
    def test_get_note_not_found(self, notes_db):
        """Test retrieving non-existent note."""
        result = notes_db.get_note("non-existent-id")
        assert result is None
    
    def test_get_all_notes_empty(self, notes_db):
        """Test getting all notes when database is empty."""
        notes = notes_db.get_all_notes()
        assert notes == []
    
    def test_get_all_notes_multiple(self, notes_db):
        """Test getting all notes with multiple entries."""
        # Create multiple notes
        notes_data = [
            Note(title="Note 1", content="Content 1"),
            Note(title="Note 2", content="Content 2"),
            Note(title="Note 3", content="Content 3")
        ]
        
        for note in notes_data:
            notes_db.create_note(note)
        
        # Get all notes
        all_notes = notes_db.get_all_notes()
        
        assert len(all_notes) == 3
        assert all(isinstance(note, Note) for note in all_notes)
        
        # Check they're ordered by updated_at DESC
        assert all_notes[0].title == "Note 3"
        assert all_notes[2].title == "Note 1"
    
    def test_search_notes_by_title(self, notes_db):
        """Test searching notes by title."""
        # Create test notes
        notes_db.create_note(
            Note(title="Python Tutorial", content="Learn Python"))
        notes_db.create_note(
            Note(title="JavaScript Guide", content="Learn JS"))
        notes_db.create_note(
            Note(title="Python Advanced", content="Advanced topics"))
        
        # Search for Python
        results = notes_db.search_notes("Python")
        
        assert len(results) == 2
        assert all("Python" in note.title for note in results)
    
    def test_search_notes_by_content(self, notes_db):
        """Test searching notes by content."""
        # Create test notes
        notes_db.create_note(Note(title="Note 1", content="Django framework"))
        notes_db.create_note(Note(title="Note 2", content="Flask framework"))
        notes_db.create_note(Note(title="Note 3", content="No framework here"))
        
        # Search for framework
        results = notes_db.search_notes("framework")
        
        assert len(results) == 3
    
    def test_search_notes_by_tags(self, notes_db):
        """Test searching notes by tags."""
        # Create test notes with tags
        notes_db.create_note(
            Note(title="Note 1", content="", tags=["python", "tutorial"]))
        notes_db.create_note(
            Note(title="Note 2", content="", tags=["javascript", "tutorial"]))
        notes_db.create_note(
            Note(title="Note 3", content="", tags=["python", "advanced"]))
        
        # Search for python tag
        results = notes_db.search_notes("python")
        
        assert len(results) == 2
    
    def test_search_notes_case_insensitive(self, notes_db):
        """Test that search is case insensitive."""
        notes_db.create_note(Note(title="UPPERCASE", content="content"))
        notes_db.create_note(Note(title="lowercase", content="content"))
        notes_db.create_note(Note(title="MixedCase", content="content"))
        
        # Search with different cases
        results1 = notes_db.search_notes("case")
        results2 = notes_db.search_notes("CASE")
        results3 = notes_db.search_notes("CaSe")
        
        assert len(results1) == len(results2) == len(results3) == 3
    
    def test_search_notes_empty_query(self, notes_db):
        """Test searching with empty query returns all notes."""
        # Create some notes
        notes_db.create_note(Note(title="Note 1", content="Content 1"))
        notes_db.create_note(Note(title="Note 2", content="Content 2"))
        
        results = notes_db.search_notes("")
        
        assert len(results) == 2
    
    # UPDATE TESTS
    def test_update_note_success(self, notes_db):
        """Test successful note update."""
        # Create a note
        note = Note(title="Original", content="Original content")
        notes_db.create_note(note)
        
        # Update it
        updates = {
            "title": "Updated Title",
            "content": "Updated content",
            "tags": ["new", "tags"]
        }
        result = notes_db.update_note(note.id, updates)
        
        assert result["success"] is True
        assert result["message"] == "Note updated successfully"
        
        # Verify changes
        updated_note = notes_db.get_note(note.id)
        assert updated_note.title == "Updated Title"
        assert updated_note.content == "Updated content"
        assert updated_note.tags == ["new", "tags"]
    
    def test_update_note_partial(self, notes_db):
        """Test partial update (only some fields)."""
        # Create a note
        note = Note(title="Original", content="Original content", tags=["old"])
        notes_db.create_note(note)
        
        # Update only title
        result = notes_db.update_note(note.id, {"title": "New Title"})
        
        assert result["success"] is True
        
        # Verify only title changed
        updated_note = notes_db.get_note(note.id)
        assert updated_note.title == "New Title"
        assert updated_note.content == "Original content"  # Unchanged
        assert updated_note.tags == ["old"]  # Unchanged
    
    def test_update_note_not_found(self, notes_db):
        """Test updating non-existent note."""
        result = notes_db.update_note("non-existent-id", {"title": "New"})
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_update_note_empty_updates(self, notes_db):
        """Test update with empty updates dict."""
        # Create a note
        note = Note(title="Test", content="Test")
        notes_db.create_note(note)
        
        # Update with empty dict
        result = notes_db.update_note(note.id, {})
        
        assert result["success"] is True  # Should succeed but do nothing
    
    def test_update_note_updated_at_changes(self, notes_db):
        """Test that updated_at timestamp changes on update."""
        # Create a note
        note = Note(title="Test", content="Test")
        notes_db.create_note(note)
        
        original_note = notes_db.get_note(note.id)
        original_updated_at = original_note.updated_at
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update the note
        notes_db.update_note(note.id, {"title": "Updated"})
        
        updated_note = notes_db.get_note(note.id)
        assert updated_note.updated_at > original_updated_at
    
    # DELETE TESTS
    def test_delete_note_success(self, notes_db):
        """Test successful note deletion (soft delete)."""
        # Create a note
        note = Note(title="To Delete", content="Will be deleted")
        notes_db.create_note(note)
        
        # Delete it
        result = notes_db.delete_note(note.id)
        
        assert result["success"] is True
        assert result["message"] == "Note deleted successfully"
        
        # Verify it's not in normal get
        assert notes_db.get_note(note.id) is None
        
        # Verify it's not in get_all
        all_notes = notes_db.get_all_notes()
        assert not any(n.id == note.id for n in all_notes)
    
    def test_delete_note_not_found(self, notes_db):
        """Test deleting non-existent note."""
        result = notes_db.delete_note("non-existent-id")
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_restore_deleted_note(self, notes_db):
        """Test restoring a soft-deleted note."""
        # Create and delete a note
        note = Note(title="To Restore", content="Will be restored")
        notes_db.create_note(note)
        notes_db.delete_note(note.id)
        
        # Restore it
        result = notes_db.restore_note(note.id)
        
        assert result["success"] is True
        assert result["message"] == "Note restored successfully"
        
        # Verify it's back
        restored_note = notes_db.get_note(note.id)
        assert restored_note is not None
        assert restored_note.title == "To Restore"
    
    def test_permanent_delete(self, notes_db):
        """Test permanent deletion of a note."""
        # Create a note
        note = Note(
            title="To Permanently Delete",
            content="Will be gone forever")
        notes_db.create_note(note)
        
        # Permanently delete it
        result = notes_db.permanent_delete_note(note.id)
        
        assert result["success"] is True
        
        # Verify it's completely gone (even from database)
        conn = notes_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes WHERE id = ?", (note.id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 0
    
    # TAG OPERATIONS TESTS
    def test_get_all_tags(self, notes_db):
        """Test getting all unique tags."""
        # Create notes with various tags
        notes_db.create_note(
            Note(title="Note 1", content="", tags=["python", "tutorial"]))
        notes_db.create_note(
            Note(title="Note 2", content="", tags=["javascript", "tutorial"]))
        notes_db.create_note(
            Note(title="Note 3", content="", tags=["python", "advanced"]))
        
        tags = notes_db.get_all_tags()
        
        assert len(tags) == 4
        assert set(tags) == {"python", "tutorial", "javascript", "advanced"}
    
    def test_get_notes_by_tag(self, notes_db):
        """Test getting notes by specific tag."""
        # Create notes with tags
        note1 = Note(
            title="Python Basic", content="", tags=["python", "basic"])
        note2 = Note(
            title="Python Advanced", content="", tags=["python", "advanced"])
        note3 = Note(
            title="JS Tutorial", content="", tags=["javascript", "tutorial"])
        
        notes_db.create_note(note1)
        notes_db.create_note(note2)
        notes_db.create_note(note3)
        
        # Get notes with "python" tag
        python_notes = notes_db.get_notes_by_tag("python")
        
        assert len(python_notes) == 2
        assert all("python" in note.tags for note in python_notes)
    
    # EDGE CASES AND ERROR HANDLING
    def test_database_connection_error(self, monkeypatch):
        """Test handling database connection errors."""
        # Mock sqlite3.connect to raise an error
        def mock_connect(*args, **kwargs):
            raise sqlite3.Error("Connection failed")
        
        monkeypatch.setattr(sqlite3, "connect", mock_connect)
        
        db = NotesDatabase()
        result = db.create_note(Note(title="Test", content="Test"))
        
        assert result["success"] is False
        assert "error" in result
    
    def test_concurrent_access(self, notes_db):
        """Test concurrent database access."""
        import threading
        results = []
        
        def create_note(title):
            note = Note(title=title, content=f"Content for {title}")
            result = notes_db.create_note(note)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_note, args=(f"Note {i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert all(r["success"] for r in results)
        
        # Verify all notes were created
        all_notes = notes_db.get_all_notes()
        assert len(all_notes) == 5
    
    def test_very_long_content(self, notes_db):
        """Test handling very long content."""
        # Create a note with very long content
        long_content = "x" * 10000  # 10KB of content
        note = Note(title="Long Note", content=long_content)
        
        result = notes_db.create_note(note)
        assert result["success"] is True
        
        # Verify it can be retrieved
        saved_note = notes_db.get_note(note.id)
        assert saved_note.content == long_content
    
    def test_unicode_content(self, notes_db):
        """Test handling Unicode content."""
        note = Note(
            title="Unicode Test 🎉",
            content="Emojis: 😀😃😄 Special chars: ñáéíóú Chinese: 你好",
            tags=["unicode", "测试"]
        )
        
        result = notes_db.create_note(note)
        assert result["success"] is True
        
        # Verify Unicode is preserved
        saved_note = notes_db.get_note(note.id)
        assert saved_note.title == note.title
        assert saved_note.content == note.content
        assert saved_note.tags == note.tags
    
    def test_sql_injection_protection(self, notes_db):
        """Test protection against SQL injection."""
        # Try to inject SQL
        malicious_title = "'; DROP TABLE notes; --"
        note = Note(title=malicious_title, content="Test")
        
        result = notes_db.create_note(note)
        assert result["success"] is True
        
        # Verify table still exists and note was saved properly
        saved_note = notes_db.get_note(note.id)
        assert saved_note.title == malicious_title
        
        # Verify we can still get all notes
        all_notes = notes_db.get_all_notes()
        assert len(all_notes) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])