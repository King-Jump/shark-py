""" 
Follow market making strategies, such as market making with USDT and following the rise and fall of another cryptocurrency pair with USDT
The placement strategy can be switched between the following three situations
1. Strictly follow the price of A_USDT, that is, the price of B_USDT remains consistent with A_USDT in real time
2. Manually specify the initial price (IPO price) of B_USDT, but the fluctuation of B_USDT always follows the fluctuation of A_USDT
3. The central price of B_USDT (the middle price of market making orders) is based on the previous transaction price, plus the fluctuation of A_USDT during the same period
"""
import os
import sys
import time
import asyncio
import logging
import traceback
import random
from logging import Logger
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import (
    ValidationError
)

SRV_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRV_PATH not in sys.path:
    sys.path.insert(0, SRV_PATH)

from utils.log_util import create_logger
from utils.config_util import load_config, load_config_str
from utils.db_util import set_dict
from exchange.base_restapi import NewOrder, OrderID, ORDER_STATE_CONSTANTS
from exchange.helper import get_private_client, get_market_client
from sharkpy.liquidity.liquidity import gen_amt_dist
from sharkpy.management.follow_maker_strategy import SideStrategy, LevelStrategy, FollowMakerStrategy, NEAR_END, FAR_END, NEAREST_END

BJ_TZ = timezone(timedelta(hours=8))
LOG_NAME = 'FollowMaker'
    
def _mix(ask_orders: list[NewOrder], bid_orders: list[NewOrder]) -> list[NewOrder]:
    """ Mix orders
    """
    mixed_orders = []
    for ask, bid in zip(ask_orders, bid_orders):
        mixed_orders.append(ask)
        mixed_orders.append(bid)
    if len(ask_orders) > len(bid_orders):
        mixed_orders.extend(ask_orders[len(bid_orders):])
    if len(ask_orders) < len(bid_orders):
        mixed_orders.extend(bid_orders[len(ask_orders):])
    return mixed_orders

