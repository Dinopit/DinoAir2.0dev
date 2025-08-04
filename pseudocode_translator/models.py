"""
Data models for the Pseudocode Translator
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List


class BlockType(Enum):
    """
    Enumeration for different types of code blocks
    """
    ENGLISH = "english"
    PYTHON = "python"
    MIXED = "mixed"
    COMMENT = "comment"


@dataclass
class CodeBlock:
    """
    Represents a parsed block of code or instruction
    """
    type: BlockType
    content: str
    line_numbers: Tuple[int, int]  # (start_line, end_line)
    metadata: Dict[str, Any]
    context: Optional[str] = None  # Surrounding code context
    
    def __post_init__(self):
        """Validate the code block after initialization"""
        if self.line_numbers[0] > self.line_numbers[1]:
            raise ValueError(f"Invalid line numbers: start ({self.line_numbers[0]}) > end ({self.line_numbers[1]})")
        
        if not self.content.strip():
            raise ValueError("Code block content cannot be empty")
    
    @property
    def is_pure_english(self) -> bool:
        """Check if block contains only English instructions"""
        return self.type == BlockType.ENGLISH
    
    @property
    def is_pure_python(self) -> bool:
        """Check if block contains only Python code"""
        return self.type == BlockType.PYTHON
    
    @property
    def is_mixed(self) -> bool:
        """Check if block contains mixed English/Python"""
        return self.type == BlockType.MIXED
    
    @property
    def line_count(self) -> int:
        """Get the number of lines in this block"""
        return self.line_numbers[1] - self.line_numbers[0] + 1
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Safely get metadata value with default"""
        return self.metadata.get(key, default)


@dataclass
class ParseError:
    """
    Represents an error encountered during parsing
    """
    message: str
    line_number: Optional[int] = None
    block_content: Optional[str] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        error_msg = self.message
        if self.line_number:
            error_msg = f"Line {self.line_number}: {error_msg}"
        if self.suggestion:
            error_msg += f"\nSuggestion: {self.suggestion}"
        return error_msg


@dataclass
class ParseResult:
    """
    Result of parsing operation containing blocks and any errors
    """
    blocks: List[CodeBlock]
    errors: List[ParseError]
    warnings: List[str]
    
    @property
    def success(self) -> bool:
        """Check if parsing was successful (no errors)"""
        return len(self.errors) == 0
    
    @property
    def block_count(self) -> int:
        """Get total number of parsed blocks"""
        return len(self.blocks)
    
    def get_blocks_by_type(self, block_type: BlockType) -> List[CodeBlock]:
        """Get all blocks of a specific type"""
        return [block for block in self.blocks if block.type == block_type]
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0