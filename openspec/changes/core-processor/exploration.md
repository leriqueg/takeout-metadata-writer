## Exploration: Core Takeout Metadata Processor + TUI

### Current State
Greenfield project — no code exists. SDD initialized with hybrid persistence (OpenSpec + Engram), chained PRs with stacked-to-main, 200-line review budget. Strict TDD disabled. Python 3.14.4 available locally; target is 3.10+.

The README and research.md define the problem clearly: Google Takeout exports strip original file timestamps. Companion `supplemental-metadata.json` files contain `photoTakenTime` (real capture date) and `creationTime` (upload date). The tool must scan recursively, match JSON to media files, and restore timestamps.

### Affected Areas
Since no code exists, this maps the *planned* module structure:

- `src/takeout_metadata_writer/` — package root (or single-file module)
- `src/takeout_metadata_writer/__main__.py` — entry point for `python -m`
- `src/takeout_metadata_writer/core.py` — directory scanning, JSON matching, timestamp logic
- `src/takeout_metadata_writer/platform.py` — platform-specific timestamp handling (ctypes for Windows)
- `src/takeout_metadata_writer/tui.py` — terminal output (argparse + formatted display)
- `pyproject.toml` or `setup.cfg` — packaging metadata
- Any file matching `.supplemental-metadata.json` — the data source

### Approaches

#### 1. Pure std-lib + ctypes (recommended)
Core processing via `pathlib`, `json`, `datetime`, `os.utime`. Windows creation time via `ctypes.windll.kernel32.SetFileTime` (zero external deps). CLI via `argparse`. Output via formatted `print()` with aligned columns.

- **Pros**: Zero external dependencies. `ctypes` is std-lib. Full control. Maximum portability. Smallest install footprint.
- **Cons**: More boilerplate for CLI ergonomics. No progress bars without rich. Windows `SetFileTime` via ctypes is low-level (handle management, FILETIME conversion, error handling).
- **Effort**: Medium

#### 2. Rich-enhanced CLI
Same core as approach 1, but add `rich` as the sole dependency for tables, progress bars, panels, and colored output.

- **Pros**: Beautiful output with ~50 lines of code. Built-in progress bar for large scans. Table rendering for dry-run summaries. Markdown support for help text.
- **Cons**: One external dependency (though `rich` is pure Python, well-maintained). Adds ~3MB to install. Slightly more complex packaging.
- **Effort**: Low-Medium

#### 3. Textual TUI
Full interactive terminal app using `textual` (builds on `rich`). Interactive file browser, live-updating progress, keyboard navigation.

- **Pros**: Impressive interactive UI. Real-time progress updates. Keyboard-navigable file lists.
- **Cons**: Multiple transitive deps (`textual` + `rich` + `markdown-it-py` + `platformdirs` + ...). Overkill for a tool that primarily runs as a batch process. Harder to test. Windows compatibility requires `textual` v0.41+.
- **Effort**: High

#### 4. Click + Rich
Use `click` for CLI argument handling (instead of `argparse`) and `rich` for output formatting.

- **Pros**: Cleaner CLI definition (nested commands, automatic help, validation). `click` is the de-facto standard for Python CLIs.
- **Cons**: Two external deps. `click` adds ~500KB. `argparse` does the job well enough for a single-command tool.
- **Effort**: Low-Medium

### Recommendation

**Go with Approach 1: pure std-lib + ctypes** for the initial implementation.

Rationale:
1. **Zero external dependencies** is a real advantage for a utility tool — install with `pip install takeout-metadata-writer` and it Just Works everywhere.
2. **Windows creation time** is the only hard part: `os.utime` cannot set `st_birthtime`. The `ctypes` approach (`kernel32.SetFileTime`) is well-documented, uses only std-lib, and is the standard solution for this problem. The code is ~30 lines and easily tested.
3. **Cross-platform fallback**: On macOS/Linux, skip creation time (no standard way to set it) and only set `mtime` via `os.utime`. This is honest and functional.
4. **CLI simplicity**: `argparse` with a few flags (`--dry-run`, `--verbose`, path argument) is all this tool needs. The user isn't asking for an interactive TUI loop — they want a clear summary before writing.
5. **Progress indication**: Can be done with simple `print()` and carriage returns (`\r`) for scan progress without any deps.
6. **200-line PR constraint**: With the module split, each piece fits comfortably. Pure std-lib keeps the code dense and focused.

