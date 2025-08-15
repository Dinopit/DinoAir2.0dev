# Stabilization and Modular Boundaries - Phased Plan

This phased plan prioritizes import safety, test stability, and strict modular boundaries before performance polish. Each phase lists goals, concrete tasks, acceptance criteria, and simple terminal commands.

Note: GUI is already implemented. Do not add GUI elements. Keep changes self-contained and testable from terminal.

## Phase 0: Guardrails (Modular Structure Tests) - Completed
- Goal: Prevent spaghetti imports across layers (GUI/tools/agents vs. pseudocode_translator).
- Tasks:
  - Add boundary tests that scan for forbidden imports (done in tests/test_regression.py).
- Acceptance:
  - Fails if pseudocode_translator imports PySide6 or src.gui; or GUI imports pseudocode_translator.
- Commands:
  - python -m unittest pseudocode_translator.tests.test_regression.TestModularStructure

## Phase 1: Import Safety and Baseline Integrity
- Goal: Make modules importable without syntax/runtime errors.
- Tasks:
  - validator.py: ensure required imports (ast, re, tokenize, functools.lru_cache, io.StringIO), complete stubs to return lists, not raise.
  - Ensure functions provide conservative, side-effect-free behavior until full logic is in.
    - Return neutral values on failure (e.g., [], {}, None) instead of raising.
    - Catch broad exceptions within validators/analyzers and fail-safe without side effects.
    - No I/O (disk/network), no environment mutations, no GUI calls from core modules.
    - Avoid global/module-level state mutations; keep computations pure and deterministic.
    - Do not perform retries, sleeps, or external subprocess calls in interim code.
    - Prefer cached AST parsing (parse_cached) over re-parsing when applicable.
- Acceptance:
  - python -c "import pseudocode_translator.validator" completes without error.
  - python -m unittest pseudocode_translator.tests.test_regression.TestRegressionBugs.test_bug_005_circular_import_detection passes import and returns ValidationResult object (even if only basic checks pass).

## Phase 2: Validator Core (validate_syntax) and Essential Checks
- Goal: Reliable syntax validation compatible with Python 3.8+ features (walrus, match, type hints, async).
- Tasks:
  - validate_syntax: parse with ast; return ValidationResult(is_valid, errors, warnings).
  - Implement targeted checks used by tests:
    - Undefined names (conservative) for simple cases.
    - Division by zero, while True without break, unreachable code after return.
    - Missing returns for typed functions.
    - Line length vs config.max_line_length.
    - Unsafe operations with line numbers.
    - Performance: detect list.append in loops → suggestion.
- Acceptance:
  - test_validator_simple.py prints expected booleans (append detection True; scoped undefineds flagged).
  - Regression tests involving validator return is_valid where expected.

## Phase 3: Parser Robustness (ParserModule.get_parse_result)
- Goal: Parse mixed content; recognize Python constructs and f-strings, decorators, generators, walrus, match; handle unicode, nested quotes, and multiline strings.
- Tasks:
  - Precompile regexes for performance.
  - Classify BlockType (ENGLISH/PYTHON/MIXED) correctly for provided cases.
  - Gracefully fail on empty input; avoid memory spikes on very long lines.
- Acceptance:
  - Test cases: bug_001 to bug_015 that exercise parser all pass.
  - Single-line blocks produce exactly one block.

## Phase 4: Assembler Correctness (CodeAssembler.assemble)
- Goal: Deterministic output with proper indentation normalization and optional comment preservation.
- Tasks:
  - Convert tabs to spaces, stabilize indentation.
  - preserve_comments flag honored; unicode safe.
- Acceptance:
  - Mixed indentation test yields no tabs.
  - Comment preservation test finds expected comments in result.
  - Deeply nested structures preserved (outer/middle/inner present).

## Phase 5: Targeted Validator Enhancements
- Goal: Improve quality of findings without heavy dependencies.
- Tasks:
  - Style hints: function/class naming, spaces after comma, around operators.
  - Readability/basic best-practices placeholders that safely return [] to avoid false positives.
- Acceptance:
  - _check_style returns expected suggestions for simple violations.
  - No false-positive explosions on valid code samples.

## Phase 6: AST Cache Behavior
- Goal: Effective caching to reduce repeated parse costs.
- Tasks:
  - Ensure ast_cache.parse_cached returns ast.AST and caches by content.
  - Keep thread-safe LRU behavior intact.
