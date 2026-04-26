import struct
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from unicorn_linker import Library, Linker, load


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

    def test_linker_repr(self, linker: Linker) -> None:
        """Test Linker __repr__ contains expected fields."""
        r = repr(linker)
        assert "Linker(" in r
        assert "lib_addr=" in r
        assert "jni_addr=" in r
        assert "symbols=" in r


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
        """Test loading library succeeds and data is written to memory."""
        payload = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 100
        lib_path = tmp_path / "test.so"
        lib_path.write_bytes(payload)
        size = linker.load_library(str(lib_path))
        assert size == len(payload)
        mem = bytes(linker.mu.mem_read(linker.lib_addr, len(payload)))
        assert mem == payload

    def test_load_library_too_large(self, linker: Linker, tmp_path: Path) -> None:
        """Test that loading a library exceeding 32 MB raises ValueError."""
        lib_path = tmp_path / "big.so"
        lib_path.write_bytes(b"\x00" * (Linker.MAX_LIB_SIZE + 1))
        with pytest.raises(ValueError, match="Library too large"):
            linker.load_library(str(lib_path))


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

    def test_apply_relocations_resets_stub_idx(
        self, linker: Linker, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Test that apply_relocations resets stub_idx on each call."""
        lib_path = tmp_path / "test.so"
        lib_path.write_bytes(b"\x00" * 8)
        mocker.patch(
            "subprocess.run",
            return_value=mocker.Mock(returncode=0, stdout="", stderr=""),
        )
        linker.stub_idx = 5
        linker.apply_relocations(str(lib_path))
        assert linker.stub_idx == 0


class TestLinkerCall:
    """Tests for call method."""

    def test_call_with_no_args(self, linker: Linker) -> None:
        """Test call with no arguments."""
        result = linker.call(0, timeout=1000)
        assert isinstance(result, int)

    def test_call_custom_timeout(self, linker: Linker) -> None:
        """Test call with a custom timeout value."""
        result = linker.call(0, timeout=500)
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

    def test_set_input_data_written(self, linker: Linker) -> None:
        """Test that set_input writes the encoded string to memory."""
        linker.set_input("hi")
        mem = bytes(linker.mu.mem_read(linker.input_addr, 3))
        assert mem == b"hi\x00"

    def test_set_input_too_large(self, linker: Linker) -> None:
        """Test that set_input raises ValueError when input exceeds buffer."""
        with pytest.raises(ValueError, match="Input too large"):
            linker.set_input("x" * Linker.MAX_INPUT_SIZE)


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

    def test_set_jni_entry_readback(self, linker: Linker) -> None:
        """Test that set_jni_entry writes the correct value to memory."""
        linker.set_jni_entry(0, 0xDEADBEEF)
        raw = bytes(linker.mu.mem_read(linker.jni_addr, 8))
        assert struct.unpack("<Q", raw)[0] == 0xDEADBEEF

    def test_set_jni_entry_index_offset(self, linker: Linker) -> None:
        """Test that set_jni_entry at index 2 writes at offset 16."""
        linker.set_jni_entry(2, 0xCAFEBABE)
        raw = bytes(linker.mu.mem_read(linker.jni_addr + 2 * 8, 8))
        assert struct.unpack("<Q", raw)[0] == 0xCAFEBABE


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

    def test_find_function_by_prefix_found(
        self, linker: Linker, mocker: MockerFixture
    ) -> None:
        """Test find_function_by_prefix returns address when prefix matches."""
        mocker.patch.object(
            linker,
            "get_functions",
            return_value={"myFunc": 0x1234, "otherFunc": 0x5678},
        )
        addr = linker.find_function_by_prefix("dummy.so", "myF")
        assert addr == 0x1234

    def test_find_function_by_prefix_no_match(
        self, linker: Linker, mocker: MockerFixture
    ) -> None:
        """Test find_function_by_prefix returns None when no prefix matches."""
        mocker.patch.object(
            linker,
            "get_functions",
            return_value={"myFunc": 0x1234},
        )
        result = linker.find_function_by_prefix("dummy.so", "xyz")
        assert result is None


class TestLibrary:
    """Tests for Library class."""

    def test_library_init_nonexistent_file(self) -> None:
        """Test Library with non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Library("/nonexistent/path/lib.so")

    def test_library_call_passes_timeout(self, mocker: MockerFixture) -> None:
        """Test that Library.__call__ forwards timeout to Linker.call."""
        lib = mocker.MagicMock(spec=Library)
        lib.linker = mocker.MagicMock()
        lib.linker.call.return_value = 42
        Library.__call__(lib, 0x100, 1, 2, timeout=9999)
        lib.linker.call.assert_called_once_with(0x100, 1, 2, timeout=9999)


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
