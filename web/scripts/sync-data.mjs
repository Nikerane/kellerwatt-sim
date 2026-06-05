// Copy the SANITIZED engine artifact into the web app's data module.
// The real artifact (dist/real) must NEVER be referenced here.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../dist/sanitized/sim_results.json");
const dest = resolve(here, "../src/data/sim_results.json");

if (!existsSync(src)) {
  console.error(`sanitized artifact not found at ${src}\n` +
    `run: .venv/bin/python -m engine.export   (from the repo root)`);
  process.exit(1);
}
mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`synced ${src} -> ${dest}`);
