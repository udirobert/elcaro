"""Contest / contract check: WebMCP tools are registered in the playground source."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "app" / "web" / "src" / "lib" / "webmcp-register.ts"


def test_webmcp_register_tool_source_exists():
    text = REGISTER.read_text()
    assert "document.modelContext.registerTool(" in text
    for name in (
        '"scan_content"',
        '"load_specimen"',
        '"list_specimens"',
        '"explain_verdict"',
    ):
        assert name in text, f"missing tool {name}"
    assert "untrustedContentHint" in text
    assert "readOnlyHint" in text
