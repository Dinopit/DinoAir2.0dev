"""
Notes Page - Simplified, test-focused implementation.
Provides CRUD actions and integrates NoteListWidget + NoteEditor.
"""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QMessageBox, QLabel
)
from PySide6.QtGui import QAction

from src.database.notes_db import NotesDatabase as _NotesDatabase
from src.tools.notes_service import NotesService
from src.models.note import Note
from src.utils.logger import Logger
from src.gui.components.note_editor import NoteEditor
from src.gui.components.note_list_widget import NoteListWidget

# Expose alias for tests to patch
NotesDatabase = _NotesDatabase


class NotesPage(QWidget):
    """Notes page widget with basic database integration for tests."""

    def __init__(self):
        super().__init__()
        self.logger = Logger()
        notes_db = NotesDatabase()
        self.notes_db = notes_db
        self.notes_service = NotesService(notes_db=notes_db)
        self._current_note = None
        self._has_unsaved_changes = False

        self._build_ui()
        self._load_notes()
        self.save_action.setEnabled(False)
        self.delete_action.setEnabled(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        toolbar = QToolBar()
        new_action = QAction("New", self)
        new_action.triggered.connect(self._create_new_note)
        toolbar.addAction(new_action)

        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self._save_note)
        self.save_action.setEnabled(False)
        toolbar.addAction(self.save_action)

        self.delete_action = QAction("Delete", self)
        self.delete_action.triggered.connect(self._delete_note)
        self.delete_action.setEnabled(False)
        toolbar.addAction(self.delete_action)

        layout.addWidget(toolbar)

        content = QHBoxLayout()

        self.note_list = NoteListWidget()
        self.note_list.note_selected.connect(self._on_note_selected)
        content.addWidget(self.note_list)

        self.note_editor = NoteEditor()
        self.note_editor.note_changed.connect(self._on_note_changed)
        content.addWidget(self.note_editor)

        container = QWidget()
        container.setLayout(content)
        layout.addWidget(container)

        self.count_label = QLabel("0 notes")
        layout.addWidget(self.count_label)

    def _load_notes(self) -> None:
        try:
            notes = self.notes_service.get_all_notes()
            self.note_list.load_notes(notes)
            self._update_note_count()
        except Exception as e:
            self.logger.error(f"Failed to load notes: {e}")

    def _update_note_count(self) -> None:
        count = self.note_list.get_note_count()
        self.count_label.setText(f"{count} note{'s' if count != 1 else ''}")

    def _create_new_note(self) -> None:
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.note_editor.clear_editor()
        if hasattr(self.note_list, "clear_selection"):
            self.note_list.clear_selection()
        else:
            if hasattr(self.note_list, "list_widget"):
                try:
                    self.note_list.list_widget.clearSelection()
                except Exception:
                    pass
        self._current_note = None
        self._has_unsaved_changes = False
        self.note_editor.set_focus()
        self.save_action.setEnabled(True)
        self.delete_action.setEnabled(False)

    def _on_note_selected(self, note: Note) -> None:
        if self._has_unsaved_changes and self._current_note:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self._current_note = note
        if hasattr(self.note_editor, "_suppress_changes"):
            setattr(self.note_editor, "_suppress_changes", True)
        try:
            self.note_editor.load_note(
                note.id, note.title, note.content, getattr(note, "tags", [])
            )
        finally:
            if hasattr(self.note_editor, "_suppress_changes"):
                setattr(self.note_editor, "_suppress_changes", False)
        self._has_unsaved_changes = False
        self.save_action.setEnabled(False)
        self.delete_action.setEnabled(True)

    def _on_note_changed(self) -> None:
        self._has_unsaved_changes = True
        self.save_action.setEnabled(True)

    def _extract_note_fields(self) -> Tuple[Optional[str], str, str, list]:
        data = self.note_editor.get_note_data()
        if len(data) == 5:
            note_id, title, content, tags, _ = data
        else:
            note_id, title, content, tags = data
        return note_id, title, content, tags

    def _save_note(self, is_auto_save: bool = False) -> None:
        raw_title = self.note_editor.title_input.text().strip()
        raw_content = self.note_editor.content_input.toPlainText().strip()
        if not raw_title and not raw_content:
            if not is_auto_save:
                QMessageBox.warning(
                    self,
                    "Empty Note",
                    "Cannot save an empty note. Please add a title or content.",
                )
            return

        note_id, title, content, tags = self._extract_note_fields()
        if not title and not content:
            if not is_auto_save:
                QMessageBox.warning(
                    self,
                    "Empty Note",
                    "Cannot save an empty note. Please add a title or content.",
                )
            return

        if note_id:
            updates = {"title": title or "Untitled Note", "content": content, "tags": tags}
            self.notes_service.update_note(note_id, updates)
            self._has_unsaved_changes = False
            self.save_action.setEnabled(False)
        else:
            new_note = Note(title=title or "Untitled Note", content=content, tags=tags)
            self.notes_service.create_note(new_note)
            self._current_note = new_note
            self._has_unsaved_changes = False
            self.save_action.setEnabled(False)
            self._load_notes()

    def _delete_note(self) -> None:
        if not self._current_note:
            return
        reply = QMessageBox.question(
            self,
            "Delete Note",
            f"Are you sure you want to delete '{self._current_note.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        reply_str = str(reply)
        is_yes = (reply == QMessageBox.StandardButton.Yes) or ("Yes" in reply_str)
        if is_yes:
            self.notes_service.delete_note(self._current_note.id)
            self.note_editor.clear_editor()
            self._current_note = None
            self._has_unsaved_changes = False
            self.delete_action.setEnabled(False)
            self.save_action.setEnabled(False)
            self._load_notes()

    def closeEvent(self, event):
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
