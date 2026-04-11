# Secure Connections Specification

## Status
- Draft

## Problem Statement
The app currently connects in insecure anonymous mode only. It does not expose OPC UA security mode/policy, authentication choices, or certificate trust management. Secure connections commonly fail on first attempt because either:
- the server certificate is unknown/untrusted by the client, or
- the client certificate is unknown/untrusted by the server.

The app needs a clear, deterministic workflow for these first-attempt failures.

## Goals
- Support secure OPC UA channels in the connect flow (`Sign`, `SignAndEncrypt`) with explicit policy selection.
- Support v1 authentication modes: `anonymous` and `username/password`.
- Manage client certificate/key lifecycle with local persistence and auto-generation when missing.
- Implement explicit server certificate trust flow (prompt-and-pin / TOFU) with user-visible fingerprint and retry path.
- Surface structured, actionable connection errors for common OPC UA security status codes.

## Non-Goals
- User certificate identity authentication (`AuthenticationMode.CERTIFICATE`) in v1.
- Private key passphrase prompt/UI in v1.
- Automatic reconnect loops for trust-related failures.
- Enterprise PKI/GDS integration in v1.

## Reference
- OPC UA Part 6, Application Instance Certificates: https://reference.opcfoundation.org/Core/Part6/v104/docs/6.2.2
- OPC UA Part 4, Common StatusCodes: https://reference.opcfoundation.org/Core/Part4/v104/docs/7.34.2
- OPC UA Part 4, OpenSecureChannel: https://reference.opcfoundation.org/Core/Part4/v105/docs/5.6.2
- asyncua client security APIs: https://raw.githubusercontent.com/FreeOpcUa/opcua-asyncio/master/asyncua/client/client.py
- node-opcua certificate trust workflow: https://github.com/node-opcua/node-opcua/blob/master/packages/node-opcua-certificate-manager/source/certificate_manager.ts

## Proposed Architecture

### 1) Connect Form and Validation
Add fields to connect modal:
- Endpoint
- Security Mode: `None`, `Sign`, `SignAndEncrypt`
- Security Policy: `None`, `Basic256Sha256`, `Aes128Sha256RsaOaep`, `Aes256Sha256RsaPss` (legacy policies optional/advanced)
- Auth Mode: `Anonymous`, `Username/Password`
- Username/Password (shown only for username mode)
- Advanced optional overrides: client cert path, private key path

Validation:
- `mode=None` requires `policy=None`
- secure mode requires non-`None` policy
- username/password required only in username mode
- endpoint must be `opc.tcp://...`
- encrypted private keys fail with explicit "not supported in v1" message

### 2) PKI Storage and Certificate Lifecycle
Local PKI root:
- `~/.opcua-tui/pki`

Subfolders:
- `own/` for client cert+key
- `trusted/` for trusted server certs/issuers
- `rejected/` for rejected/unknown captures
- `issuers/` for issuer material when needed

Behavior:
- On secure connect, if cert/key paths are absent, load or generate persistent client cert/key.
- Reuse generated material across runs.
- Include client cert details (path, thumbprint) in trust-failure diagnostics so users can trust it server-side.

### 3) Secure Connect Execution
Adapter behavior for secure modes:
- Resolve asyncua security policy class from selected domain enum.
- Call `set_security(...)` before `connect()`.
- Apply user credentials for username mode.
- Query/validate endpoint supports requested mode+policy and fail with explicit alternatives if not.

### 4) Trust and First-Try Failure Flow
Server cert policy for v1: prompt-and-pin (manual trust).
- Unknown server certificate returns structured trust failure (maps to `BadCertificateUntrusted`).
- UI shows:
  - short reason
  - certificate fingerprint/thumbprint
  - local trust action hint/path
  - dedicated `Retry` action
- No automatic retry loop.

Client cert not yet trusted by server:
- On failure patterns consistent with server-side rejection (`BadSecurityChecksFailed` and related security errors), show actionable guidance:
  - trust/import client certificate on server
  - include local client cert path + fingerprint
  - retry manually after server-side change

### 5) Error Model and State Flow
Introduce structured connection error mapping in infrastructure/effects:
- `status_code` (when available)
- `category` (`trust`, `credentials`, `policy_mismatch`, `certificate`, `transport`, `unknown`)
- `message`
- optional metadata (`fingerprint`, `cert_path`, `endpoint_offers`)

Reducer/UI:
- preserve form values after failure
- render concise user-facing error and keep technical details in logs
- maintain existing error reference IDs for diagnostics

## Data Structures

### ConnectParams (existing, expanded usage)
Use existing fields end-to-end:
- `endpoint`
- `security_mode`
- `security_policy`
- `authentication_mode`
- `username`
- `password`
- `certificate_path`
- `private_key_path`

### ConnectionErrorView (new)
- `category: str`
- `status_code: str | None`
- `message: str`
- `error_ref: str | None`
- `fingerprint: str | None`
- `cert_path: str | None`
- `endpoint_offers: list[str]`

## Module Changes
- `src/opcua_tui/ui/screens/connect_modal_screen.py`
  - add security/auth inputs, conditional rendering, and validation
  - add trust-failure retry UX
- `src/opcua_tui/infrastructure/opcua/stub_client.py` (or renamed adapter module)
  - implement secure setup, cert loading/generation, trust validation, error classification
- `src/opcua_tui/app/effects.py`
  - preserve structured connect failures and metadata
- `src/opcua_tui/app/reducer.py`
  - keep params on failure and map structured errors to modal/state
- `src/opcua_tui/domain/models.py` / `domain/enums.py`
  - ensure policy/mode/auth enums map cleanly to asyncua options
- `README.md`
  - document secure connect usage, trust flow, and PKI location

## Test Plan

### Unit tests
- connect form validation matrix for mode/policy/auth combinations
- secure connect path invokes asyncua security setup correctly
- auto-generate client cert/key when missing; reuse when present
- unknown server cert produces trust failure metadata
- manual retry after trust decision succeeds
- username auth success/failure mapping
- policy mismatch error lists offered endpoint combinations

### Integration/UI checks
- screenshot harness captures:
  - secure connect form
  - trust-failure error state
  - successful post-trust connect state
- regression: insecure anonymous flow still works

## Rollout Phases
1. PKI service + certificate lifecycle.
2. Adapter secure-channel and endpoint/policy validation.
3. Connect modal security/auth UI and validation.
4. Structured error mapping + retry CTA.
5. Tests, docs, and screenshot harness updates.

## Acceptance Criteria
- User can establish secure OPC UA connections with selected mode/policy.
- Unknown/untrusted server cert does not silently pass; app provides fingerprinted trust guidance and manual retry.
- Missing client cert/key in secure mode is handled by deterministic auto-generation in `~/.opcua-tui/pki`.
- Username/password auth works over secure channel in v1.
- Existing insecure anonymous workflow remains functional.

## Open Questions
- Should legacy policies (`Basic128Rsa15`, `Basic256`) be hidden behind an explicit advanced toggle in v1?
- Should trust/reject certificate management UI (list + approve/reject) be added in a follow-up spec?

## Assumptions
- Existing spec style in `specs/logging-and-diagnostics.md` is the canonical template.
- v1 should prioritize deterministic behavior and clear operator guidance over auto-retry automation.
