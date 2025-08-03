"""Pattern normalization and fuzzy matching module.

Normalizes common patterns and typos to improve intent recognition
and user experience.
"""

from typing import Tuple, Dict, List, Optional
import re
from difflib import SequenceMatcher


class PatternNormalizer:
    """Normalizes patterns and fixes common typos.
    
    This class handles pattern normalization, typo correction,
    and fuzzy matching to improve user input understanding.
    """
    
    def __init__(self):
        """Initialize with pattern replacements and shortcuts."""
        # Common time pattern replacements
        self.time_patterns = {
            r'\b(\d+)\s*mins?\b': r'\1 minutes',
            r'\b(\d+)\s*min\b': r'\1 minutes',
            r'\b(\d+)\s*hrs?\b': r'\1 hours',
            r'\b(\d+)\s*hr\b': r'\1 hours',
            r'\b(\d+)\s*secs?\b': r'\1 seconds',
            r'\b(\d+)\s*sec\b': r'\1 seconds',
            r'\b(\d+)\s*ms\b': r'\1 milliseconds',
            r'\b(\d+)m\b': r'\1 minutes',
            r'\b(\d+)h\b': r'\1 hours',
            r'\b(\d+)s\b': r'\1 seconds',
        }
        
        # Common shortcuts and abbreviations
        self.shortcuts = {
            'pls': 'please',
            'plz': 'please',
            'thx': 'thanks',
            'ty': 'thank you',
            'tysm': 'thank you so much',
            'u': 'you',
            'ur': 'your',
            'r': 'are',
            'b4': 'before',
            '2': 'to',
            '4': 'for',
            'w/': 'with',
            'w/o': 'without',
            'btw': 'by the way',
            'imo': 'in my opinion',
            'imho': 'in my humble opinion',
            'fyi': 'for your information',
            'asap': 'as soon as possible',
            'eta': 'estimated time of arrival',
        }
        
        # Command variations
        self.command_variations = {
            'stop watchdog': ['stop wd', 'kill watchdog', 'end watchdog', 'watchdog stop'],
            'start watchdog': ['start wd', 'run watchdog', 'begin watchdog', 'watchdog start'],
            'watchdog status': ['wd status', 'watchdog info', 'check watchdog', 'watchdog check'],
            'clear chat': ['clear history', 'delete chat', 'reset chat', 'clean chat'],
            'save chat': ['export chat', 'download chat', 'backup chat'],
            'help': ['?', 'h', 'commands', 'what can you do'],
        }
        
        # Build reverse lookup for command variations
        self.command_lookup = {}
        for canonical, variations in self.command_variations.items():
            for variant in variations:
                self.command_lookup[variant.lower()] = canonical
    
    def normalize_time_patterns(self, text: str) -> str:
        """Normalize time-related patterns.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized time patterns
        """
        result = text
        for pattern, replacement in self.time_patterns.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
    
    def expand_shortcuts(self, text: str) -> str:
        """Expand common shortcuts and abbreviations.
        
        Args:
            text: Input text
            
        Returns:
            Text with expanded shortcuts
        """
        # Split into words to avoid partial matches
        words = text.split()
        expanded_words = []
        
        for word in words:
            # Preserve punctuation
            prefix = ''
            suffix = ''
            clean_word = word
            
            # Extract leading punctuation
            while clean_word and not clean_word[0].isalnum():
                prefix += clean_word[0]
                clean_word = clean_word[1:]
            
            # Extract trailing punctuation
            while clean_word and not clean_word[-1].isalnum():
                suffix = clean_word[-1] + suffix
                clean_word = clean_word[:-1]
            
            # Check if it's a shortcut
            lower_word = clean_word.lower()
            if lower_word in self.shortcuts:
                expanded_words.append(prefix + self.shortcuts[lower_word] + suffix)
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        # Add space after punctuation if missing
        text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
        return text.strip()
    
    def normalize_case(self, text: str) -> str:
        """Normalize case for better matching.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized case
        """
        # Don't lowercase everything - preserve acronyms and proper nouns
        # Just normalize common patterns
        if text.isupper() and len(text) > 4:
            # All caps text (likely shouting) - convert to title case
            return text.title()
        return text
    
    def find_command_match(self, text: str) -> Optional[str]:
        """Find matching command from variations.
        
        Args:
            text: Input text
            
        Returns:
            Canonical command name if found, None otherwise
        """
        lower_text = text.lower().strip()
        
        # Direct lookup
        if lower_text in self.command_lookup:
            return self.command_lookup[lower_text]
        
        # Check if text starts with any variation
        for variant, canonical in self.command_lookup.items():
            if lower_text.startswith(variant):
                return canonical
        
        # Fuzzy matching for close matches
        best_match = None
        best_ratio = 0.0
        threshold = 0.8  # 80% similarity required
        
        for variant in self.command_lookup:
            ratio = SequenceMatcher(None, lower_text, variant).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = self.command_lookup[variant]
        
        return best_match
    
    def fix_common_typos(self, text: str) -> str:
        """Fix common typos using fuzzy matching.
        
        Args:
            text: Input text
            
        Returns:
            Text with common typos fixed
        """
        # Common typo patterns
        typo_fixes = {
            r'\bteh\b': 'the',
            r'\btaht\b': 'that',
            r'\bwaht\b': 'what',
            r'\bwehn\b': 'when',
            r'\bwhcih\b': 'which',
            r'\bcoudl\b': 'could',
            r'\bwoudl\b': 'would',
            r'\bshoudl\b': 'should',
            r'\btihs\b': 'this',
            r'\bhte\b': 'the',
            r'\badn\b': 'and',
            r'\bteh\b': 'the',
            r'\byuo\b': 'you',
            r'\byoru\b': 'your',
            r'\bthier\b': 'their',
            r'\bfreind\b': 'friend',
            r'\bbeacuse\b': 'because',
            r'\bdefinate\b': 'definite',
            r'\boccured\b': 'occurred',
            r'\buntill\b': 'until',
            r'\brecieve\b': 'receive',
            r'\bseperate\b': 'separate',
        }
        
        result = text
        for pattern, replacement in typo_fixes.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def normalize(self, text: str) -> Tuple[str, Dict[str, any]]:
        """Normalize text through all stages.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Tuple of (normalized_text, metadata_dict)
        """
        if not text:
            return text, {}
        
        original = text
        metadata = {
            'original': original,
            'transformations': []
        }
        
        # Apply normalizations in order
        # 1. Fix whitespace first
        text = self.normalize_whitespace(text)
        if text != original:
            metadata['transformations'].append('whitespace_normalized')
        
        # 2. Fix common typos
        text = self.fix_common_typos(text)
        if text != original:
            metadata['transformations'].append('typos_fixed')
        
        # 3. Expand shortcuts
        expanded = self.expand_shortcuts(text)
        if expanded != text:
            metadata['transformations'].append('shortcuts_expanded')
            text = expanded
        
        # 4. Normalize time patterns
        time_normalized = self.normalize_time_patterns(text)
        if time_normalized != text:
            metadata['transformations'].append('time_patterns_normalized')
            text = time_normalized
        
        # 5. Normalize case
        case_normalized = self.normalize_case(text)
        if case_normalized != text:
            metadata['transformations'].append('case_normalized')
            text = case_normalized
        
        # 6. Check for command match
        command_match = self.find_command_match(text)
        if command_match:
            metadata['detected_command'] = command_match
        
        metadata['normalized'] = text
        metadata['changed'] = text != original
        
        return text, metadata


