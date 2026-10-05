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
            "references" => {
                println!("{}", write_input_references(&input, &output, allow)?);
            }
            _ => return Err("unknown subcommand".into()),
        }
        return Ok(());
    }
    Err("sigma-import --config CONFIG --receipt NEW_RECEIPT (framed stdin); sigma-import <cache|references|labels> --input DATASET --output NEWPATH [--allow-test]".into())
}
