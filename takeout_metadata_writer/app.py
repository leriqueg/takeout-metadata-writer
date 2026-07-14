"""Textual TUI application for the Takeout Metadata Writer."""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from takeout_metadata_writer.screens import PathInputScreen, ResultsScreen, SummaryScreen


class WriterApp(App):
    """Textual TUI for scanning and writing Google Takeout metadata timestamps.

    A thin container — all screen logic lives in :mod:`takeout_metadata_writer.screens`.

    Screen navigation uses callbacks from :meth:`push_screen` rather than
    the legacy ``on_screen_dismissed`` message handler (removed in textual 8.x).
    """

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def on_mount(self) -> None:
        """Start on the path input screen."""
        self._go_path_input()

    # ── Screen navigation helpers ───────────────────────────────────────────

    def _go_path_input(self) -> None:
        """Push PathInputScreen and handle its dismiss result."""
        self.push_screen(PathInputScreen(), self._on_path_selected)

    def _on_path_selected(self, path: object) -> None:
        """PathInputScreen was dismissed: ``path`` is a :class:`Path` or ``None``."""
        if isinstance(path, Path):
            self.push_screen(ResultsScreen(path), self._on_results_complete)

    def _on_results_complete(self, result: object) -> None:
        """ResultsScreen was dismissed (Back → ``None``, or write finish → count tuple)."""
        if isinstance(result, tuple):
            up, sk, er = result
            self.push_screen(SummaryScreen(up, sk, er), self._on_summary_done)
        else:
            self._go_path_input()

    def _on_summary_done(self, result: object) -> None:
        """SummaryScreen was dismissed (Back to start) — restart at path input."""
        self._go_path_input()
