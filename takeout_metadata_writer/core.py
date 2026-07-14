"""Core processing pipeline for the Takeout Metadata Writer.

Provides the file-scanning, JSON-companion matching, metadata parsing, and
per-file processing orchestration that forms the heart of the application.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Generator, Optional

from takeout_metadata_writer.models import MediaFile, ProcessResult
from takeout_metadata_writer.platform import set_file_times

logger = logging.getLogger(__name__)

# ── Constants ----------------------------------------------------------------

_MEDIA_EXTENSIONS = frozenset({
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".heic",
    ".heif",
    ".3gp",
})

_SUPPLEMENTAL_SUFFIX = ".supplemental-metadata.json"

# ── Public API ---------------------------------------------------------------


def scan_directory(path: Path) -> Generator[Path, None, None]:
    """Walk *path* recursively and yield media-file paths.

    Yields only regular files whose extension matches one of the recognised
    media types.  Comppanion ``.supplemental-metadata.json`` files (which also
    match media extensions by name) are excluded so they are never processed
    as media.
    """
    for entry in path.rglob("*"):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in _MEDIA_EXTENSIONS:
            continue
        # Skip companion metadata files — they may embed a media extension in
        # their name (e.g. ``IMG_001.jpg.supplemental-metadata.json``) but
        # should never be treated as media.
        if entry.name.endswith(_SUPPLEMENTAL_SUFFIX):
            continue
        yield entry


def match_json(media_path: Path) -> Optional[Path]:
    """Locate the companion ``.supplemental-metadata.json`` for *media_path*.

    Google Takeout produces companion files named after the pattern::

        {original_filename}.supplemental-metadata.json

    e.g. ``IMG_001.jpg.supplemental-metadata.json``.

    If the exact name is not found, falls back to a glob for
    ``{media_path.name}.*.json`` in the same directory — this handles
    truncated suffixes (e.g. ``.supplemental-metad.json``) and duplicate
    markers (e.g. ``.supplemental-metadata(1).json``).  If the glob
    matches exactly one file, that file is returned; otherwise ``None``.
    """
    companion_name = f"{media_path.name}{_SUPPLEMENTAL_SUFFIX}"
    companion = media_path.with_name(companion_name)
    if companion.is_file():
        return companion

    # Fallback: glob for any JSON suffixed to the full media name
    candidates = list(media_path.parent.glob(f"{media_path.name}.*.json"))
    if len(candidates) == 1:
        logger.debug("Fallback matched %s for %s", candidates[0].name, media_path.name)
        return candidates[0]

    return None


def read_metadata(
    json_path: Path,
) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Parse Google Takeout companion metadata JSON.

    Extracts ``photoTakenTime.timestamp`` (required) and
    ``creationTime.timestamp`` (optional) as Unix-epoch integers.

    Parameters
    ----------
    json_path:
        Path to the companion ``.supplemental-metadata.json`` file.

    Returns
    -------
    A three-tuple ``(photo_taken_time, creation_time, error_message)``.
    On success *error_message* is ``None``.  On any failure both timestamp
    fields are ``None`` and *error_message* contains the exception text.
    """
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        photo_time = int(data["photoTakenTime"]["timestamp"])
    except (KeyError, json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        return None, None, str(exc)

    # creationTime is optional in Takeout metadata — return None if absent
    creation_time: Optional[int] = None
    creation_data = data.get("creationTime")
    if creation_data is not None:
        ts = creation_data.get("timestamp")
        if ts is not None:
            try:
                creation_time = int(ts)
            except (TypeError, ValueError):
                creation_time = None

    return photo_time, creation_time, None


def process_file(media_path: Path, dry_run: bool) -> ProcessResult:
    """Process a single media file end-to-end.

    The pipeline is::

        stat → match_json → read_metadata → [set_file_times]

    If *dry_run* is ``True`` the timestamps are read and reported but never
    written to disk.

    Parameters
    ----------
    media_path:
        Path to the media file to process.
    dry_run:
        If ``True``, skip the actual ``set_file_times`` call.

    Returns
    -------
    A :class:`ProcessResult` describing what happened.
    """
    # --- stat ---------------------------------------------------------------
    try:
        current_stat = media_path.stat()
    except OSError as exc:
        return ProcessResult(
            media_file=MediaFile(path=media_path),
            action="error",
            reason=str(exc),
        )

    # --- match JSON companion -----------------------------------------------
    json_path = match_json(media_path)
    if json_path is None:
        return ProcessResult(
            media_file=MediaFile(path=media_path, current_stat=current_stat),
            action="skip_no_json",
        )

    # --- read metadata ------------------------------------------------------
    photo_time, creation_time, error_msg = read_metadata(json_path)
    if photo_time is None:
        return ProcessResult(
            media_file=MediaFile(
                path=media_path,
                json_path=json_path,
                current_stat=current_stat,
            ),
            action="skip_no_photo_time",
            reason=error_msg or "photoTakenTime.timestamp not found in JSON",
        )

    # --- apply timestamps (write mode only) ---------------------------------
    if not dry_run:
        err = set_file_times(
            media_path,
            creation_time=photo_time,
            modification_time=creation_time,
        )
        if err is not None:
            return ProcessResult(
                media_file=MediaFile(
                    path=media_path,
                    json_path=json_path,
                    photo_taken_time=photo_time,
                    creation_time=creation_time,
                    current_stat=current_stat,
                ),
                action="error",
                reason=err,
            )

    return ProcessResult(
        media_file=MediaFile(
            path=media_path,
            json_path=json_path,
            photo_taken_time=photo_time,
            creation_time=creation_time,
            current_stat=current_stat,
        ),
        action="update",
    )


def summarize(results: list[ProcessResult]) -> tuple[int, int, int]:
    """Aggregate processing results into counts.

    Parameters
    ----------
    results:
        The full list of :class:`ProcessResult` instances from processing.

    Returns
    -------
    ``(updated_count, skipped_count, error_count)`` where *skipped* includes
    both ``skip_no_json`` and ``skip_no_photo_time`` results.
    """
    updated = 0
    skipped = 0
    errors = 0

    for r in results:
        if r.action == "update":
            updated += 1
        elif r.action == "error":
            errors += 1
        else:
            skipped += 1

    return updated, skipped, errors
