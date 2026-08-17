# Deployment TODO — go live checklist

## Cloudflare DNS (for trustfall.xyz)

- [ ] Add A record: `api.elcaro` → `144.202.117.160`, **Proxied** (orange cloud)
- [ ] Add Origin Rule: for hostname `api.elcaro.trustfall.xyz`, set Origin Port to `8847`
- [ ] Add CNAME record: `elcaro` → `[your-site].netlify.app`, **DNS only** (grey cloud)
- [ ] Verify miner: `BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh` — 18/18 checks pass

## Netlify

- [ ] Set environment variable: `ELCARO_MINER_URL` = `https://api.elcaro.trustfall.xyz`
- [ ] Set custom domain: `elcaro.trustfall.xyz`
- [ ] Trigger redeploy after env var is set
- [ ] Verify end-to-end: `bash deploy/verify-live.sh` (includes the Netlify `/api/scan` proxy checks) and scan something at `https://elcaro.trustfall.xyz`

## VPS (already done)

- [x] Clone repo to `/home/linuxuser/elcaro`
- [x] Python venv + deps installed
- [x] 54 tests passing
- [x] PM2 running `elcaro-miner` on `127.0.0.1:8848`
- [x] nginx proxying `:8847` → `:8848`
- [x] Health check responding
- [x] Scan endpoint returning full threat cards
