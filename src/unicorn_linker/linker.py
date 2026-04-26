import logging
import os
import struct
import subprocess

from unicorn import UC_ARCH_ARM64, UC_MODE_ARM, Uc, UcError
from unicorn.arm64_const import (
    UC_ARM64_REG_SP,
    UC_ARM64_REG_X0,
)

logger = logging.getLogger(__name__)


class Linker:
    """ARM64 native library emulator.

    Provides functionality to load shared libraries (.so files), apply relocations,
    and call functions within an emulated ARM64 environment.
    """

    LIB_ADDR: int = 0x10000000
    JNI_ADDR: int = 0x400000
    STUBS_ADDR: int = 0x20000000
    INPUT_ADDR: int = 0x600000
    OUTPUT_ADDR: int = 0x700000
    ZERO_PAGE_ADDR: int = 0x0
    MAX_LIB_SIZE: int = 0x2000000  # 32 MB
    MAX_INPUT_SIZE: int = 0x100000  # 1 MB

    def __init__(self) -> None:
        """Initialize ARM64 emulator with default memory regions."""
        self.lib_addr = self.LIB_ADDR
        self.jni_addr = self.JNI_ADDR
        self.stubs_addr = self.STUBS_ADDR
        self.input_addr = self.INPUT_ADDR
        self.output_addr = self.OUTPUT_ADDR

        self.mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self._alloc_memory()

        self.symbols: dict[str, int] = {}
        self.stub_idx = 0

    def __repr__(self) -> str:
        """Return string representation of Linker."""
        return (
            f"Linker(lib_addr=0x{self.lib_addr:x}, jni_addr=0x{self.jni_addr:x}, "
            f"symbols={len(self.symbols)})"
        )

    def _alloc_memory(self) -> None:
        """Allocate memory for emulated regions."""
        self.mu.mem_map(self.ZERO_PAGE_ADDR, 0x100000)
        self.mu.mem_write(self.ZERO_PAGE_ADDR, b"\x70\x00\x00\x14")
        self.mu.reg_write(UC_ARM64_REG_SP, 0x100000 - 0x100)

        self.mu.mem_map(self.jni_addr, 0x100000)
        self.mu.mem_map(self.lib_addr, 0x2000000)
        self.mu.mem_map(self.stubs_addr, 0x400000)
        self.mu.mem_map(self.input_addr, 0x100000)
        self.mu.mem_map(self.output_addr, 0x100000)

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
        if not os.path.exists(path):
            raise FileNotFoundError(f"Library not found: {path}")

        with open(path, "rb") as f:
            data = f.read()

        if len(data) > self.MAX_LIB_SIZE:
            raise ValueError(
                f"Library too large: {len(data)} bytes (max {self.MAX_LIB_SIZE})"
            )

        self.mu.mem_write(self.lib_addr, data)
        return len(data)

    def get_functions(self, path: str) -> dict[str, int]:
        """Get exported functions from library using readelf.

        Args:
            path: Path to shared library (.so) file.

        Returns:
            Dictionary mapping function names to their addresses.

        Raises:
            RuntimeError: If readelf fails.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Library not found: {path}")

        result = subprocess.run(
            ["readelf", "-s", path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"readelf failed: {result.stderr}")

        funcs: dict[str, int] = {}
        for line in result.stdout.splitlines():
            if "FUNC" in line and "UND" not in line:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        addr = int(parts[1], 16)
                        name = parts[-1]
                        if not name.startswith("_") and len(name) > 2:
                            funcs[name] = addr
                    except (ValueError, IndexError):
                        pass

        return funcs

    def apply_relocations(self, path: str) -> tuple[int, int]:
        """Apply relocations from readelf output.

        Args:
            path: Path to shared library file.

        Returns:
            Tuple of (relative_relocations_count, function_relocations_count).

        Raises:
            RuntimeError: If readelf fails.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Library not found: {path}")

        result = subprocess.run(["readelf", "-r", path], capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"readelf failed: {result.stderr}")

        self.symbols = {}
        self.stub_idx = 0

        for line in result.stdout.splitlines():
            if not line.strip() or line.startswith("Relocation"):
                continue
            if (
                "R_AARCH64_JUMP" not in line
                and "R_AARCH64_GLOB" not in line
                and "R_AARCH64_ABS" not in line
            ):
                continue
            parts = line.split()
            if len(parts) >= 5:
                sym = parts[4].split("@")[0]
                if sym and sym not in self.symbols:
                    self.symbols[sym] = self.stub_idx
                    self.stub_idx += 1

        stub_insn = b"\x00\x00\x00\xd2\xc0\x03\x5f\xd6"
        for i in range(self.stub_idx):
            try:
                self.mu.mem_write(self.stubs_addr + i * 0x20, stub_insn)
            except UcError:
                pass

        rel_count = 0
        func_count = 0

        for line in result.stdout.splitlines():
            if not line.strip() or line.startswith("Relocation"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue

            reloc_type = parts[2]
            try:
                offset = int(parts[0], 16)
                target = self.lib_addr + offset
            except (ValueError, IndexError):
                continue

            if "R_AARCH64_RELATIV" in reloc_type and len(parts) >= 4:
                try:
                    value = int(parts[3], 16)
                    self.mu.mem_write(target, struct.pack("<Q", self.lib_addr + value))
                    rel_count += 1
                except (ValueError, UcError):
                    pass
            elif (
                "R_AARCH64_JUMP" in reloc_type
                or "R_AARCH64_GLOB" in reloc_type
                or "R_AARCH64_ABS" in reloc_type
            ) and len(parts) >= 5:
                sym = parts[4].split("@")[0]
                if sym in self.symbols:
                    stub = self.stubs_addr + self.symbols[sym] * 0x20
                    try:
                        self.mu.mem_write(target, struct.pack("<Q", stub))
                        func_count += 1
                    except UcError:
                        pass

        return rel_count, func_count

    def call(self, offset: int, *args: int, timeout: int = 100000) -> int:
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
        fn = self.lib_addr + offset

        for i, arg in enumerate(args[:4]):
            self.mu.reg_write(UC_ARM64_REG_X0 + i, arg)

        for i in range(len(args), 4):
            self.mu.reg_write(UC_ARM64_REG_X0 + i, 0)

        try:
            self.mu.emu_start(fn, 0, timeout=timeout)
        except UcError:
            return 0

        return self.mu.reg_read(UC_ARM64_REG_X0)

    def set_input(self, text: str) -> int:
        """Set input buffer with text.

        Args:
            text: String to write to input buffer.

        Returns:
            Address of input buffer.

        Raises:
            ValueError: If encoded text exceeds input buffer capacity.
        """
        encoded = text.encode() + b"\x00"
        if len(encoded) > self.MAX_INPUT_SIZE:
            raise ValueError(
                f"Input too large: {len(encoded)} bytes (max {self.MAX_INPUT_SIZE})"
            )
        self.mu.mem_write(self.input_addr, encoded)
        return self.input_addr

    def get_output(self, size: int = 0x1000) -> bytes:
        """Read output buffer.

        Args:
            size: Number of bytes to read (default: 0x1000).

        Returns:
            Output buffer contents.
        """
        return self.mu.mem_read(self.output_addr, size)

    def set_jni_entry(self, index: int, value: int) -> None:
        """Set JNI function pointer.

        Args:
            index: JNI entry index.
            value: Function address to set.
        """
        self.mu.mem_write(self.jni_addr + index * 8, struct.pack("<Q", value))

    def patch(self, offset: int, code: bytes = b"\xc0\x03\x5f\xd6") -> None:
        """Patch memory with code.

        Args:
            offset: Offset within library memory.
            code: Machine code to write.
        """
        self.mu.mem_write(self.lib_addr + offset, code)

    def clear_heap(self) -> None:
        """Clear JNI heap memory."""
        self.mu.mem_write(self.jni_addr, bytes(0x100000))

    def find_function_by_prefix(self, path: str, prefix: str) -> int | None:
        """Find function by name prefix.

        Args:
            path: Path to shared library.
            prefix: Function name prefix to search for.

        Returns:
            Function address if found, None otherwise.
        """
        funcs = self.get_functions(path)
        for name, addr in funcs.items():
            if name.startswith(prefix):
                return addr
        return None


class Library:
    """Loaded library wrapper.

    Provides a simplified interface for loading and interacting with
    ARM64 shared libraries.
    """

    def __init__(self, path: str) -> None:
        """Load library and apply relocations.

        Args:
            path: Path to shared library (.so) file.

        Raises:
            FileNotFoundError: If library does not exist.
        """
        self.path = path
        self.linker = Linker()

        size = self.linker.load_library(path)
        logger.info("Loaded: %d bytes", size)

        rels = self.linker.apply_relocations(path)
        logger.info("Relocations: %d RELATIVE + %d FUNC", rels[0], rels[1])

        self.functions = self.linker.get_functions(path)
        logger.info("Functions: %d", len(self.functions))

    def __call__(self, offset: int, *args: int, timeout: int = 100000) -> int:
        """Shortcut to call function.

        Args:
            offset: Function offset.
            *args: Arguments to pass.
            timeout: Emulation timeout in microseconds (default: 100000).

        Returns:
            Return value from function.
        """
        return self.linker.call(offset, *args, timeout=timeout)


def load(path: str) -> Library:
    """Load a shared library.

    Args:
        path: Path to .so file.

    Returns:
        Library instance.
    """
    return Library(path)
