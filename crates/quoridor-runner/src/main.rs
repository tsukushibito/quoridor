use quoridor_data::Result;
use quoridor_runner::{config::Config, runtime};
use std::{
    fs::{File, OpenOptions},
    path::PathBuf,
    process::Command,
};
fn argument(args: &[String], name: &str) -> Result<String> {
    let i = args
        .iter()
        .position(|a| a == name)
        .ok_or_else(|| format!("missing {name}"))?;
    args.get(i + 1)
        .cloned()
        .ok_or_else(|| format!("missing value {name}").into())
}
fn strict_pairs(args: &[String], required: &[&str], optional: &[&str]) -> Result<()> {
    let mut seen = std::collections::BTreeSet::new();
    let tail = args.get(1..).ok_or("missing command")?;
    if !tail.len().is_multiple_of(2) {
        return Err("flags require explicit values".into());
    }
    for pair in tail.as_chunks::<2>().0 {
        if !required.contains(&pair[0].as_str()) && !optional.contains(&pair[0].as_str())
            || !seen.insert(pair[0].as_str())
            || pair[1].starts_with("--")
        {
            return Err("unknown/duplicate flag or missing value".into());
        }
    }
    if required.iter().any(|name| !seen.contains(name)) {
        return Err("required explicit flag missing".into());
    }
    Ok(())
}

fn prepare_teacher_inputs(args: &[String]) -> Result<serde_json::Value> {
    strict_pairs(args, &["--prepare-inputs", "--input-sha256"], &[])?;
    let bound = quoridor_data::terminal_stream::BoundJson {
        path: argument(args, "--prepare-inputs")?.into(),
        sha256: argument(args, "--input-sha256")?,
    };
    let config: quoridor_runner::teacher_pilot::depth6::InputConfig =
        serde_json::from_value(bound.read()?)?;
    let result = quoridor_runner::teacher_pilot::depth6::prepare_inputs(&config)?;
    Ok(serde_json::json!({"config": bound, "result": result}))
}

