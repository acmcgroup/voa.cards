"""
Gera apenas os PDFs dos cartões de acesso (vertical + horizontal).

Preferir: python generate_cards_pdf.py --access
"""
from __future__ import annotations

from generate_cards_pdf import main_access


def main() -> int:
    return main_access()


if __name__ == "__main__":
    raise SystemExit(main())
