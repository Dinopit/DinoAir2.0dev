
# InputSanitizer Module Design Guide

Recommended Architecture:

1. validation.py
Purpose: Security-focused input validation
Features: Path traversal detection, command injection prevention, length limits
Returns: ValidationResult with threat level assessment

Normalize and Resolve Paths: Always convert the user-supplied path to an absolute path (using os.path.realpath() or Path.resolve()) and ensure it stays within an explicitly allowed base directory. For example:

python
import os
def is_safe_path(base_dir, user_path):
    abs_base = os.path.realpath(base_dir)
    abs_user = os.path.realpath(os.path.join(base_dir, user_path))
    return abs_user.startswith(abs_base)
This prevents users from escaping the intended directory.

Prefer Pathlib Over os.path: Pathlib's Path.resolve() and Path.relative_to() give clearer, more robust file handling. Example:

python
from pathlib import Path
def is_safe_path(base_dir, user_path):
    base = Path(base_dir).resolve()
    candidate = (base / user_path).resolve()
    # Raises ValueError if candidate is not below base
    candidate.relative_to(base)
    return True
This approach raises exceptions if traversal is detected.

Whitelist Allowed Files/IDs: Restrict inputs to a set of filenames or file IDs that you control, rather than accepting arbitrary strings. This may involve mapping IDs to files internally, with no direct user input in path assembly.

Avoid User-Controlled File Paths When Possible: Where feasible, design your APIs or commands so that users never directly supply file paths. Prefer indirect references (like IDs or keys), and resolve those server-side.

Do Not Rely on Blacklist Filtering: Simple checks, like rejecting paths containing "..", are easily bypassed with encoding tricks or alternate path separators. Proper path canonicalization must precede any directory check.

Relevant Example Patterns:

Using os.path.abspath() or os.path.realpath() plus prefix checking with your base directory.

Using Path.resolve() and then relative_to() from pathlib to ensure the requested file is a subpath of the safe directory.

Implementing a whitelist of allowed filenames.

Detection Considerations:

Test with various path encodings (e.g., %2e%2e%2f, double encoding, mixed path separators) as attackers might try obfuscated inputs.

Always validate and canonicalize after decoding and normalizing input, just before file operations.

Caveat:

Path traversal risks also appear during operations such as archive extraction (e.g., tar files). Always verify extracted file paths remain within intended directories.


2. escaping.py
Purpose: Model-specific character escaping
Strategy Pattern: ClaudeEscaper, GPTEscaper, DefaultEscaper
Prevents: Prompt injection, formatting issues

3. pattern.py
Purpose: Pattern normalization and typo correction
Features: Time pattern normalization, command shortcuts, fuzzy matching
Improves: User experience and intent recognition

4. profanity.py
Purpose: Content filtering with severity levels
Features: Configurable word lists, severity classification
Returns: FilterResult with flagged words and severity

5. intent.py
Purpose: Classify user input into actionable intents
Features: Keyword/phrase matching, context awareness, confidence scoring
Intents: NOTE, TIMER, SEARCH, HELP, WATCHDOG, etc.

6. rate_limiter.py (Extract from main)
Purpose: Prevent spam and abuse
Features: Configurable cooldown, per-user tracking

7. command_handlers/ (New directory)
watchdog_commands.py: All watchdog-specific logic
Future: Other command modules