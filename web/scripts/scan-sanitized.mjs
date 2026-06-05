// B6 deploy gate: fail the build if the public data module or the built bundle
// carries any confidential marker, or if a real IRR/payback leaked.
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FORBIDDEN, findLeaks, checkSanitizedDoc } from "./leak-scan.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const dataPath = resolve(here, "../src/data/sim_results.json");
const distDir = resolve(here, "../dist");

const problems = [];

const raw = readFileSync(dataPath, "utf8");
problems.push(...findLeaks(raw).map((t) => `data module contains forbidden token '${t}'`));
problems.push(...checkSanitizedDoc(JSON.parse(raw)));

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else if (/\.(js|json|html|css)$/.test(e.name)) out.push(p);
  }
  return out;
}

if (existsSync(distDir)) {
  for (const f of walk(distDir)) {
    problems.push(...findLeaks(readFileSync(f, "utf8")).map((t) => `${f} contains forbidden token '${t}'`));
  }
}

if (problems.length) {
  console.error("✗ sanitized scan FAILED:\n" + problems.map((p) => "  - " + p).join("\n"));
  process.exit(1);
}
console.log(`✓ sanitized scan passed (forbidden: ${FORBIDDEN.join(", ")})`);
