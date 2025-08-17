"""
Artifacts Service
Thin, testable wrapper around ArtifactsDatabase and ProjectsDatabase with simple caching.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from time import monotonic

from src.database.initialize_db import DatabaseManager
from src.database.artifacts_db import ArtifactsDatabase
from src.database.projects_db import ProjectsDatabase
from src.models.artifact import Artifact, ArtifactCollection
from src.utils.logger import Logger


class ArtifactsService:
    """Service for artifacts, with project link helpers and caching."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        artifacts_db: Optional[ArtifactsDatabase] = None,
        projects_db: Optional[ProjectsDatabase] = None,
        cache_ttl_sec: float = 5.0,
    ):
        self.logger = Logger()
        self._db_manager = db_manager or DatabaseManager()
        self._artifacts_db = artifacts_db or ArtifactsDatabase(self._db_manager)
        self._projects_db = projects_db or ProjectsDatabase(self._db_manager)
        self._cache_ttl = cache_ttl_sec
        self._cache_time = 0.0
        self._cache_all: Optional[List[Artifact]] = None
        self._collections_cache: Optional[List[ArtifactCollection]] = None

    def _is_cache_valid(self) -> bool:
        return self._cache_all is not None and (monotonic() - self._cache_time) < self._cache_ttl

    def _invalidate(self) -> None:
        self._cache_all = None
        self._collections_cache = None
        self._cache_time = 0.0

    # Public hook for GUI to refresh immediately after mutations
    def invalidate_cache(self) -> None:
        self._invalidate()

    def get_all_artifacts(self, limit: int = 1000) -> List[Artifact]:
        """Return all non-deleted artifacts, up to a limit.

        Uses a short TTL cache to avoid repeated DB scans during quick UI refreshes.
        """
        try:
            if self._is_cache_valid():
                return list(self._cache_all or [])
            data = self._artifacts_db.search_artifacts("", limit=limit)
            self._cache_all = list(data)
            self._cache_time = monotonic()
            return list(self._cache_all)
        except Exception as e:
            self.logger.error(f"Failed to get artifacts: {e}")
            return []

    def get_collections(self) -> List[ArtifactCollection]:
        """Return root-level collections.

        Mirrors ArtifactsDatabase.get_collections(parent_id=None).
        """
        if self._collections_cache is not None:
            return list(self._collections_cache)
        try:
            cols = self._artifacts_db.get_collections(parent_id=None)
            self._collections_cache = list(cols)
            return list(self._collections_cache)
        except Exception as e:
            self.logger.error(f"Failed to get collections: {e}")
            return []

    def create_collection(self, collection: ArtifactCollection) -> Dict[str, Any]:
        """Create a collection and invalidate caches."""
        try:
            result = self._artifacts_db.create_collection(collection)
            self._invalidate()
            return result
        except Exception as e:
            self.logger.error(f"Failed to create collection: {e}")
            return {"success": False, "error": str(e)}

    def update_collection(self, collection_id: str, updates: Dict[str, Any]) -> bool:
        """Update a collection and invalidate caches."""
        try:
            ok = self._artifacts_db.update_collection(collection_id, updates)
            if ok:
                self._invalidate()
            return ok
        except Exception as e:
            self.logger.error(f"Failed to update collection: {e}")
            return False

    def get_artifacts_by_project(self, project_id: str) -> List[Artifact]:
        try:
            return self._artifacts_db.get_artifacts_by_project(project_id)
        except Exception as e:
            self.logger.error(f"Failed to get artifacts by project: {e}")
            return []

    def link_artifact_to_project(self, artifact_id: str, project_id: Optional[str]) -> bool:
        # Keep logic out of GUI and minimal here.
        ok = self._artifacts_db.update_artifact(artifact_id, {"project_id": project_id})
        self._invalidate()
        return ok

    def create_artifact(self, artifact: Artifact, content_bytes: Optional[bytes] = None) -> Dict[str, Any]:
        result = self._artifacts_db.create_artifact(artifact, content_bytes)
        self._invalidate()
        return result

    def update_artifact(
        self,
        artifact_id: str,
        updates: Dict[str, Any],
        content_bytes: Optional[bytes] = None,
    ) -> bool:
        ok = self._artifacts_db.update_artifact(artifact_id, updates, content_bytes)
        self._invalidate()
        return ok

    def delete_artifact(self, artifact_id: str) -> bool:
        ok = self._artifacts_db.delete_artifact(artifact_id)
        self._invalidate()
        return ok
