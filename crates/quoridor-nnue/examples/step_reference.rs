//! Bounded general-input native reference inlet. Geometry/history qualification
//! uses the canonical context APIs separately; this inlet never labels a game.
use quoridor_nnue::{
    EvaluationMode, Features,
    distance_step::{ScoreView, StepModel},
};
use serde::Deserialize;
use std::{fs::File, io::Read, path::PathBuf};

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
enum FtMode {
    Scalar,
    Simd,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    manifest: PathBuf,
    ids: [Vec<u16>; 2],
    distance: [f32; 2],
    side: u8,
    integer_distance: [u8; 2],
    ft_mode: FtMode,
    view: ScoreView,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    schema: String,
    rows: Vec<Row>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 2 {
        return Err("usage: step_reference <bound-request.json>".into());
    }
    let file = File::open(&args[1])?;
    if file.metadata()?.len() > 65536 {
        return Err("reference input exceeds 64 KiB".into());
    }
    let mut bytes = Vec::new();
    file.take(65537).read_to_end(&mut bytes)?;
    if bytes.len() > 65536 {
        return Err("reference input grew beyond 64 KiB".into());
    }
    let request: Request = serde_json::from_slice(&bytes)?;
    if request.schema != "nnue-distance-step-general-reference-v1"
        || request.rows.is_empty()
        || request.rows.len() > 16
    {
        return Err("explicit general-input reference schema/1..16 rows required".into());
    }
    let mut outputs = Vec::with_capacity(request.rows.len());
    for (index, row) in request.rows.into_iter().enumerate() {
        let model = StepModel::load(&row.manifest)?;
        if row.view != model.default_view() {
            return Err("row view does not match frozen deployment manifest".into());
        }
        let mode = match row.ft_mode {
            FtMode::Scalar => EvaluationMode::Scalar,
            FtMode::Simd => EvaluationMode::Simd,
        };
        let input = Features {
            ids: row.ids,
            distance: row.distance,
            side: row.side,
        };
        let accumulator = model.full_features(input, mode, row.integer_distance)?;
        let mut scratch = model.evaluation_scratch();
        let mut route = (false, false);
        let value = model.evaluate_with_scratch_observed(
            &accumulator,
            &mut scratch,
            row.view,
            |permit, avx2| route = (permit, avx2),
        )?;
        outputs.push(serde_json::json!({
            "row": index, "score_identity": model.score_identity(row.view)?, "weights_SHA": model.weights_sha(),
            "ft_mode": match mode { EvaluationMode::Scalar => "scalar", EvaluationMode::Simd => "simd" },
            "raw_abs_bound": model.raw_abs_bound(), "derived_raw_abs_bound": model.derived_raw_abs_bound(),
            "value": value, "raw_bits": value.raw_steps.to_bits(), "value_bits": value.value.to_bits(),
            "range_permit": route.0, "AVX2_available": route.1, "head_AVX2_selected": route.0 && route.1
        }));
    }
    println!(
        "{}",
        serde_json::json!({
            "schema": "nnue-distance-step-general-reference-result-v1", "rows": outputs,
            "scope": "general numerical inputs only; no legal geometry/history/game certificate",
            "physical_kernels": "UNKNOWN"
        })
    );
    Ok(())
}
