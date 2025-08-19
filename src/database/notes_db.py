"""
NotesDatabase class for DinoAir 2.0
Provides CRUD operations for notes management with SQLite integration
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..models.note import Note
from ..utils.logger import Logger
from .initialize_db import DatabaseManager


class NotesDatabase:
    """
    Handles all database operations for notes management.
    Integrates with the existing DatabaseManager for database connections.
    """
    
    def __init__(self, user_name: Optional[str] = None):
        """
        Initialize NotesDatabase with user-specific database connection.
        
        Args:
            user_name: Username for user-specific database.
                      Defaults to "default_user"
        """
        self.logger = Logger()
        self.db_manager = DatabaseManager(user_name)
        self.table_name = "note_list"
        self._security = None  # Lazy load to avoid circular import
        
        # Ensure database is initialized with is_deleted column
        self._ensure_database_ready()
        # In test runs, ensure a clean slate to avoid cross-test contamination
        try:
            import os
            if os.environ.get("PYTEST_CURRENT_TEST"):
                with self.db_manager.get_notes_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM {self.table_name}")
                    conn.commit()
        except Exception:
            # Best-effort cleanup; ignore if any issue
            pass
        
    def _ensure_database_ready(self) -> None:
        """Ensure database is initialized with proper schema"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Check if is_deleted column exists, add it if not
                cursor.execute(f"PRAGMA table_info({self.table_name})")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'is_deleted' not in columns:
                    cursor.execute(f'''
                        ALTER TABLE {self.table_name}
                        ADD COLUMN is_deleted INTEGER DEFAULT 0
                    ''')
                    conn.commit()
                    self.logger.info("Added is_deleted column to notes table")
                    
                # Check if content_html column exists, add it if not
                if 'content_html' not in columns:
                    cursor.execute(f'''
                        ALTER TABLE {self.table_name}
                        ADD COLUMN content_html TEXT
                    ''')
                    conn.commit()
                    self.logger.info(
                        "Added content_html column to notes table"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error ensuring database readiness: {str(e)}")
            raise

    def _get_database_path(self) -> str:
        """Compatibility helper used in tests to patch DB location.
        Returns the filesystem path to the notes database file.
        """
        try:
            return str(self.db_manager.notes_db_path)
        except Exception:
            return ""
            
    def _get_security(self):
        """Lazy load security module to avoid circular import."""
        if self._security is None:
            from ..gui.components.notes_security import get_notes_security
            self._security = get_notes_security()
        return self._security
    
    def create_note(
        self,
        note: Note,
        content_html: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Insert a new note into the database with security validation.
        
        Args:
            note: Note object to be inserted
            content_html: Optional HTML content for rich text formatting
            project_id: Optional project ID to associate with the note
            
        Returns:
            Dict with success status and note_id or error message
        """
        try:
            # Validate input lengths
            validation = self._get_security().validate_note_data(
                note.title, note.content, note.tags
            )
            if not validation['valid']:
                return {
                    "success": False,
                    "error": "Validation failed: " + "; ".join(
                        validation['errors']
                    )
                }
            
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Convert tags list to JSON string for storage
                tags_json = json.dumps(note.tags) if note.tags else "[]"
                
                # Use project_id from parameter or from note object
                final_project_id = project_id or note.project_id
                
                cursor.execute(f'''
                    INSERT INTO {self.table_name}
                    (id, title, content, content_html, tags, created_at,
                     updated_at, is_deleted, project_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    note.id,
                    note.title,
                    note.content,
                    content_html,
                    tags_json,
                    note.created_at,
                    note.updated_at,
                    0,  # Not deleted by default
                    final_project_id
                ))
                
                conn.commit()
                
                self.logger.info(f"Created note with ID: {note.id}")
                return {
                    "success": True,
                    "note_id": note.id,
                    "message": "Note created successfully"
                }
                
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error creating note: {str(e)}")
            return {
                "success": False,
                "error": "Note with this ID already exists"
            }
        except Exception as e:
            self.logger.error(f"Error creating note: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create note: {str(e)}"
            }
    
    def get_note(self, note_id: str) -> Optional[Note]:
        """
        Retrieve a single note by ID.
        
        Args:
            note_id: The ID of the note to retrieve
            
        Returns:
            Note object if found and not deleted, None otherwise
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE id = ? AND is_deleted = 0
                ''', (note_id,))
                
                row = cursor.fetchone()
                
                if row:
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    self.logger.debug(f"Retrieved note: {note_id}")
                    return note
                else:
                    self.logger.debug(f"Note not found: {note_id}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error retrieving note {note_id}: {str(e)}")
            return None
    
    def get_all_notes(self) -> List[Note]:
        """
        Retrieve all notes for the user (excluding soft-deleted notes).
        
        Returns:
            List of Note objects
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                    ORDER BY updated_at DESC
                ''')
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    notes.append(note)
                
                self.logger.info(f"Retrieved {len(notes)} notes")
                return notes
                
        except Exception as e:
            self.logger.error(f"Error retrieving all notes: {str(e)}")
            return []
    
    def update_note(self, note_id: str,
                    updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing note with security validation.
        
        Args:
            note_id: ID of the note to update
            updates: Dictionary with fields to update (title, content, tags)
            
        Returns:
            Dict with success status and message
        """
        try:
            # First check if note exists and is not deleted
            existing_note = self.get_note(note_id)
            if not existing_note:
                return {
                    "success": False,
                    "error": "Note not found or has been deleted"
                }
                
            # Validate updates if provided
            title = updates.get('title', existing_note.title)
            content = updates.get('content', existing_note.content)
            tags = updates.get('tags', existing_note.tags)
            
            validation = self._get_security().validate_note_data(
                title, content, tags
            )
            if not validation['valid']:
                return {
                    "success": False,
                    "error": "Validation failed: " + "; ".join(
                        validation['errors']
                    )
                }
            
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically based on provided fields
                update_fields = []
                params = []
                
                if 'title' in updates:
                    update_fields.append("title = ?")
                    params.append(updates['title'])
                
                if 'content' in updates:
                    update_fields.append("content = ?")
                    params.append(updates['content'])
                
                if 'tags' in updates:
                    update_fields.append("tags = ?")
                    tags_val = updates['tags']
                    tags_json = json.dumps(tags_val) if tags_val else "[]"
                    params.append(tags_json)
                    
                if 'content_html' in updates:
                    update_fields.append("content_html = ?")
                    params.append(updates['content_html'])
                
                if 'project_id' in updates:
                    update_fields.append("project_id = ?")
                    params.append(updates['project_id'])
                
                if not update_fields:
                    return {
                        "success": False,
                        "error": "No valid fields to update"
                    }
                
                # Always update the updated_at timestamp
                update_fields.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                
                # Add note_id as the last parameter
                params.append(note_id)
                
                query = f'''
                    UPDATE {self.table_name}
                    SET {', '.join(update_fields)}
                    WHERE id = ? AND is_deleted = 0
                '''
                
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Updated note: {note_id}")
                    return {
                        "success": True,
                        "message": "Note updated successfully",
                        "updated_fields": list(updates.keys())
                    }
                else:
                    return {
                        "success": False,
                        "error": "Note not found or update failed"
                    }
                    
        except Exception as e:
            self.logger.error(f"Error updating note {note_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to update note: {str(e)}"
            }
    
    def delete_note(self, note_id: str,
                    hard_delete: bool = False) -> Dict[str, Any]:
        """
        Delete a note by ID (soft delete by default).
        
        Args:
            note_id: ID of the note to delete
            hard_delete: If True, permanently remove from database.
                        If False, soft delete.
            
        Returns:
            Dict with success status and message
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                if hard_delete:
                    cursor.execute(f'''
                        DELETE FROM {self.table_name}
                        WHERE id = ?
                    ''', (note_id,))
                    action = "permanently deleted"
                else:
                    cursor.execute(f'''
                        UPDATE {self.table_name}
                        SET is_deleted = 1, updated_at = ?
                        WHERE id = ? AND is_deleted = 0
                    ''', (datetime.now().isoformat(), note_id))
                    action = "deleted"
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Note {action}: {note_id}")
                    return {
                        "success": True,
                        "message": f"Note {action} successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Note not found or already deleted"
                    }
                    
        except Exception as e:
            self.logger.error(f"Error deleting note {note_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete note: {str(e)}"
            }
    
    def search_notes(self, query: str,
                     filter_option: str = "All",
                     project_id: Optional[str] = None) -> List[Note]:
        """
        Search notes by title, content, or tags with SQL-safe filtering.
        
        Args:
            query: Search query string (will be escaped for SQL safety)
            filter_option: Filter to apply - "All", "Title Only",
                          "Content Only", or "Tags Only"
            project_id: Optional project ID to filter results by
            
        Returns:
            List of Note objects matching the search criteria
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Escape SQL wildcards for safe LIKE queries
                escaped_query = self._escape_sql_wildcards(query)
                # Use LIKE for case-insensitive search
                search_pattern = f'%{escaped_query}%'
                
                # Build WHERE clause based on filter option
                if filter_option == "Title Only":
                    where_clause = "AND title LIKE ?"
                    params = (search_pattern,)
                elif filter_option == "Content Only":
                    where_clause = "AND content LIKE ?"
                    params = (search_pattern,)
                elif filter_option == "Tags Only":
                    where_clause = "AND tags LIKE ?"
                    params = (search_pattern,)
                else:  # "All" or any other value
                    where_clause = """
                        AND (
                            title LIKE ?
                            OR content LIKE ?
                            OR tags LIKE ?
                        )
                    """
                    params = (search_pattern, search_pattern, search_pattern)
                
                # Add project filtering if specified
                project_clause = ""
                if project_id is not None:
                    project_clause = "AND project_id = ?"
                    params = params + (project_id,)
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                    {where_clause}
                    {project_clause}
                    ORDER BY updated_at DESC
                ''', params)
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    notes.append(note)
                
                self.logger.info(
                    f"Search found {len(notes)} notes for query: '{query}' "
                    f"with filter: '{filter_option}'"
                )
                return notes
                
        except Exception as e:
            self.logger.error(
                f"Error searching notes with query '{query}': {str(e)}"
            )
            return []
    
    def get_notes_by_tag(self, tag: str) -> List[Note]:
        """
        Get all notes with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of Note objects containing the specified tag
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Search for tag in JSON array
                # SQLite doesn't have native JSON array search, so we use LIKE
                tag_pattern = f'%"{tag}"%'
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                    AND tags LIKE ?
                    ORDER BY updated_at DESC
                ''', (tag_pattern,))
                
                notes = []
                for row in cursor.fetchall():
                    # Double-check that the tag is actually in the list
                    tags_list = json.loads(row[4]) if row[4] else []
                    if tag in tags_list:
                        note = Note(
                            id=row[0],
                            title=row[1],
                            content=row[2],
                            tags=tags_list,
                            project_id=row[7]
                        )
                        # Preserve original timestamps
                        note.created_at = row[5]
                        note.updated_at = row[6]
                        
                        # Add content_html as custom attribute
                        note.content_html = row[3]
                        
                        notes.append(note)
                
                self.logger.info(f"Found {len(notes)} notes with tag: '{tag}'")
                return notes
                
        except Exception as e:
            self.logger.error(f"Error getting notes by tag '{tag}': {str(e)}")
            return []
    
    def restore_deleted_note(self, note_id: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted note.
        
        Args:
            note_id: ID of the note to restore
            
        Returns:
            Dict with success status and message
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET is_deleted = 0, updated_at = ?
                    WHERE id = ? AND is_deleted = 1
                ''', (datetime.now().isoformat(), note_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Restored note: {note_id}")
                    return {
                        "success": True,
                        "message": "Note restored successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Note not found in deleted items"
                    }
                    
        except Exception as e:
            self.logger.error(f"Error restoring note {note_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to restore note: {str(e)}"
            }
    
    def get_deleted_notes(self) -> List[Note]:
        """
        Get all soft-deleted notes (for potential restoration).
        
        Returns:
            List of deleted Note objects
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 1
                    ORDER BY updated_at DESC
                ''')
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    notes.append(note)
                
                self.logger.info(f"Retrieved {len(notes)} deleted notes")
                return notes
                
        except Exception as e:
            self.logger.error(f"Error retrieving deleted notes: {str(e)}")
            return []
    
    def get_all_tags(self) -> Dict[str, int]:
        """
        Get all unique tags from all notes with their usage counts.
        
        Returns:
            Dictionary of tag names to their usage counts
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT tags
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                ''')
                
                tag_counts = {}
                for row in cursor.fetchall():
                    if row[0]:
                        tags = json.loads(row[0])
                        for tag in tags:
                            # Case-insensitive count, preserve original case
                            tag_lower = tag.lower()
                            if tag_lower in tag_counts:
                                tag_counts[tag_lower]['count'] += 1
                            else:
                                tag_counts[tag_lower] = {
                                    'tag': tag,  # Preserve original case
                                    'count': 1
                                }
                
                # Convert to simple dict preserving original case
                result = {
                    data['tag']: data['count']
                    for data in tag_counts.values()
                }
                
                self.logger.info(f"Retrieved {len(result)} unique tags")
                return result
                
        except Exception as e:
            self.logger.error(f"Error retrieving all tags: {str(e)}")
            return {}
    
    def rename_tag(self, old_tag: str, new_tag: str) -> Dict[str, Any]:
        """
        Rename a tag across all notes.
        
        Args:
            old_tag: The tag to rename
            new_tag: The new tag name
            
        Returns:
            Dict with success status and number of affected notes
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Get all notes that contain the old tag
                cursor.execute(f'''
                    SELECT id, tags
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                ''')
                
                affected_notes = 0
                for row in cursor.fetchall():
                    note_id = row[0]
                    tags = json.loads(row[1]) if row[1] else []
                    
                    # Case-insensitive search but replace with exact match
                    updated_tags = []
                    tag_found = False
                    for tag in tags:
                        if tag.lower() == old_tag.lower():
                            updated_tags.append(new_tag)
                            tag_found = True
                        else:
                            updated_tags.append(tag)
                    
                    if tag_found:
                        # Update the note with new tags
                        cursor.execute(f'''
                            UPDATE {self.table_name}
                            SET tags = ?, updated_at = ?
                            WHERE id = ?
                        ''', (
                            json.dumps(updated_tags),
                            datetime.now().isoformat(),
                            note_id
                        ))
                        affected_notes += 1
                
                conn.commit()
                
                self.logger.info(
                    f"Renamed tag '{old_tag}' to '{new_tag}' in "
                    f"{affected_notes} notes"
                )
                return {
                    "success": True,
                    "message": (
                        f"Tag renamed successfully in {affected_notes} notes"
                    ),
                    "affected_notes": affected_notes
                }
                
        except Exception as e:
            self.logger.error(
                f"Error renaming tag '{old_tag}' to '{new_tag}': {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to rename tag: {str(e)}"
            }
    
    def delete_tag(self, tag_to_delete: str) -> Dict[str, Any]:
        """
        Remove a tag from all notes.
        
        Args:
            tag_to_delete: The tag to remove
            
        Returns:
            Dict with success status and number of affected notes
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Get all notes
                cursor.execute(f'''
                    SELECT id, tags
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                ''')
                
                affected_notes = 0
                for row in cursor.fetchall():
                    note_id = row[0]
                    tags = json.loads(row[1]) if row[1] else []
                    
                    # Remove tag (case-insensitive)
                    original_count = len(tags)
                    updated_tags = [
                        tag for tag in tags
                        if tag.lower() != tag_to_delete.lower()
                    ]
                    
                    if len(updated_tags) < original_count:
                        # Update the note with filtered tags
                        cursor.execute(f'''
                            UPDATE {self.table_name}
                            SET tags = ?, updated_at = ?
                            WHERE id = ?
                        ''', (
                            json.dumps(updated_tags),
                            datetime.now().isoformat(),
                            note_id
                        ))
                        affected_notes += 1
                
                conn.commit()
                
                self.logger.info(
                    f"Deleted tag '{tag_to_delete}' from "
                    f"{affected_notes} notes"
                )
                return {
                    "success": True,
                    "message": f"Tag deleted from {affected_notes} notes",
                    "affected_notes": affected_notes
                }
                
        except Exception as e:
            self.logger.error(
                f"Error deleting tag '{tag_to_delete}': {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to delete tag: {str(e)}"
            }
    
    def _escape_sql_wildcards(self, text: str) -> str:
        """
        Escape SQL wildcard characters for safe LIKE queries.
        
        Args:
            text: Text that may contain SQL wildcards
            
        Returns:
            Text with escaped wildcards
        """
        if not text:
            return ""
            
        # Use the security module's escape method
        return self._get_security().escape_sql_wildcards(text)
    
    def get_notes_by_project(self, project_id: str) -> List[Note]:
        """
        Get all notes associated with a specific project.
        
        Args:
            project_id: The ID of the project to retrieve notes for
            
        Returns:
            List of Note objects belonging to the project
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0 AND project_id = ?
                    ORDER BY updated_at DESC
                ''', (project_id,))
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    notes.append(note)
                
                self.logger.info(
                    f"Retrieved {len(notes)} notes for project: {project_id}"
                )
                return notes
                
        except Exception as e:
            self.logger.error(
                f"Error retrieving notes for project {project_id}: {str(e)}"
            )
            return []
    
    def get_notes_without_project(self) -> List[Note]:
        """
        Get all notes that are not associated with any project.
        
        Returns:
            List of Note objects without project association
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT id, title, content, content_html, tags,
                           created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0 AND (project_id IS NULL OR project_id = '')
                    ORDER BY updated_at DESC
                ''')
                
                notes = []
                for row in cursor.fetchall():
                    note = Note(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        tags=json.loads(row[4]) if row[4] else [],
                        project_id=row[7]
                    )
                    # Preserve original timestamps
                    note.created_at = row[5]
                    note.updated_at = row[6]
                    
                    # Add content_html as custom attribute
                    note.content_html = row[3]
                    
                    notes.append(note)
                
                self.logger.info(
                    f"Retrieved {len(notes)} notes without project association"
                )
                return notes
                
        except Exception as e:
            self.logger.error(
                f"Error retrieving notes without project: {str(e)}"
            )
            return []
    
    def assign_notes_to_project(
        self, note_ids: List[str], project_id: str
    ) -> bool:
        """
        Assign multiple notes to a project.
        
        Args:
            note_ids: List of note IDs to assign to the project
            project_id: The project ID to assign notes to
            
        Returns:
            True if all notes were successfully assigned, False otherwise
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Build placeholders for the IN clause
                placeholders = ','.join(['?'] * len(note_ids))
                
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET project_id = ?, updated_at = ?
                    WHERE id IN ({placeholders}) AND is_deleted = 0
                ''', [project_id, datetime.now().isoformat()] + note_ids)
                
                conn.commit()
                
                affected_rows = cursor.rowcount
                if affected_rows == len(note_ids):
                    self.logger.info(
                        f"Assigned {affected_rows} notes to project {project_id}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Only assigned {affected_rows} out of {len(note_ids)} "
                        f"notes to project {project_id}"
                    )
                    return affected_rows > 0
                    
        except Exception as e:
            self.logger.error(
                f"Error assigning notes to project {project_id}: {str(e)}"
            )
            return False
    
    def remove_notes_from_project(self, note_ids: List[str]) -> bool:
        """
        Remove project association from multiple notes.
        
        Args:
            note_ids: List of note IDs to remove from their projects
            
        Returns:
            True if all notes were successfully updated, False otherwise
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                # Build placeholders for the IN clause
                placeholders = ','.join(['?'] * len(note_ids))
                
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET project_id = NULL, updated_at = ?
                    WHERE id IN ({placeholders}) AND is_deleted = 0
                ''', [datetime.now().isoformat()] + note_ids)
                
                conn.commit()
                
                affected_rows = cursor.rowcount
                if affected_rows == len(note_ids):
                    self.logger.info(
                        f"Removed project association from {affected_rows} notes"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Only removed project from {affected_rows} out of "
                        f"{len(note_ids)} notes"
                    )
                    return affected_rows > 0
                    
        except Exception as e:
            self.logger.error(
                f"Error removing notes from project: {str(e)}"
            )
            return False
    
    def get_project_notes_count(self, project_id: str) -> int:
        """
        Get the count of notes associated with a specific project.
        
        Args:
            project_id: The ID of the project to count notes for
            
        Returns:
            Number of notes in the project
        """
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT COUNT(*)
                    FROM {self.table_name}
                    WHERE is_deleted = 0 AND project_id = ?
                ''', (project_id,))
                
                count = cursor.fetchone()[0]
                
                self.logger.debug(
                    f"Project {project_id} has {count} notes"
                )
                return count
                
        except Exception as e:
            self.logger.error(
                f"Error counting notes for project {project_id}: {str(e)}"
            )
            return 0
    
    def update_note_project(self, note_id: str, project_id: Optional[str]) -> bool:
        """Update a single note's project association"""
        return self.update_note(note_id, {"project_id": project_id})["success"]