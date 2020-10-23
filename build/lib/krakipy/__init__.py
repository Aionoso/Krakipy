""" 
A complete interface to the kraken-api provided by `krakipy`.
Usage example:

.. code-block:: python

   from krakipy import KrakenAPI

   kr = KrakenAPI()
   data = kr.get_trade_volume("ZEUR")

"""
from __future__ import absolute_import
from .krakipy import KrakenAPI, add_dtime, datetime_to_unixtime, unixtime_to_datetime
__all__ = ["KrakenAPI", "add_dtime", "datetime_to_unixtime", "unixtime_to_datetime"]