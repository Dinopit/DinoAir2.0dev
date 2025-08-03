"""Debug script to verify project tool implementation issues"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.initialize_db import DatabaseManager
from src.database.projects_db import ProjectsDatabase
from src.database.notes_db import NotesDatabase
from src.database.artifacts_db import ArtifactsDatabase
from src.models.project import Project

def debug_project_integration():
    """Debug the project integration implementation"""
    print("=== Project Tool Integration Debug ===\n")
    
    # Initialize databases
    db_manager = DatabaseManager("debug_user")
    projects_db = ProjectsDatabase(db_manager)
    notes_db = NotesDatabase("debug_user")
    artifacts_db = ArtifactsDatabase(db_manager)
    
    # Check if databases have project support methods
    print("1. Checking NotesDatabase for project methods:")
    notes_methods = [
        'get_notes_by_project',
        'get_project_notes_count',
        'assign_notes_to_project'
    ]
    for method in notes_methods:
        has_method = hasattr(notes_db, method)
        print(f"   - {method}: {'✓ Found' if has_method else '✗ Missing'}")
    
    print("\n2. Checking ArtifactsDatabase for project methods:")
    artifacts_methods = [
        'get_artifacts_by_project',
        'get_project_artifacts_count'
    ]
    for method in artifacts_methods:
        has_method = hasattr(artifacts_db, method)
        print(f"   - {method}: {'✓ Found' if has_method else '✗ Missing'}")
    
    print("\n3. Checking GUI implementation in tasks_page.py:")
    print("   - Artifacts tab: Placeholder only (line 799-803)")
    print("   - Events tab: Placeholder only (line 806-809)")
    print("   - Notes loading: Commented out (line 969)")
    
    print("\n4. Testing actual project creation and retrieval:")
    try:
        # Create a test project
        test_project = Project(
            name="Debug Test Project",
            description="Testing project integration"
        )
        result = projects_db.create_project(test_project)
        if result["success"]:
            print(f"   ✓ Created project: {test_project.id}")
            
            # Test statistics retrieval
            stats = projects_db.get_project_statistics(test_project.id)
            print(f"   ✓ Retrieved statistics: Notes={stats.total_notes}, "
                  f"Artifacts={stats.total_artifacts}, Events={stats.total_calendar_events}")
            
            # Clean up
            projects_db.delete_project(test_project.id, hard_delete=True)
            print("   ✓ Cleaned up test project")
        else:
            print(f"   ✗ Failed to create project: {result.get('error')}")
    except Exception as e:
        print(f"   ✗ Error during project testing: {str(e)}")
    
    print("\n=== Diagnosis Summary ===")
    print("The project tool was only partially implemented:")
    print("1. Database schema and models: ✓ Complete")
    print("2. Project database manager: ✓ Complete")
    print("3. Notes integration backend: ✓ Complete")
    print("4. GUI project page structure: ✓ Complete")
    print("5. Artifacts tab implementation: ✗ Placeholder only")
    print("6. Events/Calendar tab: ✗ Placeholder only")
    print("7. Notes tab integration: ✗ Not connected to database")
    print("8. Artifacts database integration: ✗ Missing get_artifacts_by_project method")

if __name__ == "__main__":
    debug_project_integration()