fn main() {
    // Disable before dlopen/CreateEnv can initialize ORT's telemetry SDK.
    // SAFETY: entrypoint initialization, before this program starts any threads.
    unsafe { std::env::set_var("ORT_DISABLE_TELEMETRY", "1") };
    if let Err(e) = execute() {
        eprintln!("{e}");
        std::process::exit(1)
    }
}
fn execute() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let command = args.first().map(String::as_str).unwrap_or("help");
    if args.iter().any(|a| a == "--report-mode") {
        if command != "arena" || argument(&args, "--report-mode")? != "receipt" {
            return Err("only arena report-mode receipt is supported".into());
        }
        let route = if args.iter().any(|a| a == "--recover") {
            "--recover"
        } else if args.iter().any(|a| a == "--audit") {
            "--audit"
        } else {
            "--config"
        };
        strict_pairs(&args, &[route, "--report-mode"], &[])?;
    }
    match command {
        "strength-book" | "strength-configs" => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let bound = quoridor_runner::research_manifest::BoundControl {
                path: argument(&args, "--experiment")?.into(),
                sha256: argument(&args, "--experiment-sha256")?,
            };
            let phase = match command {
                "strength-book" => "generation",
                "strength-configs" => "materialize",
                _ => unreachable!(),
            };
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::value_search_strength::execute(
                    &bound, phase
                )?)?
            );
        }
        #[cfg(feature = "measurement")]
        "measure" => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let report = quoridor_runner::measurement::run(
                &quoridor_runner::research_manifest::BoundControl {
                    path: argument(&args, "--experiment")?.into(),
                    sha256: argument(&args, "--experiment-sha256")?,
                },
            )?;
            println!(
                "{}",
                serde_json::to_string(&serde_json::json!({
                    "records_saved": true,
                    "status": report.get("status"),
                    "runtime_launch_origin": report.get("runtime_launch_origin"),
                }))?
            );
        }
        "value-search-compare" => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let report = quoridor_runner::value_search_compare::run(
                &quoridor_runner::research_manifest::BoundControl {
                    path: argument(&args, "--experiment")?.into(),
                    sha256: argument(&args, "--experiment-sha256")?,
                },
            )?;
            println!("{}", serde_json::to_string(&report)?);
        }
        "teacher-pilot" if args.iter().any(|a| a == "--experiment") => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let bound = quoridor_runner::research_manifest::BoundControl {
                path: argument(&args, "--experiment")?.into(),
                sha256: argument(&args, "--experiment-sha256")?,
            };
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::teacher_pilot_execution::run_bound(
                    &bound
                )?)?
            );
        }
        "teacher-pilot" if args.iter().any(|a| a == "--prepare-inputs") => {
            println!(
                "{}",
                serde_json::to_string(&prepare_teacher_inputs(&args)?)?
            );
        }
        "teacher-pilot" if args.iter().any(|a| a == "--audit") => {
            strict_pairs(&args, &["--audit"], &[])?;
            let output = PathBuf::from(argument(&args, "--audit")?);
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::teacher_pilot_execution::audit(&output)?)?
            );
        }
        "teacher-pilot" => {
            return Err(
                "teacher-pilot requires bound --experiment, --prepare-inputs or saved --audit"
                    .into(),
            );
        }
        "arena" if args.iter().any(|a| a == "--recover") => {
            strict_pairs(&args, &["--recover"], &["--report-mode"])?;
            let output = PathBuf::from(argument(&args, "--recover")?);
            let recovered = quoridor_runner::recover_arena(&output)?;
            if args.iter().any(|a| a == "--report-mode") {
                println!(
                    "{}",
                    serde_json::json!({"output":output,"finalized":false,"partial_journal_tail":recovered["partial_journal_tail"],"missing_slots":recovered["missing_slots"],"summary":recovered["summary"],"observed_outcome_count":recovered["observed_outcomes"].as_array().map(Vec::len),"full_observations":"retained completed.jsonl and result.json when available; not stdout"})
                );
            } else {
                println!("{}", serde_json::to_string(&recovered)?);
            }
        }
        "decisions" => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let bound = quoridor_runner::research_manifest::BoundControl {
                path: argument(&args, "--experiment")?.into(),
                sha256: argument(&args, "--experiment-sha256")?,
            };
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::arena::decisions_bound(&bound)?)?
            );
        }
        "arena" if args.iter().any(|a| a == "--audit") => {
            strict_pairs(&args, &["--audit"], &["--report-mode"])?;
            let output = PathBuf::from(argument(&args, "--audit")?);
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::audit_arena(&output)?)?
            );
        }
        "arena" if args.iter().any(|a| a == "--experiment") => {
            strict_pairs(&args, &["--experiment", "--experiment-sha256"], &[])?;
            let bound = quoridor_runner::research_manifest::BoundControl {
                path: argument(&args, "--experiment")?.into(),
                sha256: argument(&args, "--experiment-sha256")?,
            };
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::arena::run_bound(&bound)?)?
            );
        }
        "selfplay" | "arena" => {
            strict_pairs(&args, &["--config"], &["--report-mode"])?;
            let config: Config =
                serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
            if config
                .arena
                .as_ref()
                .is_some_and(|a| a.comparison != quoridor_runner::arena::Comparison::Functional)
            {
                return Err("research arena requires the bound --experiment entry".into());
            }
            let report = runtime::run(&config, command)?;
            if args.iter().any(|a| a == "--report-mode") {
                let output = PathBuf::from(argument(&args, "--config")?);
                let c: Config = serde_json::from_reader(File::open(output)?)?;
                println!(
                    "{}",
                    quoridor_runner::value_search_strength::result_receipt(&c, &report)?
                );
            } else if config.common_study.is_some() {
                println!(
                    "{}",
                    serde_json::json!({"result":config.output.join("result.json"),"planned":report.planned,"returned":report.outcomes.len(),"rows":report.rows,"eligible_rows":report.eligible_rows,"stopped":report.stopped,"payload_saved":true})
                );
            } else {
                println!("{}", serde_json::to_string(&report)?);
            }
            if report.stopped.is_some() || !report.all_workers_joined {
                return Err("run incomplete: evidence saved".into());
            }
        }
        "benchmark" => {
            strict_pairs(&args, &["--config"], &[])?;
            let config: Config =
                serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
            let report = runtime::benchmark(&config)?;
            if config.benchmark_repetitions.is_some() {
                println!(
                    "{}",
                    serde_json::json!({"result":config.output.join("result.json"),
                    "completed":report["records"].as_array().map(Vec::len),
                    "stopped":report["stopped"],"payload_saved":true})
                );
            } else {
                println!("{}", serde_json::to_string(&report)?);
            }
        }
        "dataset" => {
            let action = args
                .get(1)
                .map(String::as_str)
                .ok_or("dataset requires cache/inspect/evaluate")?;
            let input = PathBuf::from(argument(&args, "--input")?);
            match action {
                "cache" => {
                    let output = PathBuf::from(argument(&args, "--output")?);
                    let manifest = quoridor_data::write_tensor_cache(
                        &input,
                        &output,
                        args.iter().any(|a| a == "--allow-test"),
                    )?;
                    println!("{}", serde_json::to_string(&manifest)?);
                }
                "evaluate" => {
                    let model = quoridor_nnue::LoadedModel::load(PathBuf::from(argument(
                        &args, "--model",
                    )?))
                    .map_err(|e| e.to_string())?;
                    let output = OpenOptions::new()
                        .create_new(true)
                        .write(true)
                        .open(argument(&args, "--output")?)?;
                    let mut writer = std::io::BufWriter::new(output);
                    let mode = if args.iter().any(|a| a == "--simd") {
                        quoridor_nnue::EvaluationMode::Simd
                    } else {
                        quoridor_nnue::EvaluationMode::Scalar
                    };
                    let mut count = 0;
                    quoridor_data::for_each_row(
                        &input,
                        args.iter().any(|a| a == "--allow-test"),
                        |r| {
                            let features = quoridor_nnue::Features {
                                ids: r.ids.clone(),
                                distance: r.distance,
                                side: r.side - 1,
                            };
                            let value = model
                                .evaluate_features(features, mode)
                                .map_err(|e| e.to_string())?;
                            serde_json::to_writer(
                                &mut writer,
                                &serde_json::json!({"id":r.id,"split":r.split,"value":value}),
                            )?;
                            std::io::Write::write_all(&mut writer, b"\n")?;
                            count += 1;
                            Ok(())
                        },
                    )?;
                    std::io::Write::flush(&mut writer)?;
                    println!(
                        "{}",
                        serde_json::json!({"rows":count,"test_labels_opened":args.iter().any(|a|a=="--allow-test")})
                    );
                }
                "inspect" => {
                    let rows = quoridor_data::read_dataset(
                        &input,
                        args.iter().any(|a| a == "--allow-test"),
                    )?;
                    println!(
                        "{}",
                        serde_json::json!({"rows":rows.len(),"eligible":rows.iter().filter(|r|r.eligible).count(),"test_labels_opened":args.iter().any(|a|a=="--allow-test")})
                    );
                }
                _ => return Err("unknown dataset action".into()),
            }
        }
        "cycle" => {
            strict_pairs(&args, &["--config"], &[])?;
            let config: Config =
                serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
            let cycle = config.cycle.clone().ok_or("cycle settings required")?;
            let exe = std::env::current_exe()?;
            let config_path = PathBuf::from(argument(&args, "--config")?).canonicalize()?;
            let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .parent()
                .unwrap()
                .to_owned();
            let status = Command::new(cycle.python)
                .arg("-m")
                .arg("quoridor_training.cycle")
                .arg("--config")
                .arg(config_path)
                .arg("--runner")
                .arg(exe)
                .env("PYTHONPATH", repo.join("python"))
                .status()?;
            if !status.success() {
                return Err(format!("learning cycle failed: {status}").into());
            }
        }
        "model-check" => {
            let path = PathBuf::from(argument(&args, "--model")?);
            let model = quoridor_nnue::LoadedModel::load(&path).map_err(|e| e.to_string())?;
            println!(
                "{}",
                serde_json::json!({"format": model.format(), "fingerprint": model.fingerprint()})
            );
        }
        "qf1-bulk" => {
            let prefix_json: Vec<Vec<u16>> =
                serde_json::from_reader(File::open(argument(&args, "--input")?)?)?;
            let mut output = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(argument(&args, "--output")?)?;
            let mut features = Vec::new();
            for p in prefix_json {
                features.push(qf1_prefix_record(&p)?);
            }
            serde_json::to_writer(&mut output, &features)?;
        }
        "help" | "--help" | "-h" => println!("{HELP}"),
        _ => return Err("unknown command; use --help".into()),
    }
    Ok(())
}

