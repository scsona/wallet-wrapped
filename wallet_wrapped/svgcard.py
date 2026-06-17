"""Render a :class:`~wallet_wrapped.wrapped.Wrapped` as a self-contained SVG.

No browser, no external fonts, no scripts — just a string you can drop into a
README via ``<img src="assets/wrapped.svg">`` and let GitHub serve. Built on
the standard library so the card generator has zero runtime dependencies.
"""

from __future__ import annotations

import math
from typing import List, Optional

from .wrapped import Wrapped, money

W, H = 860, 500
PAD = 40
INNER_W = W - 2 * PAD  # 780
FONT = "'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _full_usd(value: float) -> str:
    if abs(value) >= 1000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _ring_color(score: int) -> str:
    if score >= 67:
        return "#34d399"
    if score >= 34:
        return "#fbbf24"
    return "#fb7185"


def render_card(wrapped: Wrapped, generated_at: Optional[str] = None) -> str:
    """Return a complete ``<svg>…</svg>`` document for ``wrapped``."""
    parts: List[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Wallet Wrapped card for {_esc(wrapped.short_address)}">'
    )
    parts.append(_defs())

    # backdrop
    parts.append(
        f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="24" '
        f'fill="url(#bg)" stroke="#1e293b" stroke-width="1.5"/>'
    )
    parts.append(
        f'<rect x="6" y="6" width="{W - 12}" height="6" rx="3" fill="url(#accent)"/>'
    )

    parts.append(_header(wrapped, generated_at))
    parts.append(_net_worth_block(wrapped))
    parts.append(_ring(wrapped))
    parts.append(_stat_tiles(wrapped))
    parts.append(_allocation(wrapped))
    parts.append(_footer())

    parts.append("</svg>")
    return "".join(parts)


def _defs() -> str:
    return (
        "<defs>"
        '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#0b1220"/>'
        '<stop offset="1" stop-color="#0f172a"/>'
        "</linearGradient>"
        '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#38bdf8"/>'
        '<stop offset="0.5" stop-color="#a78bfa"/>'
        '<stop offset="1" stop-color="#34d399"/>'
        "</linearGradient>"
        '<linearGradient id="nw" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#7dd3fc"/>'
        '<stop offset="1" stop-color="#c4b5fd"/>'
        "</linearGradient>"
        "</defs>"
    )


def _header(w: Wrapped, generated_at: Optional[str]) -> str:
    out = [
        f'<text x="{PAD}" y="58" font-family="{FONT}" font-size="24" '
        f'font-weight="700" letter-spacing="1">'
        f'<tspan fill="#f8fafc">WALLET</tspan> '
        f'<tspan fill="url(#accent)">WRAPPED</tspan></text>',
        f'<text x="{PAD}" y="80" font-family="{FONT}" font-size="12.5" '
        f'fill="#64748b">a Spotify-Wrapped for your on-chain life</text>',
    ]
    # address pill (top-right)
    pill_w = 168
    pill_x = W - PAD - pill_w
    out.append(
        f'<rect x="{pill_x}" y="38" width="{pill_w}" height="30" rx="15" '
        f'fill="#1e293b"/>'
        f'<circle cx="{pill_x + 18}" cy="53" r="5" fill="#34d399"/>'
        f'<text x="{pill_x + 32}" y="57" font-family="{FONT}" font-size="14" '
        f'font-weight="600" fill="#e2e8f0">{_esc(w.short_address)}</text>'
    )
    if generated_at:
        out.append(
            f'<text x="{W - PAD}" y="82" text-anchor="end" font-family="{FONT}" '
            f'font-size="11.5" fill="#64748b">as of {_esc(generated_at)}</text>'
        )
    return "".join(out)


def _net_worth_block(w: Wrapped) -> str:
    out = [
        f'<text x="{PAD}" y="128" font-family="{FONT}" font-size="13" '
        f'letter-spacing="2" fill="#64748b">TOTAL NET WORTH</text>',
        f'<text x="{PAD}" y="178" font-family="{FONT}" font-size="52" '
        f'font-weight="800" fill="url(#nw)">{_esc(_full_usd(w.net_worth))}</text>',
    ]
    # persona pill
    label = f"{w.persona.emoji} {w.persona.name}"
    pill_w = 34 + int(len(w.persona.name) * 10.5) + 24
    out.append(
        f'<rect x="{PAD}" y="200" width="{pill_w}" height="34" rx="17" '
        f'fill="#11203a" stroke="#334155" stroke-width="1"/>'
        f'<text x="{PAD + 16}" y="223" font-family="{FONT}" font-size="16" '
        f'font-weight="700" fill="#f1f5f9">{_esc(label)}</text>'
    )
    out.append(
        f'<text x="{PAD}" y="258" font-family="{FONT}" font-size="13.5" '
        f'fill="#94a3b8">{_esc(w.persona.tagline)}</text>'
    )
    return "".join(out)


