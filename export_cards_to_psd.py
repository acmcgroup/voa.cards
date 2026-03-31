"""
Exporta cartões para PSD (Photoshop) ~300 DPI com camadas nomeadas.

Por ficheiro:
  · Grupo "Front" / "Back" (ordem típica de edição)
  · Camada "Guides  -  trim (10mm)"  -  rectângulo de corte (sangria)
  · Camada "Print  -  composite 300dpi"  -  raster igual ao PDF
  · (Só access cards) "Asset  -  logo.png"  -  logótipo posicionado para editar independentemente

Requer: playwright, pymupdf (fitz), pillow, pytoshop

Uso:
  python export_cards_to_psd.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw

from card_pdf_utils import prepare_html_for_pdf

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore

from pytoshop import enums
from pytoshop.layers import ChannelImageData
from pytoshop.user.nested_layers import Group, Image as PsdImage, nested_layers_to_psd

DPI = 300
BLEED_MM = 10.0


def mm_to_px(mm: float) -> int:
    return max(1, int(round(mm * DPI / 25.4)))


def bleed_px() -> int:
    return mm_to_px(BLEED_MM)


def _pdf_bytes_from_html(html: str, page_w_mm: str, page_h_mm: str) -> bytes:
    if sync_playwright is None:
        raise RuntimeError("Install playwright")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.emulate_media(media="print")
        pdf = page.pdf(
            width=page_w_mm,
            height=page_h_mm,
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            page_ranges="1-2",
        )
        browser.close()
    return pdf


def _page_rgb_at_dpi(pdf_bytes: bytes, page_index: int) -> np.ndarray:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index >= len(doc):
        doc.close()
        raise IndexError(f"PDF has no page {page_index}")
    page = doc[page_index]
    zoom = DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    h, w = pix.height, pix.width
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(h, w, pix.n)
    doc.close()
    if rgb.shape[2] == 4:
        rgb = rgb[:, :, :3]
    return rgb


def _guides_rgba(h: int, w: int, bleed: int) -> np.ndarray:
    """Contorno do trim (área de corte) sobre fundo transparente."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    gray = (60, 60, 60, 255)
    dash, gap = max(4, DPI // 50), max(3, DPI // 80)
    x0, y0 = bleed, bleed
    x1, y1 = w - 1 - bleed, h - 1 - bleed
    if x1 <= x0 or y1 <= y0:
        return np.array(im)

    def dash_h(y: int) -> None:
        x = x0
        while x < x1:
            draw.line([(x, y), (min(x + dash, x1), y)], fill=gray, width=max(1, DPI // 300))
            x += dash + gap

    def dash_v(x: int) -> None:
        y = y0
        while y < y1:
            draw.line([(x, y), (x, min(y + dash, y1))], fill=gray, width=max(1, DPI // 300))
            y += dash + gap

    dash_h(y0)
    dash_h(y1)
    dash_v(x0)
    dash_v(x1)
    return np.array(im)


def _rgba_to_psd_image(name: str, rgba: np.ndarray) -> PsdImage:
    h, w, _ = rgba.shape
    r = rgba[:, :, 0].astype(np.uint8, copy=False)
    g = rgba[:, :, 1].astype(np.uint8, copy=False)
    b = rgba[:, :, 2].astype(np.uint8, copy=False)
    a = rgba[:, :, 3].astype(np.uint8, copy=False)
    ch = {
        enums.ChannelId.red: ChannelImageData(np.ascontiguousarray(r)),
        enums.ChannelId.green: ChannelImageData(np.ascontiguousarray(g)),
        enums.ChannelId.blue: ChannelImageData(np.ascontiguousarray(b)),
        enums.ChannelId.transparency: ChannelImageData(np.ascontiguousarray(a)),
    }
    return PsdImage(
        name=name,
        top=0,
        left=0,
        bottom=h,
        right=w,
        channels=ch,
    )


def _rgb_to_psd_image(name: str, rgb: np.ndarray) -> PsdImage:
    h, w, _ = rgb.shape
    r = np.ascontiguousarray(rgb[:, :, 0])
    g = np.ascontiguousarray(rgb[:, :, 1])
    b = np.ascontiguousarray(rgb[:, :, 2])
    t = np.full((h, w), 255, dtype=np.uint8)
    ch = {
        enums.ChannelId.red: ChannelImageData(r),
        enums.ChannelId.green: ChannelImageData(g),
        enums.ChannelId.blue: ChannelImageData(b),
        enums.ChannelId.transparency: ChannelImageData(t),
    }
    return PsdImage(name=name, top=0, left=0, bottom=h, right=w, channels=ch)


def _logo_layer_vertical(w: int, h: int) -> PsdImage | None:
    logo_path = Path(__file__).resolve().parent / "logo.png"
    if not logo_path.is_file():
        return None
    b = bleed_px()
    logo = Image.open(logo_path).convert("RGBA")
    target_h = mm_to_px(7)
    tw = max(1, int(logo.width * target_h / logo.height))
    logo = logo.resize((tw, target_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = (w - tw) // 2
    y = b + mm_to_px(3.8)
    canvas.paste(logo, (x, y), logo)
    return _rgba_to_psd_image("Asset  -  logo.png", np.array(canvas))


def _logo_layer_horizontal(w: int, h: int) -> PsdImage | None:
    logo_path = Path(__file__).resolve().parent / "logo.png"
    if not logo_path.is_file():
        return None
    b = bleed_px()
    edge = mm_to_px(17)
    top_pad = mm_to_px(3)
    logo = Image.open(logo_path).convert("RGBA")
    target_h = mm_to_px(6)
    tw = max(1, int(logo.width * target_h / logo.height))
    logo = logo.resize((tw, target_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = b + edge
    y = b + top_pad
    canvas.paste(logo, (x, y), logo)
    return _rgba_to_psd_image("Asset  -  logo.png", np.array(canvas))


def _build_psd(
    front_rgb: np.ndarray,
    back_rgb: np.ndarray,
    logo_layer_fn,
    out_path: Path,
) -> None:
    h, w, _ = front_rgb.shape
    bleed = bleed_px()
    guides = _guides_rgba(h, w, bleed)

    front_layers: list = []
    extra = logo_layer_fn(w, h)
    if extra is not None:
        front_layers.append(extra)
    front_layers.append(_rgb_to_psd_image("Print  -  composite 300dpi", front_rgb))
    front_layers.append(_rgba_to_psd_image("Guides  -  trim (10mm bleed)", guides))

    back_layers = [
        _rgb_to_psd_image("Print  -  composite 300dpi", back_rgb),
        _rgba_to_psd_image("Guides  -  trim (10mm bleed)", np.array(_guides_rgba(h, w, bleed))),
    ]

    # Ordem: capa (frente) primeiro, informação (verso) a seguir — alinhado ao HTML e ao PDF
    root = [
        Group(name="Front", closed=False, layers=front_layers),
        Group(name="Back", closed=False, layers=back_layers),
    ]

    psd = nested_layers_to_psd(
        root,
        enums.ColorMode.rgb,
        size=(h, w),
        compression=enums.Compression.raw,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        psd.write(f)


def _export_one(
    html_path: Path,
    out_psd: Path,
    pdf_w: str,
    pdf_h: str,
    logo_fn,
) -> None:
    here = html_path.parent
    html = prepare_html_for_pdf(html_path.read_text(encoding="utf-8"), here)
    pdf_bytes = _pdf_bytes_from_html(html, pdf_w, pdf_h)
    front = _page_rgb_at_dpi(pdf_bytes, 0)
    back = _page_rgb_at_dpi(pdf_bytes, 1)
    if front.shape != back.shape:
        raise RuntimeError("Front/back raster size mismatch")
    _build_psd(front, back, logo_fn, out_psd)
    print(f"Wrote {out_psd}")


def main() -> int:
    if sync_playwright is None:
        print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1
    here = Path(__file__).resolve().parent

    jobs = [
        (
            here / "access-card-vertical.html",
            here / "access-card-vertical-300dpi.psd",
            "74mm",
            "105.6mm",
            _logo_layer_vertical,
        ),
        (
            here / "access-card-horizontal.html",
            here / "access-card-horizontal-300dpi.psd",
            "105.6mm",
            "74mm",
            _logo_layer_horizontal,
        ),
        (
            here / "visitor-card.html",
            here / "visitor-card-300dpi.psd",
            "105mm",
            "75mm",
            lambda w, h: None,
        ),
    ]

    for html_path, out_psd, pw, ph, logo_fn in jobs:
        if not html_path.exists():
            print(f"Missing {html_path}", file=sys.stderr)
            return 1
        _export_one(html_path, out_psd, pw, ph, logo_fn)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
