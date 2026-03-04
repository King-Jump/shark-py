""" Self-trade using real orders
"""
import os
import sys
import time
import asyncio
import logging
import random
import traceback
from logging import Logger
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import (
    BaseModel, PositiveInt, PositiveFloat, NonNegativeInt, ValidationError,
    NonNegativeFloat
)

SRV_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCTOPUS_PATH = os.path.join(os.path.dirname(SRV_PATH), 'octopus-py')
sys.path.insert(0, SRV_PATH)
if OCTOPUS_PATH not in sys.path:
    sys.path.insert(0, OCTOPUS_PATH)

from utils.log_util import create_logger
from utils.config_util import load_config
from utils.db_util import set_dict
from octopuspy import NewOrder, OrderID, ORDER_STATE_CONSTANTS
from octopuspy.exchange.helper import get_private_client

BJ_TZ = timezone(timedelta(hours=8))
LOG_NAME = 'SelfTrader'

# price strategy
UNIFORM_RANDOM = 0      # Random price between ask1 and bid1
TOP_ASK_BID_RANDOM = 1  # Ratio: 33% posibility top_ask, 33% posibility top_bid，33% posibility random between 2 prices.

PRICE_STRATEGY = UNIFORM_RANDOM
# Whether the opening price of the next one minute bar to be equal to the closing price of the previous bar
PRICE_CONTINUOUS = True

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



def _price_strategy(top_ask: float, top_bid: float, st_context: Context) -> float:
    if PRICE_STRATEGY == TOP_ASK_BID_RANDOM:
        rand_val = random.choice([0, 1, 2])
        if rand_val == 0:
            price_rand = top_bid
        elif rand_val == 1:
            price_rand = top_ask
        else:
            price_rand = random.uniform(top_bid, top_ask)
    elif PRICE_STRATEGY == UNIFORM_RANDOM:
        price_rand = random.uniform(top_bid, top_ask)

    if PRICE_CONTINUOUS:
        minute = int(time.time() / 60)
        if st_context.minute and minute > st_context.minute:
            st_context.minute = minute
            price_rand = st_context.prev_price
        else:
            st_context.prev_price = price_rand
    return price_rand

def _calc_price_qty(
    client, symbol: str, param: SelftradeStrategy, st_context: Context, scale: str, logger: Logger
) -> tuple[float, float]:
    ask_bid = client.top_askbid(symbol)
    logger.debug('%s Top Ask/Bid: %s', symbol, ask_bid)
    if not ask_bid or not ask_bid[0].ap or not ask_bid[0].bp:
        return 0, 0
    top_ask = float(ask_bid[0].ap)
    top_bid = float(ask_bid[0].bp)
    # Self-trade price: 33% chance to execute at bid price, 33% at ask price, 33% at mid price
    price_rand = _price_strategy(top_ask, top_bid, st_context)

    _previous_strategy = '''
    price_rand = top_ask * rand_val + top_bid * (1 - rand_val)

    prev_ask, prev_bid = param.get('prev_ask_bid', (0, 0))
    if prev_ask and prev_bid:
        if prev_ask >= top_ask and prev_bid >= top_bid:
            # move downwards, price must close to top bid
            rand_val = random.uniform(0.1, 0.2)
            price_rand = top_bid * (1 - rand_val) + mean_price * rand_val
        elif prev_ask <= top_ask and prev_bid <= top_bid:
            # move upwords, price must close to top ask
            rand_val = random.uniform(0.1, 0.2)
            price_rand = top_ask * (1 - rand_val) + mean_price * rand_val
    param['prev_ask_bid'] = (top_ask, top_bid)
    logger.debug('prev_ask=%s, prev_bid=%s, ask=%s, bid=%s, price=%s, rand=%s',
                 prev_ask, prev_bid, top_ask, top_bid, price_rand, rand_val)
    '''

    # control divergence
    if param.prev_price > 0 and \
        abs(price_rand / param.prev_price - 1) > param.prevention_rate * 0.01:
        logger.warning("Abnormal Ticker Volatility %s: pre price=%s, price=%s, limit divergence=%s",
            symbol, param.prev_price, price_rand, 0.01 * param.prevention_rate)
        if price_rand > param.prev_price:
            price_rand = param.prev_price * (1 + 0.01 * param.prevention_rate)
        else:
            price_rand = param.prev_price * (1 - 0.01 * param.prevention_rate)
    param.prev_price = price_rand

    # calculate random trade price and quantity
    if scale == "large":
        amount_rand_range = max(min(0.999999, float(param.large_float_range)), 0.000001)
        qty_rand = float(param.large_amount) * random.uniform(1 - amount_rand_range, 1 + amount_rand_range) / price_rand
    elif scale == "middle":
        amount_rand_range = max(min(0.999999, float(param.middle_float_range)), 0.000001)
        qty_rand = float(param.middle_amount) * random.uniform(1 - amount_rand_range, 1 + amount_rand_range) / price_rand
    else:
        amount_rand_range = max(min(0.999999, float(param.small_float_range)), 0.000001)
        qty_rand = float(param.small_amount) * random.uniform(1 - amount_rand_range, 1 + amount_rand_range) / price_rand
    price = round(price_rand, param.price_decimals)
    qty = round(qty_rand, param.qty_decimals)
    return price, qty