Only add `rich` later if the user explicitly asks for prettier output. Don't add it preemptively.

### Architecture

```
takeout_metadata_writer/
├── __init__.py
├── __main__.py          # if __name__ == "__main__": cli()
├── core.py              # scan, match, process, summarize
├── platform.py          # set_file_times() — ctypes on Windows, os.utime elsewhere
├── tui.py               # format_output(), dry_run_report()
├── cli.py               # argparse setup, main entry
└── models.py            # dataclasses: MediaFile, JsonMetadata
```

Key design decisions:
- **`core.py`**: Generator-based scanning (`yield` media files as found) to avoid loading everything into memory. Pure functions: `scan_directory()`, `match_json()`, `read_metadata()`, `resolve_timestamps()`.
- **`platform.py`**: Single `set_file_times(path, creation_time, modification_time)` function. On Windows, uses `ctypes` + `kernel32.SetFileTime`. On other platforms, uses `os.utime` (mtime only) and logs a warning about creation time.
- **`models.py`**: `@dataclass` for `MediaFile` (path, json_path, photo_taken_time, creation_time, current_stat) and `ProcessResult` (file, action: skip|update, reason).
- **TUI**: Functions return structured data; `tui.py` formats it. Dry-run: aligned table with columns (File | Current Created | New Created | Current Modified | New Modified). Write mode: summary line count + progress dots.
- **Safety**: Each file processed individually; on `OSError` or `KeyError`, log and continue. Atomic writes are not needed (we're only modifying timestamps, not file contents).

### Windows Timestamp Strategy (Detail)

`os.utime()` sets `atime`/`mtime` only. On Windows, `st_birthtime` (creation time) requires Win32 API:
1. `kernel32.CreateFileW(path, FILE_WRITE_ATTRIBUTES, ...)` → get handle
2. Build `FILETIME` struct from `photoTakenTime` (100-ns intervals since 1601-01-01 UTC)
3. `kernel32.SetFileTime(handle, lpCreationTime, NULL, lpLastWriteTime)` → set both creation and modification
4. `kernel32.CloseHandle(handle)`

`ctypes` is std-lib, available on all CPython builds. Guard with `if sys.platform == "win32"`.

### Risks

- **Windows creation time mutation**: Some filesystems (FAT32, exFAT, network drives) may not support changing creation time. The `SetFileTime` call will fail silently or with an error — need graceful fallback to just mtime.
- **Permission errors**: The tool needs write access to file timestamps. On read-only files or system directories, this will fail. Must handle `PermissionError` per-file and continue.
- **JSON malformation**: `supplemental-metadata.json` files might have missing keys, wrong types, or be from different Takeout versions. Every JSON read must handle `KeyError`, `ValueError`, `json.JSONDecodeError`.
- **Timestamp range**: Some Takeout photos might have timestamps outside valid `datetime` range. Need bounds checking before calling `SetFileTime` (FILETIME uses 1601-01-01 epoch, negative values are invalid).
- **Non-ASCII filenames**: Takeout exports may contain Unicode characters from multiple languages. `pathlib` handles this, but ensure all file operations use Unicode-aware APIs (which Python 3 does by default).
- **Large datasets**: 10,000+ files. Generator pattern avoids memory issues. Progress indication becomes important for UX.
- **False JSON matches**: Files named `foo.mp4.supplemental-metadata.json` might exist without a corresponding `foo.mp4`. Need to handle orphans gracefully.

### Ready for Proposal
**Yes**. The problem is well-understood, the domain is narrow, and the recommended approach is clear. The orchestrator should proceed to `sdd-propose` for a change named `core-processor` with the pure-stdlib approach.

Key items for proposal phase:
1. Confirm change name: `core-processor`
2. Decide single change or break into two (core + TUI) — I recommend one change (200 lines is tight but doable with module split)
3. Confirm Python minimum version (3.10+ vs 3.12+ for `st_birthtime` reading)
4. Confirm Windows-first vs cross-platform priority
