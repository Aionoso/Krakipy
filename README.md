# Krakipy
[![Documentation Status](https://readthedocs.org/projects/krakipy/badge/?version=latest)](https://krakipy.readthedocs.io/en/latest/?badge=latest)
Krakipy is an easy to use Kraken API.
It uses the [REST-API](https://www.kraken.com/features/api) of the [Kraken.com](https://www.kraken.com) cryptocurrency exchange.

For more information please visit the [krakipy documentation](https://krakipy.readthedocs.io/en/latest/)

31.07.2021 - Updated krakipy to support staking and unstaking


### Features
- All methods of the kraken rest api are included (Krakipy documentation also updated)
- Easy and fast to use
- Two factor authentification support (static and OTP)
- Tor suppport

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install krakipy.

```bash
pip install krakipy
```

## Usage Examples

### Public Requests

Public requests dont need API keys

```python
from krakipy import KrakenAPI

# Create a session
kr = KrakenAPI()

# Bitcoin - EUR
kr.get_ticker_information("XXBTZEUR")

# Doge - Tether
kr.get_ohlc_data("XDGUSDT")

# Ether - USD
kr.get_recent_spreads("XETHZUSD")

# Check the Kraken API system status
kr.get_system_status()
```

### Private Requests

Private requests need a valid API key pair to your Kraken account for validation

```python
from krakipy import KrakenAPI

api_key = "*************************************************"
api_key_secret = "*************************************************"

# Create a validated session
kr = KrakenAPI(api_key, api_key_secret)

# Create a Limit order to buy 420.69 Bitcoin under 100,000.0 EUR/BTC
kr.add_standard_order("XXBTZEUR", "buy", "limit", volume = 420.69, price = 100000.0)
->
{'descr': {'order': 'buy 420.69000000 XBTEUR @ limit 100000.0'},
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

The krakipy code is licensed under the GNU GENERAL PUBLIC LICENSE Version 3.
This program comes with ABSOLUTELY NO WARRANTY

Krakipy  Copyright (C) 2020-2021  Hubertus Wilisch