def put_new_orders(
    client, param: FollowMakerStrategy, level: str, base_buy_price: float, base_sell_price: float, logger: Logger
) -> list[OrderID]:
    """ Put orders
    """
    # load strategy parameters
    logger.debug("put new orders: strategy [%s], base_buy_price [%s], base_sell_price [%s], level [%s]",
                 param.maker_type, base_buy_price, base_sell_price, level)
    strategy_id = param.strategy_id
    symbol = param.symbol
    price_decimals = param.price_decimals
    qty_decimals = param.qty_decimals
    
    if level == FAR_END:
        level_strategy: LevelStrategy = param.far_end
    elif level == NEAR_END:
        level_strategy: LevelStrategy = param.near_end
    else:
        level_strategy: LevelStrategy = param.nearest_end
    
    # fm strategy may not have all levels
    if not level_strategy:
        logger.info("strategy id [%s] has no strtegy of [%s]", strategy_id, level)
        return []

    side = level_strategy.side # Order placement direction
    # Spot or futures
    is_spot = param.term_type == "SPOT"
    # Contract size
    contract_size = param.contract_size
    # Contract leverage
    leverage = param.leverage

    new_ask_orders, new_bid_orders = [], []
    ts = int(time.time() * 100) % 8640000
    if base_sell_price > 0 and side in ('BOTH', 'SELL'):
        total_amount = 0
        sell_price = base_sell_price
        size = level_strategy.side_buy.size # Order numbers of buy side
        max_acc_amt = level_strategy.side_sell.total_amount # Total amount of sell orders
        max_amt_per_order = float(level_strategy.side_sell.amount) # Amount of sell order
        tif = level_strategy.side_sell.time_in_force # Sell order time in force
        level_spread_type = level_strategy.side_sell.level_type 
        level_spread_margin = level_strategy.side_sell.level_margin
        level_spread_step = level_strategy.side_sell.step_size

        ask_amt_dist = gen_amt_dist(max_amt_per_order, int(size), 'SELL') # Sell amount distribution
        logger.debug("ask_amt_dist at [%s], side [SELL]: %s", level, ask_amt_dist)
        idx = 1
        for level_amt in ask_amt_dist:
            # Making sell orders
            sell_qty = level_amt/sell_price
            sell_qty = round(sell_qty, qty_decimals) if qty_decimals else int(sell_qty)
            if sell_qty > 0:
                price = round(sell_price, price_decimals) if price_decimals else int(sell_price)
                client_id = f'{strategy_id}_U{ts}S{idx}' if level == NEAREST_END else f'{strategy_id}_{level[0]}{ts}S{idx}'
                if is_spot:
                    _quantity = sell_qty
                    order = NewOrder(
                        symbol=symbol,
                        client_id=client_id[-18:],
                        side='SELL',
                        type='LIMIT',
                        quantity=sell_qty,
                        price=str(price),
                        biz_type='SPOT',
                        tif='GTX' if tif == 'BAIT' else tif,
                        reduce_only=False,
                        position_side='',
                        bait=tif == 'BAIT',
                        selftrade_enabled=True,
                    )
                else: # future
                    _quantity = str(int((sell_qty * leverage) / contract_size))
                    order = NewOrder(
                        symbol=symbol,
                        client_id=client_id[-18:],
                        side='SELL',
                        type='LIMIT',
                        quantity=_quantity,
                        price=str(price),
                        biz_type='FUTURE',
                        tif='GTX' if tif == 'BAIT' else tif,
                        reduce_only=False,
                        position_side='SHORT',
                        bait=tif == 'BAIT',
                        selftrade_enabled=True,
                    )
                new_ask_orders.append(order)
                logger.debug("new [SELL] order of size [%s] at price [%s], level_amt [%s]", 
                             _quantity, price, level_amt)
            total_amount += level_amt
            if total_amount >= max_acc_amt:
                break
            # Calculate sell order prices in this level
            sell_price = _calc_price_by_spread('SELL', sell_price,
                level_spread_type, level_spread_margin, level_spread_step)
            idx += 1

    if base_buy_price > 0 and side in ('BOTH', 'BUY'):
        total_amount = 0
        buy_price = base_buy_price
        size = level_strategy.side_buy.size # Buy order numbers
        max_acc_amt = level_strategy.side_buy.total_amount # Total amount of buy orders
        max_amt_per_order = float(level_strategy.side_buy.amount) # Amount for buy order
        tif = level_strategy.side_buy.time_in_force # Buy order time in force
        level_spread_type = level_strategy.side_buy.level_type
        level_spread_margin = level_strategy.side_buy.level_margin
        level_spread_step = level_strategy.side_buy.step_size

        bid_amt_dist = gen_amt_dist(max_amt_per_order, int(size), 'BUY') # Amount distribution of buy orders
        logger.debug("bid_amt_dist at [%s], side [BUY]: %s", level, bid_amt_dist)
        idx = 1
        for level_amt in bid_amt_dist:
            buy_qty = level_amt/buy_price
            buy_qty = round(buy_qty, qty_decimals) if qty_decimals else int(buy_qty)
            price = round(buy_price, price_decimals) if price_decimals else int(buy_price)
            if buy_qty > 0:
                client_id = f'{strategy_id}_U{ts}B{idx}' if level == NEAREST_END else f'{strategy_id}_{level[0]}{ts}B{idx}'
                if is_spot:
                    _quantigy = buy_qty
                    order = NewOrder(
                        symbol=symbol,
                        client_id=client_id[-18:],
                        side='BUY',
                        type='LIMIT',
                        quantity=buy_qty,
                        price=str(price),
                        biz_type='SPOT',
                        tif='GTX' if tif == 'BAIT' else tif,
                        reduce_only=False,
                        position_side='',
                        bait=tif == 'BAIT',
                        selftrade_enabled=True,
                    )
                else: # future
                    _quantigy = str(int((buy_qty * leverage ) / contract_size))
                    order = NewOrder(
                        symbol=symbol,
                        client_id=client_id[-18:],
                        side='BUY',
                        type='LIMIT',
                        quantity=_quantigy,
                        price=str(price),
                        biz_type='FUTURE',
                        tif='GTX' if tif == 'BAIT' else tif,
                        reduce_only=False,
                        position_side='LONG',
                        bait=tif == 'BAIT',
                        selftrade_enabled=True,
                    )
                new_bid_orders.append(order)
                logger.debug("new [BUY] order of size [%s] at price [%s], level_amt [%s]",
                             _quantigy, price, level_amt)
            total_amount += level_amt
            if total_amount >= max_acc_amt:
                break
            # Calculate buy order prices
            buy_price = _calc_price_by_spread('BUY', buy_price,
                level_spread_type, level_spread_margin, level_spread_step)
            idx += 1

    new_orders = _mix(new_ask_orders, new_bid_orders)
    make_res = {}
    
    if new_orders:
        make_res = client.batch_make_orders(new_orders, symbol)
        logger.info("%s %s New orders %s, response: %s", symbol, level, new_orders, make_res)
    return make_res

