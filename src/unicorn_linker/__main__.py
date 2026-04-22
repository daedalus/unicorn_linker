import sys

from unicorn_linker import load as load_lib


def main() -> int:
    """CLI entry point for unicorn-linker."""
    if len(sys.argv) < 2:
        print("Usage: unicorn-linker <library.so>")
        return 1

    lib = load_lib(sys.argv[1])

    print("\nFirst 20 functions:")
    for i, (name, addr) in enumerate(list(lib.functions.items())[:20]):
        print(f"  {name}: 0x{addr:x}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
