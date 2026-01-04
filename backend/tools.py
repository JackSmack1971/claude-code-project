"""
Agent tools including CCXT trading capabilities.
Implements proper exchange initialization and precision handling.
"""
from typing import Optional, Any
from pydantic import BaseModel
import ccxt
from database import settings


class TradingContext(BaseModel):
    """Context for trading operations. Passed via RunContext deps."""
    exchange_id: str = "binance"
    api_key: Optional[str] = None
    secret: Optional[str] = None
    testnet: bool = True


def get_exchange(ctx: TradingContext) -> ccxt.Exchange:
    """
    Initialize CCXT exchange with proper configuration.

    CRITICAL: enableRateLimit must be True to avoid IP bans.
    Exchange must call load_markets() before any operations.

    Args:
        ctx: Trading context with API credentials

    Returns:
        Configured exchange instance
    """
    exchange_class = getattr(ccxt, ctx.exchange_id)

    config = {
        'enableRateLimit': True,  # CRITICAL: Prevent rate limit errors
        'options': {
            'defaultType': 'future' if ctx.testnet else 'spot',
        }
    }

    if ctx.api_key and ctx.secret:
        config['apiKey'] = ctx.api_key
        config['secret'] = ctx.secret

    if ctx.testnet:
        config['options']['testnet'] = True

    exchange = exchange_class(config)
    return exchange


async def get_market_price(
    symbol: str,
    exchange: ccxt.Exchange
) -> dict[str, Any]:
    """
    Fetch current market price for a symbol.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        exchange: CCXT exchange instance

    Returns:
        Dict with bid, ask, and last price
    """
    # Ensure markets are loaded
    if not exchange.markets:
        await exchange.load_markets()

    ticker = await exchange.fetch_ticker(symbol)
    return {
        "symbol": symbol,
        "bid": ticker['bid'],
        "ask": ticker['ask'],
        "last": ticker['last'],
        "timestamp": ticker['timestamp']
    }


async def create_limit_order(
    symbol: str,
    side: str,
    amount: float,
    price: float,
    exchange: ccxt.Exchange
) -> dict[str, Any]:
    """
    Create a limit order with proper precision handling.

    CRITICAL: Must use amount_to_precision() and price_to_precision()
    to ensure orders meet exchange requirements.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        side: 'buy' or 'sell'
        amount: Order quantity
        price: Limit price
        exchange: CCXT exchange instance

    Returns:
        Order details
    """
    # Ensure markets are loaded
    if not exchange.markets:
        await exchange.load_markets()

    # Apply precision requirements
    precise_amount = exchange.amount_to_precision(symbol, amount)
    precise_price = exchange.price_to_precision(symbol, price)

    order = await exchange.create_limit_order(
        symbol=symbol,
        side=side,
        amount=float(precise_amount),
        price=float(precise_price)
    )

    return {
        "id": order['id'],
        "symbol": order['symbol'],
        "side": order['side'],
        "type": order['type'],
        "amount": order['amount'],
        "price": order['price'],
        "status": order['status'],
        "timestamp": order['timestamp']
    }


async def get_account_balance(exchange: ccxt.Exchange) -> dict[str, Any]:
    """
    Fetch account balance.

    Args:
        exchange: CCXT exchange instance

    Returns:
        Account balance details
    """
    balance = await exchange.fetch_balance()
    return {
        "total": balance['total'],
        "free": balance['free'],
        "used": balance['used']
    }


# Tool descriptions for Pydantic AI
TRADING_TOOLS = {
    "get_market_price": {
        "description": "Get current market price for a trading pair",
        "parameters": {
            "symbol": "Trading pair (e.g., 'BTC/USDT')"
        }
    },
    "create_limit_order": {
        "description": "Create a limit buy or sell order",
        "parameters": {
            "symbol": "Trading pair (e.g., 'BTC/USDT')",
            "side": "Order side: 'buy' or 'sell'",
            "amount": "Quantity to trade",
            "price": "Limit price"
        }
    },
    "get_account_balance": {
        "description": "Get account balance across all assets",
        "parameters": {}
    }
}
