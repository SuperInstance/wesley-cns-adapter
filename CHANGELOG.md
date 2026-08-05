# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Speaker now increments sequence IDs instead of always writing `_001.json`
- Translator `response_to_uscp` now correctly passes agent_id into payload
  instead of hardcoding `"wesley"` as the agent name
- Translator now accepts a `model` parameter so the response packet records
  the actual model used (was hardcoded to `"granite"`)

### Added
- Full test suite: `test_translator.py`, `test_listener.py`, `test_speaker.py`
- Example scripts: `examples/handshake_response.py`, `examples/query_wesley.py`
- This CHANGELOG.md
- CONTRIBUTING.md

## [0.1.0] - 2026-08-04

### Added
- Initial release
- Listener polls CNS outbox for USCP signals addressed to Wesley
- Translator converts USCP ↔ Ollama chat messages
- Speaker writes response packets to CNS inbox with atomic writes
- CLI entry point (`wesley-cns`) with watch mode, dry-run, and options
