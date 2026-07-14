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
        photo_taken_time: Resolved creation time (Unix epoch seconds).
            Priority order: EXIF ``DateTimeOriginal`` > JSON
            ``photoTakenTime.timestamp`` > ``None``.
        creation_time: Resolved modification time (Unix epoch seconds).
            Typically from JSON ``creationTime.timestamp``.
        creation_source: Short label indicating where the creation time
            came from — ``"EXIF"``, ``"JSON"``, or ``"—"``.
        modification_source: Short label for the modification time
            source — ``"JSON"`` or ``"—"``.
        current_stat: Result of ``os.stat()`` on the media file at discovery
            time, or ``None`` if the stat failed.
        description: Free-text description from the companion JSON, or
            ``None``.
        device_make: Camera/device manufacturer from EXIF ``Make`` tag,
            or ``None``.
        device_model: Camera/device model from EXIF ``Model`` tag,
            or ``None``.
    """

    path: Path
    json_path: Optional[Path] = None
    photo_taken_time: Optional[int] = None
    creation_time: Optional[int] = None
    creation_source: str = "\u2014"
    modification_source: str = "\u2014"
    current_stat: Optional[os.stat_result] = None
    description: Optional[str] = None
    device_make: Optional[str] = None
    device_model: Optional[str] = None


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
