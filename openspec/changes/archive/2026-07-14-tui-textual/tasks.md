# Tasks: TUI — Rich Textual TUI for Google Takeout Metadata Writer

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~332 (170 + 140 + 22) |
| 400-line budget risk | Low |
| Chained PRs recommended | Yes |
| Suggested split | PR 2a (screens.py) → PR 2b (app.py + tcss) → PR 2c (cli.py + toml) |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Screen classes | PR 2a | `screens.py` — base slice, no deps |
| 2 | App + CSS | PR 2b | `app.py` + `app.tcss` — stacked on PR 2a branch |
| 3 | CLI + dependency | PR 2c | `cli.py` + `pyproject.toml` — stacked on PR 2b branch |

## Phase 1: Screen Classes (PR 2a)

- [x] 1.1 Create `PathInputScreen` in `screens.py` — `Input` + `DirectoryTree` + "Scan" button, path validation, empty-dir error guard
- [x] 1.2 Create `ResultsScreen` in `screens.py` — 6-column sortable `DataTable`, loading indicator, "Write"/"Back" buttons, `@work(thread=True)` scan worker
- [x] 1.3 Create `ConfirmModal` in `screens.py` — "Write timestamps to N files?" modal with Yes/No, returns bool via `Screen.dismiss()`
- [x] 1.4 Create `SummaryScreen` in `screens.py` — updated/skipped/error counts, "Back to start"/"Quit" buttons

## Phase 2: App + CSS (PR 2b)

- [x] 2.1 Create `WriterApp(App)` in `app.py` — `SCREENS` dict, `CSS_PATH`, reactive state, keyboard bindings for auto-dismiss
- [x] 2.2 Create `app.tcss` — layouts for all 4 screens, widget sizing, button colors

## Phase 3: CLI Wiring + Dependency (PR 2c)

- [x] 3.1 Add `--cli` flag to `cli.py`, TUI dispatch via `WriterApp().run()` by default, legacy terminal detection with error message
- [x] 3.2 Add `textual>=6.6.0` to `pyproject.toml` dependencies
