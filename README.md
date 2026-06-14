# MedBand by The Billionaire Republic

A human-in-the-loop healthcare workflow MVP where Band AI agents coordinate patient service requests while a human reviewer keeps final approval control.

Built by **The Billionaire Republic (TBR)** for the Band of Agents Hackathon 2026 — **Track 3: Regulated and High-Stakes Workflows**.

## Problem

Healthcare service requests are often slow, fragmented, and hard to coordinate across intake, verification, availability checks, and final approval. The steps are usually handled by different people and systems, so requests stall, context gets lost, and there is no clean record of who made the final call.

## Solution

MedBand uses specialized AI agents to move a case through a structured workflow — intake, verification, and resource availability — while preserving **human approval for the final decision**. The AI agents coordinate; a licensed human reviewer approves or rejects. The system records the final approval as human-made.

**Core value proposition:** AI agents automate coordination, but the final decision stays with a human reviewer.

## MVP Scope

This MVP intentionally focuses on **one working Pharmacy workflow**, end to end, rather than every healthcare sector at once.

**Working MVP (Pharmacy):**

- Pharmacy case submission via web form
- Intake processing
- Medication / request verification
- Pharmacy resource availability check
- Human review
- Final human approval
- Case closure

**Not yet built — roadmap only:**

- Hospital triage
- Lab / diagnostics
- Mental health
- HMO / insurance
- Emergency dispatch
- Full institution dashboard
- Payment system
- User account system
- SMS / WhatsApp notifications

## Demo Workflow

A pharmacy case moves through these stages:

```
NEW_CASE_FROM_WEB
CASE OPENED
INTAKE COMPLETE
VERIFY CASE
VERIFICATION COMPLETE
CHECK AVAILABILITY
RESOURCE COMPLETE
CASE READY FOR HUMAN REVIEW
CASE APPROVED
```

See [demo_flow.md](demo_flow.md) for the full demo script.

## Agent Roles

| Agent | Responsibility |
|-------|----------------|
| **Web Agent** | Receives the patient form and starts the case. |
| **Coordinator** | Orchestrates the workflow and routes the case between agents. |
| **Intake** | Extracts and confirms the patient request. |
| **Verification** | Checks whether the requested service can proceed safely. |
| **Resource** | Checks availability at the selected institution. |
| **Approval Desk** | Receives the final case summary for human review. It does not approve or reject. |
| **Human Reviewer** | Makes the final approval or rejection decision. |

## Human-in-the-Loop Safety

- AI agents do **not** make the final approval.
- The Approval Desk does **not** approve — it only presents the case summary for review.
- A human reviewer must **manually** approve or reject in the Band room.
- The system records the final approval as **human-made**.
- MedBand is workflow support, **not** a replacement for licensed medical professionals. It does not diagnose, prescribe, or treat patients, and it makes no claim of regulatory compliance or production medical readiness.

## Architecture

- **Band AI rooms and agents** — agents collaborate in a visible Band room on app.band.ai.
- **Railway services** — separate services for `web`, `coordinator`, `intake`, `verification`, and `resource`, plus a managed Postgres.
- **Web form** — Flask app where patients submit a request.
- **Postgres stage tracking** — each workflow stage (CASE_OPENED, INTAKE_COMPLETE, VERIFY_REQUEST, etc.) is recorded for idempotency and audit.
- **Human approval in the Band room** — the reviewer is added to the room and approves or rejects directly there.

## Live Links

- **Live web form:** https://web-production-6d13b.up.railway.app
- **Landing page:** https://medband-landing.vercel.app
- **GitHub:** https://github.com/Qui-vira/Tbr-Medband
- **Band:** https://app.band.ai

## Successful Demo Proof

A real production case was driven from web submission all the way to `CASE APPROVED`:

