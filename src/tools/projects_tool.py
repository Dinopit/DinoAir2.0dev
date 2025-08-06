"""
Projects Tool Functions for DinoAir 2.0 AI Integration

This module provides AI-accessible functions for project management,
enabling AI models to programmatically interact with project creation,
organization, and tracking operations.

All functions follow the standard tool pattern with comprehensive
documentation and error handling for proper AI discovery and usage.
"""

import logging
from typing import Dict, Any, Optional, List

from ..database.projects_db import ProjectsDatabase
from ..models.project import Project
from ..database.initialize_db import DatabaseManager


logger = logging.getLogger(__name__)


def create_project(name: str, description: str = "",
                   status: str = "active", color: Optional[str] = None,
                   icon: Optional[str] = None,
                   parent_project_id: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   user_name: str = "default_user") -> Dict[str, Any]:
    """
    Create a new project with the specified details.
    
    Creates a new project in the projects database with proper validation
    and hierarchical support for AI-driven project management workflows.
    
    Args:
        name (str): The name of the project (required)
        description (str): Description of the project (default: "")
        status (str): Project status - "active", "completed", "archived"
        color (Optional[str]): Color for project visualization
        icon (Optional[str]): Icon identifier for the project
        parent_project_id (Optional[str]): ID of parent project for hierarchy
        tags (Optional[List[str]]): List of tags for the project
        metadata (Optional[Dict]): Additional project metadata
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - project_id (str): ID of the created project (if successful)
            - message (str): Success or error message
            - project_data (Dict): Created project information
            
    Example:
        >>> create_project("Website Redesign", "Redesign company website")
        {
            'success': True,
            'project_id': 'project_abc123',
            'message': 'Project created successfully',
            'project_data': {...}
        }
    """
    try:
        if not name or not name.strip():
            return {
                "success": False,
                "error": "Project name is required",
                "message": "Failed to create project: name is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Create project object
        project = Project(
            name=name.strip(),
            description=description,
            status=status,
            color=color,
            icon=icon,
            parent_project_id=parent_project_id,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Create in database
        result = projects_db.create_project(project)
        
        if result['success']:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "color": project.color,
                "icon": project.icon,
                "parent_project_id": project.parent_project_id,
                "tags": project.tags,
                "metadata": project.metadata,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
            
            return {
                "success": True,
                "project_id": result['id'],
                "message": "Project created successfully",
                "project_data": project_data
            }
        else:
            return {
                "success": False,
                "error": result['error'],
                "message": f"Failed to create project: {result['error']}"
            }
            
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create project: {str(e)}"
        }


def get_project(project_id: str,
                user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve a specific project by its ID.
    
    Fetches a project from the database with all its metadata
    for AI-driven project retrieval and analysis workflows.
    
    Args:
        project_id (str): Unique identifier of the project to retrieve
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - project (Dict): Project data including all metadata
            - message (str): Success or error message
            
    Example:
        >>> get_project("project_abc123")
        {
            'success': True,
            'project': {'id': 'project_abc123', 'name': 'Website Redesign'},
            'message': 'Project retrieved successfully'
        }
    """
    try:
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required",
                "message": "Failed to get project: project_id is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Get project
        project = projects_db.get_project(project_id)
        
        if project:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "color": project.color,
                "icon": project.icon,
                "parent_project_id": project.parent_project_id,
                "tags": project.tags,
                "metadata": project.metadata,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "completed_at": project.completed_at,
                "archived_at": project.archived_at
            }
            
            return {
                "success": True,
                "project": project_data,
                "message": f"Successfully retrieved project: {project.name}"
            }
        else:
            return {
                "success": False,
                "error": f"Project not found: {project_id}",
                "message": f"Project with ID '{project_id}' not found"
            }
            
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get project: {str(e)}"
        }


def update_project(project_id: str, name: Optional[str] = None,
                   description: Optional[str] = None,
                   status: Optional[str] = None,
                   color: Optional[str] = None,
                   icon: Optional[str] = None,
                   parent_project_id: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   user_name: str = "default_user") -> Dict[str, Any]:
    """
    Update an existing project with new information.
    
    Modifies project fields as specified while preserving unchanged fields
    for AI-driven project editing and maintenance workflows.
    
    Args:
        project_id (str): Unique identifier of the project to update
        name (Optional[str]): New name for the project
        description (Optional[str]): New description for the project
        status (Optional[str]): New status for the project
        color (Optional[str]): New color for the project
        icon (Optional[str]): New icon for the project
        parent_project_id (Optional[str]): New parent project ID
        tags (Optional[List[str]]): New tags for the project
        metadata (Optional[Dict]): New metadata for the project
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message
            - updated_fields (List[str]): List of fields that were updated
            
    Example:
        >>> update_project("project_abc123", status="completed")
        {
            'success': True,
            'message': 'Project updated successfully',
            'updated_fields': ['status']
        }
    """
    try:
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required",
                "message": "Failed to update project: project_id is required"
            }
        
        # Build updates dictionary
        updates = {}
        updated_fields = []
        
        if name is not None:
            updates['name'] = name.strip()
            updated_fields.append('name')
        if description is not None:
            updates['description'] = description
            updated_fields.append('description')
        if status is not None:
            updates['status'] = status
            updated_fields.append('status')
        if color is not None:
            updates['color'] = color
            updated_fields.append('color')
        if icon is not None:
            updates['icon'] = icon
            updated_fields.append('icon')
        if parent_project_id is not None:
            updates['parent_project_id'] = parent_project_id
            updated_fields.append('parent_project_id')
        if tags is not None:
            updates['tags'] = tags
            updated_fields.append('tags')
        if metadata is not None:
            updates['metadata'] = metadata
            updated_fields.append('metadata')
        
        if not updates:
            return {
                "success": False,
                "error": "At least one field must be provided for update",
                "message": "No fields specified for update"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Update project
        success = projects_db.update_project(project_id, updates)
        
        if success:
            return {
                "success": True,
                "message": "Project updated successfully",
                "updated_fields": updated_fields
            }
        else:
            return {
                "success": False,
                "error": "Update operation failed",
                "message": "Failed to update project"
            }
            
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update project: {str(e)}"
        }


def delete_project(project_id: str, cascade: bool = False,
                   user_name: str = "default_user") -> Dict[str, Any]:
    """
    Delete a project from the database.
    
    Removes a project with optional cascade deletion of child projects
    for AI-driven project cleanup and management workflows.
    
    Args:
        project_id (str): Unique identifier of the project to delete
        cascade (bool): Whether to delete child projects too (default: False)
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message
            - cascade (bool): Whether cascade deletion was used
            
    Example:
        >>> delete_project("project_abc123", cascade=True)
        {
            'success': True,
            'message': 'Project and children deleted successfully',
            'cascade': True
        }
    """
    try:
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required",
                "message": "Failed to delete project: project_id is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Delete project
        success = projects_db.delete_project(project_id, cascade=cascade)
        
        if success:
            message = ("Project deleted successfully" if not cascade
                       else "Project and children deleted successfully")
            return {
                "success": True,
                "message": message,
                "cascade": cascade
            }
        else:
            return {
                "success": False,
                "error": "Delete operation failed",
                "message": "Failed to delete project"
            }
            
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete project: {str(e)}"
        }


def list_all_projects(user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve all projects for the specified user.
    
    Gets a complete list of all projects with basic metadata
    for AI-driven project overview and management workflows.
    
    Args:
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - projects (List[Dict]): List of all projects with metadata
            - count (int): Total number of projects
            - message (str): Success or error message
            
    Example:
        >>> list_all_projects()
        {
            'success': True,
            'projects': [{'id': 'proj_1', 'name': 'Project 1', ...}],
            'count': 5,
            'message': 'Retrieved 5 projects'
        }
    """
    try:
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Get all projects
        projects = projects_db.get_all_projects()
        
        # Format results
        projects_data = []
        for project in projects:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "color": project.color,
                "icon": project.icon,
                "parent_project_id": project.parent_project_id,
                "tags": project.tags,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
            projects_data.append(project_data)
        
        return {
            "success": True,
            "projects": projects_data,
            "count": len(projects_data),
            "message": f"Retrieved {len(projects_data)} projects"
        }
        
    except Exception as e:
        logger.error(f"Error listing all projects: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list projects: {str(e)}"
        }


def search_projects(query: str,
                    user_name: str = "default_user") -> Dict[str, Any]:
    """
    Search for projects matching the specified query.
    
    Performs text-based search across project names, descriptions, and tags
    for AI-driven project discovery and organization.
    
    Args:
        query (str): Search term to find in projects
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - projects (List[Dict]): List of matching projects
            - count (int): Number of projects found
            - query (str): The search query used
            - message (str): Success or error message
            
    Example:
        >>> search_projects("website")
        {
            'success': True,
            'projects': [{'id': 'proj_1', 'name': 'Website Redesign'}],
            'count': 1,
            'query': 'website',
            'message': 'Found 1 projects matching \"website\"'
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
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Search projects
        projects = projects_db.search_projects(query)
        
        # Format results
        projects_data = []
        for project in projects:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "color": project.color,
                "icon": project.icon,
                "parent_project_id": project.parent_project_id,
                "tags": project.tags,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
            projects_data.append(project_data)
        
        return {
            "success": True,
            "projects": projects_data,
            "count": len(projects_data),
            "query": query,
            "message": (f"Found {len(projects_data)} projects "
                       f"matching '{query}'")
        }
        
    except Exception as e:
        logger.error(f"Error searching projects with query '{query}': {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search projects: {str(e)}"
        }


def get_projects_by_status(status: str,
                           user_name: str = "default_user") -> Dict[str, Any]:
    """
    Retrieve all projects with the specified status.
    
    Finds projects filtered by their current status for AI-driven
    status-based project organization and tracking.
    
    Args:
        status (str): Status to filter by ("active", "completed", "archived")
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - projects (List[Dict]): List of projects with specified status
            - count (int): Number of projects found
            - status (str): The status that was filtered by
            - message (str): Success or error message
            
    Example:
        >>> get_projects_by_status("active")
        {
            'success': True,
            'projects': [{'id': 'proj_1', 'name': 'Active Project'}],
            'count': 3,
            'status': 'active',
            'message': 'Found 3 active projects'
        }
    """
    try:
        if not status:
            return {
                "success": False,
                "error": "status is required",
                "message": "Failed to get projects: status is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Get projects by status
        projects = projects_db.get_projects_by_status(status)
        
        # Format results
        projects_data = []
        for project in projects:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "color": project.color,
                "icon": project.icon,
                "parent_project_id": project.parent_project_id,
                "tags": project.tags,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
            projects_data.append(project_data)
        
        return {
            "success": True,
            "projects": projects_data,
            "count": len(projects_data),
            "status": status,
            "message": f"Found {len(projects_data)} {status} projects"
        }
        
    except Exception as e:
        logger.error(f"Error getting projects by status '{status}': {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get projects by status: {str(e)}"
        }


def get_project_statistics(project_id: str,
                           user_name: str = "default_user") -> Dict[str, Any]:
    """
    Get comprehensive statistics for a specific project.
    
    Provides detailed analytics including notes count, artifacts count,
    calendar events, and activity metrics for AI-driven project analysis.
    
    Args:
        project_id (str): Unique identifier of the project
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - statistics (Dict): Comprehensive project statistics
            - message (str): Success or error message
            
    Example:
        >>> get_project_statistics("project_abc123")
        {
            'success': True,
            'statistics': {'total_notes': 15, 'total_artifacts': 8, ...},
            'message': 'Statistics retrieved for project'
        }
    """
    try:
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required",
                "message": "Failed to get statistics: project_id is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Get project statistics
        stats = projects_db.get_project_statistics(project_id)
        
        # Convert to dictionary format
        stats_data = {
            "project_id": stats.project_id,
            "project_name": stats.project_name,
            "total_notes": stats.total_notes,
            "total_artifacts": stats.total_artifacts,
            "total_calendar_events": stats.total_calendar_events,
            "child_project_count": stats.child_project_count,
            "completed_items": stats.completed_items,
            "total_items": stats.total_items,
            "completion_percentage": stats.completion_percentage,
            "days_since_last_activity": stats.days_since_last_activity,
            "last_activity_date": (stats.last_activity_date.isoformat()
                                   if stats.last_activity_date else None)
        }
        
        return {
            "success": True,
            "statistics": stats_data,
            "message": (f"Statistics retrieved for project "
                       f"'{stats.project_name}'")
        }
        
    except Exception as e:
        logger.error(f"Error getting project statistics for {project_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get project statistics: {str(e)}"
        }


def get_project_tree(project_id: str,
                     user_name: str = "default_user") -> Dict[str, Any]:
    """
    Get the hierarchical tree structure starting from a project.
    
    Retrieves the complete project hierarchy including all child projects
    for AI-driven project organization and visualization.
    
    Args:
        project_id (str): Root project ID to build tree from
        user_name (str): Username for database operations
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - tree (Dict): Hierarchical project tree structure
            - message (str): Success or error message
            
    Example:
        >>> get_project_tree("project_abc123")
        {
            'success': True,
            'tree': {'id': 'proj_1', 'name': 'Parent', 'children': [...]},
            'message': 'Project tree retrieved successfully'
        }
    """
    try:
        if not project_id:
            return {
                "success": False,
                "error": "project_id is required",
                "message": "Failed to get tree: project_id is required"
            }
        
        # Initialize database
        db_manager = DatabaseManager(user_name)
        projects_db = ProjectsDatabase(db_manager)
        
        # Get project tree
        tree = projects_db.get_project_tree(project_id)
        
        if tree:
            return {
                "success": True,
                "tree": tree,
                "message": "Project tree retrieved successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Project not found: {project_id}",
                "message": "Cannot build tree for non-existent project"
            }
        
    except Exception as e:
        logger.error(f"Error getting project tree for {project_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get project tree: {str(e)}"
        }


# Tool registry for discovery
PROJECTS_TOOLS = {
    "create_project": create_project,
    "get_project": get_project,
    "update_project": update_project,
    "delete_project": delete_project,
    "list_all_projects": list_all_projects,
    "search_projects": search_projects,
    "get_projects_by_status": get_projects_by_status,
    "get_project_statistics": get_project_statistics,
    "get_project_tree": get_project_tree,
}