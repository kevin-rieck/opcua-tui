# Node Subscriptions Specification

## Status
- Draft

## Problem Statement
The app currently supports browsing, inspecting, and writing node values, but it cannot monitor node value changes live. Operators need a deterministic way to subscribe to selected nodes, see which nodes are actively monitored, and view incoming updates in the main browser workflow.

## Goals
- Support v1 OPC UA data-change subscriptions for `AttributeIds.Value` on `Variable` nodes.
- Show active subscriptions and latest values in Browser UI.
- Make subscription state explicit per node (subscribing, active, unsubscribing, failed).
- Use one shared OPC UA subscription per session with multiple monitored items.
- Surface live updates via async callback flow (no polling loop).

## Non-Goals
- Event subscriptions / alarms in v1.
- Arbitrary attribute subscriptions beyond `Value` in v1.
- Advanced per-node tuning (sampling interval, queue size, deadband UI) in v1.

## Reference
- node-opcua examples under `.tmp/node-opcua/documentation`:
  - `sample_client_ts.ts`
  - `sample_client_async_await.js`
  - `creating_a_client_typescript.md`

## Proposed Architecture

### 1) Subscription Scope
- Only `Variable` nodes are subscribable.
- Subscription target is `AttributeIds.Value`.
- Duplicate subscribe requests for the same node are idempotent.
- Unsubscribe for non-subscribed nodes is idempotent.

### 2) Runtime Model
- On successful connection, start one shared asyncua subscription stream.
- Add one monitored item per subscribed node.
- Maintain `node_id -> monitored_item_handle` map in adapter.
- On disconnect/reconnect, delete shared subscription and clear tracked handles.

### 3) Value Rendering
- First-class scalar rendering for bool/int/float/string/date-time/bytes.
- Complex payloads (arrays/ExtensionObject/dicts) are rendered using compact safe fallback (`repr`, truncated when long).
- Keep raw callback value in domain update model for future enhancements.

### 4) UI Integration
- Add explicit subscribe/unsubscribe control for selected node in inspector area.
- Add watchlist panel to Browser screen to show active subscriptions and latest values.
- Mark subscribed nodes in address tree labels.
- Show per-node errors inline and global status updates in status bar.

## Data Structures
- `SubscriptionValueUpdate` (domain):
  - `node_id`, `value`, `rendered_value`, `variant_type`, `status_code`, `source_timestamp`, `server_timestamp`
- `SubscriptionItemState` (app state):
  - `node_id`, `display_name`, `active`, `last_value`, `variant_type`, `status_code`, `source_timestamp`, `update_count`, `error`
- `SubscriptionsState` (app state slice):
  - `items_by_node_id`, `subscribing`, `unsubscribing`

## Module Changes
- `application/ports/opcua_client.py`
  - Add methods: `start_subscription_stream`, `stop_subscription_stream`, `subscribe_value`, `unsubscribe_value`.
- `infrastructure/opcua/stub_client.py`
  - Implement shared asyncua subscription handler and monitored-item tracking.
  - Map asyncua callback data to `SubscriptionValueUpdate`.
- `app/messages.py`
  - Add subscribe/unsubscribe intent/lifecycle/update messages.
- `app/reducer.py`
  - Add `subscriptions` state transitions and live update handling.
- `app/effects.py`
  - Start stream after `ConnectionSucceeded`.
  - Handle subscribe/unsubscribe effects and callback dispatch.
- `ui/widgets/subscription_panel.py` (new)
  - Inspector action control for subscribe/unsubscribe.
- `ui/widgets/watchlist_panel.py` (new)
  - Live watchlist rendering.
- `ui/widgets/address_tree.py`
  - Add subscribed-node marker in labels.
- `ui/screens/browser_screen.py`
  - Compose and render subscription panel + watchlist panel.
  - Dispatch new subscribe/unsubscribe messages.

## Test Plan
- Unit tests:
  - reducer subscription lifecycle and connection-reset cleanup.
  - effects subscribe/unsubscribe flow and callback dispatch.
  - protocol surface updates in client port tests.
  - widget/screen tests for subscription panel, watchlist panel, and tree marker rendering.
- Infrastructure tests:
  - adapter stream lifecycle and monitored-item handle idempotency.
  - value rendering fallback behavior.
- Integration/UI verification:
  - Browser screen flow with selected Variable node, subscribe/unsubscribe action, and watchlist updates.

## Acceptance Criteria
- User can subscribe/unsubscribe selected `Variable` nodes from Browser inspector.
- Watchlist shows active nodes and latest live values.
- Address tree visually marks subscribed nodes.
- Live updates propagate from asyncua callbacks into app state/UI without polling.
- Disconnect/reconnect clears stale monitored-item state safely.

## Assumptions
- v1 keeps existing store/reducer/effects architecture.
- v1 prioritizes deterministic lifecycle handling over advanced monitoring controls.
