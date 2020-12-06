# This file is part of krakipy.
#
# krakipy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public market data License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# krakipy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public market data License for more details.
#
# You should have received a copy of the GNU Lesser
# General Public market data LICENSE along with krakipy. If not, see
# <http://www.gnu.org/licenses/lgpl-3.0.txt> and
# <http://www.gnu.org/licenses/gpl-3.0.txt>.


from pandas import to_datetime, DataFrame, Series, concat
from torpy.http.adapter import TorHttpAdapter
from datetime import datetime, timedelta
from requests import Session, HTTPError
from base64 import b64encode, b64decode
from torpy.client import TorClient
from urllib.parse import urlencode
from hashlib import sha256, sha512
from time import time, sleep
from functools import wraps 
from pyotp import TOTP
from hmac import new

from . import version

def callratelimiter(increment):
    def call(func):
        @wraps(func)
        def retry_decorator(*args, **kwargs):
            self = args[0]
            self._update_api_counter()
            try_number = 1
            while self.api_counter < self.limit-1:
                try:
                    if self.use_tor:
                        if self.counter % self.tor_refresh == 0:
                            self.session.new()
                    self.api_counter += increment
                    result = func(*args, **kwargs)
                    return result
                except HTTPError as err:
                    print(f"Attempt: {try_number:_>3}")
                    try_number += 1
                    sleep(self.retry * increment)
                    self._update_api_counter()
                    continue
            raise CallRateLimitError(f"Call rate limiter exceeded: counter={self.api_counter} limit={self.limit}")
        return retry_decorator
    return call


class KrakenAPIError(Exception):
    pass
class CallRateLimitError(Exception):
    pass

class Dark_Session(object):
    def __init__(self, use_tor=False):
        self.use_tor = use_tor
        if use_tor:
            self._tor = TorClient()
        self.new()

    def new(self):
        if self.use_tor:
            self._guard = self._tor.get_guard()
            adapter = TorHttpAdapter(self._guard, 3, retries=0)
            self.session = Session()
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        else:
            self.session = Session()

    def get_ip(self):
        return self.session.get("http://httpbin.org/ip").json()["origin"]
            
    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)
        
    def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)
        
    def close(self):
        self.session.close()
        if self.use_tor:
            self._guard.close()
        self.session = None
        self._guard = None