def _ring(w: Wrapped) -> str:
    cx, cy, r = 700, 168, 66
    stroke = 15
    circ = 2 * math.pi * r
    frac = max(0.0, min(1.0, w.diversification / 100))
    on = circ * frac
    color = _ring_color(w.diversification)
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1e293b" '
        f'stroke-width="{stroke}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-dasharray="{on:.2f} {circ - on:.2f}" '
        f'transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="40" font-weight="800" fill="#f8fafc">{w.diversification}</text>'
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="12" fill="#64748b">out of 100</text>'
        f'<text x="{cx}" y="{cy + 92}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="13" letter-spacing="1.5" fill="#94a3b8">DIVERSIFICATION</text>'
    )


def _stat_tiles(w: Wrapped) -> str:
    tiles = [
        (str(w.n_chains), "CHAINS"),
        (str(w.n_tokens), "TOKENS"),
        (str(w.n_protocols), "PROTOCOLS"),
        (f"{w.defi_ratio * 100:.0f}%", "IN DEFI"),
    ]
    gap = 16
    tw = (INNER_W - gap * (len(tiles) - 1)) / len(tiles)
    y = 290
    th = 72
    out = []
    for i, (value, label) in enumerate(tiles):
        x = PAD + i * (tw + gap)
        cx = x + tw / 2
        out.append(
            f'<rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="{th}" rx="14" '
            f'fill="#0e1a30" stroke="#1e293b" stroke-width="1"/>'
            f'<text x="{cx:.1f}" y="{y + 38}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="28" font-weight="800" '
            f'fill="#e2e8f0">{_esc(value)}</text>'
            f'<text x="{cx:.1f}" y="{y + 58}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11" letter-spacing="1.5" '
            f'fill="#64748b">{_esc(label)}</text>'
        )
    return "".join(out)


def _allocation(w: Wrapped) -> str:
    bar_y = 392
    bar_h = 24
    out = [
        f'<text x="{PAD}" y="382" font-family="{FONT}" font-size="12" '
        f'letter-spacing="1.5" fill="#64748b">PORTFOLIO ALLOCATION</text>'
    ]
    if not w.allocation:
        out.append(
            f'<rect x="{PAD}" y="{bar_y}" width="{INNER_W}" height="{bar_h}" '
            f'rx="12" fill="#1e293b"/>'
            f'<text x="{PAD + INNER_W / 2}" y="{bar_y + 16}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" fill="#64748b">no holdings</text>'
        )
        return "".join(out)

    # clip so segments share rounded ends
    out.append(
        f'<clipPath id="barclip"><rect x="{PAD}" y="{bar_y}" width="{INNER_W}" '
        f'height="{bar_h}" rx="12"/></clipPath>'
    )
    out.append(f'<g clip-path="url(#barclip)">')
    total_pct = sum(a.pct for a in w.allocation) or 100.0
    x = float(PAD)
    for a in w.allocation:
        seg = INNER_W * (a.pct / total_pct)
        out.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{seg:.2f}" height="{bar_h}" '
            f'fill="{a.color}"/>'
        )
        x += seg
    out.append("</g>")

    # legend, wrapping across up to two rows
    out.append(_legend(w))
    return "".join(out)


def _legend(w: Wrapped) -> str:
    out = []
    x = float(PAD)
    y = 448
    line_h = 24
    max_x = PAD + INNER_W
    for a in w.allocation:
        text = f"{a.label} {a.pct:.0f}%"
        item_w = 16 + len(text) * 7.3 + 20
        if x + item_w > max_x and x > PAD:
            x = float(PAD)
            y += line_h
        out.append(
            f'<circle cx="{x + 5:.1f}" cy="{y - 4}" r="5" fill="{a.color}"/>'
            f'<text x="{x + 16:.1f}" y="{y}" font-family="{FONT}" font-size="13" '
            f'fill="#cbd5e1">{_esc(text)}</text>'
        )
        x += item_w
    return "".join(out)


def _footer() -> str:
    y = H - 22
    return (
        f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="11.5" '
        f'fill="#475569">Data: '
        f'<tspan fill="#64748b" font-weight="600">CoinStats Crypto API</tspan>'
        f' · /wallet/balance + /wallet/defi</text>'
        f'<text x="{W - PAD}" y="{y}" text-anchor="end" font-family="{FONT}" '
        f'font-size="11.5" fill="#475569">github.com/scsona/wallet-wrapped</text>'
    )