def check_and_cancel(
    client, symbol: str, order_ids: list, prev_order_ids: list, logger: Logger
) -> bool:
    """ 
    1. Check the status of this round of orders, and if it is NEW, cancel the order
    --In order to improve the efficiency of order placement, giving up checking the order placement status may result in an empty order book
    2. Cancel the previous round of orders
    """
    # 2. Cancel previous orders
    if prev_order_ids:
        res = client.batch_cancel(prev_order_ids, symbol)
        logger.info("%s cancel previous orders: %s", symbol, res)
    return True

def _calc_mirror_pivot(client, strategy: FollowMakerStrategy, fl_price: float, logger: Logger) -> float:
    if not strategy.price_baseline:
        #In case of an accident, reset the price baseline and use the current follow price as the new benchmark price
        strategy.price_baseline = fl_price
        strategy.minute_price_baseline = {
            'minute': int(time.time() / 60),
            'price_minus1': fl_price,
            'price_minus2': fl_price,
            'prev_price': fl_price,
        }
        logger.warning("None price baseline of Pivot Strategy, Try to rebuild: %s", strategy)
        return 0

    #Calculate the fluctuation range of the following symbol between two samples
    # rtn = fl_price / strategy.price_baseline
    rtn = fl_price / strategy.price_baseline - 1
    # update new ticker price of the followed symbol
    strategy.price_baseline = fl_price

    # calculate minutely return
    curr_minute = int(time.time() / 60)
    minute_ctx = strategy.minute_price_baseline
    if curr_minute > minute_ctx['minute']:
        # calculate return by open price of each minute
        minute_ctx['price_minus2'] = minute_ctx['price_minus1']
        minute_ctx['price_minus1'] = minute_ctx['prev_price']
        minute_ctx['minute'] = curr_minute
    minute_ctx['prev_price'] = fl_price

    up_beta, down_beta = strategy.follow_upside_beta, strategy.follow_downside_beta

    if minute_ctx['price_minus1'] >= minute_ctx['price_minus2']:
        rtn *= 1 + up_beta
    else:
        rtn *= 1 + down_beta
    # Prev_pivot is the central price of a market making coin pair
    if not strategy.prev_pivot:
        # Use the latest transaction price as the previous central price. Use IPO price otherwise
        ticker = client.ticker(strategy.symbol)
        if ticker:
            strategy.prev_pivot = float(ticker[0].p)
        else:
            logger.error("Get Ticker %s:%s, %s",
                         strategy.strategy_id, strategy.symbol, ticker)
            strategy.prev_pivot = strategy.ipo_price

    pivot = strategy.prev_pivot * (1 + rtn)
    strategy.prev_pivot = pivot
    return pivot

def _set_monitor_redis(project_id, exchange, symbol, pivot, logger):
    # update new pivot price of each project
    rkey = f'{project_id}{exchange}{symbol}'
    set_dict(rkey, {'pivot': pivot})
    logger.info('Set redis Monitor: %s pivot=%s', rkey, pivot)

def _calc_price_by_spread(
    side: str, price: float, spread_type: str, margin: float, step: float
) -> float:
    if side == 'SELL':
        return price * (1 + margin * 0.0001) if spread_type == 'BPS' else price + margin * step
    return price * (1 - margin * 0.0001) if spread_type == 'BPS' else max(0, price - margin * step)

def get_strategy_open_orders(client, strategy: FollowMakerStrategy, level: str, logger:Logger):
    strategy_id = str(strategy.strategy_id)
    symbol = strategy.symbol
    prev_order_ids = []
    # get open orders of this strategy
    open_orders = client.open_orders(symbol)
    if open_orders:
        if level != NEAREST_END:
            clorder_prefix = f'{strategy_id}_{level[0]}'
        else:
            clorder_prefix = f'{strategy_id}_U'

        total_num, total_amount, total_qty = 0, 0, 0
        for order in open_orders:
            if order.state not in (ORDER_STATE_CONSTANTS.CANCELED,
                ORDER_STATE_CONSTANTS.REJECTED, ORDER_STATE_CONSTANTS.EXPIRED):
                total_num += 1
                qty = float(order.origQty)
                total_qty += qty
                total_amount += float(order.price) * qty
            # Filter out the historical orders of current strategy, and encode the name in the client order ID
            if order.client_id.startswith(clorder_prefix):
                prev_order_ids.append(order.order_id)

        # Update strategy status, save in redis
        value = {
            'total_orders': len(prev_order_ids),
            'new_order_num': total_num,
            'total_amount': total_amount,
            'avg_price': round(total_amount / total_qty, strategy.price_decimals) \
                if strategy.price_decimals else int(total_amount / total_qty),
            'timestamp': int(1000 * time.time()),
        }
        # update strategy status in redis
        set_dict(f'_amstatus_{strategy_id}', value)
        logger.info("Update Redis Strategy Status: %s, %s", strategy_id, value)
    logger.debug("%s %s open orders: %s, %s/%s", symbol, level, prev_order_ids,
                len(prev_order_ids), len(open_orders))
    return prev_order_ids

