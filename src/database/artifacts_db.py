#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Artifacts Database Manager
Manages all artifact database operations with resilient handling,
version control, and file storage integration.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models.artifact import (
    Artifact, ArtifactVersion, ArtifactCollection
)
from ..utils.logger import Logger


class ArtifactsDatabase:
    """Manages artifacts database operations with file storage support"""
    
    # File size threshold for external storage (5MB)
    FILE_SIZE_THRESHOLD = 5 * 1024 * 1024
    
    def __init__(self, db_manager):
        """Initialize with database manager reference"""
        self.db_manager = db_manager
        self.logger = Logger()
        self.username = db_manager.user_name
        
    def _get_connection(self):
        """Get database connection"""
        return self.db_manager.get_artifacts_connection()
    
    def _get_storage_path(self, artifact: Artifact) -> Path:
        """Get file storage path for artifact"""
        storage_path = artifact.get_storage_path(self.username)
        return Path(self.db_manager.base_dir) / storage_path
    
    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA256 checksum of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _handle_file_storage(self, artifact: Artifact, 
                             content: Optional[bytes] = None) -> Artifact:
        """Handle file storage for large artifacts"""
        if content is None:
            return artifact
            
        size_bytes = len(content)
        artifact.size_bytes = size_bytes
        artifact.checksum = self._compute_checksum(content)
        
        # Determine storage strategy based on size
        if size_bytes > self.FILE_SIZE_THRESHOLD:
            # Store in filesystem
            storage_path = self._get_storage_path(artifact)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path = storage_path / "content.bin"
            with open(file_path, 'wb') as f:
                f.write(content)
                
            artifact.content_path = str(file_path.relative_to(
                self.db_manager.base_dir))
            artifact.content = None  # Don't store in database
            
            self.logger.info(f"Stored artifact {artifact.id} to file: "
                             f"{artifact.content_path}")
        else:
            # Store in database
            artifact.content = content.decode('utf-8', errors='replace')
            artifact.content_path = None
            
        return artifact
    
    def create_artifact(self, artifact: Artifact, 
                        content: Optional[bytes] = None) -> Dict[str, Any]:
        """Create a new artifact with optional file content"""
        try:
            # Handle file storage if content provided
            artifact = self._handle_file_storage(artifact, content)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                artifact_dict = artifact.to_dict()
                
                # Insert artifact
                cursor.execute('''
                    INSERT INTO artifacts 
                    (id, name, description, content_type, status, content,
                     content_path, size_bytes, mime_type, checksum,
                     collection_id, parent_id, version, is_latest,
                     encrypted_fields, encryption_key_id, project_id,
                     chat_session_id, note_id, tags, metadata, properties,
                     created_at, updated_at, accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    artifact_dict['id'],
                    artifact_dict['name'],
                    artifact_dict['description'],
                    artifact_dict['content_type'],
                    artifact_dict['status'],
                    artifact_dict['content'],
                    artifact_dict['content_path'],
                    artifact_dict['size_bytes'],
                    artifact_dict['mime_type'],
                    artifact_dict['checksum'],
                    artifact_dict['collection_id'],
                    artifact_dict['parent_id'],
                    artifact_dict['version'],
                    artifact_dict['is_latest'],
                    artifact_dict['encrypted_fields'],
                    artifact_dict['encryption_key_id'],
                    artifact_dict['project_id'],
                    artifact_dict['chat_session_id'],
                    artifact_dict['note_id'],
                    artifact_dict['tags'],
                    artifact_dict['metadata'],
                    artifact_dict['properties'],
                    artifact_dict['created_at'],
                    artifact_dict['updated_at'],
                    artifact_dict['accessed_at']
                ))
                
                # Create initial version
                self._create_version(cursor, artifact)
                
                # Update collection stats if applicable
                if artifact.collection_id:
                    self._update_collection_stats(cursor, 
                                                  artifact.collection_id)
                
                conn.commit()
                
                self.logger.info(f"Created artifact: {artifact.id}")
                return {"success": True, "id": artifact.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create artifact: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_artifact(self, artifact_id: str, 
                        updates: Dict[str, Any],
                        content: Optional[bytes] = None) -> bool:
        """Update an existing artifact"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current artifact for version tracking
                current = self.get_artifact(artifact_id)
                if not current:
                    return False
                
                # Handle file storage if new content provided
                if content is not None:
                    temp_artifact = Artifact(id=artifact_id)
                    temp_artifact.created_at = current.created_at
                    temp_artifact = self._handle_file_storage(
                        temp_artifact, content)
                    
                    updates['content'] = temp_artifact.content
                    updates['content_path'] = temp_artifact.content_path
                    updates['size_bytes'] = temp_artifact.size_bytes
                    updates['checksum'] = temp_artifact.checksum
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                # Allowed fields for update
                allowed_fields = [
                    'name', 'description', 'content_type', 'status',
                    'content', 'content_path', 'size_bytes', 'mime_type',
                    'checksum', 'collection_id', 'parent_id',
                    'encrypted_fields', 'encryption_key_id', 'project_id',
                    'chat_session_id', 'note_id', 'tags', 'metadata',
                    'properties'
                ]
                
                changed_fields = []
                for key, value in updates.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = ?")
                        # Handle special formatting for certain fields
                        if (key == 'encrypted_fields' and
                                isinstance(value, list)):
                            value = ','.join(value)
                        elif key == 'tags' and isinstance(value, list):
                            value = ','.join(value)
                        elif (key in ['metadata', 'properties'] and
                              isinstance(value, dict)):
                            value = json.dumps(value)
                        params.append(value)
                        changed_fields.append(key)
                
                if not set_clauses:
                    return False
                
                # Update version and timestamps
                new_version = current.version + 1
                set_clauses.extend([
                    "version = ?",
                    "updated_at = CURRENT_TIMESTAMP",
                    "accessed_at = CURRENT_TIMESTAMP"
                ])
                params.extend([new_version, artifact_id])
                
                query = f"""UPDATE artifacts 
                           SET {', '.join(set_clauses)} 
                           WHERE id = ?"""
                cursor.execute(query, params)
                
                # Create new version with changes
                if cursor.rowcount > 0:
                    # Get updated artifact for version storage
                    updated = self.get_artifact(artifact_id)
                    if updated:
                        version = ArtifactVersion(
                            artifact_id=artifact_id,
                            version_number=new_version,
                            artifact_data=updated.to_dict(),
                            change_summary=updates.get('change_summary', 
                                                       'Updated artifact'),
                            changed_fields=changed_fields
                        )
                        self._create_version_record(cursor, version)
                
                # Update collection stats if collection changed
                if 'collection_id' in updates:
                    # Update old collection
                    if current.collection_id:
                        self._update_collection_stats(cursor, 
                                                      current.collection_id)
                    # Update new collection
                    if updates['collection_id']:
                        self._update_collection_stats(cursor, 
                                                      updates['collection_id'])
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to update artifact: {str(e)}")
            return False
    
    def delete_artifact(self, artifact_id: str, 
                        hard_delete: bool = False) -> bool:
        """Delete an artifact (soft delete by default)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if hard_delete:
                    # Get artifact for cleanup
                    artifact = self.get_artifact(artifact_id)
                    if not artifact:
                        return False
                    
                    # Delete versions first (foreign key constraint)
                    cursor.execute('''DELETE FROM artifact_versions 
                                     WHERE artifact_id = ?''', (artifact_id,))
                    
                    # Delete permissions
                    cursor.execute('''DELETE FROM artifact_permissions 
                                     WHERE artifact_id = ?''', (artifact_id,))
                    
                    # Delete artifact
                    cursor.execute('''DELETE FROM artifacts 
                                     WHERE id = ?''', (artifact_id,))
                    
                    # Clean up file storage if exists
                    if artifact.content_path:
                        file_path = (Path(self.db_manager.base_dir) / 
                                     artifact.content_path)
                        if file_path.exists():
                            file_path.unlink()
                            # Try to remove empty directories
                            try:
                                file_path.parent.rmdir()
                            except OSError:
                                pass  # Directory not empty
                    
                    # Update collection stats
                    if artifact.collection_id:
                        self._update_collection_stats(cursor, 
                                                      artifact.collection_id)
                else:
                    # Soft delete
                    cursor.execute('''UPDATE artifacts 
                                     SET status = 'deleted', 
                                         updated_at = CURRENT_TIMESTAMP 
                                     WHERE id = ?''', (artifact_id,))
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to delete artifact: {str(e)}")
            return False
    
    def get_artifact(self, artifact_id: str, 
                     update_accessed: bool = True) -> Optional[Artifact]:
        """Get a specific artifact"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM artifacts WHERE id = ?
                ''', (artifact_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Update accessed timestamp if requested
                if update_accessed:
                    cursor.execute('''UPDATE artifacts 
                                     SET accessed_at = CURRENT_TIMESTAMP 
                                     WHERE id = ?''', (artifact_id,))
                    conn.commit()
                
                return self._row_to_artifact(row)
                
        except Exception as e:
            self.logger.error(f"Failed to get artifact: {str(e)}")
            return None
    
    def get_artifact_content(self, artifact_id: str) -> Optional[bytes]:
        """Get artifact content (from database or file)"""
        try:
            artifact = self.get_artifact(artifact_id)
            if not artifact:
                return None
                
            if artifact.content:
                # Content stored in database
                return artifact.content.encode('utf-8')
            elif artifact.content_path:
                # Content stored in file
                file_path = (Path(self.db_manager.base_dir) /
                             artifact.content_path)
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        return f.read()
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get artifact content: {str(e)}")
            return None
    
    def search_artifacts(self, query: str, 
                         limit: int = 100) -> List[Artifact]:
        """Search artifacts by name, description, or tags"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT * FROM artifacts 
                    WHERE (name LIKE ? OR description LIKE ? OR tags LIKE ?)
                    AND status != 'deleted'
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (search_pattern, search_pattern, search_pattern, limit))
                
                artifacts = []
                for row in cursor.fetchall():
                    artifact = self._row_to_artifact(row)
                    artifacts.append(artifact)
                
                return artifacts
                
        except Exception as e:
            self.logger.error(f"Failed to search artifacts: {str(e)}")
            return []
    
    def get_artifacts_by_type(self, content_type: str, 
                              limit: int = 100) -> List[Artifact]:
        """Get artifacts by content type"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM artifacts 
                    WHERE content_type = ? AND status != 'deleted'
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (content_type, limit))
                
                artifacts = []
                for row in cursor.fetchall():
                    artifact = self._row_to_artifact(row)
                    artifacts.append(artifact)
                
                return artifacts
                
        except Exception as e:
            self.logger.error(f"Failed to get artifacts by type: {str(e)}")
            return []
    
    def get_artifacts_by_collection(self,
                                    collection_id: str) -> List[Artifact]:
        """Get all artifacts in a collection"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM artifacts
                    WHERE collection_id = ? AND status != 'deleted'
                    ORDER BY name, updated_at DESC
                ''', (collection_id,))
                
                artifacts = []
                for row in cursor.fetchall():
                    artifact = self._row_to_artifact(row)
                    artifacts.append(artifact)
                
                return artifacts
                
        except Exception as e:
            self.logger.error(
                f"Failed to get artifacts by collection: {str(e)}")
            return []
    
    def get_artifacts_by_project(self, project_id: str) -> List[Artifact]:
        """Get all artifacts in a project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM artifacts
                    WHERE project_id = ? AND status != 'deleted'
                    ORDER BY updated_at DESC
                ''', (project_id,))
                
                artifacts = []
                for row in cursor.fetchall():
                    artifact = self._row_to_artifact(row)
                    artifacts.append(artifact)
                
                return artifacts
                
        except Exception as e:
            self.logger.error(
                f"Failed to get artifacts by project: {str(e)}")
            return []
    
    def create_collection(self,
                          collection: ArtifactCollection) -> Dict[str, Any]:
        """Create a new artifact collection"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                collection_dict = collection.to_dict()
                
                cursor.execute('''
                    INSERT INTO artifact_collections 
                    (id, name, description, parent_id, project_id,
                     is_encrypted, is_public, tags, properties,
                     artifact_count, total_size_bytes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    collection_dict['id'],
                    collection_dict['name'],
                    collection_dict['description'],
                    collection_dict['parent_id'],
                    collection_dict['project_id'],
                    collection_dict['is_encrypted'],
                    collection_dict['is_public'],
                    collection_dict['tags'],
                    collection_dict['properties'],
                    collection_dict['artifact_count'],
                    collection_dict['total_size_bytes'],
                    collection_dict['created_at'],
                    collection_dict['updated_at']
                ))
                
                conn.commit()
                
                self.logger.info(f"Created collection: {collection.id}")
                return {"success": True, "id": collection.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create collection: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_collections(
            self,
            parent_id: Optional[str] = None) -> List[ArtifactCollection]:
        """Get all collections or collections under a parent"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if parent_id is None:
                    # Get root collections
                    cursor.execute('''
                        SELECT * FROM artifact_collections 
                        WHERE parent_id IS NULL
                        ORDER BY name
                    ''')
                else:
                    # Get child collections
                    cursor.execute('''
                        SELECT * FROM artifact_collections 
                        WHERE parent_id = ?
                        ORDER BY name
                    ''', (parent_id,))
                
                collections = []
                for row in cursor.fetchall():
                    collection = self._row_to_collection(row)
                    collections.append(collection)
                
                return collections
                
        except Exception as e:
            self.logger.error(f"Failed to get collections: {str(e)}")
            return []
    
    def update_collection(self, collection_id: str, 
                          updates: Dict[str, Any]) -> bool:
        """Update a collection"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                # Allowed fields for update
                allowed_fields = [
                    'name', 'description', 'parent_id', 'project_id',
                    'is_encrypted', 'is_public', 'tags', 'properties'
                ]
                
                for key, value in updates.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = ?")
                        # Handle special formatting for certain fields
                        if key == 'tags' and isinstance(value, list):
                            value = ','.join(value)
                        elif key == 'properties' and isinstance(value, dict):
                            value = json.dumps(value)
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                # Always update the timestamp
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(collection_id)
                
                query = f"""UPDATE artifact_collections 
                           SET {', '.join(set_clauses)} 
                           WHERE id = ?"""
                cursor.execute(query, params)
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to update collection: {str(e)}")
            return False
    
    def create_version(self, artifact_id: str,
                       change_summary: Optional[str] = None) -> bool:
        """Create a new version of an artifact"""
        try:
            artifact = self.get_artifact(artifact_id)
            if not artifact:
                return False
                
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                version = ArtifactVersion(
                    artifact_id=artifact_id,
                    version_number=artifact.version,
                    artifact_data=artifact.to_dict(),
                    change_summary=change_summary or 'Manual version created'
                )
                
                self._create_version_record(cursor, version)
                conn.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create version: {str(e)}")
            return False
    
    def get_versions(self, artifact_id: str) -> List[ArtifactVersion]:
        """Get all versions of an artifact"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM artifact_versions 
                    WHERE artifact_id = ?
                    ORDER BY version_number DESC
                ''', (artifact_id,))
                
                versions = []
                for row in cursor.fetchall():
                    version = self._row_to_version(row)
                    versions.append(version)
                
                return versions
                
        except Exception as e:
            self.logger.error(f"Failed to get versions: {str(e)}")
            return []
    
    def restore_version(self, artifact_id: str, 
                        version_number: int) -> bool:
        """Restore an artifact to a specific version"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the version to restore
                cursor.execute('''
                    SELECT artifact_data FROM artifact_versions 
                    WHERE artifact_id = ? AND version_number = ?
                ''', (artifact_id, version_number))
                
                row = cursor.fetchone()
                if not row:
                    return False
                
                # Parse artifact data
                artifact_data = json.loads(row[0])
                
                # Prepare update data
                updates = {
                    key: value for key, value in artifact_data.items()
                    if key not in ['id', 'version', 'created_at', 'updated_at']
                }
                
                # Add restoration metadata
                updates['change_summary'] = (
                    f'Restored to version {version_number}')
                
                # Perform the update
                return self.update_artifact(artifact_id, updates)
                
        except Exception as e:
            self.logger.error(f"Failed to restore version: {str(e)}")
            return False
    
    def get_artifact_statistics(self) -> Dict[str, Any]:
        """Get artifact statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total artifacts
                cursor.execute('''SELECT COUNT(*) FROM artifacts 
                                 WHERE status != 'deleted' ''')
                stats['total_artifacts'] = cursor.fetchone()[0]
                
                # Artifacts by type
                cursor.execute('''
                    SELECT content_type, COUNT(*) 
                    FROM artifacts 
                    WHERE status != 'deleted'
                    GROUP BY content_type
                ''')
                stats['artifacts_by_type'] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }
                
                # Total storage size
                cursor.execute('''
                    SELECT SUM(size_bytes) 
                    FROM artifacts 
                    WHERE status != 'deleted'
                ''')
                total_size = cursor.fetchone()[0] or 0
                stats['total_size_bytes'] = total_size
                stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
                
                # Encrypted artifacts
                cursor.execute('''
                    SELECT COUNT(*) FROM artifacts 
                    WHERE encrypted_fields != '' AND status != 'deleted'
                ''')
                stats['encrypted_artifacts'] = cursor.fetchone()[0]
                
                # Collections
                cursor.execute('SELECT COUNT(*) FROM artifact_collections')
                stats['total_collections'] = cursor.fetchone()[0]
                
                # Artifacts with versions
                cursor.execute('''
                    SELECT COUNT(DISTINCT artifact_id) 
                    FROM artifact_versions
                ''')
                stats['versioned_artifacts'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get artifact statistics: {str(e)}")
            return {}
    
    def _create_version(self, cursor, artifact: Artifact):
        """Create initial version for new artifact"""
        version = ArtifactVersion(
            artifact_id=artifact.id,
            version_number=1,
            artifact_data=artifact.to_dict(),
            change_summary='Initial version'
        )
        self._create_version_record(cursor, version)
    
    def _create_version_record(self, cursor, version: ArtifactVersion):
        """Insert version record into database"""
        version_dict = version.to_dict()
        cursor.execute('''
            INSERT INTO artifact_versions 
            (id, artifact_id, version_number, artifact_data,
             change_summary, changed_by, changed_fields, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_dict['id'],
            version_dict['artifact_id'],
            version_dict['version_number'],
            version_dict['artifact_data'],
            version_dict['change_summary'],
            version_dict['changed_by'],
            version_dict['changed_fields'],
            version_dict['created_at']
        ))
    
    def _update_collection_stats(self, cursor, collection_id: str):
        """Update collection statistics"""
        cursor.execute('''
            SELECT COUNT(*), SUM(size_bytes) 
            FROM artifacts 
            WHERE collection_id = ? AND status != 'deleted'
        ''', (collection_id,))
        
        count, total_size = cursor.fetchone()
        
        cursor.execute('''
            UPDATE artifact_collections 
            SET artifact_count = ?, 
                total_size_bytes = ?,
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (count or 0, total_size or 0, collection_id))
    
    def _row_to_artifact(self, row) -> Artifact:
        """Convert database row to Artifact object"""
        return Artifact.from_dict({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'content_type': row[3],
            'status': row[4],
            'content': row[5],
            'content_path': row[6],
            'size_bytes': row[7],
            'mime_type': row[8],
            'checksum': row[9],
            'collection_id': row[10],
            'parent_id': row[11],
            'version': row[12],
            'is_latest': bool(row[13]),
            'encrypted_fields': row[14],
            'encryption_key_id': row[15],
            'project_id': row[16],
            'chat_session_id': row[17],
            'note_id': row[18],
            'tags': row[19],
            'metadata': row[20],
            'properties': row[21],
            'created_at': row[22],
            'updated_at': row[23],
            'accessed_at': row[24]
        })
    
    def _row_to_collection(self, row) -> ArtifactCollection:
        """Convert database row to ArtifactCollection object"""
        return ArtifactCollection.from_dict({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'parent_id': row[3],
            'project_id': row[4],
            'is_encrypted': bool(row[5]),
            'is_public': bool(row[6]),
            'tags': row[7],
            'properties': row[8],
            'artifact_count': row[9],
            'total_size_bytes': row[10],
            'created_at': row[11],
            'updated_at': row[12]
        })
    
    def _row_to_version(self, row) -> ArtifactVersion:
        """Convert database row to ArtifactVersion object"""
        return ArtifactVersion.from_dict({
            'id': row[0],
            'artifact_id': row[1],
            'version_number': row[2],
            'artifact_data': row[3],
            'change_summary': row[4],
            'changed_by': row[5],
            'changed_fields': row[6],
            'created_at': row[7]
        })
    
    def update_artifact_project(self, artifact_id: str, project_id: Optional[str]) -> bool:
        """Update a single artifact's project association"""
        return self.update_artifact(artifact_id, {"project_id": project_id})