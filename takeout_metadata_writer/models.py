"""Data models for the Takeout Metadata Writer core processor."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MediaFile:
    """Represents a media file found during scanning with its metadata.

    Attributes:
        path: Absolute or relative path to the media file.
        json_path: Path to the companion ``.supplemental-metadata.json`` file,
            or ``None`` if no companion exists.
        photo_taken_time: Unix epoch seconds from ``photoTakenTime.timestamp``
            in the companion JSON, or ``None`` if unavailable.
        creation_time: Unix epoch seconds from ``creationTime.timestamp``
            in the companion JSON, or ``None`` if unavailable.
        current_stat: Result of ``os.stat()`` on the media file at discovery
            time, or ``None`` if the stat failed.
    """

    path: Path
    json_path: Optional[Path] = None
    photo_taken_time: Optional[int] = None
    creation_time: Optional[int] = None
    current_stat: Optional[os.stat_result] = None


@dataclass
class ProcessResult:
    """Outcome of processing a single media file.

    Attributes:
        media_file: The ``MediaFile`` instance that was processed.
        action: Type of result — one of ``"update"``, ``"skip_no_json"``,
            ``"skip_no_photo_time"``, or ``"error"``.
        reason: Human-readable explanation when the file was skipped or
            an error occurred. ``None`` when the action is ``"update"``.
    """

    media_file: MediaFile
    action: str
    reason: Optional[str] = None
