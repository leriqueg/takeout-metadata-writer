## Exploration: Rich TUI with Textual for takeout-metadata-writer

### Current State
The project has a working CLI (`cli.py` + `tui.py`) with dry-run preview table and per-file write mode — pure std-lib, zero external dependencies. `core.py` provides synchronous generator-based scanning and per-file processing. `tui.py` formats tables and summaries via plain `print()` statements (142 lines). The existing CLI is the default entry point via `python -m takeout_metadata_writer` → `cli.main()`.

PR 1 (core-processor) is complete and archived. The user now wants to add a rich Terminal User Interface using the `textual` library as a second PR.

### Affected Areas
- `takeout_metadata_writer/tui.py` — Will be partially or fully replaced by Textual widgets. The current `print_dry_run_table()` and `print_summary()` can be kept as fallback for CLI mode.
- `takeout_metadata_writer/cli.py` — Needs an `--cli` flag (or mode switch) so both TUI and CLI paths work.
- `takeout_metadata_writer/__main__.py` — May need to decide which mode to launch.
- `takeout_metadata_writer/app.py` (NEW) — Textual application class and screen definitions.
- `takeout_metadata_writer/app.tcss` (NEW) — Textual CSS styling file.
- `pyproject.toml` — Must add `textual` dependency (and `textual-dev` as optional dev dep).

### Approaches

#### 1. Multi-screen Textual App with DataTable (Recommended)
Full TUI flow across 3 screens:
1. **Path Input Screen** — Input widget + optional "Browse" button using `DirectoryTree`
2. **Results Screen** — `DataTable` showing dry-run results (sortable columns, row selection via cursor)
3. **Confirmation Modal** — `ModalScreen` with Confirm/Cancel buttons, then writes with progress

- **Pros**: Complete, polished UX. Each screen has single responsibility. Textual's `push_screen`/`pop_screen` makes navigation trivial. Async workers handle blocking `core.py` calls naturally.
- **Cons**: More code (~350-400 lines for app + CSS). Slightly steeper learning curve.
- **Effort**: Medium-High

#### 2. Single-Screen App (Minimal)
Everything on one screen: input at top, DataTable below, footer with actions.

- **Pros**: Simpler wiring (~250-300 lines). Less boilerplate.
- **Cons**: Cluttered UI. Harder to manage state transitions. No modal dialog without custom work.
- **Effort**: Medium

### Recommendation

**Go with Approach 1 (multi-screen) with the following specifics:**

1. **Three screens**: `PathInputScreen` → `ResultsScreen` → `ConfirmModal` → write progress on `ResultsScreen` → `SummaryScreen`
2. **Directory input**: `Input` widget + built-in `DirectoryTree` for browsing (avoids `textual-fspicker` dependency — can be added later if needed)
3. **Async strategy**: `@work(thread=True)` on all `core.py` calls. No asyncio rewrite of sync code. Use `call_from_thread()` for UI updates from workers.
4. **Sorting**: Handle `DataTable.HeaderSelected` events to call `table.sort(column_key)` — verified working in Textual v6.x.
5. **Entry point**: TUI as default, `--cli` flag to fall back. `cli.main()` dispatches based on args.
6. **Styling**: Single `app.tcss` file alongside `app.py`.
7. **Dependencies**: `textual>=6.6.0` in `pyproject.toml`. `textual-dev` as optional dev dependency.

### Risks
1. **Textual version compatibility**: Check `DataTable.HeaderSelected` availability on the target version before coding.
2. **Windows terminal**: Textual requires a modern terminal (Windows Terminal). Legacy consoles should gracefully fall back to CLI.
3. **Large datasets (10k+ files)**: Loading everything into DataTable at once may be slow. Monitor performance; paginate if needed.
4. **PR budget**: The original config.yaml sets `max_lines_per_pr: 200`. This change is ~400-500 lines. Needs config exception or chained PRs.
5. **Thread safety**: `call_from_thread()` mandatory for all UI mutations from worker threads.

### Ready for Proposal
**Yes**. The TUI direction is clear, approaches compared, architecture concrete. Proceed to `sdd-propose` for change name `tui-textual`.
