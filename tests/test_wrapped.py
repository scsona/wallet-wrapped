"""Tests for the analysis engine."""

import pytest

from wallet_wrapped.sample_data import SAMPLE_BALANCE, SAMPLE_DEFI
from wallet_wrapped.wrapped import (
    build_wrapped,
    money,
    pick_persona,
)

ADDR = "0x94845333028B1204Fbe14E1278Fd4Adde46B22ce"


@pytest.fixture
def demo():
    return build_wrapped(ADDR, SAMPLE_BALANCE, SAMPLE_DEFI)


def test_net_worth_is_liquid_plus_defi(demo):
    # 0.8*64000 + 12.5*3400 + 25000 + 8000*1.1 + 3000*2.4 + 5000*0.7 = 138200 liquid
    assert demo.liquid_value == pytest.approx(138200.0)
    assert demo.defi_value == pytest.approx(139000.0)
    assert demo.net_worth == pytest.approx(277200.0)
    assert demo.defi_ratio == pytest.approx(139000.0 / 277200.0)


def test_counts_and_chains(demo):
    assert demo.n_tokens == 6
    assert demo.n_protocols == 4
    # ethereum, arbitrum, optimism, polygon
    assert demo.n_chains == 4
    assert set(demo.chains) == {"ethereum", "arbitrum", "optimism", "polygon"}


def test_allocation_weights_sum_to_100(demo):
    total = sum(a.pct for a in demo.allocation)
    assert total == pytest.approx(100.0, abs=0.5)
    # the bar collapses the tail into a single "Other" slice
    assert demo.allocation[-1].label == "Other"


def test_top_tokens_sorted_desc(demo):
    values = [t.value_usd for t in demo.top_tokens]
    assert values == sorted(values, reverse=True)
    assert demo.top_tokens[0].label == "WBTC"  # 0.8 * 64000 = 51200, the biggest token


def test_diversification_in_range(demo):
    assert 0 <= demo.diversification <= 100
    # a spread-out, multi-asset book should not look concentrated
    assert demo.diversification >= 60


def test_demo_persona_is_yield_farmer(demo):
    # ~50% in DeFi across 4 protocols beats the other archetypes.
    assert demo.persona.name == "Yield Farmer"


def test_empty_wallet_is_ghost():
    w = build_wrapped(ADDR, [], {"totalAssets": {}, "protocols": []})
    assert w.net_worth == 0
    assert w.persona.name == "Ghost Wallet"
    assert w.diversification == 0
    assert w.allocation == []


def test_stable_heavy_persona():
    balance = [
        {"symbol": "USDC", "chain": "ethereum", "amount": 90000, "price": 1.0},
        {"symbol": "ETH", "chain": "ethereum", "amount": 1, "price": 3000.0},
    ]
    w = build_wrapped(ADDR, balance, None)
    assert w.persona.name == "Stable Captain"


def test_single_bluechip_is_diamond_hands():
    balance = [{"symbol": "ETH", "chain": "ethereum", "amount": 10, "price": 3000.0}]
    w = build_wrapped(ADDR, balance, None)
    # all-in on a blue chip, no DeFi
    assert w.persona.name == "Diamond Hands"
    assert w.diversification == 0  # everything in one asset


def test_pick_persona_ghost_on_zero():
    assert pick_persona({"net_worth": 0}).name == "Ghost Wallet"


def test_zero_value_tokens_are_skipped():
    balance = [
        {"symbol": "SCAM", "chain": "ethereum", "amount": 1000, "price": 0.0},
        {"symbol": "ETH", "chain": "ethereum", "amount": 1, "price": 3000.0},
    ]
    w = build_wrapped(ADDR, balance, None)
    assert w.n_tokens == 1
    assert w.net_worth == pytest.approx(3000.0)


@pytest.mark.parametrize(
    "value,expected",
    [
        (277200.0, "$277.2K"),
        (1_500_000.0, "$1.50M"),
        (2_300_000_000.0, "$2.30B"),
        (42.5, "$42.50"),
        (0.0, "$0.00"),
    ],
)
def test_money_formatting(value, expected):
    assert money(value) == expected


def test_defi_total_falls_back_to_protocol_sum():
    defi = {
        "protocols": [
            {"name": "Aave", "chain": "ethereum", "totalValue": {"USD": 10.0},
             "investments": [{"name": "Lending"}]},
        ]
    }  # no totalAssets
    w = build_wrapped(ADDR, [], defi)
    assert w.defi_value == pytest.approx(10.0)
    assert w.top_protocols[0].kinds == ["Lending"]
