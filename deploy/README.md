# Deployment

> Host-specific detail (IP, SSH alias, exact paths, neighbouring services) lives
> in `docs/ops.md`, which is gitignored. This file stays generic on purpose.

## Architecture

The miner runs on a **Coolify-managed VPS**. Coolify's `coolify-proxy` container
(Traefik v3.6) is the only process bound to public :80/:443 and terminates TLS
for every domain on the host via Let's Encrypt. Host-level nginx is **not** part
of the serving path — the `nginx.service` unit is in a `failed` state and nothing
on the host binds :80/:443.

```
┌──────────┐        ┌──────────────────────────────────────────────┐
│  Browser │───────▶│  VPS                                         │
└──────────┘ HTTPS  │  ┌────────────────────────────────────────┐  │
             :443   │  │ coolify-proxy (Traefik v3.6)           │  │
                    │  │  • owns :80 / :443                     │  │
                    │  │  • Let's Encrypt HTTP-01 (acme.json)   │  │
                    │  │  • file provider: /traefik/dynamic/    │  │
                    │  └───────────────┬────────────────────────┘  │
                    │                  │ host.docker.internal      │
                    │                  │ :8848                     │
                    │                  ▼                           │
                    │        uvicorn (PM2: elcaro-miner)           │
                    │        binds 0.0.0.0:8848                    │
                    │        ufw: 8848 open to Docker bridges only  │
                    └──────────────────────────────────────────────┘
```

DNS is a plain A-record at the registrar pointing straight at the VPS. No CDN
proxy is involved, and none is needed: Traefik terminates TLS at the origin.

## Frontend (Netlify)

`netlify.toml` at the repo root is the source of truth for this — base
directory `app/web`, build command `npm run build`, publish `app/web/.next`,
via `@netlify/plugin-nextjs`.

1. Connect the GitHub repo to Netlify (New site from Git)
2. It reads `netlify.toml` automatically — no manual build settings needed
3. Site settings → Environment variables → add
   `ELCARO_MINER_URL` = `https://api.elcaro.trustfall.xyz`
4. Site settings → Domain management → add custom domain: `elcaro.trustfall.xyz`

**Live since Aug 21, 2026:** the site serves at
[elcaro.trustfall.xyz](https://elcaro.trustfall.xyz) via a CNAME to
`elcaro.netlify.app` (registrar DNS at GoDaddy) with an automatically
provisioned Let's Encrypt certificate. Full suite `deploy/verify-live.sh`
passes 21/21 including the frontend proxy checks.

## Miner API (VPS)

> ⚠️ **This is a shared host.** It runs many unrelated projects (dozens of
> containers and PM2 processes). Do **not** install a host-level nginx/certbot on
> it, and do **not** touch other projects' files in the Traefik dynamic config
> directory — Traefik reads that whole directory, and every other domain's
> routing lives there. See `docs/ops.md`.

### Exposing the miner (the established pattern on this host)

Three pieces, mirroring how the other host-run apps on the box are wired:

1. **Bind the app so Traefik can reach it.** uvicorn must listen on `0.0.0.0`,
   not `127.0.0.1` — Traefik runs in a container and cannot reach host loopback;
   it connects via `host.docker.internal`. Set in `ecosystem.config.cjs`.

2. **Keep it private with ufw.** The port is bound broadly but firewalled to the
   Docker bridge networks, so it is unreachable from the internet:

   ```bash
   sudo ufw allow from 10.0.0.0/8 to any port 8848 proto tcp \
     comment "elcaro-miner from Docker/Traefik"
   ```

3. **Add a Traefik route.** Install `deploy/traefik-elcaro.yaml` into Coolify's
   Traefik dynamic directory as `elcaro.yaml` (root:root 0644). Traefik runs with
   `--providers.file.watch=true`, so it is picked up live — no proxy restart, no
   impact on other projects. Exact path and command: `docs/ops.md`.

Traefik then requests the Let's Encrypt cert automatically over HTTP-01 and
stores it in the shared `acme.json`.

### Exposing the Gateway (Phase 2) — LIVE 2026-11-15

`gateway.elcaro.trustfall.xyz` is live: DNS A → `144.202.117.160`, ufw
8849→10.0.0.0/8, `elcaro-gateway.yaml` installed in the Traefik dynamic dir,
cert issued, `verify-live.sh` 27/27 including `/health` + fail-closed 401s.

The steps below remain the reference for re-creating it (or the next service):

1. **DNS**: A record `gateway.elcaro.trustfall.xyz` → VPS public IP.
2. **ufw**:

   ```bash
   sudo ufw allow from 10.0.0.0/8 to any port 8849 proto tcp \
     comment "elcaro-gateway from Docker/Traefik"
   ```

3. **Traefik**: install `deploy/traefik-elcaro-gateway.yaml` into the dynamic
   dir as `elcaro-gateway.yaml` — a *new* file, alongside `elcaro.yaml`,
   touching nothing else.
4. **Env**: the gateway reads `ELCARO_SIGNING_KEY`, `ELCARO_METERING_DSN`,
   `ELCARO_GATEWAY_PRICE_USDC` and `ELCARO_UPSTREAM_<NAME>_URL` from the same
   `~/elcaro/.env` the ecosystem file already loads. Optional x402
   pay-per-call (armed only when a payTo resolves *and* a server-held
   upstream credential is set): `X402_PAYTO` or `TELEGRAPH_X402_KEY`,
   `X402_SCAN_AMOUNT`, `X402_FACILITATOR_URL`,
   `ELCARO_PAYPERCALL_UPSTREAM` / `ELCARO_PAYPERCALL_MODE`,
   `ELCARO_UPSTREAM_KEY_<NAME>` (`SERV_API_KEY` is the fallback when the
   upstream is `serv`).
5. **Boot**: `pm2 startOrRestart deploy/ecosystem.config.cjs && pm2 save`,
   then `GATEWAY_URL=https://gateway.elcaro.trustfall.xyz bash deploy/verify-live.sh`
   — the gateway checks assert `/health` and that keyless/bogus-key chat
   requests fail closed (401).

**ACME gotcha (hit live):** if the route file is installed *before* DNS
propagates, Let's Encrypt's first attempt fails NXDOMAIN and Traefik caches
the failure in memory — subsequent requests don't retry it (the route
itself works under the fallback cert; `curl -k` 200s). Fix is
`sudo docker restart coolify-proxy`; the retry succeeds on the next
handshake. Ordering DNS → route avoids it.

