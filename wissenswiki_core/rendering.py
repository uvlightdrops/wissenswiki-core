"""Sanitized Markdown for read-only content panes."""

import bleach
import markdown

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em",
    "blockquote", "ul", "ol", "li", "pre", "code", "a", "table", "thead",
    "tbody", "tr", "th", "td", "del",
}


def render_markdown(body: str) -> str:
    """Render headings, tables and fenced code without active HTML."""
    html = markdown.markdown(body, extensions=["fenced_code", "tables"])
    return bleach.clean(
        html, tags=ALLOWED_TAGS, attributes={"a": ["href", "title"]},
        protocols=["http", "https", "mailto"], strip=True,
    )
