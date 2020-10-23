# Krakipy
Krakipy is a easy to use Kraken API.
It uses the [REST-API](https://www.kraken.com/features/api) of the [Kraken.com](https://www.kraken.com) cryptocurrency exchange.

For more information please visit the [krakipy documentation](https://krakipy.readthedocs.io/en/latest/)

### Features
- all methods of the kraken rest api are included
- easy and fast to use
- two factor authentification support
- tor suppport

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install krakipy.

```bash
pip install krakipy
```

## Usage

```python
from krakipy import KrakenAPI

kr = KrakenAPI()

kr.get_ticker_information("XXBTZEUR")
```

## License

The krakipy code is licensed under the GNU GENERAL PUBLIC LICENSE Version 3.
This program comes with ABSOLUTELY NO WARRANTY

Krakipy  Copyright (C) 2020  Hubertus Wilisch