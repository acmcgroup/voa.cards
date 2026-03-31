"""Partilhado: embutir logos/SVGs e CSS da barra de exportação para PDF/Playwright."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

LINK_EXPORT_CSS = '<link rel="stylesheet" href="cards-export.css" />'


def _svg_data_url(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _png_data_url(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def inject_wordmarks(html: str, here: Path) -> str:
    """Inline logo.png + SVGs para o PDF não depender de caminhos relativos."""
    logo_png = here / "logo.png"
    if logo_png.is_file():
        html = html.replace(
            'src="logo.png"',
            f'src="{_png_data_url(logo_png)}"',
        )
    else:
        print(f"Warning: missing {logo_png}", file=sys.stderr)
    for rel, needle in (
        ("voa-wordmark.svg", 'src="voa-wordmark.svg"'),
        ("voa-wordmark-light.svg", 'src="voa-wordmark-light.svg"'),
    ):
        p = here / rel
        if p.is_file():
            html = html.replace(needle, f'src="{_svg_data_url(p)}"')
        else:
            print(f"Warning: missing {p}", file=sys.stderr)
    return html


def inject_export_css_inline(html: str, here: Path) -> str:
    """Playwright set_content não resolve links relativos; embute cards-export.css."""
    if LINK_EXPORT_CSS not in html:
        return html
    css_path = here / "cards-export.css"
    if not css_path.is_file():
        print(f"Warning: missing {css_path}", file=sys.stderr)
        return html
    css_text = css_path.read_text(encoding="utf-8")
    return html.replace(
        LINK_EXPORT_CSS,
        f"<style>\n{css_text}\n</style>",
        1,
    )


def prepare_html_for_pdf(html: str, here: Path) -> str:
    html = inject_wordmarks(html, here)
    html = inject_export_css_inline(html, here)
    return html