def _cal_level_price_by_spread(strategy:FollowMakerStrategy, base_price:float, level:str):
    """
    Calculate the propagation price based on the level
    Different levels access different sub objects of strategy
    """
    if level == FAR_END:
        side_buy: SideStrategy = strategy.far_end.side_buy
        side_sell: SideStrategy = strategy.far_end.side_sell
    elif level == NEAR_END:
        side_buy: SideStrategy = strategy.near_end.side_buy
        side_sell: SideStrategy = strategy.near_end.side_sell
    else:
        side_buy: SideStrategy = strategy.nearest_end.side_buy
        side_sell: SideStrategy = strategy.nearest_end.side_sell

    fl_buy_price = _calc_price_by_spread('BUY', base_price,
        side_buy.base_type, side_buy.base_margin, side_buy.step_size)
    fl_sell_price = _calc_price_by_spread('SELL', base_price,
        side_sell.base_type, side_sell.base_margin, side_sell.step_size)
    return fl_buy_price, fl_sell_price
    
def exact_making_price(strategy:FollowMakerStrategy, market_client, level:str, logger:Logger):
    # Accurately copy the price of the target coin pair and obtain the market trend of the
    # follow symbol (captured by the market trend module and stored in Redis)
    # This strategy is the simplest and does not require attention to historical order prices
    # fl_buy_price = fl_sell_price = 0.0
    fl_symbol = strategy.follow_symbol
    strategy_id = str(strategy.strategy_id)
    if strategy.follow_symbol_address:
        fl_ticker = market_client.ticker(strategy.follow_symbol_address)
    else:
        fl_ticker = market_client.ticker(fl_symbol)
    if not fl_ticker:
        logger.error("Get Ticker %s:%s, %s", strategy_id, fl_symbol, fl_ticker)
        return f"Exact Maker Error: {fl_symbol} no latest ticker", 0, 0

    _set_monitor_redis(project_id=strategy.term_id,
                       exchange=strategy.exchange,
                       symbol=strategy.symbol,
                       pivot=fl_ticker[0].p,
                       logger=logger)
    logger.debug("Get Ticker %s:%s, %s", strategy_id, fl_symbol, fl_ticker)
    # Determine the buy one sell one price based on the latest price of the follow symbol
    base_price = float(fl_ticker[0].p)
    fl_buy_price, fl_sell_price = _cal_level_price_by_spread(strategy=strategy,
                                      base_price=base_price,
                                      level=level)
    return "ok", fl_buy_price, fl_sell_price

def pivot_making_price(strategy: FollowMakerStrategy, client, prev_maker_strategy, 
                 market_client, level:str, logger: Logger):
    """
    # Follow the rise and fall of the symbol, but the benchmark for the placement price is stored in Redis. 
    # If switching from other market making strategies to pivot strategies,
    # Need to reconstruct context
    """
    fl_symbol = strategy.follow_symbol
    if strategy.follow_symbol_address:
        fl_ticker = market_client.ticker(strategy.follow_symbol_address)
    else:
        fl_ticker = market_client.ticker(fl_symbol)
    if not fl_ticker:
        logger.error("Get Ticker %s:%s, %s", strategy.strategy_id, fl_symbol, fl_ticker)
        return f"Pivot Maker Error: {fl_symbol} no latest ticker"

    logger.debug("Get Pivot %s:%s, %s", strategy.strategy_id, fl_symbol, fl_ticker)
    fl_price = float(fl_ticker[0].p)
    
    symbol = strategy.symbol
    strategy_id = strategy.strategy_id
    if prev_maker_strategy != strategy.maker_type:  
        # When starting or switching to pivot strategy for the first time, the follow price at the start time
        # needs to be used as the price benchmark to calculate the pivot price
        strategy.price_baseline = fl_price
        strategy.minute_price_baseline = {
            'minute': int(time.time() / 60),
            'price_minus1': fl_price,
            'price_minus2': fl_price,
            'prev_price': fl_price,
        }
        if prev_maker_strategy == '':
            # Launch pivot strategy for the first time, with IPO price as the center of the previous round
            strategy.prev_pivot = strategy.ipo_price
            logger.debug('Pivot Strategy use IPO as previous Pivot %s',
                            strategy.prev_pivot)
        else:
           # Switching from other market making strategies to a central strategy requires using the latest
           # transaction price of the market making currency pair as the previous central strategy
            ticker = client.ticker(symbol)
            if not ticker:
                logger.error("Get Ticker %s:%s, %s", strategy_id, symbol, ticker)
                return f"Trade Maker Error: {symbol} no latest ticker"

            logger.debug("Get Ticker %s:%s, %s", strategy_id, symbol, ticker)
            strategy.prev_pivot = float(ticker[0].p)
            logger.debug('Pivot Strategy use latest ticker as previous Pivot %s',
                            strategy.prev_pivot)

    pivot = _calc_mirror_pivot(client, strategy, fl_price, logger)
    logger.debug("New Pivot %s: %s", symbol, pivot)

    _set_monitor_redis(project_id=strategy.term_id,
                       exchange=strategy.exchange,
                       symbol=symbol,
                       pivot=pivot,
                       logger=logger)
    fl_buy_price, fl_sell_price = _cal_level_price_by_spread(strategy=strategy,
                                      level=level,
                                      base_price=pivot)
    return "ok", fl_buy_price, fl_sell_price

