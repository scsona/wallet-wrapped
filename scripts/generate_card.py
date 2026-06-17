#!/usr/bin/env python3
"""Render assets/wrapped.svg — the entry point for the self-updating card job.

Usage:
    COINSTATS_API_KEY=... WALLET_ADDRESS=0x... python scripts/generate_card.py [out.svg]

With no key (or on any API hiccup) it falls back to bundled sample data, so the
GitHub Action — and any fork — never breaks.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Allow running straight from a checkout without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallet_wrapped.api import CoinStatsClient, CoinStatsError  # noqa: E402
from wallet_wrapped.sample_data import (  # noqa: E402
    DEMO_ADDRESS,
    SAMPLE_BALANCE,
    SAMPLE_DEFI,
)
from wallet_wrapped.svgcard import render_card  # noqa: E402
from wallet_wrapped.wrapped import build_wrapped  # noqa: E402


def main() -> int:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "assets/wrapped.svg"
    address = os.environ.get("WALLET_ADDRESS") or DEMO_ADDRESS
    api_key = os.environ.get("COINSTATS_API_KEY")

    if api_key:
        try:
            client = CoinStatsClient(api_key=api_key)
            balance = client.get_wallet_balance(address, blockchain="all")
            defi = client.get_wallet_defi(address, blockchain="all")
            wrapped = build_wrapped(address, balance, defi)
            print(f"• live data for {wrapped.short_address}: net worth ${wrapped.net_worth:,.0f}")
        except CoinStatsError as exc:
            print(f"! API error ({exc.status}); falling back to sample data.")
            wrapped = build_wrapped(DEMO_ADDRESS, SAMPLE_BALANCE, SAMPLE_DEFI)
    else:
        print("! No COINSTATS_API_KEY set — rendering from bundled sample data.")
        wrapped = build_wrapped(DEMO_ADDRESS, SAMPLE_BALANCE, SAMPLE_DEFI)

    generated_at = datetime.now(timezone.utc).strftime("%b %d, %Y")
    svg = render_card(wrapped, generated_at=generated_at)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"✓ wrote {out_path} ({wrapped.persona.emoji} {wrapped.persona.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
