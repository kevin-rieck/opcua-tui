# Browser Loading Spinner Specification

## Status

In Progress

## Problem Statement

Browsing OPC UA nodes can take noticeable time due to network latency and per-node metadata reads. During this time, the UI may appear unresponsive even though work is in progress.

## Goals

- Provide immediate visual feedback while browse operations are in flight.
- Reuse existing app state and message flow (`browser.loading`) without introducing complex new state.
- Keep the first version simple and low-risk.
- Preserve a clean path for a later progress bar implementation.

## Non-Goals

- No determinate progress percentage in v1.
- No browse pipeline redesign in v1.
- No cancellation UX changes in v1.

## Reference

- `src/opcua_tui/domain/models.py` (`BrowserState.loading`)
- `src/opcua_tui/app/reducer.py` (`RootBrowseStarted`, `ChildrenLoadStarted`, and completion/failure transitions)
- `src/opcua_tui/ui/screens/browser_screen.py`
- `src/opcua_tui/ui/widgets/status_bar.py`

## Proposed Architecture

### 1) Loading Source of Truth

- Introduce a shared operation activity model in `UiState.activities`.
- Each in-flight server interaction is represented by `OperationActivity` (kind, label, scope, start time, optional progress).
- Existing feature-specific loading flags remain for local UI behavior (tree placeholders, panel disable rules).

### 2) Status Bar Spinner (v1)

- Extend `StatusBar` to render a Rich `Spinner` while operation activities are active.
- Follow Textual/Rich spinner rendering pattern (`render()` + periodic `refresh()`).
- UX smoothing:
  - spinner show delay (~200ms) to avoid flicker on fast operations
  - minimum visible duration (~400ms) to avoid blink-out
- Render format:
  - Idle: `<status text>`
  - Loading (single): `<spinner> <activity label>`
  - Loading (multiple): `<spinner> <activity label> (+N)`

### 3) Browser Screen Wiring

- `BrowserScreen.render_state` passes current activities into `StatusBar.render_status(...)`.

### 4) Existing Placeholder Preservation

- Keep address tree placeholder behavior unchanged for v1.
- Spinner complements existing local context; it does not replace it.

## Data Structures

- New app messages:
  - `OperationStarted`
  - `OperationFinished`
- New domain model:
  - `OperationActivity`
- Status bar keeps internal UI-only fields for delayed visibility/min duration.

## Module Changes

- `src/opcua_tui/ui/widgets/status_bar.py`
  - Add spinner state, interval tick handler, activity-aware rendering, and UX timing controls.
- `src/opcua_tui/ui/screens/browser_screen.py`
  - Provide activities when rendering status.
- `src/opcua_tui/app/messages.py`
  - Add operation lifecycle messages.
- `src/opcua_tui/app/effects.py`
  - Emit operation lifecycle messages for connect/browse/inspect/write/subscribe/unsubscribe.
- `src/opcua_tui/app/reducer.py`
  - Track active operations in `UiState.activities`.
- `src/opcua_tui/domain/models.py`
  - Add `OperationActivity` and `UiState.activities`.
- `tests/unit/ui/widgets/test_status_bar.py`
  - Add tests for loading render, spinner ticks, and non-loading behavior.
- `tests/unit/ui/screens/test_browser_screen.py`
  - Assert loading flags are forwarded to status bar.

## Test Plan

### Unit tests

- Status bar renders plain text when `is_loading=False`.
- Status bar shows spinner when activities exist (after delay).
- Spinner tick refreshes render while operation remains active.
- Browser screen passes activities into status rendering.
- Effects emit `OperationStarted` / `OperationFinished` around slow OPC UA interactions.

### Integration/UI checks

- Run screenshot harness after UI changes:
  - `uv run .\tools\capture_screenshot.py --screen browser --endpoint opc.tcp://localhost:48010 --output artifacts/screens/browser-loading-spinner.svg`

## Rollout Phases

1. Implement status bar spinner for browse loading.
2. Validate with unit tests and screenshot harness.
3. Evaluate progress bar follow-up based on browse instrumentation.

## Acceptance Criteria

- During slow OPC UA operations, status bar visibly animates with a spinner.
- Spinner stops when no activities are active (after minimum visible duration).
- Existing browse behavior and keyboard interactions remain unchanged.
- Unit tests covering spinner behavior pass.

## Future Extension (Progress Bar)

- Add optional browse progress events from infrastructure browse loops.
- Track `processed` and optional `total` per browse request.
- Render determinate bar when total is known, indeterminate otherwise.

## Assumptions

- Textual timer callbacks are sufficient for lightweight status-bar animation.
- `browser.loading` accurately reflects browse in-flight state across current flows.
