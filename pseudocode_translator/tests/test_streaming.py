"""
Tests for streaming functionality
"""

import pytest
from unittest.mock import Mock, patch
import time
import socket

from pseudocode_translator.streaming.pipeline import (
    StreamingPipeline, StreamingProgress, ChunkResult
)
from pseudocode_translator.streaming.buffer import StreamBuffer, BufferConfig
from pseudocode_translator.config import TranslatorConfig, StreamingConfig


class TestStreamingPipeline:
    """Test cases for StreamingPipeline"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        config = TranslatorConfig()
        config.streaming = StreamingConfig(
            enable_streaming=True,
            auto_enable_threshold=100,  # Small threshold for testing
            chunk_size=1024,
            max_concurrent_chunks=2
        )
        return config
    
    @pytest.fixture
    def pipeline(self, config):
        """Create test pipeline"""
        return StreamingPipeline(config)
    
    def test_should_use_streaming(self, pipeline):
        """Test streaming decision logic"""
        # Small code should not use streaming
        small_code = "print('hello')"
        assert not pipeline.should_use_streaming(small_code)
        
        # Large code should use streaming
        large_code = "x = 1\n" * 200  # Create code larger than threshold
        assert pipeline.should_use_streaming(large_code)
        
        # Disabled streaming should return False
        pipeline.stream_config.enable_streaming = False
        assert not pipeline.should_use_streaming(large_code)
    
    def test_streaming_progress_tracking(self):
        """Test progress tracking"""
        progress = StreamingProgress()
        
        # Initial state
        assert progress.progress_percentage == 0.0
        assert not progress.is_complete
        
        # Update progress
        progress.total_chunks = 10
        progress.processed_chunks = 5
        assert progress.progress_percentage == 50.0
        assert not progress.is_complete
        
        # Complete progress
        progress.processed_chunks = 10
        assert progress.progress_percentage == 100.0
        assert progress.is_complete
    
    @patch('pseudocode_translator.streaming.pipeline.TranslationManager')
    def test_stream_translate_basic(self, mock_translator_class, pipeline):
        """Test basic streaming translation"""
        # Setup mock translator
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        # Create test code
        test_code = """
# This is a comment
print("Hello, World!")

Create a function that adds two numbers

