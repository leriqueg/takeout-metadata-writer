"""Command-line interface for the Takeout Metadata Writer.

Provides ``main()`` that parses ``argv`` with ``argparse``, scans a
directory, processes every media file, and prints formatted output
(dry-run preview table or write-mode per-file status + summary).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from takeout_metadata_writer.core import process_file, scan_directory, summarize
from takeout_metadata_writer.models import ProcessResult
from takeout_metadata_writer.tui import _safe_print, print_dry_run_table, print_summary

logger = logging.getLogger(__name__)


# ── Argument parser -----------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Restore file creation and modification timestamps from Google "
            "Takeout companion metadata (.supplemental-metadata.json)."
        ),
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use CLI mode instead of TUI (requires path)",
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=str,
        help="Directory to scan for media files with companion metadata (required with --cli)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview what would change without writing timestamps (default: false)",
    )
    return parser


# ── Entry point ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv:
        Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    ``0`` on success, ``1`` when the input path is invalid or when at
    least one file errored.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # ── TUI mode (default) ───────────────────────────────────────────────
    if not args.cli:
        try:
            from takeout_metadata_writer.app import WriterApp

            app = WriterApp()
            app.run()
            return 0
        except Exception:
            print(
                "Error: Textual TUI is not available in this terminal.",
                file=sys.stderr,
            )
            print(
                "Tip: Use --cli flag for command-line mode: "
                "python -m takeout_metadata_writer --cli <path>",
                file=sys.stderr,
            )
            return 1

    # ── CLI mode: path is required ───────────────────────────────────────
    if not args.path:
        parser.error("path argument is required in CLI mode")

    # ── Resolve & validate path ───────────────────────────────────────────
    try:
        root = Path(args.path).resolve(strict=True)
    except FileNotFoundError:
        print(f"Error: path not found -- {args.path}", file=sys.stderr)
        return 1

    if not root.is_dir():
        print(f"Error: not a directory -- {args.path}", file=sys.stderr)
        return 1

    # ── Scan ──────────────────────────────────────────────────────────────
    media_paths = list(scan_directory(root))

    if not media_paths:
        print("No media files found.")
        return 0

    # ── Process each file ─────────────────────────────────────────────────
    results: list[ProcessResult] = []
    for mp in media_paths:
        result = process_file(mp, dry_run=args.dry_run)
        results.append(result)

    # ── Aggregate ─────────────────────────────────────────────────────────
    updated, skipped, errors = summarize(results)

    # ── Output ────────────────────────────────────────────────────────────
    if args.dry_run:
        # Preview table + summary
        print_dry_run_table(results)
    else:
        # Write mode: per-file action, no preview table
        for r in results:
            name = r.media_file.path.name
            if r.action == "update":
                _safe_print(f"  WROTE    {name}")
            elif r.action == "skip_no_json":
                _safe_print(f"  SKIP     {name}  (no companion JSON)")
            elif r.action == "skip_no_photo_time":
                _safe_print(f"  SKIP     {name}  ({r.reason or 'no photo time'})")
            elif r.action == "error":
                reason = r.reason or "unknown error"
                _safe_print(f"  ERROR    {name}  --  {reason}")

    print_summary(updated, skipped, errors)

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
