# unicorn-linker

ARM64 native library emulator using Unicorn CPU emulator.

[![PyPI](https://img.shields.io/pypi/v/unicorn-linker.svg)](https://pypi.org/project/unicorn-linker/)
[![Python](https://img.shields.io/pypi/pyversions/unicorn-linker.svg)](https://pypi.org/project/unicorn-linker/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Install

```bash
pip install unicorn-linker
```

## Usage

```python
from unicorn_linker import load

lib = load("mylibrary.so")

lib.linker.set_input("Hello World")
lib.linker.call(0x1000, lib.linker.jni_addr, 0x600000, 0x700000, 0x1000)

result = lib.linker.get_output().rstrip(b"\x00").decode("utf-8")
print(result)
```

## CLI

```bash
unicorn-linker mylibrary.so
```

## API

### Linker

ARM64 native library emulator.

```python
class Linker:
    def __init__(self) -> None:
        """Initialize ARM64 emulator."""
```

### Library

Loaded library wrapper.

```python
class Library:
    def __init__(self, path: str) -> None:
        """Load library and apply relocations."""
```

### load()

Load a shared library.

```python
def load(path: str) -> Library:
    """Load a shared library."""
```

## Development

```bash
git clone https://github.com/daedalus/unicorn_linker.git
cd unicorn_linker
pip install -e ".[test]"

# run tests
pytest

# format
ruff format src/ tests/

# lint
ruff check src/ tests/

# type check
mypy src/
```