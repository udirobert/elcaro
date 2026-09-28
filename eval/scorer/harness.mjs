// Load Telegraph scoring modules the way a validator node does and report the
// numbers that decide a registration: margin, ordering wins, self-match, and
// rank agreement with the seated champion.
//
//   node eval/scorer/harness.mjs [module.wasm ...]            bench (default: ours + text baseline)
//   node eval/scorer/harness.mjs --attacks [module.wasm ...]  anti-gaming attacks
//   node eval/scorer/harness.mjs --agreement ours.wasm champion.wasm
//   node eval/scorer/harness.mjs --diff ours.wasm champion.wasm   cases where we lose
//   node eval/scorer/harness.mjs --case "q" "ground truth" "answer" [module.wasm]
//
// Champion binaries are public (wasm_url in https://devnode.telegraphprotocol.com/api/wasm).
// Put them in eval/scorer/champions/ (gitignored — other people's binaries) and
// every bench run includes them.
//
// `text-baseline` is a built-in token-F1 scorer standing in for the
// text-overlap modules that dominate the network; it is not a real champion.

import { readFile } from "node:fs/promises";
import { existsSync, readdirSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OURS = join(HERE, "target/wasm32-unknown-unknown/release/elcaro_scorer.wasm");
const CHAMPIONS = join(HERE, "champions");

/** A scoring module: zero imports, strings written through its own alloc. */
export async function load(path) {
  const { instance } = await WebAssembly.instantiate(await readFile(path), {});
  const { memory, alloc, rank_answer, breakdown_answer } = instance.exports;
  if (typeof alloc !== "function" || typeof rank_answer !== "function") {
    throw new Error(`${path}: missing alloc/rank_answer export`);
  }
  const enc = new TextEncoder();
  const write = (s) => {
    const bytes = enc.encode(s);
    const ptr = alloc(bytes.length);
    new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
    return [ptr, bytes.length];
  };
  // Argument order is fixed: question, ground truth, miner answer.
  const args = (q, gt, a) => [...write(q), ...write(gt), ...write(a)];
  return {
    name: basename(path),
    score: (q, gt, a) => rank_answer(...args(q, gt, a)),
    breakdown:
      typeof breakdown_answer === "function"
        ? (q, gt, a) => {
            const ptr = breakdown_answer(...args(q, gt, a));
            return Array.from(new Float32Array(memory.buffer, ptr, 5));
          }
        : null,
  };
}

/** Token-F1 stand-in for a text-overlap champion. */
export const textBaseline = {
  name: "text-baseline",
  score(_q, gt, a) {
    const toks = (s) => new Set(s.toLowerCase().match(/[a-z0-9]+/g) ?? []);
    const g = toks(gt);
    const m = toks(a);
    if (!g.size || !m.size) return 0;
    let hit = 0;
    for (const t of m) if (g.has(t)) hit++;
    if (!hit) return 0;
    const p = hit / m.size;
    const r = hit / g.size;
    return (2 * p * r) / (p + r);
  },
  breakdown: null,
};

/** Stage-2 style metrics over good/bad pairs. */
export function evaluate(mod, cases) {
  let wins = 0;
  let margin = 0;
  let worstSelf = 1;
  const all = [];
  for (const c of cases) {
    const good = mod.score(c.question, c.ground_truth, c.good);
    const bad = mod.score(c.question, c.ground_truth, c.bad);
    const self = mod.score(c.question, c.ground_truth, c.ground_truth);
    if (good > bad) wins++;
    margin += good - bad;
    worstSelf = Math.min(worstSelf, self);
    all.push(good, bad);
  }
  const mean = all.reduce((a, b) => a + b, 0) / all.length;
  const stddev = Math.sqrt(all.reduce((a, b) => a + (b - mean) ** 2, 0) / all.length);
  return { margin: margin / cases.length, wins, cases: cases.length, worstSelf, stddev };
}

/**
 * Approximate the node's rank-agreement gate (~0.60): score a ladder of
 * answers per case with both modules and average Spearman's rho. The node
 * uses real historical miner answers we can't see; this is a proxy.
 */
export function agreement(a, b, cases) {
  const rhos = cases.map((c) => {
    const ladder = [c.ground_truth, c.good, `${c.good} Hope this helps!`, c.bad, c.question, ""];
    return spearman(
      ladder.map((x) => a.score(c.question, c.ground_truth, x)),
      ladder.map((x) => b.score(c.question, c.ground_truth, x)),
    );
  });
  return rhos.reduce((s, r) => s + r, 0) / rhos.length;
}

function ranks(xs) {
  const order = xs.map((v, i) => [v, i]).sort((p, q) => p[0] - q[0]);
  const r = new Array(xs.length);
  for (let i = 0; i < order.length; ) {
    let j = i;
    while (j + 1 < order.length && order[j + 1][0] === order[i][0]) j++;
    for (let k = i; k <= j; k++) r[order[k][1]] = (i + j) / 2 + 1;
    i = j + 1;
  }
  return r;
}

function spearman(x, y) {
  const rx = ranks(x);
  const ry = ranks(y);
  const n = x.length;
  const mx = rx.reduce((a, b) => a + b, 0) / n;
  const my = ry.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < n; i++) {
    num += (rx[i] - mx) * (ry[i] - my);
    dx += (rx[i] - mx) ** 2;
    dy += (ry[i] - my) ** 2;
  }
  // Two flat orderings agree; one flat and one not carries no information.
  if (dx === 0 && dy === 0) return 1;
  if (dx === 0 || dy === 0) return 0;
  return num / Math.sqrt(dx * dy);
}

