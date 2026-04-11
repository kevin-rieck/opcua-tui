# OPC UA TUI

A Textual-based terminal UI for connecting to an OPC UA server, browsing the address space, inspecting node data, writing scalar values, and viewing runtime logs.

## How To (Quick Start)

```bash
uv sync --extra dev
uv run opcua-tui
```

1. Enter an endpoint in the connect modal (for local testing: `opc.tcp://localhost:48010`).
2. Choose security/auth options in the modal (or keep defaults for insecure anonymous).
3. Press `Enter` (or select `Connect`).
3. Browse the tree, select a node to inspect, and use the write panel to update values.
4. Press `Ctrl+L` to open the log viewer.

## Current State

- Real async OPC UA client is used (`asyncua`); this is not a stub-only flow anymore.
- App starts with a connect modal and connects only after user submit.
- Browser screen includes:
  - Address tree with lazy child loading
  - Inspector panel (attributes + value + status code)
  - Write value panel
  - Status bar + footer
- Log viewer screen is available in-app (`Ctrl+L`) with filter and level controls.
- State is driven via store/reducer/effects (`UI event -> message -> effect -> state -> render`).

## Current Limitations

- Connect UI currently supports only insecure anonymous connections.
- Endpoint must start with `opc.tcp://`.
- Server-certificate trust management UI is not yet implemented (manual trust/retry flow).
- Certificate user identity auth is not yet implemented (username/password is supported).

## Connect Modal (Secure)

The connect modal supports secure channel and authentication choices:

- `Endpoint`: OPC UA endpoint URL, for example `opc.tcp://localhost:48010`
- `Security Mode`: `None`, `Sign`, `SignAndEncrypt`
- `Security Policy`: `None`, `Basic256Sha256`, `Aes128Sha256RsaOaep`, `Aes256Sha256RsaPss` (plus legacy options)
- `Auth Mode`: `Anonymous` or `Username/Password`
- `Username` / `Password`: shown only for username auth
- `Client Certificate Path` / `Client Private Key Path`: optional overrides

If certificate/key paths are omitted for secure modes, the app auto-generates and reuses client material under:

- `~/.opcua-tui/pki/own/client_certificate.der`
- `~/.opcua-tui/pki/own/client_private_key.pem`

Validation rules:

- `Security Mode=None` requires `Security Policy=None`
- Secure modes require a non-`None` policy
- Username/password are required only for username auth
- Certificate and key override paths must be provided together

## Key Bindings

- Global:
  - `q`: quit
- Connect modal:
  - `Enter`: connect
  - `Esc`: cancel/exit
- Browser:
  - `w`: focus write input
  - `Ctrl+L`: open log viewer
- Log viewer:
  - `Esc` or `q`: back
  - `f`: toggle follow mode
  - `c`: clear current log view
  - `/`: focus filter input
  - `l`: cycle minimum level (`DEBUG`/`INFO`/`WARNING`/`ERROR`)

## Tooling

- `uv` for environment and dependency management
- `ruff` for linting and formatting
- `pytest` for tests
- `pre-commit` hooks for automated checks
- `Makefile` shortcuts for common tasks

## Development Commands

```bash
make sync
make run
make lint
make format
make test
make pre-commit-run
```

## Logging

- Default file output: `~/.opcua-tui/logs/opcua-tui.log` (rotating).
- In-memory ring buffer powers the in-app log viewer.
- Root logger capture includes `opcua_tui.*`, `asyncua.*`, and `textual.*`.
- Environment variables:
  - `OPCUA_TUI_LOG_DIR`
  - `OPCUA_TUI_LOG_LEVEL`
  - `OPCUA_TUI_LOG_FILE_MAX_BYTES`
  - `OPCUA_TUI_LOG_FILE_BACKUP_COUNT`
  - `OPCUA_TUI_LOG_BUFFER_SIZE`
  - `OPCUA_TUI_LOG_LEVEL_ASYNCUA`
  - `OPCUA_TUI_LOG_LEVEL_TEXTUAL`
  - `OPCUA_TUI_LOG_TEXTUAL_HANDLER=1`
  - `OPCUA_TUI_LOG_TEXTUAL_STDERR`
  - `OPCUA_TUI_LOG_TEXTUAL_STDOUT`

## Write Support

- Scalar write support with optional type hint from node metadata/value type.
- Supported scalar types:
  - `Boolean`
  - `SByte`, `Byte`
  - `Int16`, `UInt16`
  - `Int32`, `UInt32`
  - `Int64`, `UInt64`
  - `Float`, `Double`
  - `String`
- Integer ranges are validated by type.
- Without a hint, parsing fallback is: `bool -> int -> float -> string`.
- If server returns `BadWriteNotSupported`, client retries with value-only attribute write.

## Screenshot Harness (UI Debugging)

Script: `tools/capture_screenshot.py`

```bash
uv run .\tools\capture_screenshot.py
uv run .\tools\capture_screenshot.py --screen connect --output artifacts/screens/connect-modal-current.svg
uv run .\tools\capture_screenshot.py --screen browser --endpoint opc.tcp://localhost:48010 --output artifacts/screens/browser-post-connect.svg
uv run .\tools\capture_screenshot.py --screen logs --endpoint opc.tcp://localhost:48010 --output artifacts/screens/log-viewer-post-connect.svg
```
