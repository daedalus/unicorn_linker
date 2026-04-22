from pathlib import Path

import pytest

from unicorn_linker import Library, Linker, load


@pytest.fixture
def mock_library(tmp_path: Path) -> Path:
    """Create a minimal mock ARM64 library for testing."""
    return tmp_path / "mock_lib.so"


@pytest.fixture
def linker() -> Linker:
    """Create a Linker instance."""
    return Linker()


class TestLinkerInit:
    """Tests for Linker initialization."""

    def test_linker_initializes(self, linker: Linker) -> None:
        """Test that Linker initializes correctly."""
        assert linker.lib_addr == Linker.LIB_ADDR
        assert linker.jni_addr == Linker.JNI_ADDR
        assert linker.stubs_addr == Linker.STUBS_ADDR
        assert linker.input_addr == Linker.INPUT_ADDR
        assert linker.output_addr == Linker.OUTPUT_ADDR

    def test_linker_has_unicorn_instance(self, linker: Linker) -> None:
        """Test that Linker has a Unicorn instance."""
        assert linker.mu is not None

    def test_linker_symbols_start_empty(self, linker: Linker) -> None:
        """Test that symbols dictionary starts empty."""
        assert linker.symbols == {}


class TestLinkerMemoryAllocation:
    """Tests for memory allocation."""

    def test_alloc_memory(self, linker: Linker) -> None:
        """Test memory regions are allocated."""
        assert linker.mu is not None


class TestLinkerLoadLibrary:
    """Tests for load_library method."""

    def test_load_library_nonexistent_file(self, linker: Linker) -> None:
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            linker.load_library("/nonexistent/path/lib.so")

    def test_load_library_success(self, linker: Linker, tmp_path: Path) -> None:
        """Test loading library succeeds."""
        lib_path = tmp_path / "test.so"
        lib_path.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 100)
        size = linker.load_library(str(lib_path))
        assert size > 100


class TestLinkerGetFunctions:
    """Tests for get_functions method."""

    def test_get_functions_nonexistent_file(self, linker: Linker) -> None:
        """Test get_functions on non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            linker.get_functions("/nonexistent/path/lib.so")


class TestLinkerApplyRelocations:
    """Tests for apply_relocations method."""

    def test_apply_relocations_nonexistent_file(self, linker: Linker) -> None:
        """Test apply_relocations on non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            linker.apply_relocations("/nonexistent/path/lib.so")


class TestLinkerCall:
    """Tests for call method."""

    def test_call_with_no_args(self, linker: Linker) -> None:
        """Test call with no arguments."""
        result = linker.call(0, timeout=1000)
        assert isinstance(result, int)


class TestLinkerSetInput:
    """Tests for set_input method."""

    def test_set_input_empty_string(self, linker: Linker) -> None:
        """Test set_input with empty string."""
        addr = linker.set_input("")
        assert addr == linker.input_addr

    def test_set_input_normal_string(self, linker: Linker) -> None:
        """Test set_input with normal string."""
        addr = linker.set_input("hello")
        assert addr == linker.input_addr


class TestLinkerGetOutput:
    """Tests for get_output method."""

    def test_get_output_default_size(self, linker: Linker) -> None:
        """Test get_output with default size."""
        output = linker.get_output()
        assert isinstance(output, (bytes, bytearray))

    def test_get_output_custom_size(self, linker: Linker) -> None:
        """Test get_output with custom size."""
        output = linker.get_output(size=100)
        assert len(output) == 100


class TestLinkerSetJniEntry:
    """Tests for set_jni_entry method."""

    def test_set_jni_entry(self, linker: Linker) -> None:
        """Test set_jni_entry."""
        linker.set_jni_entry(0, 0x10000000)
        linker.set_jni_entry(1, 0x20000000)


class TestLinkerPatch:
    """Tests for patch method."""

    def test_patch_default_code(self, linker: Linker) -> None:
        """Test patch with default code."""
        linker.patch(0, b"\xc0\x03\x5f\xd6")


class TestLinkerClearHeap:
    """Tests for clear_heap method."""

    def test_clear_heap(self, linker: Linker) -> None:
        """Test clear_heap."""
        linker.clear_heap()


class TestLinkerFindFunctionByPrefix:
    """Tests for find_function_by_prefix method."""

    def test_find_function_by_prefix_not_found(self, linker: Linker) -> None:
        """Test find_function_by_prefix raises error for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            linker.find_function_by_prefix("/nonexistent.so", "NonExistent")


class TestLibrary:
    """Tests for Library class."""

    def test_library_init_nonexistent_file(self) -> None:
        """Test Library with non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Library("/nonexistent/path/lib.so")


class TestLoad:
    """Tests for load function."""

    def test_load_nonexistent_file(self) -> None:
        """Test load with non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load("/nonexistent/path/lib.so")


class TestVersion:
    """Tests for version attribute."""

    def test_version_exists(self) -> None:
        """Test __version__ exists."""
        from unicorn_linker import __version__

        assert __version__ == "0.1.0"


class TestExports:
    """Tests for module exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from unicorn_linker import __all__

        assert "Linker" in __all__
        assert "Library" in __all__
        assert "load" in __all__
        assert "__version__" in __all__
