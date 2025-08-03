"""
Comprehensive unit tests for Notes GUI components.
Tests NoteEditor, NoteListWidget, and NotesPage with mocked database.
"""

import pytest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from src.models.note import Note
from src.gui.components.note_editor import NoteEditor
from src.gui.components.note_list_widget import NoteListWidget
from src.gui.pages.notes_page import NotesPage


@pytest.fixture(scope="session")
def app():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def mock_notes_db():
    """Create a mock NotesDatabase."""
    mock_db = Mock()
    mock_db.get_all_notes.return_value = []
    mock_db.create_note.return_value = {"success": True, "id": "test-id"}
    mock_db.update_note.return_value = {"success": True, "message": "Updated"}
    mock_db.delete_note.return_value = {"success": True, "message": "Deleted"}
    mock_db.search_notes.return_value = []
    return mock_db


class TestNoteEditor:
    """Test suite for NoteEditor component."""
    
    @pytest.fixture
    def editor(self, app):
        """Create a NoteEditor instance."""
        return NoteEditor()
    
    def test_initial_state(self, editor):
        """Test editor initial state."""
        assert editor.title_input.text() == ""
        assert editor.content_input.toPlainText() == ""
        assert editor.tags_input.text() == ""
        assert editor._note_id is None
    
    def test_load_note(self, editor):
        """Test loading a note into editor."""
        editor.load_note(
            note_id="test-123",
            title="Test Note",
            content="Test content",
            tags=["tag1", "tag2"]
        )
        
        assert editor._note_id == "test-123"
        assert editor.title_input.text() == "Test Note"
        assert editor.content_input.toPlainText() == "Test content"
        assert editor.tags_input.text() == "tag1, tag2"
    
    def test_load_note_with_empty_tags(self, editor):
        """Test loading note with empty tags."""
        editor.load_note(
            note_id="test-123",
            title="Test Note",
            content="Test content",
            tags=[]
        )
        
        assert editor.tags_input.text() == ""
    
    def test_get_note_data(self, editor):
        """Test getting note data from editor."""
        editor.title_input.setText("My Title")
        editor.content_input.setPlainText("My Content")
        editor.tags_input.setText("tag1, tag2, tag3")
        editor._note_id = "test-id"
        
        note_id, title, content, tags = editor.get_note_data()
        
        assert note_id == "test-id"
        assert title == "My Title"
        assert content == "My Content"
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_get_note_data_strips_whitespace(self, editor):
        """Test that tags are properly stripped of whitespace."""
        editor.tags_input.setText("  tag1  ,  tag2  ,  tag3  ")
        
        _, _, _, tags = editor.get_note_data()
        
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_get_note_data_filters_empty_tags(self, editor):
        """Test that empty tags are filtered out."""
        editor.tags_input.setText("tag1,,tag2,  ,tag3")
        
        _, _, _, tags = editor.get_note_data()
        
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_clear_editor(self, editor):
        """Test clearing the editor."""
        # Set some data
        editor.load_note("test-id", "Title", "Content", ["tag"])
        
        # Clear it
        editor.clear_editor()
        
        assert editor._note_id is None
        assert editor.title_input.text() == ""
        assert editor.content_input.toPlainText() == ""
        assert editor.tags_input.text() == ""
    
    def test_note_changed_signal_on_title(self, editor):
        """Test note_changed signal emits on title change."""
        signal_spy = Mock()
        editor.note_changed.connect(signal_spy)
        
        editor.title_input.setText("New Title")
        
        assert signal_spy.call_count >= 1
    
    def test_note_changed_signal_on_content(self, editor):
        """Test note_changed signal emits on content change."""
        signal_spy = Mock()
        editor.note_changed.connect(signal_spy)
        
        editor.content_input.setPlainText("New Content")
        
        assert signal_spy.call_count >= 1
    
    def test_note_changed_signal_on_tags(self, editor):
        """Test note_changed signal emits on tags change."""
        signal_spy = Mock()
        editor.note_changed.connect(signal_spy)
        
        editor.tags_input.setText("new, tags")
        
        assert signal_spy.call_count >= 1
    
    def test_set_focus(self, editor, app):
        """Test setting focus to title input."""
        editor.show()
        app.processEvents()
        
        editor.set_focus()
        app.processEvents()
        
        assert editor.title_input.hasFocus()


