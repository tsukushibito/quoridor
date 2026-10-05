use std::io::{self, BufRead, Write};
fn main() {
    let stdin = io::stdin();
    let mut out = io::BufWriter::new(io::stdout());
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let r = match serde_json::from_str(&line) {
            Ok(v) => ai_sigma_ort_search::native_call(v),
            Err(e) => serde_json::json!({"ok":false,"error":e.to_string()}),
        };
        writeln!(out, "{}", r).unwrap();
        out.flush().unwrap();
    }
}
