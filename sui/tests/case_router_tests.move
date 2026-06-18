#[test_only]
module mediflow_sui::case_router_tests;

use mediflow_sui::case_router::{Self, Case};
use std::string;
use sui::test_scenario as ts;

const COORDINATOR: address = @0xC0;
const REVIEWER: address = @0xA11CE;

#[test]
fun test_full_workflow_to_approval() {
    let mut scenario = ts::begin(COORDINATOR);

    // Coordinator opens the case.
    case_router::open_case(
        string::utf8(b"MB-TEST01"),
        string::utf8(b"pharmacy"),
        string::utf8(b"walrus-case-record"),
        ts::ctx(&mut scenario),
    );

    // Agents record their stages against the shared Case.
    ts::next_tx(&mut scenario, COORDINATOR);
    {
        let mut case = ts::take_shared<Case>(&scenario);
        case_router::record_intake(
            &mut case,
            string::utf8(b"walrus-intake-blob"),
            ts::ctx(&mut scenario),
        );
        case_router::record_verification(
            &mut case,
            string::utf8(b"CASE_CLEAR"),
            string::utf8(b"walrus-verification-blob"),
            ts::ctx(&mut scenario),
        );
        case_router::record_resource(
            &mut case,
            string::utf8(b"walrus-resource-blob"),
            ts::ctx(&mut scenario),
        );
        assert!(case_router::verification_outcome(&case) == string::utf8(b"CASE_CLEAR"), 0);
        ts::return_shared(case);
    };

    // Human reviewer approves.
    ts::next_tx(&mut scenario, REVIEWER);
    {
        let mut case = ts::take_shared<Case>(&scenario);
        case_router::approve_case(
            &mut case,
            string::utf8(b"Verified and in stock"),
            ts::ctx(&mut scenario),
        );
        assert!(case_router::status(&case) == 4, 1); // STATUS_APPROVED
        ts::return_shared(case);
    };

    ts::end(scenario);
}

#[test]
#[expected_failure(abort_code = mediflow_sui::case_router::ECaseAlreadyDecided)]
fun test_cannot_mutate_after_rejection() {
    let mut scenario = ts::begin(COORDINATOR);

    case_router::open_case(
        string::utf8(b"MB-TEST02"),
        string::utf8(b"pharmacy"),
        string::utf8(b"walrus-case-record"),
        ts::ctx(&mut scenario),
    );

    ts::next_tx(&mut scenario, REVIEWER);
    {
        let mut case = ts::take_shared<Case>(&scenario);
        case_router::reject_case(
            &mut case,
            string::utf8(b"Out of stock"),
            ts::ctx(&mut scenario),
        );
        // Recording a stage after a decision must abort.
        case_router::record_intake(
            &mut case,
            string::utf8(b"walrus-late-intake"),
            ts::ctx(&mut scenario),
        );
        ts::return_shared(case);
    };

    ts::end(scenario);
}
