#![cfg(feature = "ai")]
use quoridor_core::Game;
use quoridor_wasm::wire::{
    AiCorrelationDto, AiResultDto, AiStartPayloadDto, AiStatsDto, AiWorkerRequestDto,
    AiWorkerResponseDto, SearchLimitsDto, SnapshotDto,
};
use serde_json::{Value, json};

fn valid() -> Value {
    let game = Game::new();
    let snapshot = SnapshotDto::from_game(&game).unwrap();
    let value = AiStartPayloadDto {
        schema_version: 1,
        meta: AiCorrelationDto {
            protocol_version: 2,
            engine_build_id: "quoridor-b0-1".into(),
            request_id: 1,
            game_epoch: 1,
            revision: 0,
            position_key: snapshot.position_key.clone(),
            ruleset_id: "standard-2p-v1".into(),
            worker_generation: 1,
        },
        snapshot: serde_json::to_vec(&snapshot).unwrap(),
        limits: SearchLimitsDto {
            simulations: 96,
            max_nodes: 512,
            max_depth: 24,
        },
        seed: "1979".into(),
    };
    serde_json::to_value(value).unwrap()
}

#[test]
fn serde_shape_and_numeric_rejection_match_generated_dto() {
    let original = valid();
    assert_eq!(original["schemaVersion"], 1);
    assert_eq!(original["meta"]["workerGeneration"], 1);
    assert_eq!(original["limits"]["maxNodes"], 512);
    assert_eq!(original["seed"], "1979");
    assert!(original.get("schema_version").is_none());
    for (path, replacement) in [
        ("simulations", json!(-1)),
        ("simulations", json!(1.5)),
        ("maxNodes", json!(4294967296u64)),
        ("maxDepth", json!(256)),
    ] {
        let mut bad = original.clone();
        bad["limits"][path] = replacement;
        assert!(
            serde_json::from_value::<AiStartPayloadDto>(bad).is_err(),
            "{path}"
        );
    }
    for replacement in [json!(-1), json!(1.5), json!(4294967296u64)] {
        let mut bad = original.clone();
        bad["meta"]["requestId"] = replacement;
        assert!(serde_json::from_value::<AiStartPayloadDto>(bad).is_err());
    }
    for bad in [json!(null), json!({}), json!([1, 2])] {
        assert!(serde_json::from_value::<AiStartPayloadDto>(bad).is_err());
    }
    let mut extra = original.clone();
    extra["unexpected"] = json!(true);
    assert!(serde_json::from_value::<AiStartPayloadDto>(extra).is_err());
    let parsed: AiStartPayloadDto = serde_json::from_value(original).unwrap();
    let decoded = SnapshotDto::decode(&parsed.snapshot).unwrap();
    assert_eq!(decoded.position_key, parsed.meta.position_key);
}

#[test]
fn worker_union_serde_tags_and_camel_case_match_generated_types() {
    let payload: AiStartPayloadDto = serde_json::from_value(valid()).unwrap();
    let start = AiWorkerRequestDto::Start {
        payload: payload.clone(),
    };
    let json = serde_json::to_value(&start).unwrap();
    assert_eq!(json["type"], "start");
    assert_eq!(json["payload"]["meta"]["workerGeneration"], 1);
    assert_eq!(
        serde_json::from_value::<AiWorkerRequestDto>(json).unwrap(),
        start
    );
    let result = AiWorkerResponseDto::Result {
        meta: payload.meta,
        result: AiResultDto {
            action_id: Some(13),
            stats: AiStatsDto {
                simulations: 2,
                nodes: 2,
                edges: 131,
                arena_bytes: 2000,
                high_water_bytes: 2000,
                max_depth_reached: 1,
                policy_fallbacks: 0,
                value_fallbacks: 0,
                budget_exhausted: false,
            },
        },
        slice_ms: 2.5,
        slice_samples: vec![1.0, 2.5],
        wasm_memory_bytes: 1048576,
    };
    let json = serde_json::to_value(&result).unwrap();
    assert_eq!(json["type"], "result");
    assert_eq!(json["sliceMs"], 2.5);
    assert_eq!(json["sliceSamples"], json!([1.0, 2.5]));
    assert_eq!(json["wasmMemoryBytes"], 1048576);
    assert_eq!(json["result"]["actionId"], 13);
    assert_eq!(
        serde_json::from_value::<AiWorkerResponseDto>(json).unwrap(),
        result
    );
    assert!(serde_json::from_value::<AiWorkerRequestDto>(json!({"type":"unknown"})).is_err());
    assert!(
        serde_json::from_value::<AiWorkerResponseDto>(json!({"type":"result","meta":null}))
            .is_err()
    );
}
