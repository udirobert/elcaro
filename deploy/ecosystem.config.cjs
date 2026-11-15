// Elcaro Miner — PM2 ecosystem config
// Start: pm2 start deploy/ecosystem.config.cjs
// From:  /home/linuxuser/elcaro/

const fs = require("fs");
const path = require("path");

// Load the deploy host's .env (repo root on the VPS, gitignored, mode 600) so
// secrets never live in this file. Plain KEY=value lines; `export` prefixes,
// blank lines, # comments and matched quotes are tolerated.
//
// Precedence: a key set in the committed `env` block below WINS over .env —
// that block is the deployment contract (what this release expects), while
// .env carries secrets (SERV_API_KEY, ELCARO_SIGNING_KEY, ELCARO_CANARY_DSN…)
// and any var the block does not set.
//
// NOTE: `pm2 restart <name>` reuses the env stored in pm2's dump and does NOT
// re-evaluate this file. To pick up env/config changes use
// `pm2 startOrRestart deploy/ecosystem.config.cjs` (update.sh already does).
function loadEnvFile(file) {
  const out = {};
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return out; // no .env — committed config still applies
  }
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (
      v.length >= 2 &&
      ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))
    ) {
      v = v.slice(1, -1);
    }
    out[m[1]] = v;
  }
  return out;
}

const fileEnv = loadEnvFile(path.join(__dirname, "..", ".env"));

module.exports = {
  apps: [
    {
      name: "elcaro-miner",
      script: ".venv/bin/uvicorn",
      // Binds 0.0.0.0 so Coolify's Traefik container can reach the miner via
      // host.docker.internal. Public exposure is prevented by ufw: port 8848 is
      // only allowed from 10.0.0.0/8 (the Docker bridge networks).
      args: "miner.api:app --host 0.0.0.0 --port 8848",
      cwd: "/home/linuxuser/elcaro",
      interpreter: "none",
      env: {
        ...fileEnv,
        PORT: "8848",
        PYTHONUNBUFFERED: "1",
        // SERV Reasoning second pass — armed in production (docs advertise
        // it; verify-live.sh asserts serv_available + a live serv_used call).
        // SERV_API_KEY itself lives in the VPS .env, loaded above.
        SERV_ENABLED: "1",
        SERV_MODEL: "gpt-5.4-mini",
      },
      // Restart policy
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      // Logging
      error_file: "/home/linuxuser/.pm2/logs/elcaro-miner-error.log",
      out_file: "/home/linuxuser/.pm2/logs/elcaro-miner-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      // Resource limits
      max_memory_restart: "512M",
    },
    {
      name: "elcaro-gateway",
      script: ".venv/bin/uvicorn",
      // Same ingress story as the miner: 0.0.0.0 for Traefik, ufw-restricted
      // to Docker bridges (see deploy/traefik-elcaro-gateway.yaml).
      // gateway.app lands with Dev B's gateway/service merge — this entry
      // crash-loops (then backs off via max_restarts) if deployed early.
      args: "gateway.app:app --host 0.0.0.0 --port 8849",
      cwd: "/home/linuxuser/elcaro",
      interpreter: "none",
      env: {
        ...fileEnv,
        PORT: "8849",
        PYTHONUNBUFFERED: "1",
        SERV_ENABLED: "1",
        SERV_MODEL: "gpt-5.4-mini",
      },
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      error_file: "/home/linuxuser/.pm2/logs/elcaro-gateway-error.log",
      out_file: "/home/linuxuser/.pm2/logs/elcaro-gateway-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      max_memory_restart: "512M",
    },
  ],
};
