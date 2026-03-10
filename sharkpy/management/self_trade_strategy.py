from pydantic import (
    BaseModel, PositiveInt, PositiveFloat, NonNegativeInt, NonNegativeFloat
)
from typing import Optional

class SelftradeStrategy(BaseModel):
    api_key: str                   # Api key for making account
    api_secret: str                # Api secret for making account
    passphrase: str = ""
    buy_order_rate: NonNegativeInt      # Ratio of 
    exchange: NonNegativeInt            # Exchange ID for trading
    large_amount: PositiveFloat         # Hudge trading amount
    large_float_range: PositiveFloat    # Hudge trading floating range
    large_frequency: NonNegativeFloat   # Hudge trading frequence, second.
    middle_amount: PositiveFloat        # Medium trading amount
    middle_float_range: PositiveFloat   # Medium trading floating range.
    middle_frequency: NonNegativeFloat  # Medium trading frequence，seconds
    small_amount: PositiveFloat         # Small trading acount.
    small_float_range: PositiveFloat    # Small trading floating range.
    small_frequency: NonNegativeFloat   # Small trading frequence，seconds
    name: str = "self_trade"
    prevention_rate: PositiveFloat      # Limit price changing rate: 1%
    price_decimals: PositiveInt         # Price predision
    qty_decimals: PositiveInt           # Quantigy predision
    start_time: str = ""                # Trading start time in timedate format. eg.'2025-10-18 00:00:00'
    strategy_id: str = ""
    symbol: str                     # Cryptocurrency pair. eg. btc_usdt, BTC_USDT...
    symbol_address: str = ""        # Crypto address
    term_id: PositiveInt            # Project_id to identify wich project the strategy belongs to
    term_type: str = "SPOT"         # SPOT | FUTURE
    trade_type: str = ""            # MOCK or ""
    version: NonNegativeInt
    start_ts: Optional[float] = None    # Trading start time in second.
    prev_price: NonNegativeFloat = 0    # Previous price.

class Context:
    def __init__(self, minute: int, prev_price: float) -> None:
        self.minute = 0
        self.prev_price = 0