"""Tests for the SVG card renderer."""

import xml.dom.minidom as minidom

from wallet_wrapped.sample_data import SAMPLE_BALANCE, SAMPLE_DEFI
from wallet_wrapped.svgcard import render_card
from wallet_wrapped.wrapped import build_wrapped

ADDR = "0x94845333028B1204Fbe14E1278Fd4Adde46B22ce"


def _card():
    w = build_wrapped(ADDR, SAMPLE_BALANCE, SAMPLE_DEFI)
    return render_card(w, generated_at="Jun 17, 2026")


def test_card_is_well_formed_xml():
    svg = _card()
    # raises on malformed markup
    doc = minidom.parseString(svg)
    assert doc.documentElement.tagName == "svg"


def test_card_contains_key_content():
    svg = _card()
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "WALLET" in svg and "WRAPPED" in svg
    assert "0x9484…22ce" in svg          # short address
    assert "Yield Farmer" in svg          # persona
    assert "/wallet/balance + /wallet/defi" in svg
    assert "as of Jun 17, 2026" in svg


def test_card_escapes_angle_brackets():
    # symbols are upper-cased by the engine, so "<x>" becomes "<X>"
    w = build_wrapped("0xabc", [
        {"symbol": "<x>", "chain": "ethereum", "amount": 1, "price": 100.0},
    ], None)
    svg = render_card(w)
    assert "<X>" not in svg
    assert "&lt;X&gt;" in svg
    # still valid XML after escaping
    minidom.parseString(svg)


def test_empty_wallet_card_renders():
    w = build_wrapped(ADDR, [], None)
    svg = render_card(w)
    minidom.parseString(svg)
    assert "Ghost Wallet" in svg
    assert "no holdings" in svg
