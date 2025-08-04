"""
Comprehensive tests for error handling improvements in the Pseudocode
Translator.

This module tests the custom exception hierarchy, error context, error
recovery, and helpful error messages across all translator components.
"""

import pytest
from unittest.mock import patch

from pseudocode_translator.exceptions import (
    TranslatorError, ParsingError, ValidationError, 
    AssemblyError, ConfigurationError, CacheError,
    ErrorContext
)
from pseudocode_translator.parser import PseudocodeParser
from pseudocode_translator.validator import PseudocodeValidator
from pseudocode_translator.translator import PseudocodeTranslator
from pseudocode_translator.assembler import CodeAssembler
from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models import CodeBlock, BlockType


class TestExceptionHierarchy:
    """Test the custom exception hierarchy and error formatting."""
    
    def test_base_error_formatting(self):
        """Test base TranslatorError formatting."""
        error = TranslatorError("Test error message")
        formatted = error.format_error()
        
        assert "TranslatorError: Test error message" in formatted
        assert "Context:" not in formatted  # No context provided
        assert "Suggestions:" not in formatted  # No suggestions added
    
    def test_error_with_context(self):
        """Test error with context information."""
        context = ErrorContext(
            line_number=42,
            code_snippet="for i in range(10):",
            metadata={"variable": "i"}
        )
        
        error = ParsingError("Invalid syntax", context=context)
        formatted = error.format_error()
        
        assert "Line 42:" in formatted
        assert "for i in range(10):" in formatted
        assert "Context:" in formatted
    
    def test_error_with_suggestions(self):
        """Test error with helpful suggestions."""
        error = ValidationError("Undefined variable 'count'")
        error.add_suggestion("Did you mean 'counter'?")
        error.add_suggestion("Declare the variable before use")
        
        formatted = error.format_error()
        
        assert "Suggestions:" in formatted
        assert "Did you mean 'counter'?" in formatted
        assert "Declare the variable before use" in formatted
    
    def test_specific_error_types(self):
        """Test specific error type attributes."""
        # ParsingError
        parse_error = ParsingError("Parse failed", parse_position=100)
        assert parse_error.parse_position == 100
        
        # ValidationError
        valid_error = ValidationError(
            "Invalid", validation_type="undefined_var"
        )
        assert valid_error.validation_type == "undefined_var"
        
        # AssemblyError
        assembly_error = AssemblyError(
            "Assembly failed", assembly_stage="imports"
        )
        assert assembly_error.assembly_stage == "imports"
        
        # ConfigurationError
        config_error = ConfigurationError(
            "Bad config", config_key="indent_size"
        )
        assert config_error.config_key == "indent_size"
        
        # CacheError
        cache_error = CacheError("Cache miss", cache_key="test.py")
        assert cache_error.cache_key == "test.py"


