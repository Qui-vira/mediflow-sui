# MedBand

**MedBand** is a sector-configurable, multi-agent healthcare workflow engine built by **The Billionaire Republic (TBR)** for the Band of Agents Hackathon 2026 — **Track 3: Regulated and High-Stakes Workflows**.

Four AI agents process healthcare requests from intake through verification and resource checking to a structured case summary. A human professional makes the final approval decision **directly in the Band room** — no separate dashboard required.

## Safety Rules

- No AI agent prescribes medication
- No AI agent approves medical decisions
- The system only prepares, verifies, flags, summarizes, and escalates
- Final approval belongs to the human professional (`human_role` shown in every summary)

## Sectors

| Sector | Human Approver |
|--------|----------------|
| Pharmacy | Pharmacist |
| Hospital Triage | Doctor / Nurse |
| Lab / Diagnostics | Lab Officer |
| Mental Health | Clinical Coordinator |
| HMO / Insurance Claims | Claims Officer |
| Emergency Dispatch | Dispatcher |

Switch sectors via the web form dropdown or `ACTIVE_SECTOR` in `.env`.

## How It Works

1. **Patient submits** via the Flask web form (`BAND_MODE=true` by default)
2. **Intake agent** sends the case to the Coordinator via Band REST API
3. **Four Band agents** coordinate in a visible Band room on app.band.ai
4. **Coordinator** posts `CASE_READY` and @mentions the institution approver
5. **Human approves or rejects** in the Band room (`APPROVE` / `REJECT: reason`)
6. **Patient tracks status** at `/status?case_id=...`

See [demo_flow.md](demo_flow.md) for the full judge demo script.

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
# Edit .env — set ANTHROPIC_API_KEY, Band agent credentials, BAND_MODE=true
```

## Run Commands

```powershell
# Web form (Flask)
python frontend\app.py
# → http://127.0.0.1:5000

# Band agents (one terminal each)
python agents\coordinator.py
python agents\intake.py
python agents\verification.py
python agents\resource.py

# CLI pipeline (Phase 1 fallback — set BAND_MODE=false)
python main.py "Name: Ada. Issue: fever. Requested service: Amoxicillin. Urgency: high"
```

## Human Approval via Band

Institution approvers are configured in `data/institution_users.json` with Band handles.

When a case reaches `CASE_READY`, the Coordinator:
- Adds the approver to the Band room via `thenvoi_add_participant`
- @mentions them with a human-readable summary
- Waits for `APPROVE`, `REJECT: reason`, or `MORE INFO: ...`

For hackathon demo, all institutions route to `@medlabbytbr`.

## Test Commands

```powershell
# Full validation suite
python tests\validate.py

# Direct pipeline test (BAND_MODE=false)
python -c "from core.workflow import run_case; import json; print(json.dumps(run_case('Name: Ada. Issue: fever. Requested service: Amoxicillin. Urgency: high'), indent=2))"

# Escalation test — banned drug (Rohypnol)
python main.py "Name: Test. Issue: insomnia. Requested service: Rohypnol. Urgency: high"
```

## Demo Cases

| Sector | Input | Expected |
|--------|-------|----------|
| Pharmacy | Amoxicillin, fever | CASE_READY in Band room, await approval |
| Pharmacy | Rohypnol (banned) | HUMAN_ALERT in Band room |
| Hospital Triage | chest pain + arm radiation | ESCALATED |
| Mental Health | self-harm mention | ESCALATED |

## Project Structure

```
tbr-medband/
├── agents/           Band persistent agents (coordinator, intake, verification, resource)
├── core/             workflow.py, band_client.py, sector_loader.py
├── prompts/          6 sectors × 4 agent prompts
├── data/             institutions.json, institution_users.json, sector JSON
├── frontend/         app.py, index.html, status.html
├── cases/            saved case summaries (gitignored)
├── demo_flow.md      judge demo script
├── railway-start.py  Railway multi-service launcher
└── requirements.txt
```

## Railway Deployment

```bash
railway up -s web -d          # Flask form
railway up -s coordinator -d  # Band agents
railway up -s intake -d
railway up -s verification -d
railway up -s resource -d
```

Required web service variables: `BAND_MODE=true`, `INTAKE_AGENT_ID`, `INTAKE_API_KEY`, `COORDINATOR_AGENT_ID`, `ANTHROPIC_API_KEY`.

Live form: https://web-production-6d13b.up.railway.app

## Team

The Billionaire Republic (TBR) — Band of Agents Hackathon 2026
