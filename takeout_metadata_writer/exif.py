"""Pure-Python EXIF parser for JPEG and HEIF/HEIC files.

Reads only the tags needed by the Takeout Metadata Writer:

* ``DateTimeOriginal`` (0x9003) — original capture time
* ``Make`` (0x010F) — camera / device manufacturer
* ``Model`` (0x0110) — camera / device model
* ``OffsetTimeOriginal`` (0x9011) — timezone offset (optional)

All parsing is done with the standard library (``struct``, ``datetime``) —
no Pillow or other dependencies required.
"""

from __future__ import annotations

import logging
import struct
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── TIFF tag IDs ──────────────────────────────────────────────────────────────

_TAG_EXIF_IFD = 0x8769
_TAG_MAKE = 0x010F
_TAG_MODEL = 0x0110
_TAG_DATE_TIME_ORIGINAL = 0x9003

# ── TIFF IFD entry types ──────────────────────────────────────────────────────

_TYPE_BYTE = 1
_TYPE_ASCII = 2
_TYPE_SHORT = 3
_TYPE_LONG = 4
_TYPE_RATIONAL = 5
_TYPE_UNDEFINED = 7
_TYPE_SLONG = 9
_TYPE_SRATIONAL = 10

_TYPE_SIZES = {
    _TYPE_BYTE: 1,
    _TYPE_ASCII: 1,
    _TYPE_SHORT: 2,
    _TYPE_LONG: 4,
    _TYPE_RATIONAL: 8,
    _TYPE_UNDEFINED: 1,
    _TYPE_SLONG: 4,
    _TYPE_SRATIONAL: 8,
}


# ── Internal helpers ──────────────────────────────────────────────────────────


def _parse_tiff_timestamp(dt_str: str) -> Optional[int]:
    """Convert an EXIF ``YYYY:MM:DD HH:MM:SS`` string to a Unix timestamp.

    Returns ``None`` if the string cannot be parsed.
    """
    dt_str = dt_str.strip()
    try:
        dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, OSError, OverflowError):
        return None


def _read_value(data: BytesIO, fmt: str, tag_type: int, count: int):
    """Read a typed value from the current stream position."""
    if tag_type == _TYPE_ASCII:
        raw = data.read(count)
        return raw.split(b"\0")[0].decode("ascii", errors="replace").strip()
    elif tag_type == _TYPE_SHORT:
        return struct.unpack(f"{fmt}{count}H", data.read(2 * count))
    elif tag_type == _TYPE_LONG:
        return struct.unpack(f"{fmt}{count}I", data.read(4 * count))
    elif tag_type == _TYPE_RATIONAL:
        vals = []
        for _ in range(count):
            num, den = struct.unpack(f"{fmt}II", data.read(8))
            vals.append((num, den))
        return vals
    elif tag_type == _TYPE_SLONG:
        return struct.unpack(f"{fmt}{count}i", data.read(4 * count))
    elif tag_type == _TYPE_SRATIONAL:
        vals = []
        for _ in range(count):
            num, den = struct.unpack(f"{fmt}ii", data.read(8))
            vals.append((num, den))
        return vals
    else:
        # BYTE, UNDEFINED — skip
        data.read(count)
        return None


def _read_ifd_entry_value(
    data: BytesIO,
    endian: str,
    tag_type: int,
    count: int,
    raw_offset: bytes,
) -> any:
    """Dispatch an IFD entry's 4-byte value/offset field.

    Values that fit in 4 bytes are stored inline; larger values store a
    file offset pointing to the actual data.
    """
    fmt = "<" if endian == "II" else ">"
    size = _TYPE_SIZES.get(tag_type, 1) * count

    if size <= 4:
        # ── Inline value ─────────────────────────────────────────────────
        if tag_type == _TYPE_ASCII:
            return raw_offset.split(b"\0")[0].decode("ascii", errors="replace").strip()
        elif tag_type == _TYPE_SHORT:
            return struct.unpack(f"{fmt}H", raw_offset[:2])[0]
        elif tag_type == _TYPE_LONG:
            return struct.unpack(f"{fmt}I", raw_offset)[0]
        elif tag_type == _TYPE_SLONG:
            return struct.unpack(f"{fmt}i", raw_offset)[0]
        elif tag_type == _TYPE_RATIONAL:
            num = struct.unpack(f"{fmt}I", raw_offset[:4])[0]
            den = struct.unpack(f"{fmt}I", raw_offset[4:])[0]
            return [(num, den)]
        elif tag_type == _TYPE_SRATIONAL:
            num = struct.unpack(f"{fmt}i", raw_offset[:4])[0]
            den = struct.unpack(f"{fmt}i", raw_offset[4:])[0]
            return [(num, den)]
        else:
            return None
    else:
        # ── Offset to value ──────────────────────────────────────────────
        offset = struct.unpack(f"{fmt}I", raw_offset)[0]
        save = data.tell()
        try:
            data.seek(offset)
            return _read_value(data, fmt, tag_type, count)
        except (OSError, ValueError):
            return None
        finally:
            data.seek(save)


