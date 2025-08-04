"""
Worker thread implementation for asynchronous translation operations

This module provides the TranslationWorker class that runs translations
in a separate thread to keep the GUI responsive.
"""

from typing import Optional, Dict, Any
import logging
import traceback

from PySide6.QtCore import QObject, Signal, Slot

from .models import ParseResult, BlockType, CodeBlock
from .parser import ParserModule
from .llm_interface import LLMInterface
from .config import TranslatorConfig
from .assembler import CodeAssembler


logger = logging.getLogger(__name__)


from dataclasses import dataclass


@dataclass
class TranslationStatus:
    """Status information for translation operations"""
    phase: str  # "parsing", "translating", "assembling", "validating"
    progress: int  # 0-100
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    success: bool
    code: Optional[str]
    errors: list[str]
    warnings: list[str]
    metadata: Dict[str, Any]
    parse_result: Optional[ParseResult] = None


class TranslationWorker(QObject):
    """
    Worker class for performing translations in a separate thread
    
    This class handles the actual translation work and emits signals
    to communicate progress and results back to the main thread.
    """
    
    # Signals
    started = Signal()
    progress = Signal(int)  # Progress percentage
    status = Signal(TranslationStatus)  # Detailed status
    completed = Signal(TranslationResult)  # Final result
    error = Signal(str)  # Error message
    finished = Signal()  # Worker done
    
    def __init__(self, 
                 pseudocode: str,
                 config: TranslatorConfig,
                 parser: ParserModule,
                 llm_interface: LLMInterface,
                 parent: Optional[QObject] = None):
        """
        Initialize the translation worker
        
        Args:
            pseudocode: The pseudocode text to translate
            config: Translator configuration
            parser: Parser module instance
            llm_interface: LLM interface instance
            parent: Optional parent QObject
        """
        super().__init__(parent)
        
        self.pseudocode = pseudocode
        self.config = config
        self.parser = parser
        self.llm_interface = llm_interface
        
        # State tracking
        self._cancelled = False
        self._running = False
    
    @Slot()
    def run(self):
        """
        Main worker method that performs the translation
        
        This method is called when the worker thread starts.
        It emits signals to communicate progress and results.
        """
        if self._running:
            logger.warning("Translation already running")
            return
        
        self._running = True
        self._cancelled = False
        
        try:
            self.started.emit()
            
            # Parse the pseudocode
            self._emit_status("parsing", 10, "Parsing pseudocode...")
            
            parse_result = self.parser.get_parse_result(self.pseudocode)
            
            if self._cancelled:
                self._handle_cancellation()
                return
            
            if not parse_result.success:
                result = TranslationResult(
                    success=False,
                    code=None,
                    errors=[str(e) for e in parse_result.errors],
                    warnings=parse_result.warnings,
                    metadata={"phase": "parsing"},
                    parse_result=parse_result
                )
                self.completed.emit(result)
                return
            
            # Get English blocks to translate
            english_blocks = parse_result.get_blocks_by_type(BlockType.ENGLISH)
            total_blocks = len(english_blocks)
            
            if total_blocks == 0:
                # No English blocks to translate, just return Python code
                result = self._create_result_from_parse(parse_result, [])
                self.completed.emit(result)
                return
            
            # Translate English blocks
            self._emit_status(
                "translating", 
                30, 
                f"Translating {total_blocks} instruction blocks..."
            )
            
            translated_blocks = []
            
            for i, block in enumerate(english_blocks):
                if self._cancelled:
                    self._handle_cancellation()
                    return
                
                # Calculate progress
                block_progress = 30 + int((i / total_blocks) * 40)
                self.progress.emit(block_progress)
                
                # Update status
                self._emit_status(
                    "translating",
                    block_progress,
                    f"Translating block {i+1} of {total_blocks}...",
                    {"current_block": i+1, "total_blocks": total_blocks}
                )
                
                # Get context for translation
                context = {
                    'code': block.context,
                    'metadata': block.metadata,
                    'line_numbers': block.line_numbers
                }
                
                try:
                    # Translate the block
                    python_code = self.llm_interface.translate(
                        block.content,
                        context
                    )
                    translated_blocks.append(python_code)
                    
                except Exception as e:
                    logger.error(f"Translation failed for block {i+1}: {e}")
                    error_code = f"# Error translating block {i+1}: {str(e)}\n# Original instruction:\n# {block.content}"
                    translated_blocks.append(error_code)
            
            if self._cancelled:
                self._handle_cancellation()
                return
            
            # Assemble the final code
            self._emit_status("assembling", 75, "Assembling final code...")
            
            # Create CodeBlock objects for assembly
            assembled_blocks = self._create_code_blocks_for_assembly(parse_result, translated_blocks)
            
            # Use CodeAssembler for sophisticated assembly
            assembler = CodeAssembler(self.config)
            final_code = assembler.assemble(assembled_blocks)
            
            # Validate the generated code
            self._emit_status("validating", 90, "Validating generated code...")
            
            validation_errors = self._validate_code(final_code)
            
            # Attempt to fix validation errors if configured
            if validation_errors and self.config.llm.validation_level == "normal":
                self._emit_status("refining", 95, "Attempting to fix validation errors...")
                
                for error in validation_errors[:3]:  # Limit refinement attempts
                    try:
                        final_code = self.llm_interface.refine_code(final_code, error)
                        # Re-validate
                        validation_errors = self._validate_code(final_code)
                        if not validation_errors:
                            break
                    except Exception as e:
                        logger.warning(f"Code refinement failed: {e}")
            
            # Create final result
            result = TranslationResult(
                success=len(validation_errors) == 0,
                code=final_code,
                errors=validation_errors,
                warnings=parse_result.warnings,
                metadata={
                    "blocks_processed": parse_result.block_count,
                    "english_blocks": total_blocks,
                    "translated_blocks": len(translated_blocks),
                    "model_info": self.llm_interface.get_model_info(),
                    "validation_level": self.config.llm.validation_level
                },
                parse_result=parse_result
            )
            
            self.progress.emit(100)
            self.completed.emit(result)
            
        except Exception as e:
            logger.error(f"Translation worker error: {e}")
            logger.error(traceback.format_exc())
            self.error.emit(str(e))
            
        finally:
            self._running = False
            self.finished.emit()
    
    @Slot()
    def cancel(self):
        """Cancel the translation operation"""
        self._cancelled = True
        logger.info("Translation cancelled by user")
    
    def _emit_status(self, phase: str, progress: int, message: str, details: Optional[Dict[str, Any]] = None):
        """Helper to emit status updates"""
        status = TranslationStatus(phase, progress, message, details)
        self.status.emit(status)
    
    def _handle_cancellation(self):
        """Handle cancellation of the translation"""
        self._emit_status("cancelled", 0, "Translation cancelled")
        result = TranslationResult(
            success=False,
            code=None,
            errors=["Translation cancelled by user"],
            warnings=[],
            metadata={"cancelled": True}
        )
        self.completed.emit(result)
    
    def _create_code_blocks_for_assembly(self, parse_result: ParseResult, translated_blocks: list[str]) -> list[CodeBlock]:
        """
        Create CodeBlock objects for assembly by combining original blocks with translations
        
        Args:
            parse_result: The parse result containing all blocks
            translated_blocks: List of translated Python code for English blocks
            
        Returns:
            List of CodeBlock objects ready for assembly
        """
        assembled_blocks = []
        translation_index = 0
        
        for block in parse_result.blocks:
            if block.type == BlockType.ENGLISH:
                # Replace English block with translated Python code
                if translation_index < len(translated_blocks):
                    translated_code = translated_blocks[translation_index]
                    # Create a new CodeBlock with the translated content
                    python_block = CodeBlock(
                        type=BlockType.PYTHON,
                        content=translated_code,
                        line_numbers=block.line_numbers,
                        context=block.context,
                        metadata=block.metadata
                    )
                    assembled_blocks.append(python_block)
                    translation_index += 1
            else:
                # Keep other blocks as-is (Python, Comment, Mixed)
                assembled_blocks.append(block)
        
        return assembled_blocks
    
    def _validate_code(self, code: str) -> list[str]:
        """
        Validate Python code and return list of errors
        
        Args:
            code: Python code to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not code or not code.strip():
            errors.append("Generated code is empty")
            return errors
        
        # Syntax validation
        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            line_info = f" at line {e.lineno}" if e.lineno else ""
            errors.append(f"Syntax error{line_info}: {e.msg}")
        except Exception as e:
            errors.append(f"Compilation error: {str(e)}")
        
        # Additional validation based on configuration
        if self.config.llm.validation_level == "strict":
            # Check for undefined variables (simplified check)
            if self.config.check_undefined_vars:
                undefined_check_errors = self._check_undefined_variables(code)
                errors.extend(undefined_check_errors)
            
            # Check imports
            if self.config.validate_imports:
                import_errors = self._check_imports(code)
                errors.extend(import_errors)
        
        return errors
    
    def _check_undefined_variables(self, code: str) -> list[str]:
        """
        Check for potentially undefined variables using the validator module
        
        This delegates to the robust implementation in the validator module
        that properly handles scopes, imports, and special cases.
        """
        # Import validator here to avoid circular imports
        from .validator import Validator
        
        # Create a temporary validator instance
        validator = Validator(self.config)
        
        try:
            # Parse the code
            import ast
            tree = ast.parse(code)
            
            # Use the validator's comprehensive undefined names check
            return validator._check_undefined_names(tree, code)
            
        except SyntaxError:
            # If code has syntax errors, we can't check undefined vars
            return ["Cannot check undefined variables due to syntax errors"]
    
    def _check_imports(self, code: str) -> list[str]:
        """
        Check if imports are valid
        
        This is a basic implementation that checks for common issues.
        """
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for malformed imports
            if stripped.startswith('import ') or stripped.startswith('from '):
                try:
                    compile(stripped, '<import>', 'single')
                except SyntaxError:
                    errors.append(f"Invalid import statement at line {i}: {stripped}")
        
        return errors
    
    def _create_result_from_parse(self, parse_result: ParseResult, translated_blocks: list[str]) -> TranslationResult:
        """
        Create a translation result when no translation is needed
        
        Args:
            parse_result: The parse result
            translated_blocks: Empty list of translations
            
        Returns:
            TranslationResult object
        """
        # Use CodeAssembler even when no translation is needed
        # This ensures consistent formatting and import organization
        assembler = CodeAssembler(self.config)
        
        # Filter for Python and comment blocks only
        blocks_to_assemble = [
            block for block in parse_result.blocks
            if block.type in [BlockType.PYTHON, BlockType.COMMENT]
        ]
        
        final_code = assembler.assemble(blocks_to_assemble)
        validation_errors = self._validate_code(final_code)
        
        return TranslationResult(
            success=len(validation_errors) == 0,
            code=final_code,
            errors=validation_errors,
            warnings=parse_result.warnings + ["No English instructions found to translate"],
            metadata={
                "blocks_processed": parse_result.block_count,
                "english_blocks": 0,
                "translated_blocks": 0
            },
            parse_result=parse_result
        )