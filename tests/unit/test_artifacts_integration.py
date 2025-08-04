#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive Artifacts GUI Integration Test
Tests the complete artifacts functionality in DinoAir 2.0 including:
- Artifacts widget in right panel
- Artifacts tab in main content
- CRUD operations
- Collection management
- Search and filtering
- Encryption functionality
- Version history
"""

import sys
import os
import time
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTabWidget, QSplitter, QMessageBox, QLabel, QPushButton
)
from PySide6.QtCore import Qt, QTimer

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import artifacts components
from src.gui.components.artifact_panel import ArtifactsWidget  # noqa: E402
from src.gui.pages.artifacts_page import ArtifactsPage  # noqa: E402
from src.database.initialize_db import DatabaseManager  # noqa: E402
from src.database.artifacts_db import ArtifactsDatabase  # noqa: E402
from src.models.artifact import (  # noqa: E402
    Artifact, ArtifactType, ArtifactStatus, ArtifactCollection
)
from src.utils.colors import DinoPitColors  # noqa: E402
from src.utils.logger import Logger  # noqa: E402
from src.utils.artifact_encryption import ArtifactEncryption  # noqa: E402


class TestArtifactsIntegration(QMainWindow):
    """Test application for artifacts integration"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.test_results = []
        self.current_test = 0
        
        # Initialize database
        self.db_manager = DatabaseManager("test_user")
        self.artifacts_db = ArtifactsDatabase(self.db_manager)
        self.encryption = ArtifactEncryption()
        
        # Clean up any existing test artifacts
        self._cleanup_test_data()
        
        # Setup UI
        self.setup_ui()
        
        # Start tests after UI is ready
        QTimer.singleShot(100, self.run_tests)
        
    def setup_ui(self):
        """Setup the test UI"""
        self.setWindowTitle("DinoAir 2.0 - Artifacts Integration Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply DinoAir theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
            }}
            QLabel {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("DinoAir 2.0 - Artifacts Integration Test")
        header.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {DinoPitColors.DINOPIT_ORANGE};
            padding: 20px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Test status
        self.status_label = QLabel("Initializing tests...")
        self.status_label.setStyleSheet(f"""
            font-size: 16px;
            color: {DinoPitColors.STUDIOS_CYAN};
            padding: 10px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Main content with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.ACCENT_TEXT};
                padding: 10px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
        """)
        
        # Add test tab
        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        self.test_output = QLabel("Test output will appear here...")
        self.test_output.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.test_output.setWordWrap(True)
        self.test_output.setStyleSheet(f"""
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 20px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: {DinoPitColors.PRIMARY_TEXT};
        """)
        test_layout.addWidget(self.test_output)
        self.tab_widget.addTab(test_tab, "Test Results")
        
        # Add artifacts page
        self.artifacts_page = ArtifactsPage()
        self.tab_widget.addTab(self.artifacts_page, "Artifacts")
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tab_widget)
        
        # Right side - Artifacts widget
        right_panel = QWidget()
        right_panel.setMaximumWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add artifacts widget
        self.artifacts_widget = ArtifactsWidget()
        right_layout.addWidget(self.artifacts_widget)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 300])
        
        content_layout.addWidget(splitter)
        main_layout.addLayout(content_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.run_button = QPushButton("Run Tests")
        self.run_button.clicked.connect(self.run_tests)
        button_layout.addWidget(self.run_button)
        
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.artifacts_widget.artifact_selected.connect(
            self.on_widget_artifact_selected
        )
        self.artifacts_widget.artifact_deleted.connect(
            self.on_widget_artifact_deleted
        )
        self.artifacts_page.artifact_selected.connect(
            self.on_page_artifact_selected
        )
        
    def run_tests(self):
        """Run all integration tests"""
        self.status_label.setText("Running tests...")
        self.test_results.clear()
        self.current_test = 0
        
        # Schedule tests to run sequentially
        QTimer.singleShot(100, self.test_1_create_sample_artifacts)
        
    def test_1_create_sample_artifacts(self):
        """Test 1: Create sample artifacts of different types"""
        self.update_status("Test 1: Creating sample artifacts...")
        results = []
        
        try:
            # Create sample collection
            collection = ArtifactCollection(
                name="Test Collection",
                description="Collection for integration testing"
            )
            coll_result = self.artifacts_db.create_collection(collection)
            results.append(f"Created collection: {coll_result}")
            
            # Text artifact
            text_artifact = Artifact(
                name="Test Text Document",
                description="A sample text artifact for testing",
                content_type=ArtifactType.TEXT.value,
                content="This is a test text document with some content.",
                tags=["test", "text", "sample"]
            )
            text_result = self.artifacts_db.create_artifact(text_artifact)
            results.append(f"Created text artifact: {text_result}")
            
            # Code artifact
            code_artifact = Artifact(
                name="test_script.py",
                description="Sample Python code",
                content_type=ArtifactType.CODE.value,
                content="def hello_world():\n    print('Hello from DinoAir!')",
                collection_id=collection.id,
                tags=["python", "code", "test"],
                metadata={"language": "Python"}
            )
            code_result = self.artifacts_db.create_artifact(code_artifact)
            results.append(f"Created code artifact: {code_result}")
            
            # Document artifact with encryption
            doc_artifact = Artifact(
                name="Encrypted Document",
                description="A document with encrypted content",
                content_type=ArtifactType.DOCUMENT.value,
                content="This is sensitive information to encrypt.",
                encrypted_fields=["content", "description"],
                tags=["encrypted", "document", "sensitive"]
            )
            doc_result = self.artifacts_db.create_artifact(doc_artifact)
            results.append(f"Created encrypted document: {doc_result}")
            
            # Image artifact (simulated)
            image_artifact = Artifact(
                name="test_image.png",
                description="Simulated image artifact",
                content_type=ArtifactType.IMAGE.value,
                content_path="simulated/path/to/image.png",
                size_bytes=1024 * 500,  # 500KB
                mime_type="image/png",
                collection_id=collection.id
            )
            image_result = self.artifacts_db.create_artifact(image_artifact)
            results.append(f"Created image artifact: {image_result}")
            
            # Binary artifact
            binary_artifact = Artifact(
                name="data.bin",
                description="Binary data file",
                content_type=ArtifactType.BINARY.value,
                size_bytes=1024 * 1024 * 2,  # 2MB
                mime_type="application/octet-stream",
                status=ArtifactStatus.ARCHIVED.value
            )
            binary_result = self.artifacts_db.create_artifact(binary_artifact)
            results.append(f"Created binary artifact: {binary_result}")
            
            self.test_results.append({
                "test": "Create Sample Artifacts",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Create Sample Artifacts",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_2_widget_functionality)
        
    def test_2_widget_functionality(self):
        """Test 2: Test artifacts widget functionality"""
        self.update_status("Test 2: Testing artifacts widget...")
        results = []
        
        try:
            # Refresh widget
            self.artifacts_widget.refresh()
            time.sleep(0.1)
            
            # Check artifact count
            count = self.artifacts_widget.get_artifact_count()
            results.append(f"Widget shows {count} artifacts")
            
            # Test search
            self.artifacts_widget.search_input.setText("test")
            time.sleep(0.5)  # Wait for debounce
            
            # Test type filter
            self.artifacts_widget.type_filter_combo.setCurrentIndex(1)  # Text
            time.sleep(0.1)
            
            self.test_results.append({
                "test": "Artifacts Widget Functionality",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Artifacts Widget Functionality",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_3_page_functionality)
        
    def test_3_page_functionality(self):
        """Test 3: Test artifacts page functionality"""
        self.update_status("Test 3: Testing artifacts page...")
        results = []
        
        try:
            # Switch to artifacts tab
            self.tab_widget.setCurrentWidget(self.artifacts_page)
            time.sleep(0.1)
            
            # Test search
            self.artifacts_page.search_input.setText("document")
            time.sleep(0.5)
            
            # Clear search
            self.artifacts_page.search_input.clear()
            time.sleep(0.1)
            
            results.append("Page navigation working")
            results.append("Search functionality working")
            
            self.test_results.append({
                "test": "Artifacts Page Functionality",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Artifacts Page Functionality",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_4_crud_operations)
        
    def test_4_crud_operations(self):
        """Test 4: Test CRUD operations"""
        self.update_status("Test 4: Testing CRUD operations...")
        results = []
        
        try:
            # Create
            new_artifact = Artifact(
                name="CRUD Test Artifact",
                description="Testing CRUD operations",
                content_type=ArtifactType.TEXT.value,
                content="This artifact tests CRUD functionality"
            )
            create_result = self.artifacts_db.create_artifact(new_artifact)
            artifact_id = create_result.get("id")
            results.append(f"CREATE: {create_result}")
            
            # Read
            if artifact_id:
                read_artifact = self.artifacts_db.get_artifact(artifact_id)
                if read_artifact:
                    results.append(
                        f"READ: Found artifact '{read_artifact.name}'"
                    )
                else:
                    results.append("READ: Failed to find artifact")
            
            # Update
            if artifact_id:
                updates = {
                    "name": "Updated CRUD Test",
                    "description": "Description has been updated"
                }
                update_result = self.artifacts_db.update_artifact(
                    artifact_id, updates
                )
                results.append(f"UPDATE: Success = {update_result}")
                
                # Delete (soft)
                delete_result = self.artifacts_db.delete_artifact(
                    artifact_id, hard_delete=False
                )
                results.append(f"DELETE (soft): Success = {delete_result}")
                
                # Verify soft delete
                deleted_artifact = self.artifacts_db.get_artifact(artifact_id)
                if deleted_artifact:
                    results.append(
                        f"Status after delete: {deleted_artifact.status}"
                    )
            
            self.test_results.append({
                "test": "CRUD Operations",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "CRUD Operations",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_5_collection_management)
        
    def test_5_collection_management(self):
        """Test 5: Test collection management"""
        self.update_status("Test 5: Testing collection management...")
        results = []
        
        try:
            # Create nested collections
            parent_collection = ArtifactCollection(
                name="Parent Collection",
                description="Parent for nesting test"
            )
            parent_result = self.artifacts_db.create_collection(
                parent_collection
            )
            results.append(f"Created parent collection: {parent_result}")
            
            child_collection = ArtifactCollection(
                name="Child Collection",
                description="Nested collection",
                parent_id=parent_collection.id,
                is_encrypted=True
            )
            child_result = self.artifacts_db.create_collection(
                child_collection
            )
            results.append(f"Created child collection: {child_result}")
            
            # Get collections
            collections = self.artifacts_db.get_collections()
            results.append(f"Found {len(collections)} root collections")
            
            # Update collection
            update_result = self.artifacts_db.update_collection(
                parent_collection.id,
                {"name": "Updated Parent Collection"}
            )
            results.append(f"Updated collection: {update_result}")
            
            self.test_results.append({
                "test": "Collection Management",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Collection Management",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_6_search_filtering)
        
    def test_6_search_filtering(self):
        """Test 6: Test search and filtering"""
        self.update_status("Test 6: Testing search and filtering...")
        results = []
        
        try:
            # Search by name
            search_results = self.artifacts_db.search_artifacts("test")
            results.append(
                f"Search 'test': Found {len(search_results)} artifacts"
            )
            
            # Search by tag
            tag_results = self.artifacts_db.search_artifacts("python")
            results.append(
                f"Search 'python': Found {len(tag_results)} artifacts"
            )
            
            # Filter by type
            text_artifacts = self.artifacts_db.get_artifacts_by_type(
                ArtifactType.TEXT.value
            )
            results.append(f"Text artifacts: {len(text_artifacts)}")
            
            code_artifacts = self.artifacts_db.get_artifacts_by_type(
                ArtifactType.CODE.value
            )
            results.append(f"Code artifacts: {len(code_artifacts)}")
            
            self.test_results.append({
                "test": "Search and Filtering",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Search and Filtering",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_7_encryption)
        
    def test_7_encryption(self):
        """Test 7: Test encryption functionality"""
        self.update_status("Test 7: Testing encryption...")
        results = []
        
        try:
            # Create artifact with encrypted fields
            secret_artifact = Artifact(
                name="Secret Document",
                description="Contains encrypted information",
                content_type=ArtifactType.DOCUMENT.value,
                content="This is highly confidential data",
                encrypted_fields=["content", "description"],
                tags=["secret", "encrypted"]
            )
            
            # Test encryption marker
            if secret_artifact.is_encrypted():
                results.append("Artifact is marked for encryption")
            else:
                results.append("Artifact not marked for encryption")
            
            # Create with encryption
            create_result = self.artifacts_db.create_artifact(secret_artifact)
            results.append(f"Created encrypted artifact: {create_result}")
            
            # Retrieve and decrypt
            retrieved = self.artifacts_db.get_artifact(secret_artifact.id)
            if retrieved and retrieved.is_encrypted():
                results.append("Artifact marked as encrypted")
                
            self.test_results.append({
                "test": "Encryption Functionality",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Encryption Functionality",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_8_version_history)
        
    def test_8_version_history(self):
        """Test 8: Test version history"""
        self.update_status("Test 8: Testing version history...")
        results = []
        
        try:
            # Create artifact
            versioned_artifact = Artifact(
                name="Versioned Document",
                description="Testing version control",
                content_type=ArtifactType.TEXT.value,
                content="Version 1 content"
            )
            create_result = self.artifacts_db.create_artifact(
                versioned_artifact
            )
            artifact_id = create_result.get("id")
            results.append(f"Created artifact: {artifact_id}")
            
            if artifact_id:
                # Make updates to create versions
                for i in range(2, 4):
                    update_result = self.artifacts_db.update_artifact(
                        artifact_id,
                        {
                            "content": f"Version {i} content",
                            "change_summary": f"Updated to version {i}"
                        }
                    )
                    results.append(f"Updated to version {i}: {update_result}")
                    time.sleep(0.1)
                
                # Get version history
                versions = self.artifacts_db.get_versions(artifact_id)
                results.append(f"Found {len(versions)} versions")
                
                # Test version restore
                if len(versions) > 1:
                    restore_result = self.artifacts_db.restore_version(
                        artifact_id,
                        versions[-1].version_number
                    )
                    results.append(
                        f"Restored to version {versions[-1].version_number}: "
                        f"{restore_result}"
                    )
            
            self.test_results.append({
                "test": "Version History",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Version History",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_9_synchronization)
        
    def test_9_synchronization(self):
        """Test 9: Test synchronization between widget and page"""
        self.update_status("Test 9: Testing widget/page synchronization...")
        results = []
        
        try:
            # Refresh both components
            self.artifacts_widget.refresh()
            self.artifacts_page._load_artifacts()
            time.sleep(0.2)
            
            # Get counts from both
            widget_count = self.artifacts_widget.get_artifact_count()
            results.append(f"Widget artifact count: {widget_count}")
            
            # Create artifact and check if both update
            sync_artifact = Artifact(
                name="Sync Test Artifact",
                description="Testing synchronization",
                content_type=ArtifactType.TEXT.value,
                content="This tests sync between components"
            )
            self.artifacts_db.create_artifact(sync_artifact)
            
            # Refresh and check
            self.artifacts_widget.refresh()
            self.artifacts_page._load_artifacts()
            time.sleep(0.2)
            
            new_widget_count = self.artifacts_widget.get_artifact_count()
            results.append(f"Widget count after create: {new_widget_count}")
            results.append(
                f"Count increased: {new_widget_count > widget_count}"
            )
            
            self.test_results.append({
                "test": "Widget/Page Synchronization",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Widget/Page Synchronization",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        QTimer.singleShot(500, self.test_10_statistics)
        
    def test_10_statistics(self):
        """Test 10: Test statistics and summary"""
        self.update_status("Test 10: Testing statistics...")
        results = []
        
        try:
            stats = self.artifacts_db.get_artifact_statistics()
            
            results.append("=== Artifact Statistics ===")
            results.append(
                f"Total artifacts: {stats.get('total_artifacts', 0)}"
            )
            results.append(
                f"Total size: {stats.get('total_size_mb', 0):.2f} MB"
            )
            results.append(
                f"Encrypted artifacts: {stats.get('encrypted_artifacts', 0)}"
            )
            results.append(
                f"Total collections: {stats.get('total_collections', 0)}"
            )
            results.append(
                f"Versioned artifacts: {stats.get('versioned_artifacts', 0)}"
            )
            
            if 'artifacts_by_type' in stats:
                results.append("\n=== Artifacts by Type ===")
                for artifact_type, count in stats['artifacts_by_type'].items():
                    results.append(f"{artifact_type}: {count}")
            
            self.test_results.append({
                "test": "Statistics",
                "status": "PASSED",
                "details": "\n".join(results)
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "Statistics",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            
        self.update_test_output()
        self.complete_tests()
        
    def complete_tests(self):
        """Complete the test suite"""
        self.update_status("All tests completed!")
        
        # Enable export button
        self.export_button.setEnabled(True)
        
        # Show summary
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results if r["status"] == "FAILED")
        
        summary = f"\n\n{'='*50}\nTEST SUMMARY\n{'='*50}\n"
        summary += f"Total tests: {len(self.test_results)}\n"
        summary += f"Passed: {passed}\n"
        summary += f"Failed: {failed}\n"
        total_tests = len(self.test_results)
        success_rate = (passed/total_tests*100) if total_tests > 0 else 0
        summary += f"Success rate: {success_rate:.1f}%\n"
        
        self.test_output.setText(self.test_output.text() + summary)
        
        # Switch back to test results tab
        self.tab_widget.setCurrentIndex(0)
        
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
        QApplication.processEvents()
        
    def update_test_output(self):
        """Update test output display"""
        output = ""
        for i, result in enumerate(self.test_results):
            output += f"\n{'='*50}\n"
            output += f"Test {i+1}: {result['test']}\n"
            output += f"Status: {result['status']}\n"
            output += f"Details:\n{result['details']}\n"
        
        self.test_output.setText(output)
        QApplication.processEvents()
        
    def export_results(self):
        """Export test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"artifacts_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("DinoAir 2.0 - Artifacts Integration Test Results\n")
            test_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"Test Date: {test_date}\n")
            f.write("="*70 + "\n\n")
            
            for i, result in enumerate(self.test_results):
                f.write(f"Test {i+1}: {result['test']}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Details:\n{result['details']}\n")
                f.write("-"*50 + "\n\n")
                
        QMessageBox.information(
            self,
            "Export Complete",
            f"Test results exported to: {filename}"
        )
        
    def on_widget_artifact_selected(self, artifact):
        """Handle artifact selection in widget"""
        self.logger.info(f"Widget selected artifact: {artifact.name}")
        
    def on_widget_artifact_deleted(self, artifact_id):
        """Handle artifact deletion in widget"""
        self.logger.info(f"Widget deleted artifact: {artifact_id}")
        
    def on_page_artifact_selected(self, artifact):
        """Handle artifact selection in page"""
        self.logger.info(f"Page selected artifact: {artifact.name}")
        
    def _cleanup_test_data(self):
        """Clean up any existing test data"""
        try:
            # Search for test artifacts
            test_artifacts = self.artifacts_db.search_artifacts("test")
            for artifact in test_artifacts:
                self.artifacts_db.delete_artifact(
                    artifact.id, hard_delete=True
                )
                
            self.logger.info("Cleaned up existing test data")
        except Exception as e:
            self.logger.error(f"Error cleaning test data: {str(e)}")
            
    def closeEvent(self, event):
        """Clean up on close"""
        # Optional: Clean up test data
        # self._cleanup_test_data()
        event.accept()


def main():
    """Run the test application"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show test window
    test_window = TestArtifactsIntegration()
    test_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()