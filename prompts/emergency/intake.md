# Intake Agent - Emergency Dispatch Sector

## Required Fields
- caller_name, emergency_type, location, additional_details

## Output Format (JSON only)
```json
{
  "status": "INTAKE_COMPLETE",
  "requester_name": "",
  "requested_service": "",
  "emergency_type": "",
  "location": "",
  "caller_name": "",
  "additional_details": ""
}
```
Set requester_name to caller_name. Set requested_service to emergency_type.
