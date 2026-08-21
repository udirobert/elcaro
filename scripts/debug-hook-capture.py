#!/usr/bin/env python3
"""Debug script: capture everything Kiro passes to a hook command.

Writes to /tmp/kiro-hook-event.json so we can inspect the exact
payload shape. Remove after confirming field names.
"""

from __future__ import annotations

import json
import os
import sys

stdin_raw = sys.stdin.read()
stdin_parsed = None
stdin_error = None
try:
    if stdin_raw.strip():
        stdin_parsed = json.loads(stdin_raw)
except json.JSONDecodeError as e:
    stdin_error = str(e)

# Capture env vars that might carry hook context
env_hook = {
    k: v
    for k, v in os.environ.items()
    if any(x in k.lower() for x in ("kiro", "tool", "hook", "event"))
}

data = {
    "stdin_length": len(stdin_raw),
    "stdin_head": stdin_raw[:1000],
    "stdin_parsed": stdin_parsed,
    "stdin_error": stdin_error,
    "argv": sys.argv,
    "env_hook_keys": env_hook,
}

with open("/tmp/kiro-hook-event.json", "w") as f:  # noqa: S108
    json.dump(data, f, indent=2)

print("HOOK_DEBUG: captured to /tmp/kiro-hook-event.json", flush=True)
