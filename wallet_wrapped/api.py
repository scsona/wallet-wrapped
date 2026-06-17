"""Thin, dependency-light client for the CoinStats Crypto API.

Docs & free API key: https://api.coinstats.app/
Base URL: https://openapiv1.coinstats.app
Auth: send your key in the ``X-API-KEY`` header.

This module only wraps the two endpoints wallet-wrapped is built on:

  * ``GET /wallet/balance`` — token balances for an address
    https://coinstats.app/api-docs/openapi/get-wallet-balance/
  * ``GET /wallet/defi`` — DeFi positions for an address
    https://coinstats.app/api-docs/openapi/get-wallet-defi/
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

BASE_URL = "https://openapiv1.coinstats.app"


class CoinStatsError(RuntimeError):
    """Raised when the CoinStats API returns a non-2xx response."""

    def __init__(self, status: int, message: str, path: str = ""):
        self.status = status
        self.message = message
        self.path = path
        super().__init__(f"CoinStats API error {status} on {path}: {message}")


class CoinStatsClient:
    """Minimal CoinStats Open API client built on the standard library.

    Parameters
    ----------
    api_key:
        Your CoinStats API key. Falls back to the ``COINSTATS_API_KEY``
        environment variable. Grab a free key at https://api.coinstats.app/
    timeout:
        Per-request timeout in seconds.
    max_retries:
        How many times to retry on transient errors (429 / 5xx).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 20.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.environ.get("COINSTATS_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set COINSTATS_API_KEY or pass api_key=... "
                "Get a free key at https://api.coinstats.app/"
            )
        self.timeout = timeout
        self.max_retries = max_retries

    # -- low level ---------------------------------------------------------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query = ""
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            query = "?" + urllib.parse.urlencode(clean)
        url = f"{BASE_URL}{path}{query}"

        request = urllib.request.Request(url, method="GET")
        request.add_header("X-API-KEY", self.api_key)
        request.add_header("Accept", "application/json")
        request.add_header(
            "User-Agent",
            "wallet-wrapped/1.0 (+https://github.com/scsona/wallet-wrapped)",
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else None
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                message = body
                try:
                    message = json.loads(body).get("message", body)
                except (ValueError, AttributeError):
                    pass
                # Retry only on rate limiting / server hiccups.
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    last_error = exc
                    continue
                raise CoinStatsError(exc.code, str(message), path) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    last_error = exc
                    continue
                raise CoinStatsError(0, str(exc), path) from exc

        raise CoinStatsError(0, str(last_error), path)  # pragma: no cover

    # -- endpoints ---------------------------------------------------------

    def get_wallet_balance(
        self,
        address: str,
        blockchain: str = "all",
        connection_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Token balances for ``address``. Wraps ``GET /wallet/balance``.

        Either ``blockchain`` (a chain id, comma-separated list, or ``"all"``)
        or ``connection_id`` must be set; ``connection_id`` wins if both are
        given. Returns a flat list of token dicts with at least ``amount``,
        ``price``, ``symbol`` and ``chain``. We tolerate both a bare-list and a
        ``{"result": [...]}`` response shape.
        """
        params: Dict[str, Any] = {"address": address}
        if connection_id:
            params["connectionId"] = connection_id
        else:
            params["blockchain"] = blockchain
        data = self._get("/wallet/balance", params)
        if isinstance(data, dict):
            return data.get("result") or data.get("balances") or []
        if isinstance(data, list):
            return data
        return []

    def get_wallet_defi(
        self,
        address: str,
        blockchain: str = "all",
        connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """DeFi positions for ``address``. Wraps ``GET /wallet/defi``.

        Returns the raw object ``{"totalAssets": {...}, "protocols": [...]}``.
        Normalises a ``{"result": {...}}`` wrapper if the API adds one.
        """
        params: Dict[str, Any] = {"address": address}
        if connection_id:
            params["connectionId"] = connection_id
        else:
            params["blockchain"] = blockchain
        data = self._get("/wallet/defi", params)
        if isinstance(data, dict):
            if "protocols" in data or "totalAssets" in data:
                return data
            result = data.get("result")
            if isinstance(result, dict):
                return result
        return {"totalAssets": {}, "protocols": []}
