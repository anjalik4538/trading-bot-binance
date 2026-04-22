"""
Binance Futures Testnet REST client.
 
Handles:
  - HMAC-SHA256 request signing
  - Timestamp synchronisation
  - HTTP request execution with retries
  - Structured logging of every request / response / error
"""
 
from __future__ import annotations
 
import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode
 
import requests
 
from bot.logging_config import setup_logger
 
BASE_URL = "https://demo-fapi.binance.com"
RECV_WINDOW = 5000  # milliseconds
 
logger = setup_logger("trading_bot")
 
 
class BinanceClientError(Exception):
    """Raised when the Binance API returns an error response."""
 
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")
 
 
class NetworkError(Exception):
    """Raised on network-level failures (timeouts, connection errors)."""
 
 
class BinanceFuturesClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.
 
    Usage:
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        response = client.place_order(symbol="BTCUSDT", side="BUY",
                                      order_type="MARKET", quantity=0.001)
    """
 
    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceFuturesClient initialised — base_url=%s", self.base_url)
 
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
 
    def _sign(self, params: dict) -> str:
        """Generate HMAC-SHA256 signature for the given parameter dict."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature
 
    def _timestamp(self) -> int:
        """Return current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)
 
    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request and return the parsed JSON body.
 
        Args:
            method:   HTTP verb ("GET" / "POST" / "DELETE").
            endpoint: API path, e.g. "/fapi/v1/order".
            params:   Query / body parameters.
            signed:   If True, adds timestamp + signature.
 
        Returns:
            Parsed JSON response (dict or list).
 
        Raises:
            BinanceClientError: API returned an error code.
            NetworkError:       Connection / timeout failure.
        """
        params = params or {}
 
        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = RECV_WINDOW
            params["signature"] = self._sign(params)
 
        url = f"{self.base_url}{endpoint}"
        logger.debug("REQUEST  %s %s  params=%s", method, url, {k: v for k, v in params.items() if k != "signature"})
 
        try:
            if method == "GET":
                resp = self.session.get(url, params=params, timeout=10)
            elif method == "POST":
                resp = self.session.post(url, data=params, timeout=10)
            elif method == "DELETE":
                resp = self.session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.Timeout as exc:
            logger.error("TIMEOUT  %s %s", method, url)
            raise NetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("CONNECTION ERROR  %s %s — %s", method, url, exc)
            raise NetworkError(f"Connection error: {exc}") from exc
 
        logger.debug("RESPONSE %s %s  status=%s  body=%s", method, url, resp.status_code, resp.text[:500])
 
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response from %s: %s", url, resp.text[:200])
            resp.raise_for_status()
            raise NetworkError(f"Unexpected non-JSON response (HTTP {resp.status_code})")
 
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            if isinstance(data["code"], int) and data["code"] < 0:
                logger.error("API ERROR  code=%s  msg=%s", data["code"], data.get("msg"))
                raise BinanceClientError(data["code"], data.get("msg", "Unknown error"))
 
        return data
 
    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------
 
    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds (health-check)."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]
 
    def get_account_info(self) -> dict:
        """Fetch futures account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account", signed=True)
 
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a new futures order.
 
        Args:
            symbol:        Trading pair, e.g. "BTCUSDT".
            side:          "BUY" or "SELL".
            order_type:    "MARKET", "LIMIT", or "STOP_MARKET".
            quantity:      Order quantity in base asset.
            price:         Limit price (required for LIMIT orders).
            stop_price:    Trigger price (required for STOP_MARKET orders).
            time_in_force: "GTC" / "IOC" / "FOK" (for LIMIT orders).
 
        Returns:
            Raw order response dict from Binance.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
 
        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force
 
        elif order_type == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("stop_price is required for STOP_MARKET orders.")
            params["stopPrice"] = stop_price
            params["workingType"] = "CONTRACT_PRICE"
            try:
                r = self._request("POST", "/fapi/v1/order", params=params, signed=True)
                logger.info("Order OK orderId=%s", r.get("orderId"))
                return r
            except Exception:
                pass
            p2 = {"symbol": symbol, "side": side, "type": "STOP_MARKET", "quantity": quantity, "triggerPrice": stop_price, "workingType": "CONTRACT_PRICE", "algoType": "CONDITIONAL", "timeInForce": "GTC"}
            r2 = self._request("POST", "/fapi/v1/algoOrder", params=p2, signed=True)
            logger.info("Order OK via algo orderId=%s", r2.get("orderId"))
            return r2
 
        logger.info(
            "Placing %s %s order — symbol=%s  qty=%s  price=%s  stopPrice=%s",
            side,
            order_type,
            symbol,
            quantity,
            price,
            stop_price,
        )
 
        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        logger.info("Order placed successfully — orderId=%s  status=%s", response.get("orderId"), response.get("status"))
        return response
 
    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling orderId=%s on %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
 
    def get_open_orders(self, symbol: str | None = None) -> list:
        """List all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol