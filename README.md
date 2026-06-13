# MedBand

**MedBand** is a sector-configurable, multi-agent healthcare workflow engine built by **The Billionaire Republic (TBR)** for the Band of Agents Hackathon 2026 - **Track 3: Regulated and High-Stakes Workflows**.

Four AI agents process healthcare requests from intake through verification and resource checking to a structured case summary. A human professional makes the final approval decision.

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

## Phase 1 (Current - Band-Free)

Agents call each other as direct Python functions. `core/audit_log.py` mocks the Band room. Every agent appends structured JSON to `audit_log`. The dashboard reads and displays the audit trail.

## Setup

```powershell
cd C:\Users\Bigquiv\tbr-medband

# Create venv (Python 3.11 recommended)
C:\Users\Bigquiv\AppData\Local\Programs\Python\Python311\python.exe -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env - set ANTHROPIC_API_KEY and ACTIVE_SECTOR=pharmacy
```

## Run Commands

```powershell
# Terminal 1 - Web form (Flask)
.\venv\Scripts\python frontend\app.py
# → http://127.0.0.1:5000

# Terminal 2 - Human approval dashboard (Streamlit)
.\venv\Scripts\streamlit run dashboard\dashboard.py
# → http://localhost:8501

# CLI pipeline
.\venv\Scripts\python main.py "Name: Ada. Issue: fever. Requested service: Amoxicillin. Urgency: high"
```

## Test Commands

```powershell
# Full validation suite (JSON + prompts + pipeline + escalation)
.\venv\Scripts\python tests\validate.py

# Validate pharmacy JSON
.\venv\Scripts\python -c "import json; json.load(open('data/pharmacy/registry.json')); print('OK')"

# Audit log smoke test
.\venv\Scripts\python -c "from core.audit_log import post; post('test','TEST','C001',{}); print('audit_log works')"

# Agent module smoke tests
.\venv\Scripts\python agents\intake.py
.\venv\Scripts\python agents\verification.py
.\venv\Scripts\python agents\resource.py

# Direct pipeline test (requires ANTHROPIC_API_KEY)
.\venv\Scripts\python -c "from core.workflow import run_case; import json; print(json.dumps(run_case('Name: Ada. Issue: fever and headache. Requested service: Amoxicillin. Urgency: high'), indent=2))"

# Escalation test - banned drug (Rohypnol)
.\venv\Scripts\python main.py "Name: Test. Issue: insomnia. Requested service: Rohypnol. Urgency: high"

# Hospital triage escalation - chest pain
.\venv\Scripts\python main.py "Name: Chidi. Issue: chest pain radiating to arm. Requested service: Emergency triage. Urgency: critical" --sector hospital_triage
```

## Demo Cases

| Sector | Input | Expected |
|--------|-------|----------|
| Pharmacy | Amoxicillin, fever | READY_FOR_REVIEW, 5+ audit entries |
| Pharmacy | Rohypnol (banned) | ESCALATED, HUMAN_ALERT, no resource check |
| Hospital Triage | chest pain + arm radiation | ESCALATED (red triage) |
| Mental Health | self-harm mention | ESCALATED |
| Lab | Full Blood Count + valid referral | READY_FOR_REVIEW |
| Emergency | cardiac arrest keywords | ESCALATED (P1) |

## Project Structure

```
tbr-medband/
├── agents/           intake.py, verification.py, resource.py, coordinator.py
├── core/             audit_log.py, sector_loader.py, workflow.py
├── prompts/          6 sectors × 4 agent prompts
├── data/             6 sectors × JSON config files
├── frontend/         app.py, index.html
├── dashboard/        dashboard.py
├── cases/            saved case summaries (gitignored)
├── tests/            validate.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Phase 2 (June 12)

Replace `audit_log` with Band SDK room calls. See Phase 2 Band Wiring Guide.

## Team

The Billionaire Republic (TBR) - Band of Agents Hackathon 2026

## Global Configurability

MedBand is designed to work with any country's healthcare infrastructure. The pharmacy sector demo uses Nigerian NAFDAC drug registry data. To deploy for another country:

1. Replace `data/pharmacy/registry.json` with your national drug regulatory database
2. Update the `registry_body` field to your country's regulatory body name (e.g. FDA, MHRA, PPB)
3. Update `data/pharmacy/doctors.json` with registered practitioners from your country's medical council
4. All agent logic, Band workflows, and approval flows remain identical

Supported regulatory body examples:

- Nigeria: NAFDAC (National Agency for Food and Drug Administration and Control)
- USA: FDA (Food and Drug Administration)
- UK: MHRA (Medicines and Healthcare products Regulatory Agency)
- Ghana: FDA Ghana
- Kenya: PPB (Pharmacy and Poisons Board)
- South Africa: SAHPRA
