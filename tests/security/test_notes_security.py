"""
Security test cases for DinoAir 2.0 Notes feature.
Tests for XSS, SQL injection, and other security vulnerabilities.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.notes_db import NotesDatabase
from src.models.note import Note
from src.input_processing.input_sanitizer import InputPipeline
from src.input_processing.stages.enhanced_sanitizer import EnhancedInputSanitizer


class TestNotesSecurityVulnerabilities:
    """Security test cases for Notes feature."""
    
    @pytest.fixture
    def notes_db(self, tmp_path):
        """Create a test database instance."""
        # Use temporary database for testing
        test_user = f"test_user_{tmp_path.name}"
        return NotesDatabase(test_user)
    
    @pytest.fixture
    def input_pipeline(self):
        """Create input pipeline for sanitization."""
        return InputPipeline(
            gui_feedback_hook=lambda msg: None,
            enable_enhanced_security=True
        )
    
    @pytest.fixture
    def enhanced_sanitizer(self):
        """Create enhanced sanitizer instance."""
        return EnhancedInputSanitizer()
    
    # XSS Attack Tests
    def test_xss_in_note_title(self, notes_db, enhanced_sanitizer):
        """Test XSS prevention in note titles."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<body onload=alert('XSS')>",
        ]
        
        for payload in xss_payloads:
            # Sanitize the payload
            sanitized_title = enhanced_sanitizer.sanitize_input(
                payload, 
                context='plain'
            )
            
            # Create note with sanitized title
            note = Note(
                title=sanitized_title,
                content="Test content",
                tags=[]
            )
            
            result = notes_db.create_note(note)
            assert result["success"]
            
            # Verify stored title is sanitized
            retrieved_note = notes_db.get_note(note.id)
            assert retrieved_note is not None
            assert "<script>" not in retrieved_note.title
            assert "alert(" not in retrieved_note.title
            assert "onerror=" not in retrieved_note.title
            assert "javascript:" not in retrieved_note.title
    
    def test_xss_in_note_content(self, notes_db, enhanced_sanitizer):
        """Test XSS prevention in note content."""
        xss_content = """
        Hello <script>alert('XSS')</script>
        <img src=x onerror=alert('XSS')>
        <iframe src="javascript:alert('XSS')"></iframe>
        """
        
        # Sanitize content
        sanitized_content = enhanced_sanitizer.sanitize_input(
            xss_content,
            context='plain'
        )
        
        note = Note(
            title="Test Note",
            content=sanitized_content,
            tags=[]
        )
        
        result = notes_db.create_note(note)
        assert result["success"]
        
        # Verify content is sanitized
        retrieved_note = notes_db.get_note(note.id)
        assert "<script>" not in retrieved_note.content
        assert "onerror=" not in retrieved_note.content
    
    def test_xss_in_tags(self, notes_db, enhanced_sanitizer):
        """Test XSS prevention in tags."""
        xss_tags = [
            "<script>alert('XSS')</script>",
            "tag<img src=x onerror=alert(1)>",
            "javascript:alert('XSS')",
            "</tag><script>alert('XSS')</script>",
        ]
        
        # Sanitize tags
        sanitized_tags = [
            enhanced_sanitizer.sanitize_input(tag, context='plain')
            for tag in xss_tags
        ]
        
        note = Note(
            title="Test Note",
            content="Test content",
            tags=sanitized_tags
        )
        
        result = notes_db.create_note(note)
        assert result["success"]
        
        # Verify tags are sanitized
        retrieved_note = notes_db.get_note(note.id)
        for tag in retrieved_note.tags:
            assert "<script>" not in tag
            assert "alert(" not in tag
            assert "javascript:" not in tag
    
    # SQL Injection Tests
    def test_sql_injection_in_search(self, notes_db, enhanced_sanitizer):
        """Test SQL injection prevention in search."""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE note_list; --",
            "' UNION SELECT * FROM note_list --",
            "1' AND SLEEP(5) --",
            "' OR 1=1 --",
            "'; DELETE FROM note_list; --",
            "' OR 'x'='x",
            "1' ORDER BY 1--",
            "1' GROUP BY 1 HAVING 1=1--",
        ]
        
        # Create a test note
        test_note = Note(
            title="Test Note",
            content="Test content for search",
            tags=["test"]
        )
        notes_db.create_note(test_note)
        
        for payload in sql_payloads:
            # Sanitize search query
            sanitized_query = enhanced_sanitizer.sanitize_input(
                payload,
                context='sql'
            )
            
            # Search should not cause SQL errors
            try:
                results = notes_db.search_notes(sanitized_query)
                # Search should complete without SQL injection
                assert isinstance(results, list)
            except Exception as e:
                # Should not raise SQL syntax errors
                assert "SQL" not in str(e)
    
    def test_sql_injection_in_tag_search(self, notes_db, enhanced_sanitizer):
        """Test SQL injection in tag search."""
        # Create note with tag
        note = Note(
            title="Test",
            content="Test",
            tags=["testtag"]
        )
        notes_db.create_note(note)
        
        # Try SQL injection in tag search
        sql_tag = "'; DROP TABLE note_list; --"
        sanitized_tag = enhanced_sanitizer.sanitize_input(
            sql_tag,
            context='sql'
        )
        
        # Should not cause SQL injection
        results = notes_db.get_notes_by_tag(sanitized_tag)
        assert isinstance(results, list)
        assert len(results) == 0  # No notes should match the injection attempt
    
    # Unicode Attack Tests
    def test_unicode_normalization_attack(self, notes_db, enhanced_sanitizer):
        """Test Unicode normalization attack prevention."""
        unicode_payloads = [
            "аdmin",  # Cyrillic 'а' instead of Latin 'a'
            "adm\u0131n",  # Turkish dotless i
            "ad\u2060min",  # Word joiner
            "admin\u200b",  # Zero-width space
            "ad\ufeffmin",  # Zero-width no-break space
            "ａｄｍｉｎ",  # Full-width characters
        ]
        
        for payload in unicode_payloads:
            # Sanitize with Unicode protection
            sanitized = enhanced_sanitizer.sanitize_input(
                payload,
                allow_unicode=False
            )
            
            note = Note(
                title=sanitized,
                content="Test",
                tags=[]
            )
            
            result = notes_db.create_note(note)
            assert result["success"]
            
            # Verify normalization
            retrieved_note = notes_db.get_note(note.id)
            # Should be normalized or converted to ASCII
            assert retrieved_note.title != payload or not any(ord(c) > 127 for c in retrieved_note.title)
    
    # Path Traversal Tests (for potential future file operations)
    def test_path_traversal_in_content(self, notes_db, enhanced_sanitizer):
        """Test path traversal pattern detection."""
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\cmd.exe",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
        ]
        
        for payload in path_payloads:
            sanitized = enhanced_sanitizer.sanitize_input(
                payload,
                context='general'
            )
            
            # Path traversal sequences should be removed
            assert "../" not in sanitized
            assert "..\\" not in sanitized
            assert "%2e" not in sanitized.lower()
            assert "%2f" not in sanitized.lower()
    
    # Command Injection Tests
    def test_command_injection_prevention(self, notes_db, enhanced_sanitizer):
        """Test command injection prevention."""
        command_payloads = [
            "; whoami",
            "| ls -la",
            "& net user",
            "`id`",
            "$(whoami)",
            "; rm -rf /",
            "|| ping -c 10 127.0.0.1",
        ]
        
        for payload in command_payloads:
            sanitized = enhanced_sanitizer.sanitize_input(
                payload,
                context='general'
            )
            
            # Command separators should be removed
            assert ";" not in sanitized
            assert "|" not in sanitized
            assert "&" not in sanitized
            assert "`" not in sanitized
            assert "$(" not in sanitized
    
    # Combined Attack Tests
    def test_combined_xss_sql_attack(self, notes_db, enhanced_sanitizer):
        """Test combined XSS and SQL injection attack."""
        combined_payload = "'; DROP TABLE users; <script>alert('XSS')</script>--"
        
        # Sanitize for both contexts
        sanitized = enhanced_sanitizer.sanitize_input(
            combined_payload,
            context='general'
        )
        
        note = Note(
            title=sanitized,
            content=sanitized,
            tags=[sanitized]
        )
        
        result = notes_db.create_note(note)
        assert result["success"]
        
        # Verify both attack vectors are neutralized
        retrieved_note = notes_db.get_note(note.id)
        assert "DROP TABLE" not in retrieved_note.title
        assert "<script>" not in retrieved_note.title
        assert ";" not in retrieved_note.title
    
    # Input Length and DoS Tests
    def test_large_input_dos_prevention(self, notes_db, enhanced_sanitizer):
        """Test prevention of DoS through large inputs."""
        # Create very large input
        large_content = "A" * 1000000  # 1MB of data
        
        # Sanitize with max length
        sanitized = enhanced_sanitizer.sanitize_input(
            large_content,
            max_length=10000  # Limit to 10KB
        )
        
        assert len(sanitized) <= 10000
        
        note = Note(
            title="Large Note",
            content=sanitized,
            tags=[]
        )
        
        # Should handle large input gracefully
        result = notes_db.create_note(note)
        assert result["success"]
    
    # Tag Injection Tests
    def test_tag_injection_attacks(self, notes_db, enhanced_sanitizer):
        """Test various injection attacks through tags."""
        injection_tags = [
            '","malicious":"data"',  # JSON injection
            'tag1","tag2"],"extra":"data',  # JSON structure break
            'a' * 1000,  # Long tag
            '',  # Empty tag
            ' ',  # Whitespace tag
            '\n\r\t',  # Control characters
        ]
        
        for tag in injection_tags:
            sanitized_tag = enhanced_sanitizer.sanitize_input(
                tag,
                context='plain',
                max_length=50
            )
            
            if sanitized_tag.strip():  # Only test non-empty tags
                note = Note(
                    title="Test",
                    content="Test",
                    tags=[sanitized_tag]
                )
                
                result = notes_db.create_note(note)
                assert result["success"]
                
                # Verify tag is stored safely
                retrieved_note = notes_db.get_note(note.id)
                assert len(retrieved_note.tags[0]) <= 50
    
    # Integration Tests
    def test_full_pipeline_integration(self, input_pipeline):
        """Test full input pipeline integration with Notes."""
        test_inputs = [
            "<script>alert('XSS')</script>Note Title",
            "'; DROP TABLE notes; --",
            "Normal note with некоторые Unicode",
            "../../../etc/passwd",
            "Test & Command | Injection ; Attack",
        ]
        
        for raw_input in test_inputs:
            try:
                # Process through pipeline
                sanitized, intent = input_pipeline.run(raw_input)
                
                # Should process without raising security exceptions
                assert isinstance(sanitized, str)
                
                # Should not contain dangerous patterns
                assert "<script>" not in sanitized
                assert "DROP TABLE" not in sanitized
                assert "../" not in sanitized
                assert ";" not in sanitized or intent.name == "COMMAND"
                
            except Exception as e:
                # Only InputPipelineError for rate limiting is acceptable
                assert "rate limit" in str(e).lower()


