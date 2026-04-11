# Logging and Diagnostics Specification

## Status
- Draft

## Problem Statement
The app currently writes only `opcua_tui.*` logs to a rotating file. It does not explicitly capture third-party OPC UA client logs (for example `asyncua.*`) or Textual framework logs in the same logging pipeline, and there is no in-app log viewer.

## Goals
- Capture application logs, OPC UA client logs, and Textual logs in a unified logging pipeline.
- Keep file logging as the durable source of truth.
- Provide optional forwarding to Textual devtools console during development.
- Make logs reachable from the UI without placing them on the primary browser layout.
- Keep behavior configurable via environment variables (and optionally CLI flags later).

## Non-Goals
- Full observability stack (no external log shipping in this phase).
- Persisted user preferences UI for logging settings.
- Replacing Textual devtools itself.

## Reference
- Textual Devtools Guide: https://textual.textualize.io/guide/devtools/
- Textual logging handler API: https://textual.textualize.io/api/logging/

## Proposed Architecture

### 1) Logging Pipeline
Use Python `logging` as the single pipeline with three sinks:
- Rotating file sink (existing, retained).
- In-memory ring buffer sink for in-app log viewer.
- Optional `TextualHandler` sink for devtools console integration.

#### Logger capture scope
Capture these logger trees:
- `opcua_tui.*`
- `asyncua.*` (and optionally `opcua.*` for compatibility with library variants)
- `textual.*`

Implementation detail:
- Configure handlers on the root logger.
- Set root level from `OPCUA_TUI_LOG_LEVEL`.
- Set namespace-specific overrides for noisy domains with dedicated env vars.
- Keep structured context fields (`operation`, `error_ref`) with safe defaults.

### 2) Handler Set
- `RotatingFileHandler`: durable logs, existing rotation policy retained.
- `InMemoryLogHandler` (new): stores last N formatted records for UI retrieval.
- `TextualHandler` (optional): enabled only when configured, to route stdlib logging into Textual devtools console when app is active.

`TextualHandler` behavior (from docs):
- With active Textual app: writes to devtools console.
- Without active app: falls back to stderr/stdout based on constructor flags.

### 3) Configuration Surface
Environment variables:
- `OPCUA_TUI_LOG_LEVEL` (default `INFO`)
- `OPCUA_TUI_LOG_DIR` (existing)
- `OPCUA_TUI_LOG_FILE_MAX_BYTES` (default `2000000`)
- `OPCUA_TUI_LOG_FILE_BACKUP_COUNT` (default `5`)
- `OPCUA_TUI_LOG_BUFFER_SIZE` (default `2000` lines)
- `OPCUA_TUI_LOG_TEXTUAL_HANDLER` (`0|1`, default `0`)
- `OPCUA_TUI_LOG_TEXTUAL_STDERR` (`0|1`, default `1`)
- `OPCUA_TUI_LOG_TEXTUAL_STDOUT` (`0|1`, default `0`)
- `OPCUA_TUI_LOG_LEVEL_ASYNCUA` (optional override)
- `OPCUA_TUI_LOG_LEVEL_TEXTUAL` (optional override)

Validation rules:
- Invalid levels fallback to `INFO` (consistent with current behavior).
- Invalid numeric settings fallback to defaults.
- Buffer size minimum `100`.

### 4) UI Access Pattern (Not on Main Page)
Add a dedicated `LogViewerScreen` (new screen, pushed on demand):
- Accessible via key binding from `BrowserScreen` (proposal: `ctrl+l`).
- Optional command palette action `Show Logs`.
- Not embedded in main browser screen layout.

`LogViewerScreen` contents:
- `Log` or `RichLog` widget with tail-follow mode.
- Header row with current filter/level and source summary.
- Controls:
  - `f`: toggle follow tail
  - `c`: clear in-memory view (does not delete file)
  - `/`: focus filter input (text match)
  - `l`: cycle minimum level (DEBUG/INFO/WARNING/ERROR)
  - `o`: open log file path hint (display only in phase 1)
  - `escape`/`q`: close screen

Behavior:
- On open: load recent in-memory records.
- While open: append new records live from in-memory bus/handler callbacks.
- On close: unsubscribe from live updates.

## Data Structures

### LoggingConfig (new dataclass)
Fields:
- `root_level: int`
- `asyncua_level: int | None`
- `textual_level: int | None`
- `log_dir: Path`
- `max_bytes: int`
- `backup_count: int`
- `buffer_size: int`
- `enable_textual_handler: bool`
- `textual_stderr: bool`
- `textual_stdout: bool`

### LogRecordView (new typed model)
UI-facing, immutable projection of a log entry:
- `timestamp`
- `level`
- `logger_name`
- `message`
- `operation`
- `error_ref`

## Module Changes
- `src/opcua_tui/infrastructure/logging_config.py`
  - Refactor into config parse + setup helpers.
  - Add handler setup for root and namespace levels.
  - Expose `get_log_buffer()` and `get_log_file_path()` accessors.
- `src/opcua_tui/ui/screens/log_viewer_screen.py` (new)
  - Screen implementation and key bindings.
- `src/opcua_tui/ui/screens/browser_screen.py`
  - Add binding/action to open `LogViewerScreen`.
- `src/opcua_tui/ui/textual_app.py`
  - Ensure log infrastructure initialized before screens are pushed.
- `src/opcua_tui/main.py`
  - Keep startup log, update to use new return object if setup signature changes.

## Test Plan

### Unit tests
- `tests/unit/infrastructure/test_logging_config.py`
  - Root logger contains expected handlers.
  - `asyncua` and `textual` logger levels honor overrides.
  - Textual handler inclusion toggles with env var.
  - In-memory handler respects max buffer size.
- `tests/unit/ui/screens/test_log_viewer_screen.py` (new)
  - Opens from browser action.
  - Renders initial buffered logs.
  - Appends live records.
  - Filters and level toggles work.

### Integration/UI checks
- Add screenshot harness mode:
  - `--screen logs` captures log viewer screen after seeding entries.
- Validate no regression for existing connect/browser captures.

## Rollout Phases
1. Logging backend refactor + env configuration parity.
2. In-memory handler and API for UI consumption.
3. `LogViewerScreen` and browser binding.
4. Optional devtools bridge (`TextualHandler`) toggle.
5. Tests + screenshot harness update.

## Acceptance Criteria
- Logs from `opcua_tui.*`, `asyncua.*`, and `textual.*` appear in rotating log file.
- When `OPCUA_TUI_LOG_TEXTUAL_HANDLER=1`, stdlib logs are visible in Textual devtools console during `textual run --dev`.
- User can open and close log viewer from UI with a dedicated action, without logs appearing on main browser layout.
- Buffer and log levels are configurable and validated.
- Existing logging tests still pass, with new tests covering added behavior.

## Open Questions
- Should file logs include JSON format option (`OPCUA_TUI_LOG_FORMAT=json`) now, or defer?
- Should `LogViewerScreen` allow exporting filtered lines in phase 1?
- Preferred default key for log viewer (`ctrl+l` vs `F8`) in terminal compatibility terms.
