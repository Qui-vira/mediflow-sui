/// MediFlow-Sui :: case_router
///
/// On-chain case router for the MediFlow-Sui agentic healthcare workflow.
///
/// In the original MedBand, the four agents (Coordinator, Intake, Verification,
/// Resource) coordinate through a Band chat room and progress is tracked in a
/// Postgres `case_stages` table. This module replaces that coordination layer
/// with a Sui shared object plus on-chain events:
///
///   * `open_case`           -> creates a shared `Case` and emits `CaseOpened`
///   * `record_intake`       -> records the Intake stage,        emits `StageRecorded`
///   * `record_verification` -> records the Verification stage,  emits `StageRecorded`
///   * `record_resource`     -> records the Resource stage,      emits `StageRecorded`
///   * `approve_case`        -> human approval,                  emits `CaseDecided`
///   * `reject_case`         -> human rejection,                 emits `CaseDecided`
///
/// Heavy payloads (the full intake/verification/resource JSON and the patient
/// case record) are stored off-chain in Walrus decentralized storage. This
/// contract keeps only the Walrus blob id reference for each stage, so the
/// chain holds a tamper-evident index of who recorded what and when, while
/// Walrus holds the bulky records. Every state transition emits an event so an
/// off-chain indexer can rebuild the full audit trail.
module mediflow_sui::case_router;

use std::string::{Self, String};
use sui::event;

// === Status codes ===
const STATUS_OPEN: u8 = 0;
const STATUS_INTAKE: u8 = 1;
const STATUS_VERIFIED: u8 = 2;
const STATUS_RESOURCED: u8 = 3;
const STATUS_APPROVED: u8 = 4;
const STATUS_REJECTED: u8 = 5;

// === Errors ===
/// A decided (approved/rejected) case cannot be mutated further.
const ECaseAlreadyDecided: u64 = 1;

/// A single case tracked through the MediFlow workflow.
///
/// Shared so the Coordinator, the three agents, and the human reviewer can each
/// write to it from their own Sui address. Each `*_blob` field holds a Walrus
/// blob id; an empty string means that stage has not been recorded yet.
public struct Case has key {
    id: UID,
    case_id: String,
    sector: String,
    opened_by: address,
    status: u8,
    case_blob: String,
    intake_blob: String,
    verification_blob: String,
    verification_outcome: String,
    resource_blob: String,
    decision: String,
    reason: String,
    decided_by: address,
}

// === Events ===

/// Emitted when a case is opened (mirrors CASE_OPENED in the Band version).
public struct CaseOpened has copy, drop {
    case_object_id: ID,
    case_id: String,
    sector: String,
    case_blob: String,
    opened_by: address,
    timestamp_ms: u64,
}

/// Emitted on every agent stage write (intake / verification / resource).
public struct StageRecorded has copy, drop {
    case_object_id: ID,
    case_id: String,
    stage: String,
    outcome: String,
    walrus_blob_id: String,
    status: u8,
    recorded_by: address,
    timestamp_ms: u64,
}

/// Emitted on the final human decision (approve / reject).
public struct CaseDecided has copy, drop {
    case_object_id: ID,
    case_id: String,
    decision: String,
    reason: String,
    decided_by: address,
    timestamp_ms: u64,
}

// === Workflow functions (public so the TS SDK can call them in a PTB) ===

/// Open a new case and share it on-chain.
///
/// `case_blob` is the Walrus blob id of the initial patient case record.
public fun open_case(
    case_id: String,
    sector: String,
    case_blob: String,
    ctx: &mut TxContext,
) {
    let sender = ctx.sender();
    let case = Case {
        id: object::new(ctx),
        case_id,
        sector,
        opened_by: sender,
        status: STATUS_OPEN,
        case_blob,
        intake_blob: string::utf8(b""),
        verification_blob: string::utf8(b""),
        verification_outcome: string::utf8(b""),
        resource_blob: string::utf8(b""),
        decision: string::utf8(b""),
        reason: string::utf8(b""),
        decided_by: @0x0,
    };
    event::emit(CaseOpened {
        case_object_id: object::id(&case),
        case_id: case.case_id,
        sector: case.sector,
        case_blob: case.case_blob,
        opened_by: sender,
        timestamp_ms: ctx.epoch_timestamp_ms(),
    });
    transfer::share_object(case);
}

/// Record the Intake stage output (Walrus blob id of the structured intake).
public fun record_intake(
    case: &mut Case,
    walrus_blob_id: String,
    ctx: &mut TxContext,
) {
    assert_not_decided(case);
    case.intake_blob = walrus_blob_id;
    case.status = STATUS_INTAKE;
    emit_stage(case, string::utf8(b"intake"), string::utf8(b""), case.intake_blob, ctx);
}

/// Record the Verification stage. `outcome` is the verification verdict, e.g.
/// CASE_CLEAR / CASE_CAUTION / CASE_ESCALATE.
public fun record_verification(
    case: &mut Case,
    outcome: String,
    walrus_blob_id: String,
    ctx: &mut TxContext,
) {
    assert_not_decided(case);
    case.verification_blob = walrus_blob_id;
    case.verification_outcome = outcome;
    case.status = STATUS_VERIFIED;
    emit_stage(
        case,
        string::utf8(b"verification"),
        case.verification_outcome,
        case.verification_blob,
        ctx,
    );
}

/// Record the Resource stage output (Walrus blob id of the availability check).
public fun record_resource(
    case: &mut Case,
    walrus_blob_id: String,
    ctx: &mut TxContext,
) {
    assert_not_decided(case);
    case.resource_blob = walrus_blob_id;
    case.status = STATUS_RESOURCED;
    emit_stage(case, string::utf8(b"resource"), string::utf8(b""), case.resource_blob, ctx);
}

/// Human reviewer approves the case. AI agents never call this.
public fun approve_case(case: &mut Case, reason: String, ctx: &mut TxContext) {
    decide(case, STATUS_APPROVED, string::utf8(b"approved"), reason, ctx);
}

/// Human reviewer rejects the case. AI agents never call this.
public fun reject_case(case: &mut Case, reason: String, ctx: &mut TxContext) {
    decide(case, STATUS_REJECTED, string::utf8(b"rejected"), reason, ctx);
}

// === Internal helpers ===

fun assert_not_decided(case: &Case) {
    assert!(
        case.status != STATUS_APPROVED && case.status != STATUS_REJECTED,
        ECaseAlreadyDecided,
    );
}

fun emit_stage(
    case: &Case,
    stage: String,
    outcome: String,
    walrus_blob_id: String,
    ctx: &TxContext,
) {
    event::emit(StageRecorded {
        case_object_id: object::id(case),
        case_id: case.case_id,
        stage,
        outcome,
        walrus_blob_id,
        status: case.status,
        recorded_by: ctx.sender(),
        timestamp_ms: ctx.epoch_timestamp_ms(),
    });
}

fun decide(
    case: &mut Case,
    new_status: u8,
    decision: String,
    reason: String,
    ctx: &TxContext,
) {
    assert_not_decided(case);
    case.status = new_status;
    case.decision = decision;
    case.reason = reason;
    case.decided_by = ctx.sender();
    event::emit(CaseDecided {
        case_object_id: object::id(case),
        case_id: case.case_id,
        decision: case.decision,
        reason: case.reason,
        decided_by: case.decided_by,
        timestamp_ms: ctx.epoch_timestamp_ms(),
    });
}

// === Read-only accessors ===

public fun status(case: &Case): u8 { case.status }

public fun case_id(case: &Case): String { case.case_id }

public fun verification_outcome(case: &Case): String { case.verification_outcome }
