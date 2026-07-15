# takeout-metadata-writer

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/leriqueg/takeout-metadata-writer)](https://github.com/leriqueg/takeout-metadata-writer)
[![GitHub issues](https://img.shields.io/github/issues/leriqueg/takeout-metadata-writer)](https://github.com/leriqueg/takeout-metadata-writer/issues)

Restore the original capture and upload timestamps on photos and videos exported from Google Takeout, using the companion JSON metadata files Google bundles with every export.

---

## Motivation

When you export your Google Photos library via Takeout, every file loses its original timestamps:

- The **creation time** becomes the date the Takeout archive was generated.
- The **modification time** becomes the date the file was written to disk.

That makes it impossible to browse your photos chronologically in any file explorer. Luckily, Google includes a `.supplemental-metadata.json` file for each media item with two critical fields:

| JSON field             | Meaning                            | Maps to              |
|------------------------|------------------------------------|----------------------|
| `photoTakenTime`       | When the photo was actually taken  | Creation time        |
| `creationTime`         | When it was uploaded to Google     | Modification time    |

---

## Features

- **Recursive scanning** — walks an entire unarchived Takeout directory tree.
- **Smart JSON matching** — finds each file's companion metadata by exact name, with a glob fallback that handles truncated suffixes (e.g. `.supplemental-meta.json`) and duplicate markers (e.g. `.supplemental-metadata(1).json`).
- **EXIF timestamp resolution** — for JPEG files, reads `DateTimeOriginal` from the file's own EXIF header and uses it as the creation time when available. Falls back to the JSON `photoTakenTime` if no EXIF data exists.
- **Timestamp validation** — ensures creation time is never later than modification time. If EXIF data contradicts the JSON, the parser falls back through JSON `photoTakenTime` and, if still invalid, clamps creation to match modification.
- **Device metadata** — extracts camera/phone make and model from EXIF (`Make` / `Model` tags).
- **Source columns** — the dry-run table and TUI show where each timestamp came from (`EXIF`, `JSON`, or `—`).
- **Dual interface** — rich Textual TUI (default) or classic CLI (`--cli`).
- **Pure Python** — uses only the standard library for media processing. The Textual TUI requires `textual >= 6.6.0`, but the core library is dependency-free.

---

## Quick start

```bash
# Install
pip install takeout-metadata-writer

# Preview what would change (no files touched)
takeout-meta-writer /path/to/Takeout --dry-run

# Apply timestamps
takeout-meta-writer /path/to/Takeout
```

### Run from source

```bash
git clone https://github.com/leriqueg/takeout-metadata-writer.git
cd takeout-metadata-writer

# Install runtime dependency (Textual TUI)
pip install textual>=6.6.0

# Preview
python -m takeout_metadata_writer /path/to/Takeout --dry-run

# Apply
python -m takeout_metadata_writer /path/to/Takeout
```

---

## Usage

### CLI mode

Use the `--cli` flag to get a terminal table instead of the TUI:

```bash
# Preview with source columns
python -m takeout_metadata_writer --cli /path/to/Takeout --dry-run

# Apply timestamps
python -m takeout_metadata_writer --cli /path/to/Takeout
```

The dry-run table shows eight columns:

| Column           | Description                                     |
|------------------|-------------------------------------------------|
| File             | Media file name                                 |
| Current Created  | File system creation time (before change)       |
| Current Modified | File system modification time (before change)   |
| Target Created   | Resolved creation timestamp to apply            |
| Created From     | Source of the creation time — `EXIF`, `JSON`, `—` |
| Target Modified  | Resolved modification timestamp to apply        |
| Modified From    | Source of the modification time — `JSON` or `—`   |
| Status           | `UPDATE`, `ERROR`, or skip reason               |

### TUI mode (default)

Running without `--cli` launches the Textual interface:

1. **Path input** — type or browse to your Takeout folder, then press **Scan**.
2. **Results** — a scrollable table with all files and their proposed changes.
3. **Confirm** — review and confirm before writing.
4. **Summary** — final counts of updated / skipped / errored files.

> **Note**: if Textual is not installed or the terminal doesn't support it, the app falls back to CLI mode with an error message.

### Timestamp resolution logic

```
For each media file:

  1. Read EXIF DateTimeOriginal    (JPEG / HEIF only)
  2. Match companion .supplemental-metadata.json
  3. Read JSON photoTakenTime & creationTime
  4. Resolve creation time:
       EXIF DateTimeOriginal  → creation_time  (source: EXIF)
       JSON photoTakenTime    → creation_time  (source: JSON)
       neither                 → creation_time  (source: —)
  5. Resolve modification time:
       JSON creationTime      → modification_time
  6. Validate: creation ≤ modification
       If creation > modification:
         EXIF source → fall back to JSON photoTakenTime
         still invalid → clamp creation = modification
  7. Apply stat(2) changes (write mode only)
```

---

## Expected file layout

```
Takeout/
├── Google Photos/
│   ├── 2007/
│   │   ├── DSC01449.JPG
│   │   ├── DSC01449.JPG.supplemental-metadata.json
│   │   ├── VID_20210101_123456.mp4
│   │   └── VID_20210101_123456.mp4.supplemental-metadata.json
│   └── ...
└── ...
```

The tool recognises these media extensions: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.mp4`, `.mov`, `.avi`, `.mkv`, `.heic`, `.heif`, `.3gp`.

---

## Stack

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Runtime      | **Python ≥ 3.10**                            |
| Core lib     | Standard library only (`pathlib`, `struct`, `json`, `datetime`, `os`, `stat`) |
| EXIF parsing | Pure Python (`struct` + `datetime`) — no Pillow needed |
| TUI          | **Textual** ≥ 6.6.0                         |
| Distribution | `setuptools` + `pyproject.toml`             |

---

## License

MIT
