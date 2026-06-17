"""Tests for the CoinStats client — response normalisation, no network."""

import pytest

from wallet_wrapped.api import CoinStatsClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COINSTATS_API_KEY", "test-key")
    return CoinStatsClient()


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("COINSTATS_API_KEY", raising=False)
    with pytest.raises(ValueError):
        CoinStatsClient()


def test_balance_accepts_bare_list(client, monkeypatch):
    sentinel = [{"symbol": "ETH", "amount": 1, "price": 3000}]
    monkeypatch.setattr(client, "_get", lambda path, params=None: sentinel)
    assert client.get_wallet_balance("0xabc") == sentinel


def test_balance_unwraps_result_dict(client, monkeypatch):
    rows = [{"symbol": "ETH"}]
    monkeypatch.setattr(client, "_get", lambda path, params=None: {"result": rows})
    assert client.get_wallet_balance("0xabc") == rows


def test_balance_connection_id_takes_precedence(client, monkeypatch):
    seen = {}

    def fake_get(path, params=None):
        seen.update(params or {})
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    client.get_wallet_balance("0xabc", blockchain="all", connection_id="ethereum")
    assert seen.get("connectionId") == "ethereum"
    assert "blockchain" not in seen


def test_defi_passthrough(client, monkeypatch):
    payload = {"totalAssets": {"USD": 5}, "protocols": [{"name": "Aave"}]}
    monkeypatch.setattr(client, "_get", lambda path, params=None: payload)
    assert client.get_wallet_defi("0xabc") == payload


def test_defi_unwraps_result(client, monkeypatch):
    inner = {"totalAssets": {"USD": 5}, "protocols": []}
    monkeypatch.setattr(client, "_get", lambda path, params=None: {"result": inner})
    assert client.get_wallet_defi("0xabc") == inner


def test_defi_handles_garbage(client, monkeypatch):
    monkeypatch.setattr(client, "_get", lambda path, params=None: None)
    assert client.get_wallet_defi("0xabc") == {"totalAssets": {}, "protocols": []}
