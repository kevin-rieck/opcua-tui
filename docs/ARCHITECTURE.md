# Architecture

## Decision (April 11, 2026)
Use a Textual-first architecture inspired by Posting:
- keep domain models and port boundaries
- keep async IO out of widgets
- drop the global Redux-style `store + reducer + effects` runtime path
- move orchestration to screen/app controllers using Textual messages, `@on`, `reactive`, and `@work`

This keeps separation of concerns without adding a second event system on top of Textual.

## Why this change

The current implementation is correct in principle, but the global MVU loop is high ceremony for current scope:
- every interaction goes through `dispatch -> reducer -> subscriber render -> effect -> dispatch`
- screens manually diff and re-render from snapshots
- reducer deep-copies full state for every message
- message count grows quickly for simple UI interactions

Posting demonstrates a simpler and more idiomatic Textual model:
- screen/widget-level state with `reactive` and `watch_*`
- typed widget messages for communication
- async tasks via `@work` with clear ownership
- CSS classes tied to state for styling

## Target shape

### Presentation (`ui/`)
- Screens own feature state (`connect`, `browser`, `inspector`) as `reactive` fields.
- Widgets emit explicit Textual messages upward.
- Screens handle events with `@on(...)` and call feature service/controller methods.
- Screens update only affected widgets directly; no global state diff loop.

### Application (`application/`)
- Keep ports and add use-case style services where needed.
- Services are called by screens/controllers, not by widgets.

### Domain (`domain/`)
- Keep typed models (`ConnectParams`, `NodeRef`, `NodeAttributes`, `DataValueView`, ...).
- Keep enums and value objects.

### Infrastructure (`infrastructure/`)
- Keep adapter implementations behind ports.
- No UI imports here.

## Rules

1. Widgets never call OPC UA directly.
2. Async operations run in screen/app workers (`@work`), not in reducers.
3. Use Textual messages for UI-to-UI communication, not global app messages.
4. Keep state local unless it must be shared across screens.
5. Use CSS classes for visual state (loading, error, connected, etc.).
6. Keep domain and adapter contracts stable and typed.

## Migration plan from current code

1. Keep current functionality; remove architecture churn first.
2. Replace `Store` subscriptions in `ConnectModalScreen` with local `reactive` state + `@work` for connect flow.
3. Replace `BrowserScreen.render_state` diff logic with reactive fields and targeted widget updates.
4. Move effect logic into screen-level controller methods (same behavior, fewer cross-dispatches).
5. Delete unused global reducer/effects/message paths once each screen is migrated.
6. Add/expand snapshot tests for connect and browse flows.

## What remains valid from the current design

- Ports/adapters separation
- Typed domain models
- Explicit error handling with operation references
- Lazy browse approach

## What we are intentionally removing

- Global runtime event bus for UI interactions
- Deep-copy reducer updates for transient UI state
- Manual state snapshot diffing in screens

## Testing strategy

- Unit test application services and adapter mappers.
- Snapshot-test UI behavior with deterministic terminal sizes.
- Keep integration tests against local OPC UA server (`opc.tcp://localhost:48010`).
