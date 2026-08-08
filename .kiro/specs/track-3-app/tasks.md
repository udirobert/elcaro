# Track 3 — App: Tasks

Track 3 opens ~Aug 31. Use the time before then to build the hosted demo so it can go live on day one. The middleware itself is code-complete — all work here is the web UI, deployment, and adoption.

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — Middleware hardening (complete by Aug 20, before Track 3 opens)

- [ ] **1.1 Add fail-open error handling to remote miner calls**
  - In `app/middleware.py`, wrap `_call_miner` in try/except
  - On any exception (timeout, connection error, HTTP error): log a warning, return a safe `ScanResponse` with `risk_score=0.0`
  - Rationale: if Elcaro goes down, it must not break the agents using it — that destroys adoption
  - Add a test: `test_middleware_fails_open_on_miner_timeout`

- [ ] **1.2 Add `app/README.md` with 5-line integration example**
  - Show the minimal integration pattern (see design.md)
  - Include: pip install instructions, environment variable setup, the 5-line code snippet
  - Include: link to the hosted demo once deployed

- [ ] **1.3 Verify `python app/demo.py` runs cleanly end-to-end**
  - Must work from the repo root with `.venv` activated
  - Output should show all 6 samples with correct quarantine decisions
  - Fix any import path issues

---

## Phase 2 — Hosted demo web UI (complete by Aug 31)

- [ ] **2.1 Create `app/web.py` — FastAPI demo server**
  - `GET /` → serve `app/static/index.html`
  - `POST /demo/scan` → accept `{content: str, content_type: str}`, call `ElcaroMiddleware.scan()` in remote mode, return JSON result
  - Set `use_local_engine=False`, use `ELCARO_MINER_URL` environment variable
  - Add CORS middleware for the hosted domain

- [ ] **2.2 Create `app/static/index.html` — demo page**
  - Text area for content input (placeholder: "Paste email, search result, document...")
  - Content type dropdown (email, search_result, webpage, document, code)
  - "Scan" button → POST to `/demo/scan` → display result
  - Result display:
    - Risk score as a numeric badge with colour (green < 0.2, yellow 0.2–0.5, orange 0.5–0.7, red ≥ 0.7)
    - Risk level label
    - Flagged techniques as pill badges
    - Indicators list: technique name, confidence %, matched text, explanation
    - Quarantine status: "✅ Safe to process" or "🚫 Quarantined"
  - "Try an example" buttons pre-populated with 4–6 payloads from `demo.py` (mix of injections and clean)
  - No build step — vanilla HTML/CSS/JS only

- [ ] **2.3 Update `app/requirements.txt`**
  - Add `fastapi` and `uvicorn` if not already present (they're in `miner/requirements.txt` but not `app/`)
  - Add `python-multipart` if form parsing is needed

- [ ] **2.4 Test locally**
  ```bash
  ELCARO_MINER_URL=http://localhost:8000 uvicorn app.web:app --reload --port 8001
  ```
  - Open http://localhost:8001 in a browser
  - Submit the injection examples — verify quarantine results
  - Submit clean examples — verify they pass through
  - Confirm every request appears in the miner's logs (real traffic)

---

## Phase 3 — Deploy hosted demo (complete by Aug 31)

- [ ] **3.1 Deploy `app/web.py` to Railway (or Hugging Face Spaces if using Gradio)**
  - Set `ELCARO_MINER_URL` to the deployed Track 1 miner URL
  - Add start command: `uvicorn app.web:app --host 0.0.0.0 --port $PORT`

- [ ] **3.2 Smoke test the hosted deployment**
  - Submit one injection payload → confirm quarantined, risk score > 0.7
  - Submit one clean payload → confirm safe, risk score < 0.3
  - Check the Track 1 miner logs — confirm requests are coming in from the demo

- [ ] **3.3 Update `app/README.md` with the live demo URL**

---

## Phase 4 — Adoption outreach (Aug 31 – Sep 7)

- [ ] **4.1 Post Track 3 announcement on X**
  - Lead with the demo URL — let people try it immediately
  - Show a GIF or screenshot of a real injection being caught
  - "Building an agent for the Telegraph hackathon? Protect it from prompt injection for free."

- [ ] **4.2 Post in Telegraph hackathon Discord**
  - Share the middleware package + demo link
  - Offer to help other participants integrate Elcaro into their Track 3 apps
  - Any other team using Elcaro = more requests to Track 1 miner + evidence of adoption for Track 3 judges

- [ ] **4.3 Monitor request volume on Track 1 miner**
  - Track requests/day from the demo vs direct API users
  - Report in weekly X posts

- [ ] **4.4 Post "week 1 results" on X**
  - How many scans, how many injections caught, example of most interesting detection
  - Engagement drives Track 3 judging score

---

## Phase 5 — Polish (if time allows before Sep 7)

- [ ] **5.1 Add a live stats banner to the demo page**
  - Total scans served, injections caught, false-positive rate
  - Fetched from a simple `/stats` endpoint on the miner

- [ ] **5.2 Add batch scan endpoint**
  - `POST /demo/batch` accepts a list of content items → returns a list of results
  - Useful for developers testing their own content sets

- [ ] **5.3 Add a "copy integration code" button**
  - Pre-filled Python snippet showing how to integrate Elcaro into an agent
  - Lowers the barrier for other developers to adopt

---

## Completion criteria

Track 3 is submission-ready when:
- [ ] `python app/demo.py` runs cleanly with local engine
- [ ] Hosted demo is live at a public URL
- [ ] Hosted demo routes all requests through the live Track 1 miner
- [ ] Fail-open error handling is implemented in `_call_miner`
- [ ] `app/README.md` has the integration example and live demo link
- [ ] At least one X post with the demo link published
- [ ] At least one other team or user has integrated Elcaro (or outreach is documented)
