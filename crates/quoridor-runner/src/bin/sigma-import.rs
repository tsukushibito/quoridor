//! Generic fixed-source Sigma original-plane stream to canonical external-z data.
use quoridor_data::{
    OutcomeImportConfig, for_each_row, import_sigma_outcomes, sigma_plane_position,
    write_input_references, write_tensor_cache,
};
use std::{
    fs::File,
    io::{BufWriter, Read, Write},
    path::PathBuf,
};
fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() == 5 && args[1] == "--qualify-inputs" && args[3] == "--output" {
        let count: usize = args[2].parse()?;
        if count > 1_000_000 {
            return Err("input qualification count exceeds bound".into());
        }
        let mut input = std::io::stdin().lock();
        let mut writer = BufWriter::new(
            File::options()
                .write(true)
                .create_new(true)
                .open(&args[4])?,
        );
        for _ in 0..count {
            let mut index = [0u8; 8];
            input.read_exact(&mut index)?;
            let mut payload = [0u8; 648 * 4];
            input.read_exact(&mut payload)?;
            let planes = std::array::from_fn(|i| {
                f32::from_le_bytes(payload[i * 4..(i + 1) * 4].try_into().unwrap())
            });
            let error = sigma_plane_position(&planes).err().map(|e| e.to_string());
            serde_json::to_writer(
                &mut writer,
                &serde_json::json!({
                    "original_index": u64::from_le_bytes(index),
                    "input_valid": error.is_none(), "reason": error,
                }),
            )?;
            writer.write_all(b"\n")?;
        }
        if input.read(&mut [0u8; 1])? != 0 {
            return Err("trailing qualification stream bytes".into());
        }
        writer.flush()?;
        println!("{{\"qualified_input_records\":{count},\"NN\":0,\"labels_read\":0}}");
        return Ok(());
    }
    if args.len() == 5 && args[1] == "--config" && args[3] == "--receipt" {
        let config: OutcomeImportConfig = serde_json::from_reader(File::open(&args[2])?)?;
        let result = import_sigma_outcomes(std::io::stdin().lock(), &config)?;
        let path = PathBuf::from(&args[4]);
        let mut out = BufWriter::new(File::options().write(true).create_new(true).open(path)?);
        serde_json::to_writer_pretty(&mut out, &result)?;
        out.flush()?;
        return Ok(());
    }
    if (args.len() == 6 || args.len() == 7) && args[2] == "--input" && args[4] == "--output" {
        let allow = args.len() == 7 && args[6] == "--allow-test";
        let input = PathBuf::from(&args[3]);
        let output = PathBuf::from(&args[5]);
        match args[1].as_str() {
            "cache" => {
                println!(
                    "{}",
                    serde_json::to_string(&write_tensor_cache(&input, &output, allow)?)?
                );
            }
            "labels" => {
                let mut writer =
                    BufWriter::new(File::options().write(true).create_new(true).open(output)?);
                let mut count = 0;
                for_each_row(&input, allow, |row| {
                    serde_json::to_writer(
                        &mut writer,
                        &serde_json::json!({
                            "id": row.id,
                            "native_family": row.family,
                            "rootmean": row.teacher.value(),
                            "z": row.z,
                        }),
                    )?;
                    writer.write_all(b"\n")?;
                    count += 1;
                    Ok(())
                })?;
                writer.flush()?;
                println!("{{\"rows\":{count}}}");
            }
            // Static-teacher input/value projection: current research data, never sealed test.
            "static-label-inputs" => {
                if allow {
                    return Err("static teacher input projection cannot read sealed test".into());
                }
                let sink: Box<dyn Write> = if output.as_os_str() == "-" {
                    Box::new(std::io::stdout())
                } else {
                    Box::new(File::options().write(true).create_new(true).open(output)?)
                };
                let mut writer = BufWriter::new(sink);
                let mut count = 0;
                for_each_row(&input, false, |row| {
                    let context = quoridor_core::research::SigmaContext::from_prefix(&row.prefix)
                        .map_err(|e| format!("static teacher full prefix: {e}"))?;
                    if context.terminal_value().is_some() || context.total_ply() != row.ply {
                        return Err(
                            "static teacher source must be a nonterminal complete prefix".into(),
                        );
                    }
                    let expected = quoridor_data::TeacherRow::from_context(
                        row.id.clone(),
                        row.game.clone(),
                        row.family.clone(),
                        row.split.clone(),
                        row.prefix.clone(),
                        &context,
                        row.action,
                        row.teacher.clone(),
                        row.model_sha.clone(),
                    )?;
                    if expected.state_key != row.state_key
                        || expected.history_key != row.history_key
                        || expected.feature_signature != row.feature_signature
                        || expected.side != row.side
                        || expected.ids != row.ids
                        || expected.distance.map(f32::to_bits) != row.distance.map(f32::to_bits)
                    {
                        return Err(
                            "static teacher source/chronology/input identity differs".into()
                        );
                    }
                    let (single_value, source_completed_simulations) = match &row.teacher {
                        quoridor_data::Teacher::Mcts {
                            root_nn,
                            root_visits,
                            ..
                        } => (*root_nn, Some(*root_visits)),
                        _ => (None, None),
                    };
                    let reflected_prefix = row
                        .prefix
                        .iter()
                        .map(|&a| {
                            Ok(match a {
                                0..=80 => (a / 9) * 9 + (8 - a % 9),
                                81..=144 => {
                                    let x = a - 81;
                                    81 + (x / 8) * 8 + (7 - x % 8)
                                }
                                145..=208 => {
                                    let x = a - 145;
                                    145 + (x / 8) * 8 + (7 - x % 8)
                                }
                                _ => return Err("invalid canonical ActionID in reflected prefix"),
                            })
                        })
                        .collect::<std::result::Result<Vec<u16>, _>>()?;
                    let reflected =
                        quoridor_core::research::SigmaContext::from_prefix(&reflected_prefix)
                            .map_err(|e| format!("static teacher reflected full prefix: {e}"))?;
                    if reflected.terminal_value().is_some() || reflected.total_ply() != row.ply {
                        return Err("static teacher reflected chronology/terminal mismatch".into());
                    }
                    let reflected_input = quoridor_data::TeacherRow::from_context(
                        row.id.clone(),
                        row.game.clone(),
                        row.family.clone(),
                        row.split.clone(),
                        reflected_prefix.clone(),
                        &reflected,
                        None,
                        quoridor_data::Teacher::InputOnly,
                        row.model_sha.clone(),
                    )?;
                    let position = context.position();
                    let reflected_position = reflected.position();
                    let sigma_input = quoridor_core::research::features(position);
                    let reflected_sigma_input =
                        quoridor_core::research::features(reflected_position);
                    serde_json::to_writer(
                        &mut writer,
                        &serde_json::json!({
                            "id":row.id,"native_family":row.family,"source_split":row.split,
                            "ply":row.ply,"prefix":row.prefix,"absolute_side":position.turn,
                            "state_key":row.state_key,"history_key":row.history_key,
                            "feature_signature":row.feature_signature,"distance":row.distance,
                            "z":row.z,"sigma_single_root_nn":single_value,"source_completed_simulations":source_completed_simulations,"model_sha":row.model_sha,
                            "sigma_features":sigma_input.as_slice(),
                            "reflected":{"prefix":reflected_prefix,"state_key":reflected_input.state_key,
                                "history_key":reflected_input.history_key,"feature_signature":reflected_input.feature_signature,
                                "distance":reflected_input.distance,"sigma_features":reflected_sigma_input.as_slice(),
                                "board":{"pawns":reflected_position.pawns,"stocks":reflected_position.walls_remaining,
                                    "horizontal":reflected_position.horizontal,"vertical":reflected_position.vertical,"turn":reflected_position.turn}},
                            "board":{"pawns":position.pawns,"stocks":position.walls_remaining,
                                "horizontal":position.horizontal,"vertical":position.vertical,"turn":position.turn},
                        }),
                    )?;
                    writer.write_all(b"\n")?;
                    count += 1;
                    Ok(())
                })?;
                writer.flush()?;
                eprintln!("{{\"rows\":{count},\"new_network_calls\":0}}");
            }
            "references" => {
                println!("{}", write_input_references(&input, &output, allow)?);
            }
            _ => return Err("unknown subcommand".into()),
        }
        return Ok(());
    }
    Err("sigma-import --config CONFIG --receipt NEW_RECEIPT (framed stdin); sigma-import <cache|references|labels> --input DATASET --output NEWPATH [--allow-test]".into())
}