def trade_making_price(strategy: FollowMakerStrategy, client, prev_maker_strategy, 
                       market_client, level:str, logger:Logger):
    # Follow the rise and fall of the following symbol, but the benchmark for the placement price is the
    # latest transaction price of the market making symbol, and the market making context is stored in Redis.
    # To migrate from other market making strategies to TRADE strategy, simply update the latest price.
    symbol = strategy.symbol
    strategy_id = strategy.strategy_id
    ticker = client.ticker(symbol)
    fl_symbol = strategy.follow_symbol
    if not ticker:
        logger.error("Get Ticker %s:%s, %s", strategy_id, symbol, ticker)
        return f"Trade Maker Error: {symbol} no latest ticker", 0, 0

    logger.debug("[TRADE] Get Ticker %s:%s, %s", strategy_id, symbol, ticker)
    latest_price = float(ticker[0].p)

    # Price of following symbol
    if strategy.follow_symbol_address:
        fl_ticker = market_client.ticker(strategy.follow_symbol_address)
    else:
        fl_ticker = market_client.ticker(fl_symbol)
    if not fl_ticker:
        logger.error("Get follow Ticker %s:%s, %s", strategy_id, fl_symbol, fl_ticker)
        return f"Trade Maker Error: {fl_symbol} no latest ticker", 0, 0

    logger.debug("[TRADE] Follow Ticker %s:%s, %s", strategy_id, fl_symbol, fl_ticker)
    fl_price = float(fl_ticker[0].p)

    #Switching from other strategies to TRADE strategy or launching
    # Trade strategy for the first time requires resetting the benchmark price
    if prev_maker_strategy != "TRADE" or not strategy.prev_fl_price:
        # Save status in strategy
        strategy.prev_fl_price = fl_price
        strategy.minute_price_baseline = {
            'minute': int(time.time() / 60),
            'price_minus1': fl_price,
            'price_minus2': fl_price,
            'prev_price': fl_price,
        }
        logger.info('[TRADE]  %s initialed: prev_fl_price=%s', strategy.maker_type, fl_price)
        return f"{strategy.maker_type} initialed", 0, 0

    # Calculate the range of price fluctuations based on the price of the symbol followed during the previous order placement
    fl_rtn = fl_price / strategy.prev_fl_price - 1
    logger.debug('Trade Strategy: previous follow price=%s, follow return=%s',
                    strategy.prev_fl_price, fl_rtn)
    # Update the latest price of the follow symbol for calculating the next round of price fluctuations
    strategy.prev_fl_price = fl_price
    # calculate minutely return
    curr_minute = int(time.time() / 60)
    minute_ctx = strategy.minute_price_baseline
    if curr_minute > minute_ctx['minute']:
        # calculate return by open price of each minute
        minute_ctx['price_minus2'] = minute_ctx['price_minus1']
        minute_ctx['price_minus1'] = minute_ctx['prev_price']
        minute_ctx['minute'] = curr_minute
    minute_ctx['prev_price'] = fl_price
    up_beta, down_beta = strategy.follow_upside_beta, strategy.follow_downside_beta
    if minute_ctx['price_minus1'] >= minute_ctx['price_minus2']:
        fl_rtn *= 1 + up_beta
    else:
        fl_rtn *= 1 + down_beta
    # Based on the latest transaction price as the central price
    pivot = latest_price * (1 + fl_rtn)
    logger.debug("New Pivot %s: %s, beta-rtn=%s", symbol, pivot, fl_rtn)
    _set_monitor_redis(project_id=strategy_id,
                       exchange=strategy.exchange,
                       symbol=symbol,
                       pivot=pivot,
                       logger=logger)
    fl_buy_price, fl_sell_price = _cal_level_price_by_spread(strategy=strategy,
                                      base_price=pivot,
                                      level=level)
    return "ok", fl_buy_price, fl_sell_price

