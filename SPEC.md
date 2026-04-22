# SPEC.md — unicorn_linker

## Purpose

A Python library that emulates ARM64 native libraries using the Unicorn CPU emulator. It provides functionality to load shared libraries (.so files), apply relocations, and call functions within the emulated environment. Includes JNI (Java Native Interface) support for interacting with Android-style native libraries.

## Scope

### What IS in Scope

- ARM64 emulation using Unicorn engine
- Loading shared libraries (.so files) into emulated memory
- Applying relocations (RELATIVE, JUMP_SLOT, GLOBAL, ABS)
- Calling functions with up to 4 arguments
- Memory management (input/output buffers, JNI heap)
- Function discovery using readelf
- JNI entry point management
- CLI entry point for translating text

### What is NOT in Scope

- x86 or other architectures (ARM64 only)
- Shared library linking/compilation
- Debugging or interactive debugging
- Multi-threading support
- Network or filesystem operations inside emulator

## Public API / Interface

### `unicorn_linker.Linker`

```python
class Linker:
    def __init__(self) -> None:
        """Initialize ARM64 emulator with default memory regions."""
```

**Memory Layout:**
- Zero page: 0x0 - 0x100000
- JNI heap: 0x400000 - 0x500000
- Library: 0x10000000 - 0x21000000
- Stubs: 0x20000000 - 0x20400000
- Input buffer: 0x600000 - 0x700000
- Output buffer: 0x700000 - 0x800000

```python
    def load_library(self, path: str) -> int:
        """Load .so file into memory.
        
        Args:
            path: Path to shared library (.so) file.
        
        Returns:
            Number of bytes loaded.
        
        Raises:
            FileNotFoundError: If library file does not exist.
            PermissionError: If file cannot be read.
        """
```

```python
    def apply_relocations(self, path: str) -> Tuple[int, int]:
        """Apply relocations from readelf output.
        
        Args:
            path: Path to shared library file.
        
        Returns:
            Tuple of (relative_relocations_count, function_relocations_count).
        
        Raises:
            RuntimeError: If readelf fails.
        """
```

```python
    def get_functions(self, path: str) -> Dict[str, int]:
        """Get exported functions from library using readelf.
        
        Args:
            path: Path to shared library (.so) file.
        
        Returns:
            Dictionary mapping function names to their addresses.
        
        Raises:
            RuntimeError: If readelf fails.
        """
```

```python
    def call(self, offset: int, *args, timeout: int = 100000) -> int:
        """Call function at offset with arguments.
        
        Args:
            offset: Function offset within loaded library.
            *args: Up to 4 integer arguments (passed in X0-X3).
            timeout: Emulation timeout in microseconds (default: 100000).
        
        Returns:
            Return value from X0 register.
        
        Raises:
            UcError: If emulation fails.
        """
```

```python
    def set_input(self, text: str) -> int:
        """Set input buffer with text.
        
        Args:
            text: String to write to input buffer.
        
        Returns:
            Address of input buffer.
        """
```

```python
    def get_output(self, size: int = 0x1000) -> bytes:
        """Read output buffer.
        
        Args:
            size: Number of bytes to read (default: 0x1000).
        
        Returns:
            Output buffer contents.
        """
```

```python
    def set_jni_entry(self, index: int, value: int):
        """Set JNI function pointer.
        
        Args:
            index: JNI entry index.
            value: Function address to set.
        """
```

```python
    def patch(self, offset: int, code: bytes = b"\xC0\x03\x5F\xD6"):
        """Patch memory with code.
        
        Args:
            offset: Offset within library memory.
            code: Machine code to write.
        """
```

```python
    def clear_heap(self):
        """Clear JNI heap memory."""
```

```python
    def find_function_by_prefix(self, path: str, prefix: str) -> Optional[int]:
        """Find function by name prefix.
        
        Args:
            path: Path to shared library.
            prefix: Function name prefix to search for.
        
        Returns:
            Function address if found, None otherwise.
        """
```

### `unicorn_linker.Library`

```python
class Library:
    def __init__(self, path: str):
        """Load library and apply relocations.
        
        Args:
            path: Path to shared library (.so) file.
        
        Raises:
            FileNotFoundError: If library does not exist.
        """
```

```python
    def __call__(self, offset: int, *args) -> int:
        """Shortcut to call function.
        
        Args:
            offset: Function offset.
            *args: Arguments to pass.
        
        Returns:
            Return value from function.
        """
```

### Module Functions

```python
def load(path: str) -> Library:
    """Load a shared library.
    
    Args:
        path: Path to .so file.
    
    Returns:
        Library instance.
    """
```

### Module Attributes

```python
__version__: str = "0.1.0"
```

### CLI Entry Point

```bash
unicorn-linker --help
unicorn-linker <library.so>
```

## Edge Cases

1. **Empty library** - Loading a library with no functions should succeed
2. **Missing relocations** - Library with no relocations should load without error
3. **Function name starting with underscore** - Skip functions like `_init` 
4. **Very long function names** - Handle function names > 64 characters
5. **Invalid memory access** - Catch and handle Unicorn memory errors
6. **Timeout during emulation** - Long-running functions should timeout
7. **Empty input string** - set_input with empty string should work
8. **Non-UTF8 output** - Handle binary output with replacement characters
9. **Missing readelf** - Handle case where readelf is not installed
10. **Corrupted library file** - Handle read errors gracefully

## Performance & Constraints

- Single-threaded emulation only
- Maximum library size: 32 MB (0x2000000 bytes)
- Maximum timeout: 10 seconds (10000000 microseconds)
- Pure Python with unicorn dependency (no other external deps)