#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Artifact Models
Data models for artifacts with support for various content types,
version tracking, collections, and field-level encryption.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import json
from enum import Enum


class ArtifactType(Enum):
    """Artifact content type enumeration"""
    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    BINARY = "binary"


class ArtifactStatus(Enum):
    """Artifact status enumeration"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    DRAFT = "draft"


@dataclass
class Artifact:
    """Artifact with support for various content types and encryption"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    content_type: str = ArtifactType.TEXT.value
    status: str = ArtifactStatus.ACTIVE.value
    
    # Content fields
    content: Optional[str] = None  # For text/code stored in database
    content_path: Optional[str] = None  # For files stored in filesystem
    size_bytes: int = 0
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    
    # Organization
    collection_id: Optional[str] = None
    parent_id: Optional[str] = None  # For hierarchical organization
    
    # Versioning
    version: int = 1
    is_latest: bool = True
    
    # Encryption
    encrypted_fields: List[str] = field(default_factory=list)
    encryption_key_id: Optional[str] = None
    
    # Integration
    project_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    note_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None  # Custom properties
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content_type': self.content_type,
            'status': self.status,
            'content': self.content,
            'content_path': self.content_path,
            'size_bytes': self.size_bytes,
            'mime_type': self.mime_type,
            'checksum': self.checksum,
            'collection_id': self.collection_id,
            'parent_id': self.parent_id,
            'version': self.version,
            'is_latest': self.is_latest,
            'encrypted_fields': (','.join(self.encrypted_fields) 
                                 if self.encrypted_fields else ''),
            'encryption_key_id': self.encryption_key_id,
            'project_id': self.project_id,
            'chat_session_id': self.chat_session_id,
            'note_id': self.note_id,
            'tags': ','.join(self.tags) if self.tags else '',
            'metadata': json.dumps(self.metadata) if self.metadata else None,
            'properties': (json.dumps(self.properties)
                           if self.properties else None),
            'created_at': (self.created_at.isoformat() 
                           if isinstance(self.created_at, datetime) 
                           else self.created_at),
            'updated_at': (self.updated_at.isoformat() 
                           if isinstance(self.updated_at, datetime) 
                           else self.updated_at),
            'accessed_at': (self.accessed_at.isoformat() 
                            if self.accessed_at else None)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artifact':
        """Create from dictionary"""
        # Parse timestamps
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        accessed_at = data.get('accessed_at')
        if accessed_at and isinstance(accessed_at, str):
            accessed_at = datetime.fromisoformat(accessed_at)
        
        # Parse lists
        encrypted_fields = data.get('encrypted_fields', '')
        if isinstance(encrypted_fields, str) and encrypted_fields:
            encrypted_fields = [f.strip() for f in encrypted_fields.split(',')]
        else:
            encrypted_fields = []
            
        tags = data.get('tags', '')
        if isinstance(tags, str) and tags:
            tags = [tag.strip() for tag in tags.split(',')]
        else:
            tags = []
        
        # Parse JSON fields
        metadata = data.get('metadata')
        if metadata and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None
                
        properties = data.get('properties')
        if properties and isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError:
                properties = None
                
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description'),
            content_type=data.get('content_type', ArtifactType.TEXT.value),
            status=data.get('status', ArtifactStatus.ACTIVE.value),
            content=data.get('content'),
            content_path=data.get('content_path'),
            size_bytes=data.get('size_bytes', 0),
            mime_type=data.get('mime_type'),
            checksum=data.get('checksum'),
            collection_id=data.get('collection_id'),
            parent_id=data.get('parent_id'),
            version=data.get('version', 1),
            is_latest=data.get('is_latest', True),
            encrypted_fields=encrypted_fields,
            encryption_key_id=data.get('encryption_key_id'),
            project_id=data.get('project_id'),
            chat_session_id=data.get('chat_session_id'),
            note_id=data.get('note_id'),
            tags=tags,
            metadata=metadata,
            properties=properties,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            accessed_at=accessed_at
        )
    
    def get_storage_path(self, username: str) -> str:
        """Get the file storage path for this artifact"""
        if self.created_at:
            year = self.created_at.year
            month = f"{self.created_at.month:02d}"
        else:
            now = datetime.now()
            year = now.year
            month = f"{now.month:02d}"
            
        return f"src/user_data/{username}/artifacts/{year}/{month}/{self.id}"
    
    def is_encrypted(self) -> bool:
        """Check if artifact has encrypted fields"""
        return bool(self.encrypted_fields)
    
    def __str__(self) -> str:
        """String representation"""
        size_str = (f"{self.size_bytes:,} bytes"
                    if self.size_bytes > 0 else "No size")
        return f"Artifact({self.name}, {self.content_type}, {size_str})"