def _mock_trade(
    client, symbol: str, param: SelftradeStrategy, price: float, qty: float, logger: Logger
) -> dict:
    ts = int(time.time() * 1000) % 86400000
    # Exchange take the view of maker，trans it to view of taker.
    side = 'SELL' if random.randrange(0, 100) < float(param.buy_order_rate) else 'BUY'
    is_spot = param.term_type == 'SPOT'

    contract_size = 0.1
    leverage = 2

    if not is_spot:
        _ = {
            'orderSide': 'BUY' if side == 'SELL' else 'SELL',
            'symbol': symbol,
            'price': str(price),
            'origQty': str(int((qty * leverage) / contract_size)),
            'reduceOnly': False,
            'positionSide': 'LONG' if side == 'SELL' else 'SHORT'
        }
    return client.self_trade(symbol, side, price, qty)

def _put_orders(
    client, symbol: str, param: SelftradeStrategy, price: float, qty: float, logger: Logger
) -> list[OrderID]:
    ts = int(time.time() * 1000) % 86400000
    # Exchange take the view of maker，trans it to view of taker.
    side = 'SELL' if random.randrange(0, 100) < float(param.buy_order_rate) else 'BUY'
    is_spot = param.term_type == 'SPOT'
    contract_size = 0.1
    leverage = 2
    orders = [
        NewOrder(
            symbol=symbol,
            client_id=f'M{param.strategy_id}_{ts}',
            side='BUY' if side == 'SELL' else 'SELL',
            type="LIMIT",
            quantity=qty,
            price=price,
            biz_type="SPOT",
            tif='GTX',
            reduce_only=False,
            position_side='',
            bait=False,
            selftrade_enabled=False,
        ) if is_spot else NewOrder(
            symbol=symbol,
            client_id=f'M{param.strategy_id}_{ts}',
            side='BUY' if side == 'SELL' else 'SELL',
            type="LIMIT",
            quantity=str(int((qty * leverage) / contract_size)),
            price=price,
            biz_type="FUTURE",
            tif='GTX',
            reduce_only=False,
            position_side='LONG' if side == 'SELL' else 'SHORT',
            bait=False,
            selftrade_enabled=False,
        ),
        NewOrder(
            symbol=symbol,
            client_id=f'T{param.strategy_id}_{ts}',
            side=side,
            type="LIMIT",
            quantity=qty,
            price=price,
            biz_type="SPOT",
            tif='IOC',
            reduce_only=False,
            position_side='',
            bait=False,
            selftrade_enabled=False,
        ) if is_spot else NewOrder(
            symbol=symbol,
            client_id=f'T{param.strategy_id}_{ts}',
            side=side,
            type="LIMIT",
            quantity=str(int((qty * leverage) / contract_size)),
            price=price,
            biz_type="FUTURE",
            tif='IOC',
            reduce_only=False,
            position_side='SHORT' if side == 'SELL' else 'LONG',
            bait=False,
            selftrade_enabled=False,
        ),
    ]
    logger.debug("selftrade trade 1: %s", orders[0])
    logger.debug("selftrade trade 2: %s", orders[1])
    return client.batch_make_orders(orders)
    
def _check_gtc_order(
    client, sid: str, symbol: str, order_id: str, logger: Logger
) -> bool:
    """ check orders' status and cancel previous orders if status is NEW
    """
    entry_ts = time.time()
    while 1:
        order_status = client.order_status(order_id, symbol)
        if order_status:
            client_order_id = order_status[0].client_id
            if client_order_id and not client_order_id.startswith('M'):
                logger.info("GTC order is already canceled: %s", order_status)
                return True

        logger.debug("%s new order status: %s", symbol, order_status)
        if entry_ts + 3 < time.time():
            # 3s timeout
            break

        if not order_status:
            # wait for updating order status
            time.sleep(0.5)
            continue

        if order_status:
            # update strategy status in redis
            set_dict(f'_amstatus_{sid}', order_status)
            logger.info("Update Redis Strategy Status: %s, %s", symbol, order_status)
            if order_status[0].state in (
                ORDER_STATE_CONSTANTS.NEW, ORDER_STATE_CONSTANTS.PARTIALLY_FILLED):
                res = client.cancel_order(order_id, symbol)
                logger.info("Cancel GTC order: %s, %s", order_id, res)
            return True
    return False

