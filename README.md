Private README — DinoAir 2.5 (internal)

This README is written for my private repo and daily use on Windows. It aims to make fresh installs, clean resets, and common workflows fast and predictable.

Quick Start (Windows, Python 3.12)
- Create venv:
  - `py -3.12 -m venv .venv`
  - `.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel`
- Install deps (Windows-friendly):
  - `.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt`
- Run app:
  - `.\.venv\Scripts\python.exe main.py`

Notes on Dependencies
- The `requirements.txt` skips `faiss-cpu` on Windows and includes `PyYAML` + `tqdm`, which avoids native build headaches and covers runtime imports used by the pseudocode translator.
- Heavy packages (torch, transformers) are pinned to binary wheels — expect a larger install, but no compilation.

Clean Reset (nuclear)
- Terminates Python, removes venvs, caches, logs, dbs, and user data:
  - `taskkill /F /IM python.exe /T 2>$null; taskkill /F /IM py.exe /T 2>$null`
  - `if (Test-Path .\.venv) { cmd /c "rmdir /s /q .\.venv" }`
  - `Get-ChildItem -Recurse -Directory -Force | ? { $_.Name -in '__pycache__','.pytest_cache','.mypy_cache','.ruff_cache' } | rm -Recurse -Force`
  - `Get-ChildItem -Recurse -Force -Include *.pyc,*.pyo | rm -Force`
  - `if (Test-Path .\logs) { rm -Recurse -Force .\logs }`
  - `Get-ChildItem -Recurse -Force -Include *.db,*.log | rm -Force`
  - `if (Test-Path .\user_data) { rm -Recurse -Force .\user_data }`

Minimal Test Workflow
- GUI quick tests (tasks available in VS Code):
  - `pytest -q tests/test_notes_gui.py`
  - `pytest -q tests/test_signal_coordination_integration.py`
- Pseudocode translator tests (skip slow):
  - `.\.venv\Scripts\python.exe -m pip install pytest pytest-asyncio pytest-timeout pytest-mock`
  - `.\.venv\Scripts\python.exe -m pytest -q pseudocode_translator/tests -m "not slow"`
- Bandit + audit:
  - `.\.venv\Scripts\python.exe -m bandit -r src utils dinoair -x tests,.venv -ll`
  - `.\.venv\Scripts\python.exe -m pip_audit -r requirements-prod.lock.txt`

Operational Tips
- Ollama: verify service is up (`ollama --version`), and keep `config/app_config.json` host/port aligned.
- Logs: app logs live under `logs/`. Use when debugging startup or tool orchestration.
- Databases: multiple SQLite dbs under `src/database`-managed locations; delete `*.db` for a clean state.

Known Windows Pitfalls
- Locked venv files: kill `python.exe` before removing `.venv`.
- Native builds: avoid installing `llama-cpp-python`, `line-profiler`, `py-spy` on Windows unless toolchains are present. Tests mock LLM, so they are not required.
- `faiss-cpu` is skipped on Windows via marker.

Security Posture
- SQL safety centralized; dynamic SQL guarded with allowlists or parameterization. Bandit clean (0 Medium/High) on core modules.
- Control-plane endpoints restricted to POST for mutations.
- Subprocesses use absolute paths and `shell=False`.

Handy Commands
- Start app: `.\.venv\Scripts\python.exe main.py`
- Run quick tests: `pytest -q tests/test_notes_gui.py`
- Full clean + reinstall:
  - Clean (see “Clean Reset”), then run Quick Start commands again.

Private TODO (running list)
- [ ] Add unit tests for `src/database/sql_safety.py`
- [ ] Optional Windows CI job with cached wheels
- [ ] Document minimal deps for pseudocode translator in `pseudocode_translator/README.md`

Repo Structure (high-level)
- `src/` app code (GUI, tools, agents, database, utils)
- `pseudocode_translator/` translator module + tests
- `config/` config files (service, app, env)
- `tests/` integration and GUI tests
- `docs/` reference and architecture notes

License & Usage
- Private repo. MIT with Ethical Use clause in `LICENSE`. Keep `.env` and secrets out of VCS.