class TestNotesSecurityIntegration:
    """Integration tests for Notes security with GUI components."""
    
    def test_search_widget_sanitization(self, enhanced_sanitizer):
        """Test search widget input sanitization."""
        from src.gui.components.notes_search import NotesSearchWidget
        
        # Mock the search widget behavior
        search_queries = [
            "<script>alert('XSS')</script>",
            "' OR '1'='1",
            "search term with <img src=x>",
        ]
        
        for query in search_queries:
            # Sanitize as the widget should
            sanitized = enhanced_sanitizer.sanitize_input(
                query,
                context='plain'
            )
            
            # Verify sanitization
            assert "<script>" not in sanitized
            assert "'" not in sanitized or "''" in sanitized
            assert "<img" not in sanitized
    
    def test_tag_input_widget_sanitization(self, enhanced_sanitizer):
        """Test tag input widget sanitization."""
        dangerous_tags = [
            "<script>tag</script>",
            "tag'); DROP TABLE--",
            "tag<img src=x onerror=alert(1)>",
            "../../../../etc/passwd",
        ]
        
        for tag in dangerous_tags:
            sanitized = enhanced_sanitizer.sanitize_input(
                tag,
                context='plain',
                max_length=50
            )
            
            # Tags should be safe
            assert "<" not in sanitized
            assert ">" not in sanitized
            assert "DROP TABLE" not in sanitized
            assert "../" not in sanitized


def test_security_monitoring():
    """Test security monitoring and alerting."""
    sanitizer = EnhancedInputSanitizer()
    
    # Perform multiple attacks
    attacks = [
        "<script>alert('XSS')</script>",
        "' OR '1'='1",
        "../../../etc/passwd",
        "; whoami",
    ]
    
    for attack in attacks:
        sanitizer.sanitize_input(attack)
    
    # Check security summary
    summary = sanitizer.get_security_summary()
    assert summary['total_attacks'] >= 4
    assert 'XSS' in summary['attack_counts']
    assert 'SQL Injection' in summary['attack_counts']
    assert 'Path Traversal' in summary['attack_counts']
    assert 'Command Injection' in summary['attack_counts']


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])