# tui-textual Specification

## Purpose

Rich Textual TUI that replaces the default CLI entry point. Provides interactive directory browsing, sortable dry-run preview, confirmation dialog, and final summary — all without remembering flags.

## Requirements

### Requirement: Path Input

The system MUST provide an interactive path input screen with an `Input` widget, a `DirectoryTree` folder browser, and a "Scan" button that validates the path before transitioning.

#### Scenario: Select and scan a valid directory

- GIVEN the app launches without `--cli`
- WHEN the PathInputScreen is displayed
- THEN the user MUST be able to type or browse to a directory
- AND click "Scan" to validate and proceed

#### Scenario: Invalid path shows error

- GIVEN the user enters a path that does not exist
- WHEN "Scan" is clicked
- THEN the system MUST display an error message
- AND MUST NOT transition to ResultsScreen

#### Scenario: Empty directory scan

- GIVEN the user selects a valid directory with no media files
- WHEN "Scan" is clicked
- THEN the system MUST show "No media files found."
- AND MUST NOT transition to ResultsScreen

### Requirement: Results Display

The system MUST display scan results in a `DataTable` with columns: File, Current Created, Current Modified, Target Created, Target Modified, Status. Results MUST be sortable by any column, and a loading indicator MUST appear during scanning.

#### Scenario: Sort by column header

- GIVEN the DataTable is populated with results
- WHEN the user clicks a column header
- THEN the table MUST sort ascending by that column
- AND a second click on the same header MUST sort descending

#### Scenario: Back button returns to path input

- GIVEN the user is on the ResultsScreen
- WHEN the "Back" button is clicked
- THEN the system MUST return to PathInputScreen

#### Scenario: Loading indicator during scan

- GIVEN the user clicks "Scan" on a valid directory
- WHEN processing begins
- THEN the system MUST show a loading indicator
- AND use `@work(thread=True)` to call blocking core functions

### Requirement: Write Confirmation

The system MUST show a ConfirmModal dialog with "Write timestamps to N files?" and Yes/No buttons before writing.

#### Scenario: Confirm write

- GIVEN the ConfirmModal is displayed
- WHEN the user clicks "Yes"
- THEN the system MUST write timestamps to all files
- AND transition to SummaryScreen

#### Scenario: Cancel write

- GIVEN the ConfirmModal is displayed
- WHEN the user clicks "No"
- THEN the system MUST return to ResultsScreen
- AND MUST NOT write any files

### Requirement: Summary Display

The system MUST show a SummaryScreen with counts of updated, skipped, and errored files, plus "Back to start" and "Quit" buttons.

#### Scenario: Back to start

- GIVEN the SummaryScreen is displayed
- WHEN the user clicks "Back to start"
- THEN the system MUST return to PathInputScreen

#### Scenario: Quit application

- GIVEN the SummaryScreen is displayed
- WHEN the user clicks "Quit"
- THEN the application MUST exit

### Requirement: CLI Fallback

The system MUST support a `--cli` flag that preserves the existing argparse CLI behavior from `cli.main()`.

#### Scenario: --cli flag bypasses TUI

- GIVEN the user passes `--cli /path/to/dir` and optional `--dry-run`
- WHEN the application starts
- THEN the system MUST bypass the Textual app entirely
- AND run the existing CLI pipeline from `cli.main()`

### Requirement: Terminal Detection

The system SHOULD detect legacy terminals (e.g., cmd.exe) and display an error directing the user to use `--cli`.

#### Scenario: Legacy terminal error

- GIVEN the user runs the app in cmd.exe or another legacy terminal
- WHEN the app starts without `--cli`
- THEN the system SHOULD display an error: "Textual TUI requires Windows Terminal. Use --cli for legacy terminal support."
- AND exit with a non-zero exit code