const HELP: &str = "quoridor-runner teacher-pilot --prepare-inputs SETTINGS --input-sha256 SHA256\nquoridor-runner teacher-pilot --experiment EXPERIMENT --experiment-sha256 SHA256\nquoridor-runner arena --experiment EXPERIMENT --experiment-sha256 SHA256\nquoridor-runner strength-book --experiment EXPERIMENT --experiment-sha256 SHA256\nquoridor-runner strength-configs --experiment EXPERIMENT --experiment-sha256 SHA256\nquoridor-runner arena --config CONFIG --report-mode receipt\nquoridor-runner <selfplay|arena|benchmark|cycle> --config CONFIG\nquoridor-runner arena --audit OUTPUT_DIRECTORY\nquoridor-runner arena --recover OUTPUT_DIRECTORY\nquoridor-runner dataset <cache|inspect> --input PATH [--output PATH] [--allow-test]\nquoridor-runner dataset evaluate --input PATH --model MODEL --output PATH [--simd] [--allow-test]\nquoridor-runner model-check --model MODEL\nquoridor-runner qf1-bulk --input PREFIXES.json --output FEATURES.json\nSigma dataset import: use the separate sigma-import binary";

#[cfg(test)]
mod tests {

    #[test]
    fn help_exposes_supported_dataset_commands() {
        assert!(super::HELP.contains("dataset evaluate"));
        assert!(super::HELP.contains("dataset <cache|inspect>"));
        assert!(!super::HELP.contains("dataset <import"));
        assert!(super::HELP.contains("model-check --model"));
    }
}

