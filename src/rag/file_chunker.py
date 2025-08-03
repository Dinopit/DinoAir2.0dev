"""
Text chunking module for DinoAir 2.0 RAG File Search system.
Provides intelligent text chunking with configurable strategies.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import logging from DinoAir's logger
from ..utils.logger import Logger


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    chunk_index: int
    start_pos: int
    end_pos: int
    chunk_type: str  # 'text', 'code', 'sentence', 'paragraph'
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class TextChunk:
    """Represents a chunk of text with its metadata."""
    content: str
    metadata: ChunkMetadata


class FileChunker:
    """
    Handles text chunking with various strategies.
    Supports overlapping chunks and smart boundaries.
    """
    
    # Default chunk settings
    DEFAULT_CHUNK_SIZE = 1000  # characters
    DEFAULT_OVERLAP = 200  # characters
    DEFAULT_MIN_CHUNK_SIZE = 100  # minimum chunk size
    
    def __init__(self, 
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 overlap: int = DEFAULT_OVERLAP,
                 min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE):
        """
        Initialize the FileChunker.
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum size for a chunk
        """
        self.logger = Logger()
        self.chunk_size = max(chunk_size, 1)
        self.overlap = max(overlap, 0)
        self.min_chunk_size = max(min_chunk_size, 1)
        
        # Validate settings
        if self.overlap >= self.chunk_size:
            self.logger.warning(
                f"Overlap ({overlap}) >= chunk_size ({chunk_size}). "
                f"Setting overlap to {chunk_size // 2}"
            )
            self.overlap = chunk_size // 2
        
        # Compile regex patterns for sentence splitting
        self.sentence_end_pattern = re.compile(
            r'[.!?]+[\s\n]+|[\n]{2,}'
        )
        
        # Compile regex patterns for code chunking
        self.code_block_patterns = {
            'function': re.compile(
                r'^\s*(def\s+\w+|function\s+\w+|'
                r'public\s+\w+|private\s+\w+|protected\s+\w+|'
                r'class\s+\w+|interface\s+\w+|struct\s+\w+)',
                re.MULTILINE
            ),
            'class': re.compile(
                r'^\s*(class\s+\w+|interface\s+\w+|struct\s+\w+)',
                re.MULTILINE
            ),
            'method': re.compile(
                r'^\s*(def\s+\w+|function\s+\w+|'
                r'public\s+\w+.*\(|private\s+\w+.*\(|'
                r'protected\s+\w+.*\()',
                re.MULTILINE
            )
        }
    
    def chunk_text(self, text: str, 
                   respect_boundaries: bool = True) -> List[TextChunk]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: The text to chunk
            respect_boundaries: Whether to respect natural boundaries
                               (sentences, paragraphs)
            
        Returns:
            List of TextChunk objects
        """
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        current_pos = 0
        chunk_index = 0
        
        while current_pos < text_length:
            # Determine chunk end position
            chunk_end = min(current_pos + self.chunk_size, text_length)
            
            # If respecting boundaries and not at text end,
            # try to find a good break point
            if respect_boundaries and chunk_end < text_length:
                chunk_end = self._find_boundary(
                    text, current_pos, chunk_end
                )
            
            # Extract chunk content
            chunk_content = text[current_pos:chunk_end]
            
            # Skip if chunk is too small (unless it's the last chunk)
            if (len(chunk_content) < self.min_chunk_size and 
                chunk_end < text_length):
                current_pos = chunk_end
                continue
            
            # Calculate overlaps
            overlap_prev = 0
            overlap_next = 0
            
            if chunk_index > 0 and self.overlap > 0:
                overlap_start = max(0, current_pos - self.overlap)
                overlap_prev = current_pos - overlap_start
            
            if chunk_end < text_length and self.overlap > 0:
                overlap_next = self.overlap
            
            # Create chunk
            metadata = ChunkMetadata(
                chunk_index=chunk_index,
                start_pos=current_pos,
                end_pos=chunk_end,
                chunk_type='text',
                overlap_with_previous=overlap_prev,
                overlap_with_next=overlap_next
            )
            
            chunk = TextChunk(content=chunk_content, metadata=metadata)
            chunks.append(chunk)
            
            # Move to next chunk position
            chunk_index += 1
            current_pos = chunk_end - self.overlap
            
            # Ensure we make progress
            if current_pos <= chunks[-1].metadata.start_pos:
                current_pos = chunk_end
        
        self.logger.info(
            f"Created {len(chunks)} chunks from {text_length} characters"
        )
        return chunks
    
    def chunk_by_sentences(self, text: str) -> List[TextChunk]:
        """
        Split text into chunks based on sentence boundaries.
        
        Args:
            text: The text to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text:
            return []
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return self.chunk_text(text, respect_boundaries=False)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        chunk_start_pos = 0
        
        for i, (sentence, start_pos, end_pos) in enumerate(sentences):
            sentence_size = len(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if (current_size + sentence_size > self.chunk_size and 
                current_chunk):
                # Create chunk from accumulated sentences
                chunk_content = ''.join(current_chunk)
                
                # Add overlap from next sentences if available
                overlap_content = self._get_sentence_overlap(
                    sentences, i, self.overlap
                )
                if overlap_content:
                    chunk_content += overlap_content
                
                metadata = ChunkMetadata(
                    chunk_index=chunk_index,
                    start_pos=chunk_start_pos,
                    end_pos=chunk_start_pos + len(chunk_content),
                    chunk_type='sentence',
                    overlap_with_previous=(
                        self.overlap if chunk_index > 0 else 0
                    ),
                    overlap_with_next=(
                        len(overlap_content) if overlap_content else 0
                    )
                )
                
                chunk = TextChunk(content=chunk_content, metadata=metadata)
                chunks.append(chunk)
                
                # Reset for next chunk
                current_chunk = []
                current_size = 0
                chunk_index += 1
                chunk_start_pos = start_pos
                
                # Add overlap from previous chunk
                if self.overlap > 0 and i > 0:
                    overlap_sentences = self._get_previous_sentences(
                        sentences, i, self.overlap
                    )
                    current_chunk.extend(overlap_sentences)
                    current_size = sum(len(s) for s in overlap_sentences)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Handle remaining sentences
        if current_chunk:
            chunk_content = ''.join(current_chunk)
            
            metadata = ChunkMetadata(
                chunk_index=chunk_index,
                start_pos=chunk_start_pos,
                end_pos=chunk_start_pos + len(chunk_content),
                chunk_type='sentence',
                overlap_with_previous=(
                    self.overlap if chunk_index > 0 else 0
                ),
                overlap_with_next=0
            )
            
            chunk = TextChunk(content=chunk_content, metadata=metadata)
            chunks.append(chunk)
        
        self.logger.info(
            f"Created {len(chunks)} sentence-based chunks"
        )
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[TextChunk]:
        """
        Split text into chunks based on paragraph boundaries.
        
        Args:
            text: The text to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text:
            return []
        
        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        
        if not paragraphs:
            return self.chunk_text(text, respect_boundaries=False)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        chunk_start_pos = 0
        
        for i, (paragraph, start_pos, end_pos) in enumerate(paragraphs):
            paragraph_size = len(paragraph)
            
            # Check if adding this paragraph would exceed chunk size
            if (current_size + paragraph_size > self.chunk_size and 
                current_chunk):
                # Create chunk from accumulated paragraphs
                chunk_content = '\n\n'.join(current_chunk)
                
                metadata = ChunkMetadata(
                    chunk_index=chunk_index,
                    start_pos=chunk_start_pos,
                    end_pos=chunk_start_pos + len(chunk_content),
                    chunk_type='paragraph',
                    overlap_with_previous=(
                        self.overlap if chunk_index > 0 else 0
                    ),
                    overlap_with_next=0
                )
                
                chunk = TextChunk(content=chunk_content, metadata=metadata)
                chunks.append(chunk)
                
                # Reset for next chunk
                current_chunk = []
                current_size = 0
                chunk_index += 1
                chunk_start_pos = start_pos
            
            # Add paragraph to current chunk
            current_chunk.append(paragraph)
            current_size += paragraph_size + 2  # Account for \n\n
        
        # Handle remaining paragraphs
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            
            metadata = ChunkMetadata(
                chunk_index=chunk_index,
                start_pos=chunk_start_pos,
                end_pos=chunk_start_pos + len(chunk_content),
                chunk_type='paragraph',
                overlap_with_previous=(
                    self.overlap if chunk_index > 0 else 0
                ),
                overlap_with_next=0
            )
            
            chunk = TextChunk(content=chunk_content, metadata=metadata)
            chunks.append(chunk)
        
        self.logger.info(
            f"Created {len(chunks)} paragraph-based chunks"
        )
        return chunks
    
    def chunk_code(self, code: str, language: str = 'unknown') -> List[TextChunk]:
        """
        Smart chunking for code files that respects code boundaries.
        
        Args:
            code: The code to chunk
            language: Programming language (for better chunking)
            
        Returns:
            List of TextChunk objects
        """
        if not code:
            return []
        
        # Find natural code boundaries
        boundaries = self._find_code_boundaries(code, language)
        
        if not boundaries:
            # Fall back to regular chunking if no boundaries found
            return self.chunk_text(code, respect_boundaries=True)
        
        chunks = []
        chunk_index = 0
        
        for i, (start, end, boundary_type) in enumerate(boundaries):
            block_content = code[start:end]
            
            # If block is too large, split it further
            if len(block_content) > self.chunk_size * 2:
                # Recursively chunk large blocks
                sub_chunks = self.chunk_text(
                    block_content, 
                    respect_boundaries=True
                )
                
                for sub_chunk in sub_chunks:
                    # Adjust positions relative to original code
                    metadata = ChunkMetadata(
                        chunk_index=chunk_index,
                        start_pos=start + sub_chunk.metadata.start_pos,
                        end_pos=start + sub_chunk.metadata.end_pos,
                        chunk_type='code',
                        additional_info={
                            'boundary_type': boundary_type,
                            'language': language
                        }
                    )
                    
                    chunk = TextChunk(
                        content=sub_chunk.content,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                # Create chunk for the code block
                metadata = ChunkMetadata(
                    chunk_index=chunk_index,
                    start_pos=start,
                    end_pos=end,
                    chunk_type='code',
                    additional_info={
                        'boundary_type': boundary_type,
                        'language': language
                    }
                )
                
                chunk = TextChunk(content=block_content, metadata=metadata)
                chunks.append(chunk)
                chunk_index += 1
        
        self.logger.info(
            f"Created {len(chunks)} code chunks for {language}"
        )
        return chunks
    
    def _find_boundary(self, text: str, start: int, 
                      preferred_end: int) -> int:
        """
        Find a good boundary point for chunk splitting.
        
        Args:
            text: The text being chunked
            start: Start position of the chunk
            preferred_end: Preferred end position
            
        Returns:
            Adjusted end position
        """
        # Look for sentence end
        search_start = max(start, preferred_end - 100)
        search_text = text[search_start:preferred_end + 50]
        
        # Find last sentence boundary
        matches = list(self.sentence_end_pattern.finditer(search_text))
        if matches:
            last_match = matches[-1]
            return search_start + last_match.end()
        
        # Look for paragraph break
        last_newline = text.rfind('\n', start, preferred_end)
        if last_newline > start + self.min_chunk_size:
            return last_newline + 1
        
        # Look for space
        last_space = text.rfind(' ', start, preferred_end)
        if last_space > start + self.min_chunk_size:
            return last_space + 1
        
        # Return original if no good boundary found
        return preferred_end
    
    def _split_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into sentences with position information.
        
        Returns:
            List of tuples (sentence, start_pos, end_pos)
        """
        sentences = []
        last_end = 0
        
        for match in self.sentence_end_pattern.finditer(text):
            end = match.end()
            sentence = text[last_end:end]
            if sentence.strip():
                sentences.append((sentence, last_end, end))
            last_end = end
        
        # Add remaining text
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining.strip():
                sentences.append((remaining, last_end, len(text)))
        
        return sentences
    
    def _split_paragraphs(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into paragraphs with position information.
        
        Returns:
            List of tuples (paragraph, start_pos, end_pos)
        """
        paragraphs = []
        current_start = 0
        
        # Split by double newlines
        parts = text.split('\n\n')
        
        for part in parts:
            if part.strip():
                end_pos = current_start + len(part)
                paragraphs.append((part, current_start, end_pos))
                current_start = end_pos + 2  # Account for \n\n
            else:
                current_start += 2
        
        return paragraphs
    
    def _find_code_boundaries(self, code: str, 
                             language: str) -> List[Tuple[int, int, str]]:
        """
        Find natural boundaries in code (functions, classes, etc.).
        
        Returns:
            List of tuples (start_pos, end_pos, boundary_type)
        """
        boundaries = []
        
        # Find function/method definitions
        for match in self.code_block_patterns['function'].finditer(code):
            start = match.start()
            # Find the end of the function (simplified approach)
            end = self._find_code_block_end(code, start, language)
            if end > start:
                boundaries.append((start, end, 'function'))
        
        # Sort boundaries by start position
        boundaries.sort(key=lambda x: x[0])
        
        # Merge overlapping boundaries
        merged = []
        for boundary in boundaries:
            if not merged or boundary[0] >= merged[-1][1]:
                merged.append(boundary)
            else:
                # Extend the previous boundary
                merged[-1] = (
                    merged[-1][0],
                    max(merged[-1][1], boundary[1]),
                    merged[-1][2]
                )
        
        # Add any gaps as 'general' code blocks
        final_boundaries = []
        last_end = 0
        
        for start, end, btype in merged:
            if start > last_end:
                final_boundaries.append((last_end, start, 'general'))
            final_boundaries.append((start, end, btype))
            last_end = end
        
        if last_end < len(code):
            final_boundaries.append((last_end, len(code), 'general'))
        
        return final_boundaries
    
    def _find_code_block_end(self, code: str, start: int, 
                            language: str) -> int:
        """
        Find the end of a code block starting at the given position.
        
        This is a simplified implementation that uses indentation
        and brace matching.
        """
        lines = code[start:].split('\n')
        if not lines:
            return start
        
        # Get indentation of first line
        first_line = lines[0]
        base_indent = len(first_line) - len(first_line.lstrip())
        
        # Count braces for languages that use them
        brace_count = 0
        in_string = False
        string_char = None
        
        end_pos = start
        
        for i, line in enumerate(lines):
            # Update position
            end_pos += len(line) + 1  # +1 for newline
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check indentation
            current_indent = len(line) - len(line.lstrip())
            
            # Simple string detection (not perfect but good enough)
            for char in line:
                if not in_string and char in ['"', "'"]:
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    in_string = False
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
            
            # Check if we've returned to base level
            if i > 0 and not in_string:
                # For brace languages
                if brace_count == 0 and '{' in first_line:
                    break
                # For indentation-based languages (like Python)
                elif (current_indent <= base_indent and 
                      line.strip() and 
                      not line.strip().startswith(('else', 'elif', 
                                                  'except', 'finally'))):
                    end_pos -= len(line) + 1  # Don't include this line
                    break
        
        return min(end_pos, start + len(code[start:]))
    
    def _get_sentence_overlap(self, sentences: List[Tuple[str, int, int]], 
                             start_idx: int, 
                             target_size: int) -> str:
        """
        Get overlap content from following sentences.
        """
        overlap_content = []
        current_size = 0
        
        for i in range(start_idx, len(sentences)):
            sentence = sentences[i][0]
            if current_size + len(sentence) > target_size:
                break
            overlap_content.append(sentence)
            current_size += len(sentence)
        
        return ''.join(overlap_content)
    
    def _get_previous_sentences(self, 
                               sentences: List[Tuple[str, int, int]], 
                               current_idx: int, 
                               target_size: int) -> List[str]:
        """
        Get sentences from previous chunk for overlap.
        """
        overlap_sentences = []
        current_size = 0
        
        for i in range(current_idx - 1, -1, -1):
            sentence = sentences[i][0]
            if current_size + len(sentence) > target_size:
                break
            overlap_sentences.insert(0, sentence)
            current_size += len(sentence)
        
        return overlap_sentences