class TestNoteListWidget:
    """Test suite for NoteListWidget component."""
    
    @pytest.fixture
    def note_list(self, app):
        """Create a NoteListWidget instance."""
        return NoteListWidget()
    
    def test_initial_state(self, note_list):
        """Test initial state of note list."""
        assert note_list.count() == 0
        assert note_list.search_input.text() == ""
    
    def test_load_notes(self, note_list):
        """Test loading notes into the list."""
        notes = [
            Note(id="1", title="Note 1", content="Content 1"),
            Note(id="2", title="Note 2", content="Content 2"),
            Note(id="3", title="Note 3", content="Content 3")
        ]
        
        note_list.load_notes(notes)
        
        assert note_list.count() == 3
        assert note_list.item(0).text() == "Note 1"
        assert note_list.item(1).text() == "Note 2"
        assert note_list.item(2).text() == "Note 3"
    
    def test_load_notes_with_custom_item(self, note_list):
        """Test that custom note items have correct properties."""
        note = Note(
            id="test-id",
            title="Test Note",
            content="Test content"
        )
        
        note_list.load_notes([note])
        
        item = note_list.item(0)
        assert hasattr(item, 'note')
        assert item.note.id == "test-id"
        assert item.note.title == "Test Note"
    
    def test_clear_notes(self, note_list):
        """Test clearing the note list."""
        notes = [
            Note(id="1", title="Note 1", content="Content 1"),
            Note(id="2", title="Note 2", content="Content 2")
        ]
        note_list.load_notes(notes)
        
        note_list.clear()
        
        assert note_list.count() == 0
    
    def test_select_first_note(self, note_list):
        """Test selecting the first note."""
        notes = [
            Note(id="1", title="Note 1", content="Content 1"),
            Note(id="2", title="Note 2", content="Content 2")
        ]
        note_list.load_notes(notes)
        
        note_list.select_first_note()
        
        assert note_list.currentRow() == 0
    
    def test_note_selected_signal(self, note_list):
        """Test note_selected signal emission."""
        signal_spy = Mock()
        note_list.note_selected.connect(signal_spy)
        
        note = Note(id="1", title="Note 1", content="Content 1")
        note_list.load_notes([note])
        
        # Simulate clicking on the note
        note_list.setCurrentRow(0)
        note_list._on_item_clicked(note_list.item(0))
        
        signal_spy.assert_called_once()
        emitted_note = signal_spy.call_args[0][0]
        assert emitted_note.id == "1"
    
    def test_search_functionality(self, note_list):
        """Test search filtering."""
        notes = [
            Note(id="1", title="Python Tutorial", content="Learn Python"),
            Note(id="2", title="JavaScript Guide", content="Learn JS"),
            Note(id="3", title="Python Advanced", content="Advanced Python")
        ]
        note_list.load_notes(notes)
        note_list.set_all_notes(notes)
        
        # Search for "Python"
        note_list.search_input.setText("Python")
        note_list._on_search_text_changed("Python")
        
        # Should show 2 Python notes
        visible_count = sum(
            1 for i in range(note_list.count()) 
            if not note_list.item(i).isHidden()
        )
        assert visible_count == 2
    
    def test_search_case_insensitive(self, note_list):
        """Test that search is case insensitive."""
        notes = [
            Note(id="1", title="PYTHON", content=""),
            Note(id="2", title="python", content=""),
            Note(id="3", title="Python", content="")
        ]
        note_list.load_notes(notes)
        note_list.set_all_notes(notes)
        
        # Search with different case
        note_list.search_input.setText("python")
        note_list._on_search_text_changed("python")
        
        # All should be visible
        visible_count = sum(
            1 for i in range(note_list.count()) 
            if not note_list.item(i).isHidden()
        )
        assert visible_count == 3
    
    def test_get_note_count(self, note_list):
        """Test getting note count."""
        notes = [
            Note(id="1", title="Note 1", content=""),
            Note(id="2", title="Note 2", content=""),
            Note(id="3", title="Note 3", content="")
        ]
        note_list.load_notes(notes)
        
        assert note_list.get_note_count() == 3


