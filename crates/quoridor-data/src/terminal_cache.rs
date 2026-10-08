//! Lossless compact cache for the new dual-teacher dataset, without dense mirrors.

use crate::{Result, TensorCache, file_sha, for_each_row};
use quoridor_core::research::{HistoryKey, SigmaContext};
use std::{
    collections::BTreeMap,
    fs::{self, OpenOptions},
    io::{BufWriter, Write},
    path::Path,
};

pub const CACHE_SCHEMA: &str = "quoridor-terminal-geometry-v1";

pub fn write(dataset: &Path, output: &Path, allow_test: bool) -> Result<TensorCache> {
    fs::create_dir(output)?;
    let names = [
        "geometry.bin",
        "distance-steps.u8",
        "terminal-margin.f32",
        "labels.f32",
        "rows.jsonl",
    ];
    let mut streams = names
        .iter()
        .map(|name| {
            Ok(BufWriter::new(
                OpenOptions::new()
                    .create_new(true)
                    .write(true)
                    .open(output.join(name))?,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let mut count = 0usize;
    for_each_row(dataset, allow_test, |r| {
        let targets = r
            .terminal_targets
            .as_ref()
            .ok_or("mixed historical/dual-teacher cache")?;
        let context = SigmaContext::from_prefix(&r.prefix)?;
        let p = context.position();
        let side = usize::from(r.side - 1);
        let pawns = if side == 0 {
            p.pawns
        } else {
            [80 - p.pawns[1], 80 - p.pawns[0]]
        };
        let stocks = [p.walls_remaining[side], p.walls_remaining[side ^ 1]];
        let horizontal = if side == 0 {
            p.horizontal
        } else {
            p.horizontal.reverse_bits()
        };
        let vertical = if side == 0 {
            p.vertical
        } else {
            p.vertical.reverse_bits()
        };
        let mut geometry = Vec::with_capacity(66);
        geometry.extend(pawns);
        geometry.extend(stocks);
        geometry.extend(horizontal.to_le_bytes());
        geometry.extend(vertical.to_le_bytes());
        for d in r.distance {
            geometry.extend(d.to_le_bytes());
        }
        geometry.push(targets.outcome_z.unwrap_or(0) as u8);
        geometry.push(0); // Source shard is this hash-bound cache, not a historical public shard.
        geometry.extend(u32::try_from(count)?.to_le_bytes());
        let input_sha = crate::hex_digest(&geometry[..28]);
        for i in (0..64).step_by(2) {
            geometry.push(u8::from_str_radix(&input_sha[i..i + 2], 16)?);
        }
        assert_eq!(geometry.len(), 66);
        streams[0].write_all(&geometry)?;
        streams[1].write_all(&targets.current_distance_steps_stm_opponent)?;
        streams[2].write_all(
            &targets
                .margin_target_steps
                .map(f32::from)
                .unwrap_or(f32::NAN)
                .to_le_bytes(),
        )?;
        for v in [
            r.teacher.value().unwrap_or(f32::NAN),
            r.z.unwrap_or(f32::NAN),
        ] {
            streams[3].write_all(&v.to_le_bytes())?;
        }
        let metadata = serde_json::json!({
            "metadata_schema": "quoridor-terminal-tensor-row-v1", "id": r.id, "group":r.family, "game":r.game,
            "split":r.split, "primary_eligible":r.eligible, "teacher_type":"terminal_pair",
            "prefix":r.prefix, "ply":r.ply, "state_key":HistoryKey::from(p).history_string(), "history_key":r.history_key,
            "research_ruleset":r.research_ruleset, "side":r.side, "ids":r.ids,
            "rootmean":r.teacher.value(), "z":r.z, "terminal_targets":targets,
            "distance":r.distance, "distance_order":"STM_then_opponent_f32", "tensor_view_order":"STM_then_opponent",
            "input_geometry_SHA256":input_sha, "action":r.action, "search":r.teacher,
        });
        serde_json::to_writer(&mut streams[4], &metadata)?;
        streams[4].write_all(b"\n")?;
        count += 1;
        Ok(())
    })?;
    for stream in &mut streams {
        stream.flush()?;
    }
    drop(streams);
    let mut files = BTreeMap::new();
    let mut hashes = BTreeMap::new();
    for name in names {
        files.insert(name.into(), name.into());
        hashes.insert(name.into(), file_sha(&output.join(name))?);
    }
    let manifest = TensorCache {
        rows: count,
        feature_count: 312,
        files,
        sha256: hashes,
        dataset_sha: file_sha(&dataset.join("manifest.json"))?,
        allow_test,
        schema: Some(CACHE_SCHEMA.into()),
        label_columns: Some(vec![
            "rootmean".into(),
            "z".into(),
            "terminal_margin".into(),
        ]),
    };
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("cache.json"))?,
        &manifest,
    )?;
    Ok(manifest)
}
