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
fn qualified_route(command: &str, args: &[String]) -> Result<bool> {
    let present = args.iter().any(|a| {
        matches!(
            a.as_str(),
            "--sigma-cost-qualification" | "--qualification-sha256"
        )
    });
    if present
        && (command != "arena" && command != "sigma-cost-measure"
            || args
                .iter()
                .any(|a| matches!(a.as_str(), "--audit" | "--recover")))
    {
        return Err("qualification flags require the explicit arena or measurement route".into());
    }
    Ok(present)
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
    let qualified = qualified_route(command, &args)?;
    if command == "teacher-pilot"
        && !(args.len() == 3 && matches!(args[1].as_str(), "--config" | "--audit")
            || args.len() == 4 && args[1] == "--config" && args[3] == "--check-config")
    {
        return Err(
            "teacher-pilot accepts only the fixed config or saved audit; no fit/full/games inlet"
                .into(),
        );
    }
    match command {
        "sigma-cost-bindings" => {
            strict_pairs(&args, &["--config", "--config-sha256"], &[])?;
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::sigma_qualification::inspect_config(
                    quoridor_runner::sigma_qualification::BoundControl {
                        path: argument(&args, "--config")?.into(),
                        sha256: argument(&args, "--config-sha256")?,
                    },
                )?)?
            );
        }
        "sigma-cost-measure" => {
            use quoridor_runner::sigma_qualification::{BoundControl, MeasurementPlan};
            strict_pairs(
                &args,
                &["--plan", "--plan-sha256"],
                &["--sigma-cost-qualification", "--qualification-sha256"],
            )?;
            let plan_sha = argument(&args, "--plan-sha256")?;
            let plan: MeasurementPlan = BoundControl {
                path: argument(&args, "--plan")?.into(),
                sha256: plan_sha.clone(),
            }
            .read()?;
            let has_qualification = args.iter().any(|a| a == "--sigma-cost-qualification");
            if has_qualification != args.iter().any(|a| a == "--qualification-sha256")
                || (plan.mode == "qualified-timed") != has_qualification
            {
                return Err("untimed measurement refuses a bound; timed validation requires its SHA-bound measurement evidence".into());
            }
            let qualification = if has_qualification {
                Some(BoundControl {
                    path: argument(&args, "--sigma-cost-qualification")?.into(),
                    sha256: argument(&args, "--qualification-sha256")?,
                })
            } else {
                None
            };
            let report = runtime::measure_sigma_cost(plan, plan_sha, qualification)?;
            println!("{}", serde_json::to_string(&report)?);
            if report["complete"] != true {
                return Err(
                    "measurement incomplete: evidence retained; games are not qualified".into(),
                );
            }
        }
        "teacher-pilot" if args.iter().any(|a| a == "--audit") => {
            let output = PathBuf::from(argument(&args, "--audit")?);
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::teacher_pilot_execution::audit(&output)?)?
            );
        }
        "teacher-pilot" => {
            use sha2::{Digest, Sha256};
            let raw = std::fs::read(argument(&args, "--config")?)?;
            let config: quoridor_runner::teacher_pilot::PilotConfig = serde_json::from_slice(&raw)?;
            config.validate()?;
            let digest = format!("{:x}", Sha256::digest(&raw));
            if args.iter().any(|a| a == "--check-config") {
                println!(
                    "{}",
                    serde_json::json!({"pilot_config_sha256":digest,"valid":true,"main_volume_n":null,
                        "compiled_sources":quoridor_runner::teacher_pilot_execution::compiled_sources(),
                        "fixed_D":"original-distance-a0-b8-tanh","models_loaded":0})
                );
                return Ok(());
            }
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::teacher_pilot_execution::run(
                    &config, digest
                )?)?
            );
        }
        "arena" if args.iter().any(|a| a == "--recover") => {
            let output = PathBuf::from(argument(&args, "--recover")?);
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::recover_arena(&output)?)?
            );
        }
        "arena" if args.iter().any(|a| a == "--audit") => {
            let output = PathBuf::from(argument(&args, "--audit")?);
            println!(
                "{}",
                serde_json::to_string(&quoridor_runner::audit_arena(&output)?)?
            );
        }
        "selfplay" | "arena" => {
            if qualified {
                if command != "arena" {
                    return Err("qualified receipt caller belongs to explicit arena entry".into());
                }
                strict_pairs(
                    &args,
                    &[
                        "--config",
                        "--sigma-cost-qualification",
                        "--qualification-sha256",
                    ],
                    &[],
                )?;
            }
            let report = if qualified {
                let (config, qualification) =
                    quoridor_runner::sigma_qualification::load_qualified_entry(
                        &PathBuf::from(argument(&args, "--sigma-cost-qualification")?),
                        &argument(&args, "--qualification-sha256")?,
                        &PathBuf::from(argument(&args, "--config")?),
                    )?;
                runtime::run_with_sigma_cost_qualification(&config, command, None, qualification)?
            } else {
                let config: Config =
                    serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
                runtime::run(&config, command)?
            };
            println!("{}", serde_json::to_string(&report)?);
            if report.stopped.is_some() || !report.all_workers_joined {
                return Err("run incomplete: evidence saved".into());
            }
        }
        "benchmark" => {
            let config: Config =
                serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
            println!("{}", serde_json::to_string(&runtime::benchmark(&config)?)?);
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
                let context = quoridor_core::research::SigmaContext::from_prefix(&p)
                    .map_err(|e| format!("{e:?}"))?;
                let f = quoridor_nnue::encode_qf1(context.position()).map_err(|e| e.to_string())?;
                features
                    .push(serde_json::json!({"ids":f.ids,"distance":f.distance,"side":f.side+1}));
            }
            serde_json::to_writer(&mut output, &features)?;
        }
        "help" | "--help" | "-h" => println!("{HELP}"),
        _ => return Err("unknown command; use --help".into()),
    }
    Ok(())
}