#[cfg(test)]
mod generic_arena_361_cli_tests {
    #[test]
    fn generic_arena_361_cli_cannot_override_parent_approved_plan_or_mix_config_route() {
        let argv = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        let required = ["--experiment", "--experiment-sha256"];
        assert!(
            super::strict_pairs(
                &argv(&["arena", "--experiment", "e", "--experiment-sha256", "h"]),
                &required,
                &[]
            )
            .is_ok()
        );
        for suffix in ["--config", "--approved-plan-sha256", "--depth"] {
            assert!(
                super::strict_pairs(
                    &argv(&[
                        "arena",
                        "--experiment",
                        "e",
                        "--experiment-sha256",
                        "h",
                        suffix,
                        "x"
                    ]),
                    &required,
                    &[]
                )
                .is_err()
            );
        }
    }
}

#[cfg(test)]
mod no_cost_prediction_tests {
    use super::*;
    #[test]
    fn no_cost_prediction_current_config_flags_refuse_obsolete_or_unknown_authority() {
        for flag in [
            "--sigma-cost-qualification",
            "--qualification-sha256",
            "--unknown",
        ] {
            let args = ["arena", "--config", "c", flag, "x"].map(String::from);
            assert!(strict_pairs(&args, &["--config"], &["--report-mode"]).is_err());
        }
        let args = ["arena", "--config", "c"].map(String::from);
        assert!(strict_pairs(&args, &["--config"], &["--report-mode"]).is_ok());
    }
}

#[cfg(test)]
mod configured_teacher_input_tests {
    use super::*;