async function modules(paths) {
  if (paths.length) return Promise.all(paths.map(load));
  if (!existsSync(OURS)) {
    throw new Error(`build first: ${OURS} not found (see eval/scorer/README.md)`);
  }
  const mods = [await load(OURS), textBaseline];
  if (existsSync(CHAMPIONS)) {
    for (const f of readdirSync(CHAMPIONS).filter((f) => f.endsWith(".wasm"))) {
      mods.push(await load(join(CHAMPIONS, f)));
    }
  }
  return mods;
}

const json = async (f) => JSON.parse(await readFile(join(HERE, f), "utf8"));
const fmt = (x) => x.toFixed(4);

async function main(argv) {
  const flag = argv[0]?.startsWith("--") ? argv.shift() : "--bench";

  if (flag === "--case") {
    const [q, gt, a, ...paths] = argv;
    for (const m of await modules(paths)) {
      const b = m.breakdown ? m.breakdown(q, gt, a).map(fmt).join(" ") : "";
      console.log(`${m.name.padEnd(28)} ${fmt(m.score(q, gt, a))}  ${b}`);
    }
    return;
  }

  if (flag === "--attacks") {
    const attacks = await json("attacks.json");
    let failed = 0;
    for (const m of await modules(argv)) {
      let held = 0;
      for (const t of attacks) {
        const honest = m.score(t.question, t.ground_truth, t.honest);
        const attack = m.score(t.question, t.ground_truth, t.attack);
        const ok = honest > attack;
        if (ok) held++;
        console.log(
          `${m.name.padEnd(28)} ${ok ? "held" : "FELL"}  ${t.id.padEnd(22)} ` +
            `honest ${fmt(honest)}  attack ${fmt(attack)}`,
        );
      }
      console.log(`${m.name}: ${held}/${attacks.length} attacks held\n`);
      if (m.name === basename(OURS) && held < attacks.length) failed = 1;
    }
    process.exitCode = failed;
    return;
  }

  const cases = await json("bench.json");

  if (flag === "--agreement" || flag === "--diff") {
    const [a, b] = await modules(argv);
    if (!b) throw new Error(`${flag} needs two modules`);
    if (flag === "--agreement") {
      console.log(`rank agreement ${a.name} vs ${b.name}: ${fmt(agreement(a, b, cases))}`);
      return;
    }
    for (const c of cases) {
      const da = a.score(c.question, c.ground_truth, c.good) - a.score(c.question, c.ground_truth, c.bad);
      const db = b.score(c.question, c.ground_truth, c.good) - b.score(c.question, c.ground_truth, c.bad);
      if (da < db) console.log(`${c.id.padEnd(6)} ${a.name} margin ${fmt(da)} < ${b.name} ${fmt(db)}`);
    }
    return;
  }

  console.log(`bench: ${cases.length} cases\n`);
  console.log("module                       margin   wins    worst-self  stddev");
  let failed = 0;
  for (const m of await modules(argv)) {
    const r = evaluate(m, cases);
    console.log(
      `${m.name.padEnd(28)} ${fmt(r.margin)}  ${`${r.wins}/${r.cases}`.padEnd(7)} ` +
        `${fmt(r.worstSelf)}      ${fmt(r.stddev)}`,
    );
    if (m.name === basename(OURS) && (r.wins < r.cases || r.worstSelf < 0.99)) failed = 1;
  }
  process.exitCode = failed;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch((e) => {
    console.error(e.message);
    process.exitCode = 2;
  });
}