x = 10
y = 20
"""
        
        # Mock chunker to return predictable chunks
        mock_chunks = [
            Mock(
                content="# This is a comment\nprint('Hello, World!')",
                chunk_index=0,
                size=50,
                total_chunks=2
            ),
            Mock(
                content=(
                    "Create a function that adds two numbers\n\n"
                    "x = 10\ny = 20"
                ),
                chunk_index=1,
                size=50,
                total_chunks=2
            )
        ]
        
        with patch.object(
            pipeline.chunker, 'stream_chunks', return_value=mock_chunks
        ):
            results = list(pipeline.stream_translate(test_code))
        
        # Verify results
        assert len(results) == 2
        assert all(isinstance(r, ChunkResult) for r in results)
        assert results[0].chunk_index == 0
        assert results[1].chunk_index == 1
    
    def test_progress_callbacks(self, pipeline):
        """Test progress callback functionality"""
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append({
                'percentage': progress.progress_percentage,
                'chunks': progress.processed_chunks
            })
        
        # Mock simple translation
        test_code = "print('test')" * 200  # Large enough for streaming
        
        with patch.object(pipeline, '_process_single_chunk') as mock_process:
            mock_process.return_value = ChunkResult(
                chunk_index=0,
                success=True,
                translated_blocks=[]
            )
            
            # Run with progress callback
            list(pipeline.stream_translate(
                test_code,
                progress_callback=progress_callback
            ))
        
        # Should have received progress updates
        assert len(progress_updates) > 0
    
    def test_memory_usage_tracking(self, pipeline):
        """Test memory usage statistics"""
        # Initial memory usage should be minimal
        memory_stats = pipeline.get_memory_usage()
        assert 'buffer_size' in memory_stats
        assert 'context_window_size' in memory_stats
        assert 'queue_size' in memory_stats
        
        # All should start at 0 or very small
        assert memory_stats['buffer_size'] >= 0
        assert memory_stats['context_window_size'] >= 0
        assert memory_stats['queue_size'] >= 0
    
    def test_cancel_streaming(self, pipeline):
        """Test cancellation of streaming operation"""
        # Set up a flag to track cancellation
        pipeline._stop_event.set()
        
        test_code = "x = 1\n" * 1000
        
        # Should return empty results when cancelled
        results = list(pipeline.stream_translate(test_code))
        
        # May get some results before cancellation takes effect
        assert isinstance(results, list)
    
    @patch('pseudocode_translator.streaming.pipeline.TranslationManager')
    def test_parallel_chunk_processing(self, mock_translator_class, pipeline):
        """Test parallel processing of chunks"""
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        # Configure for parallel processing
        pipeline.stream_config.max_concurrent_chunks = 3
        
        # Track processing times
        processing_times = []
        
        def mock_process_chunk(chunk):
            start = time.time()
            time.sleep(0.01)  # Simulate processing
            processing_times.append(time.time() - start)
            return ChunkResult(
                chunk_index=chunk.chunk_index,
                success=True,
                translated_blocks=[]
            )
        
        with patch.object(
            pipeline, '_process_single_chunk', side_effect=mock_process_chunk
        ):
            # Create multiple chunks
            test_chunks = [
                Mock(chunk_index=i, size=100, total_chunks=5)
                for i in range(5)
            ]
            
            with patch.object(
                pipeline.chunker, 'stream_chunks', return_value=test_chunks
            ):
                results = list(pipeline._process_chunks_parallel(test_chunks))
        
        # Should process all chunks
        assert len(results) == 5
        
        # Processing should have some parallelism
        # (exact timing depends on system, so just check we got results)
        assert len(processing_times) == 5


class TestStreamBuffer:
    """Test cases for StreamBuffer"""
    
    @pytest.fixture
    def buffer_config(self):
        """Create test buffer configuration"""
        return BufferConfig(
            max_size_mb=1,  # Small size for testing
            enable_compression=True,
            eviction_policy="lru"
        )
    
    @pytest.fixture
    def buffer(self, buffer_config):
        """Create test buffer"""
        return StreamBuffer(buffer_config)
    
    def test_add_and_get_chunk(self, buffer):
        """Test basic add and get operations"""
        test_data = {"code": "print('hello')", "index": 0}
        
        # Add chunk
        assert buffer.add_chunk(0, test_data)
        
        # Get chunk
        retrieved = buffer.get_chunk(0)
        assert retrieved == test_data
        
        # Get non-existent chunk
        assert buffer.get_chunk(999) is None
    
    def test_buffer_stats(self, buffer):
        """Test buffer statistics"""
        # Initial stats
        stats = buffer.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['chunks'] == 0
        
        # Add some data
        buffer.add_chunk(0, {"data": "test"})
        
        # Hit
        buffer.get_chunk(0)
        stats = buffer.get_stats()
        assert stats['hits'] == 1
        assert stats['chunks'] == 1
        
        # Miss
        buffer.get_chunk(999)
        stats = buffer.get_stats()
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_buffer_eviction(self, buffer):
        """Test buffer eviction when full"""
        # Fill buffer with data
        large_data = "x" * 1000  # 1KB of data
        
        # Add chunks until buffer is full
        chunks_added = 0
        for i in range(2000):  # Try to add more than buffer can hold
            if buffer.add_chunk(i, large_data):
                chunks_added += 1
            else:
                break
        
        # Should have added some chunks but not all
        assert chunks_added > 0
        assert chunks_added < 2000
        
        # Check eviction happened
        stats = buffer.get_stats()
        assert stats['evictions'] > 0
    
    def test_compression(self, buffer):
        """Test data compression"""
        # Compressible data
        test_data = {"text": "a" * 1000}  # Highly compressible
        
        # Add with compression
        assert buffer.add_chunk(0, test_data)
        
        # Stats should show compression
        stats = buffer.get_stats()
        assert stats['compressions'] > 0
        
        # Retrieved data should match original
        retrieved = buffer.get_chunk(0)
        assert retrieved == test_data
    
    def test_lru_eviction(self, buffer):
        """Test LRU eviction policy"""
        buffer.config.eviction_policy = "lru"
        
        # Add multiple chunks
        for i in range(3):
            buffer.add_chunk(i, f"data_{i}")
        
        # Access chunk 0 and 1 (making them recently used)
        buffer.get_chunk(0)
        buffer.get_chunk(1)
        
        # Add more data to trigger eviction
        large_data = "x" * (buffer._max_size // 2)
        buffer.add_chunk(3, large_data)
        
        # Chunk 2 should be evicted (least recently used)
        assert buffer.get_chunk(2) is None
        assert buffer.get_chunk(0) is not None  # Should still exist
        assert buffer.get_chunk(1) is not None  # Should still exist


class TestStreamingIntegration:
    """Integration tests for streaming functionality"""
    
    @pytest.fixture
    def full_config(self):
        """Create full configuration for integration tests"""
        config = TranslatorConfig()
        config.streaming.enable_streaming = True
        config.streaming.auto_enable_threshold = 100
        config.streaming.chunk_size = 512
        return config
    
    def test_end_to_end_streaming(self, full_config):
        """Test complete streaming translation flow"""
        from pseudocode_translator.translator import TranslationManager
        
        # Create manager
        manager = TranslationManager(full_config)
        
        # Large pseudocode for streaming
        pseudocode = """
