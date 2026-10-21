use super::{Config, Result, guard, save};
use quoridor_nnue::{
    EvaluationMode, Features,
    residual::{ResidualManifest, ResidualModel},
};
use quoridor_runner::arena::{digest, sha_valid};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{collections::BTreeSet, fs, time::Instant};
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    ordinal: u64,
    record_sha256: String,
    features_sha256: String,
    ids: [Vec<u16>; 2],
    distance: [f32; 2],
    native_side: u8,
    torch_side: u8,
    expected: f32,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Packet {
    schema: String,
    manifest_sha256: String,
    weights_sha256: String,
    reference_source_sha256: String,
    rows: Vec<Row>,
}
fn input_bytes(row: &Row) -> Vec<u8> {
    let mut bytes = Vec::new();
    for ids in &row.ids {
        for k in 0..312_u16 {
            bytes.extend_from_slice(&(if ids.contains(&k) { 1_f32 } else { 0_f32 }).to_le_bytes());
        }
    }
    for d in row.distance {
        bytes.extend_from_slice(&d.to_le_bytes());
    }
    bytes.extend_from_slice(&i64::from(row.torch_side).to_le_bytes());
    bytes
}
fn validate(p: &Packet) -> Result<()> {
    if p.schema != "native-residual-reference-v1"
        || p.rows.len() != 16
        || [
            &p.manifest_sha256,
            &p.weights_sha256,
            &p.reference_source_sha256,
        ]
        .iter()
        .any(|s| !sha_valid(s))
    {
        return Err("REFERENCE_SCHEMA_SHAPE_BINDING".into());
    }
    let mut ordinals = BTreeSet::new();
    for r in &p.rows {
        if !ordinals.insert(r.ordinal)
            || r.native_side != 0
            || r.torch_side != 1
            || !r.expected.is_finite()
            || r.expected.abs() > 1.
            || r.distance
                .iter()
                .any(|d| !d.is_finite() || !(0. ..=1.).contains(d))
            || [&r.record_sha256, &r.features_sha256]
                .iter()
                .any(|s| !sha_valid(s))
            || r.ids.iter().any(|v| {
                v.len() > 24
                    || v.windows(2).any(|w| w[0] >= w[1])
                    || v.iter().any(|k| *k >= 312)
                    || [(0, 81), (81, 162), (290, 301), (301, 312)]
                        .iter()
                        .any(|&(lo, hi)| v.iter().filter(|&&k| k >= lo && k < hi).count() != 1)
            })
        {
            return Err("REFERENCE_INPUT_FINITE_SIDE_QF1".into());
        }
        if digest(&input_bytes(r)) != r.features_sha256 {
            return Err("REFERENCE_INPUT_SHA".into());
        }
    }
    if p.rows.windows(2).any(|w| w[0].ordinal >= w[1].ordinal) {
        return Err("REFERENCE_ROW_ORDER".into());
    }
    Ok(())
}
pub(super) fn run(c: &Config, start: Instant) -> Result<Value> {
    if c.engines.len() != 1
        || c.engines[0].kind != "distance_residual"
        || !c.prefixes.is_empty()
        || !c.depths.is_empty()
        || c.generate.is_some()
        || c.max_plies != 0
    {
        return Err("INPUT_ONLY".into());
    }
    let path = c.input.as_ref().ok_or("REFERENCE_INPUT_REQUIRED")?;
    if fs::metadata(path)?.len() > 65536 {
        return Err("REFERENCE_INPUT_BYTES".into());
    }
    let bytes = fs::read(path)?;
    if c.input_sha256 != Some(digest(&bytes)) {
        return Err("INPUT_SHA".into());
    }
    let p: Packet = serde_json::from_slice(&bytes)?;
    validate(&p)?;
    let manifest = c.engines[0].manifest.as_ref().ok_or("manifest")?;
    let mbytes = fs::read(manifest)?;
    let m: ResidualManifest = serde_json::from_slice(&mbytes)?;
    if digest(&mbytes) != p.manifest_sha256 || m.weights_sha != p.weights_sha256 {
        return Err("REFERENCE_MODEL_BINDING".into());
    }
    let model = ResidualModel::load(manifest)?;
    let mut scratch = model.evaluation_scratch();
    let mut predictions = Vec::new();
    let mut attempted = 0;
    let mut completed = 0;
    let mut failures = 0;
    for r in &p.rows {
        for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
            guard(c, start, attempted, completed)?;
            attempted += 1;
            save(
                &c.counter,
                &json!({"attempted":attempted,"completed":completed,"failed":failures,"NN":attempted,"processed":completed}),
            )?;
            let mut route = Value::Null;
            let value = (|| -> Result<f32> {
                let a = model.full_features(
                    Features {
                        ids: r.ids.clone(),
                        distance: r.distance,
                        side: r.native_side,
                    },
                    mode,
                )?;
                Ok(model.evaluate_with_scratch_observed(&a, &mut scratch, |permit, avx2| {
                    route = json!({"range_permitted":permit,"selected":if permit&&avx2 {"avx2_lane8_no_fma"} else {"ordered_scalar"}});
                })?)
            })();
            match value {
                Ok(v) => {
                    completed += 1;
                    let error = v - r.expected;
                    predictions.push(json!({"ordinal":r.ordinal,"mode":format!("{mode:?}"),"value":v,"expected":r.expected,"signed_error":error,"guard_route":route,"within_alert":v.is_finite()&&error.abs()<=1e-5+1e-4*r.expected.abs()}));
                }
                Err(e) => {
                    failures += 1;
                    predictions.push(json!({"ordinal":r.ordinal,"mode":format!("{mode:?}"),"error":e.to_string(),"guard_route":route,"within_alert":false}));
                }
            }
        }
    }
    save(
        &c.counter,
        &json!({"attempted":attempted,"completed":completed,"failed":failures,"NN":attempted,"processed":completed}),
    )?;
    let pass = predictions.iter().all(|p| p["within_alert"] == true);
    let exe = std::env::current_exe()?;
    Ok(
        json!({"schema":p.schema,"status":if pass {"COMPATIBILITY_PASS_INPUT_ONLY"}else{"COMPATIBILITY_ALERT"},"input_sha256":digest(&bytes),"manifest_sha256":p.manifest_sha256,"weights_sha256":p.weights_sha256,"reference_source_sha256":p.reference_source_sha256,
        "predictions":predictions,"NN":attempted,"processed":completed,"failed":failures,"abs_tol":1e-5,"rel_tol":1e-4,"executable_sha256":digest(&fs::read(exe)?),
        "head_policy":"fp32_avx2_lane8_balanced_no_fma_guarded_scalar_fallback_v1","actual_per_input_guard_route":"predictions[].guard_route","qualification_complete":false,"limits":"Input correspondence only; legal/caller qualification separate.","wall_s":start.elapsed().as_secs_f64()}),
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    fn packet() -> Packet {
        let rows = (0..16)
            .map(|ordinal| {
                let mut r = Row {
                    ordinal,
                    record_sha256: "a".repeat(64),
                    features_sha256: String::new(),
                    ids: [vec![4, 157, 300, 311], vec![4, 157, 300, 311]],
                    distance: [0.1, 0.1],
                    native_side: 0,
                    torch_side: 1,
                    expected: 0.,
                };
                r.features_sha256 = digest(&input_bytes(&r));
                r
            })
            .collect();
        Packet {
            schema: "native-residual-reference-v1".into(),
            manifest_sha256: "b".repeat(64),
            weights_sha256: "c".repeat(64),
            reference_source_sha256: "d".repeat(64),
            rows,
        }
    }
    #[test]
    fn reject_bad_binding() {
        assert!(validate(&packet()).is_ok());
        for case in 0..6 {
            let mut p = packet();
            match case {
                0 => p.rows[0].native_side = 1,
                1 => {
                    p.rows.pop();
                }
                2 => p.rows[1].ordinal = 0,
                3 => p.rows[0].features_sha256 = "e".repeat(64),
                4 => p.rows[0].distance[0] = f32::NAN,
                _ => p.rows[0].ids[0].push(312),
            }
            assert!(validate(&p).is_err());
        }
    }
}
