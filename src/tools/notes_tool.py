"""
Notes Tool Functions for DinoAir 2.0 AI Integration

This module provides AI-accessible functions for notes management,
enabling AI models to programmatically interact with the notes system
through standardized CRUD operations and search capabilities.

All functions follow the standard tool pattern with comprehensive
documentation and error handling for proper AI discovery and usage.
"""

import logging
from typing import Dict, Any, Optional, List

from ..database.notes_db import NotesDatabase
from ..models.note import Note


logger = logging.getLogger(__name__)


def create_note(title: str, content: str, tags: Optional[List[str]] = None,
                project_id: Optional[str] = None,
                content_html: Optional[str] = None,
                user_name: str = "default_user") -> Dict[str, Any]:
    """
    Create a new note with the specified content and metadata.
    
    This function creates a new note in the notes database with proper
    validation and error handling for AI-driven note creation workflows.
    
    Args:
        title (str): The title of the note (required)
        content (str): The main content/body of the note (required)
        tags (Optional[List[str]]): List of tags to associate with the note
        project_id (Optional[str]): Project ID to associate the note with
        content_html (Optional[str]): Rich HTML content for the note
        user_name (str): Username for database operations
                         (default: "default_user")
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - note_id (str): ID of the created note (if successful)
            - message (str): Success or error message
            - note_data (Dict): Created note information (if successful)
            - error (str): Error details (if failed)
            
    Example:
        >>> create_note("Meeting Notes", "Discussed project timeline", 
        ...             tags=["meeting", "project"])
        {
            'success': True,
            'note_id': 'note_12345',
            'message': 'Note created successfully',
            'note_data': {...}
        }
    """
    try:
        if not title or not content:
            return {
                "success": False,
                "error": "Both title and content are required",
                "message": "Failed to create note: missing required fields"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Create note object
        note = Note(
            title=title,
            content=content,
            tags=tags or [],
            project_id=project_id
        )
        
        # Create in database
        result = notes_db.create_note(note, content_html=content_html)
        
        if result['success']:
            return {
                "success": True,
                "note_id": result['note_id'],
                "message": result['message'],
                "note_data": {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "tags": note.tags,
                    "project_id": note.project_id,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at
                }
            }
        else:
            return {
                "success": False,
                "error": result['error'],
                "message": f"Failed to create note: {result['error']}"
            }
            
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create note: {str(e)}"
        }