@dataclass
class ArtifactVersion:
    """Version tracking for artifacts"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    artifact_id: str = ""
    version_number: int = 1
    
    # Version content (stores the full artifact data at this version)
    artifact_data: Dict[str, Any] = field(default_factory=dict)
    
    # Version metadata
    change_summary: Optional[str] = None
    changed_by: Optional[str] = None
    changed_fields: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'artifact_id': self.artifact_id,
            'version_number': self.version_number,
            'artifact_data': json.dumps(self.artifact_data),
            'change_summary': self.change_summary,
            'changed_by': self.changed_by,
            'changed_fields': (','.join(self.changed_fields) 
                               if self.changed_fields else ''),
            'created_at': (self.created_at.isoformat() 
                           if isinstance(self.created_at, datetime) 
                           else self.created_at)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactVersion':
        """Create from dictionary"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        artifact_data = data.get('artifact_data', '{}')
        if isinstance(artifact_data, str):
            try:
                artifact_data = json.loads(artifact_data)
            except json.JSONDecodeError:
                artifact_data = {}
        
        changed_fields = data.get('changed_fields', '')
        if isinstance(changed_fields, str) and changed_fields:
            changed_fields = [f.strip() for f in changed_fields.split(',')]
        else:
            changed_fields = []
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            artifact_id=data.get('artifact_id', ''),
            version_number=data.get('version_number', 1),
            artifact_data=artifact_data,
            change_summary=data.get('change_summary'),
            changed_by=data.get('changed_by'),
            changed_fields=changed_fields,
            created_at=created_at or datetime.now()
        )


@dataclass
class ArtifactCollection:
    """Collection for organizing artifacts"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    
    # Organization
    parent_id: Optional[str] = None  # For nested collections
    project_id: Optional[str] = None
    
    # Collection properties
    is_encrypted: bool = False
    is_public: bool = False
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    properties: Optional[Dict[str, Any]] = None
    
    # Statistics
    artifact_count: int = 0
    total_size_bytes: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'project_id': self.project_id,
            'is_encrypted': self.is_encrypted,
            'is_public': self.is_public,
            'tags': ','.join(self.tags) if self.tags else '',
            'properties': (json.dumps(self.properties)
                           if self.properties else None),
            'artifact_count': self.artifact_count,
            'total_size_bytes': self.total_size_bytes,
            'created_at': (self.created_at.isoformat() 
                           if isinstance(self.created_at, datetime) 
                           else self.created_at),
            'updated_at': (self.updated_at.isoformat() 
                           if isinstance(self.updated_at, datetime) 
                           else self.updated_at)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactCollection':
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
            
        properties = data.get('properties')
        if properties and isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError:
                properties = None
                
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            project_id=data.get('project_id'),
            is_encrypted=data.get('is_encrypted', False),
            is_public=data.get('is_public', False),
            tags=tags,
            properties=properties,
            artifact_count=data.get('artifact_count', 0),
            total_size_bytes=data.get('total_size_bytes', 0),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now()
        )
    
    def __str__(self) -> str:
        """String representation"""
        return (f"ArtifactCollection({self.name}, "
                f"{self.artifact_count} artifacts)")


@dataclass
class ArtifactPermission:
    """Permission model for artifacts (future-ready)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    artifact_id: str = ""
    user_id: str = ""
    
    # Permission levels
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False
    can_share: bool = False
    
    # Permission metadata
    granted_by: Optional[str] = None
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'artifact_id': self.artifact_id,
            'user_id': self.user_id,
            'can_read': self.can_read,
            'can_write': self.can_write,
            'can_delete': self.can_delete,
            'can_share': self.can_share,
            'granted_by': self.granted_by,
            'granted_at': (self.granted_at.isoformat() 
                           if isinstance(self.granted_at, datetime) 
                           else self.granted_at),
            'expires_at': (self.expires_at.isoformat() 
                           if self.expires_at else None)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactPermission':
        """Create from dictionary"""
        granted_at = data.get('granted_at')
        if isinstance(granted_at, str):
            granted_at = datetime.fromisoformat(granted_at)
            
        expires_at = data.get('expires_at')
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            artifact_id=data.get('artifact_id', ''),
            user_id=data.get('user_id', ''),
            can_read=data.get('can_read', True),
            can_write=data.get('can_write', False),
            can_delete=data.get('can_delete', False),
            can_share=data.get('can_share', False),
            granted_by=data.get('granted_by'),
            granted_at=granted_at or datetime.now(),
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if permission has expired"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False