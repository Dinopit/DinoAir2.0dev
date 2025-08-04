"""
Stream handlers for various input/output sources

This module provides handlers for different stream types including files,
sockets, pipes, and other I/O sources with buffering strategies.
"""

import io
import os
import socket
import threading
from typing import (
    Iterator, Optional, Union, BinaryIO, TextIO, Callable
)
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging
import select
import time
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for stream handlers"""
    buffer_size: int = 8192
    encoding: str = 'utf-8'
    timeout: Optional[float] = None
    auto_flush: bool = True
    retry_attempts: int = 3
    retry_delay: float = 0.1


class StreamHandler(ABC):
    """Abstract base class for stream handlers"""
    
    def __init__(self, config: Optional[StreamConfig] = None):
        """
        Initialize stream handler
        
        Args:
            config: Stream configuration
        """
        self.config = config or StreamConfig()
        self.is_closed = False
        
    @abstractmethod
    def read(self, size: int = -1) -> str:
        """Read data from stream"""
        pass
        
    @abstractmethod
    def write(self, data: str) -> int:
        """Write data to stream"""
        pass
        
    @abstractmethod
    def close(self):
        """Close the stream"""
        pass
        
    @abstractmethod
    def is_readable(self) -> bool:
        """Check if stream is readable"""
        pass
        
    @abstractmethod
    def is_writable(self) -> bool:
        """Check if stream is writable"""
        pass
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def __iter__(self) -> Iterator[str]:
        """Iterate over lines in stream"""
        return self
        
    def __next__(self) -> str:
        """Get next line from stream"""
        line = self.readline()
        if not line:
            raise StopIteration
        return line
        
    def readline(self, size: int = -1) -> str:
        """Read a single line from stream"""
        line = []
        while True:
            char = self.read(1)
            if not char or char == '\n':
                break
            line.append(char)
            if size > 0 and len(line) >= size:
                break
        return ''.join(line) + (char if char == '\n' else '')


class FileStreamHandler(StreamHandler):
    """Handler for file streams"""
    
    def __init__(
        self,
        filepath: Union[str, Path],
        mode: str = 'r',
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize file stream handler
        
        Args:
            filepath: Path to file
            mode: File open mode
            config: Stream configuration
        """
        super().__init__(config)
        self.filepath = Path(filepath)
        self.mode = mode
        self._file = None
        self._is_aiofiles = False
        self._open_file()
        
    def _open_file(self):
        """Open the file with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                self._file = open(
                    self.filepath,
                    self.mode,
                    encoding=(
                        self.config.encoding if 'b' not in self.mode else None
                    ),
                    buffering=self.config.buffer_size
                )
                return
            except IOError as e:
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise e
                    
    def read(self, size: int = -1) -> str:
        """Read from file"""
        if self.is_closed or not self._file:
            raise IOError("Stream is closed")
        return self._file.read(size)
        
    def write(self, data: str) -> int:
        """Write to file"""
        if self.is_closed or not self._file:
            raise IOError("Stream is closed")
        result = self._file.write(data)
        if self.config.auto_flush:
            self._file.flush()
        return result
        
    def close(self):
        """Close file"""
        if self._file and not self.is_closed:
            self._file.close()
            self.is_closed = True
            
    def is_readable(self) -> bool:
        """Check if file is readable"""
        return 'r' in self.mode and not self.is_closed
        
    def is_writable(self) -> bool:
        """Check if file is writable"""
        return ('w' in self.mode or 'a' in self.mode) and not self.is_closed
        
    def seek(self, offset: int, whence: int = 0):
        """Seek to position in file"""
        if self._file:
            self._file.seek(offset, whence)
            
    def tell(self) -> int:
        """Get current position in file"""
        if self._file:
            return self._file.tell()
        return 0


class SocketStreamHandler(StreamHandler):
    """Handler for socket streams"""
    
    def __init__(
        self,
        sock: Optional[socket.socket] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize socket stream handler
        
        Args:
            sock: Existing socket object
            host: Host to connect to (if creating new socket)
            port: Port to connect to (if creating new socket)
            config: Stream configuration
        """
        super().__init__(config)
        
        if sock:
            self.socket = sock
        elif host and port:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.config.timeout:
                self.socket.settimeout(self.config.timeout)
            self._connect(host, port)
        else:
            raise ValueError("Either socket or host/port must be provided")
            
        self._read_buffer = ""
        self._write_buffer = []
        
    def _connect(self, host: str, port: int):
        """Connect to remote host with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                self.socket.connect((host, port))
                return
            except socket.error as e:
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    raise e
                    
    def read(self, size: int = -1) -> str:
        """Read from socket"""
        if self.is_closed:
            raise IOError("Socket is closed")
            
        if size == -1:
            # Read all available data
            data = []
            while True:
                try:
                    chunk = self.socket.recv(self.config.buffer_size)
                    if not chunk:
                        break
                    data.append(chunk.decode(self.config.encoding))
                except socket.timeout:
                    break
            return ''.join(data)
        else:
            # Read specific amount
            data = self.socket.recv(size)
            return data.decode(self.config.encoding)
            
    def write(self, data: str) -> int:
        """Write to socket"""
        if self.is_closed:
            raise IOError("Socket is closed")
            
        encoded = data.encode(self.config.encoding)
        sent = self.socket.send(encoded)
        
        if self.config.auto_flush:
            self.flush()
            
        return sent
        
    def flush(self):
        """Flush write buffer"""
        # Socket sends immediately, nothing to flush
        pass
        
    def close(self):
        """Close socket"""
        if not self.is_closed and self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.socket.close()
            self.is_closed = True
            
    def is_readable(self) -> bool:
        """Check if socket is readable"""
        if self.is_closed:
            return False
            
        # Use select to check if data is available
        readable, _, _ = select.select([self.socket], [], [], 0)
        return bool(readable)
        
    def is_writable(self) -> bool:
        """Check if socket is writable"""
        if self.is_closed:
            return False
            
        # Use select to check if socket is writable
        _, writable, _ = select.select([], [self.socket], [], 0)
        return bool(writable)


class PipeStreamHandler(StreamHandler):
    """Handler for pipe streams"""
    
    def __init__(
        self,
        read_fd: Optional[int] = None,
        write_fd: Optional[int] = None,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize pipe stream handler
        
        Args:
            read_fd: File descriptor for reading
            write_fd: File descriptor for writing
            config: Stream configuration
        """
        super().__init__(config)
        
        if not read_fd and not write_fd:
            # Create a new pipe
            self.read_fd, self.write_fd = os.pipe()
        else:
            self.read_fd = read_fd
            self.write_fd = write_fd
            
        # Create file objects from descriptors
        self.read_file = (
            os.fdopen(self.read_fd, 'r', encoding=self.config.encoding)
            if self.read_fd else None
        )
        self.write_file = (
            os.fdopen(self.write_fd, 'w', encoding=self.config.encoding)
            if self.write_fd else None
        )
                                    
    def read(self, size: int = -1) -> str:
        """Read from pipe"""
        if self.is_closed or not self.read_file:
            raise IOError("Pipe is closed or not readable")
        return self.read_file.read(size)
        
    def write(self, data: str) -> int:
        """Write to pipe"""
        if self.is_closed or not self.write_file:
            raise IOError("Pipe is closed or not writable")
            
        result = self.write_file.write(data)
        if self.config.auto_flush:
            self.write_file.flush()
        return result
        
    def close(self):
        """Close pipe"""
        if not self.is_closed:
            if self.read_file:
                self.read_file.close()
            if self.write_file:
                self.write_file.close()
            self.is_closed = True
            
    def is_readable(self) -> bool:
        """Check if pipe is readable"""
        return self.read_file is not None and not self.is_closed
        
    def is_writable(self) -> bool:
        """Check if pipe is writable"""
        return self.write_file is not None and not self.is_closed


