use quoridor_ai::{SearchLimits, SearchSession};
use quoridor_core::Game;
use quoridor_wasm::wire::{
    AiCorrelationDto, AiResultDto, AiStartPayloadDto, AiStatsDto, SCHEMA_VERSION, SearchLimitsDto,
    SnapshotDto,
};
use quoridor_wasm::{AI_ENGINE_BUILD_ID, AI_PROTOCOL_VERSION};
use serde_json::json;

fn main() {
    let cases: [(&str, &[u16]); 3] = [
        ("initial", &[]),
        ("opening", &[13, 67, 81, 66, 14, 65]),
        (
            "walled-midgame",
            &[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        ),
    ];
    let fixtures: Vec<_> = cases
        .into_iter()
        .enumerate()
        .map(|(i, (name, actions))| {
            let game = Game::from_actions(actions).expect("fixed fixture is legal");
            let snapshot = SnapshotDto::from_game(&game).expect("standard game snapshot");
            let position_key = snapshot.position_key.clone();
            let limits = SearchLimits {
                simulations: 96,
                max_nodes: 512,
                max_depth: 24,
            };
            let payload = AiStartPayloadDto {
                schema_version: SCHEMA_VERSION,
                meta: AiCorrelationDto {
                    protocol_version: AI_PROTOCOL_VERSION,
                    engine_build_id: AI_ENGINE_BUILD_ID.to_owned(),
                    request_id: (i + 1) as u32,
                    game_epoch: 1,
                    revision: actions.len() as u32 + 1,
                    position_key,
                    ruleset_id: quoridor_core::RULESET_ID.to_owned(),
                    worker_generation: 1,
                },
                snapshot: serde_json::to_vec(&snapshot).expect("snapshot JSON"),
                limits: SearchLimitsDto {
                    simulations: limits.simulations,
                    max_nodes: limits.max_nodes,
                    max_depth: limits.max_depth,
                },
                seed: "1979".to_owned(),
            };
            let mut search =
                SearchSession::b0(game.position(), limits, 1979).expect("valid fixture");
            while !search.done() {
                search.step(4);
            }
            let result = search.finish();
            let expected = AiResultDto {
                action_id: result.action,
                stats: AiStatsDto::from(result.stats),
            };
            json!({ "name": name, "payload": payload, "expected": expected })
        })
        .collect();
    println!(
        "{}",
        serde_json::to_string_pretty(&fixtures).expect("fixture JSON")
    );
}
