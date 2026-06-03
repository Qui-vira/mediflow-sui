# Verification Agent - Mental Health Sector

## Data Source: risk_screening

## Verdict Logic
- CASE_CLEAR: low risk
- CASE_CAUTION: medium risk
- CASE_ESCALATE: high risk or self_harm_flag yes

## Output Format (JSON only)
```json
{
  "status": "CASE_CLEAR|CASE_CAUTION|CASE_ESCALATE",
  "risk_level": "low|medium|high|critical",
  "flags_matched": [],
  "reason": "",
  "recommended_action": ""
}
```
