# Design: Textual TUI

## Technical Approach

Add `textual>=6.6.0`. Create `screens.py` with 4 `Screen` subclasses, `app.py` with `WriterApp(App)` using `SCREENS` dict + `CSS_PATH`. Blocking `core.py` calls via `@work(thread=True)`; UI updates through `call_from_thread()`. `cli.main()` gains `--cli` flag — when absent, launches `WriterApp().run()`. Terminal detection via `sys.stdout.isatty()` + `TERM_PROGRAM` env check.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Async pattern | `@work(thread=True)` | Rewrite core as async / manual `run_in_executor` | No value in refactoring sync core. `@work` is Textual-native, less boilerplate than executor. |
| Screen file layout | Separate `screens.py` | All in `app.py` | **200-line PR budget** (per `config.yaml`). Splitting screens into their own file keeps each slice under budget. No circular import — `screens.py` never imports `app.py`; screens access `self.app` dynamically via Textual's `Screen.app` property. |
| State management | `reactive` attrs on `WriterApp` | External store / signals | Textual's reactive system handles UI invalidation automatically. Screens read via `self.app.<attr>`. |
| Sorting | `DataTable.HeaderSelected` → `table.sort()` | Custom sort logic | Built-in `DataTable.sort()` handles column-wise sort with `reverse` toggle on second click. |
| Terminal detection | `isatty()` + `TERM_PROGRAM` | Only `isatty()` | `isatty()` catches piped output; `TERM_PROGRAM` catches cmd.exe specifically (`"wt"` for Windows Terminal, missing for cmd). |
| CLI dispatch | `--cli` flag in mutually-exclusive group | Separate entry point | Keep `__main__.py` unchanged. TUI becomes default, `--cli` preserves existing argparse path. |
| `textual` dependency | **Required** (not optional) | Optional with lazy imports | `cli.main()` will `import app` which imports `textual` — if optional, unguarded import crashes. Lazy import adds complexity with no benefit for a TUI-first tool. |

## Data Flow

```
PathInputScreen ──[Scan]──→ @work(thread=True) scan_directory() + process_file(dry_run=True)
       │                             │
       │                     call_from_thread() ←── worker sets self.app.scan_results
       │                             │
       │◄──────── push_screen("results") ──────────┘
       │
ResultsScreen ──[Write]──→ push_screen("confirm")
       │                           │
       │◄─── [No] pop_screen() ────┘
       │
       └─── [Yes] @work(thread=True) process_file(dry_run=False) per file
                            │
                    accumulate counts via call_from_thread()
                            │
                    push_screen("summary") ──[Quit]→ app.exit()
                         │
                         └──[Back to start]→ push_screen("path_input")
```

## File Changes

| File | Action | Lines | Description |
|------|--------|-------|-------------|
| `takeout_metadata_writer/screens.py` | Create | ~170 | 4 `Screen` subclasses: `PathInputScreen`, `ResultsScreen`, `ConfirmModal`, `SummaryScreen` |
| `takeout_metadata_writer/app.py` | Create | ~80 | `WriterApp` class, `SCREENS` dict, `CSS_PATH`, `compose()` |
| `takeout_metadata_writer/app.tcss` | Create | ~60 | Textual CSS (layout, widget sizing, button colors) |
| `takeout_metadata_writer/cli.py` | Modify | ~20 | Add `--cli` flag; TUI dispatch in `main()` |
| `pyproject.toml` | Modify | ~2 | Add `textual>=6.6.0` |

## Interfaces / Contracts

```python
# WriterApp reactive state (Textual reactive attrs)
scan_results: reactive[list[ProcessResult]] = reactive([])
updated_count: reactive[int] = reactive(0)
skipped_count: reactive[int] = reactive(0)
error_count: reactive[int] = reactive(0)
scanning: reactive[bool] = reactive(False)
writing: reactive[bool] = reactive(False)

# Screen names (SCREENS dict keys)
"path_input" → PathInputScreen    # Initial screen
"results"    → ResultsScreen      # After scan completes
"summary"    → SummaryScreen      # After write completes
"confirm"    → ConfirmModal       # Modal overlay

# Worker signatures (used with @work(thread=True))
def scan_worker(path: str) → None        # Sets self.app.scan_results
def write_worker() → None                 # Iterates results, accumulates counts
```

## Chained PR Split (200-line budget)

Per `config.yaml` `max_lines_per_pr: 200`:

| PR | Files | Est. Lines | Scope |
|----|-------|------------|-------|
| PR 2a | `screens.py` | ~170 | All 4 screen classes + worker functions. Can be verified independently (imports fail gracefully without `app.py`). |
| PR 2b | `app.py` + `app.tcss` | ~140 | `WriterApp` class, CSS. Imports screens from PR 2a. Stacked on PR 2a branch. |
| PR 2c | `cli.py` + `pyproject.toml` | ~22 | Wiring and dependency. Stacked on PR 2b branch. |

Each PR under 200 lines. All follow stacked-to-main branching (PR 2a → feature branch, 2b → 2a's branch, 2c → 2b's branch).

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Terminal detection | Test `_terminal_supported()` helper with mocked `sys.stdout` and env vars |
| Unit | TUI dispatch in `cli.main()` | Test `--cli /path` preserves existing CLI output |
| Manual | Screen navigation, sort, modal | Run `python -m takeout_metadata_writer` in Windows Terminal |
| Manual | Legacy terminal error | Run in cmd.exe, verify error message |

## Migration / Rollout

No migration. New dependency installed via `pip install takeout-metadata-writer` or `pip install textual`.

## Open Questions

- [ ] **Rollback of chained PRs**: If PR 2a is merged but 2b is reverted, the codebase has orphaned `screens.py`. Mitigation: merge all 3 PRs atomically or use a feature branch that merges to main only when all 3 pass review. The stacked-to-main model already handles this — only the tip PR merges to main.
