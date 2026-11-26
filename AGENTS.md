# AGENTS.md

## Development

Local dev uses [uv](https://docs.astral.sh/uv/) with a native arm64 Python 3.12
(matching CI). Do NOT use `/usr/local/bin/python3` — it is an x86_64 (Rosetta)
interpreter and binary wheels like `pydantic_core` will fail to import.

```bash
export PATH="$HOME/.local/bin:$PATH"   # uv
uv python install 3.12                  # once
uv sync --extra all                     # create/update .venv with all extras

uv run pytest -q                        # test suite (644 tests)
uv run ruff check                       # lint
cd lexsi-eval && uv run --project .. python selftest.py
```

Expected: `644 passed`, `All checks passed!`, and
`selftest OK — 24 tasks, references pass, wrong answers fail`.

## Secrets and SERV locally

Repo-root `.env` (gitignored, mode 600) holds API keys — including
`SERV_API_KEY`. `uv run` does **not** auto-load it; pass `--env-file`:

```bash
# SERV second pass locally (opt-in per command; pytest stays offline by default)
SERV_ENABLED=1 uv run --env-file .env python -c "from miner.api import app"

# same pattern for any tool that should see .env
uv run --env-file .env pytest -q
```

Production loads the same `.env` via `deploy/ecosystem.config.cjs` — see
`deploy/README.md` → "Environment variables".
