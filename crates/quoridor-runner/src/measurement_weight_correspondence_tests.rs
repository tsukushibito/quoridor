//! One explicitly invoked check of changed exported weights, using canonical primitives.
use crate::research_manifest::FileRef;
use quoridor_ai::alphabeta::{ResidualEvaluator, StaticEvaluator};
use quoridor_core::research::SigmaContext;
use quoridor_data::Result;
use quoridor_nnue::{Accumulator, EvaluationMode, residual::ResidualModel};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    cell::{Cell, RefCell},
    fs,
    path::PathBuf,
    sync::Arc,
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    descriptor: FileRef,
    weights: FileRef,
    normalization_descriptor: FileRef,
    book: FileRef,
    prefixes: Vec<Vec<u16>>,
    state_cap: u64,
    head_cap: u64,
}

fn close(a: f32, b: f32) {
    assert!(a.is_finite() && b.is_finite());
    assert!((a - b).abs() <= 1e-5 + 1e-4 * a.abs());
}

#[test]
#[ignore = "actual changed weights; owning numerical job must bind inputs and account every head"]
fn changed_export_full_delta_and_parent_restore_once() -> Result<()> {
    let input_path = PathBuf::from(std::env::var("QUORIDOR_CHANGED_WEIGHTS_INPUT")?);
    let output_path = PathBuf::from(std::env::var("QUORIDOR_CHANGED_WEIGHTS_OUTPUT")?);
    let raw = fs::read(&input_path)?;
    assert_eq!(
        crate::arena::digest(&raw),
        std::env::var("QUORIDOR_CHANGED_WEIGHTS_INPUT_SHA256")?
    );
    let input: Input = serde_json::from_slice(&raw)?;
    assert!(!output_path.exists() && !input.prefixes.is_empty());
    for file in [
        &input.descriptor,
        &input.weights,
        &input.normalization_descriptor,
        &input.book,
    ] {
        file.verify()?;
    }
    let descriptor: Value = input.descriptor.read()?;
    let incumbent: Value = input.normalization_descriptor.read()?;
    assert_eq!(descriptor["weights_SHA"], input.weights.sha256);
    assert_eq!(
        input.descriptor.path.parent().unwrap().join("weights.f32"),
        input.weights.path
    );
    for key in [
        "mu_f32",
        "sigma_f32",
        "feature",
        "schema",
        "route_mode",
        "topology",
        "route_mu_f32",
        "route_sigma_f32",
        "value_perspective",
    ] {
        assert_eq!(descriptor[key], incumbent[key]);
    }
    for key in ["a", "b"] {
        assert_eq!(
            descriptor["distance_fit"][key].as_f64(),
            incumbent["distance_fit"][key].as_f64()
        );
    }
    let book: Value = input.book.read()?;
    let expected: Vec<Vec<u16>> = book["openings"]
        .as_array()
        .ok_or("book openings")?
        .iter()
        .take(input.prefixes.len())
        .map(|row| serde_json::from_value(row["prefix"].clone()))
        .collect::<std::result::Result<_, _>>()?;
    assert_eq!(input.prefixes, expected);
    let heads = Cell::new(0_u64);
    let returned = Cell::new(0_u64);
    let states = Cell::new(0_u64);
    let fingerprint = RefCell::new(None::<String>);
    let mut rows = Vec::new();
    let persist = |status: &str, rows: &Vec<Value>| -> Result<()> {
        fs::write(
            &output_path,
            serde_json::to_vec(&json!({
                "status":status,"heads_started":heads.get(),"heads_returned":returned.get(),"distinct_states":states.get(),
                "rows":rows,"Search_calls":0,"new_Torch_calls":0,
                "physical_FT_and_head_hardware_counts":"UNKNOWN",
                "descriptor":input.descriptor,"weights":input.weights,
                "book":input.book,"input_sha256":crate::arena::digest(&raw),
                "native_evaluator_fingerprint":fingerprint.borrow().as_deref()
            }))?,
        )?;
        Ok(())
    };
    persist("PENDING_MODEL_ENTRY", &rows)?;
    let model = Arc::new(ResidualModel::load(&input.descriptor.path)?);
    *fingerprint.borrow_mut() = Some(quoridor_data::hex_digest(&model.fingerprint()));
    let evaluator = ResidualEvaluator::new(model.clone());
    let mut scratch = model.evaluation_scratch();
    let mut evaluate = |accumulator: &Accumulator, rows: &Vec<Value>| -> Result<f32> {
        assert!(heads.get() < input.head_cap);
        heads.set(heads.get() + 1);
        persist("PENDING_HEAD_RETURN", rows)?;
        let value = model.evaluate_with_scratch(accumulator, &mut scratch)?;
        returned.set(returned.get() + 1);
        persist("HEAD_RETURNED", rows)?;
        Ok(value)
    };
    let evaluate_factory = |context: &SigmaContext, rows: &Vec<Value>| -> Result<f32> {
        let accumulator = evaluator.prepare_context(context)?;
        assert!(heads.get() < input.head_cap);
        heads.set(heads.get() + 1);
        persist("PENDING_FACTORY_HEAD_RETURN", rows)?;
        let value = evaluator.evaluate(context, accumulator.as_ref())?;
        returned.set(returned.get() + 1);
        persist("FACTORY_HEAD_RETURNED", rows)?;
        Ok(value)
    };
    for prefix in &input.prefixes {
        let mut context = SigmaContext::from_prefix(prefix)?;
        context.validate_normal()?;
        assert!(context.terminal_value().is_none());
        states.set(states.get() + 1);
        assert!(states.get() <= input.state_cap);
        let before = (
            context.position(),
            context.history_counts(),
            context.total_ply(),
        );
        let parent = model.full_context(&context, EvaluationMode::Scalar)?;
        let parent_value = evaluate(&parent, &rows)?;
        close(parent_value, evaluate_factory(&context, &rows)?);
        let legal = context.legal_ids();
        let actions: Vec<_> = [0..81, 81..145, 145..209]
            .into_iter()
            .filter_map(|range| legal.iter().copied().find(|a| range.contains(a)))
            .collect();
        for action in actions {
            let expected = context.play(action)?;
            let undo = context.make_move(action)?;
            assert_eq!(context.position(), expected.position());
            assert_eq!(context.history_counts(), expected.history_counts());
            states.set(states.get() + 1);
            assert!(states.get() <= input.state_cap);
            let full = model.full_context(&context, EvaluationMode::Scalar)?;
            let delta = model.delta_context(&parent, &context)?;
            assert_eq!(full.features.ids, delta.features.ids);
            assert_eq!(full.features.side, delta.features.side);
            let value = evaluate(&full, &rows)?;
            close(value, evaluate(&delta, &rows)?);
            let simd = model.full_context(&context, EvaluationMode::Simd)?;
            let simd_parent =
                model.full_context(&SigmaContext::from_prefix(prefix)?, EvaluationMode::Simd)?;
            close(value, evaluate(&simd, &rows)?);
            close(
                value,
                evaluate(&model.delta_context(&simd_parent, &context)?, &rows)?,
            );
            close(value, evaluate_factory(&context, &rows)?);
            context.unmake_move(undo)?;
            assert_eq!(context.position(), before.0);
            assert_eq!(context.history_counts(), before.1);
            assert_eq!(context.total_ply(), before.2);
            close(
                parent_value,
                evaluate(
                    &model.full_context(&context, EvaluationMode::Scalar)?,
                    &rows,
                )?,
            );
            rows.push(json!({"prefix":prefix,"child_action":action,
                "parent_value":parent_value,"child_value":value,"parent_restored":true}));
            persist("PENDING_REMAINING_STATES", &rows)?;
        }
    }
    persist("COMPLETE", &rows)?;
    for file in [
        &input.descriptor,
        &input.weights,
        &input.normalization_descriptor,
        &input.book,
    ] {
        file.verify()?;
    }
    eprintln!("changed-weight contexts saved to {}", output_path.display());
    Ok(())
}

