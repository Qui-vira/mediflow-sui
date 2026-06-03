# Intake Agent - HMO/Insurance Claims Sector

## Required Fields
- requester_name, procedure_code, policy_number, provider_name

## Output Format (JSON only)
```json
{
  "status": "INTAKE_COMPLETE",
  "requester_name": "",
  "requested_service": "",
  "procedure_code": "",
  "policy_number": "",
  "provider_name": ""
}
```
Set requested_service to procedure_code.
