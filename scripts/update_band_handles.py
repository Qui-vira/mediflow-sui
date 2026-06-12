"""Update coordinator prompts with real Band agent handles."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTORS = ["pharmacy", "hospital_triage", "lab", "mental_health", "hmo_claims", "emergency"]

REPLACEMENTS = {
    "@Intake": "@medlabbytbr/intake",
    "@Verification": "@medlabbytbr/verification",
    "@Resource": "@medlabbytbr/resource",
    "intake_agent_handle": "@medlabbytbr/intake",
    "verification_agent_handle": "@medlabbytbr/verification",
    "resource_agent_handle": "@medlabbytbr/resource",
}

for sector in SECTORS:
    path = ROOT / "prompts" / sector / "coordinator.md"
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    if "@medlabbytbr/coordinator" not in text:
        text += "\n## Band Agent Handles\n"
        text += "- Coordinator: @medlabbytbr/coordinator\n"
        text += "- Intake: @medlabbytbr/intake\n"
        text += "- Verification: @medlabbytbr/verification\n"
        text += "- Resource: @medlabbytbr/resource\n"
    path.write_text(text, encoding="utf-8")
    print(f"Updated handles in {path}")
