""" 
A complete interface to the `Kraken API <https://www.kraken.com/features/api>`_ provided by `Krakipy <https://pypi.org/project/krakipy/>`_.

Usage example:

.. code-block:: python

   from krakipy import KrakenAPI

   kr = KrakenAPI()
   data = kr.get_trade_volume("ZEUR")

"""
from __future__ import absolute_import
from .krakipy import KrakenAPI, KeyNotSetError, KrakenAPIError, CallRateLimitError, add_dtime, datetime_to_unixtime, unixtime_to_datetime
__all__ = ["KrakenAPI", "KeyNotSetError", "KrakenAPIError", "CallRateLimitError", "add_dtime", "datetime_to_unixtime", "unixtime_to_datetime"]
