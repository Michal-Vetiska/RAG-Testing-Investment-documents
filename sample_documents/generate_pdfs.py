#!/usr/bin/env python3
"""Generate synthetic investment fund PDFs for the RAG PoC (no real personal data)."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

OUT_DIR = Path(__file__).resolve().parent


def _add_page(doc: fitz.Document, title: str, lines: list[str]) -> None:
    page = doc.new_page(width=595, height=842)  # A4
    y = 72
    page.insert_text((72, y), title, fontsize=16, fontname="helv")
    y += 28
    for line in lines:
        # Simple wrap for long lines
        while len(line) > 95:
            page.insert_text((72, y), line[:95], fontsize=11, fontname="helv")
            line = line[95:]
            y += 16
        page.insert_text((72, y), line, fontsize=11, fontname="helv")
        y += 16


def build_alpha() -> Path:
    doc = fitz.open()
    _add_page(
        doc,
        "Alpha Growth Fund — Key Investor Information",
        [
            "Fund name: Alpha Growth Fund",
            "Management company: Northbridge Asset Management",
            "Legal form: open-ended mutual fund",
            "",
            "Minimum initial investment: 50 000 CZK",
            "Subsequent subscription minimum: 5 000 CZK",
            "Recommended investment horizon: minimum 5 years",
            "Synthetic risk indicator (SRRI): 5 / 7",
            "",
            "Investment objective: long-term capital growth through equity",
            "exposure primarily in developed markets.",
            "",
            "This document is synthetic and for technical demonstration only.",
            "It does not constitute investment advice.",
        ],
    )
    _add_page(
        doc,
        "Alpha Growth Fund — Fees and Charges",
        [
            "Fund name: Alpha Growth Fund",
            "",
            "Annual management fee: 1.35 %",
            "Entry fee (subscription fee): 3.00 %",
            "Exit fee (redemption fee): 0.00 %",
            "Performance fee: none",
            "",
            "Ongoing charges figure (OCF) estimate: 1.55 % per year.",
            "Fees are deducted from fund assets and reduce net returns.",
            "",
            "Comparison note: Alpha Growth Fund management fee is higher than",
            "the Beta Income Fund management fee disclosed in that fund's KIID.",
        ],
    )
    _add_page(
        doc,
        "Alpha Growth Fund — ESG Policy",
        [
            "Fund name: Alpha Growth Fund",
            "",
            "Internal ESG scoring uses a 0–100 scale.",
            "Minimum internal ESG score required for a new Alpha equity position: 55 / 100",
            "",
            "Positions below this threshold may not be newly initiated.",
            "Existing holdings that fall below the threshold are reviewed quarterly.",
            "",
            "Synthetic risk indicator reminder: 5 / 7",
            "",
            "Northbridge Asset Management publishes an annual stewardship report.",
            "No individual executive biography is included in this fund document.",
        ],
    )
    path = OUT_DIR / "Alpha Growth Fund.pdf"
    doc.save(path)
    doc.close()
    return path


def build_beta() -> Path:
    doc = fitz.open()
    _add_page(
        doc,
        "Beta Income Fund — Key Investor Information",
        [
            "Fund name: Beta Income Fund",
            "Management company: Northbridge Asset Management",
            "Legal form: open-ended mutual fund",
            "",
            "Minimum initial investment: 20 000 CZK",
            "Recommended investment horizon: minimum 3 years",
            "Synthetic risk indicator (SRRI): 3 / 7",
            "",
            "Investment objective: generate regular income with moderate capital",
            "preservation through investment-grade fixed income instruments.",
            "",
            "This document is synthetic and for technical demonstration only.",
            "It does not constitute investment advice.",
        ],
    )
    _add_page(
        doc,
        "Beta Income Fund — Fees and Income Distribution",
        [
            "Fund name: Beta Income Fund",
            "",
            "Annual management fee: 0.85 %",
            "Entry fee (subscription fee): 1.00 %",
            "Exit fee (redemption fee): 0.00 %",
            "",
            "Income distribution frequency: quarterly",
            "Distribution months: March / June / September / December",
            "",
            "Compared with Alpha Growth Fund (management fee 1.35 %),",
            "Beta Income Fund has the lower annual management fee by",
            "0.50 percentage points (1.35 % − 0.85 % = 0.50).",
        ],
    )
    _add_page(
        doc,
        "Beta Income Fund — ESG Policy",
        [
            "Fund name: Beta Income Fund",
            "",
            "Internal ESG scoring uses a 0–100 scale.",
            "Minimum internal ESG score required for a new Beta corporate bond",
            "position: 60 / 100",
            "",
            "Sovereign bonds may use a separate country-level ESG overlay.",
            "Issuers failing the minimum score are excluded from new purchases.",
            "",
            "Northbridge Asset Management oversees ESG integration for both",
            "Alpha Growth Fund and Beta Income Fund.",
            "This KIID does not name any individual CEO.",
        ],
    )
    path = OUT_DIR / "Beta Income Fund.pdf"
    doc.save(path)
    doc.close()
    return path


def main() -> None:
    alpha = build_alpha()
    beta = build_beta()
    print(f"Wrote {alpha}")
    print(f"Wrote {beta}")


if __name__ == "__main__":
    main()
