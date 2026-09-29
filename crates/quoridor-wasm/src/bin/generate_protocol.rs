use quoridor_wasm::wire::{
    AiCorrelationDto, AiResultDto, AiStartPayloadDto, AiStatsDto, AiWorkerRequestDto,
    AiWorkerResponseDto, GameViewDto, NewGameConfigDto, ReplayDto, SearchLimitsDto, SnapshotDto,
};
use ts_rs::{Config, TS};

fn main() {
    println!("// Generated from quoridor-wasm/src/wire.rs. Do not edit by hand.");
    let config = Config::default();
    for (index, declaration) in [
        NewGameConfigDto::decl(&config),
        GameViewDto::decl(&config),
        ReplayDto::decl(&config),
        SnapshotDto::decl(&config),
        AiCorrelationDto::decl(&config),
        SearchLimitsDto::decl(&config),
        AiStartPayloadDto::decl(&config),
        AiStatsDto::decl(&config),
        AiResultDto::decl(&config),
        AiWorkerRequestDto::decl(&config),
        AiWorkerResponseDto::decl(&config),
    ]
    .into_iter()
    .enumerate()
    {
        if index > 0 {
            println!();
        }
        println!("export {declaration}");
    }
}
