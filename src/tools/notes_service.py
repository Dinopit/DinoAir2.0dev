"""
Notes Service
Thin, testable wrapper around NotesDatabase with simple caching and invalidation.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from time import monotonic

from src.database.initialize_db import DatabaseManager
from src.database.notes_db import NotesDatabase
from src.models.note import Note
from src.utils.logger import Logger


class NotesService:
    """Service for notes CRUD with straightforward caching.

    The cache aims to reduce repeated reads during rapid GUI updates.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        notes_db: Optional[NotesDatabase] = None,
        cache_ttl_sec: float = 5.0,
    ):
        self.logger = Logger()
        self._db_manager = db_manager or DatabaseManager()
        self._notes_db = notes_db or NotesDatabase(self._db_manager)
        self._cache_ttl = cache_ttl_sec
        self._cache_time = 0.0
        self._cache_all: Optional[List[Note]] = None

    def _is_cache_valid(self) -> bool:
        return self._cache_all is not None and (monotonic() - self._cache_time) < self._cache_ttl

    def _invalidate(self) -> None:
        self._cache_all = None
        self._cache_time = 0.0

    def get_all_notes(self) -> List[Note]:
        try:
            if self._is_cache_valid():
                return list(self._cache_all or [])
            data = self._notes_db.get_all_notes()
            self._cache_all = list(data)
            self._cache_time = monotonic()
            return list(self._cache_all)
        except Exception as e:
            self.logger.error(f"Failed to get notes: {e}")
            return []

    def create_note(self, note: Note) -> None:
        self._notes_db.create_note(note)
        self._invalidate()

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> None:
        self._notes_db.update_note(note_id, updates)
        self._invalidate()

    def delete_note(self, note_id: str) -> None:
        self._notes_db.delete_note(note_id)
        self._invalidate()
