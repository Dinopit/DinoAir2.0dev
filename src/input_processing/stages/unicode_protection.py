"""
Unicode Attack Protection Module.

Provides comprehensive protection against Unicode-based attacks.
"""

import unicodedata
from typing import Dict, Set, Optional


class UnicodeProtection:
    """Comprehensive Unicode attack protection."""
    
    # Dangerous Unicode categories
    DANGEROUS_CATEGORIES: Set[str] = {
        'Cf',  # Format characters (invisible)
        'Co',  # Private use
        'Cn',  # Unassigned
    }
    
    # Specific dangerous characters
    DANGEROUS_CHARS: Set[str] = {
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u200e',  # Left-to-right mark
        '\u200f',  # Right-to-left mark
        '\u202a',  # Left-to-right embedding
        '\u202b',  # Right-to-left embedding
        '\u202c',  # Pop directional formatting
        '\u202d',  # Left-to-right override
        '\u202e',  # Right-to-left override
        '\u2060',  # Word joiner
        '\ufeff',  # Zero-width no-break space
        '\u206a',  # Inhibit symmetric swapping
        '\u206b',  # Activate symmetric swapping
        '\u206c',  # Inhibit Arabic form shaping
        '\u206d',  # Activate Arabic form shaping
        '\u206e',  # National digit shapes
        '\u206f',  # Nominal digit shapes
        '\u2061',  # Function application
        '\u2062',  # Invisible times
        '\u2063',  # Invisible separator
        '\u2064',  # Invisible plus
        '\u2066',  # Left-to-right isolate
        '\u2067',  # Right-to-left isolate
        '\u2068',  # First strong isolate
        '\u2069',  # Pop directional isolate
        '\u180e',  # Mongolian vowel separator
        '\ufffe',  # Non-character
        '\uffff',  # Non-character
    }
    
    # Homograph mapping (common confusables)
    HOMOGRAPH_MAP: Dict[str, str] = {
        # Cyrillic to Latin
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c',
        'у': 'y', 'х': 'x', 'А': 'A', 'В': 'B', 'Е': 'E',
        'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P',
        'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        'ѕ': 's', 'і': 'i', 'ј': 'j', 'һ': 'h', 'ԁ': 'd',
        'ԛ': 'q', 'ԝ': 'w', 'ѐ': 'e', 'ё': 'e',
        
        # Greek to Latin
        'α': 'a', 'β': 'b', 'γ': 'y', 'δ': 'd', 'ε': 'e',
        'ζ': 'z', 'η': 'n', 'θ': 'o', 'ι': 'i', 'κ': 'k',
        'λ': 'l', 'μ': 'u', 'ν': 'v', 'ξ': 'e', 'ο': 'o',
        'π': 'n', 'ρ': 'p', 'σ': 'o', 'τ': 't', 'υ': 'u',
        'φ': 'o', 'χ': 'x', 'ψ': 'w', 'ω': 'w',
        'Α': 'A', 'Β': 'B', 'Γ': 'T', 'Δ': 'A', 'Ε': 'E',
        'Ζ': 'Z', 'Η': 'H', 'Θ': 'O', 'Ι': 'I', 'Κ': 'K',
        'Λ': 'A', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'E', 'Ο': 'O',
        'Π': 'N', 'Ρ': 'P', 'Σ': 'E', 'Τ': 'T', 'Υ': 'Y',
        'Φ': 'O', 'Χ': 'X', 'Ψ': 'W', 'Ω': 'O',
        
        # Mathematical/Special to Latin
        '𝖺': 'a', '𝖻': 'b', '𝖼': 'c', '𝖽': 'd', '𝖾': 'e',
        '𝖿': 'f', '𝗀': 'g', '𝗁': 'h', '𝗂': 'i', '𝗃': 'j',
        '𝗄': 'k', '𝗅': 'l', '𝗆': 'm', '𝗇': 'n', '𝗈': 'o',
        '𝗉': 'p', '𝗊': 'q', '𝗋': 'r', '𝗌': 's', '𝗍': 't',
        '𝗎': 'u', '𝗏': 'v', '𝗐': 'w', '𝗑': 'x', '𝗒': 'y',
        '𝗓': 'z',
        
        # Full-width to normal
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y',
        'ｚ': 'z',
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
        'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
        'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
        'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y',
        'Ｚ': 'Z',
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        
        # Common ligatures
        'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
        'ﬅ': 'st', 'ﬆ': 'st',
        
        # IPA Extensions
        'ɑ': 'a',  # Latin alpha
        'ɐ': 'a',  # Turned a
        'ɒ': 'a',  # Turned alpha
        'ʙ': 'b',  # Small capital B
        'ɕ': 'c',  # Curled c
        'ɖ': 'd',  # Retroflex d
        'ɛ': 'e',  # Open e
        'ɜ': 'e',  # Reversed open e
        'ɢ': 'g',  # Small capital G
        'ɦ': 'h',  # H with hook
        'ɪ': 'i',  # Small capital I
        'ɨ': 'i',  # Barred i
        'ʟ': 'l',  # Small capital L
        'ɴ': 'n',  # Small capital N
        'ɔ': 'o',  # Open o
        'ɵ': 'o',  # Barred o
        'ʀ': 'r',  # Small capital R
        'ʁ': 'r',  # Inverted small capital R
        'ʏ': 'y',  # Small capital Y
        'ʊ': 'u',  # Upsilon
    }
    
    # Script names that should not be mixed
    SCRIPT_NAMES: Set[str] = {
        'LATIN', 'CYRILLIC', 'GREEK', 'ARABIC', 'HEBREW',
        'DEVANAGARI', 'BENGALI', 'GURMUKHI', 'GUJARATI',
        'ORIYA', 'TAMIL', 'TELUGU', 'KANNADA', 'MALAYALAM',
        'SINHALA', 'THAI', 'LAO', 'TIBETAN', 'MYANMAR',
        'GEORGIAN', 'HANGUL', 'ETHIOPIC', 'CHEROKEE',
        'CANADIAN', 'OGHAM', 'RUNIC', 'TAGALOG', 'HANUNOO',
        'BUHID', 'TAGBANWA', 'KHMER', 'MONGOLIAN'
    }
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Unicode text to prevent attacks."""
        if not text:
            return text
            
        # Step 1: NFD normalization (decompose)
        text = unicodedata.normalize('NFD', text)
        
        # Step 2: Remove dangerous characters
        cleaned = []
        for char in text:
            if char not in UnicodeProtection.DANGEROUS_CHARS:
                cleaned.append(char)
        text = ''.join(cleaned)
        
        # Step 3: Remove characters from dangerous categories
        cleaned = []
        for char in text:
            category = unicodedata.category(char)
            if category not in UnicodeProtection.DANGEROUS_CATEGORIES:
                cleaned.append(char)
        text = ''.join(cleaned)
        
        # Step 4: Convert homographs
        chars = list(text)
        for i, char in enumerate(chars):
            if char in UnicodeProtection.HOMOGRAPH_MAP:
                chars[i] = UnicodeProtection.HOMOGRAPH_MAP[char]
        text = ''.join(chars)
        
        # Step 5: NFC normalization (compose)
        text = unicodedata.normalize('NFC', text)
        
        # Step 6: Remove excessive combining characters
        # Allow max 2 combining chars per base character
        result = []
        combining_count = 0
        
        for char in text:
            if unicodedata.category(char).startswith('M'):
                # Combining character
                combining_count += 1
                if combining_count <= 2:
                    result.append(char)
            else:
                # Base character
                combining_count = 0
                result.append(char)
        
        return ''.join(result)
    
    @staticmethod
    def detect_unicode_attack(text: str) -> bool:
        """Detect potential Unicode-based attacks."""
        if not text:
            return False
            
        # Check for dangerous characters
        for char in text:
            if char in UnicodeProtection.DANGEROUS_CHARS:
                return True
        
        # Check for mixed scripts
        scripts = set()
        for char in text:
            if char.isalpha():
                try:
                    char_name = unicodedata.name(char, '')
                    if char_name:
                        # Extract script from character name
                        for script in UnicodeProtection.SCRIPT_NAMES:
                            if script in char_name:
                                scripts.add(script)
                                break
                except ValueError:
                    pass
        
        # Multiple scripts = possible homograph attack
        if len(scripts) > 1:
            # Allow mixing with LATIN for legitimate cases
            non_latin_scripts = scripts - {'LATIN'}
            if len(non_latin_scripts) > 1:
                return True
            # If mixing Cyrillic/Greek with Latin, it's suspicious
            if non_latin_scripts and 'LATIN' in scripts:
                suspicious_scripts = {'CYRILLIC', 'GREEK'}
                if non_latin_scripts & suspicious_scripts:
                    return True
        
        # Check for excessive combining characters
        text_len = len(text)
        if text_len > 0:
            combining_count = sum(
                1 for c in text 
                if unicodedata.category(c).startswith('M')
            )
            if combining_count > text_len * 0.3:  # More than 30%
                return True
        
        # Check for right-to-left override
        rtl_chars = {'\u202e', '\u202b', '\u200f'}
        if any(char in text for char in rtl_chars):
            return True
        
        # Check for invisible characters
        invisible_count = sum(
            1 for c in text 
            if unicodedata.category(c) in {'Cf', 'Cc'}
        )
        if invisible_count > 0:
            return True
        
        return False
    
    @staticmethod
    def remove_bidi_controls(text: str) -> str:
        """Remove bidirectional control characters."""
        if not text:
            return text
            
        bidi_controls = {
            '\u200e',  # LRM
            '\u200f',  # RLM
            '\u202a',  # LRE
            '\u202b',  # RLE
            '\u202c',  # PDF
            '\u202d',  # LRO
            '\u202e',  # RLO
            '\u2066',  # LRI
            '\u2067',  # RLI
            '\u2068',  # FSI
            '\u2069',  # PDI
        }
        
        return ''.join(c for c in text if c not in bidi_controls)
    
    @staticmethod
    def to_ascii_safe(text: str) -> str:
        """Convert to ASCII-safe representation."""
        if not text:
            return text
            
        # First normalize
        text = UnicodeProtection.normalize_unicode(text)
        
        # Then convert to ASCII
        try:
            # Try simple ASCII encode
            return text.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            # Fallback: convert character by character
            result = []
            for char in text:
                try:
                    char.encode('ascii')
                    result.append(char)
                except Exception:
                    # Try to get ASCII representation
                    if char in UnicodeProtection.HOMOGRAPH_MAP:
                        result.append(
                            UnicodeProtection.HOMOGRAPH_MAP[char]
                        )
                    else:
                        # Skip non-ASCII chars
                        pass
            return ''.join(result)
    
    @staticmethod
    def sanitize(
        text: str,
        allow_unicode: bool = True,
        max_length: Optional[int] = None
    ) -> str:
        """Main sanitization method."""
        if not text:
            return text
            
        # Always normalize
        text = UnicodeProtection.normalize_unicode(text)
        
        # Remove bidi controls
        text = UnicodeProtection.remove_bidi_controls(text)
        
        # Convert to ASCII if required
        if not allow_unicode:
            text = UnicodeProtection.to_ascii_safe(text)
        
        # Apply length limit if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()