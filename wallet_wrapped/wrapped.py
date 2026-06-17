"""The engine: turn raw CoinStats wallet data into a "Wrapped" story.

Everything here is pure, deterministic and standard-library only, so it is
trivially testable and the SVG card / terminal report are just two different
views over the same :class:`Wrapped` object.

Inputs are exactly what the CoinStats API returns:

  * ``balance``  -> ``GET /wallet/balance``  (a list of token dicts)
  * ``defi``     -> ``GET /wallet/defi``      (``{"totalAssets", "protocols"}``)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# --- knobs you can tweak ---------------------------------------------------

# Diversification score = blend of "how evenly spread" and "how many assets".
# Both live in [0, 1]; the weights below must sum to 1.
DIVERSIFICATION_WEIGHTS = {"spread": 0.70, "breadth": 0.30}
BREADTH_SATURATION = 12  # holding this many distinct assets maxes out breadth.

# Symbols we treat as "blue chips" and "stablecoins" when sketching a persona.
BLUECHIPS = {"BTC", "WBTC", "ETH", "WETH", "STETH", "WSTETH", "WEETH", "RETH", "CBETH"}
STABLES = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FRAX", "LUSD", "GUSD",
    "USDD", "FDUSD", "PYUSD", "USDE", "SUSD", "USDS", "CRVUSD", "GHO",
}

# Colour palette for the allocation bar (also reused by the SVG card).
PALETTE = [
    "#38bdf8", "#a78bfa", "#34d399", "#fbbf24",
    "#fb7185", "#22d3ee", "#f97316", "#94a3b8",
]
OTHER_COLOR = "#475569"


# --- data model ------------------------------------------------------------


@dataclass
class Asset:
    """One slice of the portfolio — a liquid token or a DeFi protocol stack."""

    label: str
    value_usd: float
    is_defi: bool = False
    color: str = OTHER_COLOR
    pct: float = 0.0  # share of net worth, filled in by build_wrapped


@dataclass
class Protocol:
    name: str
    value_usd: float
    chain: str = ""
    kinds: List[str] = field(default_factory=list)  # e.g. ["Lending", "Liquidity"]


@dataclass
class Persona:
    name: str
    emoji: str
    tagline: str
    score: float = 0.0


@dataclass
class Wrapped:
    """Everything the card and the report need, computed once."""

    address: str
    net_worth: float
    liquid_value: float
    defi_value: float
    defi_ratio: float
    chains: List[str]
    n_tokens: int
    n_protocols: int
    allocation: List[Asset]          # top slices + an "Other" bucket, for the bar
    top_tokens: List[Asset]          # biggest liquid holdings
    top_protocols: List[Protocol]    # biggest DeFi positions
    diversification: int             # 0-100
    persona: Persona
    fun_facts: List[str]

    @property
    def short_address(self) -> str:
        if len(self.address) <= 12:
            return self.address
        return f"{self.address[:6]}…{self.address[-4:]}"

    @property
    def n_chains(self) -> int:
        return len(self.chains)


# --- helpers ---------------------------------------------------------------


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _usd(value_obj: Any) -> float:
    """Pull a USD number out of either a scalar or a ``{"USD": ...}`` dict."""
    if isinstance(value_obj, dict):
        return _f(value_obj.get("USD"))
    return _f(value_obj)


def _token_value(token: Dict[str, Any]) -> float:
    return _f(token.get("amount")) * _f(token.get("price"))


# --- the build -------------------------------------------------------------


def build_wrapped(
    address: str,
    balance: Sequence[Dict[str, Any]],
    defi: Optional[Dict[str, Any]] = None,
    top_n: int = 6,
) -> Wrapped:
    """Crunch raw API payloads into a :class:`Wrapped`.

    Parameters
    ----------
    address:
        The wallet address (used only for display).
    balance:
        The list returned by ``GET /wallet/balance``.
    defi:
        The object returned by ``GET /wallet/defi`` (optional).
    top_n:
        How many individual slices to show in the allocation bar before the
        remainder collapses into "Other".
    """
    defi = defi or {}

    # --- liquid tokens -----------------------------------------------------
    tokens: List[Asset] = []
    chains = set()
    stable_value = 0.0
    bluechip_value = 0.0
    smallcap_value = 0.0
    for tok in balance:
        value = _token_value(tok)
        if value <= 0:
            continue
        symbol = str(tok.get("symbol") or tok.get("coinId") or "?").upper()
        chain = str(tok.get("chain") or tok.get("connectionId") or "").lower()
        if chain:
            chains.add(chain)
        tokens.append(Asset(label=symbol, value_usd=value, is_defi=False))
        if symbol in STABLES:
            stable_value += value
        elif symbol in BLUECHIPS:
            bluechip_value += value
        else:
            smallcap_value += value

    liquid_value = sum(t.value_usd for t in tokens)

    # --- DeFi protocols ----------------------------------------------------
    protocols: List[Protocol] = []
    for proto in defi.get("protocols") or []:
        value = _usd(proto.get("totalValue"))
        if value <= 0:
            continue
        chain = str(proto.get("chain") or "").lower()
        if chain:
            chains.add(chain)
        kinds = sorted(
            {
                str(inv.get("name") or inv.get("id") or "").strip()
                for inv in (proto.get("investments") or [])
                if inv.get("name") or inv.get("id")
            }
        )
        protocols.append(
            Protocol(
                name=str(proto.get("name") or proto.get("id") or "Protocol"),
                value_usd=value,
                chain=chain,
                kinds=kinds,
            )
        )

    # Trust the API's own DeFi total if present; else sum the protocols.
    defi_value = _usd(defi.get("totalAssets"))
    if defi_value <= 0:
        defi_value = sum(p.value_usd for p in protocols)

    net_worth = liquid_value + defi_value
    defi_ratio = (defi_value / net_worth) if net_worth else 0.0

    # --- allocation bar (tokens + protocols as one portfolio) --------------
    combined: List[Asset] = list(tokens) + [
        Asset(label=p.name, value_usd=p.value_usd, is_defi=True) for p in protocols
    ]
    combined.sort(key=lambda a: a.value_usd, reverse=True)

    allocation = _build_allocation(combined, net_worth, top_n)

    top_tokens = sorted(tokens, key=lambda a: a.value_usd, reverse=True)[:5]
    for t in top_tokens:
        t.pct = (t.value_usd / net_worth * 100) if net_worth else 0.0
    top_protocols = sorted(protocols, key=lambda p: p.value_usd, reverse=True)[:5]

    diversification = _diversification_score(combined, net_worth)

    signals = {
        "net_worth": net_worth,
        "defi_ratio": defi_ratio,
        "n_chains": len(chains),
        "n_tokens": len(tokens),
        "n_protocols": len(protocols),
        "top_weight": (combined[0].value_usd / net_worth) if (combined and net_worth) else 0.0,
        "stable_weight": (stable_value / net_worth) if net_worth else 0.0,
        "bluechip_weight": (bluechip_value / net_worth) if net_worth else 0.0,
        "smallcap_weight": (smallcap_value / net_worth) if net_worth else 0.0,
        "n_assets": len(combined),
    }
    persona = pick_persona(signals)

    fun_facts = _fun_facts(
        net_worth=net_worth,
        chains=chains,
        n_tokens=len(tokens),
        defi_ratio=defi_ratio,
        n_protocols=len(protocols),
        combined=combined,
        top_protocols=top_protocols,
    )

    return Wrapped(
        address=address,
        net_worth=net_worth,
        liquid_value=liquid_value,
        defi_value=defi_value,
        defi_ratio=defi_ratio,
        chains=sorted(chains),
        n_tokens=len(tokens),
        n_protocols=len(protocols),
        allocation=allocation,
        top_tokens=top_tokens,
        top_protocols=top_protocols,
        diversification=diversification,
        persona=persona,
        fun_facts=fun_facts,
    )


def _build_allocation(combined: List[Asset], net_worth: float, top_n: int) -> List[Asset]:
    if not combined or net_worth <= 0:
        return []
    head = combined[:top_n]
    tail = combined[top_n:]
    slices: List[Asset] = []
    for i, asset in enumerate(head):
        slices.append(
            Asset(
                label=asset.label,
                value_usd=asset.value_usd,
                is_defi=asset.is_defi,
                color=PALETTE[i % len(PALETTE)],
                pct=asset.value_usd / net_worth * 100,
            )
        )
    if tail:
        other = sum(a.value_usd for a in tail)
        slices.append(
            Asset(
                label="Other",
                value_usd=other,
                color=OTHER_COLOR,
                pct=other / net_worth * 100,
            )
        )
    return slices


def _diversification_score(combined: List[Asset], net_worth: float) -> int:
    """A transparent 0-100 heuristic — *not* a risk rating.

    ``spread``   = 1 - HHI, where HHI is the Herfindahl index of asset weights
                   (1.0 = everything in one bag, →0 as it spreads out).
    ``breadth``  = how many distinct assets you hold, saturating at
                   ``BREADTH_SATURATION``.
    """
    if not combined or net_worth <= 0:
        return 0
    weights = [a.value_usd / net_worth for a in combined if a.value_usd > 0]
    hhi = sum(w * w for w in weights)
    spread = 1.0 - hhi
    # 1 asset -> 0, saturating at BREADTH_SATURATION distinct assets.
    breadth = (min(len(weights), BREADTH_SATURATION) - 1) / (BREADTH_SATURATION - 1)
    breadth = max(0.0, breadth)
    score = (
        DIVERSIFICATION_WEIGHTS["spread"] * spread
        + DIVERSIFICATION_WEIGHTS["breadth"] * breadth
    )
    return max(0, min(100, round(score * 100)))


# --- personas --------------------------------------------------------------

# Each persona scores itself in [0, 1] from the signal bundle; highest wins.
# Ties break by list order (earlier = higher priority).
_PERSONAS = [
    (
        Persona("Yield Farmer", "🌾", "Capital doesn't sleep — it's out earning across protocols."),
        lambda s: s["defi_ratio"] * (0.5 + 0.5 * min(s["n_protocols"], 4) / 4),
    ),
    (
        Persona("Blue-chip Whale", "🐋", "Big bags, blue chips. The tide moves when you do."),
        lambda s: s["bluechip_weight"] * min(s["net_worth"] / 250_000, 1.0),
    ),
    (
        Persona("Diamond Hands", "💎", "Bought, held, and didn't flinch."),
        lambda s: s["bluechip_weight"] * (1 - s["defi_ratio"]),
    ),
    (
        Persona("Stable Captain", "🛡️", "Steady as she goes — most of the stack is in stables."),
        lambda s: s["stable_weight"],
    ),
    (
        Persona("Multichain Nomad", "🌐", "No single home — wherever the opportunity is."),
        lambda s: max(0.0, (s["n_chains"] - 2) / 4),
    ),
    (
        Persona("Degen", "🎲", "Small caps, big dreams, zero chill."),
        lambda s: s["smallcap_weight"] * min(s["n_tokens"], 8) / 8,
    ),
    (
        Persona("Diversified Trader", "🧺", "Never all the eggs in one basket."),
        # Spread out and holding spot — a DeFi-dominant book reads as a farmer.
        lambda s: (1 - s["top_weight"]) * min(s["n_assets"], 10) / 10 * (1 - s["defi_ratio"]),
    ),
]

_GHOST = Persona("Ghost Wallet", "👻", "Nothing on-chain here… yet.")
_CURIOUS = Persona("Crypto Curious", "🌱", "Just getting started — small stack, big future.")


def pick_persona(signals: Dict[str, float]) -> Persona:
    """Choose the best-fitting persona for a signal bundle."""
    if signals.get("net_worth", 0) <= 0:
        return _GHOST

    best: Optional[Persona] = None
    best_score = -1.0
    for persona, scorer in _PERSONAS:
        score = max(0.0, float(scorer(signals)))
        if score > best_score:
            best_score = score
            best = Persona(persona.name, persona.emoji, persona.tagline, round(score, 3))

    # Weak signal everywhere + a tiny portfolio → "Crypto Curious".
    if best is None or (best_score < 0.15 and signals.get("net_worth", 0) < 2_000):
        return _CURIOUS
    return best


# --- narration -------------------------------------------------------------


def _fun_facts(
    *,
    net_worth: float,
    chains: set,
    n_tokens: int,
    defi_ratio: float,
    n_protocols: int,
    combined: List[Asset],
    top_protocols: List[Protocol],
) -> List[str]:
    facts: List[str] = []
    if n_tokens or chains:
        facts.append(
            f"Spread across {len(chains)} chain{'s' if len(chains) != 1 else ''} "
            f"and {n_tokens} token{'s' if n_tokens != 1 else ''}."
        )
    if combined and net_worth > 0:
        top = combined[0]
        facts.append(
            f"Biggest bag: {top.label} at {top.value_usd / net_worth * 100:.0f}% of the portfolio."
        )
    if defi_ratio > 0:
        facts.append(
            f"{defi_ratio * 100:.0f}% of the stack is working in DeFi "
            f"across {n_protocols} protocol{'s' if n_protocols != 1 else ''}."
        )
    if top_protocols:
        p = top_protocols[0]
        facts.append(f"Top protocol: {p.name} holding {_money(p.value_usd)}.")
    return facts


# --- formatting helpers (shared by both renderers) -------------------------


def _money(value: float) -> str:
    """Compact USD: $1.23M / $4.5K / $123.45."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.1f}K"
    return f"{sign}${value:,.2f}"


# Public alias — handy for renderers and tests.
money = _money
