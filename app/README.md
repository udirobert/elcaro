# Elcaro Agent Middleware — Track 3 App

An agent-facing content screener that uses the Elcaro miner to pre-filter
retrieved content for prompt injection before an AI agent processes it.

## What it does

Every piece of content an agent retrieves — search results, emails, web pages,
code, documents — passes through the Elcaro middleware. If the injection risk
score exceeds a threshold, the content is quarantined (replaced, blocked, or
flagged with a warning) and the agent never sees the raw injection.

```
Agent retrieves content → Elcaro scans → Safe? → Agent processes
                                       → Unsafe? → Content quarantined
```

## Why this matters

This is the real-world application of IPI detection. Autonomous agents that
retrieve and act on external content are vulnerable to indirect prompt
injection — hidden instructions in the data they fetch. Elcaro sits between
the retrieval layer and the LLM, catching injections before they reach the
agent.

## Usage

### Local engine (no network)

```python
from app.middleware import ElcaroMiddleware
from core import ContentType

middleware = ElcaroMiddleware(use_local_engine=True, risk_threshold=0.5)
result = await middleware.scan(content, content_type=ContentType.EMAIL)

if result.is_safe():
    agent.process(result.safe_content)
else:
    agent.warn(f"Blocked: {result.reason}")
```

### Remote miner (Telegraph network)

```python
middleware = ElcaroMiddleware(
    miner_url="https://elcaro-miner.example.com",
    risk_threshold=0.5,
)
```

### Quarantine modes

- `replace` (default): Replace content with a quarantine notice
- `block`: Return empty content + warning
- `warn`: Pass content through but prepend a warning

The threshold (0.5) and the quarantine notice text live in
`core/quarantine.py` — the same module the detection engine uses to populate
`ScanResponse.safe_content` / `quarantined`, so the middleware and the API
always issue identical verdicts.

## Demo

```bash
python demo.py
```

Runs through 6 sample content items (clean + injected) and shows how Elcaro
blocks injection attempts while letting clean content through.

## Telegraph integration

The middleware's default is a direct `POST /scan` on the miner URL. That is
the right path for a local/dev agent and for the web UI.

It is **not** the path Telegraph counts toward miner request volume. Direct
calls — including 402-gated `POST /engine/v1/ask/8848` — are excluded so
operators cannot farm their own traffic. Counted volume is auto-routed
`POST /engine/v1/ask` (see [Using Telegraph](https://docs.telegraphprotocol.com/docs/using/x402-inference),
the Consume Intelligence card on [integrate.telegraphprotocol.com](https://integrate.telegraphprotocol.com/),
and `app/telegraph.py`). An agent that uses the direct path still counts as
a Track 3 application; those scans just do not add miner volume.

## Integration with agent frameworks

The middleware is framework-agnostic — it's a simple async function that
takes content and returns a safe/flagged result. To integrate with a specific
framework:

- **LangChain**: Wrap the `RetrieverInterface` to scan documents after retrieval
- **OpenAI Assistants**: Scan tool outputs before passing to the assistant
- **Custom agents**: Call `middleware.scan()` on any retrieved content before
  passing it to the LLM prompt