#[test]
#[ignore = "actual model identity only; no static evaluation or correspondence replay"]
fn changed_export_typed_identity_without_head() -> Result<()> {
    let input_path = PathBuf::from(std::env::var("QUORIDOR_CHANGED_WEIGHTS_INPUT")?);
    let output_path = PathBuf::from(std::env::var("QUORIDOR_CHANGED_WEIGHTS_OUTPUT")?);
    let raw = fs::read(&input_path)?;
    assert_eq!(
        crate::arena::digest(&raw),
        std::env::var("QUORIDOR_CHANGED_WEIGHTS_INPUT_SHA256")?
    );
    let input: Input = serde_json::from_slice(&raw)?;
    assert!(!output_path.exists());
    input.descriptor.verify()?;
    input.weights.verify()?;
    let model = ResidualModel::load(&input.descriptor.path)?;
    let model_fingerprint = model.fingerprint();
    let typed_identity = quoridor_data::hex_digest(&model_fingerprint);
    input.descriptor.verify()?;
    input.weights.verify()?;
    fs::write(
        output_path,
        serde_json::to_vec(&json!({
            "status":"COMPLETE", "descriptor":input.descriptor,"weights":input.weights,
            "model_raw_fingerprint_hex":model_fingerprint.iter().map(|b| format!("{b:02x}")).collect::<String>(),
            "typed_evaluator_sha256":typed_identity,"head_forwards":0,"Search_calls":0,
            "input_sha256":crate::arena::digest(&raw),"correspondence_replay":false,
            "identity_owner":"quoridor_data::hex_digest(model.fingerprint()), same as measurement::load_residual_model"
        }))?,
    )?;
    Ok(())
}
