"""Tangem MCP capability catalog — read-only discovery, no wallet calls.

``read_tangem_catalog()`` connects to the official Tangem MCP server through
the pinned ``mcp-remote`` stdio bridge, performs exactly ``initialize`` +
``tools/list`` (bounded pagination), and returns ``[{name, description}]``
descriptors. It never issues ``tools/call`` and never touches wallet data.

Pairing is interactive (browser OAuth opened by the bridge, QR shown by the
Tangem app) — run this OFF-projector the first time. The bridge's stderr is
sent to /dev/null so authorization URLs and tokens never reach the demo
transcript.

Auth nuance: Tangem's issuer metadata advertises CIMD support but no public
registration endpoint, so pairing may require a workshop-provided client
registration. ``TANGEM_CLIENT_METADATA_URL`` + ``TANGEM_CALLBACK_PORT``
(optional pair, validated) append the bridge's positional callback port and
``--client-metadata-url`` after the endpoint; unset → the bridge's default
flow. The metadata doc must be authorized for this client and list the
callback. Do not point these at another app's identity.

Requires the ``mcp`` extra: ``uv sync --locked --python 3.12 --extra mcp``.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
from typing import Any

MCP_REMOTE = "mcp-remote@0.17.1"
TANGEM_ENDPOINT = "https://mcp.tangem.org/mcp"

_TIMEOUT_S = 120.0
_MAX_PAGES = 10
_MAX_TOOLS = 200
# The serialized catalog is re-sent through the Gateway as a tool result.
# Conservative bound on the whole JSON document — reject early while
# collecting; no truncation, no partial catalog treated as clean.
MAX_CATALOG_BYTES = 32 * 1024


class CatalogError(RuntimeError):
    """Concise catalog failure — never carries URLs, tokens or tool names."""


def _client_metadata_args() -> list[str]:
    """Optional authorized client-metadata pair, both or neither.

    Bridge syntax: positional callback port after the endpoint, then
    ``--client-metadata-url <url>``.
    """
    url = os.environ.get("TANGEM_CLIENT_METADATA_URL", "").strip()
    port_raw = os.environ.get("TANGEM_CALLBACK_PORT", "").strip()
    if not url and not port_raw:
        return []
    if not url or not port_raw:
        raise CatalogError(
            "TANGEM_CLIENT_METADATA_URL and TANGEM_CALLBACK_PORT must be set together"
        )
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.path
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise CatalogError("TANGEM_CLIENT_METADATA_URL must be plain https with host+path")
    try:
        port = int(port_raw)
    except ValueError:
        raise CatalogError("TANGEM_CALLBACK_PORT must be an integer") from None
    if not 1024 <= port <= 65535:
        raise CatalogError("TANGEM_CALLBACK_PORT must be 1024-65535")
    return [str(port), "--client-metadata-url", url]


def _catalog_size(tools: list[dict[str, str]]) -> int:
    """Exact UTF-8 size of the serialized catalog JSON, separators included."""
    return len(json.dumps(tools, ensure_ascii=True).encode("utf-8"))


def _append_checked(tools: list[dict[str, str]], seen: set[str], tool: Any) -> None:
    name = getattr(tool, "name", "") or ""
    if not name:
        raise CatalogError("tool entry with empty name")
    if name in seen:
        raise CatalogError("duplicate tool name in catalog")
    seen.add(name)
    tools.append({"name": name, "description": getattr(tool, "description", "") or ""})
    if len(tools) > _MAX_TOOLS:
        raise CatalogError("catalog exceeds tool bound")
    if _catalog_size(tools) > MAX_CATALOG_BYTES:
        raise CatalogError("catalog exceeds the scan cap")


def _server_params() -> Any:
    from mcp import StdioServerParameters  # noqa: PLC0415

    return StdioServerParameters(
        command="npx",
        args=["-y", MCP_REMOTE, TANGEM_ENDPOINT, *_client_metadata_args()],
    )


async def _read(params: Any) -> list[dict[str, str]]:
    """initialize + tools/list against ``params`` — never tools/call.

    ``params`` is injectable so tests can point the real SDK stdio client at
    a local JSON-RPC fixture; production passes the pinned bridge args.
    """
    from mcp import ClientSession  # noqa: PLC0415
    from mcp.client.stdio import stdio_client  # noqa: PLC0415
    from mcp.types import PaginatedRequestParams  # noqa: PLC0415

    tools: list[dict[str, str]] = []
    seen: set[str] = set()
    cursors: set[str] = set()
    try:
        # anyio.open_process needs a real fileno — /dev/null, not StringIO.
        with open(os.devnull, "w") as errlog:
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    cursor = None
                    for _page in range(_MAX_PAGES):
                        result = await session.list_tools(
                            params=PaginatedRequestParams(cursor=cursor)
                        )
                        for tool in result.tools:
                            _append_checked(tools, seen, tool)
                        cursor = result.next_cursor
                        if not cursor:
                            break
                        if cursor in cursors:
                            raise CatalogError("catalog cursor repeated")
                        cursors.add(cursor)
                    else:
                        raise CatalogError("catalog pagination exceeded bound")
    except CatalogError:
        raise
    except Exception as exc:  # sanitize: no transport details in the demo output
        raise CatalogError(f"catalog read failed ({type(exc).__name__})") from None
    if not tools:
        raise CatalogError("empty catalog")
    return tools


def read_tangem_catalog() -> list[dict[str, str]]:
    """Return the live Tangem tool catalog as ``[{name, description}]``.

    Blocking, ~120s bound. Raises :class:`CatalogError` on any failure —
    pairing refusal, duplicates, empty or oversize catalog. Never partial.
    """
    try:
        return asyncio.run(asyncio.wait_for(_read(_server_params()), _TIMEOUT_S))
    except CatalogError:
        raise
    except Exception as exc:
        raise CatalogError(f"catalog read failed ({type(exc).__name__})") from None


__all__ = ["CatalogError", "MAX_CATALOG_BYTES", "read_tangem_catalog"]
