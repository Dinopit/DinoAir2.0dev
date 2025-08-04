"""
Unit tests for the translator module
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import threading
import time
from typing import List
from pseudocode_translator.translator import (
    TranslationManager, TranslationResult, TranslationMetadata
)
from pseudocode_translator.models import (
    CodeBlock, BlockType, ParseResult, ParseError
)


class TestTranslationResult:
    """Test the TranslationResult dataclass"""
    
    def test_successful_result(self):
        """Test creating a successful translation result"""
        result = TranslationResult(
            success=True,
            code="def hello(): pass",
            errors=[],
            warnings=[],
            metadata={"duration_ms": 100}
        )
        
        assert result.success is True
        assert result.code == "def hello(): pass"
        assert result.has_errors is False
        assert result.has_warnings is False
    
    def test_failed_result(self):
        """Test creating a failed translation result"""
        result = TranslationResult(
            success=False,
            code=None,
            errors=["Syntax error", "Translation failed"],
            warnings=["Code smell detected"],
            metadata={}
        )
        
        assert result.success is False
        assert result.code is None
        assert result.has_errors is True
        assert result.has_warnings is True
        assert len(result.errors) == 2
    
    def test_result_with_warnings_only(self):
        """Test result with warnings but no errors"""
        result = TranslationResult(
            success=True,
            code="def func(): pass",
            errors=[],
            warnings=["Consider using type hints"],
            metadata={}
        )
        
        assert result.success is True
        assert result.has_errors is False
        assert result.has_warnings is True


class TestTranslationMetadata:
    """Test the TranslationMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating translation metadata"""
        metadata = TranslationMetadata(
            duration_ms=150,
            blocks_processed=5,
            blocks_translated=3,
            cache_hits=2,
            model_tokens_used=500,
            validation_passed=True
        )
        
        assert metadata.duration_ms == 150
        assert metadata.blocks_processed == 5
        assert metadata.blocks_translated == 3
        assert metadata.cache_hits == 2
        assert metadata.model_tokens_used == 500
        assert metadata.validation_passed is True


class TestTranslationManager:
    """Test the TranslationManager class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock()
        config.llm = Mock()
        config.llm.cache_enabled = True
        return config
    
    @pytest.fixture
    def mock_parser(self):
        """Create a mock parser"""
        parser = Mock()
        return parser
    
    @pytest.fixture
    def mock_llm_interface(self):
        """Create a mock LLM interface"""
        llm = Mock()
        llm.cache = Mock()
        llm.cache.max_size = 1000
        llm.cache._cache = {}
        return llm
    
    @pytest.fixture
    def mock_assembler(self):
        """Create a mock assembler"""
        assembler = Mock()
        return assembler
    
    @pytest.fixture
    def mock_validator(self):
        """Create a mock validator"""
        validator = Mock()
        return validator
    
    @pytest.fixture
    def translation_manager(self, mock_config):
        """Create a TranslationManager with mocked dependencies"""
        with patch('pseudocode_translator.translator.ParserModule') as mock_parser_cls:
            with patch('pseudocode_translator.translator.LLMInterface') as mock_llm_cls:
                with patch('pseudocode_translator.translator.CodeAssembler') as mock_assembler_cls:
                    with patch('pseudocode_translator.translator.Validator') as mock_validator_cls:
                        # Create mock instances
                        mock_parser = Mock()
                        mock_llm = Mock()
                        mock_llm.cache = Mock()
                        mock_llm.cache.max_size = 1000
                        mock_llm.cache._cache = {}
                        mock_assembler = Mock()
                        mock_validator = Mock()
                        
                        # Configure class constructors to return mocks
                        mock_parser_cls.return_value = mock_parser
                        mock_llm_cls.return_value = mock_llm
                        mock_assembler_cls.return_value = mock_assembler
                        mock_validator_cls.return_value = mock_validator
                        
                        # Create manager
                        manager = TranslationManager(mock_config)
                        
                        # Store mocks for testing
                        manager._mock_parser = mock_parser
                        manager._mock_llm = mock_llm
                        manager._mock_assembler = mock_assembler
                        manager._mock_validator = mock_validator
                        
                        return manager
    
    def test_initialization(self, translation_manager):
        """Test TranslationManager initialization"""
        assert translation_manager.parser is not None
        assert translation_manager.llm_interface is not None
        assert translation_manager.assembler is not None
        assert translation_manager.validator is not None
        assert translation_manager._translation_count == 0
    
    def test_translate_simple_success(self, translation_manager):
        """Test successful translation of simple pseudocode"""
        # Setup parse result
        blocks = [
            CodeBlock(
                type=BlockType.ENGLISH,
                content="Create a hello world function",
                line_numbers=(1, 1),
                metadata={}
            )
        ]
        parse_result = ParseResult(blocks=blocks, errors=[], warnings=[])
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        
        # Setup LLM translation
        translation_manager._mock_llm.translate.return_value = "def hello():\n    print('Hello, World!')"
        
        # Setup assembly
        translation_manager._mock_assembler.assemble.return_value = "def hello():\n    print('Hello, World!')"
        
        # Setup validation
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        translation_manager._mock_validator.validate_syntax.return_value = validation_result
        translation_manager._mock_validator.validate_logic.return_value = validation_result
        translation_manager._mock_validator.suggest_improvements.return_value = []
        
        # Translate
        result = translation_manager.translate_pseudocode("Create a hello world function")
        
        assert result.success is True
        assert result.code == "def hello():\n    print('Hello, World!')"
        assert len(result.errors) == 0
    
    def test_translate_parse_failure(self, translation_manager):
        """Test translation with parse failure"""
        # Setup parse failure
        parse_result = ParseResult(
            blocks=[],
            errors=[ParseError("Invalid syntax", line_number=1)],
            warnings=[]
        )
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        
        # Translate
        result = translation_manager.translate_pseudocode("Invalid { syntax")
        
        assert result.success is False
        assert result.code is None
        assert len(result.errors) > 0
    
    def test_translate_mixed_blocks(self, translation_manager):
        """Test translation with mixed English and Python blocks"""
        # Setup parse result with mixed content
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="import math",
                line_numbers=(1, 1),
                metadata={"has_imports": True}
            ),
            CodeBlock(
                type=BlockType.ENGLISH,
                content="Create a function to calculate circle area",
                line_numbers=(3, 3),
                metadata={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="PI = math.pi",
                line_numbers=(5, 5),
                metadata={}
            )
        ]
        parse_result = ParseResult(blocks=blocks, errors=[], warnings=[])
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        
        # Setup LLM translation for English block
        translation_manager._mock_llm.translate.return_value = (
            "def calculate_circle_area(radius):\n    return PI * radius ** 2"
        )
        
        # Setup assembly
        assembled_code = """import math

def calculate_circle_area(radius):
    return PI * radius ** 2

PI = math.pi"""
        translation_manager._mock_assembler.assemble.return_value = assembled_code
        
        # Setup validation
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        translation_manager._mock_validator.validate_syntax.return_value = validation_result
        translation_manager._mock_validator.validate_logic.return_value = validation_result
        translation_manager._mock_validator.suggest_improvements.return_value = []
        
        # Translate
        result = translation_manager.translate_pseudocode("mixed content")
        
        assert result.success is True
        assert "import math" in result.code
        assert "def calculate_circle_area" in result.code
    
    def test_translate_validation_failure_with_fix(self, translation_manager):
        """Test translation with validation failure that gets fixed"""
        # Setup parse result
        blocks = [
            CodeBlock(
                type=BlockType.ENGLISH,
                content="Create add function",
                line_numbers=(1, 1),
                metadata={}
            )
        ]
        parse_result = ParseResult(blocks=blocks, errors=[], warnings=[])
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        
        # Setup LLM translation with error
        broken_code = "def add(a, b)\n    return a + b"  # Missing colon
        translation_manager._mock_llm.translate.return_value = broken_code
        
        # Setup assembly
        translation_manager._mock_assembler.assemble.return_value = broken_code
        
        # Setup validation - first fail, then succeed after fix
        fail_validation = Mock()
        fail_validation.is_valid = False
        fail_validation.errors = ["Syntax error: missing colon"]
        fail_validation.warnings = []
        
        success_validation = Mock()
        success_validation.is_valid = True
        success_validation.errors = []
        success_validation.warnings = []
        
        translation_manager._mock_validator.validate_syntax.side_effect = [
            fail_validation, success_validation
        ]
        translation_manager._mock_validator.validate_logic.return_value = success_validation
        translation_manager._mock_validator.suggest_improvements.return_value = []
        
        # Setup LLM refinement
        fixed_code = "def add(a, b):\n    return a + b"
        translation_manager._mock_llm.refine_code.return_value = fixed_code
        
        # Translate
        result = translation_manager.translate_pseudocode("Create add function")
        
        assert result.success is True
        assert "def add(a, b):" in result.code
        assert any("automatically fixed" in w for w in result.warnings)
    
    def test_translate_with_context(self, translation_manager):
        """Test translation with context from surrounding blocks"""
        # Setup blocks with context
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="x = 10\ny = 20",
                line_numbers=(1, 2),
                metadata={}
            ),
            CodeBlock(
                type=BlockType.ENGLISH,
                content="Create function to add x and y",
                line_numbers=(4, 4),
                metadata={}
            )
        ]
        parse_result = ParseResult(blocks=blocks, errors=[], warnings=[])
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        
        # Capture context passed to LLM
        captured_context = None
        def capture_translate(instruction, context=None):
            nonlocal captured_context
            captured_context = context
            return "def add_xy():\n    return x + y"
        
        translation_manager._mock_llm.translate.side_effect = capture_translate
        
        # Setup rest of pipeline
        translation_manager._mock_assembler.assemble.return_value = "complete code"
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        translation_manager._mock_validator.validate_syntax.return_value = validation_result
        translation_manager._mock_validator.validate_logic.return_value = validation_result
        translation_manager._mock_validator.suggest_improvements.return_value = []
        
        # Translate
        result = translation_manager.translate_pseudocode("test")
        
        # Check context was built correctly
        assert captured_context is not None
        assert "x = 10" in captured_context.get('code', '')
    
    def test_process_blocks_error_handling(self, translation_manager):
        """Test error handling in block processing"""
        # Setup blocks
        blocks = [
            CodeBlock(
                type=BlockType.ENGLISH,
                content="Create function",
                line_numbers=(1, 1),
                metadata={}
            )
        ]
        
        # Make LLM translation fail
        translation_manager._mock_llm.translate.side_effect = Exception("LLM error")
        
        # Process blocks
        processed = translation_manager._process_blocks(blocks)
        
        # Should mark block as failed but continue
        assert len(processed) == 1
        assert processed[0].metadata.get('translation_failed') is True
        assert processed[0].metadata.get('error') == "LLM error"
    
    def test_handle_dependencies(self, translation_manager):
        """Test dependency handling between blocks"""
        # Create blocks with dependencies
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="import numpy as np\nfrom math import pi",
                line_numbers=(1, 2),
                metadata={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def calculate():\n    return np.array([1, 2, 3])",
                line_numbers=(4, 5),
                metadata={}
            )
        ]
        
        # Handle dependencies
        translation_manager._handle_dependencies(blocks)
        
        # Check metadata was updated
        assert 'required_imports' in blocks[0].metadata
        assert 'defined_names' in blocks[1].metadata
        assert 'calculate' in blocks[1].metadata['defined_names']
    
    def test_separate_mixed_block(self, translation_manager):
        """Test separation of mixed English/Python blocks"""
        mixed_block = CodeBlock(
            type=BlockType.MIXED,
            content="""# Create a function to add numbers
def add(a, b):
    # Return the sum
    return a + b
Now create a subtract function""",
            line_numbers=(1, 5),
            metadata={}
        )
        
        # Mock the score calculation
        translation_manager.parser._calculate_python_score = Mock()
        translation_manager.parser._calculate_python_score.side_effect = [
            0.2,  # Comment line - English
            0.8,  # def line - Python
            0.2,  # Comment line - English
            0.8,  # return line - Python
            0.1   # English instruction
        ]
        
        # Separate
        sub_blocks = translation_manager._separate_mixed_block(mixed_block)
        
        # Should have multiple sub-blocks
        assert len(sub_blocks) > 1
        assert any(b.metadata.get('is_sub_block') for b in sub_blocks)
    
    def test_concurrent_translations(self, translation_manager):
        """Test thread safety with concurrent translations"""
        # Setup simple successful translation
        parse_result = ParseResult(
            blocks=[CodeBlock(
                type=BlockType.PYTHON,
                content="x = 1",
                line_numbers=(1, 1),
                metadata={}
            )],
            errors=[],
            warnings=[]
        )
        translation_manager._mock_parser.get_parse_result.return_value = parse_result
        translation_manager._mock_assembler.assemble.return_value = "x = 1"
        
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        translation_manager._mock_validator.validate_syntax.return_value = validation_result
        translation_manager._mock_validator.validate_logic.return_value = validation_result
        translation_manager._mock_validator.suggest_improvements.return_value = []
        
        results = []
        
        def translate():
            result = translation_manager.translate_pseudocode("test")
            results.append(result)
        
        # Run concurrent translations
        threads = [threading.Thread(target=translate) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert len(results) == 5
        assert all(r.success for r in results)
        # Translation IDs should be unique
        ids = [r.metadata.get('translation_id') for r in results]
        assert len(set(ids)) == 5
    
    def test_shutdown(self, translation_manager):
        """Test manager shutdown"""
        translation_manager.shutdown()
        
        # Should call LLM shutdown
        translation_manager._mock_llm.shutdown.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def translation_manager(self):
        config = Mock()
        config.llm = Mock()
        config.llm.cache_enabled = False
        
        with patch('pseudocode_translator.translator.ParserModule'):
            with patch('pseudocode_translator.translator.LLMInterface'):
                with patch('pseudocode_translator.translator.CodeAssembler'):
                    with patch('pseudocode_translator.translator.Validator'):
                        return TranslationManager(config)
    
    def test_empty_input(self, translation_manager):
        """Test translating empty input"""
        translation_manager.parser.get_parse_result.return_value = ParseResult(
            blocks=[], errors=[], warnings=[]
        )
        translation_manager.assembler.assemble.return_value = ""
        
        result = translation_manager.translate_pseudocode("")
        
        # Should handle gracefully
        assert result is not None
        assert isinstance(result, TranslationResult)
    
    def test_very_large_input(self, translation_manager):
        """Test translating very large input"""
        # Create many blocks
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content=f"x{i} = {i}",
                line_numbers=(i, i),
                metadata={}
            )
            for i in range(1000)
        ]
        
        translation_manager.parser.get_parse_result.return_value = ParseResult(
            blocks=blocks, errors=[], warnings=[]
        )
        translation_manager.assembler.assemble.return_value = "assembled code"
        
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.errors = []
        validation_result.warnings = []
        translation_manager.validator.validate_syntax.return_value = validation_result
        translation_manager.validator.validate_logic.return_value = validation_result
        translation_manager.validator.suggest_improvements.return_value = []
        
        # Should handle without error
        result = translation_manager.translate_pseudocode("large input")
        assert result is not None
    
    def test_exception_during_translation(self, translation_manager):
        """Test exception handling during translation"""
        # Make parser raise exception
        translation_manager.parser.get_parse_result.side_effect = Exception("Parser crashed")
        
        result = translation_manager.translate_pseudocode("test")
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Parser crashed" in result.errors[0]
    
    def test_assembly_failure(self, translation_manager):
        """Test handling of assembly failure"""
        blocks = [CodeBlock(
            type=BlockType.PYTHON,
            content="x = 1",
            line_numbers=(1, 1),
            metadata={}
        )]
        
        translation_manager.parser.get_parse_result.return_value = ParseResult(
            blocks=blocks, errors=[], warnings=[]
        )
        
        # Assembly returns None/empty
        translation_manager.assembler.assemble.return_value = None
        
        result = translation_manager.translate_pseudocode("test")
        
        assert result.success is False
        assert any("assemble" in err.lower() for err in result.errors)