def _parse_ifd(
    data: BytesIO,
    endian: str,
    offset: int,
    target_tags: set[int],
    visited: set[int],
) -> dict[int, any]:
    """Parse a single TIFF IFD starting at *offset*.

    Only tags in *target_tags* (plus the EXIF-IFD pointer) are extracted.
    *visited* tracks offsets already seen to avoid infinite loops (chained
    IFD0 → IFD1 → …).
    """
    if offset in visited or offset <= 0:
        return {}
    visited.add(offset)

    fmt = "<" if endian == "II" else ">"
    result: dict[int, any] = {}

    try:
        data.seek(offset)
        num_entries = struct.unpack(f"{fmt}H", data.read(2))[0]
    except (struct.error, OSError):
        return result

    for _ in range(num_entries):
        entry = data.read(12)
        if len(entry) < 12:
            break

        tag = struct.unpack(f"{fmt}H", entry[0:2])[0]
        tag_type = struct.unpack(f"{fmt}H", entry[2:4])[0]
        count = struct.unpack(f"{fmt}I", entry[4:8])[0]
        raw_offset = entry[8:12]

        if tag == _TAG_EXIF_IFD:
            # Follow pointer to the EXIF sub-IFD
            exif_offset = struct.unpack(f"{fmt}I", raw_offset)[0]
            sub = _parse_ifd(data, endian, exif_offset, target_tags, visited)
            result.update(sub)
        elif tag in target_tags:
            val = _read_ifd_entry_value(data, endian, tag_type, count, raw_offset)
            result[tag] = val

    return result


# ── Public API ────────────────────────────────────────────────────────────────


def parse_jpeg(path: Path) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Read EXIF metadata from a JPEG or HEIF/HEIC file.

    Parameters
    ----------
    path:
        Path to the image file.

    Returns
    -------
    A three-tuple ``(datetime_original_timestamp, make, model)``.
    Each value is ``None`` if the corresponding tag was not found or
    could not be parsed.
    """
    # ── Read raw bytes (first 256 KB – EXIF lives near the start) ─────────────
    try:
        with open(path, "rb") as fh:
            raw = fh.read(256 * 1024)
    except (OSError, PermissionError) as exc:
        logger.debug("EXIF: can't read %s: %s", path, exc)
        return None, None, None

    if len(raw) < 4:
        return None, None, None

    # ── JPEG: look for APP1 "Exif\0\0" ────────────────────────────────────────
    if raw[:2] == b"\xFF\xD8":
        return _parse_jpeg_app1(raw)

    # ── HEIF / HEIC: look for "ftyp" box + "Exif" data ────────────────────────
    # HEIC files can embed EXIF via the 'Exif' box inside 'meta' → 'hdir'.
    # For now this is not implemented — HEIC EXIF reading can be added later.
    logger.debug("EXIF: unsupported file signature for %s", path)
    return None, None, None


def _parse_jpeg_app1(raw: bytes) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Scan JPEG segments for APP1 with ``Exif\0\0`` and parse TIFF inside."""
    pos = 2
    while pos < len(raw) - 2:
        if raw[pos] != 0xFF:
            break
        marker = raw[pos + 1]
        # Length includes the 2-byte length field itself
        seg_len = struct.unpack(">H", raw[pos + 2: pos + 4])[0]
        if seg_len < 2:
            break

        if marker == 0xE1:  # APP1 — Exif segment
            app1_data = raw[pos + 4: pos + 4 + seg_len - 2]
            if app1_data[:6] == b"Exif\0\0":
                tiff_data = app1_data[6:]
                return _parse_tiff_header(tiff_data)

        pos += 2 + seg_len
        if marker == 0xDA:  # SOS — Start Of Scan, no more metadata
            break

    return None, None, None


def _parse_tiff_header(
    tiff_data: bytes,
) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Parse the TIFF header and IFD0 inside an Exif APP1 segment."""
    if len(tiff_data) < 8:
        return None, None, None

    endian = tiff_data[:2].decode("ascii")
    if endian not in ("II", "MM"):
        return None, None, None

    fmt = "<" if endian == "II" else ">"
    magic = struct.unpack(f"{fmt}H", tiff_data[2:4])[0]
    if magic != 42:
        return None, None, None

    ifd_offset = struct.unpack(f"{fmt}I", tiff_data[4:8])[0]
    data = BytesIO(tiff_data)

    target_tags = {_TAG_DATE_TIME_ORIGINAL, _TAG_MAKE, _TAG_MODEL}
    ifd_values = _parse_ifd(data, endian, ifd_offset, target_tags, set())

    dt_raw = ifd_values.get(_TAG_DATE_TIME_ORIGINAL)
    make = ifd_values.get(_TAG_MAKE)
    model = ifd_values.get(_TAG_MODEL)

    timestamp = _parse_tiff_timestamp(dt_raw) if isinstance(dt_raw, str) else None
    make_str = str(make).strip() if isinstance(make, str) else None
    model_str = str(model).strip() if isinstance(model, str) else None

    return timestamp, make_str, model_str
