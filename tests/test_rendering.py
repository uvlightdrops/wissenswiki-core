"""Read-only Markdown rendering keeps source text and rejects active HTML."""

import pytest

from wissenswiki_core.registry import build_registry
from wissenswiki_core.rendering import render_markdown
from wissenswiki_core.service import api_get


def test_render_markdown_preserves_structure() -> None:
    text = "### Heading\n\n**Strong** and *emphasis*\n\n- One\n- Two\n\n" \
           "| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nprint('<tag>')\n```"
    rendered = render_markdown(text)
    for fragment in ("<h3>Heading</h3>", "<strong>Strong</strong>", "<em>emphasis</em>",
                     "<ul>", "<li>One</li>", "<table>", "<th>A</th>", "<pre><code>"):
        assert fragment in rendered
    assert "&lt;tag&gt;" in rendered


@pytest.mark.parametrize("text", [
    '<script>alert(1)</script><p onclick="alert(2)">Text</p>',
    '[Unsafe](javascript:alert%281%29)',
    '<a href="data:text/html,evil" onmouseover="alert(1)">Link</a>',
    '<img src="x" onerror="alert(1)"><iframe src="https://example.org"></iframe>',
    '<svg onload="alert(1)"><a xlink:href="javascript:alert(1)">Link</a></svg>',
])
def test_render_markdown_strips_active_html(text: str) -> None:
    rendered = render_markdown(text)
    for forbidden in ("<script", "onclick", "onmouseover", "onerror", "<img", "<iframe",
                      "<svg", "onload", "javascript:", "data:", "xlink:"):
        assert forbidden not in rendered


@pytest.mark.parametrize("domain", ["", "Docs"])
def test_api_get_adds_rendered_content_without_changing_source(tmp_path, domain: str) -> None:
    docs, workspace, relations = (tmp_path / name for name in ("docs", "ws", "relations"))
    for directory in (docs, workspace, relations):
        directory.mkdir()
    text = "**Strong**\n\n<script>alert(1)</script>"
    (docs / "a.md").write_text("---\n{}\n---\n# A\n## Block [block]\n" + text)
    registry = build_registry({
        "WORKSPACE": str(workspace),
        "DOMAINS": [{"name": "Docs", "source": str(docs), "relations": str(relations)}],
    })
    registry.workspace.create("Block", text)
    snapshot = api_get(registry, domain)
    block = next(block for block in snapshot["blocks"] if "**Strong**" in block["text"])
    assert "<script>" in block["text"]
    assert "<strong>Strong</strong>" in block["text_html"]
    assert "<script>" not in block["text_html"]
    assert (docs / "a.md").read_text().endswith(text)
