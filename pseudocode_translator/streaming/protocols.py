"""
Streaming protocols and interfaces

This module defines the protocols, interfaces, and message formats for
streaming communication in the pseudocode translator.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Protocol, Optional, Dict, Any, List, Union, AsyncIterator, Iterator,
    TypeVar, TYPE_CHECKING
)
import json
import time
from datetime import datetime

from .stream_translator import StreamingMode

if TYPE_CHECKING:
    from ..models import CodeBlock


T = TypeVar('T')


class MessageType(Enum):
    """Types of streaming messages"""
    # Control messages
    START_STREAM = "start_stream"
    END_STREAM = "end_stream"
    PAUSE_STREAM = "pause_stream"
    RESUME_STREAM = "resume_stream"
    CANCEL_STREAM = "cancel_stream"
    
    # Data messages
    INPUT_CHUNK = "input_chunk"
    OUTPUT_CHUNK = "output_chunk"
    TRANSLATION_UPDATE = "translation_update"
    
    # Progress messages
    PROGRESS_UPDATE = "progress_update"
    STATUS_UPDATE = "status_update"
    
    # Error messages
    ERROR = "error"
    WARNING = "warning"
    
    # Metadata messages
    METADATA = "metadata"
    CONTEXT_UPDATE = "context_update"


@dataclass
class StreamMessage:
    """Base class for all streaming messages"""
    message_type: MessageType
    timestamp: float = field(default_factory=time.time)
    sequence_number: Optional[int] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'message_type': self.message_type.value,
            'timestamp': self.timestamp,
            'sequence_number': self.sequence_number,
            'correlation_id': self.correlation_id
        }
    
    def to_json(self) -> str:
        """Convert message to JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamMessage':
        """Create message from dictionary"""
        data['message_type'] = MessageType(data['message_type'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StreamMessage':
        """Create message from JSON"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ControlMessage(StreamMessage):
    """Control message for stream management"""
    command: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'command': self.command,
            'parameters': self.parameters
        })
        return data


@dataclass
class DataMessage(StreamMessage):
    """Data message containing content"""
    content: str = ""
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    encoding: str = "utf-8"
    compressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'content': self.content,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'encoding': self.encoding,
            'compressed': self.compressed
        })
        return data


@dataclass
class TranslationUpdateMessage(StreamMessage):
    """Translation update message"""
    chunk_index: int = 0
    block_index: int = 0
    original_content: str = ""
    translated_content: Optional[str] = None
    is_partial: bool = False
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(MessageType.TRANSLATION_UPDATE)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'chunk_index': self.chunk_index,
            'block_index': self.block_index,
            'original_content': self.original_content,
            'translated_content': self.translated_content,
            'is_partial': self.is_partial,
            'confidence': self.confidence,
            'metadata': self.metadata
        })
        return data


@dataclass
class ProgressMessage(StreamMessage):
    """Progress update message"""
    total_items: int = 0
    completed_items: int = 0
    current_item: Optional[int] = None
    percentage: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(MessageType.PROGRESS_UPDATE)
        if self.percentage is None and self.total_items > 0:
            self.percentage = (self.completed_items / self.total_items) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'current_item': self.current_item,
            'percentage': self.percentage,
            'estimated_time_remaining': self.estimated_time_remaining,
            'metadata': self.metadata
        })
        return data


@dataclass
class ErrorMessage(StreamMessage):
    """Error message"""
    error_type: str = ""
    error_message: str = ""
    error_code: Optional[str] = None
    recoverable: bool = True
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        super().__init__(MessageType.ERROR)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'recoverable': self.recoverable,
            'context': self.context,
            'stack_trace': self.stack_trace
        })
        return data


class StreamProtocol(Protocol):
    """Protocol for stream handlers"""
    
    def send_message(self, message: StreamMessage) -> None:
        """Send a message through the stream"""
        ...
    
    def receive_message(self) -> Optional[StreamMessage]:
        """Receive a message from the stream"""
        ...
    
    def close(self) -> None:
        """Close the stream"""
        ...
    
    @property
    def is_open(self) -> bool:
        """Check if stream is open"""
        ...


class AsyncStreamProtocol(Protocol):
    """Protocol for async stream handlers"""
    
    async def send_message(self, message: StreamMessage) -> None:
        """Send a message through the stream"""
        ...
    
    async def receive_message(self) -> Optional[StreamMessage]:
        """Receive a message from the stream"""
        ...
    
    async def close(self) -> None:
        """Close the stream"""
        ...
    
    @property
    def is_open(self) -> bool:
        """Check if stream is open"""
        ...


class MessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    def can_handle(self, message: StreamMessage) -> bool:
        """Check if this handler can process the message"""
        pass
    
    @abstractmethod
    def handle(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Handle the message and optionally return a response"""
        pass


class MessageRouter:
    """Routes messages to appropriate handlers"""
    
    def __init__(self):
        self.handlers: List[MessageHandler] = []
        self.default_handler: Optional[MessageHandler] = None
    
    def register_handler(self, handler: MessageHandler):
        """Register a message handler"""
        self.handlers.append(handler)
    
    def set_default_handler(self, handler: MessageHandler):
        """Set the default handler for unmatched messages"""
        self.default_handler = handler
    
    def route_message(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Route a message to the appropriate handler"""
        for handler in self.handlers:
            if handler.can_handle(message):
                return handler.handle(message)
        
        if self.default_handler:
            return self.default_handler.handle(message)
        
        return None


class StreamingProtocolAdapter:
    """Adapter for different streaming protocols"""
    
    def __init__(self, mode: StreamingMode):
        self.mode = mode
        self._message_queue: List[StreamMessage] = []
        self._sequence_number = 0
    
    def adapt_input(
        self, 
        raw_input: str,
        chunk_index: Optional[int] = None
    ) -> DataMessage:
        """Adapt raw input to protocol message"""
        self._sequence_number += 1
        
        return DataMessage(
            message_type=MessageType.INPUT_CHUNK,
            content=raw_input,
            chunk_index=chunk_index,
            sequence_number=self._sequence_number
        )
    
    def adapt_output(
        self,
        translated_content: str,
        chunk_index: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataMessage:
        """Adapt translated output to protocol message"""
        self._sequence_number += 1
        
        return DataMessage(
            message_type=MessageType.OUTPUT_CHUNK,
            content=translated_content,
            chunk_index=chunk_index,
            sequence_number=self._sequence_number
        )
    
    def create_control_message(
        self,
        command: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ControlMessage:
        """Create a control message"""
        self._sequence_number += 1
        
        message_type_map = {
            'start': MessageType.START_STREAM,
            'end': MessageType.END_STREAM,
            'pause': MessageType.PAUSE_STREAM,
            'resume': MessageType.RESUME_STREAM,
            'cancel': MessageType.CANCEL_STREAM
        }
        
        return ControlMessage(
            message_type=message_type_map.get(
                command, MessageType.START_STREAM
            ),
            command=command,
            parameters=parameters or {},
            sequence_number=self._sequence_number
        )
    
    def create_progress_message(
        self,
        total: int,
        completed: int,
        current: Optional[int] = None
    ) -> ProgressMessage:
        """Create a progress message"""
        self._sequence_number += 1
        
        return ProgressMessage(
            message_type=MessageType.PROGRESS_UPDATE,
            total_items=total,
            completed_items=completed,
            current_item=current,
            sequence_number=self._sequence_number
        )
    
    def create_error_message(
        self,
        error: Exception,
        recoverable: bool = True
    ) -> ErrorMessage:
        """Create an error message from exception"""
        self._sequence_number += 1
        
        return ErrorMessage(
            message_type=MessageType.ERROR,
            error_type=type(error).__name__,
            error_message=str(error),
            recoverable=recoverable,
            sequence_number=self._sequence_number,
            stack_trace=None  # Could add traceback if needed
        )


class StreamMessageFormatter:
    """Formats stream messages for different output formats"""
    
    @staticmethod
    def format_json(message: StreamMessage) -> str:
        """Format message as JSON"""
        return message.to_json()
    
    @staticmethod
    def format_text(message: StreamMessage) -> str:
        """Format message as human-readable text"""
        timestamp = datetime.fromtimestamp(message.timestamp).isoformat()
        
        if isinstance(message, DataMessage):
            return (
                f"[{timestamp}] {message.message_type.value}: "
                f"{message.content}"
            )
        
        elif isinstance(message, TranslationUpdateMessage):
            status = "partial" if message.is_partial else "complete"
            return (
                f"[{timestamp}] Translation {status} "
                f"(chunk {message.chunk_index}, block {message.block_index}): "
                f"{message.translated_content or 'pending'}"
            )
        
        elif isinstance(message, ProgressMessage):
            return (
                f"[{timestamp}] Progress: {message.completed_items}/"
                f"{message.total_items} ({message.percentage:.1f}%)"
            )
        
        elif isinstance(message, ErrorMessage):
            severity = "recoverable" if message.recoverable else "fatal"
            return (
                f"[{timestamp}] Error ({severity}): "
                f"{message.error_type} - {message.error_message}"
            )
        
        elif isinstance(message, ControlMessage):
            return f"[{timestamp}] Control: {message.command}"
        
        else:
            return f"[{timestamp}] {message.message_type.value}"
    
    @staticmethod
    def format_binary(message: StreamMessage) -> bytes:
        """Format message as binary data"""
        json_str = message.to_json()
        return json_str.encode('utf-8')


class StreamingProtocolHandler:
    """Handles protocol-level operations for streaming"""
    
    def __init__(
        self,
        protocol: Union[StreamProtocol, AsyncStreamProtocol],
        formatter: Optional[StreamMessageFormatter] = None
    ):
        self.protocol = protocol
        self.formatter = formatter or StreamMessageFormatter()
        self.router = MessageRouter()
        self._is_async = isinstance(protocol, AsyncStreamProtocol.__class__)
    
    def send(self, message: StreamMessage):
        """Send a message using the protocol"""
        if self._is_async:
            raise RuntimeError("Use send_async for async protocols")
        if isinstance(self.protocol, StreamProtocol.__class__):
            self.protocol.send_message(message)
    
    async def send_async(self, message: StreamMessage):
        """Send a message asynchronously"""
        if not self._is_async:
            raise RuntimeError("Use send for sync protocols")
        if hasattr(self.protocol, 'send_message'):
            await self.protocol.send_message(message)  # type: ignore
    
    def receive(self) -> Optional[StreamMessage]:
        """Receive a message using the protocol"""
        if self._is_async:
            raise RuntimeError("Use receive_async for async protocols")
        if hasattr(self.protocol, 'receive_message'):
            return self.protocol.receive_message()  # type: ignore
        return None
    
    async def receive_async(self) -> Optional[StreamMessage]:
        """Receive a message asynchronously"""
        if not self._is_async:
            raise RuntimeError("Use receive for sync protocols")
        if hasattr(self.protocol, 'receive_message'):
            return await self.protocol.receive_message()  # type: ignore
        return None
    
    def process_messages(self) -> Iterator[Optional[StreamMessage]]:
        """Process incoming messages"""
        while self.protocol.is_open:
            message = self.receive()
            if message:
                response = self.router.route_message(message)
                yield response
    
    async def process_messages_async(
        self
    ) -> AsyncIterator[Optional[StreamMessage]]:
        """Process incoming messages asynchronously"""
        while self.protocol.is_open:
            message = await self.receive_async()
            if message:
                response = self.router.route_message(message)
                yield response


# Protocol implementations for different streaming modes

class LineByLineProtocol:
    """Protocol handler for line-by-line streaming"""
    
    def __init__(self):
        self.buffer = []
        self.line_number = 0
    
    def process_line(self, line: str) -> Optional[TranslationUpdateMessage]:
        """Process a single line"""
        self.line_number += 1
        
        # Simple implementation - can be extended
        return TranslationUpdateMessage(
            message_type=MessageType.TRANSLATION_UPDATE,
            chunk_index=self.line_number,
            block_index=0,
            original_content=line,
            translated_content=None,
            is_partial=True
        )


class BlockByBlockProtocol:
    """Protocol handler for block-by-block streaming"""
    
    def __init__(self):
        self.block_buffer = []
        self.block_number = 0
    
    def process_block(
        self,
        block: 'CodeBlock'
    ) -> Optional[TranslationUpdateMessage]:
        """Process a single block"""
        self.block_number += 1
        
        return TranslationUpdateMessage(
            message_type=MessageType.TRANSLATION_UPDATE,
            chunk_index=self.block_number,
            block_index=0,
            original_content=getattr(block, 'content', ''),
            translated_content=None,
            is_partial=False,
            metadata={'block_type': getattr(block.type, 'value', 'unknown')}
        )


class FullDocumentProtocol:
    """Protocol handler for full document streaming"""
    
    def __init__(self):
        self.chunks = []
        self.total_size = 0
    
    def process_chunk(
        self,
        chunk: str,
        chunk_index: int,
        total_chunks: int
    ) -> ProgressMessage:
        """Process a document chunk"""
        self.chunks.append(chunk)
        self.total_size += len(chunk)
        
        return ProgressMessage(
            message_type=MessageType.PROGRESS_UPDATE,
            total_items=total_chunks,
            completed_items=chunk_index + 1,
            current_item=chunk_index
        )


# Helper functions for protocol operations

def create_stream_protocol(
    mode: StreamingMode,
    stream_handler: Optional[StreamProtocol] = None
) -> Union[LineByLineProtocol, BlockByBlockProtocol, FullDocumentProtocol]:
    """Create appropriate protocol handler for streaming mode"""
    if mode == StreamingMode.LINE_BY_LINE:
        return LineByLineProtocol()
    elif mode == StreamingMode.BLOCK_BY_BLOCK:
        return BlockByBlockProtocol()
    elif mode == StreamingMode.FULL_DOCUMENT:
        return FullDocumentProtocol()
    else:
        raise ValueError(f"Unsupported streaming mode: {mode}")


def negotiate_protocol(
    client_capabilities: Dict[str, Any],
    server_capabilities: Dict[str, Any]
) -> Dict[str, Any]:
    """Negotiate protocol parameters between client and server"""
    negotiated = {}
    
    # Negotiate streaming mode
    client_modes = set(client_capabilities.get('modes', []))
    server_modes = set(server_capabilities.get('modes', []))
    common_modes = client_modes & server_modes
    
    if common_modes:
        # Prefer block-by-block if available
        if StreamingMode.BLOCK_BY_BLOCK.value in common_modes:
            negotiated['mode'] = StreamingMode.BLOCK_BY_BLOCK.value
        elif StreamingMode.LINE_BY_LINE.value in common_modes:
            negotiated['mode'] = StreamingMode.LINE_BY_LINE.value
        else:
            negotiated['mode'] = list(common_modes)[0]
    else:
        negotiated['mode'] = StreamingMode.FULL_DOCUMENT.value
    
    # Negotiate chunk size
    client_chunk_size = client_capabilities.get('chunk_size', 4096)
    server_chunk_size = server_capabilities.get('chunk_size', 4096)
    negotiated['chunk_size'] = min(client_chunk_size, server_chunk_size)
    
    # Negotiate encoding
    client_encodings = client_capabilities.get('encodings', ['utf-8'])
    server_encodings = server_capabilities.get('encodings', ['utf-8'])
    common_encodings = set(client_encodings) & set(server_encodings)
    negotiated['encoding'] = (
        list(common_encodings)[0] if common_encodings else 'utf-8'
    )
    
    # Negotiate compression
    client_compression = client_capabilities.get('compression', False)
    server_compression = server_capabilities.get('compression', False)
    negotiated['compression'] = client_compression and server_compression
    
    return negotiated