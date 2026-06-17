"""A frozen, offline snapshot used by ``--demo`` and the test suite.

The shapes mirror the real CoinStats responses so the same code paths run with
or without a key:

  * ``SAMPLE_BALANCE`` -> ``GET /wallet/balance``
  * ``SAMPLE_DEFI``    -> ``GET /wallet/defi``

It describes a plausible multichain wallet with a healthy DeFi book, so the
card and report have something interesting to show.
"""

from __future__ import annotations

from typing import Any, Dict, List

DEMO_ADDRESS = "0x94845333028B1204Fbe14E1278Fd4Adde46B22ce"


def _coin(symbol, name, chain, amount, price, pch=0.0):
    return {
        "symbol": symbol,
        "name": name,
        "chain": chain,
        "connectionId": chain,
        "coinId": name.lower().replace(" ", "-"),
        "amount": amount,
        "price": price,
        "pCh24h": pch,
    }


SAMPLE_BALANCE: List[Dict[str, Any]] = [
    _coin("WBTC", "Wrapped Bitcoin", "ethereum", 0.80, 64000.0, 1.4),
    _coin("ETH", "Ethereum", "ethereum", 12.5, 3400.0, 2.1),
    _coin("USDC", "USD Coin", "ethereum", 25000.0, 1.0, 0.0),
    _coin("ARB", "Arbitrum", "arbitrum", 8000.0, 1.10, -3.2),
    _coin("OP", "Optimism", "optimism", 3000.0, 2.40, 4.8),
    _coin("MATIC", "Polygon", "polygon", 5000.0, 0.70, -1.1),
]


def _protocol(pid, name, chain, value, kinds):
    return {
        "id": pid,
        "name": name,
        "chain": chain,
        "blockchain": {"name": chain.title()},
        "totalValue": {"USD": value},
        "investments": [{"id": k.lower(), "name": k} for k in kinds],
    }


SAMPLE_DEFI: Dict[str, Any] = {
    "totalAssets": {"USD": 139000.0},
    "protocols": [
        _protocol("aave-v3", "Aave", "ethereum", 60000.0, ["Lending"]),
        _protocol("lido", "Lido", "ethereum", 45000.0, ["Staking"]),
        _protocol("uniswap-v3", "Uniswap", "arbitrum", 22000.0, ["Liquidity"]),
        _protocol("pendle", "Pendle", "ethereum", 12000.0, ["Yield"]),
    ],
}
