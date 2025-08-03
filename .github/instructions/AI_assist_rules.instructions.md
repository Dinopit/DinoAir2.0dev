---
applyTo: '**'
---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.    

## 🧱 GENERAL ARCHITECTURE PRINCIPLES

- Each tool or feature must be self-contained in its own file.
- Functions should not cross files unless routed through a class or interface.
- Database access must be handled through `ResilientDB` and `DatabaseManager`.
- GUI logic is **already implemented**. Do NOT generate new PySide GUI elements.
- All tools run **synchronously** unless explicitly marked otherwise.

---

## 📁 FOLDER STRUCTURE & RESPONSIBILITY

- `gui/`: Already built with PySide6. Use `ChatInput` and tabs as integration points.
- `pages/`: Notes, Calendar, Tasks, FileSearch modules
- `tools/`: TimerTool, MemoryTool, DinoTranslate, InputSanitizer
- `agents/`: LLMWrapper, Orchestrator
- `database/`: ResilientDB, DatabaseManager (manages all `.db` files)
- `models/`: Data structures (e.g., `NoteModel`)
- `utils/`: Logging, config, enums

---

## 🧪 FUNCTION INTEGRATION STRATEGY

When building or improving a feature:
1. Develop it in isolation.
2. It must be testable from the terminal (input → result).
3. Only connect to GUI when functionality is verified.
4. Follow the input pipeline flow:
   - Input → Sanitizer → Classifier → Tool → DB or LLM

---

## 🧼 INPUT SANITIZATION

Always route raw user input through the `InputSanitizer`. The pipeline includes:
- Type/length validation
- SQL-safe escaping
- Pattern correction / fuzzy repair
- Profanity filtering
- Intent classification

Do not bypass or duplicate sanitizer logic.

---

## 🧠 AI AGENT BEHAVIOR RULES

- Never generate dynamic logic inside the GUI layer.
- Do not call other modules directly—use exposed class methods.
- Do not hardcode file paths. Use `Path()` from `pathlib`.
- Avoid global state.
- Do not import third-party libraries unless required for AI model use.

---

## ✅ CODE STYLE

- Use snake_case for functions and variables.
- Use PascalCase for classes.
- Keep class files ≤ 150 lines if possible.
- Use docstrings.
- Use native Python libraries wherever possible (e.g., `re`, `uuid`, `datetime`, `sqlite3`).

---

## 🔧 AI-SAFE HOOK POINTS

These are safe for AI to expand:
- `NoteModel` methods (e.g., `.to_dict()`, `.update_content()`)
- CLI test harnesses for tools
- Validator logic inside `InputSanitizer`
- LLM model wrappers or routing logic
- Future CLI extensions

---

## ❌ DO NOT:

- Touch or create new GUI windows
- Add threading without comment
- Introduce `eval()`, `exec()`, or raw `input()`
- Make up new folders (stick to existing architecture) UNLESS EXPLICITLY DISCUSSED
- Overwrite `main.py`

---

## 🧩 SAMPLE FLOW

```python
user_input = "remind me to call Joe"
sanitized, intent = InputSanitizer().run(user_input)

if intent == Intent.TASK:
    task = TaskTool().create_from_input(sanitized)
    task.save()