The `elcaro-gateway` PM2 app runs `gateway.app:app` — merged, deployed, and
**metered**: `metering.install_from_env()` runs at boot and picks up
`ELCARO_CANARY_DSN` from `.env` (fallback for `ELCARO_METERING_DSN`). Verified
live: an `elk_*` key minted in Neon authenticates through the public
gateway — the stubs would 401 "Unknown Elcaro key" instead of reaching the
upstream-credential check.

Provisioning a key (raw key prints once — store it immediately):

```bash
cd ~/elcaro && .venv/bin/python - <<'EOF'
import os
env = {}
for raw in open(".env"):
    line = raw.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        env[k] = v
from metering import NeonMetering
m = NeonMetering(env.get("ELCARO_METERING_DSN") or env["ELCARO_CANARY_DSN"])
print(m.issue_key(label="…"))   # (raw_key, key_id)
EOF
```

`/api/keys` on the site is the self-service equivalent — it reads the same
Neon tables once `ELCARO_CANARY_DSN` (or `ELCARO_METERING_DSN`) is set in
Netlify env (done 2026-11-15, alongside `X402_FACILITATOR_URL` for on-chain
settlement and `X402_TEST_PAYER_KEY`, the funded Sepolia test wallet).

### Prerequisites

Python 3.12 and PM2 are already installed on the VPS.

### Deploy the app itself

```bash
cd ~/elcaro && git pull
pm2 start deploy/ecosystem.config.cjs && pm2 save
```

`pm2 save` matters: without it a reboot restores the old bind address.

### Environment variables

`deploy/ecosystem.config.cjs` loads `~/elcaro/.env` itself (plain
`KEY=value` lines, `export` prefixes and quotes tolerated) and merges it
into the app's env, so the file on the VPS is the single place secrets
live — gitignored, mode `600`. The committed `env` block wins on a key
conflict: it declares the deployment contract (e.g. `SERV_ENABLED=1`),
`.env` carries secrets (`SERV_API_KEY`, `ELCARO_SIGNING_KEY`,
`ELCARO_CANARY_DSN`, …) plus any var the block does not set.

Two pm2 gotchas this file is written around:

- `pm2 restart elcaro-miner` reuses the env frozen in pm2's dump and does
  **not** re-evaluate the ecosystem file. To apply env/config changes use
  `pm2 startOrRestart deploy/ecosystem.config.cjs` — `update.sh` does.
- After any `startOrRestart`, `pm2 save` so `pm2 resurrect` restores the
  new env, not the stale dump.
