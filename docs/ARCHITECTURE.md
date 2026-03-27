# Architecture

## Goal
Build a terminal UI for OPC UA practitioners that is fast to extend, operationally reliable, and easy for humans and coding agents to work on in parallel.

The application should support:
- connecting to OPC UA servers
- browsing the address space lazily
- inspecting node metadata and values
- adding subscriptions for live updates
- growing into a broader engineering tool over time

## Architectural recommendation
Use **MVU (Model-View-Update)** at the UI boundary, combined with **ports and adapters / clean architecture** for the application core.

This is a better fit than classic MVC because:
- terminal UIs are event-driven
- async network work must be separated cleanly from rendering
- state transitions should be deterministic and easy to test
- future features should be added without coupling them to widget code

## Core principles

### 1. UI never talks to OPC UA directly
The UI dispatches intent messages. Effects or application services perform async work through an OPC UA client port.

### 2. Reducers stay pure
State transitions are deterministic and testable. No network, file, or timing logic belongs in reducers.

### 3. Infrastructure is replaceable
The real OPC UA adapter, a fake adapter for tests, and replay/demo adapters should all satisfy the same port interface.

### 4. Browse lazily
Address spaces can be extremely large. Never crawl the tree eagerly.

### 5. Metadata and values are separate concerns
Browsing, reading attributes, reading values, and subscribing are distinct operations and should remain separate in the design.

### 6. Design for extension from day one
Writes, method calls, history, alarms, event monitoring, export, and server-specific behavior should fit as feature modules rather than rewrites.

## Proposed layers

### Presentation layer
Responsibilities:
- terminal screens and widgets
- key bindings
- rendering current state
- dispatching user intent messages

Suggested technology:
- Textual for Python implementation

### Application layer
Responsibilities:
- message dispatch
- effect orchestration
- use cases
- coordination of ports and domain models

Examples:
- connect to server
- browse children of node
- inspect selected node
- subscribe to node value changes

### Domain layer
Responsibilities:
- application-neutral models
- value objects
- enums
- business rules
- shared errors

Examples:
- ConnectParams
- SessionInfo
- NodeRef
- NodeAttributes
- DataValueView
- SubscriptionHandle

### Infrastructure layer
Responsibilities:
- async OPC UA client adapter
- persistence adapters
- secret storage
- logging
- diagnostics

Examples:
- asyncua adapter
- SQLite settings repository
- OS keyring secret repository

## Suggested package structure

```text
src/opcua_tui/
  app/
    bootstrap.py
    store.py
    state.py
    reducer.py
    effects.py
    messages.py

  application/
    ports/
      opcua_client.py
      settings_repo.py
      secrets_repo.py
    use_cases/
      connect_server.py
      disconnect_server.py
      browse_node.py
      inspect_node.py
      subscribe_node.py

  domain/
    enums.py
    errors.py
    models.py

  infrastructure/
    opcua/
      asyncua_client.py
      mappers.py
    persistence/
      sqlite_settings.py
      keyring_secrets.py
    logging/
      setup.py

  ui/
    textual_app.py
    screens/
    widgets/
```

## State model
Keep one centralized state tree with feature slices.

```python
AppState
├── session
├── browser
├── inspector
├── watchlist
├── ui
└── logs
```

### Session slice
Tracks connection state, selected endpoint, server info, auth mode, and connection errors.

### Browser slice
Tracks root nodes, loaded children, expanded nodes, loading nodes, selected node, and filter text.

### Inspector slice
Tracks selected node details, attributes, value, loading state, and errors.

### Watchlist slice
Tracks active subscriptions and the latest values for monitored nodes.

### UI slice
Tracks active pane, transient notifications, and high-level navigation state.

## Message taxonomy
Messages should be explicit and typed.

### Intent messages
Originated by the user or UI.
- ConnectRequested
- DisconnectRequested
- RootBrowseRequested
- NodeExpandRequested
- NodeSelected
- NodeRefreshRequested
- SubscribeRequested
- UnsubscribeRequested

### Lifecycle messages
Indicate an operation has started.
- ConnectionStarted
- RootBrowseStarted
- ChildrenLoadStarted
- NodeInspectionStarted
- SubscriptionStarted

### Result messages
Carry successful or failed outcomes.
- ConnectionSucceeded
- ConnectionFailed
- RootBrowseSucceeded
- RootBrowseFailed
- ChildrenLoadSucceeded
- ChildrenLoadFailed
- NodeAttributesLoaded
- NodeValueLoaded
- NodeInspectionFailed
- SubscriptionSucceeded
- SubscriptionFailed

### Ambient/system messages
Produced by background activity.
- NodeValueUpdated
- DisconnectSucceeded
- UnexpectedError
- ToastRequested
- LogAppended

## Data flow
1. User interacts with widget.
2. Widget dispatches intent message.
3. Store applies reducer.
4. Effect handler reacts to message.
5. Effect calls application service or port.
6. Result is dispatched as a new message.
7. State updates.
8. UI re-renders from state.

## Key feature boundaries

### Session management
- endpoint selection
- security mode and policy
- credentials
- reconnect strategy
- server capability detection

### Address space browsing
- root browsing
- lazy child expansion
- namespace-aware node display
- filtering and breadcrumbing later

### Node inspection
- attributes
- current value
- timestamps
- status code
- data type
- access level

### Subscriptions
- monitored item creation
- live updates
- watchlist view
- unsubscribe support

### Persistence
- recent endpoints
- saved profiles
- layout preferences
- last selected nodes later

## Non-functional requirements
- async-safe
- deterministic state updates
- strong typing
- testable without a live server
- recover gracefully from disconnects
- support large address spaces

## Testing strategy

### Unit tests
- reducers
- domain mappers
- use cases
- reconnect logic

### Integration tests
- real adapter against a test OPC UA server
- connect/browse/read flows
- subscription flows

### UI tests
- state-driven widget tests
- smoke tests for main app flows

## Agentic development guidance
- keep files small and focused
- do not bypass ports from UI code
- do not place network logic in reducers
- prefer adding a new message over reusing a vague one
- document all new state slices and messages when introduced
- add tests for every new reducer path and effect path

## Extension roadmap
Planned future features should fit into the same architecture:
- write values
- call methods
- historical reads
- event monitoring
- alarms and conditions
- export to CSV or JSON
- plugin or feature registration model

## Definition of done for architectural compliance
A feature is architecturally complete when:
- the UI dispatches typed messages
- reducer changes are pure
- async work lives in effects or use cases
- infrastructure is accessed through a port
- tests cover success and failure paths
- docs are updated when messages or state change
