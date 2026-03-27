# OPC UA TUI Starter

A runnable starter project for a terminal UI focused on OPC UA workflows.

## Included

- Textual application shell
- Left-hand address tree
- Right-hand node details panel
- Bottom status bar
- Central store, reducer, and effects
- Stub OPC UA adapter for local development
- End-to-end flow from UI event -> message -> effect -> state update -> UI render

## Tooling

- `uv` for environment and dependency management
- `ruff` for linting and formatting
- `pre-commit` hooks for automated checks
- `Makefile` shortcuts for common tasks

## Run

```bash
uv sync --extra dev
uv run opcua-tui
```

## Common commands

```bash
make lint
make format
make test
make pre-commit-run
```

## Logging

- Runtime logs are written to a rotating file at `~/.opcua-tui/logs/opcua-tui.log` by default.
- Set `OPCUA_TUI_LOG_DIR` to override the log directory.
- Set `OPCUA_TUI_LOG_LEVEL` to control verbosity (`INFO` by default, `DEBUG` for deep diagnostics).

## Current flow

- The app auto-connects to a stub server on startup.
- Root nodes are loaded into the tree.
- Selecting a node dispatches `NodeSelected`.
- Effects read attributes and value from the stub adapter.
- State updates drive the details panel and status bar.
- Expanding a node lazily loads children once.
