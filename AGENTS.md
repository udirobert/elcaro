# AGENTS.md

## Development

Local dev uses [uv](https://docs.astral.sh/uv/) with a native arm64 Python 3.12
(matching CI). Do NOT use `/usr/local/bin/python3` — it is an x86_64 (Rosetta)
interpreter and binary wheels like `pydantic_core` will fail to import.

```bash
export PATH="$HOME/.local/bin:$PATH"   # uv
uv python install 3.12                  # once
uv sync --extra all                     # create/update .venv with all extras

uv run pytest -q                        # test suite (434 tests)
uv run ruff check                       # lint
cd lexsi-eval && uv run --project .. python selftest.py
```

Expected: `434 passed`, `All checks passed!`, and
`selftest OK — 24 tasks, references pass, wrong answers fail`.
