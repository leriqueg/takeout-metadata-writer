"""Terminal-output formatting for the Takeout Metadata Writer.

Provides dry-run comparison tables and end-of-run summary output
using plain text with no external dependencies.
"""

from __future__ import annotations

import datetime
import os
import sys
from typing import Optional

from takeout_metadata_writer.models import ProcessResult


# ── Helpers -------------------------------------------------------------------


def _fmt_timestamp(ts: Optional[int]) -> str:
    """Format a Unix epoch timestamp as ``YYYY-MM-DD HH:MM:SS``.

    Returns an em-dash (``—``) when *ts* is ``None`` or can not be
    converted to a local-time datetime.
    """
    if ts is None:
        return "-"
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "-"


# ── Public API ----------------------------------------------------------------


def _safe_print(text: str, **kwargs) -> None:
    """Print with Unicode replacement for characters the terminal can't encode."""
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Replace characters that the terminal codec can't handle
        codec = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        safe = text.encode(codec, errors="replace").decode(codec, errors="replace")
        print(safe, **kwargs)


def print_dry_run_table(results: list[ProcessResult]) -> None:
    """Print a formatted table showing what WOULD change in dry-run mode.

    *Update* and *error* results appear in the main table with current vs.
    target timestamps.  Skipped results (``"skip_no_json"``,
    ``"skip_no_photo_time"``) are listed as brief notes below the table.

    Columns shown:

        File | Current Created | Current Modified | Target Created
        | Target Modified | Status
    """
    updates = [r for r in results if r.action == "update"]
    errors = [r for r in results if r.action == "error"]
    skips = [r for r in results if r.action.startswith("skip")]

    if not results:
        _safe_print("No files found.")
        return

    # ── Table rows (updates + errors) ─────────────────────────────────────
    rows: list[tuple[str, str, str, str, str, str]] = []

    for r in updates + errors:
        mf = r.media_file
        stat: Optional[os.stat_result] = mf.current_stat

        current_created = _fmt_timestamp(int(stat.st_ctime) if stat else None)
        current_modified = _fmt_timestamp(int(stat.st_mtime) if stat else None)
        target_created = _fmt_timestamp(mf.photo_taken_time)
        target_modified = _fmt_timestamp(mf.creation_time)

        if r.action == "error":
            status = f"ERROR: {r.reason}" if r.reason else "ERROR"
        else:
            status = "UPDATE"

        rows.append((
            mf.path.name,
            current_created,
            current_modified,
            target_created,
            target_modified,
            status,
        ))

    # ── Column sizing ─────────────────────────────────────────────────────
    headers = [
        "File",
        "Current Created",
        "Current Modified",
        "Target Created",
        "Target Modified",
        "Status",
    ]
    col_widths = [len(h) for h in headers]

    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Cap the filename column so very long names don't break the layout
    col_widths[0] = min(col_widths[0], 60)

    # ── Render header ─────────────────────────────────────────────────────
    separator = "  ".join("-" * w for w in col_widths)
    _safe_print("  ".join(h.ljust(w) for h, w in zip(headers, col_widths)))
    _safe_print(separator)

    # ── Render rows ───────────────────────────────────────────────────────
    for row in rows:
        _safe_print("  ".join(cell.ljust(w) for cell, w in zip(row, col_widths)))

    # ── Skip-file notes ───────────────────────────────────────────────────
    if skips:
        _safe_print("")
        _safe_print("Skipped files:")
        for r in skips:
            name = r.media_file.path.name
            if r.action == "skip_no_json":
                _safe_print(f"  * {name}: No companion JSON found")
            elif r.action == "skip_no_photo_time":
                reason = r.reason or "No photoTakenTime in JSON"
                _safe_print(f"  * {name}: {reason}")
            else:
                _safe_print(f"  * {name}: Skipped ({r.reason or r.action})")


def print_summary(updated: int, skipped: int, errors: int) -> None:
    """Print end-of-run summary counts.

    Parameters
    ----------
    updated:
        Number of files successfully updated.
    skipped:
        Number of files skipped (no JSON companion or no photo time).
    errors:
        Number of files that failed processing.
    """
    total = updated + skipped + errors
    _safe_print("")
    _safe_print("-- Summary ----")
    _safe_print(f"  Updated  {updated:>4}")
    _safe_print(f"  Skipped  {skipped:>4}")
    _safe_print(f"  Errors   {errors:>4}")
    _safe_print("------------------------------------------------------")
    _safe_print(f"  Total    {total:>4}")