async def self_trade(client, param: SelftradeStrategy, st_context: Context, scale: str):
    """ # 1. get best ask/bid
        # 2. put GTC and FOK order in reverse side
        # 3. checkout order status
    """
    logger = logging.getLogger(LOG_NAME)
    symbol = param.symbol
    # 1. get best ask/bid to calculate price and quantity
    price, qty = _calc_price_qty(client, symbol, param, st_context, scale, logger)
    logger.info('%s price=%s, qty=%s', symbol, price, qty)
    if not price or not qty:
        return

    # 2. put GTC and FOK order in reverse side
    if param.trade_type == 'MOCK':
        make_res = _mock_trade(client, symbol, param, price, qty, logger)
        logger.info('%s mock trade %s', symbol, make_res)
    else:
        make_res = _put_orders(client, symbol, param, price, qty, logger)
        if not make_res:
            logger.error("%s Failed to make orders: %s", symbol, make_res)
            return

        # 3. checkout order status
        new_order_ids = []
        for order in make_res:
            new_order_ids.append(order.order_id)
        logger.info('%s New order ids: %s', symbol, new_order_ids)

        if new_order_ids and \
            not _check_gtc_order(client, param.strategy_id, symbol, new_order_ids[0], logger):
            logger.error("%s checkout make status timeout", symbol)

class SelfTrader:
    """ Self-Trade Agent
    """
    __slots__ = ('config_key', 'config_version', 'logger', '_trade_clients', '_context')
    def __init__(self, config_key: str, logger: Logger):
        self.config_key = config_key
        self.config_version = 0
        self.logger = logger
        self._trade_clients = {}
        self._context = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type:
            self.logger.error(traceback.format_exc())
            self.logger.error(exc_value)
        return True
    
    def unpdate_config(self):
        """
        Update strategy from Redis
        :Return: True-success, False-failed
        """
        try:
            new_version, _configs = load_config(self.config_key, self.config_version)
            new_configs = [SelftradeStrategy(**item) for item in _configs]
        except ValidationError as e:
            self.logger.error("config validation error: %s", e)
            return {}
        strategy_configs = {}
        if new_version > self.config_version:
            self.logger.info("Update Config: %s", new_configs)
            strategy_configs = {conf.strategy_id: conf for conf in new_configs}
            self.config_version = new_version
        return strategy_configs

    def prepare_tasks(self, strategy_configs:dict[str, SelftradeStrategy], _op_ts:dict):
        """
        Prepare trade tasks
        """
        tasks = []
        for sid, strategy in strategy_configs.items():
            ts = time.time()
            exchange = strategy.exchange
            api_key = strategy.api_key
            if api_key not in self._trade_clients:
                self._trade_clients[api_key] = _get_client(
                    exchange, api_key, strategy.api_secret,
                    passphrase=strategy.passphrase,
                    logger=self.logger,
                    category=strategy.term_type)
            client = self._trade_clients[api_key]

            if strategy.start_ts:
                # Do not start trading before starting time.
                if ts < strategy.start_ts:
                    continue
            elif strategy.start_time:
                # Start_time in datatime format. eg. '2025-10-18 00:00:00'
                dt = datetime.strptime(strategy.start_time, '%Y-%m-%d %H:%M:%S')
                strategy.start_ts = dt.replace(tzinfo=BJ_TZ).timestamp()
                continue

            if sid not in self._context:
                self._context[sid] = Context(0, 0.0)

            large_freq = float(strategy.large_frequency)
            if large_freq and _op_ts['large'].get(sid, 0.0) + large_freq < ts:
                tasks.append(asyncio.create_task(
                    self_trade(client, strategy, self._context[sid], 'large')))
                _op_ts['large'][sid] = ts
            middle_freq = float(strategy.middle_frequency)
            if middle_freq and  _op_ts['middle'].get(sid, 0.0) + middle_freq < ts:
                tasks.append(asyncio.create_task(
                    self_trade(client, strategy, self._context[sid], 'middle')))
                _op_ts['middle'][sid] = ts
            small_freq = float(strategy.small_frequency)
            if small_freq and _op_ts['small'].get(sid, 0.0) + small_freq < ts:
                tasks.append(asyncio.create_task(
                    self_trade(client, strategy, self._context[sid], 'small')))
                _op_ts['small'][sid] = ts
        return tasks     
        
        
    async def run_forever(self):
        _op_ts = {'config': 0.0, 'large': {}, 'middle': {}, 'small': {}}
        strategy_configs = {}
        while 1:
            # update config
            ts = time.time()
            if _op_ts['config'] + 5 < ts:
                # 1. load and validate config
                _configs = self.unpdate_config()
                if _configs:
                    strategy_configs = _configs
                _op_ts['config'] = ts
                
            # 2. prepare trade tasks
            tasks = self.prepare_tasks(strategy_configs = strategy_configs,
                                             _op_ts = _op_ts)

            # 3. run tasks
            if tasks:
                await asyncio.gather(*tasks)
            else:
                await asyncio.sleep(0.1)

async def main(config_key: str):
    logger = create_logger(SRV_PATH, f'st_{config_key}.log', LOG_NAME)
    with SelfTrader(config_key, logger) as agent:
        await agent.run_forever()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"python {sys.argv[0]} <config_key>")
        sys.exit(1)

    # _amconf_self_trade
    asyncio.run(main(sys.argv[1]))
