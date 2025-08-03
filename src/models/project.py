#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Models
Data models for projects with support for hierarchical organization,
status tracking, and project-level statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import json
from enum import Enum


class ProjectStatus(Enum):
    """Project status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Project:
    """Project with hierarchical support and comprehensive metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    status: str = ProjectStatus.ACTIVE.value
    
    # Visual customization
    color: Optional[str] = None  # Hex color code (e.g., "#007bff")
    icon: Optional[str] = None   # Icon identifier or emoji
    
    # Hierarchical organization
    parent_project_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'color': self.color,
            'icon': self.icon,
            'parent_project_id': self.parent_project_id,
            'tags': ','.join(self.tags) if self.tags else '',
            'metadata': json.dumps(self.metadata) if self.metadata else None,
            'created_at': (self.created_at.isoformat()
                           if isinstance(self.created_at, datetime)
                           else self.created_at),
            'updated_at': (self.updated_at.isoformat()
                           if isinstance(self.updated_at, datetime)
                           else self.updated_at),
            'completed_at': (self.completed_at.isoformat()
                             if self.completed_at else None),
            'archived_at': (self.archived_at.isoformat()
                            if self.archived_at else None)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create from dictionary"""
        # Parse timestamps
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        completed_at = data.get('completed_at')
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
            
        archived_at = data.get('archived_at')
        if archived_at and isinstance(archived_at, str):
            archived_at = datetime.fromisoformat(archived_at)
        
        # Parse tags
        tags = data.get('tags', '')
        if isinstance(tags, str) and tags:
            tags = [tag.strip() for tag in tags.split(',')]
        else:
            tags = []
        
        # Parse metadata
        metadata = data.get('metadata')
        if metadata and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None
                
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description'),
            status=data.get('status', ProjectStatus.ACTIVE.value),
            color=data.get('color'),
            icon=data.get('icon'),
            parent_project_id=data.get('parent_project_id'),
            tags=tags,
            metadata=metadata,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            completed_at=completed_at,
            archived_at=archived_at
        )
    
    def is_active(self) -> bool:
        """Check if project is active"""
        return self.status == ProjectStatus.ACTIVE.value
    
    def is_completed(self) -> bool:
        """Check if project is completed"""
        return self.status == ProjectStatus.COMPLETED.value
    
    def is_archived(self) -> bool:
        """Check if project is archived"""
        return self.status == ProjectStatus.ARCHIVED.value
    
    def get_status_display(self) -> str:
        """Get human-readable status display"""
        status_map = {
            ProjectStatus.ACTIVE.value: "Active",
            ProjectStatus.COMPLETED.value: "Completed",
            ProjectStatus.ARCHIVED.value: "Archived"
        }
        return status_map.get(self.status, self.status.title())
    
    def has_parent(self) -> bool:
        """Check if project has a parent project"""
        return self.parent_project_id is not None
    
    def is_child_of(self, project_id: str) -> bool:
        """Check if this project is a child of the given project"""
        return self.parent_project_id == project_id
    
    def mark_completed(self) -> None:
        """Mark project as completed and set completion timestamp"""
        self.status = ProjectStatus.COMPLETED.value
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_archived(self) -> None:
        """Mark project as archived and set archive timestamp"""
        self.status = ProjectStatus.ARCHIVED.value
        self.archived_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_active(self) -> None:
        """Mark project as active and clear completion/archive timestamps"""
        self.status = ProjectStatus.ACTIVE.value
        self.completed_at = None
        self.archived_at = None
        self.updated_at = datetime.now()
    
    def get_display_color(self) -> str:
        """Get the display color with fallback to default"""
        return self.color or "#007bff"  # Default blue color
    
    def get_display_icon(self) -> str:
        """Get the display icon with fallback to default"""
        return self.icon or "📁"  # Default folder icon
    
    def __str__(self) -> str:
        """String representation"""
        status_str = self.get_status_display()
        parent_str = (f", child of {self.parent_project_id}"
                      if self.has_parent() else "")
        return f"Project({self.name}, {status_str}{parent_str})"


@dataclass
class ProjectStatistics:
    """Statistics for a project's associated data"""
    project_id: str
    project_name: str
    
    # Content counts
    total_notes: int = 0
    total_artifacts: int = 0
    total_calendar_events: int = 0
    total_chat_sessions: int = 0
    
    # Sub-project count
    child_project_count: int = 0
    
    # Activity metrics
    last_activity_date: Optional[datetime] = None
    days_since_last_activity: Optional[int] = None
    
    # Progress metrics (can be calculated based on completed tasks/events)
    completion_percentage: float = 0.0
    completed_items: int = 0
    total_items: int = 0
    
    def calculate_days_since_activity(self) -> None:
        """Calculate days since last activity"""
        if self.last_activity_date:
            delta = datetime.now() - self.last_activity_date
            self.days_since_last_activity = delta.days
    
    def calculate_completion_percentage(self) -> None:
        """Calculate completion percentage based on completed vs total items"""
        if self.total_items > 0:
            self.completion_percentage = (
                (self.completed_items / self.total_items) * 100
            )
        else:
            self.completion_percentage = 0.0
    
    def get_total_content_count(self) -> int:
        """Get total count of all content types"""
        return (self.total_notes + self.total_artifacts + 
                self.total_calendar_events + self.total_chat_sessions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'total_notes': self.total_notes,
            'total_artifacts': self.total_artifacts,
            'total_calendar_events': self.total_calendar_events,
            'total_chat_sessions': self.total_chat_sessions,
            'child_project_count': self.child_project_count,
            'last_activity_date': (self.last_activity_date.isoformat()
                                   if self.last_activity_date else None),
            'days_since_last_activity': self.days_since_last_activity,
            'completion_percentage': self.completion_percentage,
            'completed_items': self.completed_items,
            'total_items': self.total_items
        }
    
    def __str__(self) -> str:
        """String representation"""
        content_count = self.get_total_content_count()
        return (f"ProjectStatistics({self.project_name}, "
                f"{content_count} items, "
                f"{self.completion_percentage:.1f}% complete)")


