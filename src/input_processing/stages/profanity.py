"""Profanity filtering module with severity levels and context awareness.

Provides customizable profanity filtering with different severity levels
and context-aware detection to avoid false positives on technical terms.
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import re
from datetime import datetime


class Severity(Enum):
    """Profanity severity levels."""
    MILD = 1      # Minor inappropriate language
    MODERATE = 2  # Standard profanity
    SEVERE = 3    # Highly offensive content
    HATE = 4      # Hate speech / discriminatory


@dataclass
class ProfanityMatch:
    """Represents a detected profanity match."""
    word: str
    severity: Severity
    position: int
    length: int
    context: str  # Surrounding text for context
    masked: str   # Masked version of the word


@dataclass
class FilterResult:
    """Result of profanity filtering."""
    original_text: str
    filtered_text: str
    matches: List[ProfanityMatch]
    has_profanity: bool
    max_severity: Optional[Severity]
    score: float  # 0-1 score of how inappropriate the text is


class ProfanityFilter:
    """Advanced profanity filter with context awareness.
    
    This filter provides multi-level profanity detection with
    context awareness to reduce false positives on technical terms.
    """
    
    def __init__(self, custom_words: Optional[Dict[str, Severity]] = None):
        """Initialize with default and custom word lists.
        
        Args:
            custom_words: Optional dict mapping words to severity levels
        """
        # Default profanity lists by severity
        # Note: Using sanitized examples for a professional codebase
        self.word_lists = {
            Severity.MILD: {
                'damn', 'hell', 'crap', 'piss', 'ass',
                'bastard', 'bloody', 'bugger'
            },
            Severity.MODERATE: {
                'shit', 'fuck', 'bitch', 'dick', 'cock',
                'pussy', 'asshole', 'prick'
            },
            Severity.SEVERE: {
                'cunt', 'fag', 'retard', 'whore', 'slut'
            },
            Severity.HATE: {
                # Hate speech terms - keeping this minimal
                # Real implementation would have more comprehensive list
                'nigger', 'kike', 'spic', 'chink'
            }
        }
        
        # Technical terms that might be mistaken for profanity
        self.technical_whitelist = {
            'class', 'assert', 'pass', 'git', 'fork',
            'kill', 'dump', 'flush', 'abort', 'die',
            'master', 'slave', 'blacklist', 'whitelist',
            'penetration', 'injection', 'crack', 'hack',
            'screw', 'strip', 'touch', 'finger', 'mount'
        }
        
        # Common letter substitutions used to bypass filters
        self.substitutions = {
            '@': 'a',
            '4': 'a',
            '3': 'e',
            '1': 'i',
            '!': 'i',
            '0': 'o',
            '5': 's',
            '$': 's',
            '7': 't',
            '+': 't'
        }
        
        # Add custom words if provided
        if custom_words:
            for word, severity in custom_words.items():
                self.word_lists[severity].add(word.lower())
        
        # Build combined word set for quick lookup
        self._build_lookup_structures()
        
        # Masking options
        self.mask_chars = {
            'stars': '*',
            'dashes': '-',
            'underscores': '_',
            'dots': '.',
            'x': 'x'
        }
        self.current_mask_style = 'stars'
        
        # Statistics for reporting
        self.stats = {
            'total_filtered': 0,
            'by_severity': {s: 0 for s in Severity},
            'most_common': {}
        }
    
    def _build_lookup_structures(self):
        """Build efficient lookup structures."""
        self.all_profanity = set()
        self.severity_map = {}
        
        for severity, words in self.word_lists.items():
            for word in words:
                self.all_profanity.add(word)
                self.severity_map[word] = severity
    
    def set_mask_style(self, style: str):
        """Set the masking style.
        
        Args:
            style: One of 'stars', 'dashes', 'underscores', 'dots', 'x'
        """
        if style in self.mask_chars:
            self.current_mask_style = style
    
    def _normalize_for_detection(self, text: str) -> str:
        """Normalize text for profanity detection.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text with substitutions applied
        """
        normalized = text.lower()
        
        # Apply common substitutions
        for old, new in self.substitutions.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _is_technical_term(self, word: str, context: str) -> bool:
        """Check if word is likely a technical term.
        
        Args:
            word: The word to check
            context: Surrounding context
            
        Returns:
            True if likely a technical term
        """
        # Check whitelist
        if word.lower() in self.technical_whitelist:
            # Look for technical indicators in context
            tech_indicators = [
                'code', 'function', 'method', 'class', 'variable',
                'command', 'git', 'sql', 'api', 'server', 'database',
                'system', 'process', 'thread', 'memory', 'cpu'
            ]
            
            context_lower = context.lower()
            for indicator in tech_indicators:
                if indicator in context_lower:
                    return True
        
        return False
    
    def _get_context(self, text: str, position: int, word_length: int, 
                     context_size: int = 30) -> str:
        """Get surrounding context for a word.
        
        Args:
            text: Full text
            position: Position of word
            word_length: Length of word
            context_size: Characters of context on each side
            
        Returns:
            Context string
        """
        start = max(0, position - context_size)
        end = min(len(text), position + word_length + context_size)
        
        context = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        return context
    
    def _mask_word(self, word: str, keep_first_last: bool = True) -> str:
        """Mask a profane word.
        
        Args:
            word: Word to mask
            keep_first_last: Whether to keep first and last letters
            
        Returns:
            Masked word
        """
        if len(word) <= 2:
            return self.mask_chars[self.current_mask_style] * len(word)
        
        if keep_first_last:
            mask_char = self.mask_chars[self.current_mask_style]
            return word[0] + mask_char * (len(word) - 2) + word[-1]
        else:
            return self.mask_chars[self.current_mask_style] * len(word)
    
    def detect_profanity(self, text: str) -> List[ProfanityMatch]:
        """Detect profanity in text.
        
        Args:
            text: Text to check
            
        Returns:
            List of profanity matches
        """
        if not text:
            return []
        
        matches = []
        normalized = self._normalize_for_detection(text)
        
        # Word boundary pattern
        word_pattern = r'\b\w+\b'
        
        for match in re.finditer(word_pattern, normalized):
            word = match.group()
            position = match.start()
            
            if word in self.all_profanity:
                # Get context from original text
                context = self._get_context(text, position, len(word))
                
                # Check if it's a technical term
                if self._is_technical_term(word, context):
                    continue
                
                severity = self.severity_map[word]
                masked = self._mask_word(word)
                
                profanity_match = ProfanityMatch(
                    word=word,
                    severity=severity,
                    position=position,
                    length=len(word),
                    context=context,
                    masked=masked
                )
                
                matches.append(profanity_match)
                
                # Update statistics
                self.stats['total_filtered'] += 1
                self.stats['by_severity'][severity] += 1
                
                if word in self.stats['most_common']:
                    self.stats['most_common'][word] += 1
                else:
                    self.stats['most_common'][word] = 1
        
        return matches
    
    def filter(self, text: str, min_severity: Severity = Severity.MILD) -> FilterResult:
        """Filter profanity from text.
        
        Args:
            text: Text to filter
            min_severity: Minimum severity level to filter
            
        Returns:
            FilterResult with filtered text and metadata
        """
        if not text:
            return FilterResult(
                original_text=text,
                filtered_text=text,
                matches=[],
                has_profanity=False,
                max_severity=None,
                score=0.0
            )
        
        matches = self.detect_profanity(text)
        
        # Filter by minimum severity
        filtered_matches = [m for m in matches if m.severity.value >= min_severity.value]
        
        if not filtered_matches:
            return FilterResult(
                original_text=text,
                filtered_text=text,
                matches=[],
                has_profanity=False,
                max_severity=None,
                score=0.0
            )
        
        # Create filtered text
        filtered_text = text
        
        # Sort matches by position (reverse order for replacement)
        sorted_matches = sorted(filtered_matches, key=lambda m: m.position, reverse=True)
        
        for match in sorted_matches:
            start = match.position
            end = match.position + match.length
            
            # Find the corresponding position in the original text
            # (accounting for case differences)
            original_word = text[start:end]
            if original_word.lower() == match.word:
                filtered_text = (
                    filtered_text[:start] + 
                    self._mask_word(original_word) + 
                    filtered_text[end:]
                )
        
        # Calculate severity score
        max_severity = max((m.severity for m in filtered_matches), default=None)
        score = self._calculate_score(filtered_matches, len(text))
        
        return FilterResult(
            original_text=text,
            filtered_text=filtered_text,
            matches=filtered_matches,
            has_profanity=True,
            max_severity=max_severity,
            score=score
        )
    
    def _calculate_score(self, matches: List[ProfanityMatch], text_length: int) -> float:
        """Calculate profanity score (0-1).
        
        Args:
            matches: List of profanity matches
            text_length: Total text length
            
        Returns:
            Score from 0 (clean) to 1 (highly inappropriate)
        """
        if not matches or text_length == 0:
            return 0.0
        
        # Weight by severity
        severity_weights = {
            Severity.MILD: 0.25,
            Severity.MODERATE: 0.5,
            Severity.SEVERE: 0.75,
            Severity.HATE: 1.0
        }
        
        total_weight = sum(severity_weights[m.severity] for m in matches)
        
        # Factor in frequency (capped at 1.0)
        frequency_factor = min(len(matches) / 10, 1.0)
        
        # Factor in density (profanity per 100 chars)
        density_factor = min((len(matches) * 100) / text_length, 1.0)
        
        # Combine factors
        score = (total_weight * 0.5 + frequency_factor * 0.25 + density_factor * 0.25)
        
        return min(score, 1.0)
    
    def add_custom_word(self, word: str, severity: Severity):
        """Add a custom word to the filter.
        
        Args:
            word: Word to add
            severity: Severity level
        """
        word_lower = word.lower()
        self.word_lists[severity].add(word_lower)
        self.all_profanity.add(word_lower)
        self.severity_map[word_lower] = severity
    
    def remove_custom_word(self, word: str):
        """Remove a word from the filter.
        
        Args:
            word: Word to remove
        """
        word_lower = word.lower()
        if word_lower in self.severity_map:
            severity = self.severity_map[word_lower]
            self.word_lists[severity].discard(word_lower)
            self.all_profanity.discard(word_lower)
            del self.severity_map[word_lower]
    
    def get_report(self) -> Dict[str, Any]:
        """Get filtering statistics report.
        
        Returns:
            Dictionary with filtering statistics
        """
        return {
            'total_filtered': self.stats['total_filtered'],
            'by_severity': {s.name: count for s, count in self.stats['by_severity'].items()},
            'most_common': sorted(
                self.stats['most_common'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],  # Top 10
            'timestamp': datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """Reset filtering statistics."""
        self.stats = {
            'total_filtered': 0,
            'by_severity': {s: 0 for s in Severity},
            'most_common': {}
        }


# Convenience function
def filter_profanity(text: str, min_severity: Severity = Severity.MILD) -> str:
    """Quick profanity filtering function.
    
    Args:
        text: Text to filter
        min_severity: Minimum severity to filter
        
    Returns:
        Filtered text
    """
    filter = ProfanityFilter()
    result = filter.filter(text, min_severity)
    return result.filtered_text