async def market_making(client, market_client, strategy: FollowMakerStrategy, level: str) -> str:
    """ 
    # Place orders first and cancel later to avoid a bearish market trend
    # The key is to determine the central price for this round of orders
    """
    logger = logging.getLogger(LOG_NAME)
    # load strategy parameter
    # strategy_id = str(strategy.strategy_id)
    try:
        # 1. get open orders
        prev_order_ids = get_strategy_open_orders(
            client=client,
            strategy=strategy,
            level=level,
            logger=logger)
        # 2. put new orders
        # 2.1 get the latest pivot price
        # Making strategy: EXACT, PIVOT, TRADE, FIXED
        maker_strategy = strategy.maker_type
        if maker_strategy == 'PIVOT' and strategy.price_factor == 1:
            maker_strategy = 'TRADE'

        # Strategy of previous loop
        prev_maker_strategy = strategy.prev_maker_type
        strategy.prev_maker_type = maker_strategy
        if maker_strategy == 'EXACT':
            # Strategy: EXACT
            _msg, fl_buy_price, fl_sell_price = exact_making_price(
                strategy=strategy,
                market_client=market_client,
                level=level,
                logger=logger)
            logger.debug("[EXACT] make price: buy_price[%s], sell_price[%s], msg[%s]", fl_buy_price, fl_sell_price, _msg)
        elif maker_strategy == 'PIVOT': # PIVOT
            # Strategy: PIVOT
            _msg, fl_buy_price, fl_sell_price = pivot_making_price(
                strategy=strategy,
                client=client,
                prev_maker_strategy=prev_maker_strategy,
                market_client=market_client,
                level=level,
                logger=logger
            )
            logger.debug("[PIVOT] make price: buy_price[%s], sell_price[%s], msg[%s]", fl_buy_price, fl_sell_price, _msg)
        elif maker_strategy == 'TRADE': # TRADE
            # Strategy: TRADE
            _msg, fl_buy_price, fl_sell_price = trade_making_price(
                strategy=strategy,
                client=client,
                prev_maker_strategy=prev_maker_strategy,
                market_client=market_client,
                level=level,
                logger=logger
            )
            logger.debug("[TRADE] make price: buy_price[%s], sell_price[%s], msg[%s]", fl_buy_price, fl_sell_price, _msg)
        elif maker_strategy == 'FIXED':
            # Placing orders near a fixed price without considering strategy switching
            fixed_price = strategy.follow_price # Specified price center
            price_range = strategy.price_range  # Price amplitude
            fl_price = random.uniform(max(0, fixed_price - price_range),
                                       fixed_price + price_range)
            logger.debug("Get Fixed Price %s, range %s, follow price %s",
                         fixed_price, price_range, fl_price)
            _set_monitor_redis(project_id=strategy.term_id,
                               exchange=strategy.exchange,
                               symbol=strategy.symbol,
                               pivot=fl_price,
                               logger=logger)
            fl_buy_price, fl_sell_price = _cal_level_price_by_spread(strategy=strategy,
                                                                     base_price=fl_price,
                                                                     level=level)
            _msg = "ok"
            logger.debug("[FIXED] make price: buy_price[%s], sell_price[%s]", fl_buy_price, fl_sell_price)
        else:
            logger.error("Maker strategy %s is not supported.", maker_strategy)
            return f"{maker_strategy} is not supported."
        if _msg != "ok":
            return _msg
        
        # 2.2 calculate tracking beta
        logger.debug('%s %s %s follow buy price=%s, sell price=%s',
                     strategy.strategy_id, strategy.symbol, level, fl_buy_price, fl_sell_price)
        if not fl_sell_price or not fl_buy_price:
            return f"Failed to get quote of project id={strategy.term_id}, symbol={strategy.follow_symbol}"
        
        # # 2.3 put new orders
        make_res = put_new_orders(
            client, strategy, level, float(fl_buy_price), float(fl_sell_price), logger)
        logger.info('make_res: %s at [%s]', make_res, level)
        if not make_res:
            logger.error("%s Failed to make orders: %s", strategy.symbol, make_res)
            return f'Failed to make orders {strategy.strategy_id}'

        new_order_ids = [order.order_id for order in make_res if order.order_id]
        logger.info('%s %s New order ids: %s', strategy.symbol, level, new_order_ids)
        start_ts = time.time()
        while 1:
            # check and cancel orders
            if check_and_cancel(client, strategy.symbol, new_order_ids, prev_order_ids, logger):
                break

            if time.time() - start_ts > 1:
                # timeout 1s
                logger.error("%s checkout make status timeout", strategy.symbol)
                break
            await asyncio.sleep(0.05)
        return f'OK {strategy.strategy_id}'
    except Exception as e:
        logger.error(traceback.format_exc())
        return str(e)


