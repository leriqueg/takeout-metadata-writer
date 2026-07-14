# Core Processor Specification

## Purpose

Recursively scan a Google Takeout directory, match media files to companion `supplemental-metadata.json`, and restore original timestamps (`photoTakenTime` → creation, `creationTime` → modification).

## Requirements

### Requirement: Directory Scanning

The system MUST recursively scan a directory and yield media files with extensions `jpg`, `jpeg`, `png`, `gif`, `webp`, `bmp`, `mp4`, `mov`, `avi`, `mkv`, `heic`, `heif`, `3gp`.

#### Scenario: Finds files in subdirectories

- GIVEN a directory with `photo.jpg` in `Photos/2024/`
- WHEN the scanner runs
- THEN `photo.jpg` is yielded

#### Scenario: Skips unsupported types, empty dir yields nothing

- GIVEN a directory with `.txt` and `.json` files, or an empty directory
- WHEN the scanner runs
- THEN no media files are yielded

### Requirement: JSON Companion Matching

For each media file, the system MUST locate `{filename}.{ext}.supplemental-metadata.json`.

#### Scenario: Companion found and paired

- GIVEN `photo.jpg` and `photo.jpg.supplemental-metadata.json`
- WHEN matching runs
- THEN the JSON is paired with the media file

#### Scenario: No companion skips with warning

- GIVEN `photo.jpg` with no companion JSON
- WHEN matching runs
- THEN a warning is emitted and the file is skipped

### Requirement: JSON Parsing

The system MUST extract `photoTakenTime.timestamp` and `creationTime.timestamp` as integers.

#### Scenario: Valid timestamps extracted

- GIVEN JSON with both keys as numeric strings
- WHEN parsed
- THEN both integers are returned

#### Scenario: Missing key or malformed JSON

- GIVEN JSON missing `photoTakenTime` or invalid content
- WHEN parsed
- THEN a warning is emitted and the file is skipped

### Requirement: Dry-Run Mode

With `--dry-run`, the system MUST display a table of file name, current timestamps, target timestamps, and diff status. The system MUST NOT modify any timestamps.

#### Scenario: Comparison table shown, no writes

- GIVEN matched files with differing timestamps
- WHEN running with `--dry-run`
- THEN a table is printed and no timestamps are modified

### Requirement: Write Mode — Windows

On Windows, the system MUST set creation time to `photoTakenTime` via `SetFileTime` and modification time to `creationTime` via `os.utime`.

#### Scenario: Both timestamps applied

- GIVEN a matched file on Windows
- WHEN write mode executes
- THEN creation time = `photoTakenTime` and mtime = `creationTime`

#### Scenario: SetFileTime failure caught

- GIVEN a file where `SetFileTime` fails
- WHEN write mode executes
- THEN the error is logged and processing continues

### Requirement: Write Mode — Unix

On Unix, the system MUST set modification time to `creationTime` via `os.utime`. The system SHOULD log a warning that creation time cannot be set.

#### Scenario: Mtime updated, ctime warning

- GIVEN a matched file on Unix
- WHEN write mode executes
- THEN mtime = `creationTime`, ctime is unchanged, and a warning is logged

### Requirement: Per-File Error Isolation

The system MUST catch errors per file. A single failure MUST NOT abort the run.

#### Scenario: Error on one file does not stop others

- GIVEN 10 files where the 5th has a parse error
- WHEN processing runs
- THEN files 1–4 and 6–10 are handled; the 5th is skipped with logged error

#### Scenario: Permission error handled

- GIVEN a file without read permission
- WHEN processing runs
- THEN `PermissionError` is caught, logged, and processing continues

### Requirement: CLI Path Argument

The system SHALL accept a directory path as a positional argument.

#### Scenario: Valid path scanned

- GIVEN a valid directory path
- WHEN the CLI runs
- THEN that directory is scanned

#### Scenario: Invalid path rejected

- GIVEN a non-existent path
- WHEN the CLI runs
- THEN an error is displayed and the program exits with non-zero code