class FuzzyMatcher:
    """Handles fuzzy string matching for improved UX.
    
    This class provides fuzzy matching capabilities to handle
    user typos and variations in commands or queries.
    """
    
    def __init__(self, candidates: List[str]):
        """Initialize with list of valid candidates.
        
        Args:
            candidates: List of valid strings to match against
        """
        self.candidates = [c.lower() for c in candidates]
        self.original_candidates = candidates
    
    def find_best_match(self, query: str, threshold: float = 0.6) -> Optional[Tuple[str, float]]:
        """Find best matching candidate for query.
        
        Args:
            query: Query string to match
            threshold: Minimum similarity ratio (0-1)
            
        Returns:
            Tuple of (best_match, similarity_ratio) or None
        """
        if not query:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_ratio = 0.0
        best_index = -1
        
        for i, candidate in enumerate(self.candidates):
            # Check exact match first
            if query_lower == candidate:
                return (self.original_candidates[i], 1.0)
            
            # Check if query is substring
            if query_lower in candidate:
                ratio = len(query_lower) / len(candidate)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = self.original_candidates[i]
                    best_index = i
                continue
            
            # Fuzzy matching
            ratio = SequenceMatcher(None, query_lower, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = self.original_candidates[i]
                best_index = i
        
        if best_ratio >= threshold:
            return (best_match, best_ratio)
        
        return None
    
    def find_all_matches(self, query: str, threshold: float = 0.6, max_results: int = 5) -> List[Tuple[str, float]]:
        """Find all matching candidates above threshold.
        
        Args:
            query: Query string to match
            threshold: Minimum similarity ratio (0-1)
            max_results: Maximum number of results to return
            
        Returns:
            List of (match, similarity_ratio) tuples, sorted by ratio
        """
        if not query:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for i, candidate in enumerate(self.candidates):
            ratio = SequenceMatcher(None, query_lower, candidate).ratio()
            if ratio >= threshold:
                matches.append((self.original_candidates[i], ratio))
        
        # Sort by ratio descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:max_results]


# Convenience functions
def normalize_input(text: str) -> Tuple[str, Dict[str, any]]:
    """Normalize user input text.
    
    Args:
        text: Raw user input
        
    Returns:
        Tuple of (normalized_text, metadata)
    """
    normalizer = PatternNormalizer()
    return normalizer.normalize(text)


def fuzzy_match(query: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
    """Find best fuzzy match from candidates.
    
    Args:
        query: Query string
        candidates: List of valid options
        threshold: Minimum similarity (0-1)
        
    Returns:
        Best matching candidate or None
    """
    matcher = FuzzyMatcher(candidates)
    result = matcher.find_best_match(query, threshold)
    return result[0] if result else None