- Both failure modes are now visible rather than silent: `update.sh` reads the
  quota back from the restarted process (`✓ Anonymous scan quota armed` /
  a warning naming the stale dump), every scan response carries
  `X-RateLimit-*`, and `verify-live.sh` check `8b` fails when no `429` arrives
  within its burst. That is how the free-scan limiter was found running idle
  while `ecosystem.config.cjs` said `30/min · 300/day`.

### Free-scan abuse controls and paid-lane quota bypass

Production now rate-limits the expensive second-opinion rails (SERV, Jev,
Laya, JEV-VL, and deep analysis) separately from the ordinary rule-based scan.
Anonymous callers can still try them, but only inside a small durable quota;
the paid x402 lane bypasses free quotas after payment verification.
Enforcement lives at the miner edge, so callers cannot avoid premium caps by
bypassing Netlify and hitting the miner directly.

Ordinary traffic intentionally has two quotas. The strict conversion quota
applies only when the trusted Netlify proxy asserts an end-user IP. Direct
miner ingress uses a separate higher resource-protection quota because
legitimate Telegraph devnode traffic and direct API callers are not
cryptographically distinguishable today; treating all of it as one browser
user would eventually throttle counted miner volume.

The committed miner contract enables durable fixed-window quotas:

- `ELCARO_SCAN_RATE_LIMIT_PER_MINUTE=6` — trusted web-proxy burst quota
- `ELCARO_SCAN_RATE_LIMIT_PER_DAY=30` — trusted web-proxy daily conversion quota
- `ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_MINUTE=30` — direct/Telegraph ingress burst quota
- `ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_DAY=300` — direct/Telegraph ingress resource quota
- `ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_MINUTE=1` — second-opinion burst quota everywhere
- `ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_DAY=3` — second-opinion daily quota everywhere
- `ELCARO_KEYED_SCAN_RATE_LIMIT_PER_MINUTE=120` — per-key burst quota (`x-elcaro-key`)
- `ELCARO_KEYED_SCAN_RATE_LIMIT_PER_DAY=5000` — per-key daily quota
- `ELCARO_SCAN_MAX_CONTENT_CHARS=100000` — request body cost ceiling

A minted `elk_` key presented in `x-elcaro-key` is resolved through the same
Neon key store the gateway uses (`ELCARO_METERING_DSN`, falling back to
`ELCARO_CANARY_DSN`) and spends the per-key window instead of the anonymous
ones. Windows are keyed by `key_id`, never the raw secret, and a keyed scan
echoes `X-RateLimit-Limit` / `X-RateLimit-Remaining` so the quota is
observable with `curl -i`. An unrecognised key is refused with `401
unknown_key` rather than silently downgraded to anonymous; `503
key_service_unavailable` means the miner has no DSN configured.

When `ELCARO_CANARY_DSN`/`ELCARO_METERING_DSN` is present, the counters live in
Neon table `scan_rate_windows` and survive restarts/multiple workers. Stored
keys are HMACs of client IPs, not raw IPs. Set `ELCARO_RATE_LIMIT_SALT` in
`.env` for a dedicated pepper; otherwise existing deployment secrets are used
as fallback key material.

Generate one shared internal token and configure it in both places:

```bash
openssl rand -hex 32
```

- VPS `~/elcaro/.env`: `ELCARO_INTERNAL_PROXY_TOKEN=<token>`
- Netlify env: `ELCARO_INTERNAL_PROXY_TOKEN=<token>`

The token does two separate things:

1. lets Netlify assert the end-user IP (`x-elcaro-client-ip`) so free quotas
   are per visitor rather than grouped under Netlify egress IPs;
2. lets only the paid `/api/x402/scan` route set `x-elcaro-premium: 1`, which
   bypasses the anonymous free quotas after payment verification.

The ordinary `/api/scan` browser lane sends the token but sets
`x-elcaro-premium: 0`, so it remains inside the free quotas. If the token is
missing in either environment, paid-lane quota bypass fails closed and free
quota attribution is degraded. For local development only,
`ELCARO_ALLOW_ANONYMOUS_PREMIUM=1` bypasses the quotas.

### Durable funnel analytics

The web tier writes conversion events to Neon table `funnel_events` when any
of `ELCARO_ANALYTICS_DSN`, `ELCARO_METERING_DSN`, or `ELCARO_CANARY_DSN` is
present in Netlify. In the current deployment `ELCARO_CANARY_DSN` is enough —
no additional database is needed. Without a DSN the route falls back to local
JSONL only for development and reports `sink: "local_file"`.

Privacy contract: no raw IP, no user-agent, no scanned content, and no bearer
material. The browser sends a daily rotating random session id; the server
stores only its HMAC. Set these Netlify vars for production operations:

