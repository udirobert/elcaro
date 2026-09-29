// Run the widened bench (bench_wide.json — base cases + real miner outputs +
// independent-voice answers; see make_bench_wide.py) through the same metrics
// as harness.mjs: margin, ordering wins, worst self-match, and pairwise rank
// agreement against the seated champions.
//
//   node bench_wide.mjs
//
import { readFile, writeFile } from "node:fs/promises";
import { writeFileSync } from "node:fs";
import { existsSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { load, textBaseline, evaluate, agreement } from "./harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const OURS = join(HERE, "target/wasm32-unknown-unknown/release/elcaro_scorer.wasm");
const CHAMPIONS = join(HERE, "champions");
const CACHE_FILE = join(CHAMPIONS, "score-cache.json");

// The 24 MB champion transformers take ~0.5 s per score call on long content
// (~15 min for the full wide set). Scores are deterministic, so cache them
// per (module, question, ground truth, answer). Gitignored — delete the file
// to force a fresh run.
//
// Usage: the full run is long, so it is resumable per champion:
//   node bench_wide.mjs                          # everything (fast once cached)
//   node bench_wide.mjs cmod_r5.wasm bench       # one champion, bench row only
//   node bench_wide.mjs cmod_r5.wasm agreement   # one champion, agreement only
const scoreCache = existsSync(CACHE_FILE)
  ? JSON.parse(await readFile(CACHE_FILE, "utf8"))
  : {};

const flush = () => {
  try {
    writeFileSync(CACHE_FILE, JSON.stringify(scoreCache));
  } catch {}
};
process.on("exit", flush);

function cached(mod) {
  const key = (q, g, a) =>
    createHash("sha256")
      .update(`${mod.name}\u0000${q}\u0000${g}\u0000${a}`)
      .digest("hex");
  return {
    ...mod,
    score(q, g, a) {
      const k = key(q, g, a);
      if (k in scoreCache) return scoreCache[k];
      const v = mod.score(q, g, a);
      scoreCache[k] = v;
      return v;
    },
  };
}

const cases = JSON.parse(await readFile(join(HERE, "bench_wide.json"), "utf8"));
console.log(`bench_wide: ${cases.length} cases (${cases.filter((c) => c.id.startsWith("M")).length} real-miner, ${cases.filter((c) => c.id.startsWith("L")).length} independent-voice)\n`);
console.log("module                       margin   wins    worst-self  stddev");

const argv = process.argv.slice(2);
const onlyChampion = argv.find((a) => a.endsWith(".wasm")) ?? null;
const mode = argv.includes("agreement") ? "agreement" : "bench";

const mods = [await load(OURS), textBaseline];
if (existsSync(CHAMPIONS)) {
  const files = readdirSync(CHAMPIONS).filter(
    (f) => f.endsWith(".wasm") && (!onlyChampion || f === onlyChampion),
  );
  for (const f of files) {
    mods.push(cached(await load(join(CHAMPIONS, f))));
  }
}

const ours = mods[0];
const results = new Map();
for (const m of mods) {
  const r = evaluate(m, cases);
  results.set(m.name, r);
  console.log(
    `${m.name.padEnd(28)} ${r.margin.toFixed(4)}  ${`${r.wins}/${r.cases}`.padEnd(7)} ` +
      `${r.worstSelf.toFixed(4)}      ${r.stddev.toFixed(4)}`,
  );
  flush(); // persist progress after each module
}

if (mode === "agreement") {
  console.log("\nrank agreement (ours vs champion, wide cases):");
  for (const m of mods.slice(2)) {
    const rho = agreement(ours, m, cases);
    console.log(`  vs ${m.name.padEnd(20)} ${rho.toFixed(4)} ${rho >= 0.6 ? "(≥ 0.60)" : "(< 0.60)"}`);
    flush();
  }
}

// Where does ours lose on the widened set?
const champRows = [...results.entries()].filter(([n]) => n.endsWith(".wasm"));
const closest = champRows
  .map(([n, r]) => [n, r.margin])
  .sort((a, b) => b[1] - a[1])[0];
console.log(`\nclosest champion on margin: ${closest[0]} (${closest[1].toFixed(4)})`);