class MemoryStreamHandler(StreamHandler):
    """Handler for in-memory streams"""
    
    def __init__(
        self,
        initial_data: str = "",
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize memory stream handler
        
        Args:
            initial_data: Initial data in stream
            config: Stream configuration
        """
        super().__init__(config)
        self._buffer = io.StringIO(initial_data)
        self._lock = threading.Lock()
        
    def read(self, size: int = -1) -> str:
        """Read from memory stream"""
        with self._lock:
            if self.is_closed:
                raise IOError("Stream is closed")
            return self._buffer.read(size)
            
    def write(self, data: str) -> int:
        """Write to memory stream"""
        with self._lock:
            if self.is_closed:
                raise IOError("Stream is closed")
            return self._buffer.write(data)
            
    def close(self):
        """Close memory stream"""
        with self._lock:
            if not self.is_closed:
                self._buffer.close()
                self.is_closed = True
                
    def is_readable(self) -> bool:
        """Check if stream is readable"""
        return not self.is_closed
        
    def is_writable(self) -> bool:
        """Check if stream is writable"""
        return not self.is_closed
        
    def getvalue(self) -> str:
        """Get all data from memory stream"""
        with self._lock:
            if self.is_closed:
                raise IOError("Stream is closed")
            return self._buffer.getvalue()
            
    def seek(self, offset: int, whence: int = 0):
        """Seek to position in stream"""
        with self._lock:
            if not self.is_closed:
                self._buffer.seek(offset, whence)
                
    def tell(self) -> int:
        """Get current position"""
        with self._lock:
            if not self.is_closed:
                return self._buffer.tell()
            return 0


class BufferedStreamHandler(StreamHandler):
    """Buffered wrapper for any stream handler"""
    
    def __init__(
        self,
        inner_handler: StreamHandler,
        read_buffer_size: int = 8192,
        write_buffer_size: int = 8192,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize buffered stream handler
        
        Args:
            inner_handler: The underlying stream handler
            read_buffer_size: Size of read buffer
            write_buffer_size: Size of write buffer
            config: Stream configuration
        """
        super().__init__(config or inner_handler.config)
        self.inner = inner_handler
        self.read_buffer_size = read_buffer_size
        self.write_buffer_size = write_buffer_size
        
        self._read_buffer = ""
        self._write_buffer = []
        self._write_buffer_size = 0
        
    def read(self, size: int = -1) -> str:
        """Read with buffering"""
        if self.is_closed:
            raise IOError("Stream is closed")
            
        if size == -1:
            # Read all
            result = self._read_buffer + self.inner.read(-1)
            self._read_buffer = ""
            return result
            
        # Read from buffer first
        if len(self._read_buffer) >= size:
            result = self._read_buffer[:size]
            self._read_buffer = self._read_buffer[size:]
            return result
            
        # Need more data
        result = self._read_buffer
        needed = size - len(result)
        
        # Read in chunks
        while needed > 0:
            chunk = self.inner.read(max(needed, self.read_buffer_size))
            if not chunk:
                break
                
            if len(chunk) > needed:
                result += chunk[:needed]
                self._read_buffer = chunk[needed:]
                break
            else:
                result += chunk
                needed -= len(chunk)
                
        return result
        
    def write(self, data: str) -> int:
        """Write with buffering"""
        if self.is_closed:
            raise IOError("Stream is closed")
            
        self._write_buffer.append(data)
        self._write_buffer_size += len(data)
        
        # Flush if buffer is full
        if self._write_buffer_size >= self.write_buffer_size:
            self.flush()
            
        return len(data)
        
    def flush(self):
        """Flush write buffer"""
        if self._write_buffer:
            data = ''.join(self._write_buffer)
            self.inner.write(data)
            self._write_buffer = []
            self._write_buffer_size = 0
            
    def close(self):
        """Close stream"""
        if not self.is_closed:
            self.flush()
            self.inner.close()
            self.is_closed = True
            
    def is_readable(self) -> bool:
        """Check if readable"""
        return self.inner.is_readable()
        
    def is_writable(self) -> bool:
        """Check if writable"""
        return self.inner.is_writable()


class TransformStreamHandler(StreamHandler):
    """Stream handler that applies transformations to data"""
    
    def __init__(
        self,
        inner_handler: StreamHandler,
        read_transform: Optional[Callable[[str], str]] = None,
        write_transform: Optional[Callable[[str], str]] = None,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize transform stream handler
        
        Args:
            inner_handler: The underlying stream handler
            read_transform: Function to transform read data
            write_transform: Function to transform write data
            config: Stream configuration
        """
        super().__init__(config or inner_handler.config)
        self.inner = inner_handler
        self.read_transform = read_transform or (lambda x: x)
        self.write_transform = write_transform or (lambda x: x)
        
    def read(self, size: int = -1) -> str:
        """Read and transform data"""
        data = self.inner.read(size)
        return self.read_transform(data) if data else data
        
    def write(self, data: str) -> int:
        """Transform and write data"""
        transformed = self.write_transform(data)
        return self.inner.write(transformed)
        
    def close(self):
        """Close stream"""
        self.inner.close()
        self.is_closed = True
        
    def is_readable(self) -> bool:
        """Check if readable"""
        return self.inner.is_readable()
        
    def is_writable(self) -> bool:
        """Check if writable"""
        return self.inner.is_writable()


class AsyncStreamHandler(ABC):
    """Abstract base class for async stream handlers"""
    
    def __init__(self, config: Optional[StreamConfig] = None):
        """Initialize async stream handler"""
        self.config = config or StreamConfig()
        self.is_closed = False
        
    @abstractmethod
    async def read(self, size: int = -1) -> str:
        """Read data asynchronously"""
        pass
        
    @abstractmethod
    async def write(self, data: str) -> int:
        """Write data asynchronously"""
        pass
        
    @abstractmethod
    async def close(self):
        """Close stream asynchronously"""
        pass
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        
    async def __aiter__(self):
        """Async iteration over lines"""
        return self
    
    async def __anext__(self) -> str:
        """Get next line asynchronously"""
        line = await self.readline()
        if not line:
            raise StopAsyncIteration
        return line
            
    async def readline(self, size: int = -1) -> str:
        """Read a line asynchronously"""
        line = []
        while True:
            char = await self.read(1)
            if not char or char == '\n':
                break
            line.append(char)
            if size > 0 and len(line) >= size:
                break
        return ''.join(line) + (char if char == '\n' else '')


class AsyncFileStreamHandler(AsyncStreamHandler):
    """Async handler for file streams"""
    
    def __init__(
        self,
        filepath: Union[str, Path],
        mode: str = 'r',
        config: Optional[StreamConfig] = None
    ):
        """Initialize async file stream handler"""
        super().__init__(config)
        self.filepath = Path(filepath)
        self.mode = mode
        self._file = None
        
    async def _ensure_open(self):
        """Ensure file is open"""
        if self._file is None:
            try:
                import aiofiles
                # Use aiofiles with specific mode type
                if 'b' in self.mode:
                    self._file = await aiofiles.open(
                        str(self.filepath),
                        mode=self.mode  # type: ignore
                    )
                else:
                    self._file = await aiofiles.open(
                        str(self.filepath),
                        mode=self.mode,  # type: ignore
                        encoding=self.config.encoding
                    )
                self._is_aiofiles = True
            except ImportError:
                # Fallback to sync file operations in async wrapper
                import asyncio
                loop = asyncio.get_event_loop()
                if 'b' in self.mode:
                    self._file = await loop.run_in_executor(
                        None,
                        open,
                        str(self.filepath),
                        self.mode
                    )
                else:
                    self._file = await loop.run_in_executor(
                        None,
                        open,
                        str(self.filepath),
                        self.mode,
                        encoding=self.config.encoding
                    )
                self._is_aiofiles = False
            
    async def read(self, size: int = -1) -> str:
        """Read from file asynchronously"""
        if self.is_closed:
            raise IOError("Stream is closed")
        await self._ensure_open()
        if self._is_aiofiles and self._file:
            return await self._file.read(size)
        elif self._file:
            # Sync file wrapped in async
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._file.read, size)
        else:
            raise IOError("File not open")
        
    async def write(self, data: str) -> int:
        """Write to file asynchronously"""
        if self.is_closed:
            raise IOError("Stream is closed")
        await self._ensure_open()
        if self._is_aiofiles and self._file:
            await self._file.write(data)
            if self.config.auto_flush:
                await self._file.flush()
        elif self._file:
            # Sync file wrapped in async
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._file.write, data)
            if self.config.auto_flush:
                await loop.run_in_executor(None, self._file.flush)
        else:
            raise IOError("File not open")
        return len(data)
        
    async def close(self):
        """Close file asynchronously"""
        if self._file and not self.is_closed:
            if self._is_aiofiles:
                await self._file.close()
            else:
                # Sync file wrapped in async
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._file.close)
            self.is_closed = True


# Factory function for creating appropriate stream handlers
def create_stream_handler(
    source: Union[str, Path, socket.socket, int, BinaryIO, TextIO],
    mode: str = 'r',
    config: Optional[StreamConfig] = None
) -> StreamHandler:
    """
    Create appropriate stream handler based on source type
    
    Args:
        source: The data source
        mode: Access mode
        config: Stream configuration
        
    Returns:
        Appropriate StreamHandler instance
    """
    if isinstance(source, (str, Path)):
        return FileStreamHandler(source, mode, config)
    elif isinstance(source, socket.socket):
        return SocketStreamHandler(source, config=config)
    elif isinstance(source, int):
        # Assume it's a file descriptor
        if 'r' in mode:
            return PipeStreamHandler(read_fd=source, config=config)
        else:
            return PipeStreamHandler(write_fd=source, config=config)
    elif hasattr(source, 'read') or hasattr(source, 'write'):
        # It's already a file-like object
        class WrapperStreamHandler(StreamHandler):
            def __init__(self, file_obj, config):
                super().__init__(config)
                self.file_obj = file_obj
                
            def read(self, size=-1):
                return self.file_obj.read(size)
                
            def write(self, data):
                return self.file_obj.write(data)
                
            def close(self):
                if hasattr(self.file_obj, 'close'):
                    self.file_obj.close()
                self.is_closed = True
                
            def is_readable(self):
                return hasattr(self.file_obj, 'read') and not self.is_closed
                
            def is_writable(self):
                return hasattr(self.file_obj, 'write') and not self.is_closed
                
        return WrapperStreamHandler(source, config)
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")