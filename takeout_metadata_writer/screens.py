"""Textual screen classes for the Takeout Metadata Writer TUI."""

from __future__ import annotations

import datetime
from pathlib import Path

from textual import work
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, DirectoryTree, Input, Label, LoadingIndicator
from textual.worker import get_current_worker

from takeout_metadata_writer import core
from takeout_metadata_writer.models import ProcessResult


def _fmt(ts: int | None) -> str:
    if ts is None:
        return "\u2014"
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "\u2014"


class PathInputScreen(Screen):
    """Folder selection: Input + DirectoryTree + Scan button."""

    def compose(self):
        yield Input(placeholder="Enter path to Takeout folder...")
        yield DirectoryTree(path=".")
        yield Button("Scan", variant="primary", id="scan")

    def on_input_submitted(self) -> None:
        self._validate()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan":
            self._validate()

    def on_directory_tree_node_selected(self, event: DirectoryTree.NodeSelected) -> None:
        self.query_one(Input).value = str(event.path)

    def _validate(self) -> None:
        raw = self.query_one(Input).value.strip()
        if not raw:
            self.notify("Please enter a path.", severity="error")
            return
        p = Path(raw)
        if not p.exists():
            self.notify(f"Path does not exist: {p}", severity="error")
            return
        if not p.is_dir():
            self.notify(f"Not a directory: {p}", severity="error")
            return
        for _ in core.scan_directory(p):
            break
        else:
            self.notify("No media files found.", severity="error")
            return
        self.dismiss(p)


class ResultsScreen(Screen):
    """Dry-run results: sortable DataTable, Back / Write buttons."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.results: list[ProcessResult] = []

    def compose(self):
        yield Label(str(self.path))
        yield LoadingIndicator(id="loading")
        yield DataTable(id="table")
        yield Button("Back", id="back")
        yield Button("Write", variant="primary", id="write")

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns(
            "File",
            "Current Created",
            "Current Modified",
            "Target Created",
            "Created From",
            "Target Modified",
            "Modified From",
            "Status",
        )
        t.visible = False
        self.sub_title = "Scanning..."
        self.scan_worker()

    @work(thread=True)
    def scan_worker(self) -> None:
        worker = get_current_worker()
        all_results: list[ProcessResult] = []
        try:
            for mp in core.scan_directory(self.path):
                if worker.is_cancelled:
                    return
                all_results.append(core.process_file(mp, dry_run=True))
        except Exception as exc:
            self.app.call_from_thread(self._notify_err, f"Scan error: {exc}")
            return
        self.app.call_from_thread(self._show_results, all_results)

    def _notify_err(self, msg: str) -> None:
        self.sub_title = ""
        self.notify(msg, severity="error")
        self.dismiss()

    def _show_results(self, results: list[ProcessResult]) -> None:
        self.sub_title = ""
        self.results = results
        self.query_one(LoadingIndicator).remove()
        if not results:
            self.notify("No media files found.", severity="error")
            self.dismiss()
            return
        t = self.query_one(DataTable)
        t.visible = True
        for r in results:
            mf = r.media_file
            s = mf.current_stat
            status = "Update" if r.action == "update" else (f"Error: {r.reason}" if r.action == "error" else "Skip")
            t.add_row(
                mf.path.name,
                _fmt(int(s.st_ctime) if s else None),
                _fmt(int(s.st_mtime) if s else None),
                _fmt(mf.photo_taken_time),
                mf.creation_source,
                _fmt(mf.creation_time),
                mf.modification_source,
                status,
            )

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        self.query_one(DataTable).sort(event.column_key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "back":
            self.dismiss()
        elif bid == "write":

            def cb(v: bool) -> None:
                if v:
                    self.sub_title = "Writing..."
                    self.write_worker()

            self.app.push_screen(ConfirmModal(len(self.results)), cb)

    @work(thread=True)
    def write_worker(self) -> None:
        worker = get_current_worker()
        up = sk = er = 0
        try:
            for r in self.results:
                if worker.is_cancelled:
                    return
                wr = core.process_file(r.media_file.path, dry_run=False)
                if wr.action == "update":
                    up += 1
                elif wr.action == "error":
                    er += 1
                else:
                    sk += 1
        except Exception as exc:
            self.app.call_from_thread(self._notify_err, f"Write error: {exc}")
            return
        self.app.call_from_thread(self._finish_write, up, sk, er)

    def _finish_write(self, up: int, sk: int, er: int) -> None:
        self.sub_title = ""
        self.dismiss((up, sk, er))


class ConfirmModal(ModalScreen[bool]):
    """Yes / No confirmation for writing timestamps."""

    def __init__(self, file_count: int) -> None:
        super().__init__()
        self.file_count = file_count

    def compose(self):
        yield Label(f"Write timestamps to {self.file_count} file(s)? This will modify file timestamps.")
        yield Button("Yes", variant="error", id="yes")
        yield Button("No", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class SummaryScreen(Screen):
    """Final results: updated / skipped / error counts."""

    def __init__(self, updated: int, skipped: int, errors: int) -> None:
        super().__init__()
        self.updated = updated
        self.skipped = skipped
        self.errors = errors

    def compose(self):
        yield Label(f"\u2713 Updated: {self.updated}")
        yield Label(f"\u23ed Skipped: {self.skipped}")
        yield Label(f"\u2717 Errors: {self.errors}")
        yield Button("Back to start", id="back-to-start")
        yield Button("Quit", variant="primary", id="quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-to-start":
            self.dismiss()
        elif event.button.id == "quit":
            self.app.exit()