class KrakenAPI(object):
    """The KrakenAPI object stores the authentification information"""

    def __init__(self, key="", secret_key="", use_2fa=None, use_tor=False, tor_refresh=5, retry=0.5, limit=20):
        """
        Creates an object that holds the authentification information.
        The keys are only needed to perform private queries
        
        :param key: the key to the Kraken API (optional)
        :type key: str
        :param secret_key: the secret key to the Kraken API (optional)
        :type secret_key: str
        :param use_2fa: used to pass the desired two factor authentification (optional)
            
            - None = no two factor authentification (default)
            - {"static password": your_static_2fa_password} = two factor authentification using a static password method. Example: use_2fa={"static password": "/&59s^wqUU=baQ~W"}
            - {"2FA App": your_2fa_app_setup_key} = two factor authentification using the Google Authenticator App method. Example: use_2fa={"2FA App": "E452ZYHEX22AXGKIFUGQVPXF"}
        
        :type use_2fa: None or dict
        :param use_tor: weither or not to use the tor network for requests (optional)

            - False = use normal requests using the clearnet (default)
            - True = use tor requests using the darknet

        :type use_tor: bool
        :param tor_refresh: amount of requests per session before the IP is changed (optional) default = 5
        :type tor_refresh: int
        :param retry: the amount of time between retries (optional)
        :type retry: float
        :param limit: the maximum amount of retries (optional)
        :type limit: int
        """
        self.auth_method = None
        self._authentification = None
        if use_2fa:
            assert len(use_2fa) == 1, "There can only be one authentification method per API-token."
            authentification_methods = {"static password": self._auth_static_password, "2FA App": self._auth_2fa_app}
            types = authentification_methods.keys()
            method = list(use_2fa.keys())[0]
            assert method in types, f"The authentification method called {method} is not supported. Only {types} are supported."
            assert type(use_2fa[method]) == str, f"The 2FA pasword has to be a string. {use_2fa[method]} is not a string."
            self.auth_method = method
            self._authentification = {"method": authentification_methods[method], "password_2fa": use_2fa[method]}

        self._key = key
        self._secret = secret_key
         
        self.uri = "https://api.kraken.com"
        self.apiversion = "0"
        self.session = Dark_Session(use_tor)
        self.use_tor = use_tor
        if not use_tor:
            self.session.session.headers.update({"User-Agent": "krakipy/" + version.__version__ + " (+" + version.__url__ + ")"})
        else:
            self.tor_refresh = tor_refresh
        self.response = None

        self.time_of_last_query = time()
        self.api_counter = 0
        self.counter = 0
        self.limit = limit
        self.retry = retry

    def _auth_static_password(self):
        return self._authentification["password_2fa"]

    def _auth_2fa_app(self):
        return TOTP(self._authentification["password_2fa"]).now()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def __del__(self):
        self.session.close()

    def close(self):
        """ Closes the session
        """
        self.session.close()

    def __str__(self):
        return f"[{__class__.__name__}]\nVERSION:         {self.apiversion}\nURI:             {self.uri}\nAPI-Key:         {'*' * len(self._key) if self._key else '-'}\nAPI-Secretkey:   {'*' * len(self._secret) if self._secret else '-'}\nAPI-2FA-method:  {self.auth_method}\nAPI-Counter:     {self.api_counter}\nUsing Tor:       {self.use_tor}\nRequest-Counter: {self.counter}\nRequest-Limit:   {self.limit}\nRequest-Retry:   {self.retry} s"

    def _nonce(self):
        return int(1000*time())

    def _sign(self, data, urlpath):
        encoded = (str(data["nonce"]) + urlencode(data)).encode()
        message = urlpath.encode() + sha256(encoded).digest()

        signature = new(b64decode(self._secret), message, sha512)
        sigdigest = b64encode(signature.digest())

        return sigdigest.decode()
    
    def _query(self, urlpath, data, headers=None, timeout=None):
        if data is None:
            data = {}
        if headers is None:
            headers = {}

        self.response = self.session.post(self.uri + urlpath, data = data, headers = headers, timeout = timeout)
        self.counter += 1
        if self.response.status_code not in (200, 201, 202):
            self.response.raise_for_status()
        try:
            result = self.response.json()
        except:
            result = {"result":self.response.content, "error": []}

        return result


    def _query_public(self, method, data=None, timeout=None):
        urlpath = "/" + self.apiversion + "/public/" + method
        return self._query(urlpath, data, timeout = timeout)


    def _query_private(self, method, data=None, timeout=None):
        if not self._key or not self._secret:
            raise Exception("The Key or Secret-Key is not set!")
        if data is None:
            data = {}

        urlpath = "/" + self.apiversion + "/private/" + method
        data["nonce"] = self._nonce()
        if self._authentification != None:
            data["otp"] = self._authentification["method"]()
        headers = {"API-Key": self._key, "API-Sign": self._sign(data, urlpath)}
        return self._query(urlpath, data, headers, timeout = timeout)

    def _do_public_request(self, action, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        res = self._query_public(action, data = kwargs)
        _check_error(res)
        return res["result"]

    def _do_private_request(self, action, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        res = self._query_private(action, data = kwargs)
        _check_error(res)
        return res["result"]

    @callratelimiter(1)
    def get_server_time(self):
        """
        Public market data

        Returns the time of the Kraken API server.
        
        Example: ("Sun,  6 Dec 20 14:12:39 +0000", 1607263959)

        :returns: rfc1123 and unixtime
        :rtype: (str, int)
        """
        res = self._query_public("Time")
        _check_error(res)
        return res["result"]["rfc1123"], res["result"]["unixtime"]

    @callratelimiter(1)
    def get_system_status(self):
        """
        Public market data

        Returns the current system status or trading mode and a timestamp.
        
        Example: ("online", "2020-12-06T13:59:55Z")

        :returns: system status and timestamp
        :rtype: (str, str)

        .. note::

        	Possible status values include:

				- "online" (operational, full trading available)
				- "cancel_only" (existing orders are cancelable, but new orders cannot be created)
				- "post_only" (existing orders are cancelable, and only new post limit orders can be submitted)
				- "limit_only" (existing orders are cancelable, and only new limit orders can be submitted)
				- "maintenance" (system is offline for maintenance)

        """
        res = self._query_public("SystemStatus")
        _check_error(res)
        return res["result"]["status"], res["result"]["timestamp"]

    @callratelimiter(1)
    def get_asset_info(self, info=None, aclass=None, asset=None):
        """
        Public market data

        :param info: the info to retrieve (optional) - default = "all"
        :type info: str
        :param aclass: the asset class (optional) - default = "currency"
        :type aclass: str
        :param asset: a comma delimited list of assets to get info on (optional) - default = "all"
        :type asset: str

        :returns: A DataFrame of asset names and their info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        return DataFrame(self._do_public_request("Assets", info=info, aclass = aclass, asset = asset)).T

    @callratelimiter(1)
    def get_tradable_asset_pairs(self, info=None, pair=None):
        """
        Public market data

        :param info: the info to retrieve (optional)

            - info = all info (default)
            - leverage = leverage info
            - fees = fees schedule
            - margin = margin info

        :type info: str
        :param pair: comma delimited list of asset pairs to get info on (optional) - default = "all"
        :type pair: str

        :returns: A DataFrame of pair names and their info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        return DataFrame(self._do_public_request("AssetPairs", info=info, pair=pair)).T

    @callratelimiter(1)
    def get_ticker_information(self, pair):
        """
        Public market data

        :param pair: a comma delimited list of asset pairs to get info on
        :type pair: str

        :returns: A DataFrame of pair names and their ticker info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        return DataFrame(self._do_public_request("Ticker", pair=pair)).T

    @callratelimiter(1)
    def get_open_positions(self, txid=None, docalcs=False, consolidation=None):
        """
        Private user data

        :param txid: comma delimited list of transaction ids to restrict output to
        :type txid: str
        :param docalcs: whether or not to include profit/loss calculations (optional) - default = False
        :type docalcs: bool
        :param consolidation: what to consolidate the positions data around (optional) - "market" = will consolidate positions based on market pair
        :type consolidation: str

        :returns: A DataFrame of open position info
        :rtype: :py:attr:`pandas.DataFrame`

        .. note::

            Using the consolidation optional field will result in consolidated view of the data being returned.
        """
        return self._do_private_request("OpenPositions", txid=txid, docalcs=docalcs, consolidation=consolidation)

    def cancel_open_order(self, txid):
        """
        Private user trading

        :param txid: transaction id
        :type txid: str

        :returns: number of orders canceled and weither order(s) is/are pending cancellation
        :rtype: (int, bool)
        """
        data = self._do_private_request("CancelOrder", txid=txid)
        return data["count"], data["pending"]

    def cancel_all_open_orders(self):
        """
        Private user trading

        :returns: number of orders canceled
        :rtype: int
        """
        data = self._do_private_request("CancelAll")
        return int(data["count"])

    @callratelimiter(1)
    def get_withdrawal_info(self, asset, key, amount, aclass="currency"):
        """
        Private user funding
        
        :param asset: asset being withdrawn
        :type asset: str
        :param key: withdrawal key name, as set up on your account
        :type key: str
        :param amount: amount to withdraw
        :type amount: float
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str

        :returns: Dictionary of associative withdrawal info
        :rtype: dict
        """
        return self._do_private_request("WithdrawInfo", asset=asset, aclass=aclass, key=key, amount=amount)

    def withdraw_funds(self, asset, amount, key, aclass="currency"):
        """
        Private user funding

        :param asset: asset being withdrawn
        :type asset: str
        :param key: withdrawal key name, as set up on your account
        :type key: str
        :param amount: amount to withdraw
        :type amount: float
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str
        
        :returns: reference id
        :rtype: str
        """
        return self._do_private_request("Withdraw", asset=asset, key=key, amount=float(amount), aclass=aclass)["refid"]

    @callratelimiter(1)
    def get_withdrawal_status(self, asset):
        """
        Private user funding

        :param asset: asset being withdrawn
        :type asset: str

        :returns: Dictionary of withdrawal status information
        :rtype: dict
        """
        return self._do_private_request("WithdrawStatus", asset=asset)

    @callratelimiter(1)
    def request_withdrawal_cancel(self, refid, asset, aclass = "currency"):
        """
        Private user funding

        :param asset: asset being withdrawn
        :type asset: str
        :param refid: withdrawal reference id
        :type refid: str
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str

        :returns: True on success:
        :rtype: bool

        .. note::

            **Cancelation cannot be guaranteed.** This will put in a cancelation request. Depending upon how far along the withdrawal process is, it may not be possible to cancel the withdrawal.
        """
        return self._do_private_request("WithdrawCancel", asset=asset, aclass=aclass, refid=refid)

    @callratelimiter(1)
    def get_deposit_status(self, asset, method, aclass):
        """
        Private user funding

        :param asset: asset being deposited
        :type asset: str
        :param method: name of the deopsit method
        :type method: str
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str

        :returns: Dictionary of deposit status information
        :rtype: dict
        """
        return self._do_private_request("DepositStatus", asset=asset)

    @callratelimiter(1)
    def get_deposit_addresses(self, asset, method, aclass=None, new=False):
        """
        Private user funding

        :param asset: asset being deposited
        :type asset: str
        :param method: name of the deopsit method
        :type method: str
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str
        :param new: whether or not to generate a new address (optional.  default = false)
        :type new: bool

        :returns: Dictionary of associative deposit addresses
        :rtype: dict
        """
        return self._do_private_request("DepositAddresses", asset=asset, method=method, new=new)

    @callratelimiter(1)
    def get_deposit_methods(self, asset, aclass=None):
        """
        Private user funding

        :param asset: asset being deposited
        :type asset: str
        :param aclass: asset class (optional) - default = "currency"
        :type aclass: str

        :returns: Dictionary of deposit methods:
        :rtype: dict
        """
        return self._do_private_request("DepositMethods", asset=asset, aclass=aclass)

    @callratelimiter(1)
    def wallet_transfer(self, asset, to_address, from_address, amount):
        """
        Private user funding

        :param asset: asset being withdrawn
        :type asset: str
        :param to_address: which wallet the funds are being transferred to

            - Futures Wallet (default)
            - Spot Wallet

        :type to_address: str
        :param from_address: which wallet the funds are being transferred from

            - Futures Wallet
            - Spot Wallet (default)

        :type from_address: str
        :param amount: amount to withdraw
        :type amount: float
        
        :returns: reference id
        :rtype: str
        """
        data = {"asset": asset,"to": to_address, "from": from_address, "amount": amount} 
        res = self._query_private("WalletTransfer", data)
        _check_error(res)
        return res["result"]["refid"]

    def request_export_report(self, description, report, data_format="CSV", fields=None, asset=None, starttm=None, endtm=None):
        """
        Private user data

        :param description: report description info
        :type description: str
        :param report: report type

            - trades
            - ledgers

        :type report: str
        :param data_format: the data format

            - CSV (default)
            - TSV

        :type data_format: str
        :param fields: comma delimited list of fields to include in report (optional).  default = "all" 

            trades:

                - ordertxid
                - time
                - ordertype
                - price
                - cost
                - fee
                - vol
                - margin
                - misc
                - ledgers

            ledgers:

                - refid
                - time
                - type
                - aclass
                - asset
                - amount
                - fee
                - vbalance

        :type fields: str
        :param asset: comma delimited list of assets to get info on (optional) - default = "all"
        :type asset: str
        :param starttm: report start unixtime (optional).  default = one year before now
        :type starttm: int
        :param endtm: report end unixtime (optional).  default = now
        :type endtm: int

        :returns: report id
        :rtype: str

        .. note:: 

            Field options are based on report type.
        """
        return self._do_private_request("AddExport", report=report, description=description, format=data_format, fields=fields, asset=asset, starttm=starttm, endtm=endtm)["id"]

    @callratelimiter(1)
    def get_export_statuses(self, report):
        """
        Private user data

        :param report: report type:

            - trades
            - ledgers

        :type report: str

        :returns: Dictionary of reports and their info
        :rtype: dict
        """
        return self._do_private_request("ExportStatus", report=report)

    @callratelimiter(1)
    def remove_export_report(self, remove_type, report_id):
        """
        Private user data

        :param remove_type: remove type

            - cancel
            - delete

        :type remove_type: str
        :param report_id: report id
        :type report_id: str

        :returns: returns remove type
        :rtype: bool

        .. note::

            The delete remove type can only be used for a report that has already been processed. Use cancel for queued and processing statuses.
        """
        return self._do_private_request("RemoveExport", id=report_id, type=remove_type)

    @callratelimiter(2)
    def get_ohlc_data(self, pair, interval=1, since=None):
        """
        Public market data

        :param pair: a asset pair to get OHLC data for
        :type pair: str
        :param interval: the time frame interval in minutes (optional):

            - 1 (default) = 1 minute
            - 5 = 5 minutes
            - 15 = 15 minutes
            - 30 = 30 minutes
            - 60 = 1 hour
            - 240 = 4 hours
            - 1440 = 1 day
            - 10080 = 1 week
            - 21600 = 15 days

        :type interval: int
        :param since: return committed OHLC data since given id (optional.  exclusive)
        :type since: int

        :returns: A DataFrame of pair name and OHLC data
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_public_request("OHLC", pair=pair, interval=interval, since=since)
        ohlc = DataFrame(res[pair], dtype="float")
        last = int(res["last"])

        if not ohlc.empty:
            ohlc.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
            ohlc["time"] = ohlc["time"].astype(int)
        return ohlc, last

    @callratelimiter(1)
    def get_order_book(self, pair, count=100):
        """
        Public market data

        :param pair: asset pair to get market depth for
        :type pair: str
        :param count: maximum number of asks/bids (optional) - default = 100
        :type count: int

        :returns: ask and bid DataFrame of pair name and market depth
        :rtype: (:py:attr:`pandas.DataFrame`, :py:attr:`pandas.DataFrame`)
        """
        res = self._do_public_request("Depth", pair=pair, count=count)
        cols = ["price", "volume", "time"]
        asks = DataFrame(res[pair]["asks"], columns=cols, dtype="float")
        bids = DataFrame(res[pair]["bids"], columns=cols, dtype="float")
        asks["time"] = asks["time"].astype(int)
        bids["time"] = bids["time"].astype(int)
        return asks, bids

    @callratelimiter(2)
    def get_recent_trades(self, pair, since=None):
        """
        Public market data

        :param pair: a asset pair to get trade data for
        :type pair: str
        :param since: return trade data since given id (optional.  exclusive)
        :type since: int

        :returns: DataFrame of pair name and recent trade data and id to be used as since when polling for new trade data.
        :rtype: (:py:attr:`pandas.DataFrame`, int)
        """
        res = self._do_public_request("Trades", pair=pair, since=since)
        trades = DataFrame(res[pair])
        last = int(res["last"])

        if not trades.empty:
            trades.columns = ["price", "volume", "time", "buy_sell", "market_limit", "misc"]
            trades = trades.astype({"price": float, "volume": float, "time": int})
        return trades, last

    @callratelimiter(1)
    def get_recent_spread_data(self, pair, since=None):
        """
        Public market data

        :param pair: a asset pair to get spread data for
        :type pair: str
        :param since: return trade data since given id (optional.  exclusive)
        :type since: int

        :returns: DataFrame of pair name and recent spread data and id to be used as since when polling for new spread data
        :rtype: (:py:attr:`pandas.DataFrame`, int)        
        """
        res = self._do_public_request("Spread", pair=pair, since=since)
        spread = DataFrame(res[pair], columns=["time", "bid", "ask"], dtype="float")
        last = int(res["last"])
        spread["time"] = spread.time.astype(int)
        spread["spread"] = spread.ask - spread.bid
        return spread, last

    @callratelimiter(1)
    def get_account_balance(self):
        """
        Private user data

        :returns: DataFrame of asset names and balance amount
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("Balance")
        balance = DataFrame(res, index=["vol"], dtype="float").T
        return balance

    @callratelimiter(2)
    def get_trade_balance(self, aclass="currency", asset="ZEUR"):
        """
        Private user data

        :param aclass: an asset class (optional) - default = "currency" 
        :type aclass: str
        :param asset: a base asset used to determine balance - default = "ZEUR"
        :type asset: str

        :returns: DataFrame of trade balance info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("TradeBalance", aclass=aclass, asset=asset)
        tradebalance = DataFrame(res, index=[asset], dtype="float").T
        return tradebalance

    @callratelimiter(1)
    def get_open_orders(self, trades=False, userref=None):
        """
        Private user data

        :param trades: whether or not to include trades in output (optional) - default = false
        :type trades: bool
        :param userref: restrict results to given user reference id (optional)
        :type userref: str

        :returns: DataFrame of open order info with txid as the index
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("OpenOrders", trades=trades, userref=userref)
        openorders = DataFrame(res["open"]).T
        if not openorders.empty:
            openorders[["expiretm", "opentm", "starttm"]] = openorders[["expiretm", "opentm", "starttm"]].astype(int)
            openorders[["cost", "fee", "price", "vol", "vol_exec"]] = openorders[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return openorders

    @callratelimiter(1)
    def get_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime=None):
        """
        Private user data

        :param trades: whether or not to include trades in output (optional) - default = false
        :type trades: bool
        :param userref: restrict results to given user reference id (optional)
        :type userref: str
        :param start: starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: the result offset
        :type ofs: int
        :param closetime: which time to use (optional):

            - open
            - close
            - both (default)

        :type closetime: str
        
        :returns: DataFrame of of order info and amount of available order info matching criteria
        :rtype: (:py:attr:`pandas.DataFrame`, int)
        """
        res = self._do_private_request("ClosedOrders", trades=trades, userref=userref, start=start, end=end, ofs=ofs, closetime=closetime)
        closed = DataFrame(res["closed"]).T
        count = int(res["count"])
        if not closed.empty:
            closed[["closetm", "expiretm", "opentm", "starttm"]] = closed[["closetm", "expiretm", "opentm", "starttm"]].astype(int)
            closed[["cost", "fee", "price", "vol", "vol_exec"]] = closed[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return closed, count

    @callratelimiter(1)
    def query_orders_info(self, txid, trades=False, userref=None):
        """
        Private user data
            
        :param trades: whether or not to include trades in output (optional) - default = false
        :type trades: bool
        :param userref: restrict results to given user reference id (optional)
        :type userref: str
        :param txid: comma delimited list of transaction ids to query info about (50 maximum)
        :type txid: str

        :returns: DataFrame of associative orders info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("QueryOrders", txid=txid, trades=trades, userref=userref)
        orders = DataFrame(res).T

        if not orders.empty:
            orders[["closetm", "expiretm", "opentm", "starttm"]] = orders[["closetm", "expiretm", "opentm", "starttm"]].astype(int)
            orders[["cost", "fee", "price", "vol", "vol_exec"]] = orders[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return orders

    @callratelimiter(2)
    def get_trades_history(self, trade_type="all", trades=False, start=None, end=None, ofs=None):
        """
        Private user data

        :param trade_type: type of trade (optional):

            - all = all types (default)
            - any position = any position (open or closed)
            - closed position = positions that have been closed
            - closing position = any trade closing all or part of a position
            - no position = non-positional trades

        :type trade_type: str
        :param trades: whether or not to include trades related to position in output (optional) - default = false
        :type trades: bool
        :param start: starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: the result offset
        :type ofs: int

        :returns: DataFrame of trade info and the amount of available trades info matching criteria
        :rtype: (:py:attr:`pandas.DataFrame`, int)
        """
        res = self._do_private_request("TradesHistory", trades=trades, start=start, end=end, ofs=ofs, type=trade_type)
        trades = DataFrame(res["trades"]).T
        count = int(res["count"])
        if not trades.empty:
            trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)
        return trades, count

    @callratelimiter(2)
    def query_trades_info(self, txid, trades=False):
        """
        Private user data
        
        :param txid: comma delimited list of transaction ids to query info about (20 maximum)
        :type txid: str
        :param trades: whether or not to include trades related to position in output (optional) - default = false
        :type trades: bool
        
        :returns: DataFrame of associative trades info
        :rtype: (:py:attr:`pandas.DataFrame`, int)
        """
        res = self._do_private_request("QueryTrades", txid=txid, trades=trades)
        trades = DataFrame(res).T
        if not trades.empty:
            trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)
        return trades

    @callratelimiter(2)
    def get_ledgers_info(self, aclass=None, asset=None, selection_type="all", start=None, end=None, ofs=None):
        """
        Private user data

        :param aclass: an asset class (optional) - default = "currency"
        :type aclass: str
        :param asset: comma delimited list of assets to restrict output to (optional) - default = "all"
        :type asset: str
        :param selection_type: type of trade (optional):

            - all (default)
            - deposit
            - withdrawal
            - trade
            - margin

        :type selection_type: str
        :param start: starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: the result offset
        :type ofs: int

        :returns: DataFrame of associative ledgers info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("Ledgers", aclass=aclass, asset=asset, type=selection_type, start=start, end=end, ofs=ofs)
        ledgers = DataFrame(res["ledger"]).T
        if not ledgers.empty:
            ledgers[["amount", "balance", "fee"]] = ledgers[["amount", "balance", "fee"]].astype(float)
            ledgers["time"] = ledgers["time"].astype(int)
        return ledgers

    @callratelimiter(2)
    def query_ledgers(self, id):
        """
        Private user data

        :param id: comma delimited list of ledger ids to query info about (20 maximum)
        :type id: str

        :returns: DataFrame of associative ledgers info
        :rtype: :py:attr:`pandas.DataFrame`        
        """
        res = self._do_private_request("QueryLedgers", id=id)
        ledgers = DataFrame(res).T
        if not ledgers.empty:
            ledgers[["amount", "balance", "fee"]] = ledgers[["amount", "balance", "fee"]].astype(float)
            ledgers["time"] = ledgers["time"].astype(int)
        return ledgers

    @callratelimiter(2)
    def get_trade_volume(self, pair):
        """
        Private user data

        :param pair: comma delimited list of asset pairs to get fee info on (optional)
        :type pair: str
        
        :returns: The volume currency, current discount volume, DataFrame of fees and DataFrame of maker fees
        :rtype: (str, float, :py:attr:`pandas.DataFrame`, :py:attr:`pandas.DataFrame`)
        """
        res = self._do_private_request("TradeVolume", pair=pair)

        currency = res["currency"]
        volume = float(res["volume"])
        keys = res.keys()
        fees = DataFrame(res["fees"]) if "fees" in keys else None
        fees_maker = DataFrame(res["fees_maker"]) if "fees_maker" in keys else None
        return currency, volume, fees, fees_maker


    def add_standard_order(self, pair, type, ordertype, volume, price=None,
                           price2=None, leverage=None, oflags=None, starttm=0,
                           expiretm=0, userref=None, validate=True,
                           close_ordertype=None, close_price=None,
                           close_price2=None, trading_agreement="agree"):
        """
        Private user trading

        :param pair: asset pair
        :type pair: str
        :param type: type of order

            - buy
            - sell

        :type type: str
        :param ordertype: order type:

            - market
            - limit (price = limit price)
            - stop-loss (price = stop loss price)
            - take-profit (price = take profit price)
            - stop-loss-profit (price = stop loss price, price2 = take profit price)
            - stop-loss-profit-limit (price = stop loss price, price2 = take profit price)
            - stop-loss-limit (price = stop loss trigger price, price2 = triggered limit price)
            - take-profit-limit (price = take profit trigger price, price2 = triggered limit price)
            - trailing-stop (price = trailing stop offset)
            - trailing-stop-limit (price = trailing stop offset, price2 = triggered limit offset)
            - stop-loss-and-limit (price = stop loss price, price2 = limit price)
            - settle-position

        :type ordertype: str
        :param volume: order volume in lots
        :type volume: float
        :param price: price (optional.  dependent upon ordertype)
        :type price: float or int
        :param price2: secondary price (optional.  dependent upon ordertype)
        :type price2: float or int
        :param leverage: amount of leverage desired (optional.  default = none)
        :type leverage: int
        :param oflags: comma delimited list of order flags (optional):

            - viqc = volume in quote currency (not available for leveraged orders)
            - fcib = prefer fee in base currency
            - fciq = prefer fee in quote currency
            - nompp = no market price protection
            - post = post only order (available when ordertype = limit)

        :type oflags: str
        :param starttm: scheduled start time (optional):

            - 0 = now (default)
            - +<n> = schedule start time <n> seconds from now
            - <n> = unix timestamp of start time

        :type starttm: int
        :param expiretm: expiration time (optional):

            - 0 = no expiration (default)
            - +<n> = expire <n> seconds from now
            - <n> = unix timestamp of expiration time
            
        :type expiretm: int
        :param userref: user reference id. 32-bit signed number.  (optional)
        :type userref: str
        :param validate: validate inputs only. do not submit order (optional)
        :type validate: bool
        :param close_ordertype: optional closing order to add to system when order gets filled: order type
        :type close_ordertype: str
        :param close_price: price
        :type close_price: float or int
        :param  close_price2: secondary price
        :type close_price2: float or int
        
        :returns: Dictionary of order description info
        :rtype: dict

        .. note::

            - See Get tradable asset pairs for specifications on asset pair prices, lots, and leverage.
            - Prices can be preceded by +, -, or # to signify the price as a relative amount (with the exception of trailing stops, which are always relative). + adds the amount to the current offered price. - subtracts the amount from the current offered price. # will either add or subtract the amount to the current offered price, depending on the type and order type used. Relative prices can be suffixed with a % to signify the relative amount as a percentage of the offered price.
            - For orders using leverage, 0 can be used for the volume to auto-fill the volume needed to close out your position.
            - If you receive the error "EOrder:Trading agreement required", refer to your API key management page for further details.
        """
        if validate is False:
            validate = None

        volume = str(volume)
        price = str(price) if price else None
        price2 = str(price2) if price2 else None
        leverage = str(leverage) if leverage else None
        close_price = str(close_price) if close_price else None
        close_price2 = str(close_price2) if close_price2 else None

        data = {arg: value for arg, value in locals().items() if
                arg != "self" and value is not None}
        if close_ordertype != None:
            data["close[ordertype]"] = data.pop("close_ordertype")

        if close_price != None:
            data["close[price]"] = data.pop("close_price")

        if close_price2 != None:
            data["close[price2]"] = data.pop("close_price2")

        res = self._query_private("AddOrder", data=data)
        _check_error(res)
        return res["result"]

    
    @callratelimiter(3)
    def get_export_report(self, report_id, return_raw=False, path=""):
        """
        Private user data
        
        :param report_id: report id
        :type report_id: str
        :param return_raw: weither or not the report is returned as raw binary or saved at path (optional) - default = False
        :type return_raw: bool
        :param path: the directory the report zipfile is saved
        :type path: str
        
        :returns: None
        """
        report = self._do_private_request("RetrieveExport", id=report_id)
        if return_raw:
            return report
        else:
            with open("{}Report_{}.zip".format(path, report_id), "wb") as f:
                f.write(report)

    def _update_api_counter(self):
        now = time()
        self.api_counter = max(0, self.api_counter - int(now - self.time_of_last_query))
        self.time_of_last_query = now



def add_dtime(df):
    """
    Extra

    Converts the column "time" (unixtime) and adds a new column "dtime" (datetime)

    :param df: A DataFrame with a column "time" in unixtime-format
    :type df: :py:attr:`pandas.DataFrame`

    :returns: df with a "dtime" column added
    :rtype: :py:attr:`pandas.DataFrame`
    """
    df["dtime"] = to_datetime(df.time, unit="s")
    return df

def _check_error(result):
    if len(result["error"]) > 0:
        raise KrakenAPIError(result["error"])

def datetime_to_unixtime(dt):
    """
    Extra

    Converts datetime to unixtime
    
    :param dt: datetime object
    :type dt: :py:attr:`datetime.datetime`

    :returns: the unixtime of dt
    :rtype: int
    """
    return int((dt - datetime(1970, 1, 1)).total_seconds())

def unixtime_to_datetime(ux):
    """
    Extra

    Converts unixtime to datetime 
    
    :param ux: unixtime timestamp
    :type ux: int

    :returns: the datetime of ux
    :rtype: :py:attr:`datetime.datetime`
    """
    return datetime(1970, 1, 1) + timedelta(0, ux)