| Field | Value |
|-------|-------|
| Case ID | `MEDBAND-WEB-989E388C` |
| Sector | Pharmacy |
| Institution | Peaceway Pharmacy |
| Institution ID | `PHM001` |
| Patient | Band Human Approval Participant Test |
| Presenting issue | BODY PAINS |
| Requested service | PARACETAMOL |
| Prescription code | TBR-DOC-0042 |
| Human approval command | `@Coordinator APPROVE MEDBAND-WEB-989E388C` |
| Final result | **CASE APPROVED** |

Case `MEDBAND-WEB-989E388C` moved from web submission to `CASE APPROVED`. **BODY PAINS**, **PARACETAMOL**, and **Peaceway Pharmacy** were preserved through the workflow. The final approval was made manually by **Kehinde-David Damilare Samuel** in Band.

> **Final safety proof:** No AI approved this case. Final approval was made by the human reviewer.

## Setup

```powershell
cd C:\Users\Bigquiv\tbr-medband

# Create venv (Python 3.11+ recommended)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your own values (see Environment Variables below)
```

### Environment Variables

Set these as Railway environment variables (for the deployed services) and/or in your local `.env`. Use your own credentials — never commit real keys.

```
BAND_MODE=true
INTAKE_AGENT_ID=<your-band-intake-agent-id>
INTAKE_API_KEY=<your-band-intake-api-key>
COORDINATOR_AGENT_ID=<your-band-coordinator-agent-id>
ANTHROPIC_API_KEY=<your-model-provider-api-key>
DATABASE_URL=<your-postgres-connection-string>
```

Railway environment variables are required for the Band agents, Postgres, and model provider configuration. Each Railway service selects its process via a `SERVICE_TYPE` variable (`web`, `coordinator`, `intake`, `verification`, `resource`).

## Run Commands (local)

```powershell
# Web form (Flask)
python frontend\app.py
# -> http://127.0.0.1:5000

# Band agents (one terminal each)
python agents\coordinator.py
python agents\intake.py
python agents\verification.py
python agents\resource.py
```

## Human Approval via Band

Institution approvers are configured in `data/institution_users.json` with Band handles.

When a case reaches `CASE_READY`, the Coordinator:

- Adds the human reviewer to the Band room as a participant
- @mentions them with a clean, human-readable case summary (no raw JSON)
- Waits for `APPROVE`, `REJECT: reason`, or `MORE INFO: ...`

The reviewer approves by typing, for example:

```
@Coordinator APPROVE MEDBAND-WEB-989E388C
```

For the hackathon demo, the pharmacy reviewer routes to `@medlabbytbr`.

## Test Commands

```powershell
# Band message routing / formatting tests
$env:PYTHONPATH=(Get-Location).Path; pytest tests/test_band_messaging.py

# Full validation suite
python tests\validate.py
```

## Project Structure

```
tbr-medband/
├── agents/           Band persistent agents (coordinator, intake, verification, resource)
├── core/             band_messaging.py, case_state.py, case_store.py, workflow.py
├── prompts/          per-sector agent prompts
├── data/             institutions.json, institution_users.json, sector JSON
├── frontend/         app.py, index.html, status.html
├── cases/            saved case summaries (gitignored)
├── demo_flow.md      demo script
├── railway-start.py  Railway multi-service launcher
└── requirements.txt
```

## Roadmap

**Near-term:**

- Better case status UI
- Human reviewer dashboard
- Cleaner case history page
- Approval / rejection buttons
- Better monitoring and logs

**Later:**

- Hospital triage
- Lab diagnostics
- Mental health support workflows
- HMO / insurance routing
- Emergency dispatch
- SMS / WhatsApp / email notifications
- Institution onboarding
- Payments

## Hackathon Note

This MVP intentionally focuses on one polished end-to-end workflow (Pharmacy) instead of trying to build every healthcare sector at once. It is a **working MVP and hackathon demo** — not a full medical product.

## Team

The Billionaire Republic (TBR) — Band of Agents Hackathon 2026