@dataclass
class ProjectSummary:
    """Lightweight project summary for list views"""
    id: str
    name: str
    description: Optional[str] = None
    status: str = ProjectStatus.ACTIVE.value
    color: Optional[str] = None
    icon: Optional[str] = None
    
    # Quick stats
    recent_activity_count: int = 0  # Activities in last 7 days
    child_project_count: int = 0
    total_item_count: int = 0  # Total notes, artifacts, events, etc.
    
    # Parent info
    parent_project_id: Optional[str] = None
    parent_project_name: Optional[str] = None
    
    # Last activity
    last_activity_date: Optional[datetime] = None
    last_activity_type: Optional[str] = None  # e.g., "note_created"
    
    def get_status_display(self) -> str:
        """Get human-readable status display"""
        status_map = {
            ProjectStatus.ACTIVE.value: "Active",
            ProjectStatus.COMPLETED.value: "Completed",
            ProjectStatus.ARCHIVED.value: "Archived"
        }
        return status_map.get(self.status, self.status.title())
    
    def get_display_color(self) -> str:
        """Get the display color with fallback to default"""
        return self.color or "#007bff"  # Default blue color
    
    def get_display_icon(self) -> str:
        """Get the display icon with fallback to default"""
        return self.icon or "📁"  # Default folder icon
    
    def has_recent_activity(self, days: int = 7) -> bool:
        """Check if project has recent activity within specified days"""
        if self.last_activity_date:
            delta = datetime.now() - self.last_activity_date
            return delta.days <= days
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'color': self.color,
            'icon': self.icon,
            'recent_activity_count': self.recent_activity_count,
            'child_project_count': self.child_project_count,
            'total_item_count': self.total_item_count,
            'parent_project_id': self.parent_project_id,
            'parent_project_name': self.parent_project_name,
            'last_activity_date': (self.last_activity_date.isoformat()
                                   if self.last_activity_date else None),
            'last_activity_type': self.last_activity_type
        }
    
    @classmethod
    def from_project(cls, project: Project, **kwargs) -> 'ProjectSummary':
        """Create summary from a Project instance with optional stats"""
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            color=project.color,
            icon=project.icon,
            parent_project_id=project.parent_project_id,
            **kwargs
        )
    
    def __str__(self) -> str:
        """String representation"""
        status_str = self.get_status_display()
        activity_str = "active" if self.has_recent_activity() else "inactive"
        return f"ProjectSummary({self.name}, {status_str}, {activity_str})"