"""Elcaro — runtime prompt-injection defense for Hermes.

register(ctx) wires three hooks and three tools:

    transform_tool_result  — scans every tool result before it enters
                             conversation; quarantined content is replaced
                             by the signed verdict notice in-place.
    pre_tool_call          — scans args-carried payloads (write_file,
                             terminal) for smuggled instructions.
    pre_llm_call           — backstop summary of new quarantines.
    elcaro_scan / elcaro_quick_scan / elcaro_explain — on-demand tools.

Nothing in this module touches the network or builds the engine —
both are lazy so `hermes plugins doctor` (sockets blocked at
registration) stays clean.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import commands, config, guard, schemas, tools

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Entry point Hermes calls once at plugin load."""
    config.bind(ctx)

    ctx.register_tool(
        name="elcaro_scan",
        toolset="elcaro",
        schema=schemas.ELCARO_SCAN,
        handler=tools.elcaro_scan,
    )
    ctx.register_tool(
        name="elcaro_quick_scan",
        toolset="elcaro",
        schema=schemas.ELCARO_QUICK_SCAN,
        handler=tools.elcaro_quick_scan,
    )
    ctx.register_tool(
        name="elcaro_explain",
        toolset="elcaro",
        schema=schemas.ELCARO_EXPLAIN,
        handler=tools.elcaro_explain,
    )

    ctx.register_hook("transform_tool_result", guard.transform_tool_result)
    ctx.register_hook("pre_tool_call", guard.pre_tool_call)
    ctx.register_hook("pre_llm_call", guard.pre_llm_call)

    try:
        ctx.register_command(
            "elcaro",
            commands.slash_elcaro,
            description="Elcaro guard — recent scan verdicts and quarantines",
            args_hint="[index]",
        )
        ctx.register_cli_command(
            name="elcaro",
            help="Elcaro guard — threat log and status",
            setup_fn=commands.cli_setup,
            handler_fn=commands.cli_handler,
        )
    except Exception:
        logger.debug("elcaro: command registration unavailable", exc_info=True)

    skill_md = Path(__file__).parent / "skill" / "SKILL.md"
    if skill_md.exists():
        try:
            ctx.register_skill("elcaro-guard", skill_md)
        except Exception:
            logger.debug("elcaro: skill registration unavailable", exc_info=True)
