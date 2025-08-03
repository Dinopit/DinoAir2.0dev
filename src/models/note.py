### Note Class
from datetime import datetime
import sqlite3
import uuid

class Note:
    def __init__(self, id=None, title="", content="", tags=None, project_id=None):
         # Generate ID if not provided
        self.id = id if id else str(uuid.uuid4())
        self.title = title
        self.content = content
        self.tags = tags if tags else []
        self.project_id = project_id  # Optional project association
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def update(self, title=None, content=None, tags=None):
        if title:
            self.title = title
        if content:
            self.content = content
        if tags is not None:
            self.tags = tags
        self.updated_at = datetime.now().isoformat()

    def __str__(self):
        project_info = f", project_id='{self.project_id}'" if self.project_id else ""
        return f"Note(id={self.id}, title='{self.title}'{project_info})"


class NoteList:
    """A collection of notes with management operations"""
    
    def __init__(self):
        self.notes = {}
        
    def add_note(self, note):
        """Add a note to the collection"""
        self.notes[note.id] = note
        
    def get_note(self, note_id):
        """Get a note by ID"""
        return self.notes.get(note_id)
        
    def remove_note(self, note_id):
        """Remove a note by ID"""
        if note_id in self.notes:
            del self.notes[note_id]
            return True
        return False
        
    def get_all_notes(self):
        """Get all notes as a list"""
        return list(self.notes.values())
        
    def search_notes(self, query):
        """Search notes by title or content"""
        results = []
        query_lower = query.lower()
        for note in self.notes.values():
            if (query_lower in note.title.lower() or 
                query_lower in note.content.lower()):
                results.append(note)
        return results
        
    def __len__(self):
        return len(self.notes)
        
    def __str__(self):
        return f"NoteList({len(self.notes)} notes)"