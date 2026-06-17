"""wallet-wrapped — Spotify Wrapped for any crypto wallet.

Powered by the CoinStats Crypto API:
  * GET /wallet/balance  — token holdings across chains
  * GET /wallet/defi     — DeFi positions across protocols

Docs & free API key: https://api.coinstats.app/
"""

from .api import CoinStatsClient, CoinStatsError
from .wrapped import Wrapped, build_wrapped

__version__ = "1.0.0"

__all__ = [
    "CoinStatsClient",
    "CoinStatsError",
    "Wrapped",
    "build_wrapped",
    "__version__",
]