class TestNotesPage:
    """Test suite for NotesPage integration."""
    
    @pytest.fixture
    def notes_page(self, app, mock_notes_db):
        """Create a NotesPage instance with mocked database."""
        with patch('src.gui.pages.notes_page.NotesDatabase') as mock_db_class:
            mock_db_class.return_value = mock_notes_db
            page = NotesPage()
            yield page
    
    def test_initial_state(self, notes_page):
        """Test initial state of notes page."""
        assert notes_page._current_note is None
        assert notes_page._has_unsaved_changes is False
        assert notes_page.save_action.isEnabled() is False
        assert notes_page.delete_action.isEnabled() is False
    
    def test_create_new_note(self, notes_page):
        """Test creating a new note."""
        # Click new note
        notes_page._create_new_note()
        
        assert notes_page._current_note is None
        assert notes_page.save_action.isEnabled() is True
        assert notes_page.delete_action.isEnabled() is False
        assert notes_page.note_editor.title_input.text() == ""
    
    def test_save_new_note(self, notes_page, mock_notes_db):
        """Test saving a new note."""
        # Create new note
        notes_page._create_new_note()
        
        # Enter some data
        notes_page.note_editor.title_input.setText("New Note")
        notes_page.note_editor.content_input.setPlainText("New Content")
        
        # Save it
        notes_page._save_note()
        
        # Verify create_note was called
        mock_notes_db.create_note.assert_called_once()
        created_note = mock_notes_db.create_note.call_args[0][0]
        assert created_note.title == "New Note"
        assert created_note.content == "New Content"
    
    def test_save_empty_note_shows_warning(self, notes_page, mock_notes_db):
        """Test saving empty note shows warning."""
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            # Create new note but don't enter any data
            notes_page._create_new_note()
            
            # Try to save
            notes_page._save_note()
            
            # Should show warning
            mock_warning.assert_called_once()
            assert "Empty Note" in mock_warning.call_args[0][1]
            
            # Should not call database
            mock_notes_db.create_note.assert_not_called()
    
    def test_update_existing_note(self, notes_page, mock_notes_db):
        """Test updating an existing note."""
        # Create and select a note
        note = Note(id="test-id", title="Original", content="Original content")
        notes_page._on_note_selected(note)
        
        # Modify it
        notes_page.note_editor.title_input.setText("Updated Title")
        notes_page._on_note_changed()
        
        # Save it
        notes_page._save_note()
        
        # Verify update_note was called
        mock_notes_db.update_note.assert_called_once_with(
            "test-id",
            {
                "title": "Updated Title",
                "content": "Original content",
                "tags": []
            }
        )
    
    def test_delete_note_with_confirmation(self, notes_page, mock_notes_db):
        """Test deleting a note with confirmation."""
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.StandardButton.Yes
            
            # Select a note
            note = Note(id="test-id", title="To Delete", content="")
            notes_page._current_note = note
            
            # Delete it
            notes_page._delete_note()
            
            # Verify confirmation was shown
            mock_question.assert_called_once()
            assert "To Delete" in mock_question.call_args[0][2]
            
            # Verify delete was called
            mock_notes_db.delete_note.assert_called_once_with("test-id")
    
    def test_delete_note_cancelled(self, notes_page, mock_notes_db):
        """Test cancelling note deletion."""
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.StandardButton.No
            
            # Select a note
            note = Note(id="test-id", title="To Delete", content="")
            notes_page._current_note = note
            
            # Try to delete it
            notes_page._delete_note()
            
            # Verify delete was NOT called
            mock_notes_db.delete_note.assert_not_called()
    
    def test_unsaved_changes_warning_on_new_note(self, notes_page):
        """Test warning for unsaved changes when creating new note."""
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.StandardButton.Discard
            
            # Simulate having unsaved changes
            notes_page._has_unsaved_changes = True
            notes_page._current_note = Note(
                id="test", title="Current", content="")
            
            # Try to create new note
            notes_page._create_new_note()
            
            # Should show warning
            mock_question.assert_called_once()
            assert "Unsaved Changes" in mock_question.call_args[0][1]
    
    def test_unsaved_changes_warning_on_note_switch(self, notes_page):
        """Test warning for unsaved changes when switching notes."""
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.StandardButton.Discard
            
            # Simulate having unsaved changes
            notes_page._has_unsaved_changes = True
            notes_page._current_note = Note(
                id="current", title="Current", content="")
            
            # Try to switch to another note
            new_note = Note(id="new", title="New Note", content="")
            notes_page._on_note_selected(new_note)
            
            # Should show warning
            mock_question.assert_called_once()
            assert "Unsaved Changes" in mock_question.call_args[0][1]
    
    def test_note_count_update(self, notes_page):
        """Test note count label updates."""
        # Mock the note list to return a count
        notes_page.note_list.get_note_count = Mock(return_value=5)
        
        notes_page._update_note_count()
        
        assert notes_page.count_label.text() == "5 notes"
    
    def test_note_count_singular(self, notes_page):
        """Test note count label for single note."""
        notes_page.note_list.get_note_count = Mock(return_value=1)
        
        notes_page._update_note_count()
        
        assert notes_page.count_label.text() == "1 note"


class TestIntegration:
    """Integration tests for the Notes feature."""
    
    @pytest.fixture
    def integrated_page(self, app):
        """Create a real NotesPage with test database."""
        with patch('src.database.notes_db.NotesDatabase._get_database_path'):
            page = NotesPage()
            yield page
    
    def test_full_workflow(self, integrated_page):
        """Test complete workflow: create, edit, save, delete."""
        # Start with empty page
        assert integrated_page.note_list.count() == 0
        
        # Create new note
        integrated_page._create_new_note()
        integrated_page.note_editor.title_input.setText("Test Note")
        integrated_page.note_editor.content_input.setPlainText("Test Content")
        
        # Mock the database response
        with patch.object(
            integrated_page.notes_db, 'create_note'
        ) as mock_create:
            mock_create.return_value = {
                "success": True, 
                "id": "new-note-id"
            }
            
            # Save it
            integrated_page._save_note()
            
            # Verify it was called
            mock_create.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])