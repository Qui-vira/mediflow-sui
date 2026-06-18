# MediFlow-Sui

**Agentic healthcare case routing on Sui + Walrus.**
Sui Overflow 2026 - Agentic Web track.

MediFlow-Sui is a fork of MedBand, a human-in-the-loop healthcare workflow where
four AI agents (Coordinator, Intake, Verification, Resource) process a patient
service request and a human professional keeps final approval authority. The
original MedBand coordinates agents through **Band chat rooms** and records
workflow state in **Postgres**. MediFlow-Sui replaces that coordination and
audit layer with the **Sui blockchain** (a Move smart contract that emits an
event on every state change) and **Walrus decentralized storage** (which holds
the case records and per-stage agent payloads).

The result is a workflow whose audit trail is tamper-evident and verifiable by
anyone: every stage transition is an on-chain event, and every payload is a
content-addressed Walrus blob referenced from chain.

---

## Why this matters

Healthcare approvals need an audit trail that cannot be quietly edited after the
fact. In MedBand the trail lives in a private Postgres table controlled by the
operator. In MediFlow-Sui:

- Each stage write (`intake`, `verification`, `resource`) and each human
  decision (`approve` / `reject`) is an **on-chain event** with a signer address
  and timestamp.
- The bulky payload for each stage is stored in **Walrus**, and only its
  content-addressed **blob id** is written on-chain. The chain stays cheap; the
  data stays verifiable (same bytes -> same blob id).
- No AI agent can approve a case. Approval is a separate `approve_case`
  transaction signed by the human reviewer, and a decided case is immutable.

---

## Architecture

### The two modes

MediFlow-Sui keeps the entire original MedBand codebase intact and adds a single
toggle, `SUI_MODE`:

| | `SUI_MODE=false` (default) | `SUI_MODE=true` |
|---|---|---|
| Agent coordination | Band rooms (Phase 2) / direct calls (Phase 1) | same agents, same logic |
| Audit trail | in-memory `audit_log` + Postgres `case_stages` | **Sui `case_router` events** |
| Payload storage | local JSON snapshot / Postgres | **Walrus blobs** |
| Human approval | Band room message / dashboard | **`approve_case` / `reject_case` tx** |

When `SUI_MODE=false`, nothing changes: the Band version runs exactly as before.
Every Sui code path is gated and additive.

### End-to-end flow (SUI_MODE=true)

```
web form / CLI
      |
      v
core/workflow.py  (run_case_stream)
      |
      |-- CASE_OPENED ----> walrus.store_case_record() --> blob ---> sui.open_case(case_id, sector, blob)   --> CaseOpened event
      |-- intake ---------> walrus.store_stage_payload() -> blob ---> sui.record_intake(case, blob)          --> StageRecorded event
      |-- verification ---> walrus.store_stage_payload() -> blob ---> sui.record_verification(case, outcome, blob) --> StageRecorded event
      |-- resource -------> walrus.store_stage_payload() -> blob ---> sui.record_resource(case, blob)        --> StageRecorded event
      |
      v
human reviewer
      |-- approve/reject --> sui.approve_case / reject_case(case, reason)                                    --> CaseDecided event
```

The agents themselves (`agents/intake.py`, `verification.py`, `resource.py`)
also persist their own output to Walrus when `SUI_MODE=true` and attach the
resulting `walrus_blob_id` to their returned payload, so each agent is
independently verifiable.

### On-chain object model

The Move package `mediflow_sui` (in `sui/`) defines one shared object and three
events.

`Case` (shared object) holds the workflow status and a Walrus blob id reference
for each stage:

```
case_id, sector, opened_by, status,
case_blob, intake_blob, verification_blob, verification_outcome,
resource_blob, decision, reason, decided_by
```

`status` advances through: `OPEN(0) -> INTAKE(1) -> VERIFIED(2) -> RESOURCED(3)`
then `APPROVED(4)` or `REJECTED(5)`.

Entry functions (all `public`, callable from the Sui TS SDK via a PTB):

| Function | Caller | Event emitted |
|---|---|---|
| `open_case(case_id, sector, case_blob)` | Coordinator | `CaseOpened` |
| `record_intake(case, walrus_blob_id)` | Intake | `StageRecorded` |
| `record_verification(case, outcome, walrus_blob_id)` | Verification | `StageRecorded` |
| `record_resource(case, walrus_blob_id)` | Resource | `StageRecorded` |
| `approve_case(case, reason)` | Human reviewer | `CaseDecided` |
| `reject_case(case, reason)` | Human reviewer | `CaseDecided` |

A decided case is immutable: any further stage write aborts with
`ECaseAlreadyDecided`.

---

## What changed vs the Band version

Everything is additive. The Band code is untouched; new files and `SUI_MODE`
gated blocks were added.

**New files**

| File | Role |
|---|---|
| `sui/Move.toml`, `sui/sources/case_router.move` | the on-chain case router (Move 2024) |
| `sui/tests/case_router_tests.move` | Move unit tests (full workflow + immutability) |
| `core/walrus_client.py` | Walrus HTTP client; SUI-mode replacement for `core/audit_log.py` |
| `core/sui_client.py` | submits `case_router` Move calls via the Sui CLI |
| `.env.sui.example` | all new env variables |
| `railway.sui-web.json` | Railway config for the `sui-web` service |
| `package.json` / `package-lock.json` | `@mysten/sui` + `@mysten/walrus` SDK deps |

