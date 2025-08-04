"""
Streaming Translator for real-time pseudocode translation

This module provides a StreamingTranslator class that enables real-time translation
with progressive results, interactive sessions, cancellation support, and event-based
progress updates.
"""

import asyncio
import threading
import time
from typing import AsyncIterator, Iterator, Optional, Callable, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
import logging

from ..models import CodeBlock, BlockType
from ..parser import ParserModule
from ..translator import TranslationManager
from ..config import TranslatorConfig
from ..exceptions import TranslatorError, StreamingError
from .chunker import CodeChunker, CodeChunk, ChunkConfig
from .buffer import StreamBuffer, BufferConfig, ContextBuffer
from .pipeline import StreamingProgress

logger = logging.getLogger(__name__)


class StreamingMode(Enum):
    """Modes for streaming translation"""
    LINE_BY_LINE = "line_by_line"
    BLOCK_BY_BLOCK = "block_by_block"
    FULL_DOCUMENT = "full_document"
    INTERACTIVE = "interactive"


class StreamingEvent(Enum):
    """Events emitted during streaming translation"""
    STARTED = "started"
    CHUNK_STARTED = "chunk_started"
    CHUNK_COMPLETED = "chunk_completed"
    TRANSLATION_STARTED = "translation_started"
    TRANSLATION_COMPLETED = "translation_completed"
    PROGRESS_UPDATE = "progress_update"
    ERROR = "error"
    WARNING = "warning"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class StreamingEventData:
    """Data associated with streaming events"""
    event: StreamingEvent
    timestamp: float = field(default_factory=time.time)
    chunk_index: Optional[int] = None
    progress: Optional[StreamingProgress] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class TranslationUpdate:
    """Incremental translation update"""
    chunk_index: int
    block_index: int
    original_content: str
    translated_content: Optional[str]
    is_partial: bool = False
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class StreamingTranslator:
    """
    Real-time streaming translator with progressive results and cancellation support
    """
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize the streaming translator
        
        Args:
            config: Translator configuration
        """
        self.config = config
        self.parser = ParserModule()
        self.chunker = CodeChunker(ChunkConfig(
            max_chunk_size=config.max_context_length,
            respect_boundaries=True,
            chunk_by_blocks=True
        ))
        
        # Translation components
        self.translation_manager = None
        self.context_buffer = ContextBuffer(window_size=2048)
        
        # Streaming state
        self.is_streaming = False
        self.is_cancelled = False
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        
        # Event system
        self.event_listeners = []
        self.event_queue = Queue()
        self._event_thread = None
        
        # Progress tracking
        self.current_progress = StreamingProgress()
        
        # Results buffer
        self.result_buffer = StreamBuffer(BufferConfig(
            max_size_mb=100,
            enable_compression=True
        ))
        
        # Interactive mode state
        self.interactive_session = None
        
    def add_event_listener(self, listener: Callable[[StreamingEventData], None]):
        """
        Add an event listener for streaming events
        
        Args:
            listener: Callback function for events
        """
        self.event_listeners.append(listener)
        
    def remove_event_listener(self, listener: Callable[[StreamingEventData], None]):
        """Remove an event listener"""
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
    
    async def translate_stream_async(
        self,
        input_stream: AsyncIterator[str],
        mode: StreamingMode = StreamingMode.BLOCK_BY_BLOCK,
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> AsyncIterator[str]:
        """
        Asynchronously translate a stream of input
        
        Args:
            input_stream: Async iterator of input text
            mode: Streaming mode to use
            on_update: Callback for translation updates
            
        Yields:
            Translated code chunks
        """
        self._start_streaming()
        
        try:
            # Initialize translation manager
            self.translation_manager = TranslationManager(self.config)
            
            # Collect input based on mode
            if mode == StreamingMode.LINE_BY_LINE:
                async for translated in self._translate_line_by_line_async(
                    input_stream, on_update
                ):
                    yield translated
                    
            elif mode == StreamingMode.BLOCK_BY_BLOCK:
                async for translated in self._translate_block_by_block_async(
                    input_stream, on_update
                ):
                    yield translated
                    
            elif mode == StreamingMode.FULL_DOCUMENT:
                # Collect all input first
                full_input = []
                async for chunk in input_stream:
                    full_input.append(chunk)
                    if self._check_cancelled():
                        return
                
                # Translate as complete document
                full_text = ''.join(full_input)
                async for translated in self._translate_full_document_async(
                    full_text, on_update
                ):
                    yield translated
                    
            elif mode == StreamingMode.INTERACTIVE:
                async for translated in self._translate_interactive_async(
                    input_stream, on_update
                ):
                    yield translated
                    
        except Exception as e:
            self._emit_event(StreamingEventData(
                event=StreamingEvent.ERROR,
                error=str(e)
            ))
            raise StreamingError(f"Streaming translation failed: {e}")
            
        finally:
            self._stop_streaming()
            if self.translation_manager:
                self.translation_manager.shutdown()
    
    def translate_stream(
        self,
        input_stream: Iterator[str],
        mode: StreamingMode = StreamingMode.BLOCK_BY_BLOCK,
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> Iterator[str]:
        """
        Synchronously translate a stream of input
        
        Args:
            input_stream: Iterator of input text
            mode: Streaming mode to use
            on_update: Callback for translation updates
            
        Yields:
            Translated code chunks
        """
        self._start_streaming()
        
        try:
            # Initialize translation manager
            self.translation_manager = TranslationManager(self.config)
            
            if mode == StreamingMode.LINE_BY_LINE:
                yield from self._translate_line_by_line(input_stream, on_update)
                
            elif mode == StreamingMode.BLOCK_BY_BLOCK:
                yield from self._translate_block_by_block(input_stream, on_update)
                
            elif mode == StreamingMode.FULL_DOCUMENT:
                # Collect all input first
                full_text = ''.join(input_stream)
                yield from self._translate_full_document(full_text, on_update)
                
            elif mode == StreamingMode.INTERACTIVE:
                yield from self._translate_interactive(input_stream, on_update)
                
        except Exception as e:
            self._emit_event(StreamingEventData(
                event=StreamingEvent.ERROR,
                error=str(e)
            ))
            raise StreamingError(f"Streaming translation failed: {e}")
            
        finally:
            self._stop_streaming()
            if self.translation_manager:
                self.translation_manager.shutdown()
    
    def _translate_line_by_line(
        self,
        input_stream: Iterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> Iterator[str]:
        """Translate input line by line"""
        line_buffer = []
        chunk_index = 0
        
        for line in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            
            # Add line to buffer
            line_buffer.append(line)
            
            # Check if we have a complete statement
            if self._is_complete_statement(''.join(line_buffer)):
                # Process the buffer
                statement = ''.join(line_buffer)
                line_buffer.clear()
                
                # Parse and translate
                try:
                    parse_result = self.parser.get_parse_result(statement)
                    if parse_result.success:
                        for block_index, block in enumerate(parse_result.blocks):
                            translated = self._translate_block(
                                block, chunk_index, block_index
                            )
                            
                            if translated:
                                # Emit update
                                if on_update:
                                    update = TranslationUpdate(
                                        chunk_index=chunk_index,
                                        block_index=block_index,
                                        original_content=block.content,
                                        translated_content=translated,
                                        is_partial=False
                                    )
                                    on_update(update)
                                
                                yield translated + '\n'
                                
                except Exception as e:
                    logger.error(f"Error translating line: {e}")
                    self._emit_event(StreamingEventData(
                        event=StreamingEvent.WARNING,
                        warning=f"Failed to translate line: {str(e)}"
                    ))
                
                chunk_index += 1
        
        # Process any remaining lines
        if line_buffer and not self._check_cancelled():
            remaining = ''.join(line_buffer)
            try:
                parse_result = self.parser.get_parse_result(remaining)
                if parse_result.success:
                    for block in parse_result.blocks:
                        translated = self._translate_block(
                            block, chunk_index, 0
                        )
                        if translated:
                            yield translated + '\n'
            except Exception as e:
                logger.error(f"Error processing remaining lines: {e}")
    
    def _translate_block_by_block(
        self,
        input_stream: Iterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> Iterator[str]:
        """Translate input block by block"""
        # Accumulate input
        accumulated_input = []
        
        for chunk in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            accumulated_input.append(chunk)
            
            # Try to parse accumulated input
            current_input = ''.join(accumulated_input)
            
            # Check if we have complete blocks
            try:
                blocks = self.parser._identify_blocks(current_input)
                
                # Process complete blocks (all but the last one)
                if len(blocks) > 1:
                    for i, block_text in enumerate(blocks[:-1]):
                        if not block_text.strip():
                            continue
                        
                        # Parse and translate the block
                        parse_result = self.parser.get_parse_result(block_text)
                        if parse_result.success:
                            for block_index, block in enumerate(parse_result.blocks):
                                translated = self._translate_block(
                                    block, i, block_index
                                )
                                
                                if translated:
                                    # Emit update
                                    if on_update:
                                        update = TranslationUpdate(
                                            chunk_index=i,
                                            block_index=block_index,
                                            original_content=block.content,
                                            translated_content=translated
                                        )
                                        on_update(update)
                                    
                                    yield translated + '\n\n'
                    
                    # Keep only the last incomplete block
                    accumulated_input = [blocks[-1]]
                    
            except Exception as e:
                logger.warning(f"Error parsing blocks: {e}")
        
        # Process final accumulated input
        if accumulated_input and not self._check_cancelled():
            final_input = ''.join(accumulated_input)
            try:
                parse_result = self.parser.get_parse_result(final_input)
                if parse_result.success:
                    for block in parse_result.blocks:
                        translated = self._translate_block(block, -1, 0)
                        if translated:
                            yield translated + '\n'
            except Exception as e:
                logger.error(f"Error processing final input: {e}")
    
    def _translate_full_document(
        self,
        full_text: str,
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> Iterator[str]:
        """Translate complete document with streaming output"""
        # Chunk the document
        chunks = self.chunker.chunk_code(full_text)
        self.current_progress.total_chunks = len(chunks)
        
        for chunk in chunks:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            
            self.current_progress.current_chunk = chunk.chunk_index
            self._emit_event(StreamingEventData(
                event=StreamingEvent.CHUNK_STARTED,
                chunk_index=chunk.chunk_index,
                progress=self.current_progress
            ))
            
            # Parse chunk
            parse_result = self.parser.get_parse_result(chunk.content)
            
            if parse_result.success:
                chunk_translations = []
                
                for block_index, block in enumerate(parse_result.blocks):
                    translated = self._translate_block(
                        block, chunk.chunk_index, block_index
                    )
                    
                    if translated:
                        chunk_translations.append(translated)
                        
                        # Emit update
                        if on_update:
                            update = TranslationUpdate(
                                chunk_index=chunk.chunk_index,
                                block_index=block_index,
                                original_content=block.content,
                                translated_content=translated
                            )
                            on_update(update)
                
                # Yield assembled chunk
                if chunk_translations:
                    yield '\n\n'.join(chunk_translations) + '\n\n'
            
            self.current_progress.processed_chunks += 1
            self._emit_event(StreamingEventData(
                event=StreamingEvent.CHUNK_COMPLETED,
                chunk_index=chunk.chunk_index,
                progress=self.current_progress
            ))
    
    def _translate_interactive(
        self,
        input_stream: Iterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> Iterator[str]:
        """Interactive translation mode"""
        session_context = []
        interaction_count = 0
        
        for user_input in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            
            # Add to session context
            session_context.append(f"# User input {interaction_count}:\n{user_input}")
            
            # Build context for translation
            context = {
                'mode': 'interactive',
                'session_history': '\n'.join(session_context[-5:]),  # Last 5 interactions
                'interaction_count': interaction_count
            }
            
            # Translate with context
            try:
                # Parse input
                parse_result = self.parser.get_parse_result(user_input)
                
                if parse_result.success:
                    translations = []
                    
                    for block in parse_result.blocks:
                        if block.type == BlockType.ENGLISH:
                            translated = self.translation_manager.llm_interface.translate(
                                instruction=block.content,
                                context=context
                            )
                        else:
                            translated = block.content
                        
                        translations.append(translated)
                        
                        # Emit update
                        if on_update:
                            update = TranslationUpdate(
                                chunk_index=interaction_count,
                                block_index=0,
                                original_content=user_input,
                                translated_content=translated,
                                metadata={'interactive': True}
                            )
                            on_update(update)
                    
                    # Yield response
                    response = '\n'.join(translations)
                    yield f"# Translation {interaction_count}:\n{response}\n\n"
                    
                    # Add translation to context
                    session_context.append(f"# Translation {interaction_count}:\n{response}")
                    
            except Exception as e:
                error_msg = f"# Error: Failed to translate - {str(e)}\n\n"
                yield error_msg
                session_context.append(error_msg)
            
            interaction_count += 1
    
    def _translate_block(
        self,
        block: CodeBlock,
        chunk_index: int,
        block_index: int
    ) -> Optional[str]:
        """Translate a single block"""
        try:
            self._emit_event(StreamingEventData(
                event=StreamingEvent.TRANSLATION_STARTED,
                chunk_index=chunk_index,
                data={'block_type': block.type.value}
            ))
            
            if block.type == BlockType.ENGLISH:
                # Build context from buffer
                context = self._build_context()
                
                # Translate
                translated = self.translation_manager.llm_interface.translate(
                    instruction=block.content,
                    context=context
                )
                
                # Update context buffer
                self.context_buffer.add_context(translated)
                
                self._emit_event(StreamingEventData(
                    event=StreamingEvent.TRANSLATION_COMPLETED,
                    chunk_index=chunk_index
                ))
                
                return translated
                
            elif block.type == BlockType.PYTHON:
                # Python blocks pass through
                self.context_buffer.add_context(block.content)
                return block.content
                
            elif block.type == BlockType.COMMENT:
                # Include comments
                return block.content
                
        except Exception as e:
            logger.error(f"Error translating block: {e}")
            self._emit_event(StreamingEventData(
                event=StreamingEvent.WARNING,
                warning=f"Failed to translate block: {str(e)}",
                chunk_index=chunk_index
            ))
            return None
    
    def _build_context(self) -> Dict[str, Any]:
        """Build translation context from buffer"""
        return {
            'code': self.context_buffer.get_context(),
            'streaming': True,
            'mode': 'real-time'
        }
    
    def _is_complete_statement(self, text: str) -> bool:
        """Check if text contains a complete statement"""
        # Simple heuristic - can be improved
        text = text.strip()
        if not text:
            return False
            
        # Check for complete lines
        if text.endswith(':'):
            # Start of a block, need more
            return False
        
        # Check for balanced delimiters
        open_parens = text.count('(') - text.count(')')
        open_brackets = text.count('[') - text.count(']')
        open_braces = text.count('{') - text.count('}')
        
        if open_parens > 0 or open_brackets > 0 or open_braces > 0:
            return False
        
        # Check for continuation
        if text.endswith('\\'):
            return False
        
        return True
    
    def cancel(self):
        """Cancel the streaming translation"""
        self.is_cancelled = True
        self._cancel_event.set()
        self._emit_event(StreamingEventData(event=StreamingEvent.CANCELLED))
    
    def pause(self):
        """Pause the streaming translation"""
        self._pause_event.clear()
    
    def resume(self):
        """Resume the streaming translation"""
        self._pause_event.set()
    
    def _check_cancelled(self) -> bool:
        """Check if translation is cancelled"""
        return self.is_cancelled or self._cancel_event.is_set()
    
    def _wait_if_paused(self):
        """Wait if translation is paused"""
        self._pause_event.wait()
    
    def _start_streaming(self):
        """Initialize streaming state"""
        self.is_streaming = True
        self.is_cancelled = False
        self._cancel_event.clear()
        self._pause_event.set()
        self.current_progress = StreamingProgress()
        
        # Start event processing thread
        self._event_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self._event_thread.start()
        
        self._emit_event(StreamingEventData(event=StreamingEvent.STARTED))
    
    def _stop_streaming(self):
        """Clean up streaming state"""
        self.is_streaming = False
        
        if not self.is_cancelled:
            self._emit_event(StreamingEventData(
                event=StreamingEvent.COMPLETED,
                progress=self.current_progress
            ))
        
        # Stop event thread
        if self._event_thread:
            self.event_queue.put(None)  # Sentinel value
            self._event_thread.join(timeout=1)
    
    def _emit_event(self, event_data: StreamingEventData):
        """Emit an event to all listeners"""
        self.event_queue.put(event_data)
    
    def _process_events(self):
        """Process events in a separate thread"""
        while self.is_streaming:
            try:
                event_data = self.event_queue.get(timeout=0.1)
                if event_data is None:  # Sentinel value
                    break
                    
                # Notify all listeners
                for listener in self.event_listeners:
                    try:
                        listener(event_data)
                    except Exception as e:
                        logger.error(f"Error in event listener: {e}")
                        
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing events: {e}")
    
    # Async versions of translation methods
    async def _translate_line_by_line_async(
        self,
        input_stream: AsyncIterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> AsyncIterator[str]:
        """Async version of line-by-line translation"""
        line_buffer = []
        chunk_index = 0
        
        async for line in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            
            line_buffer.append(line)
            
            if self._is_complete_statement(''.join(line_buffer)):
                statement = ''.join(line_buffer)
                line_buffer.clear()
                
                # Process in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                translated = await loop.run_in_executor(
                    None,
                    self._process_statement,
                    statement,
                    chunk_index,
                    on_update
                )
                
                if translated:
                    yield translated
                
                chunk_index += 1
    
    async def _translate_block_by_block_async(
        self,
        input_stream: AsyncIterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> AsyncIterator[str]:
        """Async version of block-by-block translation"""
        accumulated_input = []
        
        async for chunk in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            accumulated_input.append(chunk)
            
            # Process in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._process_accumulated_blocks,
                accumulated_input,
                on_update
            )
            
            if result:
                translated, remaining = result
                if translated:
                    for t in translated:
                        yield t
                accumulated_input = remaining
    
    async def _translate_full_document_async(
        self,
        full_text: str,
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> AsyncIterator[str]:
        """Async version of full document translation"""
        # Process in thread pool
        loop = asyncio.get_event_loop()
        
        # Use sync generator in thread
        def generate():
            return list(self._translate_full_document(full_text, on_update))
        
        results = await loop.run_in_executor(None, generate)
        
        for result in results:
            if self._check_cancelled():
                break
            yield result
    
    async def _translate_interactive_async(
        self,
        input_stream: AsyncIterator[str],
        on_update: Optional[Callable[[TranslationUpdate], None]] = None
    ) -> AsyncIterator[str]:
        """Async version of interactive translation"""
        session_context = []
        interaction_count = 0
        
        async for user_input in input_stream:
            if self._check_cancelled():
                break
                
            self._wait_if_paused()
            
            # Process in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._process_interactive_input,
                user_input,
                session_context,
                interaction_count,
                on_update
            )
            
            if response:
                yield response
                session_context.append(f"# User {interaction_count}: {user_input}")
                session_context.append(f"# Assistant {interaction_count}: {response}")
            
            interaction_count += 1
    
    def _process_statement(
        self,
        statement: str,
        chunk_index: int,
        on_update: Optional[Callable[[TranslationUpdate], None]]
    ) -> Optional[str]:
        """Process a single statement"""
        try:
            parse_result = self.parser.get_parse_result(statement)
            if parse_result.success:
                translations = []
                for block_index, block in enumerate(parse_result.blocks):
                    translated = self._translate_block(block, chunk_index, block_index)
                    if translated:
                        translations.append(translated)
                        if on_update:
                            update = TranslationUpdate(
                                chunk_index=chunk_index,
                                block_index=block_index,
                                original_content=block.content,
                                translated_content=translated
                            )
                            on_update(update)
                
                return '\n'.join(translations) + '\n' if translations else None
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            return None
    
    def _process_accumulated_blocks(
        self,
        accumulated_input: List[str],
        on_update: Optional[Callable[[TranslationUpdate], None]]
    ) -> Optional[tuple]:
        """Process accumulated blocks and return translated and remaining"""
        current_input = ''.join(accumulated_input)
        
        try:
            blocks = self.parser._identify_blocks(current_input)
            
            if len(blocks) > 1:
                translated = []
                
                for i, block_text in enumerate(blocks[:-1]):
                    if not block_text.strip():
                        continue
                    
                    parse_result = self.parser.get_parse_result(block_text)
                    if parse_result.success:
                        block_translations = []
                        for block_index, block in enumerate(parse_result.blocks):
                            t = self._translate_block(block, i, block_index)
                            if t:
                                block_translations.append(t)
                                if on_update:
                                    update = TranslationUpdate(
                                        chunk_index=i,
                                        block_index=block_index,
                                        original_content=block.content,
                                        translated_content=t
                                    )
                                    on_update(update)
                        
                        if block_translations:
                            translated.append('\n'.join(block_translations) + '\n\n')
                
                return translated, [blocks[-1]]
                
        except Exception as e:
            logger.warning(f"Error processing blocks: {e}")
        
        return None
    
    def _process_interactive_input(
        self,
        user_input: str,
        session_context: List[str],
        interaction_count: int,
        on_update: Optional[Callable[[TranslationUpdate], None]]
    ) -> Optional[str]:
        """Process interactive input"""
        context = {
            'mode': 'interactive',
            'session_history': '\n'.join(session_context[-5:]),
            'interaction_count': interaction_count
        }
        
        try:
            parse_result = self.parser.get_parse_result(user_input)
            
            if parse_result.success:
                translations = []
                
                for block in parse_result.blocks:
                    if block.type == BlockType.ENGLISH:
                        translated = self.translation_manager.llm_interface.translate(
                            instruction=block.content,
                            context=context
                        )
                    else:
                        translated = block.content
                    
                    translations.append(translated)
                    
                    if on_update:
                        update = TranslationUpdate(
                            chunk_index=interaction_count,
                            block_index=0,
                            original_content=user_input,
                            translated_content=translated,
                            metadata={'interactive': True}
                        )
                        on_update(update)
                
                return '\n'.join(translations)
                
        except Exception as e:
            logger.error(f"Error in interactive translation: {e}")
            return f"Error: {str(e)}"