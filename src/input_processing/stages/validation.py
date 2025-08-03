"""
Input validation module for DinoAir InputSanitizer.

This module provides the first line of defense against security threats by
validating and cleaning user input. It detects and prevents various attack
vectors including path traversal, command injection, and other malicious
patterns.

Classes:
    ValidationError: Custom exception for validation failures
    ThreatLevel: Enum representing threat severity levels
    ValidationResult: Dataclass containing validation results
    InputValidator: Main validation class with configurable security patterns

Example:
    >>> validator = InputValidator()
    >>> result = validator.validate("Hello world")
    >>> print(f"Valid: {result.is_valid}, Threat: {result.threat_level}")
    Valid: True, Threat: ThreatLevel.NONE
"""

import re
import string
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Pattern, Set, Tuple
import unicodedata


class ValidationError(Exception):
    """Custom exception raised for validation failures."""
    pass


class ThreatLevel(Enum):
    """Threat severity levels for detected security issues."""
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class ValidationResult:
    """
    Result of input validation containing security assessment.
    
    Attributes:
        is_valid: Whether the input passed all validation checks
        cleaned_text: Sanitized version of the input text
        threat_level: Highest threat level detected
        issues: List of specific security issues found
    """
    is_valid: bool
    cleaned_text: str
    threat_level: ThreatLevel
    issues: List[str] = field(default_factory=list)