- `ELCARO_ANALYTICS_SALT` — dedicated HMAC key for session hashes
- `ANALYTICS_ADMIN_TOKEN` — token required for `GET /api/analytics`

Admin rollup example:

```bash
curl -H "x-admin-token: $ANALYTICS_ADMIN_TOKEN" \
  https://elcaro.trustfall.xyz/api/analytics
```

The response is aggregate-only (`events_tracked`, plus per-event event/session
counts for the last 30 days). Funnel events currently emitted:
`landing.viewed`, `scan.viewed`, `scan.started`, `scan.verdict`, `scan.error`,
`scan.shared`, `scan.copied`, `integrate.viewed`, `keys.viewed`, and
`key.minted`.

### SERV in production (Phase 0.1)

The miner advertises a SERV Reasoning second pass; it is armed by config,
not by code changes:

1. Put `SERV_API_KEY=<openserv key>` in `~/elcaro/.env` (console.openserv.ai;
   `SERV_ENABLED`/`SERV_MODEL` are already committed in the ecosystem file).
2. Configure `ELCARO_INTERNAL_PROXY_TOKEN` as described above — verify-live
   uses it to keep its SERV probe outside the tiny anonymous premium quota.
3. `pm2 startOrRestart deploy/ecosystem.config.cjs && pm2 save`
4. `BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh`
   — the SERV checks assert `serv_available: true` on `/config` and a live
   `serv_used` verdict on a gray-zone `?serv=1` scan. They fail loudly on a
   silent rules fallback.

### Update an existing deployment

```bash
bash deploy/update.sh
```

One command: records a rollback anchor, pulls, reinstalls deps, runs the test
suite (a failure aborts **before** the restart, so a bad commit never reaches
production), restarts, and smoke-checks `/health`. Rollback is printed at the
top of every run: `git checkout <anchor> && pm2 restart elcaro-miner`.

### Ports

| Port | Bound to | Exposure |
|---|---|---|
| 443 | `coolify-proxy` (Traefik) | Public — terminates TLS for all domains |
| 80 | `coolify-proxy` (Traefik) | Public — ACME HTTP-01 + redirect to 443 |
| 8848 | uvicorn (`0.0.0.0`) | Private — ufw restricts to Docker bridges |

### Do not use these on this host

| File | Why |
|---|---|
| `nginx.conf` | Assumes a CDN proxy → origin port 8847. Host nginx is not running and Traefik owns 443. Kept only for a future non-Coolify host. |
| `setup.sh` (nginx steps) | Installs a host nginx vhost; inert here at best, conflicting at worst. |

### Verify a deployment

`deploy/verify-live.sh` runs an 18-check smoke suite against a live miner
(health, metadata, dangerous/clean/system_prompt payloads, `/v1/infer` alias,
validation errors, metrics) plus frontend proxy checks:

```bash
# Miner only (frontend not yet deployed):
BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh

# Full end-to-end once Netlify has ELCARO_MINER_URL set:
bash deploy/verify-live.sh
```

### Daily operations

```bash
# View logs
pm2 logs elcaro-miner

# Restart
pm2 restart elcaro-miner

# Update code + restart (test-gated, with rollback anchor)
bash deploy/update.sh

# Check metrics
curl http://127.0.0.1:8848/metrics

# Status
pm2 show elcaro-miner
```

### Files

| File | Purpose |
|---|---|
| `ecosystem.config.cjs` | PM2 process config — binds `0.0.0.0:8848`, restart policy, memory limit |
| `traefik-elcaro.yaml` | **Live ingress.** Install into Coolify's Traefik dynamic dir as `elcaro.yaml` |
| `update.sh` | **Update path.** Test-gated deploy with rollback anchor and health smoke check |
| `verify-live.sh` | Post-deploy smoke suite (18 checks, miner + frontend proxy) |
| `pin-config.py` | Pins `miner/config.yaml` to IPFS via Pinata, returns the CID — not used for `miner/telegraph.yaml`, which is self-hosted instead (see `SUBMISSIONS.md`) |
| `nginx.conf` | Legacy CDN-proxy model — **not used on this host** |

Uptime monitoring: `.github/workflows/uptime.yml` polls the miner `/health` and
the frontend every 15 minutes and fails the workflow on 2 consecutive misses
(GitHub emails workflow-failure notifications to repo watchers).

Frontend build config lives at the repo root: `netlify.toml`.

Operational runbook, rollback steps, and host specifics: `docs/ops.md` (local only).
