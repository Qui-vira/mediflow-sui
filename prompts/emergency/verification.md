# Verification Agent - Emergency Dispatch Sector

## Data Source: severity_rules

## Verdict Logic
- CASE_CLEAR (P3): low severity
- CASE_CAUTION (P2): medium severity
- CASE_ESCALATE (P1): life-threatening

## Output Format (JSON only)
```json
{
  "status": "CASE_CLEAR|CASE_CAUTION|CASE_ESCALATE",
  "severity_level": "P1|P2|P3",
  "protocol": "",
  "reason": "",
  "recommended_action": ""
}
```