- Acceptance:
  - TestPerformanceRegressions.test_caching_effectiveness shows second parse not slower than 1.5x first and AST dumps equal.

## Phase 7: TranslationManager Edge-Input Handling
- Goal: Graceful behavior for empty/whitespace input and async-code validation.
- Tasks:
  - translate_pseudocode rejects empty/whitespace with errors.
  - Accept mocked model translation (async def) and pass validator.
- Acceptance:
  - bug_001 and bug_008 tests pass.

## Phase 8: Boundary Enforcement and Audit
- Goal: Ensure no forbidden cross-layer imports remain.
- Tasks:
  - Run modular structure tests.
  - Quick grep for "PySide6" inside pseudocode_translator and "pseudocode_translator" in GUI.
- Acceptance:
  - TestModularStructure passes fully.

## Phase 9: Performance Polish
- Goal: Confirm large-file handling and memory stability.
- Tasks:
  - Avoid re-parsing when possible; reuse trees in validator where cached.
  - Keep operations linear for 100*function template sample.
- Acceptance:
  - Large file parsing under 5 seconds; memory stability test passes.

## Phase 10: Documentation and Maintenance
- Goal: Update docs to reflect stable interfaces and behavior.
- Tasks:
  - Add troubleshooting notes for validator/parser behaviors and performance tips.
  - Keep guides consistent with tested capabilities.

---

## Quick Commands

- Run full suite:
  - python -m unittest pseudocode_translator.tests.test_regression
- Focused subsets:
  - python -m unittest pseudocode_translator.tests.test_regression.TestRegressionBugs
  - python -m unittest pseudocode_translator.tests.test_regression.TestEdgeCaseRegressions
  - python -m unittest pseudocode_translator.tests.test_regression.TestPerformanceRegressions
  - python -m unittest pseudocode_translator.tests.test_regression.TestModularStructure

## Notes
- Keep changes isolated per file; no dynamic GUI logic.
- Use only stdlib (ast, re, tokenize, functools, io, datetime).
- Respect Input → Sanitizer → Classifier → Tool → DB/LLM pipeline where applicable.

1. Codebase Hygiene

 Dead Code Removal: Any leftover debug routes? Half-baked tools? print() statements pretending to be logs?

 Modular Structure Check: Ensure tools, agents, utils, and GUI aren’t tangled spaghetti.

 Config Isolation: All paths, secrets, and toggles should live in config.py or .env.

🚦 2. Startup Sanity

 Clean terminal logs (e.g. “✅ Tools loaded” instead of Python trace gibberish)

 GUI launch failsafe (if SQLite or agent isn’t ready, show a nice warning)

 Silent fallback for disconnected tools (don't explode on tool errors)

⚙️ 3. Tools and Plugin Stability

 Each tool runs independently from CLI

 Return format is always structured (e.g. JSON, not string dumps)

 If tool fails, it should send structured error → not crash DinoAir

🧠 4. Memory + Context Improvements

 Sanity-check what gets stored in memory (no nonsense creeping in)

 Limit token bloat: don’t jam huge irrelevant logs into model context

 SQLite? JSON? Pick one and stick to it across all tools

🪄 5. Assistant Interaction

 Tools are clearly discoverable by the AI (if agent-calling is active)

 Function schemas are correctly structured (e.g. tool returns must match function defs)

 Can simulate “tool awareness” without reloading every time

🎨 6. GUI Polish Pass

 Font sizes, colors, and tabs cleanly visible in dark mode

 No “ghost” elements or tabs that don’t do anything yet

 File structure reflects GUI layout (so 2.5 port is easier later)

🔥 7. Performance Boosts (If Needed)

 Any tools that lag? Run a profiler like cProfile or pyinstrument

 Async might be worth adding for long-running tools — only after stability

 Are you caching model calls or RAG results? Could shave seconds off

🧪 Bonus: “Am I Done?” Checklist

If you can:

 Launch from CLI or GUI with no errors

 Trigger every tool cleanly from the GUI and/or CLI

 Exit and restart without broken state

 Let someone else use it with no guidance (and not crash it)

Then DinoAir 2.0 is stable enough to polish or clone into 2.5 👑