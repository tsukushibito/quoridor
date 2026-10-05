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
    match command {
        "selfplay" | "arena" => {
            let config: Config =
                serde_json::from_reader(File::open(argument(&args, "--config")?)?)?;
            let report = runtime::run(&config, command)?;
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
                    let model =
                        quoridor_nnue::Model::load(PathBuf::from(argument(&args, "--model")?))
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
                            let a = model
                                .full_features(features, mode)
                                .map_err(|e| e.to_string())?;
                            let value = model.evaluate(&a).map_err(|e| e.to_string())?;
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
        "help" | "--help" | "-h" => println!(
            "quoridor-runner <selfplay|arena|benchmark|cycle> --config CONFIG\nquoridor-runner dataset <import|cache|inspect> --input PATH [--output PATH] [--allow-test]\nquoridor-runner qf1-bulk --input PREFIXES.json --output FEATURES.json"
        ),
        _ => return Err("unknown command; use --help".into()),
    }
    Ok(())
}
