# OPC UA TUI

A terminal UI for connecting to OPC UA servers, browsing the address space, and inspecting node values.

## Vision
This project aims to become a practical, extensible TUI for engineers working with OPC UA systems.

The first version focuses on:
- connecting to a server
- browsing the address space lazily
- selecting a node
- displaying metadata and current value
- preparing the foundation for subscriptions and later features

## Architectural direction
The project uses:
- **Textual** for the terminal UI
- **MVU-style state management** for predictable updates
- **ports and adapters** to isolate OPC UA access and persistence
- **typed domain models** for clarity and maintainability

## Why this shape
This app is event-driven and async by nature. Separating state transitions from IO makes it easier to test, easier to reason about, and easier to extend.

## Planned MVP
- connect to OPC UA server
- disconnect cleanly
- browse root and child nodes lazily
- inspect node attributes
- inspect current node value
- save recent endpoints
- show operational errors clearly

## Project layout

```text
src/opcua_tui/
  app/             # store, reducer, messages, effects
  application/     # use cases and ports
  domain/          # shared models and enums
  infrastructure/  # adapters for opcua, persistence, logging
  ui/              # textual app, screens, widgets
```

## Development rules
- reducers must stay pure
- UI code must not call OPC UA directly
- effects handle async work
- adapters implement ports
- new features should add typed messages and tests

## Suggested getting started steps
1. Create the package skeleton.
2. Implement state, messages, reducer, and store.
3. Add a stub OPC UA adapter.
4. Build a minimal Textual layout.
5. Wire connect and root browse flow.
6. Add node inspection.
7. Replace the stub adapter with a real asyncua adapter.

## Near-term roadmap
- subscriptions and watchlist
- reconnect flow
- profile persistence
- richer diagnostics
- writes and method calls later

## Contribution guidance
When adding features:
- keep changes localized to the appropriate layer
- prefer simple, explicit names
- update docs and the implementation checklist
- add tests for reducer and effect behavior

## Status
This repository is currently in early architecture and implementation planning.
