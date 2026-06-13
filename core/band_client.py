"""Band REST API client for web form → Coordinator routing."""
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BAND_REST_URL = os.environ.get("BAND_REST_URL", "https://app.band.ai").rstrip("/")
COORDINATOR_HANDLE = "medlabbytbr/coordinator"


def get_coordinator_handle() -> str:
    return f"@{COORDINATOR_HANDLE}"


def _band_credentials() -> tuple[str, str]:
    """API key + agent id for the web sender.

    The web form must post NEW_CASE_FROM_WEB under a dedicated web/system Band
    identity, never under a workflow agent (Intake/Verification/Resource). Posting
    as Intake makes the case look like it came from the Intake agent and corrupts
    Coordinator routing. We require WEB_BAND_* explicitly and never fall back to a
    workflow agent's credentials.
    """
    web_key = os.environ.get("WEB_BAND_API_KEY")
    web_id = os.environ.get("WEB_BAND_AGENT_ID")
    if web_key and web_id:
        return web_id, web_key

    raise ValueError(
        "Web Band sender identity is not configured. Set WEB_BAND_AGENT_ID and "
        "WEB_BAND_API_KEY to a dedicated web/system Band agent. Do not reuse the "
        "Intake, Verification, or Resource agent identity for web submissions."
    )


def _coordinator_agent_id() -> str:
    coord_id = os.environ.get("COORDINATOR_AGENT_ID")
    if coord_id:
        return coord_id
    try:
        from agents._band import get_agent_credentials

        return get_agent_credentials("coordinator")[0]
    except ValueError as exc:
        raise ValueError("COORDINATOR_AGENT_ID is not configured.") from exc


def _format_new_case_message(case_payload: dict) -> str:
    # Clean, human-readable only. Never post raw JSON into the Band room.
    prescription_code = case_payload.get("prescription_code") or "none"
    return f"""@{COORDINATOR_HANDLE} NEW_CASE_FROM_WEB

Sector: {case_payload.get("sector")}
Institution: {case_payload.get("institution_name")}
Institution ID: {case_payload.get("institution_id")}
Case ID: {case_payload.get("case_id")}

Patient: {case_payload.get("patient_name")}
Presenting issue: {case_payload.get("presenting_issue")}
Requested service: {case_payload.get("requested_service")}
Urgency: {case_payload.get("urgency", "medium")}
Prescription code: {prescription_code}

Coordinator should open this case and follow the standard pharmacy workflow."""


def save_pending_case(case_payload: dict) -> dict:
    """Persist a web-submitted case so patients can track it while agents run."""
    from core.sector_loader import band_room_name, get_institution, human_role
    from core.workflow import _save_case

    sector = case_payload["sector"]
    case_id = case_payload["case_id"]
    institution_id = case_payload.get("institution_id")
    institution = (
        get_institution(sector, institution_id) if institution_id else None
    )

    summary = {
        "case_id": case_id,
        "sector": sector,
        "status": "PROCESSING",
        "source": case_payload.get("source", "web_form"),
        "institution_id": institution_id,
        "institution_name": case_payload.get("institution_name")
        or (institution or {}).get("name"),
        "band_room": band_room_name(case_id, sector, institution_id),
        "human_role": human_role(sector),
        "intake": {
            "requester_name": case_payload.get("patient_name"),
            "raw_input": case_payload.get("raw_input"),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turnaround": (institution or {}).get("turnaround"),
    }
    _save_case(summary)
    return summary


async def send_to_coordinator(
    case_payload: dict,
    room_id: str | None = None,
) -> dict:
    """
    Send a case to the Coordinator agent via Band REST API.
    If room_id is None, a new chat room is created for this submission.
    Returns room metadata for the Band UI.
    """
    from band.client.rest import AsyncRestClient
    from thenvoi_rest import ChatMessageRequest, ChatMessageRequestMentionsItem, ChatRoomRequest
    from thenvoi_rest.types.participant_request import ParticipantRequest

    from core.sector_loader import band_room_name

    sender_id, api_key = _band_credentials()
    coordinator_id = _coordinator_agent_id()
    case_id = case_payload["case_id"]
    sector = case_payload.get("sector", "pharmacy")
    institution_id = case_payload.get("institution_id")
    band_room = band_room_name(case_id, sector, institution_id)

    client = AsyncRestClient(api_key=api_key, base_url=BAND_REST_URL)

    if room_id is None:
        chat = await client.agent_api_chats.create_agent_chat(
            chat=ChatRoomRequest(),
        )
        room_id = chat.data.id

        if sender_id != coordinator_id:
            await client.agent_api_participants.add_agent_chat_participant(
                chat_id=room_id,
                participant=ParticipantRequest(participant_id=coordinator_id),
            )

    message = _format_new_case_message(case_payload)
    await client.agent_api_messages.create_agent_chat_message(
        chat_id=room_id,
        message=ChatMessageRequest(
            content=message,
            mentions=[
                ChatMessageRequestMentionsItem(
                    id=coordinator_id,
                    handle=COORDINATOR_HANDLE,
                    name="Coordinator",
                ),
            ],
        ),
    )

    return {
        "room_id": room_id,
        "band_room": band_room,
        "case_id": case_id,
        "status": "processing",
    }


def send_to_coordinator_sync(
    case_payload: dict,
    room_id: str | None = None,
) -> dict:
    """Synchronous wrapper for Flask routes."""
    import asyncio

    return asyncio.run(send_to_coordinator(case_payload, room_id=room_id))
