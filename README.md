# Krakipy

[![PyPI version](https://badge.fury.io/py/krakipy.svg)](https://badge.fury.io/py/krakipy)
[![Documentation Status](https://readthedocs.org/projects/krakipy/badge/?version=latest)](https://krakipy.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://pepy.tech/badge/krakipy)](https://pepy.tech/project/krakipy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Aionoso/Krakipy/blob/master/LICENSE)

Krakipy is an easy to use Kraken API.
It uses the [REST-API](https://docs.kraken.com/rest/#section/General-Usage) of the [Kraken.com](https://www.kraken.com) cryptocurrency exchange.

For more information please visit the [krakipy documentation](https://krakipy.readthedocs.io/en/latest/)

29.10.2023 - Updated krakipy to include new functions and fixed bugs
31.07.2021 - Updated krakipy to support staking and unstaking


### Features
- All methods of the Kraken Rest API are included (Krakipy documentation also updated)
- Easy and fast to use
- Two factor authentification support (static and OTP)
- Tor support

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install krakipy.

```bash
pip install krakipy
```

## Usage Examples

### Public Requests

Public requests dont need API keys.

```python
from krakipy import KrakenAPI

# Create a session
kr = KrakenAPI()


# Get Ticker for Bitcoin/EUR
kr.get_ticker_information("XXBTZEUR")

# Get OHLC for Doge/Tether
kr.get_ohlc_data("XDGUSDT")

# Get Spreads for Ether/USD
kr.get_recent_spreads("XETHZUSD")

# Check the Kraken API system status
kr.get_system_status()
```

### Private Requests

Private requests need a valid API key pair to your Kraken account for validation.

```python
from krakipy import KrakenAPI

api_key = "*************************************************"
api_key_secret = "*************************************************"

# Create a validated session
kr = KrakenAPI(api_key, api_key_secret)


# Create a Limit order to buy 1.5 Bitcoin under 100,000.0 EUR/BTC
kr.add_standard_order("XXBTZEUR", "buy", "limit", volume = 1.5, price = 100000.0)
->
{'descr': {'order': 'buy 1.50000000 XBTEUR @ limit 100000.0'},
 'txid': ['OHPCQQ-HRJTQ-ZBDGSE']}


# Check your account balance
kr.get_account_balance()

# Withdraw 1.0 Bitcoin to myBTCWallet
kr.withdraw("XBT", "myBTCWallet", 1.0)

# Unstake 300.0 Polkadot
kr.unstake_asset("DOT", 300.0)

# Download and save an export report to kraken_reports/
kr.retrieve_export_report(report_id, dir="kraken_reports/")
```

## License

The krakipy code is licensed under the MIT LICENSE.
This program comes with ABSOLUTELY NO WARRANTY

Krakipy Copyright (C) 2020-2023  Hubertus Wilisch
