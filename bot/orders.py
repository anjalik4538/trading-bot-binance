"""
Order placement and display logic.
Sits between the CLI layer and the raw Binance client.
"""

from __future__ import annotations

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logger
from bot.validators import validate_all

logger = setup_logger("trading_bot")


def _print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _print_order_summary(params: dict) -> None:
    """Pretty-print the order request before submission."""
    _print_separator()
    print("  📋  ORDER REQUEST SUMMARY")
    _print_separator()
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"  Stop Price : {params['stop_price']}")
    _print_separator()


def _print_order_response(response: dict) -> None:
    """Pretty-print key fields from the Binance order response."""
    _print_separator()
    print("  ✅  ORDER RESPONSE")
    _print_separator()
    print(f"  Order ID      : {response.get('orderId', 'N/A')}")
    print(f"  Client Order  : {response.get('clientOrderId', 'N/A')}")
    print(f"  Symbol        : {response.get('symbol', 'N/A')}")
    print(f"  Side          : {response.get('side', 'N/A')}")
    print(f"  Type          : {response.get('type', 'N/A')}")
    print(f"  Status        : {response.get('status', 'N/A')}")
    print(f"  Orig Qty      : {response.get('origQty', 'N/A')}")
    print(f"  Executed Qty  : {response.get('executedQty', 'N/A')}")

    avg_price = response.get("avgPrice") or response.get("price", "N/A")
    print(f"  Avg Price     : {avg_price}")

    if response.get("stopPrice"):
        print(f"  Stop Price    : {response.get('stopPrice')}")

    print(f"  Time In Force : {response.get('timeInForce', 'N/A')}")
    print(f"  Update Time   : {response.get('updateTime', 'N/A')}")
    _print_separator()


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
    stop_price: float | str | None = None,
) -> dict | None:
    """
    Validate inputs, submit an order, and print results.

    Args:
        client:     Authenticated BinanceFuturesClient instance.
        symbol:     Trading pair (e.g. "BTCUSDT").
        side:       "BUY" or "SELL".
        order_type: "MARKET", "LIMIT", or "STOP_MARKET".
        quantity:   Order size in base asset.
        price:      Limit price (LIMIT orders only).
        stop_price: Trigger price (STOP_MARKET orders only).

    Returns:
        Order response dict on success, None on failure.
    """
    # --- Validate ---
    try:
        params = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n  ❌  VALIDATION ERROR: {exc}\n")
        return None

    _print_order_summary(params)

    # --- Submit ---
    try:
        response = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
    except BinanceClientError as exc:
        logger.error("Order failed — %s", exc)
        print(f"\n  ❌  ORDER FAILED (API Error {exc.code}): {exc.message}\n")
        return None
    except NetworkError as exc:
        logger.error("Network error — %s", exc)
        print(f"\n  ❌  NETWORK ERROR: {exc}\n")
        return None

    # --- Display ---
    _print_order_response(response)
    order_id = response.get('orderId') or response.get('algoId', 'N/A')
    print(f"  🎉  Order submitted successfully! (orderId: {order_id})\n")
    return response