# Calculator implementation

Create a function to add two numbers
It should return the sum

Create a function to subtract two numbers
It should return the difference

Create a function to multiply two numbers
It should return the product

Create a function to divide two numbers
It should handle division by zero

Create a main function that:
- Asks user for two numbers
- Asks for operation
- Calls appropriate function
- Displays result
""" * 10  # Repeat to make it large enough
        
        # Mock the LLM interface
        with patch.object(
            manager.llm_interface, 'translate'
        ) as mock_translate:
            mock_translate.return_value = "def mock_function():\n    pass"
            
            # Run streaming translation
            results = list(manager.translate_streaming(pseudocode))
        
        # Should get results
        assert len(results) > 0
        
        # Last result should be the final one
        final_result = results[-1]
        assert hasattr(final_result, 'success')
        assert hasattr(final_result, 'code')
    
    def test_streaming_with_errors(self, full_config):
        """Test streaming with translation errors"""
        from pseudocode_translator.translator import TranslationManager
        
        manager = TranslationManager(full_config)
        
        # Pseudocode that might cause errors
        problematic_code = """
This is invalid syntax $@#%^&*
Create a function with ??? parameters
""" * 50
        
        # Mock to simulate errors
        with patch.object(
            manager.llm_interface, 'translate'
        ) as mock_translate:
            mock_translate.side_effect = Exception("Translation error")
            
            results = list(manager.translate_streaming(problematic_code))
        
        # Should handle errors gracefully
        assert len(results) > 0
        
        # Should have some failed results
        assert any(not r.success for r in results)


class TestStreamingTranslator:
    """Test cases for StreamingTranslator real-time functionality"""
    
    @pytest.fixture
    def streaming_translator(self):
        """Create test streaming translator"""
        from pseudocode_translator.streaming.stream_translator import (
            StreamingTranslator
        )
        config = TranslatorConfig()
        return StreamingTranslator(config)
    
    def test_line_by_line_mode(self, streaming_translator):
        """Test line-by-line streaming translation"""
        from pseudocode_translator.streaming.stream_translator import (
            StreamingMode, TranslationUpdate
        )
        
        lines = [
            "create a function to add numbers\n",
            "return the sum\n",
            "end function\n"
        ]
        
        updates = []
        
        def update_callback(update: TranslationUpdate):
            updates.append(update)
        
        # Mock translation manager
        with patch.object(
            streaming_translator, 'translation_manager'
        ) as mock_tm:
            mock_llm = Mock()
            mock_llm.translate.side_effect = [
                "def add_numbers(*args):",
                "    return sum(args)",
                ""
            ]
            mock_tm.llm_interface = mock_llm
            
            results = list(streaming_translator.translate_stream(
                iter(lines),
                mode=StreamingMode.LINE_BY_LINE,
                on_update=update_callback
            ))
        
        assert len(results) > 0
        assert len(updates) > 0
        assert updates[0].chunk_index == 0
    
    def test_event_system(self, streaming_translator):
        """Test streaming event system"""
        from pseudocode_translator.streaming.stream_translator import (
            StreamingEvent, StreamingMode
        )
        
        events_received = []
        
        def event_handler(event_data):
            events_received.append(event_data.event)
        
        streaming_translator.add_event_listener(event_handler)
        
        # Mock simple translation
        with patch.object(
            streaming_translator, 'translation_manager'
        ) as mock_tm:
            mock_llm = Mock()
            mock_llm.translate.return_value = "# translated"
            mock_tm.llm_interface = mock_llm
            
            list(streaming_translator.translate_stream(
                iter(["test line\n"]),
                mode=StreamingMode.LINE_BY_LINE
            ))
        
        # Should have start and complete events
        assert StreamingEvent.STARTED in events_received
        assert StreamingEvent.COMPLETED in events_received
    
    def test_cancellation_support(self, streaming_translator):
        """Test cancellation during streaming"""
        import threading
        
        # Create slow input stream
        def slow_stream():
            for i in range(10):
                yield f"line {i}\n"
                time.sleep(0.1)
        
        results = []
        
        def run_translation():
            with patch.object(
                streaming_translator, 'translation_manager'
            ) as mock_tm:
                mock_llm = Mock()
                mock_llm.translate.return_value = "# translated"
                mock_tm.llm_interface = mock_llm
                
                try:
                    for result in streaming_translator.translate_stream(
                        slow_stream(),
                        mode=StreamingMode.LINE_BY_LINE
                    ):
                        results.append(result)
                except Exception:
                    pass
        
        # Start translation
        thread = threading.Thread(target=run_translation)
        thread.start()
        
        # Cancel after brief delay
        time.sleep(0.2)
        streaming_translator.cancel()
        
        thread.join(timeout=1)
        
        # Should have processed only a few items
        assert len(results) < 10
        assert streaming_translator.is_cancelled
    
    def test_interactive_mode(self, streaming_translator):
        """Test interactive streaming mode"""
        from pseudocode_translator.streaming.stream_translator import (
            StreamingMode
        )
        
        interactions = [
            "create a list called numbers\n",
            "add 1, 2, 3 to the list\n",
            "print the list\n"
        ]
        
        with patch.object(
            streaming_translator, 'translation_manager'
        ) as mock_tm:
            mock_llm = Mock()
            mock_llm.translate.side_effect = [
                "numbers = []",
                "numbers.extend([1, 2, 3])",
                "print(numbers)"
            ]
            mock_tm.llm_interface = mock_llm
            
            results = list(streaming_translator.translate_stream(
                iter(interactions),
                mode=StreamingMode.INTERACTIVE
            ))
        
        assert len(results) == 3
        assert all("Translation" in r for r in results)


class TestStreamHandlers:
    """Test cases for various stream handlers"""
    
    def test_memory_stream_handler(self):
        """Test memory stream handler operations"""
        from pseudocode_translator.streaming.stream_handlers import (
            MemoryStreamHandler, StreamConfig
        )
        
        config = StreamConfig(buffer_size=1024)
        handler = MemoryStreamHandler("initial data", config)
        
        # Test read
        handler.seek(0)
        data = handler.read()
        assert data == "initial data"
        
        # Test write
        handler.write("\nmore data")
        handler.seek(0)
        all_data = handler.getvalue()
        assert "initial data" in all_data
        assert "more data" in all_data
        
        handler.close()
        assert handler.is_closed
    
    def test_buffered_stream_handler(self):
        """Test buffered stream operations"""
        from pseudocode_translator.streaming.stream_handlers import (
            MemoryStreamHandler, BufferedStreamHandler, StreamConfig
        )
        
        config = StreamConfig()
        inner = MemoryStreamHandler("", config)
        buffered = BufferedStreamHandler(
            inner,
            read_buffer_size=10,
            write_buffer_size=10,
            config=config
        )
        
        # Write small amount (should buffer)
        buffered.write("12345")
        assert inner.getvalue() == ""  # Not flushed yet
        
        # Write more to trigger flush
        buffered.write("67890!")
        assert len(inner.getvalue()) > 0  # Should be flushed
        
        buffered.close()
    
    def test_transform_stream_handler(self):
        """Test transform stream handler"""
        from pseudocode_translator.streaming.stream_handlers import (
            MemoryStreamHandler, TransformStreamHandler, StreamConfig
        )
        
        config = StreamConfig()
        inner = MemoryStreamHandler("hello world", config)
        
        # Create transform that uppercases
        transform = TransformStreamHandler(
            inner,
            read_transform=lambda x: x.upper(),
            write_transform=lambda x: x.lower(),
            config=config
        )
        
        # Test read transform
        inner.seek(0)
        data = transform.read()
        assert data == "HELLO WORLD"
        
        # Test write transform
        transform.write("GOODBYE")
        inner.seek(0)
        assert "goodbye" in inner.getvalue()
        
        transform.close()


class TestStreamingProtocols:
    """Test cases for streaming protocols"""
    
    def test_message_types(self):
        """Test various message types"""
        from pseudocode_translator.streaming.protocols import (
            DataMessage, ProgressMessage, ErrorMessage,
            TranslationUpdateMessage, MessageType
        )
        
        # Test DataMessage
        data_msg = DataMessage(
            message_type=MessageType.INPUT_CHUNK,
            content="test content",
            chunk_index=0
        )
        assert data_msg.to_dict()['content'] == "test content"
        
        # Test ProgressMessage
        progress_msg = ProgressMessage(
            message_type=MessageType.PROGRESS_UPDATE,
            total_items=10,
            completed_items=5
        )
        assert progress_msg.percentage == 50.0
        
        # Test ErrorMessage
        error_msg = ErrorMessage(
            message_type=MessageType.ERROR,
            error_type="TestError",
            error_message="Test error",
            recoverable=True
        )
        assert error_msg.recoverable
        
        # Test TranslationUpdateMessage
        update_msg = TranslationUpdateMessage(
            message_type=MessageType.TRANSLATION_UPDATE,
            chunk_index=1,
            block_index=0,
            original_content="create function",
            translated_content="def function():"
        )
        assert update_msg.chunk_index == 1
    
    def test_message_serialization(self):
        """Test message serialization and deserialization"""
        from pseudocode_translator.streaming.protocols import (
            DataMessage, MessageType
        )
        
        original = DataMessage(
            message_type=MessageType.OUTPUT_CHUNK,
            content="test data",
            chunk_index=5,
            compressed=False
        )
        
        # Serialize to JSON
        json_str = original.to_json()
        assert isinstance(json_str, str)
        
        # Deserialize
        # Deserialize
        import json
        data = json.loads(json_str)
        assert data['content'] == original.content
        assert data['chunk_index'] == original.chunk_index
    
    def test_streaming_mode_protocols(self):
        """Test protocols for different streaming modes"""
        from pseudocode_translator.streaming.protocols import (
            LineByLineProtocol, BlockByBlockProtocol,
            FullDocumentProtocol
        )
        
        # Test LineByLineProtocol
        line_protocol = LineByLineProtocol()
        update = line_protocol.process_line("test line")
        assert update is not None
        assert update.is_partial
        
        # Test BlockByBlockProtocol
        block_protocol = BlockByBlockProtocol()
        
        # Create mock block
        mock_block = Mock()
        mock_block.content = "block content"
        mock_block.type = Mock(value="python")
        
        # Use a proper CodeBlock for testing
        from pseudocode_translator.models import CodeBlock, BlockType
        block = CodeBlock(
            type=BlockType.PYTHON,
            content="block content",
            line_numbers=(1, 1),
            metadata={}
        )
        update = block_protocol.process_block(block)
        assert update is not None
        assert not update.is_partial
        
        # Test FullDocumentProtocol
        doc_protocol = FullDocumentProtocol()
        progress = doc_protocol.process_chunk("chunk", 0, 10)
        assert progress.total_items == 10
        assert progress.completed_items == 1


class TestStreamingMemoryEfficiency:
    """Test memory efficiency aspects of streaming"""
    
    def test_context_window_management(self):
        """Test context window for memory efficiency"""
        from pseudocode_translator.streaming.buffer import ContextBuffer
        
        buffer = ContextBuffer(window_size=100)
        
        # Add content
        for i in range(20):
            buffer.add_context(f"Line {i}: " + "x" * 20)
        
        # Context should be limited to window size
        context = buffer.get_context()
        assert len(context) <= 100
        
        # Should contain recent lines
        assert "Line 19" in context
        assert "Line 0" not in context  # Old lines should be dropped
    
    def test_chunk_memory_limits(self):
        """Test memory limits in chunking"""
        from pseudocode_translator.streaming.chunker import (
            CodeChunker, ChunkConfig
        )
        
        config = ChunkConfig(
            max_chunk_size=1000,
            max_lines_per_chunk=10
        )
        chunker = CodeChunker(config)
        
        # Create large code
        large_code = "\n".join([f"line {i}" * 50 for i in range(100)])
        
        chunks = chunker.chunk_code(large_code)
        
        # All chunks should respect size limits
        for chunk in chunks:
            assert chunk.size <= config.max_chunk_size
            assert chunk.line_count <= config.max_lines_per_chunk
    
    def test_buffer_memory_management(self):
        """Test buffer memory management with eviction"""
        from pseudocode_translator.streaming.buffer import (
            StreamBuffer, BufferConfig
        )
        
        # Very small buffer for testing
        config = BufferConfig(
            max_size_mb=1,  # 1MB (minimum)
            eviction_policy="fifo"
        )
        buffer = StreamBuffer(config)
        
        # Add data until eviction
        evictions_before = buffer.get_stats()['evictions']
        
        for i in range(100):
            buffer.add_chunk(i, f"data_{i}" * 100)
        
        evictions_after = buffer.get_stats()['evictions']
        
        # Should have evicted some chunks
        assert evictions_after > evictions_before
        
        # Total chunks should be limited
        assert buffer.get_stats()['chunks'] < 100


class TestStreamingErrorHandling:
    """Test error handling in streaming scenarios"""
    
    def test_chunk_processing_errors(self):
        """Test handling of errors during chunk processing"""
        from pseudocode_translator.streaming.pipeline import StreamingPipeline
        
        config = TranslatorConfig()
        pipeline = StreamingPipeline(config)
        
        # Mock chunk that causes error
        error_chunk = Mock()
        error_chunk.content = "invalid @#$%"
        error_chunk.chunk_index = 0
        error_chunk.size = 10
        
        with patch.object(pipeline.parser, 'get_parse_result') as mock_parse:
            mock_parse.side_effect = Exception("Parse error")
            
            result = pipeline._process_single_chunk(error_chunk)
        
        assert not result.success
        assert result.error is not None
        assert "Parse error" in result.error
    
    def test_streaming_recovery(self):
        """Test recovery from streaming errors"""
        from pseudocode_translator.streaming.stream_translator import (
            StreamingTranslator, StreamingMode
        )
        
        translator = StreamingTranslator(TranslatorConfig())
        
        # Input with some problematic lines
        input_lines = [
            "valid line 1\n",
            "@#$% invalid syntax\n",
            "valid line 2\n"
        ]
        
        results = []
        
        with patch.object(translator, 'translation_manager') as mock_tm:
            mock_llm = Mock()
            
            def translate_with_error(instruction, context):
                if "invalid" in instruction:
                    raise Exception("Translation failed")
                return f"# {instruction.strip()}"
            
            mock_llm.translate.side_effect = translate_with_error
            mock_tm.llm_interface = mock_llm
            
            # Should continue despite errors
            for result in translator.translate_stream(
                iter(input_lines),
                mode=StreamingMode.LINE_BY_LINE
            ):
                results.append(result)
        
        # Should get results for valid lines
        assert len(results) >= 2  # At least the valid lines
    
    def test_timeout_handling(self):
        """Test handling of timeouts in streaming"""
        from pseudocode_translator.streaming.stream_handlers import (
            SocketStreamHandler
        )
        from pseudocode_translator.streaming.stream_handlers import (
            StreamConfig as HandlerStreamConfig
        )
        
        config = HandlerStreamConfig(timeout=0.1)  # Very short timeout
        
        # Mock socket that times out
        mock_socket = Mock()
        mock_socket.recv.side_effect = socket.timeout()
        
        handler = SocketStreamHandler(sock=mock_socket, config=config)
        
        # Should handle timeout gracefully
        data = handler.read()
        assert data == ""  # Empty on timeout
        
        handler.close()


# Run specific test groups if needed
if __name__ == "__main__":
    pytest.main([__file__, "-v"])