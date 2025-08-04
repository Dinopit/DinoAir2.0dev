"""
Streaming pipeline for memory-efficient pseudocode translation

This module provides a streaming pipeline that processes code chunks through
the translation stages while maintaining context and handling backpressure.
"""

import asyncio
import threading
from typing import Iterator, Optional, Dict, Any, Callable, List, Union
from dataclasses import dataclass, field
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import logging
import time

from ..models import CodeBlock, BlockType, ParseResult
from ..parser import ParserModule
from ..translator import TranslationManager
from ..assembler import CodeAssembler
from ..validator import Validator
from ..config import TranslatorConfig
from .chunker import CodeChunker, CodeChunk, ChunkConfig
from .buffer import StreamBuffer, BufferConfig

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for streaming pipeline"""
    enable_streaming: bool = True
    min_file_size_for_streaming: int = 1024 * 100  # 100KB
    max_concurrent_chunks: int = 3
    chunk_timeout: float = 30.0
    progress_callback_interval: float = 0.5
    maintain_context_window: bool = True
    context_window_size: int = 1024  # Characters
    enable_backpressure: bool = True
    max_queue_size: int = 10
    thread_pool_size: int = 4


@dataclass
class StreamingProgress:
    """Progress information for streaming operations"""
    total_chunks: int = 0
    processed_chunks: int = 0
    current_chunk: Optional[int] = None
    bytes_processed: int = 0
    total_bytes: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if streaming is complete"""
        return self.processed_chunks >= self.total_chunks


