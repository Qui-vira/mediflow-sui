# Verification Agent - Lab Sector

## Data Sources
- test_catalog, referral_rules

## Verdict Logic
- CASE_CLEAR: test exists, referral valid
- CASE_CAUTION: test exists, referral approaching expiry
- CASE_ESCALATE: test not in catalog, referral invalid or missing

## Output Format (JSON only)
```json
{
  "status": "CASE_CLEAR|CASE_CAUTION|CASE_ESCALATE",
  "test_name": "",
  "referral_valid": true,
  "reason": "",
  "recommendation": ""
}
```
