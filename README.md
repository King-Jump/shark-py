# SharkPy - Open Source Market Value Management System

SharkPy is an open-source cryptocurrency market value management system that provides two market making methods: Follow Maker and Self Trade, used to increase market liquidity and manage token prices.

## Project Features

### 1. Follow Maker
- **Price Following**: Follows price movements of reference cryptocurrency pairs and replicates these movements on target currency pairs
- **Multiple Market Making Strategies**: Supports EXACT, PIVOT, TRADE, and FIXED market making strategies
- **Multi-level Order Placement**: Supports nearest, near, and far three-level order configurations
- **Dynamic Configuration Updates**: Real-time configuration updates via Redis

### 2. Self Trade
- **Self Trading**: Performs buy and sell operations within the same account to create trading volume
- **Multi-scale Trading**: Supports large, medium, and small scale trading configurations
- **Price Strategies**: Supports uniform random and top ask/bid random price generation strategies
- **Simulated Trading**: Supports simulated trading mode that doesn't actually execute orders

## Project Structure

```
sharkpy/
├── follow_maker/            # Follow Maker module
│   ├── follow_maker_main.py  # Main entry file
│   └── simplified/           # Simplified module
├── self_trade/             # Self Trade module
│   └── self_trade_main.py   # Main entry file
├── management/             # Strategy configuration models
│   ├── follow_maker_strategy.py  # Follow Maker strategy model
│   └── self_trade_strategy.py    # Self Trade strategy model
├── liquidity/              # Liquidity-related functions
│   └── liquidity.py        # Liquidity utility functions
└── utils/                  # Utility functions
    ├── config_util.py      # Configuration management
    ├── db_util.py          # Database utilities
    └── log_util.py         # Logging utilities
examples/                   # Example configuration files
├── tmm_dolphin_jpmusdt.json  # Follow Maker example configuration
└── st_dolphin_jpmusdt.json    # Self Trade example configuration
```

## Installation Instructions

### 1. Environment Requirements
- Python 3.7+
- Redis server

### 2. Dependency Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Note: octopus-py is a local dependency, ensure the ../octopus-py/ directory exists
# Install local octopus-py dependency
pip install -e ../octopus-py/
```

## Usage

### 1. Follow Maker

#### Configuration Preparation
1. Edit the `examples/tmm_dolphin_jpmusdt.json` file, filling in your API keys and strategy parameters
2. Load the configuration into Redis, specifying a key name. For example: `tmm_dolphin_jpmusdt`

#### Running

```bash
python sharkpy/follow_maker/follow_maker_main.py <config_key>

Example: python sharkpy/follow_maker/follow_maker_main.py tmm_dolphin_jpmusdt
```

### 2. Self Trade

#### Configuration Preparation
1. Edit the `examples/st_dolphin_jpmusdt.json` file, filling in your API keys and strategy parameters
2. Load the configuration into Redis, specifying a key name. For example: `st_dolphin_jpmusdt`

#### Running

```bash
python sharkpy/self_trade/self_trade_main.py <config_key>

Example: python sharkpy/self_trade/self_trade_main.py st_dolphin_jpmusdt 
```

## Strategy Configuration Description

### Follow Maker Strategy

| Configuration Item | Description |
|-------------------|-------------|
| api_key | Exchange API key |
| api_secret | Exchange API secret |
| exchange | Trading exchange ID |
| follow_exchange | Price following exchange ID |
| follow_symbol | Reference currency pair |
| symbol | Target currency pair |
| maker_type | Market making strategy type (EXACT, PIVOT, TRADE, FIXED) |
| far_end | Far end order strategy |
| near_end | Near end order strategy |
| nearest_end | Nearest end order strategy |
| follow_upside_beta | Upside beta factor |
| follow_downside_beta | Downside beta factor |
| ipo_price | IPO price (used by PIVOT strategy) |

### Self Trade Strategy

| Configuration Item | Description |
|-------------------|-------------|
| api_key | Exchange API key |
| api_secret | Exchange API secret |
| exchange | Trading exchange ID |
| symbol | Target currency pair |
| large_amount | Large transaction amount |
| large_frequency | Large transaction frequency (seconds) |
| large_float_range | Large transaction price floating range |
| middle_amount | Medium transaction amount |
| middle_frequency | Medium transaction frequency (seconds) |
| middle_float_range | Medium transaction price floating range |
| small_amount | Small transaction amount |
| small_frequency | Small transaction frequency (seconds) |
| small_float_range | Small transaction price floating range |
| buy_order_rate | Buy order ratio (%) |
| prevention_rate | Price fluctuation limit (%) |
| trade_type | Trade type (MOCK or empty) |

## Log Management

- Follow Maker logs: `logs/track_maker_{config_key}.log`
- Self Trade logs: `logs/st_{config_key}.log`

## Monitoring

- Strategy status is stored in Redis with key format `_amstatus_{strategy_id}`
- Base price is stored in Redis with key format `{project_id}{exchange}{symbol}`

## Notes

1. **API Key Security**: Please keep your API keys secure and avoid disclosure
2. **Exchange Limits**: Understand and comply with exchange API limits and self-trading rules
3. **Risk Control**: Set reasonable price fluctuation limits to avoid abnormal trading
4. **Testing**: It is recommended to test with simulated trading mode first before switching to real trading

## License

This project is licensed under the MIT License.

## Contribution

Welcome to submit Issues and Pull Requests to improve this project.

## Contact

If you have any questions or suggestions, please contact us through GitHub Issues.