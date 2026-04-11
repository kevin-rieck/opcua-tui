# Architecture Review: Current Repo vs Posting

Date: April 11, 2026

## Scope
This review evaluates whether the current `store/reducer/effects` architecture is a good fit for this repository, using `darrenburns/posting` as a Textual reference implementation.

## Findings

### 1) The current architecture works, but is over-structured for current app size
Observed flow:
- UI dispatches global messages to `Store`
- `Store` runs reducer and all subscribers
- `Effects` then run and dispatch additional messages
- Screens manually map global state to widgets

This is internally consistent, but adds significant indirection for a two-screen app.

### 2) Rendering complexity is higher than necessary
In [`browser_screen.py`](../src/opcua_tui/ui/screens/browser_screen.py), rendering is managed by:
- keeping `_last_rendered_state`
- diffing tree-related slices manually
- suppressing events while patching widget state

This is exactly the type of plumbing Textual `reactive`, `watch_*`, and local widget messages are designed to avoid.

### 3) Reducer cost and coupling will grow quickly
In [`reducer.py`](../src/opcua_tui/app/reducer.py), each dispatch deep-copies the full `AppState` before matching message branches.

Costs:
- unnecessary copy overhead as state grows
- many lifecycle/result message variants needed for each async operation
- UI concerns leak into global reducer (for example status strings and modal flags)

### 4) Two event systems are running in parallel
Current app has:
- Textual event/message system (widget events)
- custom global message bus (`Store` messages)

Posting uses Textual as the primary event system and avoids layering a second full runtime bus.

### 5) Strong parts should be preserved
Do not discard:
- domain models in `domain/models.py`
- adapter boundary in `application/ports/opcua_client.py`
- explicit operation error references in effects/logging
- lazy browse behavior

## Posting patterns relevant here
From Posting's architecture and code:
- Screen and widget composition is local and explicit.
- Cross-widget communication is done with typed Textual `Message` classes.
- State transitions are mostly widget/screen reactive state updates.
- Async actions are handled with `@work` jobs owned by the screen/app.
- CSS classes are toggled directly by state changes.
- Snapshot tests validate full UI flows with deterministic terminal sizing.

These patterns reduce ceremony while preserving good boundaries.

## Recommendation

### Keep
- Ports and adapters (clean separation for OPC UA implementation).
- Domain model typing.
- Error reference logging.

### Change
- Replace global `Store + reducer + effects` runtime path with Textual-first controllers.
- Keep state local to screens unless truly shared.
- Use Textual messages between widgets/screens.
- Run connect/browse/inspect tasks in screen/app worker methods (`@work`).

### Remove after migration
- `app/store.py`
- `app/reducer.py`
- most of `app/messages.py`
- `app/effects.py`

## Proposed target flow

1. Widget emits typed Textual message (intent).
2. Screen handles event (`@on`) and updates local reactive state.
3. Screen starts async worker (`@work`) for OPC UA call.
4. Worker updates reactive state on start/success/failure.
5. `watch_*` handlers update widgets/CSS and status text.

This keeps the same UX behavior with fewer moving parts.

## Incremental migration plan

1. Connect flow first:
- move `ConnectModalScreen` to local reactive state and local async connect worker
- call `OpcUaClientPort` directly via injected service/controller

2. Browser flow second:
- move root browse and child load logic into `BrowserScreen` workers
- remove global state diffing and `_last_rendered_state`

3. Inspector flow third:
- keep parallel attribute/value reads using `asyncio.gather`
- set loading/error/value directly on local state

4. Cleanup:
- remove store/reducer/effects once all flows are migrated
- simplify app bootstrap and screen constructors

5. Tests:
- add snapshot tests around connect modal and browser interactions
- keep integration tests against local server

## Risks and mitigations

- Risk: losing deterministic state transitions from reducer
  - Mitigation: define small feature-state dataclasses and pure helper functions for non-trivial transforms.

- Risk: async race conditions (rapid node selection)
  - Mitigation: use `@work(exclusive=True, group="inspect-node")` and compare selected node before applying late results.

- Risk: harder global introspection
  - Mitigation: keep structured logging with operation names and error refs.

## Bottom line
The reducer/effects design is not wrong, but for this Textual app it is currently more complexity than value. A Textual-first controller architecture is the better fit now, while keeping ports/domain boundaries unchanged.
