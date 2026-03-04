from typing import Optional
from pydantic import (
    BaseModel, PositiveInt, NonNegativeInt, PositiveFloat, ValidationError, Field
)

NEAR_END = 'near_end'   # near end strategy
FAR_END = 'far_end'     # far end strategy
NEAREST_END = 'nearest_end'     # nearest end strategy

class SideStrategy(BaseModel):
    """
    Strategy on single side
    Side: BUY, SELL
    """
    amount: float               # max amount for this level
    base_margin: float          # Margin for follow pricing
    base_type: str = "BPS"      # Base margine type, "BPS" or "STEP"
    level_margin: float         # Margin for order pricing
    level_type: str = "BPS"     # Level margin type, "BPS" or "STEP"
    size: float = Field(alias="quantity")               # Order numbers 5,10,20,35,50
    step_size: float            # Step, eg. 1e-05
    time_in_force: str = "GTX"  # TimeInForce or orders, GTX, GTC, IOC, FOK
    total_amount: float         # Total order amount in this level

class LevelStrategy(BaseModel):
    """
    Strategy on single level
    level: NEAREST_END, NEAR_END, FAR_END
    """
    order_frequency: PositiveInt                # time interval for makeing order, ms
    strategy_type: str = "manual"               
    side: str = ""                              # BUY, SELL, BOTH
    side_buy: Optional[SideStrategy] = None     # strategy for buying, may be None
    side_sell: Optional[SideStrategy] = None    # strategy for selling, may be None

class FollowMakerStrategy(BaseModel):
    """
    Making strategy   
    """
    api_key: str = ""                       # Accounnt api key for making orders
    api_secret: str = ""                    # Accounnt api secret for making orders
    passphrase: str = ""                    # Accounnt passwords, some exchange needs
    exchange: int = 0                       # Exchange ID for making orders
    follow_exchange: int = 0                # Exchange ID for price following
    follow_frequency: int                   # Price following interval, s
    follow_price: float                     # Pivot price
    follow_symbol: str = ""                 # Following symbol name
    follow_symbol_address: str = ""         # Following address
    follow_downside_beta: float             # Downside beta for pricing
    follow_upside_beta: float               # Upside beta for pricing
    ipo_price: float                        # Set pivot price to this value in the 1st pivot loop
    maker_type: str = "PIVOT"               # Making strategy: EXACT, PIVOT, TRADE, FIXED
    name: str = "follow_maker"
    price_decimals: NonNegativeInt = 0      # symbol price precision
    qty_decimals: NonNegativeInt = 0        # Symbol quantigy precision
    price_factor: NonNegativeInt = 0        # 0 / 1
    price_range: PositiveFloat              # Price fluctuation range
    start_time: str                         # Start tim in datatime format
    strategy_id: NonNegativeInt
    symbol: str                             # Symbol name, eg btc_usdt | BTC_USDT | BTC-USDT | BTC-USDT
    symbol_address: str = ""                # Symbol address
    term_id: int = 0                        # project_id
    term_type: str = "SPOT"                 # SPOT / FUTURE
    version: PositiveInt
    far_end: Optional[LevelStrategy] = None       # Strategy for far-end
    near_end: Optional[LevelStrategy] = None      # Strategy for near-end
    nearest_end: Optional[LevelStrategy] = None   # Strategy for nearest-end
    prev_maker_type: str = ""               # maker_type of previous strategy
    start_ts: float = 0.0                   # start time in seconds
    price_baseline: Optional[float] = None        # pviot base price during running
    minute_price_baseline: Optional[dict] = None  # pviot | trade base price in previous minute during running
    prev_pivot: Optional[float] = None            # previous pviot price during running
    prev_fl_price: Optional[float] = None         # previous follow price during running
    contract_size: float = 0.1              
    leverage: float = 2                     

