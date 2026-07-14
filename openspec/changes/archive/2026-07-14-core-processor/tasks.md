# Tasks: Core Processor

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~256 (8 files, all new) |
| 400-line budget risk | Low |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation → PR 2: Core Logic → PR 3: CLI+TUI → PR 4: Integration |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation — models, platform, package | PR 1 | Base: main (~96 lines) |
| 2 | Core logic — scanner, matcher, processor | PR 2 | Depends on PR 1 models (~75 lines) |
| 3 | CLI + TUI — argparse, output formatting | PR 3 | Depends on PR 2 (`core.process_file`) (~75 lines) |
| 4 | Integration — `__main__.py`, wiring | PR 4 | Depends on PR 3 (`cli.main`) (~10 lines) |

## Phase 1: Foundation — models, platform, package

- [x] 1.1 Create `takeout_metadata_writer/__init__.py` — empty package marker
- [x] 1.2 Create `models.py` — `MediaFile` and `ProcessResult` dataclasses with `path`, `json_path`, `photo_taken_time`, `creation_time`, `current_stat`, `action`, `reason`
- [x] 1.3 Create `platform.py` — `set_file_times()`: ctypes + `SetFileTime` for Windows creation time, `os.utime` for mtime on all platforms; per-call error handling
- [x] 1.4 Create `pyproject.toml` — package metadata, Python 3.10+, zero external deps

## Phase 2: Core Logic — scanner, matcher, processor

- [x] 2.1 Create `core.py` — `scan_directory(path)` generator yielding `Path` objects matching media extensions via `rglob`
- [x] 2.2 Implement `match_json(media_path)` — companion lookup: `{stem}.{ext}.supplemental-metadata.json`
- [x] 2.3 Implement `read_metadata(json_path)` — parse `photoTakenTime.timestamp` and `creationTime.timestamp` as ints; catch `KeyError`/`json.JSONDecodeError`
- [x] 2.4 Implement `process_file(media_path, dry_run=True)` — orchestrate: match → read metadata → write via `platform.set_file_times()`; return `ProcessResult`; isolate per-file errors
- [x] 2.5 Implement `summarize(results)` — return `(updated, skipped, errors)` counts

## Phase 3: CLI + TUI — argparse, output formatting

- [x] 3.1 Create `tui.py` — `print_dry_run_table(results)`: formatted table with file name, current timestamps, target timestamps
- [x] 3.2 Implement `print_summary(updated, skipped, errors)` — end-of-run totals output
- [x] 3.3 Create `cli.py` — argparse: positional `path` argument, `--dry-run` flag; `main()` function wiring path → `scan_directory` → `process_file` → `print_dry_run_table`/`print_summary`

## Phase 4: Integration — entry point, wiring

- [x] 4.1 Create `__main__.py` — `from takeout_metadata_writer.cli import main; main()`
- [x] 4.2 Wire imports across modules and verify `python -m takeout_metadata_writer <path>` runs end-to-end
