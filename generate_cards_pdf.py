"""
Gera PDFs de impressão (frente + verso, sangria) para os três cartões.

  · access-card-vertical-print.pdf
  · access-card-horizontal-print.pdf
  · visitor-card-print.pdf

Requer: pip install playwright && playwright install chromium

Uso:
  python generate_cards_pdf.py              # todos
  python generate_cards_pdf.py --access     # só cartões de acesso (vertical + horizontal)
  python generate_cards_pdf.py --visitor    # só cartão de visita
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from card_pdf_utils import prepare_html_for_pdf


def _render_pdf(
    html_path: Path,
    out_path: Path,
    page_width: str,
    page_height: str,
) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Install Playwright: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        raise SystemExit(1)

    here = html_path.parent
    html_text = prepare_html_for_pdf(html_path.read_text(encoding="utf-8"), here)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_text, wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(out_path),
            width=page_width,
            height=page_height,
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            page_ranges="1-2",
        )
        browser.close()


ACCESS_JOBS: list[tuple[str, str, str, str]] = [
    ("access-card-vertical.html", "access-card-vertical-print.pdf", "74mm", "105.6mm"),
    ("access-card-horizontal.html", "access-card-horizontal-print.pdf", "105.6mm", "74mm"),
]

VISITOR_JOBS: list[tuple[str, str, str, str]] = [
    ("visitor-card.html", "visitor-card-print.pdf", "105mm", "75mm"),
]

ALL_JOBS = ACCESS_JOBS + VISITOR_JOBS


def _run(jobs: list[tuple[str, str, str, str]], here: Path) -> int:
    for html_name, pdf_name, w, h in jobs:
        html_path = here / html_name
        out_path = here / pdf_name
        if not html_path.exists():
            print(f"Missing {html_path}", file=sys.stderr)
            return 1
        _render_pdf(html_path, out_path, w, h)
        print(f"Wrote {out_path}")
    return 0


def main_access() -> int:
    return _run(ACCESS_JOBS, Path(__file__).resolve().parent)


def main_visitor() -> int:
    return _run(VISITOR_JOBS, Path(__file__).resolve().parent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate VOA card PDFs.")
    parser.add_argument(
        "--access",
        action="store_true",
        help="Only access cards (vertical + horizontal)",
    )
    parser.add_argument(
        "--visitor",
        action="store_true",
        help="Only business card (cartão de visita)",
    )
    args = parser.parse_args(argv)
    here = Path(__file__).resolve().parent

    if args.access and args.visitor:
        print("Use only one of --access or --visitor, or neither for all.", file=sys.stderr)
        return 1
    if args.access:
        return _run(ACCESS_JOBS, here)
    if args.visitor:
        return _run(VISITOR_JOBS, here)
    return _run(ALL_JOBS, here)


if __name__ == "__main__":
    raise SystemExit(main())
