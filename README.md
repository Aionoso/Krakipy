# Krakipy
Krakipy is a easy to use Kraken API.
It uses the [REST-API](https://www.kraken.com/features/api) of the [Kraken.com](https://www.kraken.com) cryptocurrency exchange.

For more information please visit the [krakipy Documentation](https://krakipy.readthedocs.io/en/latest/)

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install krakipy.

```bash
pip install krakipy
```

## Usage

```python
from krakipy import KrakenAPI

kr = KrakenAPI()

kr.get_ohlc_data("XXBTZEUR")
```