@pytest.mark.parametrize("block_type,should_translate", [
    (BlockType.ENGLISH, True),
    (BlockType.PYTHON, False),
    (BlockType.MIXED, True),
    (BlockType.COMMENT, False),
])
def test_block_processing_by_type(block_type, should_translate):
    """Parametrized test for block processing based on type"""
    config = Mock()
    config.llm = Mock()
    
    with patch('pseudocode_translator.translator.ParserModule'):
        with patch('pseudocode_translator.translator.LLMInterface') as mock_llm_cls:
            with patch('pseudocode_translator.translator.CodeAssembler'):
                with patch('pseudocode_translator.translator.Validator'):
                    mock_llm = Mock()
                    mock_llm_cls.return_value = mock_llm
                    
                    manager = TranslationManager(config)
                    
                    block = CodeBlock(
                        type=block_type,
                        content="test content",
                        line_numbers=(1, 1),
                        metadata={}
                    )
                    
                    mock_llm.translate.return_value = "translated"
                    manager._separate_mixed_block = Mock(return_value=[block])
                    
                    processed = manager._process_blocks([block])
                    
                    if should_translate:
                        # Should attempt translation
                        assert mock_llm.translate.called or manager._separate_mixed_block.called
                    else:
                        # Should pass through unchanged
                        assert processed[0].content == "test content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])