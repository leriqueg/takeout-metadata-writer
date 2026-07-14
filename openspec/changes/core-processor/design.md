# Design: Core Processor — Google Takeout Metadata Writer

## Technical Approach

Pure std-lib Python 3.10+ package implementing recursive media-file scanning, JSON companion matching, and cross-platform timestamp restoration with dry-run preview. Generator-based processing avoids memory accumulation on large datasets. ctypes + `SetFileTime` for Windows creation time; `os.utime` for modification time on all platforms. Per-file error isolation with zero external dependencies. Maps directly to the exploration recommendation and spec requirements.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| **Scanning pattern** | Generator (yield) vs list collect | Generator: O(1) memory, natural one-pass pipeline. List: simple but O(n) memory. | **Generator** — 10k+ file datasets need it. |
| **Windows creation time** | ctypes+SetFileTime vs pywin32 vs skip | ctypes: std-lib but low-level (~30 lines handle/struct mgmt). pywin32: cleaner but external dep. Skip: incomplete on Windows. | **ctypes** — zero-deps mandate, well-documented pattern. |
| **Error isolation** | Per-file try/except vs abort-on-first | Per-file: processes what it can, logs warnings. Abort: simpler but loses partial progress. | **Per-file** — spec requirement, essential for robustness. |
| **Directory walk** | pathlib.rglob vs os.walk | rglob: Pythonic Path objects, unicode-safe. walk: more control but more boilerplate. | **pathlib.rglob** — simplest, handles unicode natively. |
| **Timestamp type** | int (Unix epoch) vs datetime | int: matches JSON input, direct feed to os.utime. datetime: self-documenting but needs epoch conversion. | **int** — JSON already provides Unix timestamps; FILETIME conversion needs epoch math anyway. |
| **Module layout** | Flat (7 files) vs nested package | Flat: all imports top-level, simple to navigate. Nested: scalable but premature for this scope. | **Flat** — 7 files total, no benefit from nesting yet. |

## Data Flow

```
CLI (argparse)
  │ path, --dry-run
  ▼
core.scan_directory(path) ── yields ──► Path objects
  │
  │ for each Path:
  ├── core.match_json() → JSON found?  ─No──► skip (warning logged)
  │                              ─Yes──► read_metadata() → photoTakenTime, creationTime
  │                                       Missing/malformed? → skip (warning)
  │
  ├── os.stat() → current timestamps
  │
  ├── ┌ dry-run? ──► tui.print_comparison_table()    (no writes performed)
  │   └ write?   ──► platform.set_file_times(path, ctime, mtime)
  │                    ├─ Windows: ctypes SetFileTime(creation, modification)
  │                    └─ Unix: os.utime(mtime) + ctime-skip warning
  │
  └── error? ──► log per-file warning, continue to next file

After all files: tui.print_summary(updated, skipped, errors)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `takeout_metadata_writer/__init__.py` | Create | Package marker |
| `takeout_metadata_writer/__main__.py` | Create | `python -m` entry → cli.main() |
| `takeout_metadata_writer/cli.py` | Create | argparse: positional path arg, `--dry-run` flag |
| `takeout_metadata_writer/core.py` | Create | scan_directory(), match_json(), read_metadata(), process_file(), summarize() |
| `takeout_metadata_writer/models.py` | Create | `MediaFile`, `ProcessResult` dataclasses |
| `takeout_metadata_writer/platform.py` | Create | `set_file_times()` — Windows ctypes + Unix os.utime |
| `takeout_metadata_writer/tui.py` | Create | Dry-run comparison table, write-mode summary output |
| `pyproject.toml` | Create | Package metadata, zero external deps, Python 3.10+ |

## Interfaces / Contracts

```python
# models.py — Pure data containers
@dataclass
class MediaFile:
    path: Path
    json_path: Path | None
    photo_taken_time: int | None   # Unix epoch seconds from JSON
    creation_time: int | None      # Unix epoch seconds from JSON
    current_stat: os.stat_result | None

@dataclass
class ProcessResult:
    file: MediaFile
    action: str       # "skip" | "update"
    reason: str       # Human-readable reason (e.g. "No JSON companion", "SetFileTime failed")

# core.py — Core processing pipeline
def scan_directory(path: Path) -> Generator[Path, None, None]: ...
def match_json(media_path: Path) -> Path | None: ...
def read_metadata(json_path: Path) -> tuple[int, int]: ...  # (photo_taken_time, creation_time)
def process_file(media_path: Path) -> ProcessResult: ...
def summarize(results: list[ProcessResult]) -> tuple[int, int, int]: ...  # (updated, skipped, errors)

# platform.py — Cross-platform timestamp setting
def set_file_times(path: Path, creation_time: int | None, modification_time: int | None) -> None: ...

# tui.py — Output formatting
def print_dry_run_table(results: list[ProcessResult]) -> None: ...
def print_summary(updated: int, skipped: int, errors: int) -> None: ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Manual | All spec scenarios | Run against real Takeout export directory with/without `--dry-run` |
| Manual | Error cases | Provide malformed JSON, permission-locked files, missing companions |

No automated test infrastructure available (`testing.runner.available: false` in config). Automated tests deferred until pytest is configured.

## Migration / Rollout

No migration required. Greenfield project — first commit ships the entire change. 200-line PR budget per `openspec/config.yaml`; this PR must stay within that limit.

## Open Questions

None. All architectural decisions resolved during exploration phase.
