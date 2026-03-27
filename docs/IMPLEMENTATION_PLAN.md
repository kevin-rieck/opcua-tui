# Implementation Plan

## Phase 0 — Repository setup
- [ ] Create Python project scaffold
- [ ] Add `src/` layout
- [ ] Add package `opcua_tui`
- [ ] Add formatting and linting tools
- [ ] Add test framework and basic CI
- [ ] Add dependency management for Textual and async OPC UA client

## Phase 1 — Core architecture skeleton
- [ ] Create `domain/` models and enums
- [ ] Create `application/ports/` interfaces
- [ ] Create `app/state.py`
- [ ] Create `app/messages.py`
- [ ] Create `app/reducer.py`
- [ ] Create `app/store.py`
- [ ] Create `app/effects.py`
- [ ] Add bootstrap wiring
- [ ] Add first reducer tests

## Phase 2 — Initial infrastructure adapters
- [ ] Create stub OPC UA adapter for local development
- [ ] Create settings repository abstraction
- [ ] Add in-memory settings repository
- [ ] Add logging setup
- [ ] Add adapter mapper module boundaries

## Phase 3 — Minimal Textual shell
- [ ] Create `ui/textual_app.py`
- [ ] Create app shell layout
- [ ] Add status bar widget
- [ ] Add event log widget
- [ ] Add connect screen or panel
- [ ] Add browser pane placeholder
- [ ] Add inspector pane placeholder
- [ ] Wire store subscription to UI refresh

## Phase 4 — Connect flow
- [ ] Add `ConnectRequested` and related result messages
- [ ] Implement connect effect using stub adapter
- [ ] Add connect form widget
- [ ] Display connection state in UI
- [ ] Save recent endpoint on success
- [ ] Add disconnect flow
- [ ] Add success and failure tests for connect/disconnect

## Phase 5 — Address space browsing
- [ ] Add root browse messages
- [ ] Add child load messages
- [ ] Implement lazy browse effect
- [ ] Create address tree widget
- [ ] Render roots in tree
- [ ] Expand children on demand
- [ ] Track loading state per node
- [ ] Add tests for browser reducer paths

## Phase 6 — Node inspection
- [ ] Add node selection message
- [ ] Add node inspection messages
- [ ] Implement attribute and value reads
- [ ] Create node details widget
- [ ] Render attributes cleanly
- [ ] Render value, status code, and timestamps
- [ ] Add refresh action for selected node
- [ ] Add tests for inspect success and failure cases

## Phase 7 — Persistence basics
- [ ] Replace in-memory settings repo with SQLite repo
- [ ] Persist recent endpoints
- [ ] Load recent endpoints on startup
- [ ] Display recent endpoints in connect flow
- [ ] Add persistence tests

## Phase 8 — Real OPC UA integration
- [ ] Implement real asyncua adapter
- [ ] Map server metadata into domain models
- [ ] Map browse results into `NodeRef`
- [ ] Map attribute reads into `NodeAttributes`
- [ ] Map value reads into `DataValueView`
- [ ] Add integration tests against a test OPC UA server
- [ ] Validate behavior against large address spaces

## Phase 9 — Subscriptions
- [ ] Add subscribe and unsubscribe messages
- [ ] Implement subscription effect
- [ ] Add watchlist state slice behavior
- [ ] Add watchlist UI
- [ ] Surface live value updates
- [ ] Add tests for subscription lifecycle

## Phase 10 — Reliability and ergonomics
- [ ] Add reconnect strategy
- [ ] Add diagnostics and latency logging
- [ ] Improve error presentation
- [ ] Add keyboard shortcuts
- [ ] Add filtering in tree view
- [ ] Add empty/loading/error UI states

## Phase 11 — Developer quality bar
- [ ] Add architecture decision records if needed
- [ ] Document message naming conventions
- [ ] Document state slice responsibilities
- [ ] Add fixture-based demo mode
- [ ] Add screenshot or snapshot tests for key screens

## Later feature candidates
- [ ] Write values
- [ ] Method invocation
- [ ] Historical reads
- [ ] Event monitoring
- [ ] Alarms and conditions
- [ ] Export selected nodes or values
- [ ] Saved watchlists and profiles

## Done criteria for MVP
- [ ] User can connect to a server
- [ ] User can browse the address space lazily
- [ ] User can select a node and inspect its details
- [ ] User can view the current value of a node
- [ ] Recent endpoints are persisted
- [ ] Errors are visible and understandable
- [ ] Reducer, effects, and adapter paths have tests
