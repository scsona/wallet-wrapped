"""Command line: ``wallet-wrapped show`` and ``wallet-wrapped card``."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from . import __version__
from .api import CoinStatsClient, CoinStatsError
from .sample_data import DEMO_ADDRESS, SAMPLE_BALANCE, SAMPLE_DEFI
from .wrapped import Wrapped, build_wrapped


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%b %d, %Y")


def _default_address() -> str:
    return os.environ.get("WALLET_ADDRESS") or DEMO_ADDRESS


def _gather(address: str, demo: bool, chain: str, connection_id: Optional[str]) -> Wrapped:
    """Build a Wrapped from the live API, or from bundled sample data in demo mode."""
    if demo:
        return build_wrapped(address, SAMPLE_BALANCE, SAMPLE_DEFI)
    client = CoinStatsClient()
    balance = client.get_wallet_balance(address, blockchain=chain, connection_id=connection_id)
    defi = client.get_wallet_defi(address, blockchain=chain, connection_id=connection_id)
    return build_wrapped(address, balance, defi)


def _wrapped_or_exit(args) -> Wrapped:
    address = args.address or (DEMO_ADDRESS if args.demo else _default_address())
    try:
        return _gather(address, args.demo, args.chain, args.connection_id)
    except ValueError as exc:  # no API key configured
        print(f"✗ {exc}", file=sys.stderr)
        print("  Tip: run with --demo to preview using bundled sample data.", file=sys.stderr)
        sys.exit(2)
    except CoinStatsError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        if exc.status in (401, 403):
            print("  Check your COINSTATS_API_KEY.", file=sys.stderr)
        sys.exit(1)


def _cmd_show(args) -> int:
    from .report import print_report  # local import keeps `rich` optional for `card`

    wrapped = _wrapped_or_exit(args)
    print_report(wrapped, generated_at=_today())
    return 0


def _cmd_card(args) -> int:
    from .svgcard import render_card

    wrapped = _wrapped_or_exit(args)
    svg = render_card(wrapped, generated_at=_today())
    if args.output in ("-", "/dev/stdout"):
        sys.stdout.write(svg)
        return 0
    out = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"✓ wrote {args.output}  ({wrapped.persona.emoji} {wrapped.persona.name}, "
          f"net worth {wrapped.net_worth:,.0f} USD)")
    return 0


def _add_common(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("address", nargs="?", help="wallet address (defaults to $WALLET_ADDRESS)")
    sub.add_argument("--demo", action="store_true", help="use bundled sample data, no API key needed")
    sub.add_argument("--chain", default="all",
                     help="blockchain filter: a chain id, comma list, or 'all' (default: all)")
    sub.add_argument("--connection-id", default=None,
                     help="connectionId from /wallet/blockchains (overrides --chain)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wallet-wrapped",
        description="Spotify Wrapped, but for any crypto wallet — powered by the CoinStats Crypto API.",
    )
    parser.add_argument("--version", action="version", version=f"wallet-wrapped {__version__}")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="print the Wrapped report to the terminal")
    _add_common(show)
    show.set_defaults(func=_cmd_show)

    card = sub.add_parser("card", help="render the Wrapped SVG card")
    _add_common(card)
    card.add_argument("-o", "--output", default="assets/wrapped.svg",
                      help="output path, or '-' for stdout (default: assets/wrapped.svg)")
    card.set_defaults(func=_cmd_card)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
