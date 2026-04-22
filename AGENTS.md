# AGENTS.md — unicorn_linker

## Overview

Python library for emulating ARM64 native libraries using Unicorn CPU emulator.
Loads shared libraries (.so files), applies relocations, and calls functions.

## Commands

| Command | Description |
|---------|------------|
| `pytest` | Run test suite |
| `ruff format` | Format code |
| `ruff check` | Lint code |
| `mypy src/` | Type check |

## Development

```bash
pip install -e ".[test]"

pytest

ruff check src/ tests/
ruff format src/ tests/

mypy src/
```

## Testing

Uses pytest with pytest-cov for coverage. Run tests with:
```bash
pytest --cov=src --cov-report=html
```

## Code Style

- Format: ruff
- Lint: ruff + mypy
- Docstrings: Google style

## Release

```bash
bumpversion patch
git tag v<version>
git push && git push --tags
```