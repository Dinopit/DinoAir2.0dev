"""
Unicode attack testing module.

Tests for Unicode normalization and encoding vulnerabilities.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class UnicodeAttackTester(BaseSecurityTester):
    """Tests for Unicode-based vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Unicode Attacks"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get Unicode attack test payloads."""
        return [
            # Basic Unicode variations
            ("admin\u200b", "Zero-width space in username"),
            ("admin\u00a0", "Non-breaking space"),
            ("admin\ufeff", "Zero-width no-break space"),
            
            # Homoglyphs
            ("аdmin", "Cyrillic 'а' instead of Latin 'a'"),
            ("аdmіn", "Multiple Cyrillic letters"),
            ("ɑdmin", "IPA Latin alpha"),
            
            # Direction control
            ("\u202eadmin", "Right-to-left override"),
            ("admin\u202d", "Left-to-right override"),
            ("\u2066admin\u2069", "Isolated text"),
            
            # Normalization attacks
            ("café", "NFC form"),
            ("café", "NFD form (decomposed)"),
            ("ﬁle", "Ligature 'fi'"),
            
            # Case folding attacks
            ("ADMIN", "Upper case"),
            ("Admin", "Mixed case"),
            ("aDmIn", "Random case"),
            
            # Combining characters
            ("admin̸", "Combining solidus overlay"),
            ("admin⃠", "Combining enclosing circle backslash"),
            ("ã́dmin", "Multiple combining marks"),
            
            # Invisible characters
            ("ad\u200cmin", "Zero-width non-joiner"),
            ("ad\u200dmin", "Zero-width joiner"),
            ("admin\u2060", "Word joiner"),
            
            # Confusables
            ("аⅾmіn", "Mixed scripts confusables"),
            ("αdmιn", "Greek letters"),
            ("𝖺𝖽𝗆𝗂𝗇", "Mathematical alphanumeric"),
            
            # Emoji attacks
            ("admin🔒", "Emoji in username"),
            ("👤admin", "Emoji prefix"),
            ("ad👁min", "Emoji insertion"),
            
            # Null bytes
            ("admin\x00", "Null byte suffix"),
            ("\x00admin", "Null byte prefix"),
            ("ad\x00min", "Null byte insertion"),
            
            # Overlong encodings
            ("\xc0\xaf", "Overlong slash"),
            ("\xe0\x80\xaf", "Triple-byte overlong"),
            ("\xf0\x80\x80\xaf", "Quad-byte overlong"),
            
            # Zalgo text
            ("a̸̗̲̤̪̟͓͔͕̰͍̐̃͌̊̈́̾̇͒̚d̷̢̧̛̰̯̖̺̙̮̩̔̈́̆̊̒̆͊̚m̴̧̨̱̜̲̺̖̻̠̏̊̐̃̆̈́̾̉͘"
             "i̵̢̨̛̗̣̦̟̝̦̇̐̓̒̊̈́̚͜͝n̸̡̧̢̛̪̱̯̬̼̏̊̆̈́̒̚͘",
             "Zalgo text"),
            
            # Bidirectional text
            ("admin مدير", "Mixed LTR/RTL"),
            ("‏admin‏", "RTL marks"),
            ("‪admin‬", "Embedding marks"),
        ]