    #[test]
    fn configured_input_entry_binds_settings_before_global_schedule_publication() {
        struct Scratch(PathBuf);
        impl Drop for Scratch {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
        let scratch = Scratch(std::env::temp_dir().join(format!(
                "configured-input-port-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            )));
        std::fs::create_dir(&scratch.0).unwrap();
        let output = scratch.0.join("inputs");
        let path = scratch.0.join("settings.json");
        let config = serde_json::json!({"families":3,"prefix_seed":17,"prefix_lengths":[4,2],"split_seed":23,"excluded_books":[],"output":output});
        std::fs::write(&path, serde_json::to_vec(&config).unwrap()).unwrap();
        let mut args = vec![
            "teacher-pilot".into(),
            "--prepare-inputs".into(),
            path.to_string_lossy().into_owned(),
            "--input-sha256".into(),
            "0".repeat(64),
        ];
        assert!(prepare_teacher_inputs(&args).is_err());
        assert!(!output.exists());
        args[4] = quoridor_data::file_sha(&path).unwrap();
        let mut unknown = args.clone();
        unknown.extend(["--config".into(), "obsolete".into()]);
        assert!(prepare_teacher_inputs(&unknown).is_err());
        assert!(!output.exists());
        let actual = prepare_teacher_inputs(&args).unwrap();
        assert_eq!(actual["result"]["families"], 3);
        assert_eq!(actual["result"]["search_calls"], 0);
        assert_eq!(actual["result"]["outcomes_selected"], false);
        let schedule: quoridor_data::terminal_stream::BoundJson =
            serde_json::from_value(actual["result"]["schedule"].clone()).unwrap();
        let rows = schedule.read().unwrap();
        assert_eq!(rows["scheduled"].as_array().unwrap().len(), 3);
        let partition: quoridor_data::terminal_stream::BoundJson =
            serde_json::from_value(actual["result"]["partition"].clone()).unwrap();
        assert!(partition.read().is_ok());
        assert!(prepare_teacher_inputs(&args).is_err());
    }
}

/// Preserve QF1 fields; legal IDs belong to the same full-prefix common owner.
fn qf1_prefix_record(prefix: &[u16]) -> Result<serde_json::Value> {
    let context =
        quoridor_core::research::SigmaContext::from_prefix(prefix).map_err(|e| format!("{e:?}"))?;
    let f = quoridor_nnue::encode_qf1(context.position()).map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "ids":f.ids,"distance":f.distance,"side":f.side+1,
        "prefix":prefix,"legal":context.legal_ids(),
    }))
}

#[cfg(test)]
mod claustrophobia_file_inlet_tests {
    use super::*;

    #[test]
    fn claustrophobia16_qf1_legal_publication_preserves_fields_side_and_jump() {
        for prefix in [
            vec![],
            vec![13],
            vec![81, 163],
            vec![13, 67, 22, 58, 31, 49, 40, 31],
        ] {
            let context = quoridor_core::research::SigmaContext::from_prefix(&prefix).unwrap();
            let features = quoridor_nnue::encode_qf1(context.position()).unwrap();
            let row = qf1_prefix_record(&prefix).unwrap();
            assert_eq!(row["prefix"], serde_json::json!(prefix));
            assert_eq!(row["ids"], serde_json::json!(features.ids));
            assert_eq!(row["distance"], serde_json::json!(features.distance));
            assert_eq!(row["side"], features.side + 1);
            let legal: Vec<u16> = serde_json::from_value(row["legal"].clone()).unwrap();
            assert_eq!(legal, context.legal_ids());
            assert!(legal.iter().all(|&a| a < 209));
            assert_eq!(
                legal
                    .iter()
                    .collect::<std::collections::BTreeSet<_>>()
                    .len(),
                legal.len()
            );
        }
        let initial = qf1_prefix_record(&[]).unwrap();
        let legal: Vec<u16> = serde_json::from_value(initial["legal"].clone()).unwrap();
        for action in [3, 5, 13, 81, 145] {
            assert!(legal.contains(&action));
        }
        let side1 = qf1_prefix_record(&[13]).unwrap();
        assert_eq!(side1["side"], 2);
        assert!(
            side1["legal"]
                .as_array()
                .unwrap()
                .contains(&serde_json::json!(67))
        );
        let jump = qf1_prefix_record(&[13, 67, 22, 58, 31, 49, 40, 31]).unwrap();
        let legal: Vec<u16> = serde_json::from_value(jump["legal"].clone()).unwrap();
        assert!(legal.contains(&22));
        assert!(!legal.contains(&31));
    }

    #[test]
    fn claustrophobia16_qf1_legal_publication_rejects_bad_replay_and_keeps_terminal_history() {
        assert!(qf1_prefix_record(&[209]).is_err());
        assert!(qf1_prefix_record(&[80]).is_err());
        let draw = [3, 75, 4, 76, 3, 75, 4, 76];
        let context = quoridor_core::research::SigmaContext::from_prefix(&draw).unwrap();
        assert_eq!(context.terminal_value(), Some(0.0));
        assert!(!context.position().legal_action_ids().is_empty());
        let row = qf1_prefix_record(&draw).unwrap();
        assert_eq!(row["legal"], serde_json::json!([]));
        assert_eq!(row["prefix"], serde_json::json!(draw));
        assert_eq!(row["side"], 1);
        let mut after_terminal = draw.to_vec();
        after_terminal.push(3);
        assert!(qf1_prefix_record(&after_terminal).is_err());
    }
}
