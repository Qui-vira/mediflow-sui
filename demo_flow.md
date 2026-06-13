# MedBand Demo Flow

## For Judges and Demo

### Step 1: Submit a Case

Go to: https://web-production-6d13b.up.railway.app

Select sector and institution, fill in details, submit.

### Step 2: Watch Band Room

Go to: https://app.band.ai

Open the MedBand room for the case.

Watch 4 agents coordinate in real time.

### Step 3: Human Approval

The Coordinator will @mention the approver in the Band room with a clean case summary.

Respond with: `APPROVE` or `REJECT: reason`

### Step 4: Track Case Status

Go to: https://web-production-6d13b.up.railway.app/status

Enter your Case ID to see the decision.

## Band Account for Demo Approvals

For hackathon demo purposes, all approval requests go to: **@medlabbytbr**

Log in to app.band.ai to approve cases.

## Escalation Demo

Submit a Rohypnol case (pharmacy sector) to trigger `HUMAN_ALERT`.

The Coordinator posts an urgent message in the Band room.

Respond with: `REJECT: controlled substance request`

## Architecture

| Component | Role |
|-----------|------|
| Flask web form | Patient intake, case ID, status tracking |
| Band agents (4) | Coordinator, Intake, Verification, Resource |
| Band room | Human approval — no separate dashboard |
| `/status` page | Patient-facing case lookup |
