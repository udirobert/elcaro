# Track 3 — App: Design

## Current state

`app/middleware.py` and `app/demo.py` are both implemented and functional. The middleware supports all three quarantine modes, both local and remote engine paths, and exposes a clean `scan()` → `ScanResult` API. The demo runs end-to-end with the local engine and shows 6 sample payloads (3 injections, 2 clean, 1 borderline).

**What is missing**: a hosted public demo. Everything else is code-complete.

## What needs to be built for Track 3

Track 3 is judged on *adoption* — users, usage, and engagement. The middleware library is already usable; the gap is discoverability and a no-friction way for others to see it work. That means a hosted web UI.

## Hosted demo design

### Option A — Minimal FastAPI web UI (recommended)

Add a small FastAPI app at `app/web.py` that serves a simple HTML page with a text area and a scan button. This keeps the stack entirely Python, no new frameworks.

```
app/
├── middleware.py       # existing — no changes
├── demo.py             # existing — no changes
├── web.py              # NEW — FastAPI web demo server
├── static/
│   └── index.html      # NEW — single-page demo UI
└── requirements.txt    # add: jinja2 or just inline HTML
```

**`app/web.py` responsibilities:**
- Serve `GET /` → the demo HTML page
- Accept `POST /demo/scan` with `{content, content_type}` → call `ElcaroMiddleware.scan()` in remote mode → return full JSON result
- All requests go through the live Elcaro miner (not local engine) to drive real traffic

**`app/static/index.html` features:**
- Text area for content input
- Dropdown for content_type selection (email, search_result, webpage, document, code)
- "Scan" button
- Results panel showing: risk score (with colour-coded badge), risk level, flagged techniques, full indicators list with explanations
- "Try an example" buttons pre-populated with the 6 sample payloads from `demo.py`
- No build tooling — plain HTML + CSS + vanilla JS fetch call

### Option B — Gradio (faster to build, less control)

```python
import gradio as gr
from app.middleware import ElcaroMiddleware

middleware = ElcaroMiddleware(miner_url=os.environ["ELCARO_MINER_URL"])

async def scan(content, content_type):
    result = await middleware.scan(content, ContentType(content_type))
    return result.risk_score, result.risk_level, ...

gr.Interface(fn=scan, inputs=[...], outputs=[...]).launch()
```

Gradio is deployable to Hugging Face Spaces for free. Tradeoff: less control over appearance, but zero frontend work.

**Recommendation**: Option A for a polished demo that better represents the project. Option B if time is short after Track 1/2 work.

## Deployment for hosted demo

### Railway (consistent with Track 1)
```
# Procfile addition
web-demo: uvicorn app.web:app --host 0.0.0.0 --port $PORT
```
Or deploy as a separate Railway service pointing at the same repo.

### Hugging Face Spaces (if using Gradio)
- Free, instant deployment, built-in sharing
- `ELCARO_MINER_URL` set as a Space secret

## Adoption strategy

The middleware is most useful to other Track 3 hackathon participants who are building agents. They can drop in Elcaro as a retrieval safety layer without building detection themselves.

### Adoption accelerators
1. **Simple README example** in `app/README.md` showing the 5-line integration:
   ```python
   from app.middleware import ElcaroMiddleware
   from core import ContentType

   middleware = ElcaroMiddleware(miner_url="https://your-elcaro-url.com")
   result = await middleware.scan(retrieved_content, ContentType.EMAIL)
   if result.is_safe():
       agent.process(result.safe_content)
   ```

2. **X post aimed at other hackathon participants**: "Building a Telegraph agent? Protect it from prompt injection in 5 lines. Elcaro is live — drop in this middleware."

3. **Discord outreach** in the Telegraph hackathon Discord: share the middleware, offer to help integrate.

## Error handling for remote mode

When the live miner is unreachable, the middleware should fail open (not crash the agent):

```python
async def _call_miner(self, content, content_type, context) -> ScanResponse:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(...)
            resp.raise_for_status()
            return ScanResponse(**resp.json())
    except Exception as e:
        # Fail open — log warning, return safe result
        # The agent should not be blocked by our service being down
        import logging
        logging.warning(f"Elcaro miner unreachable: {e}. Failing open.")
        return ScanResponse(
            risk_score=0.0,
            risk_level=RiskLevel.SAFE,
            flagged_techniques=[],
            indicators=[],
            content_type=content_type,
            deep_analysis_used=False,
        )
```

This is not currently implemented — `_call_miner` raises on HTTP errors. Add before production use.

## What NOT to change

`app/middleware.py` core API is stable. Do not change:
- `ElcaroMiddleware.__init__` signature
- `ScanResult` field names
- `scan()` method signature
- The three quarantine mode strings ("replace", "block", "warn")

Other developers will be integrating against this API. Stability matters for adoption.
