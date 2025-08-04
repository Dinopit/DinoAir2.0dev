"""
Translation Manager module for the Pseudocode Translator

This module coordinates the entire translation pipeline, orchestrating
the parser, LLM interface, assembler, and validator components.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
import threading

# Import from models.py file (not the models directory)
from .models import CodeBlock, BlockType
from .parser import ParserModule
from .config import TranslatorConfig
from .assembler import CodeAssembler
from .validator import Validator, ValidationResult
from .ast_cache import parse_cached
from .exceptions import (
    TranslatorError, ParsingError,
    AssemblyError, ErrorContext
)

# Import new model abstraction from models directory
from .models.base_model import (
    BaseTranslationModel, OutputLanguage,
    TranslationConfig as ModelTranslationConfig
)
from .models.model_factory import ModelFactory, create_model
from .models.plugin_system import get_plugin_system


logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    success: bool
    code: Optional[str]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


@dataclass
class TranslationMetadata:
    """Metadata about the translation process"""
    duration_ms: int
    blocks_processed: int
    blocks_translated: int
    cache_hits: int
    model_tokens_used: int
    validation_passed: bool


class TranslationManager:
    """
    Main controller that coordinates the translation pipeline
    """
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize the Translation Manager
        
        Args:
            config: Translator configuration object
        """
        self.config = config
        self.parser = ParserModule()
        self.assembler = CodeAssembler(config)
        self.validator = Validator(config)
        
        # Thread safety
        self._lock = threading.Lock()
        self._translation_count = 0
        
        # Model management
        self._current_model: Optional[BaseTranslationModel] = None
        self._model_name: Optional[str] = None
        self._target_language = OutputLanguage.PYTHON  # Default
        
        # Initialize plugin system if enabled
        if getattr(config, 'enable_plugins', True):
            plugin_system = get_plugin_system()
            plugin_system.load_all_plugins()
        
        # Initialize model
        logger.info("Initializing Translation Manager")
        try:
            self._initialize_model()
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            error = TranslatorError(
                "Failed to initialize translation model",
                cause=e
            )
            error.add_suggestion("Check model configuration")
            error.add_suggestion(
                "Verify API credentials if using external models"
            )
            error.add_suggestion(
                "Ensure model files are available for local models"
            )
            raise error
    
    def _initialize_model(self, model_name: Optional[str] = None):
        """Initialize or switch to a different model"""
        # Determine model name from config or parameter
        if model_name is None:
            model_name = getattr(
                self.config.llm, 'model_type',
                getattr(self.config.llm, 'model_name', 'qwen')
            )
        
        # Create model configuration
        model_config = {
            'temperature': self.config.llm.temperature,
            'top_p': getattr(self.config.llm, 'top_p', 0.9),
            'top_k': getattr(self.config.llm, 'top_k', 40),
            'max_tokens': self.config.llm.max_tokens,
            'n_ctx': self.config.llm.n_ctx,
            'n_batch': getattr(self.config.llm, 'n_batch', 512),
            'n_threads': self.config.llm.n_threads,
            'n_gpu_layers': self.config.llm.n_gpu_layers,
        }
        
        # Add model path if available
        if hasattr(self.config.llm, 'model_path'):
            model_config['model_path'] = self.config.llm.model_path
        
        # Create model instance
        self._current_model = create_model(model_name, model_config)
        self._model_name = model_name
        
        # Initialize the model
        model_path = None
        if hasattr(self.config.llm, 'model_path'):
            from pathlib import Path
            model_path = Path(self.config.llm.model_path)
        
        self._current_model.initialize(model_path)
        logger.info(f"Initialized model: {model_name}")
    
    def translate_pseudocode(
        self,
        input_text: str,
        target_language: Optional[OutputLanguage] = None
    ) -> TranslationResult:
        """
        Main translation method that converts pseudocode to code
        
        Args:
            input_text: Mixed English/Python pseudocode
            target_language: Target programming language (defaults to Python)
            
        Returns:
            TranslationResult with generated code and metadata
        """
        if target_language:
            self._target_language = target_language
        start_time = time.time()
        errors = []
        warnings = []
        
        # Increment translation count
        with self._lock:
            self._translation_count += 1
            translation_id = self._translation_count
        
        logger.info(f"Starting translation #{translation_id}")
        
        try:
            # Step 1: Parse the input
            logger.debug("Parsing input text")
            try:
                parse_result = self.parser.get_parse_result(input_text)
                
                if not parse_result.success:
                    # Convert parse errors to detailed error messages
                    for parse_error in parse_result.errors:
                        error = ParsingError(
                            f"Parse error: {parse_error}",
                            block_content=input_text[:200]
                        )
                        errors.append(error.format_error())
                    
                    return TranslationResult(
                        success=False,
                        code=None,
                        errors=errors,
                        warnings=warnings,
                        metadata=self._create_metadata(
                            start_time, 0, 0, 0, 0, False
                        )
                    )
            except Exception as e:
                error = ParsingError(
                    "Failed to parse input",
                    block_content=input_text[:200],
                    cause=e
                )
                error.add_suggestion("Check input format")
                error.add_suggestion("Ensure pseudocode syntax is valid")
                
                return TranslationResult(
                    success=False,
                    code=None,
                    errors=[error.format_error()],
                    warnings=warnings,
                    metadata=self._create_metadata(
                        start_time, 0, 0, 0, 0, False
                    )
                )
            
            warnings.extend(parse_result.warnings)
            
            # Step 2: Process blocks
            logger.debug(f"Processing {len(parse_result.blocks)} blocks")
            processed_blocks = self._process_blocks(parse_result.blocks)
            
            # Step 3: Handle dependencies between blocks
            try:
                self._handle_dependencies(processed_blocks)
            except Exception as e:
                logger.warning(f"Error handling dependencies: {e}")
                warnings.append(f"Could not analyze dependencies: {str(e)}")
            
            # Step 4: Assemble the code
            logger.debug("Assembling code")
            try:
                assembled_code = self.assembler.assemble(processed_blocks)
                
                if not assembled_code:
                    error = AssemblyError(
                        "Failed to assemble code from blocks",
                        blocks_info=[{
                            'type': b.type.value,
                            'lines': b.line_numbers
                        } for b in processed_blocks],
                        assembly_stage="final"
                    )
                    error.add_suggestion("Check block compatibility")
                    error.add_suggestion(
                        "Verify all blocks were translated successfully"
                    )
                    
                    errors.append(error.format_error())
                    return TranslationResult(
                        success=False,
                        code=None,
                        errors=errors,
                        warnings=warnings,
                        metadata=self._create_metadata(
                            start_time,
                            len(parse_result.blocks),
                            len(processed_blocks),
                            0, 0, False
                        )
                    )
            except Exception as e:
                error = AssemblyError(
                    "Code assembly failed",
                    blocks_info=[{
                        'type': b.type.value,
                        'lines': b.line_numbers
                    } for b in processed_blocks],
                    assembly_stage="assembly",
                    cause=e
                )
                
                errors.append(error.format_error())
                return TranslationResult(
                    success=False,
                    code=None,
                    errors=errors,
                    warnings=warnings,
                    metadata=self._create_metadata(
                        start_time,
                        len(parse_result.blocks),
                        len(processed_blocks),
                        0, 0, False
                    )
                )
            
            # Step 5: Validate the code
            logger.debug("Validating generated code")
            validation_result = self.validator.validate_syntax(assembled_code)
            
            if not validation_result.is_valid:
                # Attempt to fix validation errors
                logger.debug("Attempting to fix validation errors")
                fixed_code = self._attempt_fixes(
                    assembled_code, validation_result
                )
                
                # Re-validate
                validation_result = self.validator.validate_syntax(fixed_code)
                if validation_result.is_valid:
                    assembled_code = fixed_code
                    warnings.append(
                        "Code was automatically fixed to resolve syntax errors"
                    )
                else:
                    errors.extend(validation_result.errors)
                    warnings.extend(validation_result.warnings)
            
            # Step 6: Logic validation
            logic_result = self.validator.validate_logic(assembled_code)
            warnings.extend(logic_result.warnings)
            
            # Step 7: Get improvement suggestions
            suggestions = self.validator.suggest_improvements(assembled_code)
            if suggestions:
                warnings.append(
                    f"Improvement suggestions: {'; '.join(suggestions)}"
                )
            
            # Calculate metadata
            blocks_translated = sum(
                1 for b in processed_blocks
                if b.metadata.get('translated', False)
            )
            # For backward compatibility, estimate cache hits
            cache_hits = 0
            
            metadata = self._create_metadata(
                start_time,
                len(parse_result.blocks),
                blocks_translated,
                cache_hits,
                0,  # Token count would need to be tracked in LLM interface
                validation_result.is_valid
            )
            
            return TranslationResult(
                success=validation_result.is_valid,
                code=assembled_code,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            
            # Create comprehensive error
            error = TranslatorError(
                "Translation failed",
                cause=e
            )
            error.add_suggestion("Check the input format")
            error.add_suggestion("Review any error messages above")
            error.add_suggestion("Try breaking down complex instructions")
            
            errors.append(error.format_error())
            
            return TranslationResult(
                success=False,
                code=None,
                errors=errors,
                warnings=warnings,
                metadata=self._create_metadata(start_time, 0, 0, 0, 0, False)
            )
    
    def _process_blocks(self, blocks: List[CodeBlock]) -> List[CodeBlock]:
        """
        Process each block, translating English blocks to Python
        
        Args:
            blocks: List of parsed code blocks
            
        Returns:
            List of processed code blocks
        """
        processed_blocks = []
        
        for i, block in enumerate(blocks):
            logger.debug(f"Processing block {i+1}/{len(blocks)}: {block.type}")
            
            if block.type == BlockType.ENGLISH:
                # Translate English to Python
                context = self._build_context(blocks, i)
                
                try:
                    # Create translation config
                    translation_config = ModelTranslationConfig(
                        target_language=self._target_language,
                        temperature=self.config.llm.temperature,
                        max_tokens=self.config.llm.max_tokens,
                        top_p=getattr(self.config.llm, 'top_p', 0.9),
                        top_k=getattr(self.config.llm, 'top_k', 40),
                        include_comments=True,
                        follow_conventions=True
                    )
                    
                    # Validate input
                    is_valid, error_msg = self._current_model.validate_input(
                        block.content
                    )
                    if not is_valid:
                        raise ValueError(f"Invalid input: {error_msg}")
                    
                    # Translate using the model
                    result = self._current_model.translate(
                        instruction=block.content,
                        config=translation_config,
                        context=context
                    )
                    
                    if not result.success:
                        raise RuntimeError(
                            f"Translation failed: "
                            f"{', '.join(result.errors)}"
                        )
                    
                    translated_code = result.code
                    
                    # Create new block with translated content
                    new_block = CodeBlock(
                        type=BlockType.PYTHON,
                        content=translated_code,
                        line_numbers=block.line_numbers,
                        metadata={
                            **block.metadata,
                            'translated': True,
                            'original_type': 'english'
                        },
                        context=block.context
                    )
                    processed_blocks.append(new_block)
                    
                except Exception as e:
                    logger.error(f"Failed to translate block: {e}")
                    
                    # Create detailed error
                    error_context = ErrorContext(
                        line_number=block.line_numbers[0],
                        code_snippet=block.content[:100],
                        metadata={
                            'block_type': 'english',
                            'line_range': (
                                f"{block.line_numbers[0]}-"
                                f"{block.line_numbers[1]}"
                            )
                        }
                    )
                    
                    error = TranslatorError(
                        "Failed to translate English block",
                        context=error_context,
                        cause=e
                    )
                    error.add_suggestion("Simplify the instruction")
                    error.add_suggestion("Check for ambiguous language")
                    error.add_suggestion("Break down complex requirements")
                    
                    # Keep original block but mark as failed
                    block.metadata['translation_failed'] = True
                    block.metadata['error'] = error.format_error()
                    processed_blocks.append(block)
                    
            elif block.type == BlockType.MIXED:
                # For mixed blocks, try to separate and translate English parts
                separated_blocks = self._separate_mixed_block(block)
                
                for sub_block in separated_blocks:
                    if sub_block.type == BlockType.ENGLISH:
                        context = self._build_context(blocks, i)
                        try:
                            # Create translation config
                            translation_config = ModelTranslationConfig(
                                target_language=self._target_language,
                                temperature=self.config.llm.temperature,
                                max_tokens=self.config.llm.max_tokens,
                                top_p=getattr(self.config.llm, 'top_p', 0.9),
                                top_k=getattr(self.config.llm, 'top_k', 40),
                                include_comments=True,
                                follow_conventions=True
                            )
                            
                            # Translate using the model
                            result = self._current_model.translate(
                                instruction=sub_block.content,
                                config=translation_config,
                                context=context
                            )
                            
                            if not result.success:
                                raise RuntimeError(
                                    "Translation failed: " +
                                    ", ".join(result.errors)
                                )
                            
                            translated_code = result.code
                            sub_block.content = translated_code
                            sub_block.type = BlockType.PYTHON
                            sub_block.metadata['translated'] = True
                        except Exception as e:
                            logger.error(f"Failed to translate sub-block: {e}")
                            
                            error = TranslatorError(
                                "Failed to translate mixed block component",
                                cause=e
                            )
                            error.add_suggestion(
                                "Separate English and Python parts"
                            )
                            
                            sub_block.metadata['translation_failed'] = True
                            sub_block.metadata['error'] = str(e)
                    
                    processed_blocks.append(sub_block)
                    
            else:
                # Python and comment blocks pass through unchanged
                processed_blocks.append(block)
        
        return processed_blocks
    
    def _handle_dependencies(self, blocks: List[CodeBlock]) -> None:
        """
        Handle dependencies between blocks (imports, variables, etc.)
        
        Args:
            blocks: List of processed code blocks
        """
        # Track variables and functions defined across blocks
        defined_names = set()
        required_imports = set()
        
        for i, block in enumerate(blocks):
            if block.type == BlockType.PYTHON:
                # Analyze block for definitions and usage
                try:
                    import ast
                    tree = parse_cached(block.content)
                    
                    # Find defined names
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            defined_names.add(node.name)
                        elif isinstance(node, ast.ClassDef):
                            defined_names.add(node.name)
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    defined_names.add(target.id)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                required_imports.add(f"import {alias.name}")
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module or ''
                            for alias in node.names:
                                required_imports.add(
                                    f"from {module} import {alias.name}"
                                )
                    
                    # Store metadata for assembler
                    block.metadata['defined_names'] = list(defined_names)
                    block.metadata['required_imports'] = list(required_imports)
                    
                except SyntaxError:
                    # If we can't parse, skip dependency analysis
                    logger.warning(
                        f"Could not parse block {i} for dependency analysis"
                    )
    
    def _build_context(
        self, blocks: List[CodeBlock], current_index: int
    ) -> Dict[str, Any]:
        """
        Build context for translation based on surrounding blocks
        
        Args:
            blocks: All blocks
            current_index: Index of current block
            
        Returns:
            Context dictionary
        """
        context = {
            'code': '',
            'before': '',
            'after': ''
        }
        
        # Get previous Python code blocks for context
        previous_code = []
        for i in range(max(0, current_index - 3), current_index):
            if blocks[i].type == BlockType.PYTHON:
                previous_code.append(blocks[i].content)
        
        if previous_code:
            context['before'] = '\n\n'.join(previous_code[-2:])  # Last 2 blocks
            context['code'] = context['before']
        
        # Get next block if available (for better understanding)
        if current_index + 1 < len(blocks):
            next_block = blocks[current_index + 1]
            if next_block.type in [BlockType.PYTHON, BlockType.ENGLISH]:
                context['after'] = next_block.content[:200]  # First 200 chars
        
        return context
    
    def _separate_mixed_block(self, block: CodeBlock) -> List[CodeBlock]:
        """
        Separate a mixed block into English and Python sub-blocks
        
        Args:
            block: Mixed type block
            
        Returns:
            List of separated blocks
        """
        sub_blocks = []
        lines = block.content.splitlines()
        
        current_type = None
        current_lines = []
        start_line = block.line_numbers[0]
        
        for i, line in enumerate(lines):
            # Simple heuristic to determine line type
            line_score = self.parser._calculate_python_score(line.strip())
            line_type = BlockType.PYTHON if line_score > 0.5 else BlockType.ENGLISH
            
            if current_type is None:
                current_type = line_type
                current_lines = [line]
            elif line_type != current_type:
                # Type changed, save current block
                if current_lines:
                    sub_block = CodeBlock(
                        type=current_type,
                        content='\n'.join(current_lines),
                        line_numbers=(start_line, start_line + len(current_lines) - 1),
                        metadata={'parent_block': block.metadata, 'is_sub_block': True},
                        context=block.context
                    )
                    sub_blocks.append(sub_block)
                
                # Start new block
                current_type = line_type
                current_lines = [line]
                start_line = block.line_numbers[0] + i
            else:
                current_lines.append(line)
        
        # Don't forget the last sub-block
        if current_lines:
            sub_block = CodeBlock(
                type=current_type,
                content='\n'.join(current_lines),
                line_numbers=(start_line, block.line_numbers[1]),
                metadata={'parent_block': block.metadata, 'is_sub_block': True},
                context=block.context
            )
            sub_blocks.append(sub_block)
        
        return sub_blocks if sub_blocks else [block]
    
    def _attempt_fixes(self, code: str, validation_result: ValidationResult) -> str:
        """
        Attempt to fix validation errors in the code
        
        Args:
            code: Code with validation errors
            validation_result: Validation result with error details
            
        Returns:
            Potentially fixed code
        """
        if not validation_result.errors:
            return code
        
        # Use LLM to refine code based on errors
        error_context = '\n'.join(
            validation_result.errors[:3]
        )  # First 3 errors
        
        try:
            # Use model's refine capability
            if self._current_model:
                translation_config = ModelTranslationConfig(
                    target_language=self._target_language,
                    temperature=0.2,  # Lower temperature for refinement
                    max_tokens=self.config.llm.max_tokens
                )
                
                result = self._current_model.refine_code(
                    code=code,
                    error_context=error_context,
                    config=translation_config
                )
                
                if result.success and result.code:
                    return result.code
            
            return code
        except Exception as e:
            logger.error(f"Failed to fix code: {e}")
            
            # Log recovery attempt failure
            recovery_error = TranslatorError(
                "Automatic error recovery failed",
                cause=e
            )
            recovery_error.add_suggestion("Manual fixes may be required")
            logger.warning(recovery_error.format_error())
            
            return code
    
    def _create_metadata(
        self, start_time: float, blocks_processed: int,
        blocks_translated: int, cache_hits: int,
        model_tokens: int, validation_passed: bool
    ) -> Dict[str, Any]:
        """Create metadata dictionary for the translation result"""
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            'duration_ms': duration_ms,
            'blocks_processed': blocks_processed,
            'blocks_translated': blocks_translated,
            'cache_hits': cache_hits,
            'model_tokens_used': model_tokens,
            'validation_passed': validation_passed,
            'translation_id': self._translation_count
        }
    
    def shutdown(self):
        """Shutdown the translation manager and free resources"""
        logger.info("Shutting down Translation Manager")
        if self._current_model:
            self._current_model.shutdown()
        logger.info("Translation Manager shutdown complete")
    
    def switch_model(self, model_name: str) -> None:
        """
        Switch to a different translation model
        
        Args:
            model_name: Name of the model to switch to
        """
        logger.info(f"Switching from {self._model_name} to {model_name}")
        
        # Shutdown current model
        if self._current_model:
            self._current_model.shutdown()
        
        # Initialize new model
        self._initialize_model(model_name)
    
    def get_current_model(self) -> Optional[str]:
        """Get the name of the current model"""
        return self._model_name
    
    def list_available_models(self) -> List[str]:
        """List all available models"""
        return ModelFactory.list_models()
    
    def set_target_language(self, language: OutputLanguage) -> None:
        """Set the target output language"""
        self._target_language = language
        logger.info(f"Target language set to: {language.value}")
    
    def translate_streaming(
        self, input_text: str,
        chunk_size: int = 4096,
        progress_callback: Optional[Any] = None
    ) -> Iterator[TranslationResult]:
        """
        Translate pseudocode using streaming for memory efficiency
        
        Args:
            input_text: Mixed English/Python pseudocode
            chunk_size: Size of chunks for streaming
            progress_callback: Optional callback for progress updates
            
        Yields:
            TranslationResult objects for each processed chunk
        """
        start_time = time.time()
        
        # Use streaming pipeline if available
        try:
            from .streaming.pipeline import StreamingPipeline, StreamingProgress
            
            # Create streaming pipeline
            pipeline = StreamingPipeline(self.config)
            
            # Check if streaming is appropriate
            if not pipeline.should_use_streaming(input_text):
                # Fall back to regular translation
                yield self.translate_pseudocode(input_text)
                return
            
            logger.info("Using streaming translation")
            
            # Process with streaming
            all_results = []
            for chunk_result in pipeline.stream_translate(
                input_text,
                progress_callback=progress_callback
            ):
                # Convert chunk result to translation result
                if chunk_result.success and chunk_result.translated_blocks:
                    # Assemble chunk code
                    chunk_code = self.assembler.assemble(
                        chunk_result.translated_blocks
                    )
                    
                    result = TranslationResult(
                        success=True,
                        code=chunk_code,
                        errors=[],
                        warnings=chunk_result.warnings,
                        metadata={
                            'chunk_index': chunk_result.chunk_index,
                            'processing_time': chunk_result.processing_time,
                            'streaming': True
                        }
                    )
                else:
                    result = TranslationResult(
                        success=False,
                        code=None,
                        errors=[chunk_result.error] if chunk_result.error else [],
                        warnings=chunk_result.warnings,
                        metadata={
                            'chunk_index': chunk_result.chunk_index,
                            'streaming': True
                        }
                    )
                
                all_results.append(result)
                yield result
            
            # After all chunks, assemble final code
            final_code = pipeline.assemble_streamed_code()
            
            # Validate final assembled code
            validation_result = self.validator.validate_syntax(final_code)
            
            # Create final result
            duration_ms = int((time.time() - start_time) * 1000)
            final_result = TranslationResult(
                success=validation_result.is_valid,
                code=final_code,
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                metadata={
                    'duration_ms': duration_ms,
                    'streaming': True,
                    'total_chunks': len(all_results),
                    'memory_usage': pipeline.get_memory_usage()
                }
            )
            
            # Cleanup
            pipeline.cancel_streaming()
            
            yield final_result
            
        except ImportError:
            logger.warning(
                "Streaming module not available, using regular translation"
            )
            yield self.translate_pseudocode(input_text)
        except Exception as e:
            error = TranslatorError(
                "Streaming translation failed",
                cause=e
            )
            error.add_suggestion("Try regular translation instead")
            
            yield TranslationResult(
                success=False,
                code=None,
                errors=[error.format_error()],
                warnings=[],
                metadata={'streaming_error': True}
            )