const HELP: &str = "quoridor-runner <selfplay|arena|benchmark|cycle> --config CONFIG\nquoridor-runner arena --config CONFIG --sigma-cost-qualification PACKET --qualification-sha256 SHA256\nquoridor-runner sigma-cost-bindings --config CONFIG --config-sha256 SHA256\nquoridor-runner sigma-cost-measure --plan PLAN --plan-sha256 SHA256 [--sigma-cost-qualification VALIDATION_PACKET --qualification-sha256 SHA256]\nquoridor-runner arena --audit OUTPUT_DIRECTORY\nquoridor-runner arena --recover OUTPUT_DIRECTORY\nquoridor-runner dataset <cache|inspect> --input PATH [--output PATH] [--allow-test]\nquoridor-runner dataset evaluate --input PATH --model MODEL --output PATH [--simd] [--allow-test]\nquoridor-runner model-check --model MODEL\nquoridor-runner qf1-bulk --input PREFIXES.json --output FEATURES.json\nSigma dataset import: use the separate sigma-import binary";

#[cfg(test)]
mod tests {
    #[test]
    fn qualified_flags_refuse_partial_duplicate_and_unknown_routes() {
        let args = |values: &[&str]| values.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        for command in ["benchmark", "selfplay"] {
            assert!(
                super::qualified_route(
                    command,
                    &args(&[command, "--sigma-cost-qualification", "q"])
                )
                .is_err()
            );
        }
        assert!(
            super::qualified_route(
                "arena",
                &args(&["arena", "--audit", "x", "--sigma-cost-qualification", "q"])
            )
            .is_err()
        );
        let required = [
            "--config",
            "--sigma-cost-qualification",
            "--qualification-sha256",
        ];
        for values in [
            vec!["arena", "--config", "c"],
            vec!["arena", "--config", "c", "--config", "d"],
            vec!["arena", "--config", "c", "--unknown", "x"],
        ] {
            assert!(super::strict_pairs(&args(&values), &required, &[]).is_err());
        }
        assert!(
            super::strict_pairs(
                &args(&[
                    "arena",
                    "--config",
                    "c",
                    "--sigma-cost-qualification",
                    "q",
                    "--qualification-sha256",
                    "s"
                ]),
                &required,
                &[]
            )
            .is_ok()
        );
    }
    #[test]
    fn help_exposes_supported_dataset_commands() {
        assert!(super::HELP.contains("dataset evaluate"));
        assert!(super::HELP.contains("dataset <cache|inspect>"));
        assert!(!super::HELP.contains("dataset <import"));
        assert!(super::HELP.contains("model-check --model"));
    }
}
