# Proposal: Core Processor — Google Takeout Metadata Writer

## Intent

Google Takeout exports strip original file timestamps. Companion `supplemental-metadata.json` files contain `photoTakenTime` (real capture date) and `creationTime` (upload date). This change builds the core processor that scans directories, matches JSON metadata to media files, and restores timestamps — the foundation for all future features.

## Scope

### In Scope
1. Recursive directory scanner for media files (common photo/video extensions)
2. JSON companion matching via `{file}.{ext}.supplemental-metadata.json` pattern
3. Parse `photoTakenTime` and `creationTime` from JSON metadata
4. Read current file timestamps via `os.stat`
5. Dry-run mode: table summary of file name, current timestamps, target timestamps
6. Write mode: creation time = `photoTakenTime`, modification time = `creationTime`
7. Cross-platform timestamp setting: ctypes + `SetFileTime` on Windows, `os.utime` on Unix
8. Basic CLI with `argparse` (`--dry-run` flag, path argument)
9. Python package structure: `takeout_metadata_writer/`

### Out of Scope
- Rich TUI with progress bars, interactive selection (PR 2)
- EXIF metadata reading/writing
- Additional file format support beyond basic media types
- Test suite (no test runner installed yet)

## Capabilities

### New Capabilities
- `core-processor`: Recursive media file scanning, JSON metadata matching and parsing, timestamp restoration with dry-run and write modes, cross-platform via std-lib only

### Modified Capabilities
None — initial capability.

## Approach

Pure std-lib Python with ctypes for Windows timestamp handling. Module split: `core.py` (generator-based scanning, matching, processing), `platform.py` (cross-platform `set_file_times`), `models.py` (`MediaFile`, `ProcessResult` dataclasses), `tui.py` (formatted dry-run tables, write output), `cli.py` (argparse entry point). Each file processed individually; errors caught per-file without aborting. Generator pattern avoids memory issues on large datasets.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `takeout_metadata_writer/` | New | Package root with `__init__.py`, `__main__.py` |
| `takeout_metadata_writer/core.py` | New | Scan, match, process, summarize |
| `takeout_metadata_writer/platform.py` | New | `set_file_times()` — Windows ctypes, Unix os.utime |
| `takeout_metadata_writer/models.py` | New | `MediaFile`, `ProcessResult` dataclasses |
| `takeout_metadata_writer/tui.py` | New | Dry-run table, write-mode output formatting |
| `takeout_metadata_writer/cli.py` | New | `argparse` setup and main entry |
| `pyproject.toml` | New | Package metadata (zero external deps) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Windows `SetFileTime` fails on some FS | Low | Per-file error handling, fallback to mtime-only |
| Permission errors on read-only files | Med | Catch `PermissionError`, log, continue |
| Malformed JSON (missing keys, bad types) | Med | Defensive parsing with `KeyError`/`TypeError` handling |
| Unicode filenames | Low | `pathlib` handles natively |
| Large datasets (10k+ files) | Low | Generator-based, no memory accumulation |

## Rollback Plan

No destructive operations — only timestamp metadata changes. Dry-run previews all writes. Content is never modified; re-exporting from Takeout restores original timestamps. No backup needed.

## Dependencies

- Python 3.10+ (stdlib only: `pathlib`, `json`, `datetime`, `os`, `stat`, `argparse`, `ctypes`, `sys`)
- No external packages

## Success Criteria

- [ ] CLI accepts path and `--dry-run` flag; `--help` displays usage
- [ ] Dry-run scans a Takeout directory and prints table of matched files with current vs target timestamps
- [ ] Write mode sets modification time to `creationTime` on all platforms
- [ ] Write mode sets creation time to `photoTakenTime` on Windows
- [ ] Write mode logs warning (skips creation time) on Unix
- [ ] Invalid/missing JSON produces per-file warnings without aborting
- [ ] Total diff stays under 200-line budget
