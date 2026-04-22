#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  # Market BUY
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

  # Stop-Market BUY (bonus order type)
  python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

  # List open orders
  python cli.py orders --symbol BTCUSDT

  # Cancel an order
  python cli.py cancel --symbol BTCUSDT --order-id 123456789

  # Account / balance info
  python cli.py account
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logger
from bot.orders import place_order

# Load .env if present
load_dotenv()

logger = setup_logger("trading_bot")

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║      🚀  Binance Futures Testnet — Trading Bot           ║
║         USDT-M Perpetuals  |  Python 3.x                 ║
╚══════════════════════════════════════════════════════════╝
"""


# ---------------------------------------------------------------------------
# CLI builder
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place and manage orders on Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Optional overrides for API credentials (env vars used by default)
    parser.add_argument("--api-key", default=None, help="Binance Testnet API key (overrides env var)")
    parser.add_argument("--api-secret", default=None, help="Binance Testnet API secret (overrides env var)")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # --- place ---
    p_place = sub.add_parser("place", help="Place a new order")
    p_place.add_argument("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
    p_place.add_argument("--side",       required=True,  choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    p_place.add_argument("--type",       required=True,  dest="order_type",
                         choices=["MARKET", "LIMIT", "STOP_MARKET",
                                  "market", "limit", "stop_market"],
                         help="Order type: MARKET | LIMIT | STOP_MARKET")
    p_place.add_argument("--quantity",   required=True,  type=float, help="Quantity in base asset")
    p_place.add_argument("--price",      default=None,   type=float, help="Limit price (required for LIMIT orders)")
    p_place.add_argument("--stop-price", default=None,   type=float, dest="stop_price",
                         help="Stop trigger price (required for STOP_MARKET orders)")

    # --- orders ---
    p_orders = sub.add_parser("orders", help="List open orders")
    p_orders.add_argument("--symbol", default=None, help="Filter by symbol (optional)")

    # --- cancel ---
    p_cancel = sub.add_parser("cancel", help="Cancel an open order")
    p_cancel.add_argument("--symbol",   required=True, help="Symbol of the order")
    p_cancel.add_argument("--order-id", required=True, type=int, dest="order_id", help="orderId to cancel")

    # --- account ---
    sub.add_parser("account", help="Display account / balance info")

    # --- ping ---
    sub.add_parser("ping", help="Check API connectivity (server time)")

    return parser


# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def get_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve API key and secret from CLI args or environment variables."""
    api_key = args.api_key or os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            "\n  ❌  Missing API credentials.\n"
            "  Set environment variables BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET,\n"
            "  or pass --api-key / --api-secret on the command line.\n"
        )
        sys.exit(1)

    return api_key, api_secret


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_place(client: BinanceFuturesClient, args: argparse.Namespace) -> None:
    place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
    )


def cmd_orders(client: BinanceFuturesClient, args: argparse.Namespace) -> None:
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except (BinanceClientError, NetworkError) as exc:
        logger.error("Failed to fetch open orders: %s", exc)
        print(f"\n  ❌  Error: {exc}\n")
        return

    if not orders:
        print(f"\n  ℹ️   No open orders{' for ' + args.symbol if args.symbol else ''}.\n")
        return

    print(f"\n  📂  Open Orders ({len(orders)} found)\n")
    print(f"  {'orderId':<15} {'symbol':<12} {'side':<6} {'type':<14} {'qty':<10} {'price':<12} status")
    print("  " + "─" * 74)
    for o in orders:
        print(
            f"  {o.get('orderId', ''):<15} {o.get('symbol', ''):<12} "
            f"{o.get('side', ''):<6} {o.get('type', ''):<14} "
            f"{o.get('origQty', ''):<10} {o.get('price', ''):<12} "
            f"{o.get('status', '')}"
        )
    print()


def cmd_cancel(client: BinanceFuturesClient, args: argparse.Namespace) -> None:
    try:
        response = client.cancel_order(symbol=args.symbol, order_id=args.order_id)
    except (BinanceClientError, NetworkError) as exc:
        logger.error("Cancel failed: %s", exc)
        print(f"\n  ❌  Error: {exc}\n")
        return

    print(
        f"\n  ✅  Order cancelled — orderId={response.get('orderId')}  "
        f"status={response.get('status')}\n"
    )


def cmd_account(client: BinanceFuturesClient, _args: argparse.Namespace) -> None:
    try:
        info = client.get_account_info()
    except (BinanceClientError, NetworkError) as exc:
        logger.error("Account fetch failed: %s", exc)
        print(f"\n  ❌  Error: {exc}\n")
        return

    print("\n  💼  ACCOUNT INFO")
    print("  " + "─" * 40)
    print(f"  Can Trade    : {info.get('canTrade', 'N/A')}")
    print(f"  Total Wallet : {info.get('totalWalletBalance', 'N/A')} USDT")
    print(f"  Avail Margin : {info.get('availableBalance', 'N/A')} USDT")
    print(f"  Total PnL    : {info.get('totalUnrealizedProfit', 'N/A')} USDT")

    assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if assets:
        print(f"\n  Non-zero balances:")
        for a in assets:
            print(f"    {a['asset']}: {a['walletBalance']}")
    print()


def cmd_ping(client: BinanceFuturesClient, _args: argparse.Namespace) -> None:
    try:
        ts = client.get_server_time()
    except (BinanceClientError, NetworkError) as exc:
        logger.error("Ping failed: %s", exc)
        print(f"\n  ❌  Connection failed: {exc}\n")
        return
    print(f"\n  🟢  API reachable — server time: {ts} ms\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "place": cmd_place,
    "orders": cmd_orders,
    "cancel": cmd_cancel,
    "account": cmd_account,
    "ping": cmd_ping,
}


def main() -> None:
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args()

    api_key, api_secret = get_credentials(args)

    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        print(f"\n  ❌  Client setup error: {exc}\n")
        sys.exit(1)

    handler = COMMAND_MAP.get(args.command)
    if handler:
        handler(client, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
