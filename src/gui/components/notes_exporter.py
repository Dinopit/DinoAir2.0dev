"""
Notes Exporter - Handles exporting notes in various formats
"""

import os
import re
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize
from datetime import datetime as dt

from src.models.note import Note
from src.utils.logger import Logger
from src.utils.colors import DinoPitColors
from src.gui.components.notes_security import get_notes_security


class NotesExporter(QObject):
    """Handles exporting notes in various formats.
    
    Supported formats:
    - HTML (single note with styling)
    - TXT (plain text)
    - PDF (if supported by PyQt6)
    - ZIP (all notes with organized structure)
    """
    
    # Signals
    export_started = Signal()
    export_progress = Signal(int, int)  # current, total
    export_completed = Signal(str)  # export path
    export_failed = Signal(str)  # error message
    
    def __init__(self, parent=None):
        """Initialize the notes exporter."""
        super().__init__(parent)
        self.logger = Logger()
        self._security = get_notes_security()
        self._last_export_dir = str(Path.home())
        
    def export_note_as_html(
        self, note: Note, parent_widget=None
    ) -> Optional[str]:
        """Export a single note as HTML file.
        
        Args:
            note: The note to export
            parent_widget: Parent widget for file dialog
            
        Returns:
            Path to exported file or None if cancelled/failed
        """
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Note as HTML",
            os.path.join(
                self._last_export_dir,
                self._sanitize_filename(f"{note.title}.html")
            ),
            "HTML Files (*.html);;All Files (*)"
        )
        
        if not file_path:
            return None
            
        try:
            self.export_started.emit()
            
            # Remember export directory
            self._last_export_dir = os.path.dirname(file_path)
            
            # Generate HTML content
            html_content = self._generate_html_content(note)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"Exported note as HTML: {file_path}")
            self.export_completed.emit(file_path)
            
            # Show success message
            if parent_widget:
                QMessageBox.information(
                    parent_widget,
                    "Export Successful",
                    f"Note exported successfully to:\n{file_path}"
                )
                
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to export note as HTML: {str(e)}"
            self.logger.error(error_msg)
            self.export_failed.emit(error_msg)
            
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "Export Error",
                    error_msg
                )
                
            return None
            
    def export_note_as_txt(
        self, note: Note, parent_widget=None
    ) -> Optional[str]:
        """Export a single note as plain text file.
        
        Args:
            note: The note to export
            parent_widget: Parent widget for file dialog
            
        Returns:
            Path to exported file or None if cancelled/failed
        """
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Note as Text",
            os.path.join(
                self._last_export_dir,
                self._sanitize_filename(f"{note.title}.txt")
            ),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return None
            
        try:
            self.export_started.emit()
            
            # Remember export directory
            self._last_export_dir = os.path.dirname(file_path)
            
            # Generate text content
            text_content = self._generate_text_content(note)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
                
            self.logger.info(f"Exported note as TXT: {file_path}")
            self.export_completed.emit(file_path)
            
            # Show success message
            if parent_widget:
                QMessageBox.information(
                    parent_widget,
                    "Export Successful",
                    f"Note exported successfully to:\n{file_path}"
                )
                
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to export note as text: {str(e)}"
            self.logger.error(error_msg)
            self.export_failed.emit(error_msg)
            
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "Export Error",
                    error_msg
                )
                
            return None
            
    def export_note_as_pdf(
        self, note: Note, parent_widget=None
    ) -> Optional[str]:
        """Export a single note as PDF file.
        
        Args:
            note: The note to export
            parent_widget: Parent widget for file dialog
            
        Returns:
            Path to exported file or None if cancelled/failed
        """
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Note as PDF",
            os.path.join(
                self._last_export_dir,
                self._sanitize_filename(f"{note.title}.pdf")
            ),
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not file_path:
            return None
            
        try:
            self.export_started.emit()
            
            # Remember export directory
            self._last_export_dir = os.path.dirname(file_path)
            
            # Create PDF writer
            pdf_writer = QPdfWriter(file_path)
            pdf_writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            # Set resolution
            pdf_writer.setResolution(300)
            
            # Create text document with HTML content
            document = QTextDocument()
            
            # Generate HTML content for PDF
            html_content = self._generate_pdf_html_content(note)
            document.setHtml(html_content)
            
            # Print to PDF
            document.print_(pdf_writer)
            
            self.logger.info(f"Exported note as PDF: {file_path}")
            self.export_completed.emit(file_path)
            
            # Show success message
            if parent_widget:
                QMessageBox.information(
                    parent_widget,
                    "Export Successful",
                    f"Note exported successfully to:\n{file_path}"
                )
                
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to export note as PDF: {str(e)}"
            self.logger.error(error_msg)
            self.export_failed.emit(error_msg)
            
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "Export Error",
                    error_msg
                )
                
            return None
            
    def export_all_notes(
        self, notes: List[Note], parent_widget=None
    ) -> Optional[str]:
        """Export all notes as a ZIP archive.
        
        Args:
            notes: List of notes to export
            parent_widget: Parent widget for file dialog
            
        Returns:
            Path to exported ZIP file or None if cancelled/failed
        """
        if not notes:
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "No Notes",
                    "There are no notes to export."
                )
            return None
            
        # Get save path
        export_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export All Notes",
            os.path.join(
                self._last_export_dir,
                f"notes_export_{export_date}.zip"
            ),
            "ZIP Files (*.zip);;All Files (*)"
        )
        
        if not file_path:
            return None
            
        # Create progress dialog
        progress = QProgressDialog(
            "Exporting notes...",
            "Cancel",
            0,
            len(notes) * 2 + 2,  # HTML + TXT + index + manifest
            parent_widget
        )
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress_value = 0
        
        try:
            self.export_started.emit()
            
            # Remember export directory
            self._last_export_dir = os.path.dirname(file_path)
            
            # Create ZIP file
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Create folder structure
                base_folder = f"notes_export_{export_date}"
                
                # Export manifest
                manifest = self._create_export_manifest(notes)
                zipf.writestr(
                    f"{base_folder}/manifest.json",
                    json.dumps(manifest, indent=2, ensure_ascii=False)
                )
                progress_value += 1
                progress.setValue(progress_value)
                
                # Create index.html
                index_html = self._create_index_html(notes, base_folder)
                zipf.writestr(f"{base_folder}/index.html", index_html)
                progress_value += 1
                progress.setValue(progress_value)
                
                # Export each note
                for i, note in enumerate(notes):
                    if progress.wasCanceled():
                        os.remove(file_path)
                        return None
                        
                    # Sanitize filename
                    safe_filename = self._sanitize_filename(note.title)
                    
                    # Export as HTML
                    html_content = self._generate_html_content(note)
                    zipf.writestr(
                        f"{base_folder}/html/{safe_filename}.html",
                        html_content
                    )
                    progress_value += 1
                    progress.setValue(progress_value)
                    self.export_progress.emit(i * 2 + 1, len(notes) * 2)
                    
                    # Export as TXT
                    txt_content = self._generate_text_content(note)
                    zipf.writestr(
                        f"{base_folder}/txt/{safe_filename}.txt",
                        txt_content
                    )
                    progress_value += 1
                    progress.setValue(progress_value)
                    self.export_progress.emit(i * 2 + 2, len(notes) * 2)
                    
            progress.close()
            
            self.logger.info(f"Exported all notes to ZIP: {file_path}")
            self.export_completed.emit(file_path)
            
            # Show success message
            if parent_widget:
                QMessageBox.information(
                    parent_widget,
                    "Export Successful",
                    f"All notes exported successfully to:\n{file_path}"
                )
                
            return file_path
            
        except Exception as e:
            progress.close()
            error_msg = f"Failed to export notes: {str(e)}"
            self.logger.error(error_msg)
            self.export_failed.emit(error_msg)
            
            # Clean up partial file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                    
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "Export Error",
                    error_msg
                )
                
            return None
            
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
            
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Default if empty
        if not filename:
            filename = "untitled"
            
        return filename
        
    def _generate_html_content(self, note: Note) -> str:
        """Generate HTML content for a note.
        
        Args:
            note: The note to convert to HTML
            
        Returns:
            HTML string
        """
        # Format dates (parse ISO format strings)
        created_dt = dt.fromisoformat(note.created_at.replace('Z', '+00:00'))
        updated_dt = dt.fromisoformat(note.updated_at.replace('Z', '+00:00'))
        created_date = created_dt.strftime("%B %d, %Y at %I:%M %p")
        updated_date = updated_dt.strftime("%B %d, %Y at %I:%M %p")
        
        # Format tags
        tags_html = ""
        if note.tags:
            tags_html = ", ".join(
                f'<span class="tag">{tag}</span>'
                for tag in note.tags
            )
            
        # Get content
        # Check if note has HTML content (from database)
        content_html = getattr(note, 'content_html', None)
        if not content_html:
            # Convert plain text to HTML
            content_html = self._plain_text_to_html(note.content)
            
        # Generate complete HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._security.sanitize_note_title(note.title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .note-container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        h1 {{
            color: #1a1a1a;
            margin-bottom: 10px;
            font-size: 28px;
            border-bottom: 2px solid {DinoPitColors.DINOPIT_ORANGE};
            padding-bottom: 10px;
        }}
        
        .metadata {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }}
        
        .metadata p {{
            margin: 5px 0;
        }}
        
        .tags {{
            margin-top: 10px;
        }}
        
        .tag {{
            display: inline-block;
            background-color: {DinoPitColors.SOFT_ORANGE};
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-right: 5px;
        }}
        
        .content {{
            margin-top: 30px;
            font-size: 16px;
            line-height: 1.8;
        }}
        
        .content p {{
            margin-bottom: 15px;
        }}
        
        .content ul, .content ol {{
            margin-bottom: 15px;
            padding-left: 30px;
        }}
        
        .content li {{
            margin-bottom: 5px;
        }}
        
        .content blockquote {{
            border-left: 4px solid {DinoPitColors.DINOPIT_ORANGE};
            padding-left: 15px;
            margin: 15px 0;
            color: #666;
            font-style: italic;
        }}
        
        .content code {{
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
        }}
        
        .content pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        
        .content pre code {{
            background-color: transparent;
            padding: 0;
        }}
        
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            
            .note-container {{
                box-shadow: none;
                padding: 0;
            }}
            
            .metadata {{
                background-color: #f0f0f0;
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    <div class="note-container">
        <h1>{self._security.sanitize_note_title(note.title)}</h1>
        
        <div class="metadata">
            <p><strong>Created:</strong> {created_date}</p>
            <p><strong>Last Updated:</strong> {updated_date}</p>
            {f'<div class="tags"><strong>Tags:</strong> '
             f'{tags_html}</div>' if tags_html else ''}
        </div>
        
        <div class="content">
            {content_html}
        </div>
    </div>
</body>
</html>"""
        
        return html
        
    def _format_date(self, note: Note) -> str:
        """Format note created date for display.
        
        Args:
            note: Note with created_at timestamp
            
        Returns:
            Formatted date string
        """
        try:
            # Parse ISO format date
            created = dt.fromisoformat(
                note.created_at.replace('Z', '+00:00')
            )
            return created.strftime("%B %d, %Y")
        except Exception:
            return "Unknown date"
        
    def _generate_pdf_html_content(self, note: Note) -> str:
        """Generate HTML content optimized for PDF export.
        
        Args:
            note: The note to convert
            
        Returns:
            HTML string optimized for PDF
        """
        # Similar to HTML export but with PDF-specific optimizations
        html_content = self._generate_html_content(note)
        
        # Modify styles for better PDF rendering
        html_content = html_content.replace(
            "max-width: 800px;",
            "max-width: 100%;"
        ).replace(
            "margin: 0 auto;",
            "margin: 0;"
        ).replace(
            "padding: 20px;",
            "padding: 0;"
        ).replace(
            "background-color: #f5f5f5;",
            "background-color: white;"
        )
        
        return html_content
        
    def _generate_text_content(self, note: Note) -> str:
        """Generate plain text content for a note.
        
        Args:
            note: The note to convert to text
            
        Returns:
            Plain text string
        """
        # Format dates (parse ISO format strings)
        created_dt = dt.fromisoformat(note.created_at.replace('Z', '+00:00'))
        updated_dt = dt.fromisoformat(note.updated_at.replace('Z', '+00:00'))
        created_date = created_dt.strftime("%B %d, %Y at %I:%M %p")
        updated_date = updated_dt.strftime("%B %d, %Y at %I:%M %p")
        
        # Build text content
        lines = [
            "=" * 60,
            note.title.upper(),
            "=" * 60,
            "",
            f"Created: {created_date}",
            f"Last Updated: {updated_date}",
        ]
        
        if note.tags:
            lines.append(f"Tags: {', '.join(note.tags)}")
            
        lines.extend([
            "",
            "-" * 60,
            "",
            note.content,
            "",
            "-" * 60
        ])
        
        return "\n".join(lines)
        
    def _plain_text_to_html(self, text: str) -> str:
        """Convert plain text to HTML with basic formatting.
        
        Args:
            text: Plain text content
            
        Returns:
            HTML formatted text
        """
        # Escape HTML characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Convert line breaks to paragraphs
        paragraphs = text.split('\n\n')
        html_paragraphs = []
        
        for para in paragraphs:
            if para.strip():
                # Convert single line breaks to <br>
                para = para.replace('\n', '<br>')
                html_paragraphs.append(f"<p>{para}</p>")
                
        return "\n".join(html_paragraphs)
        
    def _create_export_manifest(self, notes: List[Note]) -> Dict[str, Any]:
        """Create a manifest file for the export.
        
        Args:
            notes: List of exported notes
            
        Returns:
            Manifest dictionary
        """
        return {
            "export_date": datetime.now().isoformat(),
            "export_version": "1.0",
            "total_notes": len(notes),
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at,
                    "tags": note.tags,
                    "filename": self._sanitize_filename(note.title)
                }
                for note in notes
            ]
        }
        
    def _create_index_html(self, notes: List[Note], base_folder: str) -> str:
        """Create an index.html file with links to all notes.
        
        Args:
            notes: List of notes
            base_folder: Base folder name in the ZIP
            
        Returns:
            HTML string for index
        """
        # Sort notes by title
        sorted_notes = sorted(notes, key=lambda n: n.title.lower())
        
        # Generate note links
        note_links = []
        for note in sorted_notes:
            safe_filename = self._sanitize_filename(note.title)
            tags_html = ""
            if note.tags:
                tags_html = " - " + ", ".join(
                    f'<span class="tag">'
                    f'{self._security.sanitize_tag(tag)}</span>'
                    for tag in note.tags
                )
                
            note_links.append(
                f'<li>'
                f'<a href="html/{safe_filename}.html">'
                f'{self._security.sanitize_note_title(note.title)}</a>'
                f'{tags_html}'
                f'<span class="date"> ({self._format_date(note)})</span>'
                f'</li>'
            )
            
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notes Export - Index</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        h1 {{
            color: #1a1a1a;
            border-bottom: 2px solid {DinoPitColors.DINOPIT_ORANGE};
            padding-bottom: 10px;
        }}
        
        .export-info {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        
        ul {{
            list-style-type: none;
            padding: 0;
        }}
        
        li {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            transition: background-color 0.2s;
        }}
        
        li:hover {{
            background-color: #f9f9f9;
        }}
        
        a {{
            color: {DinoPitColors.DINOPIT_ORANGE};
            text-decoration: none;
            font-weight: 500;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .tag {{
            display: inline-block;
            background-color: {DinoPitColors.SOFT_ORANGE};
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin: 0 2px;
        }}
        
        .date {{
            color: #999;
            font-size: 14px;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 Notes Export</h1>
        
        <div class="export-info">
            <p><strong>Export Date:</strong>
            {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            <p><strong>Total Notes:</strong> {len(notes)}</p>
            <p>Click on any note title to view it.
            Notes are available in both HTML and TXT formats.</p>
        </div>
        
        <h2>All Notes</h2>
        <ul>
            {"".join(note_links)}
        </ul>
    </div>
</body>
</html>"""
        
        return html