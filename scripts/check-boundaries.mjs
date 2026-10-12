import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Use the prepared common project environment; normal checks never sync packages.
process.stdout.write(
  execFileSync(
    "bash",
    [
      fileURLToPath(new URL("./dev/project-env.sh", import.meta.url)),
      "python",
      "-B",
      fileURLToPath(new URL("./check-boundaries.py", import.meta.url)),
      "crates/quoridor-wasm/Cargo.toml",
    ],
    { timeout: 30000, maxBuffer: 128 * 1024 },
  ),
);