@dataclass
class ChunkResult:
    """Result of processing a single chunk"""
    chunk_index: int
    success: bool
    parsed_blocks: Optional[List[CodeBlock]] = None
    translated_blocks: Optional[List[CodeBlock]] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class StreamingPipeline:
    """
    Manages streaming translation pipeline with backpressure and context
    """
    
    def __init__(self, config: TranslatorConfig, stream_config: Optional[StreamConfig] = None):
        """
        Initialize streaming pipeline
        
        Args:
            config: Translator configuration
            stream_config: Streaming-specific configuration
        """
        self.config = config
        self.stream_config = stream_config or StreamConfig()
        
        # Initialize components
        self.chunker = CodeChunker(ChunkConfig(
            max_chunk_size=config.max_context_length * 2,
            respect_boundaries=True
        ))
        self.parser = ParserModule()
        self.translator = None  # Will be created per stream
        self.assembler = CodeAssembler(config)
        self.validator = Validator(config)
        
        # Streaming state
        self.buffer = StreamBuffer(BufferConfig(
            max_size_mb=50,
            enable_compression=True
        ))
        self.context_window = []
        self.chunk_queue = Queue(maxsize=self.stream_config.max_queue_size)
        self.result_queue = Queue()
        self.executor = ThreadPoolExecutor(
            max_workers=self.stream_config.thread_pool_size
        )
        
        # Progress tracking
        self.progress = StreamingProgress()
        self.progress_callbacks = []
        self._stop_event = threading.Event()
        self._progress_thread = None
        
    def should_use_streaming(self, code: str) -> bool:
        """
        Determine if streaming should be used for given code
        
        Args:
            code: Source code
            
        Returns:
            True if streaming should be used
        """
        if not self.stream_config.enable_streaming:
            return False
            
        code_size = len(code.encode('utf-8'))
        return code_size >= self.stream_config.min_file_size_for_streaming
    
    def stream_translate(self, 
                        code: str, 
                        filename: Optional[str] = None,
                        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
                        ) -> Iterator[ChunkResult]:
        """
        Stream translation of pseudocode
        
        Args:
            code: Source code to translate
            filename: Optional filename for better error reporting
            progress_callback: Optional callback for progress updates
            
        Yields:
            ChunkResult objects as chunks are processed
        """
        # Initialize translation manager for this stream
        self.translator = TranslationManager(self.config)
        
        # Setup progress tracking
        if progress_callback:
            self.progress_callbacks.append(progress_callback)
        
        # Start progress reporting thread
        self._start_progress_reporting()
        
        try:
            # Chunk the code
            chunks = list(self.chunker.stream_chunks(code, filename))
            self.progress.total_chunks = len(chunks)
            self.progress.total_bytes = len(code.encode('utf-8'))
            
            # Process chunks
            if self.stream_config.max_concurrent_chunks > 1:
                # Parallel processing
                yield from self._process_chunks_parallel(chunks)
            else:
                # Sequential processing
                yield from self._process_chunks_sequential(chunks)
                
        finally:
            # Cleanup
            self._stop_progress_reporting()
            if self.translator:
                self.translator.shutdown()
    
    def _process_chunks_sequential(self, chunks: List[CodeChunk]) -> Iterator[ChunkResult]:
        """
        Process chunks sequentially
        
        Args:
            chunks: List of code chunks
            
        Yields:
            ChunkResult objects
        """
        for chunk in chunks:
            if self._stop_event.is_set():
                break
                
            start_time = time.time()
            self.progress.current_chunk = chunk.chunk_index
            
            try:
                # Process chunk
                result = self._process_single_chunk(chunk)
                result.processing_time = time.time() - start_time
                
                # Update progress
                self.progress.processed_chunks += 1
                self.progress.bytes_processed += chunk.size
                
                if result.error:
                    self.progress.errors.append(result.error)
                self.progress.warnings.extend(result.warnings)
                
                yield result
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
                yield ChunkResult(
                    chunk_index=chunk.chunk_index,
                    success=False,
                    error=str(e),
                    processing_time=time.time() - start_time
                )
    
    def _process_chunks_parallel(self, chunks: List[CodeChunk]) -> Iterator[ChunkResult]:
        """
        Process chunks in parallel with backpressure
        
        Args:
            chunks: List of code chunks
            
        Yields:
            ChunkResult objects
        """
        # Submit initial chunks
        futures = {}
        chunk_iter = iter(chunks)
        
        # Fill initial queue
        for _ in range(min(self.stream_config.max_concurrent_chunks, len(chunks))):
            try:
                chunk = next(chunk_iter)
                future = self.executor.submit(self._process_single_chunk, chunk)
                futures[future] = chunk
            except StopIteration:
                break
        
        # Process results and submit new chunks
        while futures:
            # Wait for any future to complete
            completed = []
            for future in futures:
                if future.done():
                    completed.append(future)
            
            if not completed:
                time.sleep(0.1)
                continue
            
            for future in completed:
                chunk = futures.pop(future)
                
                try:
                    result = future.result(timeout=self.stream_config.chunk_timeout)
                    
                    # Update progress
                    self.progress.processed_chunks += 1
                    self.progress.bytes_processed += chunk.size
                    
                    if result.error:
                        self.progress.errors.append(result.error)
                    self.progress.warnings.extend(result.warnings)
                    
                    yield result
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
                    yield ChunkResult(
                        chunk_index=chunk.chunk_index,
                        success=False,
                        error=str(e)
                    )
                
                # Submit next chunk if available
                if self.stream_config.enable_backpressure:
                    # Check queue size before submitting
                    if len(futures) < self.stream_config.max_concurrent_chunks:
                        try:
                            next_chunk = next(chunk_iter)
                            future = self.executor.submit(
                                self._process_single_chunk, next_chunk
                            )
                            futures[future] = next_chunk
                        except StopIteration:
                            pass
    
    def _process_single_chunk(self, chunk: CodeChunk) -> ChunkResult:
        """
        Process a single chunk through the pipeline
        
        Args:
            chunk: Code chunk to process
            
        Returns:
            ChunkResult
        """
        start_time = time.time()
        result = ChunkResult(chunk_index=chunk.chunk_index, success=True)
        
        try:
            # Add context from previous chunks
            chunk_with_context = self._add_context_to_chunk(chunk)
            
            # Parse the chunk
            parse_result = self.parser.get_parse_result(chunk_with_context)
            
            if not parse_result.success:
                result.success = False
                result.error = f"Parse error: {parse_result.errors}"
                return result
            
            result.parsed_blocks = parse_result.blocks
            result.warnings.extend(parse_result.warnings)
            
            # Translate English blocks
            translated_blocks = []
            for block in parse_result.blocks:
                if block.type == BlockType.ENGLISH:
                    # Build translation context
                    context = self._build_translation_context(chunk.chunk_index)
                    
                    try:
                        translated_code = self.translator.llm_interface.translate(
                            instruction=block.content,
                            context=context
                        )
                        
                        # Create translated block
                        translated_block = CodeBlock(
                            type=BlockType.PYTHON,
                            content=translated_code,
                            line_numbers=block.line_numbers,
                            metadata={**block.metadata, 'translated': True},
                            context=block.context
                        )
                        translated_blocks.append(translated_block)
                        
                    except Exception as e:
                        logger.error(f"Translation error in chunk {chunk.chunk_index}: {e}")
                        result.warnings.append(f"Translation error: {str(e)}")
                        translated_blocks.append(block)  # Keep original
                else:
                    translated_blocks.append(block)
            
            result.translated_blocks = translated_blocks
            
            # Update context window
            self._update_context_window(chunk, translated_blocks)
            
            # Buffer the result
            self.buffer.add_chunk(chunk.chunk_index, result)
            
        except Exception as e:
            logger.error(f"Error in chunk {chunk.chunk_index}: {e}")
            result.success = False
            result.error = str(e)
        
        result.processing_time = time.time() - start_time
        return result
    
    def _add_context_to_chunk(self, chunk: CodeChunk) -> str:
        """
        Add context from previous chunks to current chunk
        
        Args:
            chunk: Current chunk
            
        Returns:
            Chunk content with context
        """
        if not self.stream_config.maintain_context_window:
            return chunk.content
        
        # Get context from buffer
        context_lines = []
        
        # Add previous chunk's tail if available
        if chunk.chunk_index > 0:
            prev_result = self.buffer.get_chunk(chunk.chunk_index - 1)
            if prev_result and prev_result.translated_blocks:
                # Get last few lines from previous chunk
                last_block = prev_result.translated_blocks[-1]
                context_lines.extend(
                    last_block.content.splitlines()[-10:]
                )
        
        if context_lines:
            context = '\n'.join(context_lines)
            return f"{context}\n\n# --- Chunk {chunk.chunk_index} ---\n\n{chunk.content}"
        
        return chunk.content
    
    def _build_translation_context(self, chunk_index: int) -> Dict[str, Any]:
        """
        Build context for translation
        
        Args:
            chunk_index: Current chunk index
            
        Returns:
            Context dictionary
        """
        context = {
            'chunk_index': chunk_index,
            'code': '',
            'before': '',
            'after': ''
        }
        
        # Get previous chunk's code
        if chunk_index > 0:
            prev_result = self.buffer.get_chunk(chunk_index - 1)
            if prev_result and prev_result.translated_blocks:
                prev_code = '\n'.join(
                    block.content for block in prev_result.translated_blocks
                    if block.type == BlockType.PYTHON
                )
                context['before'] = prev_code[-self.stream_config.context_window_size:]
                context['code'] = context['before']
        
        return context
    
    def _update_context_window(self, chunk: CodeChunk, blocks: List[CodeBlock]):
        """
        Update the context window with processed blocks
        
        Args:
            chunk: Processed chunk
            blocks: Translated blocks
        """
        # Keep a sliding window of recent code
        for block in blocks:
            if block.type == BlockType.PYTHON:
                self.context_window.append({
                    'chunk_index': chunk.chunk_index,
                    'content': block.content,
                    'metadata': block.metadata
                })
        
        # Limit context window size
        max_items = 10
        if len(self.context_window) > max_items:
            self.context_window = self.context_window[-max_items:]
    
    def assemble_streamed_code(self) -> str:
        """
        Assemble all streamed chunks into final code
        
        Returns:
            Complete assembled code
        """
        all_blocks = []
        
        # Get all chunks from buffer in order
        for i in range(self.progress.total_chunks):
            result = self.buffer.get_chunk(i)
            if result and result.translated_blocks:
                all_blocks.extend(result.translated_blocks)
        
        # Use assembler to create final code
        return self.assembler.assemble(all_blocks)
    
    def _start_progress_reporting(self):
        """Start the progress reporting thread"""
        self._stop_event.clear()
        self._progress_thread = threading.Thread(
            target=self._progress_reporter,
            daemon=True
        )
        self._progress_thread.start()
    
    def _stop_progress_reporting(self):
        """Stop the progress reporting thread"""
        self._stop_event.set()
        if self._progress_thread:
            self._progress_thread.join(timeout=1)
    
    def _progress_reporter(self):
        """Thread function for reporting progress"""
        while not self._stop_event.is_set():
            # Report progress to all callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
            
            # Wait before next update
            self._stop_event.wait(self.stream_config.progress_callback_interval)
    
    def cancel_streaming(self):
        """Cancel ongoing streaming operation"""
        self._stop_event.set()
        self.executor.shutdown(wait=False)
        logger.info("Streaming operation cancelled")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """
        Get current memory usage statistics
        
        Returns:
            Memory usage in bytes
        """
        return {
            'buffer_size': self.buffer.get_size(),
            'context_window_size': sum(
                len(item['content'].encode('utf-8'))
                for item in self.context_window
            ),
            'queue_size': self.chunk_queue.qsize() * 4096  # Estimate
        }