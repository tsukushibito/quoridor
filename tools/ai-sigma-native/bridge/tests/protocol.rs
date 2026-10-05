use ai_sigma_ort_search::native_call;
use quoridor_core::research::{features, SigmaContext};
use serde_json::{json, Value};

fn call(request: Value) -> Value {
    let result = native_call(request);
    assert_eq!(result["ok"], true, "{result}");
    result["data"].clone()
}
fn new_session(prefix: &[u16], generation: u32, simulations: u32) -> u64 {
    call(json!({"op":"new", "prefix":prefix, "generation":generation,
        "simulations":simulations}))["handle"]
        .as_u64()
        .unwrap()
}
fn release(handle: u64) {
    assert_eq!(call(json!({"op":"free", "handle":handle}))["freed"], true);
}

#[test]
fn raw_fixture_uses_canonical_legal_history_features_and_f32_bits() {
    for prefix in [vec![], vec![13], vec![81 + 8 * 3 + 2]] {
        let result = call(json!({"op":"raw", "fixture":{"prefix":prefix}}));
        let context = SigmaContext::from_prefix(&prefix).unwrap();
        let expected = features(context.position()).map(f32::to_bits).to_vec();
        assert_eq!(result["features_bits"], json!(expected));
        assert_eq!(result["features_bits"].as_array().unwrap().len(), 648);
        assert_eq!(result["turn"], context.position().turn);
        let mut actual: Vec<_> = result["legal"]
            .as_array()
            .unwrap()
            .iter()
            .map(|n| n.as_u64().unwrap() as u16)
            .collect();
        let mut expected = context.legal_ids();
        actual.sort_unstable();
        expected.sort_unstable();
        assert_eq!(actual, expected);
    }
    let invalid = native_call(json!({"op":"raw", "fixture":{"prefix":[300]}}));
    assert_eq!(invalid["ok"], false);
}

#[test]
fn terminal_root_returns_done_without_neural_input() {
    let fixture = json!({
        "legal_prefix": [], "classification":"synthetic-diagnostic",
        "board":{"rust_pawns":[72,76],"walls_remaining":[10,10],"turn":1,
            "rust_h_anchors":[],"rust_v_anchors":[],"total_ply":1},
        "history_counts":[]
    });
    let handle = call(json!({"op":"new", "fixture":fixture, "diagnostic":true,
        "generation":3,"simulations":8}))["handle"]
        .as_u64()
        .unwrap();
    assert_eq!(
        call(json!({"op":"begin", "handle":handle,"generation":3})),
        json!({"pending":false,"done":true})
    );
    let cp = call(json!({"op":"checkpoint","handle":handle,"generation":3}));
    assert_eq!(cp["nn_calls"], 0);
    assert_eq!(cp["terminal_value"], -1.0);
    release(handle);
}

#[test]
fn independent_handles_enforce_generation_token_cancel_and_free() {
    let a = new_session(&[], 11, 2);
    let b = new_session(&[13], 12, 1);
    assert_ne!(a, b);
    let pending = call(json!({"op":"begin","handle":a,"generation":11}));
    assert_eq!(pending["pending"], true);
    assert_eq!(pending["features_bits"].as_array().unwrap().len(), 648);
    let duplicate = native_call(json!({"op":"begin","handle":a,"generation":11}));
    assert_eq!(duplicate["error"], "PENDING_DUPLICATE_BEGIN");
    assert_eq!(
        call(json!({"op":"cancel","handle":a,"generation":11}))["discarded"],
        true
    );
    assert_eq!(
        native_call(json!({"op":"begin","handle":a,"generation":11}))["error"],
        "STALE_GENERATION"
    );
    let p = call(json!({"op":"begin","handle":b,"generation":12}));
    // A synthetic ABI reply exercises f32 restoration/backup only: no model or forward.
    let response = call(json!({"op":"resume","handle":b,"generation":12,
        "token":p["token"],"logits":vec![0.0;136],"value":0.125}));
    assert_eq!(response["done"], true);
    let cp = call(json!({"op":"checkpoint","handle":b,"generation":12}));
    assert_eq!(cp["root_visits"], 1);
    assert_eq!(cp["nn_calls"], 1); // Synthetic protocol replies, not measured inference.
    assert_eq!(cp["root_mean"], 0.125);
    assert_eq!(
        native_call(json!({"op":"checkpoint","handle":b,"generation":13}))["error"],
        "STALE_GENERATION"
    );
    release(a);
    release(b);
    assert_eq!(call(json!({"op":"free","handle":b}))["freed"], false);
    assert_eq!(
        native_call(json!({"op":"begin","handle":b,"generation":12}))["error"],
        "INVALID_SESSION"
    );
}

#[test]
fn invalid_resume_refuses_and_quarantines_session() {
    let h = new_session(&[], 1, 2);
    let p = call(json!({"op":"begin","handle":h,"generation":1}));
    let result = native_call(json!({"op":"resume","handle":h,"generation":1,
        "token":p["token"].as_u64().unwrap()+1,"logits":vec![0.0;136],"value":0.0}));
    assert_eq!(result["error"], "TOKEN");
    assert_eq!(
        native_call(json!({"op":"checkpoint","handle":h,"generation":1}))["error"],
        "STALE_GENERATION"
    );
    release(h);
}

#[test]
fn buffer_abi_owns_input_output_and_releases_invalidated_handles() {
    use ai_sigma_ort_search::{ort_buffer, ort_call, ort_free, ort_len, ort_ptr};
    let bytes = serde_json::to_vec(&json!({"op":"raw", "fixture":{"prefix":[]}})).unwrap();
    let input = ort_buffer(bytes.len());
    assert_ne!(input, 0);
    assert_eq!(ort_len(input), bytes.len());
    // The owned buffer pointer is valid until ort_free; no foreign pointer or model memory.
    unsafe {
        std::slice::from_raw_parts_mut(ort_ptr(input) as *mut u8, bytes.len())
            .copy_from_slice(&bytes);
    }
    let output = ort_call(input);
    let response: Value = unsafe {
        serde_json::from_slice(std::slice::from_raw_parts(
            ort_ptr(output) as *const u8,
            ort_len(output),
        ))
    }
    .unwrap();
    assert_eq!(response["ok"], true);
    assert_eq!(
        response["data"]["features_bits"].as_array().unwrap().len(),
        648
    );
    assert_eq!(ort_free(input), 1);
    assert_eq!(ort_free(output), 1);
    assert_eq!(ort_len(input), 0);
    assert_eq!(ort_ptr(input), 0);
    assert_eq!(ort_free(output), 0);
    assert_eq!(ort_buffer(8 * 1024 * 1024 + 1), 0);
}
