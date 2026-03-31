"""
Build print-ready visitor-card PDF (front + back) with bleed.

Loads the wordmark from the main site brand folder:
  06-website/new-strategy/site/assets/brand/

Requires: pip install playwright && playwright install chromium

Run:
  python generate_visitor_card_pdf.py
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

# Must match src= in visitor-card.html for both logo <img> tags
LOGO_IMG_ATTR = (
    'src="../06-website/new-strategy/site/assets/brand/logo/logo.png"'
)


def _brand_dir() -> Path:
    """visitor-card/ → parent = Voa.aero repo root."""
    return Path(__file__).resolve().parent.parent / "06-website" / "new-strategy" / "site" / "assets" / "brand"


def _resolve_site_logo() -> Path | None:
    brand = _brand_dir()
    candidates: list[Path] = [
        brand / "logo.png",
        brand / "logo" / "logo.png",
    ]
    logo_dir = brand / "logo"
    if logo_dir.is_dir():
        candidates.extend(sorted(logo_dir.glob("*.png")))
    for path in candidates:
        if path.is_file():
            return path
    return None


def _png_data_url(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def main() -> int:
    here = Path(__file__).resolve().parent
    html_path = here / "visitor-card.html"
    out = here / "visitor-card-print.pdf"

    if not html_path.exists():
        print(f"Missing {html_path}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Install Playwright: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 1

    html_text = html_path.read_text(encoding="utf-8")
    logo_path = _resolve_site_logo()
    if logo_path is not None:
        html_text = html_text.replace(
            LOGO_IMG_ATTR,
            f'src="{_png_data_url(logo_path)}"',
        )
    else:
        print(
            "Warning: no PNG logo under 06-website/new-strategy/site/assets/brand/. "
            "PDF may show a broken image in the preview until logo.png exists.",
            file=sys.stderr,
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_text, wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(out),
            width="91mm",
            height="61mm",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            page_ranges="1-2",
        )
        browser.close()

    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
