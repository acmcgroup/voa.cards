"""
Gera apenas o PDF do Cartão de Visita.

Preferir: python generate_cards_pdf.py --visitor
"""
from __future__ import annotations

from generate_cards_pdf import main_visitor


def main() -> int:
    return main_visitor()


if __name__ == "__main__":
    raise SystemExit(main())
