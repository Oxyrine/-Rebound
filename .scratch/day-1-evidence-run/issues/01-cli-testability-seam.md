# 01: CLI Testability Seam

**What to build:** The ability to unit test `run_batch.py` by refactoring `main()` to accept an optional argument list (`def main(argv=None): ... parser.parse_args(argv)`), removing the need for `sys.argv` monkeypatching. This provides the test seam for the CLI flag logic.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Modify `run_batch.main` to accept `argv=None` and pass it to `parser.parse_args()`.
- [x] Ensure the script's entry point (`if __name__ == "__main__":`) calls `main()` without arguments.
- [x] Write a basic unit test that calls `main(["--interpreter=llm", "--execute-links"])` directly (which may fail if audit path logic is missing, but proves the seam works without `sys.argv`).

## Answer
Refactored `main` to accept `argv` and created `tests/test_run_batch.py` to verify the seam.
