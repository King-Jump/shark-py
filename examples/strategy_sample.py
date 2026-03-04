m01_tmm_mybx_001_data = [
    {
        "api_key": "your api key",
        "api_secret": "your api secret",
        "exchange": 10013,
        "follow_exchange": 10002,
        "follow_frequency": 1,
        "follow_price": 0.1,
        "follow_symbol": "SOLUSDT",
        "follow_symbol_address": "",
        "follow_downside_beta": 0.01,
        "follow_upside_beta": 0.01,
        "ipo_price": 0.128888,
        "maker_type": "FIXED",
        "name": "follow_maker",
        "price_decimals": 6,
        "price_factor": 1,
        "price_range": 0.00019999999999999998,
        "qty_decimals": 2,
        "start_time": "",
        "strategy_id": 23,
        "symbol": "my_usdt",
        "symbol_address": "",
        "term_id": 13,
        "term_type": "SPOT",
        "version": 31,
        "far_end": {
            "order_frequency": 5000,
            "strategy_type": "manual",
            "side_buy": {
                "amount": 100,
                "base_margin": 20,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 50,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 100,
                "base_margin": 20,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 50,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            }
        },
        "near_end": {
            "order_frequency": 3000,
            "side_buy": {
                "amount": 100,
                "base_margin": 5,
                "base_type": "BPS",
                "level_margin": 3,
                "level_type": "BPS",
                "quantity": 5,
                "step_size": 1e-06,
                "time_in_force": "GTC",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 120,
                "base_margin": 5.5,
                "base_type": "BPS",
                "level_margin": 3,
                "level_type": "BPS",
                "quantity": 5,
                "step_size": 1e-06,
                "time_in_force": "GTC",
                "total_amount": 100000
            },
            "strategy_type": "manual"
        },
        "nearest_end": {
            "order_frequency": 3000,
            "side_buy": {
                "amount": 20,
                "base_margin": 7,
                "base_type": "BPS",
                "level_margin": 5,
                "level_type": "BPS",
                "quantity": 3,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 20.69,
                "base_margin": 8.5,
                "base_type": "BPS",
                "level_margin": 5,
                "level_type": "BPS",
                "quantity": 3,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 99999.97
            },
            "strategy_type": "manual"
        }
    }
]

m01_st_mybx_001_data = [
    {
        "api_key": "your api key",
        "api_secret": "your api secret",
        "buy_order_rate": 40,
        "exchange": 10013,
        "large_amount": 800,
        "large_float_range": 0.5,
        "large_frequency": 55,
        "middle_amount": 250,
        "middle_float_range": 0.35,
        "middle_frequency": 23,
        "name": "self_trade",
        "prevention_rate": 3,
        "price_decimals": 6,
        "qty_decimals": 2,
        "small_amount": 100,
        "small_float_range": 0.22,
        "small_frequency": 4,
        "start_time": "",
        "strategy_id": 25,
        "symbol": "my_usdt",
        "symbol_address": "",
        "term_id": 13,
        "term_type": "SPOT",
        "trade_type": "MOCK",
        "version": 11
    }
]

m01_tmm_mybx_001_data = [
    {
        "api_key": "",
        "api_secret": "",
        "exchange": 10013,
        "far_end": {
            "order_frequency": 5000,
            "side_buy": {
                "amount": 50,
                "base_margin": 20,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 3,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 100,
                "base_margin": 20,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 0,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            },
            "strategy_type": "manual"
        },
        "follow_downside_beta": 0.01,
        "follow_exchange": 10002,
        "follow_frequency": 3,
        "follow_price": 0.064,
        "follow_symbol": "SOLUSDT",
        "follow_symbol_address": "",
        "follow_upside_beta": 0.01,
        "ipo_price": 0.128888,
        "maker_type": "FIXED",
        "name": "follow_maker",
        "near_end": {
            "order_frequency": 3000,
            "side_buy": {
                "amount": 50,
                "base_margin": 8,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 0,
                "step_size": 1e-06,
                "time_in_force": "GTC",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 120,
                "base_margin": 8,
                "base_type": "BPS",
                "level_margin": 8,
                "level_type": "BPS",
                "quantity": 0,
                "step_size": 1e-06,
                "time_in_force": "GTC",
                "total_amount": 100000
            },
            "strategy_type": "manual"
        },
        "nearest_end": {
            "order_frequency": 3000,
            "side_buy": {
                "amount": 10,
                "base_margin": 5,
                "base_type": "BPS",
                "level_margin": 5,
                "level_type": "BPS",
                "quantity": 0,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 100000
            },
            "side_sell": {
                "amount": 10,
                "base_margin": 5,
                "base_type": "BPS",
                "level_margin": 5,
                "level_type": "BPS",
                "quantity": 0,
                "step_size": 1e-06,
                "time_in_force": "GTX",
                "total_amount": 1000
            },
            "strategy_type": "manual"
        },
        "price_decimals": 6,
        "price_factor": 1,
        "price_range": 0.00019999999999999998,
        "qty_decimals": 2,
        "start_time": "",
        "strategy_id": 23,
        "symbol": "my_usdt",
        "symbol_address": "",
        "term_id": 13,
        "term_type": "SPOT",
        "version": 40
    }
]