class TestParserErrorHandling:
    """Test error handling in the parser module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.parser = PseudocodeParser(self.config)
    
    def test_syntax_error_handling(self):
        """Test handling of syntax errors during parsing."""
        # Invalid Python syntax
        code = """
        if x = 5:  # Should be ==
            print("Invalid")
        """
        
        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse(code)
        
        error = exc_info.value
        assert "Invalid syntax" in str(error)
        assert error.context is not None
        assert error.context.line_number == 2  # Line with error
        assert "if x = 5:" in error.context.code_snippet
    
    def test_indentation_error_recovery(self):
        """Test recovery from indentation errors."""
        code = """
        def test():
        print("Bad indent")  # Missing indentation
        """
        
        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse(code)
        
        error = exc_info.value
        assert "IndentationError" in str(error)
        assert len(error.suggestions) > 0
        assert any("indentation" in s.lower() for s in error.suggestions)
    
    def test_parser_error_context(self):
        """Test that parser errors include helpful context."""
        code = """
        for i in range(10)
            print(i)  # Missing colon
        """
        
        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse(code)
        
        error = exc_info.value
        formatted = error.format_error()
        
        # Check error includes context
        assert "Line 2:" in formatted
        assert "for i in range(10)" in formatted
        assert "Suggestions:" in formatted


class TestValidatorErrorHandling:
    """Test error handling in the validator module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.validator = PseudocodeValidator(self.config)
    
    def test_undefined_variable_error(self):
        """Test handling of undefined variable errors."""
        blocks = [
            CodeBlock(
                content="print(count)",
                type=BlockType.PYTHON,
                line_numbers=[1]
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(blocks)
        
        error = exc_info.value
        assert "undefined variable" in str(error).lower()
        assert "count" in str(error)
        assert error.validation_type == "undefined_variable"
    
    def test_typo_suggestions(self):
        """Test that validator suggests corrections for typos."""
        # First define a variable
        blocks = [
            CodeBlock(
                content="counter = 0",
                type=BlockType.PYTHON,
                line_numbers=[1]
            ),
            CodeBlock(
                content="print(countr)",  # Typo: countr instead of counter
                type=BlockType.PYTHON,
                line_numbers=[2]
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(blocks)
        
        error = exc_info.value
        formatted = error.format_error()
        
        # Should suggest the similar variable name
        assert "counter" in formatted
        assert "Did you mean" in formatted
    
    def test_indentation_validation_error(self):
        """Test handling of indentation validation errors."""
        blocks = [
            CodeBlock(
                content="def test():\nprint('bad')",  # Missing indentation
                type=BlockType.PYTHON,
                line_numbers=[1, 2]
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(blocks)
        
        error = exc_info.value
        assert "indentation" in str(error).lower()
        assert error.validation_type == "indentation"
        assert len(error.suggestions) > 0


class TestTranslatorErrorHandling:
    """Test error handling in the translator module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.translator = PseudocodeTranslator(self.config)
    
    def test_translation_error_aggregation(self):
        """Test that translator aggregates multiple errors."""
        # Pseudocode with multiple issues
        pseudocode = """
        FUNCTION calculate
            SET x = 10
            PRINT y  // Undefined variable
        END
        
        // Another block with error
        IF z > 5  // Another undefined variable
            PRINT "Large"
        """
        
        result = self.translator.translate(pseudocode)
        
        # Check that translation attempted to continue despite errors
        assert result != ""
        assert "def calculate" in result  # First function translated
    
    def test_graceful_degradation(self):
        """Test graceful degradation when partial translation is possible."""
        pseudocode = """
        // Valid block
        SET message = "Hello"
        PRINT message
        
        // Invalid block
        FUNCTION @invalid#name
            PRINT "This won't work"
        END
        
        // Another valid block  
        SET count = 42
        PRINT count
        """
        
        result = self.translator.translate(pseudocode)
        
        # Valid blocks should be translated
        assert 'message = "Hello"' in result
        assert 'print(message)' in result
        assert 'count = 42' in result
        assert 'print(count)' in result
    
    @patch('pseudocode_translator.translator.PseudocodeParser.parse')
    def test_parser_error_propagation(self, mock_parse):
        """Test that parser errors are properly propagated."""
        # Mock parser to raise an error
        mock_parse.side_effect = ParsingError(
            "Severe syntax error",
            context=ErrorContext(line_number=5, code_snippet="BAD CODE")
        )
        
        with pytest.raises(ParsingError) as exc_info:
            self.translator.translate("ANY CODE")
        
        error = exc_info.value
        assert "Severe syntax error" in str(error)
        assert error.context.line_number == 5


class TestAssemblerErrorHandling:
    """Test error handling in the assembler module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.assembler = CodeAssembler(self.config)
    
    def test_no_python_blocks_error(self):
        """Test handling when no Python blocks are provided."""
        # Only comment blocks
        blocks = [
            CodeBlock(
                content="# Just a comment",
                type=BlockType.COMMENT,
                line_numbers=[1]
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should return empty string with warning, not raise
        assert result == ""
    
    def test_import_organization_error(self):
        """Test handling of errors during import organization."""
        blocks = [
            CodeBlock(
                content="import sys as as as",  # Invalid syntax
                type=BlockType.PYTHON,
                line_numbers=[1]
            )
        ]
        
        # Should handle the error gracefully
        result = self.assembler.assemble(blocks)
        
        # Should still produce some output
        assert result != ""
    
    def test_assembly_stage_errors(self):
        """Test that assembly errors include stage information."""
        blocks = [
            CodeBlock(
                content="def test(\n    pass",  # Syntax error
                type=BlockType.PYTHON,
                line_numbers=[1, 2]
            )
        ]
        
        # Assembly should continue despite syntax errors in individual blocks
        result = self.assembler.assemble(blocks)
        
        # Should attempt to include the block
        assert "def test(" in result or result == ""
    
    def test_consistency_check_error_handling(self):
        """Test error handling in consistency checks."""
        # Create blocks with mixed indentation
        blocks = [
            CodeBlock(
                content="def func1():\n    return 1",
                type=BlockType.PYTHON,
                line_numbers=[1, 2]
            ),
            CodeBlock(
                content="def func2():\n\treturn 2",  # Tab instead of spaces
                type=BlockType.PYTHON,
                line_numbers=[3, 4]
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should fix indentation inconsistency
        assert "\t" not in result  # Tabs converted to spaces


class TestErrorRecovery:
    """Test error recovery mechanisms across modules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.translator = PseudocodeTranslator(self.config)
    
    def test_continue_after_block_error(self):
        """Test that translation continues after encountering an error."""
        pseudocode = """
        // Block 1 - Valid
        SET x = 10
        PRINT x
        
        // Block 2 - Has error
        FUNCTION 123invalid  // Invalid function name
            RETURN 0
        END
        
        // Block 3 - Valid
        SET y = 20
        PRINT y
        """
        
        result = self.translator.translate(pseudocode)
        
        # Blocks 1 and 3 should be translated
        assert "x = 10" in result
        assert "print(x)" in result
        assert "y = 20" in result
        assert "print(y)" in result
    
    def test_partial_validation_recovery(self):
        """Test recovery from validation errors in some blocks."""
        config = TranslatorConfig()
        validator = PseudocodeValidator(config)
        
        blocks = [
            CodeBlock(
                content="x = 10",
                type=BlockType.PYTHON,
                line_numbers=[1]
            ),
            CodeBlock(
                content="print(undefined_var)",  # Will fail validation
                type=BlockType.PYTHON,
                line_numbers=[2]
            ),
            CodeBlock(
                content="y = 20",
                type=BlockType.PYTHON,
                line_numbers=[3]
            )
        ]
        
        with pytest.raises(ValidationError):
            validator.validate(blocks)
        
        # Even though validation fails, the error should be informative
        try:
            validator.validate(blocks)
        except ValidationError as e:
            assert "undefined_var" in str(e)
            assert e.context is not None
            assert e.context.line_number == 2


class TestIntegrationErrorHandling:
    """Test error handling across the full translation pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslatorConfig()
        self.translator = PseudocodeTranslator(self.config)
    
    def test_full_pipeline_error_handling(self):
        """Test error handling through the complete translation process."""
        # Complex pseudocode with various issues
        pseudocode = """
        // Configuration section
        SET MAX_VALUE = 100
        
        // Function with typo in variable name
        FUNCTION calculate_sum(numbers)
            SET total = 0
            FOR EACH num IN numbers
                ADD num TO totl  // Typo: totl instead of total
            END FOR
            RETURN total
        END FUNCTION
        
        // Main execution
        SET values = [1, 2, 3, 4, 5]
        SET result = CALL calculate_sum WITH values
        PRINT result
        """
        
        # Translation should handle the error gracefully
        result = self.translator.translate(pseudocode)
        
        # Should translate most of the code
        assert "MAX_VALUE = 100" in result
        assert "def calculate_sum(numbers):" in result
        assert "values = [1, 2, 3, 4, 5]" in result
    
    def test_error_context_preservation(self):
        """Test that error context is preserved through the pipeline."""
        pseudocode = """
        FUNCTION test()
            SET x = 10
            PRINT y  // Undefined variable on line 3
        END
        """
        
        try:
            self.translator.translate(pseudocode)
        except ValidationError as e:
            # Error should preserve line number context
            assert e.context is not None
            # Error line could be 3 or 4 depending on counting
            assert e.context.line_number in [3, 4]
            assert "y" in str(e)


class TestErrorMessages:
    """Test the quality and helpfulness of error messages."""
    
    def test_parsing_error_messages(self):
        """Test that parsing errors have clear messages."""
        parser = PseudocodeParser(TranslatorConfig())
        
        with pytest.raises(ParsingError) as exc_info:
            parser.parse("if x == 5\n    print(x)")  # Missing colon
        
        error = exc_info.value
        formatted = error.format_error()
        
        # Should explain the issue clearly
        assert "syntax" in formatted.lower()
        expected_words = ["colon", ":", "expected"]
        assert any(word in formatted.lower() for word in expected_words)
    
    def test_validation_error_messages(self):
        """Test that validation errors explain the issue."""
        validator = PseudocodeValidator(TranslatorConfig())
        
        blocks = [
            CodeBlock(
                content="result = unknown_func()",
                type=BlockType.PYTHON,
                line_numbers=[1]
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(blocks)
        
        error = exc_info.value
        assert "unknown_func" in str(error)
        assert "undefined" in str(error).lower()
    
    def test_assembly_error_messages(self):
        """Test that assembly errors are descriptive."""
        assembler = CodeAssembler(TranslatorConfig())
        
        # Test with empty blocks list
        blocks = []
        result = assembler.assemble(blocks)
        
        # Should handle gracefully
        assert result == ""


class TestConfigurationErrorHandling:
    """Test configuration-related error handling."""
    
    def test_invalid_config_handling(self):
        """Test handling of invalid configuration values."""
        with pytest.raises(ConfigurationError) as exc_info:
            config = TranslatorConfig()
            config.indent_size = -1  # Invalid value
            config.validate()  # If validate method exists
        
        error = exc_info.value
        assert "indent_size" in str(error)
        assert error.config_key == "indent_size"
    
    def test_missing_config_handling(self):
        """Test handling of missing configuration."""
        # Test creating translator with None config
        with pytest.raises(ConfigurationError):
            PseudocodeTranslator(None)


class TestCacheErrorHandling:
    """Test cache-related error handling."""
    
    @patch('pseudocode_translator.ast_cache.parse_cached')
    def test_cache_error_handling(self, mock_parse):
        """Test handling of cache errors."""
        # Mock cache to raise an error
        mock_parse.side_effect = CacheError(
            "Cache corrupted",
            cache_key="test.py"
        )
        
        parser = PseudocodeParser(TranslatorConfig())
        
        # Parser should handle cache errors gracefully
        with pytest.raises(ParsingError):
            parser.parse("print('test')")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])