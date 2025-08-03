#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Session Models
Data models for chat sessions and messages with full metadata support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import json


@dataclass
class ChatMessage:
    """Individual chat message with metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    message: str = ""
    is_user: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message': self.message,
            'is_user': self.is_user,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        metadata = data.get('metadata')
        if metadata and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None
                
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            session_id=data.get('session_id', ''),
            message=data.get('message', ''),
            is_user=data.get('is_user', True),
            timestamp=timestamp or datetime.now(),
            metadata=metadata
        )


@dataclass
class ChatSession:
    """Chat session with messages and metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    status: str = "active"
    messages: List[ChatMessage] = field(default_factory=list)
    
    def add_message(self, message: str, is_user: bool = True, metadata: Optional[Dict] = None) -> ChatMessage:
        """Add a message to the session"""
        msg = ChatMessage(
            session_id=self.id,
            message=message,
            is_user=is_user,
            metadata=metadata
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg
    
    def get_preview(self, max_length: int = 50) -> str:
        """Get a preview of the session"""
        if self.messages:
            # Get the first user message as preview
            for msg in self.messages:
                if msg.is_user and msg.message:
                    preview = msg.message[:max_length]
                    if len(msg.message) > max_length:
                        preview += "..."
                    return preview
        return self.title or "Empty chat"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'tags': ','.join(self.tags) if self.tags else '',
            'summary': self.summary,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create from dictionary"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        tags = data.get('tags', '')
        if isinstance(tags, str) and tags:
            tags = [tag.strip() for tag in tags.split(',')]
        else:
            tags = []
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            project_id=data.get('project_id'),
            task_id=data.get('task_id'),
            tags=tags,
            summary=data.get('summary'),
            status=data.get('status', 'active'),
            messages=[]
        )


@dataclass
class ChatSchedule:
    """Cron-style schedule for chat sessions"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    cron_expression: str = ""
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'cron_expression': self.cron_expression,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'is_active': self.is_active
        }