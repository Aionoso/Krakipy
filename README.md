# Krakipy

[![PyPI version](https://badge.fury.io/py/krakipy.svg)](https://badge.fury.io/py/krakipy)
[![Documentation Status](https://readthedocs.org/projects/krakipy/badge/?version=latest)](https://krakipy.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://pepy.tech/badge/krakipy)](https://pepy.tech/project/krakipy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Aionoso/Krakipy/blob/master/LICENSE)

Krakipy is an easy to use Kraken API.

It uses the [REST-API](https://docs.kraken.com/api/docs/rest-api/get-server-time) of the [Kraken.com](https://www.kraken.com) cryptocurrency exchange.

For more information please visit the [krakipy documentation](https://krakipy.readthedocs.io/en/latest/)

16.08.2025 - Updated krakipy to include amend_order, get_credit_line, add_order_batch, get_websocket_token, create_subaccount, account_transfer, get_withdrawal_adresses, get_pre_trade_data, get_post_trade_data and fixed bugs

08.03.2025 - Updated krakipy to include get_order_amends and get_withdrawal_methods and fixed bugs

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
with KrakenAPI(api_key, api_key_secret) as kr:

	# Send a limit order to buy 1.5 Bitcoin at 100,000.0 EUR/BTC
	kr.add_standard_order("XXBTZEUR", "buy", "limit", volume = 1.5, price = 100000.0)

	# Check your account balance
	kr.get_account_balance()

	# Check your withdrawal adresses
	kr.get_withdrawal_adresses()

	# Withdraw 1.0 Bitcoin to myBTCWallet
	kr.withdraw("XBT", "myBTCWallet", 1.0)

	# Download and save an export report to kraken_reports/
	kr.retrieve_export_report(report_id, dir="kraken_reports/")
```

## License

The krakipy code is licensed under the MIT LICENSE.
This program comes with no WARRANTY.

Krakipy Copyright (C) 2020-2025  Hubertus Wilisch