class InputValidator:
    """
    Validates and sanitizes user input for security threats.
    
    This class implements comprehensive security validation including detection
    of path traversal attempts, command injection, null bytes, control
    characters, and Windows reserved filenames.
    
    Attributes:
        max_length: Maximum allowed input length (default: 5000)
        dangerous_patterns: Dictionary of pattern categories and their regex
            patterns
        windows_reserved: Set of Windows reserved filenames
    """
    
    def __init__(self, max_length: int = 5000):
        """
        Initialize the InputValidator with configurable settings.
        
        Args:
            max_length: Maximum allowed input length (default: 5000)
        """
        self.max_length = max_length
        self._initialize_patterns()
        self._initialize_reserved_names()
    
    def _initialize_patterns(self) -> None:
        """Initialize dangerous pattern detection regex patterns."""
        self.dangerous_patterns: Dict[
            str, List[Tuple[Pattern, ThreatLevel, str]]
        ] = {
            "path_traversal": [
                # Basic path traversal
                (re.compile(r'\.\.[\\/]'), ThreatLevel.HIGH,
                 "Path traversal attempt: ../"),
                (re.compile(r'\.\.\\'), ThreatLevel.HIGH,
                 "Path traversal attempt: ..\\"),
                # Any double dots sequence
                (re.compile(r'\.\.'), ThreatLevel.HIGH,
                 "Path traversal sequence detected"),
                # Multiple slashes (obfuscation attempt)
                (re.compile(r'[\\/]{2,}'), ThreatLevel.HIGH,
                 "Multiple slashes detected"),
                # Mixed slashes with dots
                (re.compile(r'\.{2,}[\\/]+\.{2,}'), ThreatLevel.HIGH,
                 "Complex path traversal pattern"),
                # URL encoded path traversal
                (re.compile(r'\.\.%2[Ff]'), ThreatLevel.HIGH,
                 "URL encoded path traversal: ..%2F"),
                (re.compile(r'\.\.%5[Cc]'), ThreatLevel.HIGH,
                 "URL encoded path traversal: ..%5C"),
                (re.compile(r'%2[Ee]%2[Ee]'), ThreatLevel.HIGH,
                 "URL encoded dots"),
                # Double encoded
                (re.compile(r'%252[Ee]%252[Ee]%252[Ff]'), ThreatLevel.HIGH,
                 "Double encoded path traversal"),
                (re.compile(r'%255[Cc]'), ThreatLevel.HIGH,
                 "Double encoded backslash"),
                # Unicode/UTF-8 encoded
                (re.compile(r'\\x2e\\x2e[\\\/]'), ThreatLevel.HIGH,
                 "Hex encoded path traversal"),
                (re.compile(r'\\u002e\\u002e'), ThreatLevel.HIGH,
                 "Unicode encoded path traversal"),
                # Common sensitive paths
                (re.compile(r'etc[\\/]passwd', re.IGNORECASE), ThreatLevel.HIGH,
                 "Attempt to access sensitive file"),
                (re.compile(r'windows[\\/]system', re.IGNORECASE), ThreatLevel.HIGH,
                 "Windows system directory access"),
            ],
            "command_injection": [
                # Shell command separators
                (re.compile(r'[;&|]'), ThreatLevel.HIGH,
                 "Command separator detected"),
                # Command substitution
                (re.compile(r'`'), ThreatLevel.HIGH,
                 "Backtick command substitution"),
                (re.compile(r'\$\('), ThreatLevel.HIGH,
                 "Command substitution: $("),
                (re.compile(r'\$\{'), ThreatLevel.HIGH,
                 "Variable expansion: ${"),
                # Process substitution
                (re.compile(r'<\('), ThreatLevel.HIGH,
                 "Process substitution: <("),
                (re.compile(r'>\('), ThreatLevel.HIGH,
                 "Process substitution: >("),
                # Redirection
                (re.compile(r'(?<!\w)[<>]+(?!\w)'), ThreatLevel.MEDIUM,
                 "IO redirection detected"),
                # Shell variables
                (re.compile(r'\$[A-Za-z_]'), ThreatLevel.MEDIUM,
                 "Shell variable detected"),
            ],
            "null_bytes": [
                # Direct null byte
                (re.compile(r'\x00'), ThreatLevel.HIGH,
                 "Null byte detected"),
                # URL encoded null byte
                (re.compile(r'%00'), ThreatLevel.HIGH,
                 "URL encoded null byte"),
                # Double encoded null byte
                (re.compile(r'%2500'), ThreatLevel.HIGH,
                 "Double encoded null byte"),
            ],
            "control_characters": [
                # Dangerous control characters (excluding \n, \t, \r)
                (re.compile(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]'),
                 ThreatLevel.MEDIUM, "Control character detected"),
            ],
            "file_system_abuse": [
                # Absolute paths
                (re.compile(r'^[A-Za-z]:[\\\/]'), ThreatLevel.MEDIUM,
                 "Absolute Windows path"),
                (re.compile(r'^[\\\/]'), ThreatLevel.MEDIUM,
                 "Absolute Unix path"),
                # UNC paths
                (re.compile(r'^\\\\'), ThreatLevel.HIGH,
                 "UNC path detected"),
                # Device files
                (re.compile(r'[\\\/]dev[\\\/]'), ThreatLevel.HIGH,
                 "Device file access attempt"),
                # Hidden files
                (re.compile(r'[\\\/]\.'), ThreatLevel.LOW,
                 "Hidden file access"),
            ],
        }
    
    def _initialize_reserved_names(self) -> None:
        """Initialize Windows reserved filename set."""
        # Windows reserved names
        base_reserved = {'CON', 'PRN', 'AUX', 'NUL'}
        # COM1-COM9, LPT1-LPT9
        com_ports = {f'COM{i}' for i in range(1, 10)}
        lpt_ports = {f'LPT{i}' for i in range(1, 10)}
        
        self.windows_reserved: Set[str] = base_reserved | com_ports | lpt_ports
    
    def validate(self, text: str) -> ValidationResult:
        """
        Validate input text for security threats.
        
        Performs comprehensive security validation including length checks,
        pattern matching for various attack vectors, and Windows reserved
        filename detection.
        
        Args:
            text: Input text to validate
            
        Returns:
            ValidationResult containing validation status, cleaned text,
            threat level, and list of issues found
            
        Raises:
            ValidationError: If critical validation failure occurs
        """
        if not isinstance(text, str):
            raise ValidationError(
                f"Input must be string, got {type(text).__name__}"
            )
        
        issues: List[str] = []
        threat_level = ThreatLevel.NONE
        
        # Length validation
        if len(text) > self.max_length:
            issues.append(
                f"Input exceeds maximum length of {self.max_length} characters"
            )
            threat_level = ThreatLevel.MEDIUM
            text = text[:self.max_length]
        
        # Check for empty or whitespace-only input
        if not text or text.isspace():
            return ValidationResult(
                is_valid=True,
                cleaned_text="",
                threat_level=ThreatLevel.NONE,
                issues=[]
            )
        
        # Pattern-based threat detection
        for category, patterns in self.dangerous_patterns.items():
            for pattern, level, description in patterns:
                if pattern.search(text):
                    issues.append(f"{category}: {description}")
                    threat_level = max(
                        threat_level, level, key=lambda x: x.value
                    )
        
        # Windows reserved filename check
        # Check both the full text and any potential filename components
        potential_filenames = re.findall(r'[A-Za-z0-9_\-\.]+', text)
        for filename in potential_filenames:
            base_name = filename.upper().split('.')[0]
            if base_name in self.windows_reserved:
                issues.append(
                    f"Windows reserved filename detected: {filename}"
                )
                threat_level = max(
                    threat_level, ThreatLevel.MEDIUM, key=lambda x: x.value
                )
        
        # Unicode normalization check
        normalized = unicodedata.normalize('NFKC', text)
        if normalized != text:
            issues.append(
                "Unicode normalization changed input (possible obfuscation)"
            )
            threat_level = max(
                threat_level, ThreatLevel.LOW, key=lambda x: x.value
            )
        
        # Clean the text if threats were detected
        if issues:
            cleaned_text = self._clean_text(text, threat_level)
        else:
            cleaned_text = text
        
        # Determine validity
        is_valid = threat_level.value <= ThreatLevel.LOW.value
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_text=cleaned_text,
            threat_level=threat_level,
            issues=issues
        )
    
    def _clean_text(self, text: str, threat_level: ThreatLevel) -> str:
        """
        Clean dangerous content from text based on threat level.
        
        Applies different cleaning strategies based on the severity of
        detected threats. High threats result in aggressive cleaning,
        while lower threats receive more targeted cleaning.
        
        Args:
            text: Text to clean
            threat_level: Detected threat level
            
        Returns:
            Cleaned text with dangerous content removed or escaped
        """
        if threat_level == ThreatLevel.HIGH:
            # Aggressive cleaning for high threats
            # For path traversal, completely reject the input
            if any(pattern in text.lower() for pattern in
                   ['..', 'etc/passwd', 'windows/system', 'cmd.exe']):
                return ""  # Completely reject path traversal attempts
            # Remove special chars except basic punctuation and whitespace
            allowed = (string.ascii_letters + string.digits +
                       ' .,!?-_\n\r\t')
            allowed_chars = set(allowed)
            cleaned = ''.join(c for c in text if c in allowed_chars)
        elif threat_level == ThreatLevel.MEDIUM:
            # Moderate cleaning
            # Remove dangerous characters but preserve more formatting
            dangerous_chars = {'&', '|', ';', '`', '$', '<', '>', '\\', '\x00'}
            cleaned = ''.join(c for c in text if c not in dangerous_chars)
            # Remove path traversal sequences
            cleaned = re.sub(r'\.\.[\\/]?', '', cleaned)
            cleaned = re.sub(r'%2[Ee]%2[Ee]', '', cleaned)
            cleaned = re.sub(r'%5[Cc]', '', cleaned)
        else:
            # Light cleaning for low threats
            # Just remove null bytes and normalize whitespace
            cleaned = text.replace('\x00', '').replace('%00', '')
            # Normalize multiple spaces
            cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Final safety: ensure no control characters remain
        cleaned = ''.join(
            c for c in cleaned 
            if c == '\n' or c == '\r' or c == '\t' or ord(c) >= 32
        )
        
        return cleaned.strip()
    
    def is_safe_path(self, base_dir: str, user_path: str) -> bool:
        """
        Check if a user-provided path is safe within a base directory.
        
        Uses path canonicalization to prevent directory traversal attacks.
        This method follows security best practices by resolving both paths
        to absolute form and checking containment.
        
        Args:
            base_dir: Base directory that should contain the path
            user_path: User-provided path to validate
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            base = Path(base_dir).resolve()
            candidate = (base / user_path).resolve()
            # This will raise ValueError if candidate is not relative to base
            candidate.relative_to(base)
            return True
        except (ValueError, OSError):
            return False