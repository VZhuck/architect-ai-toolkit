## ADDED Requirements

### Requirement: Meeting note input resolution
The skill SHALL accept an optional `meetingFilePath` argument identifying the meeting note to summarize. When `meetingFilePath` is not provided, the skill SHALL read `MEETING_NOTES_FOLDER` from `.env`, list the files found in that folder, and ask the user to pick one. The skill SHALL NOT auto-select a file (e.g. by most-recent-modified) and SHALL NOT maintain a freshness/sync-log of previously processed meeting notes.

#### Scenario: Explicit meeting file path given
- **WHEN** the caller invokes the skill with a `meetingFilePath` pointing to an existing file
- **THEN** the skill uses that file directly and does not consult `MEETING_NOTES_FOLDER`

#### Scenario: No path given, folder configured
- **WHEN** the caller omits `meetingFilePath` and `.env` defines `MEETING_NOTES_FOLDER` pointing to an existing directory
- **THEN** the skill lists the files in that directory and asks the user to pick one before proceeding

#### Scenario: No path given, no folder configured
- **WHEN** the caller omits `meetingFilePath` and `.env` has no `MEETING_NOTES_FOLDER` value (or it points to a non-existent directory)
- **THEN** the skill stops and reports a clear error that no meeting note could be resolved, rather than guessing

#### Scenario: Explicit path does not exist
- **WHEN** the caller supplies a `meetingFilePath` that does not exist on disk
- **THEN** the skill stops and reports a clear error naming the missing path, without falling back to `MEETING_NOTES_FOLDER`

### Requirement: ADL path resolution
The skill SHALL accept an optional `adlPath` argument identifying the Architecture Decision Log file to update. When `adlPath` is not provided, the skill SHALL fall back to the `ADL_PATH` value in `.env`. If neither resolves to a usable path, the skill SHALL stop and report a clear error.

#### Scenario: Explicit ADL path given
- **WHEN** the caller invokes the skill with an `adlPath` argument
- **THEN** the skill uses that path and does not consult `.env`'s `ADL_PATH`

#### Scenario: No ADL path given, .env provides one
- **WHEN** the caller omits `adlPath` and `.env` defines `ADL_PATH`
- **THEN** the skill uses the `.env` value as the ADL path

#### Scenario: ADL file does not yet exist
- **WHEN** the resolved ADL path (from either source) does not point to an existing file
- **THEN** the skill creates it with a markdown title and a decisions table header (`Area | Problem | Decision | Date | Approvers`) before appending any rows

#### Scenario: No ADL path resolvable
- **WHEN** the caller omits `adlPath` and `.env` has no `ADL_PATH` value
- **THEN** the skill stops and reports a clear error rather than guessing a location

### Requirement: Technical decision extraction
The skill SHALL analyze the resolved meeting note and extract only technical decisions (excluding open questions, action items, and status updates) into a markdown table with columns `Area`, `Problem`, `Decision`, `Date`, `Approvers`. When a topic is revisited multiple times in the note, the skill SHALL treat the last occurrence as the final decision, which may itself be "needs further discussion." Any of `Decision`, `Date`, or `Approvers` that cannot be identified SHALL be rendered as `TBD`.

#### Scenario: Meeting contains technical decisions
- **WHEN** the meeting note contains one or more identifiable technical decisions
- **THEN** the skill produces a markdown table with one row per decision, using `TBD` for any field it cannot determine

#### Scenario: Topic revisited multiple times
- **WHEN** the same technical topic is discussed and decided more than once in the note
- **THEN** the extracted row reflects only the last (final) decision for that topic

#### Scenario: No technical decisions present
- **WHEN** the meeting note contains no identifiable technical decisions
- **THEN** the skill returns an empty result and explicitly states that none were identified, without proceeding to the duplicate-check or confirmation steps

### Requirement: Semantic duplicate detection against existing ADL content
Before asking the user which decisions to log, the skill SHALL read the ADL file's existing decisions table (if any) and compare each candidate row against existing rows using semantic judgment of whether they describe the same decision — not exact string equality — since ADL rows may originate from manual edits worded differently than the skill's own extraction. The skill SHALL surface any rows it judges to be likely duplicates to the user alongside the candidate list.

#### Scenario: Candidate matches an existing row in substance but not wording
- **WHEN** a candidate decision describes the same Area/Problem/Decision as an existing ADL row using different phrasing
- **THEN** the skill flags the candidate as a likely duplicate of that existing row when presenting choices to the user

#### Scenario: No existing ADL content to compare against
- **WHEN** the ADL file is newly created or has no existing decisions table
- **THEN** the skill presents all candidates with no duplicate flags

### Requirement: Required user confirmation before logging
The skill SHALL present extracted decisions as a numbered list and markdown table (including any duplicate flags) and ask the user which decision numbers to add to the ADL. The skill SHALL accept comma-separated indexes or `all`, and SHALL re-prompt once with the valid options if the user supplies invalid indexes. The skill SHALL NOT write to the ADL file without this confirmation.

#### Scenario: User selects a subset
- **WHEN** the user responds with comma-separated indexes referring to a subset of the extracted decisions
- **THEN** only those decisions are appended to the ADL file

#### Scenario: User selects all
- **WHEN** the user responds with `all`
- **THEN** every extracted decision is appended to the ADL file

#### Scenario: User supplies invalid indexes
- **WHEN** the user's response contains an index outside the valid range or unparseable input
- **THEN** the skill asks once more, listing the valid index range, before proceeding

### Requirement: ADL update mechanics
A script SHALL perform the ADL file write: appending only the user-confirmed rows to the existing decisions table (or creating a `## Decisions` section if none exists), preserving existing ADL content and formatting style, and leaving the resulting table valid markdown. This script SHALL NOT perform any duplicate comparison — duplicate judgment SHALL already have occurred in the skill's semantic-comparison and user-confirmation steps.

#### Scenario: Appending to an existing decisions table
- **WHEN** the ADL file already has a decisions table under a recognizable section
- **THEN** confirmed rows are appended to that table without altering existing rows

#### Scenario: ADL file has no decisions section yet
- **WHEN** the ADL file exists but has no decisions table
- **THEN** the script creates a `## Decisions` section with the standard table header before appending the confirmed rows

#### Scenario: Write failure
- **WHEN** the ADL file cannot be written (e.g. permissions error, invalid path)
- **THEN** the skill reports a clear error rather than silently discarding the user's confirmed selections

### Requirement: Result reporting
After updating the ADL, the skill SHALL report back to the caller: the full extracted decisions table, which decision numbers were selected, and an update summary consisting of the added count, the count skipped due to the user's own choice not to log them, and the final ADL path.

#### Scenario: Successful update
- **WHEN** the skill completes an ADL update with at least one confirmed row
- **THEN** it reports the extracted table, the selected indexes, the added count, and the resolved ADL path