class TrackMaker:
    """ Market Maker Agent
    """
    __slots__ = ('config_key', 'config_version', 'logger', '_market_clients', '_trade_clients')
    def __init__(self, config_key: str, logger: Logger):
        self.config_key = config_key
        self.config_version = 0
        self.logger = logger

        self._market_clients = {}
        self._trade_clients = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type:
            self.logger.error(traceback.format_exc())
            self.logger.error(exc_value)
        return True

    def _remove_strategy(self, strategy: FollowMakerStrategy):
        """
        Remove old strategy
        Cancel open orders by prefix sid
        """
        client = self._trade_clients[strategy.api_key]
        symbol = strategy.symbol
        sid = strategy.strategy_id
        open_orders = client.open_orders(symbol)
        prev_order_ids = []
        if open_orders:
            prev_order_ids = [order.order_id for order in open_orders if order.client_id.startswith(sid)]
        if prev_order_ids:
            res = client.batch_cancel(prev_order_ids, symbol)
            self.logger.info("Remove strategy %s, cancel orders: %s", sid, res)
        # update new strategy status
        rkey = f'{sid}{symbol}'
        set_dict(rkey, {'status': 'stopped', 'ts': time.time()})
        self.logger.info('Set Monitor: strategy=%s %s stopped', sid, symbol)

    def _remove_strategy_level(self, strategy: FollowMakerStrategy, level: str):
        """
        Remove old strategy level
        Cancel open orders by prefix sid_n/f/U
        """
        client = self._trade_clients[strategy]
        open_orders = client.open_orders(strategy.symbol)
        prev_order_ids = []
        if open_orders:
            if level == NEAR_END:
                clorder_prefix = f'{strategy.strategy_id}_n'
            elif level == FAR_END:
                clorder_prefix = f'{strategy.strategy_id}_f'
            else:
                clorder_prefix = f'{strategy.strategy_id}_U'
            prev_order_ids = [order.order_id for order in open_orders if order.client_id.startswith(clorder_prefix)]
        if prev_order_ids:
            res = client.batch_cancel(prev_order_ids, strategy.symbol)
            self.logger.info("Remove strategy %s, level %s, cancel orders: %s",
                             strategy.strategy_id, level, res)
            
    def set_level_side(self, strategy: LevelStrategy):
        """
        Set making side for level strategy
        """
        if not strategy:
            return
        if strategy.side_buy and strategy.side_buy.size > 0 \
            and strategy.side_sell and strategy.side_sell.size > 0:
                strategy.side = "BOTH"
        elif strategy.side_buy and strategy.side_buy.size > 0:
            strategy.side = "BUY"
        else:
            strategy.side = "SELL"
        return
            
    def update_strategy_config(self, strategy_configs:dict):
        """
        update making strategies with values stored in redis
        :return: False - some error, True - no error
        :rtype: bool
        """
        try:
            new_version, _redis_configs = load_config(self.config_key, self.config_version)
            new_configs = [FollowMakerStrategy(**item) for item in _redis_configs]
        except ValidationError as e:
            self.logger.error("Parse FollowMakerStrategy failed: %s, %s", e.json(), _redis_configs)
            return {}
        if new_version <= self.config_version:
            return {}    # configs not changed
        # remote config version > local config version => update config
        new_strategy_configs = {}
        for item in new_configs:
            # attribute "side" given here
            if item.far_end:
                self.set_level_side(item.far_end)
            if item.near_end:
                self.set_level_side(item.near_end)
            if item.nearest_end:
                self.set_level_side(item.nearest_end)
            # use sid to indexing strategy items
            new_strategy_configs[str(item.strategy_id)]=item
            self.logger.info("Update Config: %s", new_configs)
        for sid, strategy in strategy_configs.items():
            if sid not in new_strategy_configs:
                # remove strategy, cancel all orders
                self._remove_strategy(strategy)
                self.logger.info('Remove strategy %s', sid)
            else:
                # update previous strategy config
                # level strategy in previous strategy[sid] was removed in new strategy[sid]
                if strategy.far_end and not new_strategy_configs[sid].far_end:
                    self._remove_strategy_level(strategy, FAR_END)
                    self.logger.info('Remove old strategy %s, old level %s', sid, FAR_END)
                if strategy.near_end and not new_strategy_configs[sid].near_end:
                    self._remove_strategy_level(strategy, NEAR_END)
                    self.logger.info('Remove old strategy %s, old level %s', sid, NEAR_END)
                if strategy.nearest_end and not new_strategy_configs[sid].nearest_end:
                    self._remove_strategy_level(strategy, NEAREST_END)
                    self.logger.info('Remove old strategy %s, old level %s', sid, NEAREST_END)
                # 保存策略依赖的中间状态
                if strategy.prev_maker_type:
                    new_strategy_configs[sid].prev_maker_type = strategy.prev_maker_type
        self.config_version = new_version
        return new_strategy_configs

    def prepare_making_tasks(self, strategy_configs: dict, _op_ts:dict):
        """
        Prepare follow maker tasks.
        :param strategy_configs: {sid: FollowMakerStrategy}
        :param _op_ts: {"config": time in seconds}
        """
        tasks = []
        for sid, strategy in strategy_configs.items():
            ts = time.time()
            # Begin making after start_ts
            # strategy.start_ts default 0.0
            # strategy.start_time default ""
            if strategy.start_time:
                # start_time: datatime formate, eg.'2025-10-18 00:00:00'
                dt = datetime.strptime(strategy.start_time, '%Y-%m-%d %H:%M:%S')
                strategy['start_ts'] = dt.replace(tzinfo=BJ_TZ).timestamp()
                continue
            if ts < strategy.start_ts:
                continue
            exchange = strategy.exchange
            api_key = strategy.api_key
            if api_key not in self._trade_clients:
                # create a private client to put/cancel orders
                self._trade_clients[api_key] = get_private_client(exchange, api_key,
                    strategy.api_secret, passphrase=strategy.passphrase, logger=self.logger,
                    category=strategy.term_type)    # strategy.term_type 默认值 SPOT
            client = self._trade_clients[api_key]

            # Initiate marketing client, get marketing data through restful api.
            fl_exchange = strategy.follow_exchange
            if fl_exchange not in self._market_clients:
                market_client = get_market_client(fl_exchange, logger=self.logger)
                self._market_clients[fl_exchange] = market_client
            else:
                market_client = self._market_clients[fl_exchange]
            if strategy.far_end and \
                _op_ts.get(f'{sid}{FAR_END}', 0.0) + 0.001 * float(strategy.far_end.order_frequency) < ts:
                    tasks.append(asyncio.create_task(market_making(client, market_client, strategy, FAR_END)))
                    _op_ts[f'{sid}{FAR_END}'] = ts
            if strategy.near_end and \
                _op_ts.get(f'{sid}{NEAR_END}', 0.0) + 0.001 * float(strategy.near_end.order_frequency) < ts:
                    tasks.append(asyncio.create_task(market_making(client, market_client, strategy, NEAR_END)))
                    _op_ts[f'{sid}{NEAR_END}'] = ts
            if strategy.nearest_end and \
                _op_ts.get(f'{sid}{NEAREST_END}', 0.0) + 0.001 * float(strategy.nearest_end.order_frequency) < ts:
                    tasks.append(asyncio.create_task(market_making(client, market_client, strategy, NEAREST_END)))
                    _op_ts[f'{sid}{NEAREST_END}'] = ts
            return tasks
                    
                    
    async def run_forever(self):
        """ Strategy config:
        base schema: FollowMakerStrategy
        read from redis: list[FollowMakerStrategy]
        strategy_configs: {sid: FollowMakerStrategy} where sid as index
        """
        _op_ts = {'config': 0.0}    # the timestamp of last operation
        strategy_configs = {}
        while 1:
            try:
                ts = time.time()
                # 1. Update config from redis
                if _op_ts['config'] + 5 < ts:
                    # None: reading redis or parsing object failed, not changed
                    # !None: strategy_configs renewed
                    new_strategy_configs = self.update_strategy_config(strategy_configs)
                    if new_strategy_configs:
                        strategy_configs = new_strategy_configs # config not changed
                    _op_ts['config'] = time.time()
                # 2. collect making tasks
                tasks = self.prepare_making_tasks(strategy_configs, _op_ts)
                # 3. Run making tasks
                if tasks:
                    _results = await asyncio.gather(*tasks)
                else:
                    await asyncio.sleep(0.1)
            except Exception:
                self.logger.error(traceback.format_exc())

def main(config_key: str):
    """ Start TrackMaker agent
    """
    logger = create_logger(SRV_PATH, f'track_maker_{config_key}.log', LOG_NAME)
    with TrackMaker(config_key, logger) as agent:
        asyncio.run(agent.run_forever())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"python {sys.argv[0]} <config_key>")
        sys.exit(1)
    main(sys.argv[1])
