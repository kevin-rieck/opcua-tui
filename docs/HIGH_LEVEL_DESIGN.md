# High-Level Design

## System overview

```text
+-----------------------------------------------------------+
|                       Textual TUI                          |
|  +----------------+  +----------------+  +--------------+ |
|  | Address Tree   |  | Node Details   |  | Event Log    | |
|  | / Browser      |  | / Inspector    |  | / Status     | |
|  +----------------+  +----------------+  +--------------+ |
+------------------------------|----------------------------+
                               v
+-----------------------------------------------------------+
|                     App Store / Dispatcher                 |
|   State + Reducer + Message Dispatch + Store Subscribers  |
+------------------------------|----------------------------+
                               v
+-----------------------------------------------------------+
|                         Effect Layer                       |
|     Async orchestration for connect, browse, read, sub    |
+-----------------------+-------------------+---------------+
                        |                   |
                        v                   v
+------------------------------+   +------------------------+
|      Application Use Cases   |   |     Diagnostics        |
| connect / browse / inspect   |   | logging / telemetry    |
| subscribe / disconnect       |   | operational feedback   |
+------------------------------+   +------------------------+
                        |
                        v
+-----------------------------------------------------------+
|                      Port Interfaces                       |
|   OpcUaClientPort   SettingsRepoPort   SecretsRepoPort    |
+------------------------------|----------------------------+
                               v
+-----------------------------------------------------------+
|                    Infrastructure Adapters                |
| asyncua adapter | SQLite settings | keyring secrets       |
+------------------------------|----------------------------+
                               v
+-----------------------------------------------------------+
|                        OPC UA Server                       |
+-----------------------------------------------------------+
```

## Request / response flow

```text
User action
   |
   v
Widget emits intent message
   |
   v
Store dispatch(message)
   |
   +--> Reducer updates state immediately
   |
   +--> Effect handler reacts to message
              |
              v
      Use case / port call
              |
              v
       Infrastructure adapter
              |
              v
          OPC UA server
              |
              v
     Success or failure result
              |
              v
   Dispatch result message back to store
              |
              v
        Reducer updates state
              |
              v
        UI re-renders from state
```

## Main state slices

```text
AppState
|
+-- session
|    +-- status
|    +-- params
|    +-- session_info
|    +-- error
|
+-- browser
|    +-- roots
|    +-- children_by_parent
|    +-- expanded
|    +-- loading
|    +-- selected_node_id
|    +-- filter_text
|
+-- inspector
|    +-- node_id
|    +-- loading
|    +-- attributes
|    +-- value
|    +-- error
|
+-- watchlist
|    +-- handles_by_node_id
|    +-- latest_values
|
+-- ui
|    +-- active_pane
|    +-- toast
|
+-- logs
```

## Message categories

```text
Intent messages
  ConnectRequested
  DisconnectRequested
  RootBrowseRequested
  NodeExpandRequested
  NodeSelected
  NodeRefreshRequested
  SubscribeRequested
  UnsubscribeRequested

Lifecycle messages
  ConnectionStarted
  RootBrowseStarted
  ChildrenLoadStarted
  NodeInspectionStarted
  SubscriptionStarted

Result messages
  ConnectionSucceeded / ConnectionFailed
  RootBrowseSucceeded / RootBrowseFailed
  ChildrenLoadSucceeded / ChildrenLoadFailed
  NodeAttributesLoaded
  NodeValueLoaded
  NodeInspectionFailed
  SubscriptionSucceeded / SubscriptionFailed

Ambient messages
  NodeValueUpdated
  ToastRequested
  LogAppended
  UnexpectedError
```

## Package dependency direction

```text
ui  ----------------------->  app

app ----------------------->  application
app ----------------------->  domain

application --------------->  domain
application --------------->  ports

infrastructure ------------>  application ports
infrastructure ------------>  domain

ui must not import infrastructure directly for business operations.
reducers must not perform IO.
```

## Screen layout concept

```text
+-------------------------------------------------------------------+
| Connection / Status Bar                                            |
+---------------------------+---------------------------+-------------+
| Address Space Tree        | Selected Node Details     | Event Log   |
|                           |                           |             |
| - Objects                 | Display Name              | connect ok  |
| - Types                   | Node ID                   | browse ok   |
| - Views                   | Browse Name               | value read  |
|   - child                 | Node Class                | errors      |
|                           | Data Type                 | live updates|
|                           | Access Level              |             |
|                           | Current Value             |             |
|                           | Status / Timestamps       |             |
+---------------------------+---------------------------+-------------+
| Optional footer: shortcuts / mode hints                              |
+-------------------------------------------------------------------+
```

## Extension model

```text
Base architecture
   |
   +--> Session management
   +--> Browser
   +--> Inspector
   +--> Subscriptions
   |
   +--> Later features plug into same pattern
            |
            +--> Write values
            +--> Method calls
            +--> History reads
            +--> Events / alarms
            +--> Export
```

## Reliability considerations

```text
disconnect detected
      |
      v
set session status = reconnecting
      |
      v
retry policy / backoff
      |
      +--> success --> restore operational state where possible
      |
      +--> failure --> surface error and allow manual retry
```

## Agent guidance summary
- keep architecture boundaries intact
- extend by adding messages, reducer branches, effect paths, and adapter methods
- avoid hidden side effects
- favor explicit names over generic abstractions
- document state and message changes as they are introduced
