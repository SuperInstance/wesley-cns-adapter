# Contributing to Wesley CNS Adapter

Thanks for helping Wesley hear the bus. This is a small project with a clear scope.

## Scope

This adapter connects Wesley (IBM Granite via Ollama) to the CNS signal bus. It:

1. Listens for USCP packets addressed to Wesley
2. Translates them to Ollama chat messages
3. Sends Wesley's response back through the CNS inbox

**In scope:** USCP translation, Ollama integration, signal handling, CLI tooling
**Out of scope:** Wesley's training (that's the distillation loop), CNS bus infrastructure (that's cns-bridge), other agents (that's their adapters)

## Development Setup

```bash
git clone https://github.com/casey-digennaro/wesley-cns-adapter.git
cd wesley-cns-adapter
pip install -e ".[dev]"
pytest
```

## Running Tests

```bash
pytest                    # all tests
pytest tests/test_speaker.py  # one file
pytest -k "test_broadcast"  # by name pattern
pytest -v                 # verbose
```

## Code Style

- Python 3.9+ (use `from __future__ import annotations`)
- Type hints everywhere
- Dataclasses for structured data
- Docstrings on public functions and classes
- No external dependencies beyond `requests` (keep it lean for Wesley)

## Adding Features

If you add a new intent mapping, response type, or signal handling:

1. Add the logic in `translator.py`
2. Add tests in `test_translator.py`
3. Update the README if the user-facing API changed
4. Add a CHANGELOG entry

## Filing Issues

- **Bugs:** Include the packet JSON that caused the problem
- **Features:** Explain which CNS signal pattern you want Wesley to handle
- **Questions:** The CNS bus is weird — ask freely
