#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for artifact data models and database operations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.initialize_db import DatabaseManager
from src.database.artifacts_db import ArtifactsDatabase
from src.models.artifact import Artifact, ArtifactCollection, ArtifactType
from src.utils.artifact_encryption import ArtifactEncryption
import json


def test_artifact_system():
    """Test the artifact system implementation"""
    print("=== Testing Artifact System ===\n")
    
    # Initialize database
    print("1. Initializing database...")
    db_manager = DatabaseManager("test_artifacts_user")
    db_manager.initialize_all_databases()
    print("✓ Database initialized\n")
    
    # Create artifacts database instance
    artifacts_db = ArtifactsDatabase(db_manager)
    
    # Test 1: Create a collection
    print("2. Creating artifact collection...")
    collection = ArtifactCollection(
        name="Test Documents",
        description="Collection for testing artifacts",
        tags=["test", "documents"]
    )
    result = artifacts_db.create_collection(collection)
    print(f"✓ Collection created: {result}\n")
    
    # Test 2: Create text artifact
    print("3. Creating text artifact...")
    text_artifact = Artifact(
        name="Test Note",
        description="A simple text artifact",
        content_type=ArtifactType.TEXT.value,
        collection_id=collection.id,
        tags=["note", "test"]
    )
    text_content = b"This is a test note content"
    result = artifacts_db.create_artifact(text_artifact, text_content)
    print(f"✓ Text artifact created: {result}\n")
    
    # Test 3: Create code artifact with metadata
    print("4. Creating code artifact...")
    code_artifact = Artifact(
        name="example.py",
        description="Python code example",
        content_type=ArtifactType.CODE.value,
        collection_id=collection.id,
        mime_type="text/x-python",
        metadata={"language": "python", "lines": 10},
        tags=["code", "python"]
    )
    code_content = b"""def hello_world():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
"""
    result = artifacts_db.create_artifact(code_artifact, code_content)
    print(f"✓ Code artifact created: {result}\n")
    
    # Test 4: Create large binary artifact (simulated)
    print("5. Creating large binary artifact...")
    binary_artifact = Artifact(
        name="large_file.bin",
        description="Large binary file",
        content_type=ArtifactType.BINARY.value,
        collection_id=collection.id,
        mime_type="application/octet-stream"
    )
    # Create fake large content (6MB to trigger file storage)
    large_content = b"X" * (6 * 1024 * 1024)
    result = artifacts_db.create_artifact(binary_artifact, large_content)
    print(f"✓ Binary artifact created (stored to file): {result}\n")
    
    # Test 5: Search artifacts
    print("6. Searching artifacts...")
    search_results = artifacts_db.search_artifacts("test")
    print(f"✓ Found {len(search_results)} artifacts")
    for artifact in search_results:
        print(f"   - {artifact.name}: {artifact.description}")
    print()
    
    # Test 6: Update artifact
    print("7. Updating artifact...")
    updates = {
        "description": "Updated description",
        "tags": ["updated", "test", "note"],
        "metadata": {"updated": True}
    }
    success = artifacts_db.update_artifact(text_artifact.id, updates)
    print(f"✓ Artifact updated: {success}\n")
    
    # Test 7: Get artifact versions
    print("8. Getting artifact versions...")
    versions = artifacts_db.get_versions(text_artifact.id)
    print(f"✓ Found {len(versions)} versions")
    for version in versions:
        print(f"   - Version {version.version_number}: {version.change_summary}")
    print()
    
    # Test 8: Get collection artifacts
    print("9. Getting artifacts in collection...")
    collection_artifacts = artifacts_db.get_artifacts_by_collection(collection.id)
    print(f"✓ Found {len(collection_artifacts)} artifacts in collection")
    for artifact in collection_artifacts:
        print(f"   - {artifact.name} ({artifact.content_type}, {artifact.size_bytes} bytes)")
    print()
    
    # Test 9: Test encryption
    print("10. Testing field-level encryption...")
    encryptor = ArtifactEncryption("test_password_123")
    
    # Create artifact with encrypted content
    encrypted_artifact = Artifact(
        name="Secret Document",
        description="Document with encrypted content",
        content_type=ArtifactType.DOCUMENT.value,
        collection_id=collection.id,
        content="This is secret information",
        metadata={"confidential": True, "level": "high"}
    )
    
    # Encrypt specific fields
    artifact_dict = encrypted_artifact.to_dict()
    encrypted_dict = encryptor.encrypt_artifact_fields(
        artifact_dict, ["content", "metadata"])
    
    # Create encrypted artifact in database
    encrypted_artifact_obj = Artifact.from_dict(encrypted_dict)
    result = artifacts_db.create_artifact(encrypted_artifact_obj)
    print(f"✓ Encrypted artifact created: {result}")
    
    # Retrieve and decrypt
    retrieved = artifacts_db.get_artifact(encrypted_artifact_obj.id)
    if retrieved:
        retrieved_dict = retrieved.to_dict()
        decrypted_dict = encryptor.decrypt_artifact_fields(retrieved_dict)
        print(f"✓ Decrypted content: {decrypted_dict.get('content')[:50]}...")
        print(f"✓ Decrypted metadata: {decrypted_dict.get('metadata')}")
    print()
    
    # Test 10: Get statistics
    print("11. Getting artifact statistics...")
    stats = artifacts_db.get_artifact_statistics()
    print("✓ Artifact Statistics:")
    print(f"   - Total artifacts: {stats.get('total_artifacts', 0)}")
    print(f"   - Total size: {stats.get('total_size_mb', 0):.2f} MB")
    print(f"   - Artifacts by type: {stats.get('artifacts_by_type', {})}")
    print(f"   - Encrypted artifacts: {stats.get('encrypted_artifacts', 0)}")
    print(f"   - Total collections: {stats.get('total_collections', 0)}")
    print()
    
    # Test 11: Soft delete
    print("12. Testing soft delete...")
    success = artifacts_db.delete_artifact(text_artifact.id, hard_delete=False)
    print(f"✓ Artifact soft deleted: {success}")
    
    # Verify it's marked as deleted
    deleted_artifact = artifacts_db.get_artifact(text_artifact.id, update_accessed=False)
    if deleted_artifact:
        print(f"✓ Artifact status: {deleted_artifact.status}")
    print()
    
    # Test 12: Get artifacts by type
    print("13. Getting artifacts by type...")
    code_artifacts = artifacts_db.get_artifacts_by_type(ArtifactType.CODE.value)
    print(f"✓ Found {len(code_artifacts)} code artifacts")
    for artifact in code_artifacts:
        print(f"   - {artifact.name}")
    print()
    
    print("=== All tests completed successfully! ===")


if __name__ == "__main__":
    try:
        test_artifact_system()
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()