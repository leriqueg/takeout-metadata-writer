# Proposal: TUI — Rich Textual TUI for Google Takeout Metadata Writer

## Intent

The current CLI is functional but requires terminal-familiar operation (path arguments, flags). A rich TUI lowers the barrier: users can browse directories interactively, preview results in a sortable table, and confirm writes — all without remembering flags.

## Scope

### In Scope

1. `textual>=6.6.0` dependency and package config in `pyproject.toml`
2. `takeout_metadata_writer/app.py` — Textual `App` with 3 screens + 1 modal:
   - `PathInputScreen` — `Input` + `DirectoryTree` folder browser + "Scan" button
   - `ResultsScreen` — `DataTable` with sortable columns (File, Current Created, Current Modified, Target Created, Target Modified, Status) + "Write" and "Back" buttons
   - `ConfirmModal` — Yes/No dialog before write
   - `SummaryScreen` — final counts with "Quit" and "Back to start"
3. `takeout_metadata_writer/app.tcss` — Textual CSS styling for all screens
4. CLI `--cli` flag to bypass TUI and use existing argparse path
5. `__main__.py` updated to launch TUI by default (via new `app.py`)
6. Graceful fallback: detect legacy terminal and print error directing to `--cli`

### Out of Scope
- File-level filtering/selection (checkboxes per row) — deferred
- EXIF metadata reading/writing — deferred
- Real-time progress bar during write — use a status label instead
- `textual-fspicker` dependency — use built-in `DirectoryTree`

## Capabilities

### New Capabilities
- `tui-textual`: Rich Textual TUI with multi-screen navigation, interactive directory browsing, sortable DataTable dry-run preview, confirm-before-write modal, and final summary — replaces default CLI entry point.

### Modified Capabilities
None — core-processor requirements (scan, match, parse, dry-run, write, per-file isolation) are unchanged. Only the CLI dispatch implementation changes.

## Approach

Add `textual>=6.6.0` dep. Create `app.py` with a `WriterApp` class using `SCREENS` and `CSS_PATH`. Each screen is a separate `Screen` subclass. Blocking `core.py` calls run via `@work(thread=True)` — no asyncio rewrite. UI updates from workers use `self.call_from_thread()`. Sorting via `DataTable.HeaderSelected` → `table.sort(column_key)`. `cli.py` gets a `--cli` flag; when absent, `main()` launches `WriterApp().run()`. `__main__.py` stays unchanged (still delegates to `cli.main()`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `takeout_metadata_writer/app.py` | New | Textual App, 4 Screen classes, async workers |
| `takeout_metadata_writer/app.tcss` | New | Textual CSS (~60 lines) |
| `takeout_metadata_writer/cli.py` | Modified | `--cli` flag, dispatch to `WriterApp` or CLI |
| `pyproject.toml` | Modified | Add `textual>=6.6.0` dependency |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PR exceeds 200-line budget (~400-500 total) | High | Chained PRs stacked-to-main: slice 1 = app.py + tcss, slice 2 = cli wiring + pyproject |
| Textual requires Windows Terminal, not cmd.exe | Med | Detect terminal capabilities at startup; show clear error + `--cli` fallback hint |
| Large datasets lag DataTable | Low | Monitor; defer pagination until it's a real bottleneck |
| Thread safety with `call_from_thread()` | Low | All UI mutations go through `call_from_thread()` — reviewed on code review |

## Rollback Plan

Full revert: remove `textual` from `pyproject.toml`, delete `app.py` and `app.tcss`, revert `cli.py` and `__main__.py` to PR 1 state. No data risk — TUI never modifies files without user confirmation.

## Dependencies

- Python 3.10+
- `textual>=6.6.0` (new external dependency — first for this project)

## Success Criteria

- [ ] `python -m takeout_metadata_writer` launches TUI with path input screen
- [ ] `--cli /path` falls back to original CLI flow
- [ ] DirectoryTree navigates and selects folders; "Scan" shows ResultsScreen with populated DataTable
- [ ] DataTable columns sort on header click
- [ ] "Write" opens ConfirmModal; confirm writes all files with status label
- [ ] SummaryScreen shows correct updated/skipped/error counts
- [ ] Legacy terminal shows clear error message with `--cli` workaround
- [ ] All existing CLI behavior preserved under `--cli` flag
