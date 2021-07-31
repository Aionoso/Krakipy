.. Krakipy documentation master file, created by
   sphinx-quickstart on Sat Oct 17 15:43:38 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
.. toctree::
   :maxdepth: 1
   :caption: krakipy Documentation




Getting Started
========================================================

.. automodule:: krakipy

.. autoclass:: KrakenAPI
   :members: __init__



Public Market Data
========================================================

Get Server Time
--------------------------------------------------------
.. automethod:: KrakenAPI.get_server_time

Get System Status
--------------------------------------------------------
.. automethod:: KrakenAPI.get_system_status

Get Asset Info
--------------------------------------------------------
.. automethod:: KrakenAPI.get_asset_info

Get Tradable Asset Pairs
--------------------------------------------------------
.. automethod:: KrakenAPI.get_tradable_asset_pairs

Get Ticker Information
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ticker_information

Get OHLC Data
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ohlc_data

Get Order Book
--------------------------------------------------------
.. automethod:: KrakenAPI.get_order_book

Get Recent Trades
--------------------------------------------------------
.. automethod:: KrakenAPI.get_recent_trades

Get Recent Spreads
--------------------------------------------------------
.. automethod:: KrakenAPI.get_recent_spreads



Private User Data
========================================================

Get Account Balance
--------------------------------------------------------
.. automethod:: KrakenAPI.get_account_balance

Get Trade Balance
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trade_balance

Get Open Orders
--------------------------------------------------------
.. automethod:: KrakenAPI.get_open_orders

Get Closed Orders
--------------------------------------------------------
.. automethod:: KrakenAPI.get_closed_orders

Query Orders Info
--------------------------------------------------------
.. automethod:: KrakenAPI.query_orders_info

Get Trades History
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trades_history

Query Trades Info
--------------------------------------------------------
.. automethod:: KrakenAPI.query_trades_info

Get Open Positions
--------------------------------------------------------
.. automethod:: KrakenAPI.get_open_positions

Get Ledgers Info
--------------------------------------------------------
.. automethod:: KrakenAPI.get_ledgers_info

Query Ledgers
--------------------------------------------------------
.. automethod:: KrakenAPI.query_ledgers

Get Trade Volume
--------------------------------------------------------
.. automethod:: KrakenAPI.get_trade_volume

Request Export Report
--------------------------------------------------------
.. automethod:: KrakenAPI.request_export_report

Get Export Report Status
--------------------------------------------------------
.. automethod:: KrakenAPI.get_export_report_status

Retrieve Export Report
--------------------------------------------------------
.. automethod:: KrakenAPI.retrieve_export_report

Delete Export Report
--------------------------------------------------------
.. automethod:: KrakenAPI.delete_export_report




Private User Trading
========================================================

Add Standard Order
--------------------------------------------------------
.. automethod:: KrakenAPI.add_standard_order

Cancel Order
--------------------------------------------------------
.. automethod:: KrakenAPI.cancel_order

Cancel All Orders
--------------------------------------------------------
.. automethod:: KrakenAPI.cancel_all_orders

Cancel All Orders After X
--------------------------------------------------------
.. automethod:: KrakenAPI.cancel_all_orders_after




Private User Funding
========================================================

Get Deposit Methods
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_methods

Get Deposit Addresses
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_addresses

Get Status Of Recent Deposits
--------------------------------------------------------
.. automethod:: KrakenAPI.get_deposit_status

Get Withdrawal Information
--------------------------------------------------------
.. automethod:: KrakenAPI.get_withdrawal_info

Withdraw Funds
--------------------------------------------------------
.. automethod:: KrakenAPI.withdraw_funds

Get Status Of Recent Withdrawals
--------------------------------------------------------
.. automethod:: KrakenAPI.get_withdrawal_status

Request Withdrawal Cancelation
--------------------------------------------------------
.. automethod:: KrakenAPI.request_withdrawal_cancel

Wallet Transfer
--------------------------------------------------------
.. automethod:: KrakenAPI.wallet_transfer_to_futures




Private User Staking
========================================================

Stake Asset
--------------------------------------------------------
.. automethod:: KrakenAPI.stake_asset

Unstake Asset
--------------------------------------------------------
.. automethod:: KrakenAPI.unstake_asset

Get Stakeable Assets
--------------------------------------------------------
.. automethod:: KrakenAPI.get_stakeable_assets

Get Pending Staking Transactions
--------------------------------------------------------
.. automethod:: KrakenAPI.get_pending_staking_transactions

Get Staking Transactions
--------------------------------------------------------
.. automethod:: KrakenAPI.get_staking_transactions




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
