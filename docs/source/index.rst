.. Krakipy documentation master file, created by
   sphinx-quickstart on Sat Oct 17 15:43:38 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
.. toctree::
   :maxdepth: 1
   :caption: krakipy Documentation




Getting started
========================================================

.. automodule:: krakipy

.. autoclass:: KrakenAPI
   :members: __init__



Public market data
========================================================

Get server time
--------------------------------------------------------
.. automethod:: KrakenAPI.get_server_time

Get asset info
--------------------------------------------------------
.. automethod:: KrakenAPI.get_asset_info

Get tradable asset pairs
--------------------------------------------------------
.. automethod:: KrakenAPI.get_tradable_asset_pairs

Get ticker information
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ticker_information

Get OHLC data
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ohlc_data

Get order book
--------------------------------------------------------
.. automethod:: KrakenAPI.get_order_book

Get recent trades
--------------------------------------------------------
.. automethod:: KrakenAPI.get_recent_trades

Get recent spread data
--------------------------------------------------------
.. automethod:: KrakenAPI.get_recent_spread_data



Private user data
========================================================

Get account balance
--------------------------------------------------------
.. automethod:: KrakenAPI.get_account_balance

Get trade balance
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trade_balance

Get open orders
--------------------------------------------------------
.. automethod:: KrakenAPI.get_open_orders

Get closed orders
--------------------------------------------------------
.. automethod:: KrakenAPI.get_closed_orders

Query orders info
--------------------------------------------------------
.. automethod:: KrakenAPI.query_orders_info

Get trades history
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trades_history

Query trades info
--------------------------------------------------------
.. automethod:: KrakenAPI.query_trades_info

Get open positions
--------------------------------------------------------
.. automethod:: KrakenAPI.get_open_positions

Get ledgers info
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ledgers_info

Query ledgers
--------------------------------------------------------
.. automethod:: KrakenAPI.query_ledgers

Get trade volume
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trade_volume

Request export report
--------------------------------------------------------
.. automethod:: KrakenAPI.request_export_report

Get export statuses
--------------------------------------------------------
.. automethod:: KrakenAPI.get_export_statuses

Get export report
--------------------------------------------------------
.. automethod:: KrakenAPI.get_export_report

Remove export report
--------------------------------------------------------
.. automethod:: KrakenAPI.remove_export_report




Private user trading
========================================================

Add standard order
--------------------------------------------------------
.. automethod:: KrakenAPI.add_standard_order

Cancel open order
--------------------------------------------------------
.. automethod:: KrakenAPI.cancel_open_order




Private user funding
========================================================

Get deposit methods
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_methods

Get deposit addresses
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_addresses

Get status of recent deposits
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_status

Get withdrawal information
--------------------------------------------------------
.. automethod:: KrakenAPI.get_withdrawal_info

Withdraw funds
--------------------------------------------------------
.. automethod:: KrakenAPI.withdraw_funds

Get status of recent withdrawals
--------------------------------------------------------
.. automethod:: KrakenAPI.get_withdrawal_status

Request withdrawal cancelation
--------------------------------------------------------
.. automethod:: KrakenAPI.request_withdrawal_cancel

Wallet Transfer
--------------------------------------------------------
.. automethod:: KrakenAPI.wallet_transfer




Extras
========================================================

Add datetime
--------------------------------------------------------
.. autofunction:: add_dtime

Datetime to unixtime
--------------------------------------------------------
.. autofunction:: datetime_to_unixtime

Unixtime to datetime
--------------------------------------------------------
.. autofunction:: unixtime_to_datetime
