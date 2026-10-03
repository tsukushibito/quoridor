use quoridor_core::{research::{SigmaContext,HistoryKey,DIRECTIONS,sigma_to_rust},Position};
use serde_json::Value;
fn n(v: &Value) -> Result<u16, String> {
    v.as_u64()
        .and_then(|x| u16::try_from(x).ok())
        .ok_or("INPUT_INTEGER".into())
}
fn array(v: &Value) -> Result<&Vec<Value>, String> {
    v.as_array().ok_or("INPUT_ARRAY".into())
}
fn prefix_action(p: Position, a: &Value) -> Result<u16, String> {
    if a["type"] == "pawn" {
        let dx = a["direction"][0].as_i64().ok_or("DIRECTION")?;
        let dy = a["direction"][1].as_i64().ok_or("DIRECTION")?;
        let s = DIRECTIONS
            .iter()
            .position(|&(x, y)| i64::from(x) == dx && i64::from(y) == dy)
            .ok_or("DIRECTION")?;
        sigma_to_rust(p, s as u16).ok_or("DIRECTION".into())
    } else {
        let base = match a["orientation"].as_str() {
            Some("h") => 81,
            Some("v") => 145,
            _ => return Err("WALL_ORIENTATION".into()),
        };
        let x = n(&a["x"])?;
        let y = n(&a["y"])?;
        if x >= 8 || y >= 8 {
            return Err("WALL_ANCHOR".into());
        }
        Ok(base + 8 * y + x)
    }
}
pub fn context(f: &Value, diagnostic: bool) -> Result<SigmaContext, String> {
    if let Some(prefix) = f.get("prefix") {
        let ids = array(prefix)?
            .iter()
            .map(n)
            .collect::<Result<Vec<_>, _>>()?;
        return SigmaContext::from_prefix(&ids).map_err(|e| e.to_string());
    }
    let mut c = SigmaContext::from_prefix(&[]).map_err(|e| e.to_string())?;
    let mut ids = Vec::new();
    for a in array(&f["legal_prefix"])? {
        let id = prefix_action(c.position(), a)?;
        ids.push(id);
        c = c.play(id).map_err(|e| e.to_string())?
    }
    c = SigmaContext::from_prefix(&ids).map_err(|e| e.to_string())?;
    if f["classification"] == "legal-replay" {
        return Ok(c);
    }
    if !diagnostic {
        return Err("SYNTHETIC_DIAGNOSTIC_ONLY".into());
    }
    let b = &f["board"];
    let mut p = Position {
        pawns: [
            u8::try_from(n(&b["rust_pawns"][0])?).map_err(|_| "CELL")?,
            u8::try_from(n(&b["rust_pawns"][1])?).map_err(|_| "CELL")?,
        ],
        walls_remaining: [
            u8::try_from(n(&b["walls_remaining"][0])?).map_err(|_| "WALLS")?,
            u8::try_from(n(&b["walls_remaining"][1])?).map_err(|_| "WALLS")?,
        ],
        turn: u8::try_from(n(&b["turn"])?).map_err(|_| "TURN")?,
        horizontal: 0,
        vertical: 0,
        winner: None,
    };
    for (key, bits) in [
        ("rust_h_anchors", &mut p.horizontal),
        ("rust_v_anchors", &mut p.vertical),
    ] {
        for a in array(&b[key])? {
            let a = n(a)?;
            if a >= 64 {
                return Err("ANCHOR".into());
            }
            *bits |= 1u64 << a
        }
    }
    p.winner = if p.pawns[0] / 9 == 8 {
        Some(0)
    } else if p.pawns[1] / 9 == 0 {
        Some(1)
    } else {
        None
    };
    let mut h = Vec::new();
    for a in array(&f["history_counts"])? {
        h.push((
            HistoryKey::parse(a[0].as_str().ok_or("HISTORY_KEY")?).map_err(|e| e.to_string())?,
            n(&a[1])?,
        ))
    }
    SigmaContext::synthetic_diagnostic(p, n(&b["total_ply"])?, h).map_err(|e| e.to_string())
}
