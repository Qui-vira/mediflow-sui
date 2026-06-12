
BAND_TOOLS_SECTION = """
## Band Platform Tools Available To You
Use these tools to manage the workflow through Band rooms:
- thenvoi_create_chatroom: Create a new room named MedBand-{CASE_ID}
- thenvoi_add_participant: Add Intake, Verification, Resource agents to the room
- thenvoi_send_message: Post messages with @mentions to route work
- thenvoi_get_participants: Check who is currently in the room

## Workflow Using Band Tools
1. thenvoi_create_chatroom(name='MedBand-{CASE_ID}')
2. thenvoi_add_participant(intake_agent_handle)
3. thenvoi_send_message('@Intake please process this case: {payload}')
4. Wait for INTAKE_COMPLETE in room
5. thenvoi_add_participant(verification_agent_handle)
6. thenvoi_send_message('@Verification please verify: {service} case: {case_id}')
7. If CASE_ESCALATE: thenvoi_send_message('HUMAN_ALERT: {reason}') and stop
8. thenvoi_add_participant(resource_agent_handle)
9. thenvoi_send_message('@Resource please check availability: {service}')
10. Wait for RESOURCE_COMPLETE
11. thenvoi_send_message('CASE_READY: {full_summary}')
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTORS = ["pharmacy", "hospital_triage", "lab", "mental_health", "hmo_claims", "emergency"]

for sector in SECTORS:
    path = ROOT / "prompts" / sector / "coordinator.md"
    text = path.read_text(encoding="utf-8")
    if "Band Platform Tools Available To You" not in text:
        path.write_text(text.rstrip() + "\n" + BAND_TOOLS_SECTION, encoding="utf-8")
        print(f"Updated {path}")
    else:
        print(f"Skipped {path} (already has Band tools)")