**Modified files (additive only, gated by `SUI_MODE`)**

| File | Change |
|---|---|
| `core/workflow.py` | routes stage completions through Walrus + `case_router` |
| `agents/intake.py`, `verification.py`, `resource.py` | persist output to Walrus |
| `Procfile`, `railway-start.py` | add the `sui-web` service that boots Flask with `SUI_MODE=true` |

**Left untouched**: `core/audit_log.py`, `core/band_messaging.py`,
`core/case_store.py`, `core/case_state.py`, the Band adapter, all prompts and
sector data, and `railway.json`.

---

## Tech stack

- **Smart contract**: Sui Move (2024 edition), built/tested with Sui CLI 1.73.2.
- **On-chain client**: Sui TypeScript SDK `@mysten/sui` 2.19.0 (and `sui client`
  CLI for transaction submission from Python).
- **Storage**: Walrus SDK `@mysten/walrus` 1.2.1 + Walrus HTTP API.
- **Backend**: the original MedBand Python stack (Flask, the four agents, AI/ML
  API for the LLM calls).

---

## Build and test the contract

```bash
cd sui
sui move build      # compiles mediflow_sui (framework auto-injected)
sui move test       # runs the unit tests
```

Expected: a clean build and `Test result: OK. Total tests: 2; passed: 2`.

---

## Configuration

Copy the Sui env template and fill it in:

```bash
cp .env.sui.example .env       # or merge into your existing .env
```

Required variables (see `.env.sui.example` for the full list and optional knobs):

| Variable | Meaning |
|---|---|
| `SUI_MODE` | `true` to enable the Sui path |
| `SUI_RPC_URL` | Sui full-node RPC (e.g. testnet) |
| `SUI_PRIVATE_KEY` | signing key for the transacting address |
| `SUI_PACKAGE_ID` | published `mediflow_sui` package id |
| `WALRUS_API_URL` | Walrus HTTP gateway (publisher + aggregator) |
| `WALRUS_API_KEY` | optional bearer token for hosted gateways |

If `SUI_PACKAGE_ID` (or `WALRUS_API_URL`) is unset, the corresponding client
runs in a clearly-labelled **dry-run** mode: it logs the intended call and
returns a synthetic `dryrun-...` id instead of touching the chain or network.
This lets you run the whole pipeline locally with no wallet and no funds.

---

## Deploy

### 1. Publish the Move package

```bash
cd sui
sui client publish --gas-budget 100000000 --json
```

Copy the published package id into `SUI_PACKAGE_ID` in your `.env`. Make sure the
active `sui client` address is funded on the target network (use the testnet
faucet for the demo).

### 2. Configure the signer

The Python `sui_client.py` submits transactions with the `sui` CLI, which uses
the active address and network from `sui client`. Import your key and select the
environment:

```bash
sui keytool import "$SUI_PRIVATE_KEY" ed25519
sui client new-env --alias testnet --rpc "$SUI_RPC_URL"
sui client switch --env testnet
```

### 3. Provision Walrus

Point `WALRUS_API_URL` at a Walrus publisher/aggregator gateway (a public
testnet gateway, or your own). No key is needed for public gateways; set
`WALRUS_API_KEY` only for authenticated ones.

### 4. Run the web service in Sui mode

Locally:

```bash
SUI_MODE=true python frontend/app.py
# or, like production:
SUI_MODE=true gunicorn -w 4 -b 0.0.0.0:5000 frontend.app:app
```

On Railway, deploy the `sui-web` service in either of two ways:

- Set `SERVICE_TYPE=sui-web` on a service that uses the shared `railway.json`
  (its `python railway-start.py` start command then boots Flask with
  `SUI_MODE=true`), **or**
- Set that service's Config Path to `railway.sui-web.json`.

Set `SUI_MODE`, `SUI_PACKAGE_ID`, `SUI_RPC_URL`, `SUI_PRIVATE_KEY`,
`WALRUS_API_URL`, and the base MedBand variables (`AIML_API_KEY`,
`ACTIVE_SECTOR`) on the service.

---

## Verifying the audit trail

Every workflow stage emits an event you can read back independently:

- Look up the `Case` object id (returned by `open_case`) on a Sui explorer to
  see its current `status` and the per-stage Walrus blob ids.
- Query the package's `CaseOpened` / `StageRecorded` / `CaseDecided` events to
  reconstruct the full timeline, including the signer address and timestamp of
  each step.
- Fetch any stage payload from Walrus with `GET {WALRUS_API_URL}/v1/blobs/{blob_id}`
  and confirm it hashes to the on-chain blob id.

---

## Current status

- The Move package builds and its unit tests pass on Sui CLI 1.73.2.
- The full Python pipeline runs end to end in `SUI_MODE=true`, exercising
  `open_case`, `record_intake`, `record_verification`, `record_resource`, and
  `approve_case` / `reject_case`, plus the matching Walrus writes.
- Without `SUI_PACKAGE_ID` / `WALRUS_API_URL` configured, those calls run in
  dry-run mode (synthetic ids, no chain/network I/O). Publishing the package and
  pointing at a Walrus gateway switches them to live submission with no code
  change.
- `SUI_MODE=false` reproduces the original MedBand behavior exactly.
