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

## Architecture
Current architecture decision and rationale:
- [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- [`ARCHITECTURE_REVIEW.md`](./ARCHITECTURE_REVIEW.md)

Short version:
- keep domain models and ports/adapters
- prefer Textual-native `reactive` state + `@on` + `@work`
- phase out global `store/reducer/effects` runtime plumbing

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
  app/             # legacy store/reducer/effects (to be phased out)
  application/     # ports and use-case services
  domain/          # shared models and enums
  infrastructure/  # adapters for opcua, persistence, logging
  ui/              # textual app, screens, widgets
```

## Near-term roadmap
- migrate connect/browser/inspector flows to Textual-first controllers
- snapshot-test key UI flows
- subscriptions and watchlist
- reconnect flow
- profile persistence
- richer diagnostics
- writes and method calls later

## Contribution guidance
When adding features:
- keep UI free of direct OPC UA adapter calls
- preserve port boundaries
- prefer small typed state objects close to the owning screen
- update docs when architectural boundaries change
- add tests for behavior changes
