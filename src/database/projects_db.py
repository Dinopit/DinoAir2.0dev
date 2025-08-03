#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Projects Database Manager
Manages all project database operations with resilient handling,
hierarchical organization, and cross-tool integration.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..models.project import (
    Project, ProjectStatistics, ProjectSummary, ProjectStatus
)
from ..utils.logger import Logger


class ProjectsDatabase:
    """Manages projects database operations with hierarchical support"""
    
    def __init__(self, db_manager):
        """Initialize with database manager reference"""
        self.db_manager = db_manager
        self.logger = Logger()
        
    def _get_connection(self):
        """Get database connection"""
        return self.db_manager.get_projects_connection()
    
    def create_project(self, project: Project) -> Dict[str, Any]:
        """Create a new project"""
        try:
            # Validate hierarchy if parent specified
            if project.parent_project_id:
                if not self._validate_project_hierarchy(
                        project.id, project.parent_project_id):
                    return {
                        "success": False,
                        "error": "Invalid parent project or circular reference"
                    }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                project_dict = project.to_dict()
                
                cursor.execute('''
                    INSERT INTO projects 
                    (id, name, description, status, color, icon,
                     parent_project_id, tags, metadata,
                     created_at, updated_at, completed_at, archived_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_dict['id'],
                    project_dict['name'],
                    project_dict['description'],
                    project_dict['status'],
                    project_dict['color'],
                    project_dict['icon'],
                    project_dict['parent_project_id'],
                    project_dict['tags'],
                    project_dict['metadata'],
                    project_dict['created_at'],
                    project_dict['updated_at'],
                    project_dict['completed_at'],
                    project_dict['archived_at']
                ))
                
                conn.commit()
                
                self.logger.info(f"Created project: {project.id}")
                return {"success": True, "id": project.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_project(self, project_id: str, 
                       updates: Dict[str, Any]) -> bool:
        """Update an existing project"""
        try:
            # Validate hierarchy if parent being updated
            if 'parent_project_id' in updates:
                parent_id = updates['parent_project_id']
                if parent_id and not self._validate_project_hierarchy(
                        project_id, parent_id):
                    self.logger.error(
                        f"Invalid parent project {parent_id} for {project_id}")
                    return False
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                # Allowed fields for update
                allowed_fields = [
                    'name', 'description', 'status', 'color', 'icon',
                    'parent_project_id', 'tags', 'metadata',
                    'completed_at', 'archived_at'
                ]
                
                for key, value in updates.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = ?")
                        # Handle special formatting for certain fields
                        if key == 'tags' and isinstance(value, list):
                            value = ','.join(value)
                        elif key == 'metadata' and isinstance(value, dict):
                            value = json.dumps(value)
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                # Handle status changes with appropriate timestamps
                if 'status' in updates:
                    status = updates['status']
                    if status == ProjectStatus.COMPLETED.value:
                        set_clauses.append("completed_at = ?")
                        params.append(datetime.now().isoformat())
                    elif status == ProjectStatus.ARCHIVED.value:
                        set_clauses.append("archived_at = ?")
                        params.append(datetime.now().isoformat())
                    elif status == ProjectStatus.ACTIVE.value:
                        set_clauses.extend([
                            "completed_at = ?",
                            "archived_at = ?"
                        ])
                        params.extend([None, None])
                
                # Always update the timestamp
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(project_id)
                
                query = f"""UPDATE projects 
                           SET {', '.join(set_clauses)} 
                           WHERE id = ?"""
                cursor.execute(query, params)
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to update project: {str(e)}")
            return False
    
    def delete_project(self, project_id: str, cascade: bool = False) -> bool:
        """Delete a project and optionally cascade to child projects"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                descendants = []
                if cascade:
                    # Get all descendant projects recursively
                    descendants = self._get_all_descendants(project_id)
                    
                    # Delete in reverse order (deepest first)
                    for desc_id in reversed(descendants):
                        cursor.execute(
                            'DELETE FROM projects WHERE id = ?', (desc_id,))
                
                # Delete the project itself
                cursor.execute('DELETE FROM projects WHERE id = ?', 
                               (project_id,))
                
                conn.commit()
                
                deleted_count = cursor.rowcount
                if cascade and descendants:
                    deleted_count += len(descendants)
                
                msg = f"Deleted project {project_id}"
                if cascade and descendants:
                    msg += f" and {len(descendants)} descendants"
                self.logger.info(msg)
                
                return deleted_count > 0
                
        except Exception as e:
            self.logger.error(f"Failed to delete project: {str(e)}")
            return False
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects WHERE id = ?
                ''', (project_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_project(row)
                
        except Exception as e:
            self.logger.error(f"Failed to get project: {str(e)}")
            return None
    
    def get_all_projects(self) -> List[Project]:
        """Get all projects"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects 
                    ORDER BY name, created_at DESC
                ''')
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to get all projects: {str(e)}")
            return []
    
    def get_child_projects(self, parent_id: str) -> List[Project]:
        """Get all direct child projects of a parent"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects 
                    WHERE parent_project_id = ?
                    ORDER BY name
                ''', (parent_id,))
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to get child projects: {str(e)}")
            return []
    
    def get_root_projects(self) -> List[Project]:
        """Get all root projects (projects with no parent)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects 
                    WHERE parent_project_id IS NULL
                    ORDER BY name
                ''')
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to get root projects: {str(e)}")
            return []
    
    def get_project_tree(self, project_id: str) -> Dict[str, Any]:
        """Get project tree structure starting from a project"""
        try:
            project = self.get_project(project_id)
            if not project:
                return {}
            
            tree = {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'color': project.color,
                'icon': project.icon,
                'children': []
            }
            
            # Recursively get children
            children = self.get_child_projects(project_id)
            for child in children:
                child_tree = self.get_project_tree(child.id)
                tree['children'].append(child_tree)
            
            return tree
            
        except Exception as e:
            self.logger.error(f"Failed to get project tree: {str(e)}")
            return {}
    
    def get_project_statistics(self, project_id: str) -> ProjectStatistics:
        """Get comprehensive statistics for a project"""
        project = None
        try:
            project = self.get_project(project_id)
            if not project:
                return ProjectStatistics(
                    project_id=project_id,
                    project_name="Unknown"
                )
            
            stats = ProjectStatistics(
                project_id=project_id,
                project_name=project.name
            )
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get notes count
                stats.total_notes = self.get_project_notes_count(project_id)
                
                # Get artifacts count
                stats.total_artifacts = self.get_project_artifacts_count(
                    project_id)
                
                # Get calendar events count
                stats.total_calendar_events = self.get_project_events_count(
                    project_id)
                
                # Get child projects count
                cursor.execute('''
                    SELECT COUNT(*) FROM projects 
                    WHERE parent_project_id = ?
                ''', (project_id,))
                stats.child_project_count = cursor.fetchone()[0]
                
                # Get last activity date
                # Check for most recent update across all related tables
                activity_queries = [
                    ("SELECT MAX(updated_at) FROM notes "
                     "WHERE project_id = ?", project_id),
                    ("SELECT MAX(updated_at) FROM artifacts "
                     "WHERE project_id = ?", project_id),
                    ("SELECT MAX(updated_at) FROM calendar_events "
                     "WHERE project_id = ?", project_id)
                ]
                
                last_activity = None
                for query, param in activity_queries:
                    try:
                        cursor.execute(query, (param,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            activity_date = datetime.fromisoformat(result[0])
                            if (not last_activity or
                                    activity_date > last_activity):
                                last_activity = activity_date
                    except Exception:
                        # Table might not exist yet
                        pass
                
                stats.last_activity_date = last_activity
                stats.calculate_days_since_activity()
                
                # Calculate completion metrics
                # Get completed events for this project
                cursor.execute('''
                    SELECT COUNT(*) FROM calendar_events 
                    WHERE project_id = ? AND status = 'completed'
                ''', (project_id,))
                completed_events = cursor.fetchone()[0]
                
                # Get total events
                cursor.execute('''
                    SELECT COUNT(*) FROM calendar_events 
                    WHERE project_id = ?
                ''', (project_id,))
                total_events = cursor.fetchone()[0]
                
                stats.completed_items = completed_events
                stats.total_items = total_events
                stats.calculate_completion_percentage()
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get project statistics: {str(e)}")
            # Use project name if available, otherwise "Unknown"
            project_name = project.name if project else "Unknown"
            return ProjectStatistics(
                project_id=project_id,
                project_name=project_name
            )
    
    def get_project_notes_count(self, project_id: str) -> int:
        """Get count of notes associated with a project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM notes 
                    WHERE project_id = ? AND is_deleted = 0
                ''', (project_id,))
                
                return cursor.fetchone()[0]
                
        except Exception:
            # Table might not exist or have project_id column yet
            return 0
    
    def get_project_artifacts_count(self, project_id: str) -> int:
        """Get count of artifacts associated with a project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM artifacts 
                    WHERE project_id = ? AND status != 'deleted'
                ''', (project_id,))
                
                return cursor.fetchone()[0]
                
        except Exception:
            # Table might not exist or have project_id column yet
            return 0
    
    def get_project_events_count(self, project_id: str) -> int:
        """Get count of calendar events associated with a project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM calendar_events 
                    WHERE project_id = ?
                ''', (project_id,))
                
                return cursor.fetchone()[0]
                
        except Exception:
            # Table might not exist or have project_id column yet
            return 0
    
    def get_projects_with_activity(self,
                                   days: int = 7) -> List[ProjectSummary]:
        """Get projects with recent activity within specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all projects
                projects = self.get_all_projects()
                summaries = []
                
                for project in projects:
                    summary = ProjectSummary.from_project(project)
                    
                    # Count recent activities
                    recent_count = 0
                    last_activity = None
                    last_type = None
                    
                    # Check notes
                    try:
                        cursor.execute('''
                            SELECT COUNT(*), MAX(updated_at) FROM notes 
                            WHERE project_id = ? AND updated_at >= ?
                        ''', (project.id, cutoff_date))
                        count, max_date = cursor.fetchone()
                        if count:
                            recent_count += count
                            if max_date:
                                activity_date = datetime.fromisoformat(
                                    max_date)
                                if (not last_activity or
                                        activity_date > last_activity):
                                    last_activity = activity_date
                                    last_type = "note_updated"
                    except Exception:
                        pass
                    
                    # Check artifacts
                    try:
                        cursor.execute('''
                            SELECT COUNT(*), MAX(updated_at) FROM artifacts 
                            WHERE project_id = ? AND updated_at >= ?
                        ''', (project.id, cutoff_date))
                        count, max_date = cursor.fetchone()
                        if count:
                            recent_count += count
                            if max_date:
                                activity_date = datetime.fromisoformat(
                                    max_date)
                                if (not last_activity or
                                        activity_date > last_activity):
                                    last_activity = activity_date
                                    last_type = "artifact_updated"
                    except Exception:
                        pass
                    
                    # Check calendar events
                    try:
                        cursor.execute('''
                            SELECT COUNT(*), MAX(updated_at)
                            FROM calendar_events
                            WHERE project_id = ? AND updated_at >= ?
                        ''', (project.id, cutoff_date))
                        count, max_date = cursor.fetchone()
                        if count:
                            recent_count += count
                            if max_date:
                                activity_date = datetime.fromisoformat(
                                    max_date)
                                if (not last_activity or
                                        activity_date > last_activity):
                                    last_activity = activity_date
                                    last_type = "event_updated"
                    except Exception:
                        pass
                    
                    if recent_count > 0:
                        summary.recent_activity_count = recent_count
                        summary.last_activity_date = last_activity
                        summary.last_activity_type = last_type
                        
                        # Get total counts
                        summary.total_item_count = (
                            self.get_project_notes_count(project.id) +
                            self.get_project_artifacts_count(project.id) +
                            self.get_project_events_count(project.id)
                        )
                        
                        # Get child count
                        cursor.execute('''
                            SELECT COUNT(*) FROM projects 
                            WHERE parent_project_id = ?
                        ''', (project.id,))
                        summary.child_project_count = cursor.fetchone()[0]
                        
                        summaries.append(summary)
                
                # Sort by most recent activity
                summaries.sort(
                    key=lambda s: s.last_activity_date or datetime.min,
                    reverse=True
                )
                
                return summaries
                
        except Exception as e:
            self.logger.error(
                f"Failed to get projects with activity: {str(e)}")
            return []
    
    def search_projects(self, query: str) -> List[Project]:
        """Search projects by name, description, or tags"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT * FROM projects 
                    WHERE name LIKE ? OR description LIKE ? OR tags LIKE ?
                    ORDER BY updated_at DESC
                ''', (search_pattern, search_pattern, search_pattern))
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to search projects: {str(e)}")
            return []
    
    def get_projects_by_status(self, status: str) -> List[Project]:
        """Get all projects with a specific status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM projects 
                    WHERE status = ?
                    ORDER BY name
                ''', (status,))
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to get projects by status: {str(e)}")
            return []
    
    def get_projects_by_tag(self, tag: str) -> List[Project]:
        """Get all projects containing a specific tag"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Search for tag in comma-separated list
                tag_pattern = f'%{tag}%'
                
                cursor.execute('''
                    SELECT * FROM projects 
                    WHERE tags LIKE ?
                    ORDER BY name
                ''', (tag_pattern,))
                
                projects = []
                for row in cursor.fetchall():
                    project = self._row_to_project(row)
                    # Double-check the tag is actually in the list
                    if tag in project.tags:
                        projects.append(project)
                
                return projects
                
        except Exception as e:
            self.logger.error(f"Failed to get projects by tag: {str(e)}")
            return []
    
    def _row_to_project(self, row) -> Project:
        """Convert database row to Project object"""
        return Project.from_dict({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'status': row[3],
            'color': row[4],
            'icon': row[5],
            'parent_project_id': row[6],
            'tags': row[7],
            'metadata': row[8],
            'created_at': row[9],
            'updated_at': row[10],
            'completed_at': row[11],
            'archived_at': row[12]
        })
    
    def _validate_project_hierarchy(self, project_id: str, 
                                    parent_id: str) -> bool:
        """
        Validate project hierarchy to prevent circular references.
        Returns True if the hierarchy is valid, False otherwise.
        """
        try:
            # Can't be parent of itself
            if project_id == parent_id:
                return False
            
            # Check if parent exists
            parent = self.get_project(parent_id)
            if not parent:
                return False
            
            # Check for circular reference
            # Traverse up the hierarchy from parent
            current_id = parent_id
            visited = set()
            
            while current_id:
                if current_id == project_id:
                    # Circular reference detected
                    return False
                
                if current_id in visited:
                    # Infinite loop protection
                    break
                
                visited.add(current_id)
                
                current = self.get_project(current_id)
                if current:
                    current_id = current.parent_project_id
                else:
                    break
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Error validating project hierarchy: {str(e)}")
            return False
    
    def _get_all_descendants(self, project_id: str) -> List[str]:
        """Get all descendant project IDs recursively"""
        descendants = []
        
        try:
            children = self.get_child_projects(project_id)
            for child in children:
                descendants.append(child.id)
                # Recursively get descendants of children
                descendants.extend(self._get_all_descendants(child.id))
                
        except Exception as e:
            self.logger.error(
                f"Error getting descendants for {project_id}: {str(e)}")
        
        return descendants