def read_note(note_id: str, user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve a specific note by its ID.
    
    Fetches a note from the database with all its metadata and content
    for AI-driven note retrieval and analysis workflows.
    
    Args:
        note_id (str): Unique identifier of the note to retrieve
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - note (Dict): Note data including content and metadata
            - message (str): Success or error message
            - error (str): Error details (if failed)
            
    Example:
        >>> read_note("note_12345")
        {
            'success': True,
            'note': {'id': 'note_12345', 'title': 'Meeting Notes', ...},
            'message': 'Note retrieved successfully'
        }
    """
    try:
        if not note_id:
            return {
                "success": False,
                "error": "note_id is required",
                "message": "Failed to read note: note_id is required"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Get note
        note = notes_db.get_note(note_id)
        
        if note:
            note_data = {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "project_id": note.project_id,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            
            # Note: HTML content handling would go here if needed
            
            return {
                "success": True,
                "note": note_data,
                "message": f"Successfully retrieved note: {note.title}"
            }
        else:
            return {
                "success": False,
                "error": f"Note not found: {note_id}",
                "message": f"Note with ID '{note_id}' not found"
            }
            
    except Exception as e:
        logger.error(f"Error reading note {note_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to read note: {str(e)}"
        }


def update_note(note_id: str, title: Optional[str] = None,
                content: Optional[str] = None,
                tags: Optional[List[str]] = None,
                project_id: Optional[str] = None,
                content_html: Optional[str] = None,
                user_name: str = "default_user") -> Dict[str, Any]:
    """
    Update an existing note with new content or metadata.
    
    Modifies note fields as specified while preserving unchanged fields
    for AI-driven note editing and maintenance workflows.
    
    Args:
        note_id (str): Unique identifier of the note to update
        title (Optional[str]): New title for the note
        content (Optional[str]): New content for the note
        tags (Optional[List[str]]): New tags for the note
        project_id (Optional[str]): New project association
        content_html (Optional[str]): New HTML content
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message
            - updated_fields (List[str]): List of fields that were updated
            - error (str): Error details (if failed)
            
    Example:
        >>> update_note("note_12345", content="Updated meeting notes")
        {
            'success': True,
            'message': 'Note updated successfully',
            'updated_fields': ['content']
        }
    """
    try:
        if not note_id:
            return {
                "success": False,
                "error": "note_id is required",
                "message": "Failed to update note: note_id is required"
            }
        
        # Build updates dictionary
        updates = {}
        if title is not None:
            updates['title'] = title
        if content is not None:
            updates['content'] = content
        if tags is not None:
            updates['tags'] = tags
        if project_id is not None:
            updates['project_id'] = project_id
        if content_html is not None:
            updates['content_html'] = content_html
        
        if not updates:
            return {
                "success": False,
                "error": "At least one field must be provided for update",
                "message": "No fields specified for update"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Update note
        result = notes_db.update_note(note_id, updates)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "updated_fields": result.get('updated_fields', [])
            }
        else:
            return {
                "success": False,
                "error": result['error'],
                "message": f"Failed to update note: {result['error']}"
            }
            
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update note: {str(e)}"
        }


def delete_note(note_id: str, hard_delete: bool = False,
                user_name: str = "default_user") -> Dict[str, Any]:
    """
    Delete a note from the database.
    
    Removes a note either through soft delete (default) or permanent
    deletion for AI-driven note cleanup and management workflows.
    
    Args:
        note_id (str): Unique identifier of the note to delete
        hard_delete (bool): Whether to permanently delete (default: False)
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message
            - hard_delete (bool): Whether permanent deletion was used
            - error (str): Error details (if failed)
            
    Example:
        >>> delete_note("note_12345")
        {
            'success': True,
            'message': 'Note deleted successfully',
            'hard_delete': False
        }
    """
    try:
        if not note_id:
            return {
                "success": False,
                "error": "note_id is required",
                "message": "Failed to delete note: note_id is required"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Delete note
        result = notes_db.delete_note(note_id, hard_delete=hard_delete)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "hard_delete": hard_delete
            }
        else:
            return {
                "success": False,
                "error": result['error'],
                "message": f"Failed to delete note: {result['error']}"
            }
            
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete note: {str(e)}"
        }


def search_notes(query: str, filter_option: str = "All",
                 project_id: Optional[str] = None,
                 user_name: str = "default_user") -> Dict[str, Any]:
    """
    Search for notes matching the specified query and filters.
    
    Performs text-based search across note titles, content, and tags
    with optional project filtering for AI-driven note discovery.
    
    Args:
        query (str): Search term to find in notes
        filter_option (str): Search scope - "All", "Title Only", 
                           "Content Only", or "Tags Only"
        project_id (Optional[str]): Limit search to specific project
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - notes (List[Dict]): List of matching notes with metadata
            - count (int): Number of notes found
            - query (str): The search query used
            - filter (str): The filter option used
            - message (str): Success or error message
            
    Example:
        >>> search_notes("meeting", "All")
        {
            'success': True,
            'notes': [{'id': 'note_123', 'title': 'Meeting Notes', ...}],
            'count': 1,
            'query': 'meeting',
            'message': 'Found 1 notes matching \"meeting\"'
        }
    """
    try:
        if not query:
            return {
                "success": False,
                "error": "query is required",
                "message": "Failed to search: query is required"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Search notes
        notes = notes_db.search_notes(query, filter_option, project_id)
        
        # Format results
        notes_data = []
        for note in notes:
            content_preview = (note.content[:200] + "..."
                               if len(note.content) > 200
                               else note.content)
            
            note_data = {
                "id": note.id,
                "title": note.title,
                "content": content_preview,
                "tags": note.tags,
                "project_id": note.project_id,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            notes_data.append(note_data)
        
        return {
            "success": True,
            "notes": notes_data,
            "count": len(notes_data),
            "query": query,
            "filter": filter_option,
            "message": f"Found {len(notes_data)} notes matching '{query}'"
        }
        
    except Exception as e:
        logger.error(f"Error searching notes with query '{query}': {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search notes: {str(e)}"
        }


def list_all_notes(user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve all notes for the specified user.
    
    Gets a complete list of all notes with basic metadata
    for AI-driven note overview and management workflows.
    
    Args:
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - notes (List[Dict]): List of all notes with metadata
            - count (int): Total number of notes
            - message (str): Success or error message
            
    Example:
        >>> list_all_notes()
        {
            'success': True,
            'notes': [{'id': 'note_123', 'title': 'Note 1', ...}],
            'count': 5,
            'message': 'Retrieved 5 notes'
        }
    """
    try:
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Get all notes
        notes = notes_db.get_all_notes()
        
        # Format results
        notes_data = []
        for note in notes:
            content_preview = (note.content[:100] + "..."
                               if len(note.content) > 100
                               else note.content)
            
            note_data = {
                "id": note.id,
                "title": note.title,
                "content": content_preview,
                "tags": note.tags,
                "project_id": note.project_id,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            notes_data.append(note_data)
        
        return {
            "success": True,
            "notes": notes_data,
            "count": len(notes_data),
            "message": f"Retrieved {len(notes_data)} notes"
        }
        
    except Exception as e:
        logger.error(f"Error listing all notes: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list notes: {str(e)}"
        }


def get_notes_by_tag(tag_name: str,
                     user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve all notes that contain the specified tag.
    
    Finds notes tagged with the given tag for AI-driven
    tag-based note organization and retrieval workflows.
    
    Args:
        tag_name (str): Tag to search for in notes
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - notes (List[Dict]): List of notes with the specified tag
            - count (int): Number of notes found
            - tag (str): The tag that was searched for
            - message (str): Success or error message
            
    Example:
        >>> get_notes_by_tag("work")
        {
            'success': True,
            'notes': [{'id': 'note_123', 'title': 'Work Note', ...}],
            'count': 3,
            'tag': 'work',
            'message': 'Found 3 notes with tag \"work\"'
        }
    """
    try:
        if not tag_name:
            return {
                "success": False,
                "error": "tag_name is required",
                "message": "Failed to get notes: tag_name is required"
            }
        
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Get notes by tag
        notes = notes_db.get_notes_by_tag(tag_name)
        
        # Format results
        notes_data = []
        for note in notes:
            content_preview = (note.content[:100] + "..." 
                             if len(note.content) > 100 
                             else note.content)
            
            note_data = {
                "id": note.id,
                "title": note.title,
                "content": content_preview,
                "tags": note.tags,
                "project_id": note.project_id,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            notes_data.append(note_data)
        
        return {
            "success": True,
            "notes": notes_data,
            "count": len(notes_data),
            "tag": tag_name,
            "message": f"Found {len(notes_data)} notes with tag '{tag_name}'"
        }
        
    except Exception as e:
        logger.error(f"Error getting notes by tag '{tag_name}': {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get notes by tag: {str(e)}"
        }


def get_all_tags(user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve all unique tags from all notes with usage counts.
    
    Gets a comprehensive list of all tags used in the notes system
    for AI-driven tag management and organization workflows.
    
    Args:
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - tags (Dict[str, int]): Dictionary mapping tag names to usage
                                     counts
            - count (int): Number of unique tags
            - message (str): Success or error message
            
    Example:
        >>> get_all_tags()
        {
            'success': True,
            'tags': {'work': 5, 'meeting': 3, 'personal': 2},
            'count': 3,
            'message': 'Retrieved 3 unique tags'
        }
    """
    try:
        # Initialize database
        notes_db = NotesDatabase(user_name)
        
        # Get all tags
        tags = notes_db.get_all_tags()
        
        return {
            "success": True,
            "tags": tags,
            "count": len(tags),
            "message": f"Retrieved {len(tags)} unique tags"
        }
        
    except Exception as e:
        logger.error(f"Error getting all tags: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get tags: {str(e)}"
        }


# Tool registry for discovery
NOTES_TOOLS = {
    "create_note": create_note,
    "read_note": read_note,
    "update_note": update_note,
    "delete_note": delete_note,
    "search_notes": search_notes,
    "list_all_notes": list_all_notes,
    "get_notes_by_tag": get_notes_by_tag,
    "get_all_tags": get_all_tags,
}