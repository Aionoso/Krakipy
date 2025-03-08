# This file is part of krakipy.
#
#MIT LICENSE
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
#associated documentation files (the “Software”), to deal in the Software without restriction, including
#without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
#of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
#NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
#ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from pandas import to_datetime, DataFrame, Series, concat, json_normalize
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
            raise CallRateLimitError(f"Call rate limiter exceeded: counter={self.api_counter} limit={self.limit}. Please wait!")
        return retry_decorator
    return call


class KeyNotSetError(Exception):
    """This Error indicates that you tried to do a private request but did not set the Kraken API Keys."""
    pass

class KrakenAPIError(Exception):
    """This Error indicates that in the response to your query had an error message when it was recieved."""
    pass
    
class CallRateLimitError(Exception):
    """This Error indicates that you sent to many requests in the last 20s."""
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
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
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


def _check_error(result):
    if len(result["error"]) > 0:
        raise KrakenAPIError(result["error"])


class KrakenAPI(object):
    """The KrakenAPI object stores the authentification information"""

    def __init__(self, key="", secret_key="", use_2fa=None, use_tor=False, tor_refresh=5, retry=0.5, limit=20):
        """
        Creates an object that can hold the authentification information.
        The keys are only needed to perform private queries
        
        :param key: The key to the Kraken API (optional)
        :type key: str
        :param secret_key: The secret key to the Kraken API (optional)
        :type secret_key: str
        :param use_2fa: Is used to pass the desired two factor authentification (optional)
            
            - None = no two factor authentification (default)
            - {"static password": your_static_2fa_password} = two factor authentification using a static password method. Example: use_2fa={"static password": "/&59s^wqUU=baQ~W"}
            - {"2FA App": your_2fa_app_setup_key} = two factor authentification using OTP passwords like the Google Authenticator App does it. Example: use_2fa={"2FA App": "E452ZYHEX22AXGKIFUGQVPXF"}
        
        :type use_2fa: None or dict
        :param use_tor: Weither or not to use the tor network for requests (optional)

            - False = use normal requests using the clearnet (default)
            - True = use tor requests using the darknet

        :type use_tor: bool
        :param tor_refresh: Amount of requests per session before the IP is changed (optional) default = 5
        :type tor_refresh: int
        :param retry: Amount of time between retries in sec (optional)
        :type retry: float
        :param limit: The maximum amount of retries (optional)
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
        if self.session is not None:
            self.session.close()

    def __del__(self):
        if self.session is not None:
            self.session.close()
        del self._key
        del self._secret_key
        del self._authentification
        
    def close(self):
        """ Closes the session
        """
        if self.session is not None:
            self.session.close()

    def __str__(self):
        return f"""[{__class__.__name__}]\nVERSION:         {self.apiversion}\nURI:             {self.uri}\nAPI-Key:         {"*" * len(self._key) if self._key else "-"}\nAPI-Secretkey:   {"*" * len(self._secret) if self._secret else "-"}\nAPI-2FA-method:  {self.auth_method}\nAPI-Counter:     {self.api_counter}\nUsing Tor:       {self.use_tor}\nRequest-Counter: {self.counter}\nRequest-Limit:   {self.limit}\nRequest-Retry:   {self.retry} s"""

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
            raise KeyNotSetError("The Key and Secret-Key to the API need to be set to do private queries.")
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




    #Public Market Data
    @callratelimiter(1)
    def get_server_time(self):
        """
        Public Market Data

        Returns The time of the Kraken API server.
        

        :returns: Rfc1123 and unixtime
        :rtype: (str, int)

        Example: KrakenAPI.get_server_time() -> ("Sun,  6 Dec 20 14:12:39 +0000", 1607263959)
        """
        res = self._query_public("Time")
        _check_error(res)
        return res["result"]["rfc1123"], res["result"]["unixtime"]


    @callratelimiter(1)
    def get_system_status(self):
        """
        Public Market Data

        Returns the current system status or trading mode and a timestamp.


        :returns: The system status and timestamp
        :rtype: (str, str)

        Example: KrakenAPI.get_system_status() -> ("online", "2020-12-06T13:59:55Z")

        .. note::

            Possible status values include:

                - "online" (operational, full trading available)
                - "cancel_only" (existing orders are cancelable, but new orders cannot be created)
                - "post_only" (existing orders are cancelable, and only new post limit orders can be submitted)
                - "maintenance" (system is offline for maintenance)

        """
        res = self._query_public("SystemStatus")
        _check_error(res)
        return res["result"]["status"], res["result"]["timestamp"]


    @callratelimiter(1)
    def get_asset_info(self, asset=None, aclass=None):
        """
        Public Market Data

        Get information about the assets that are available for deposit, withdrawal, trading and staking.


        :param asset: Comma delimited list of assets to get info on (optional) - default = "all"
        :type asset: str
        :param aclass: Asset class (optional) - default = "currency"
        :type aclass: str

        :returns: DataFrame of asset names and their info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        info = DataFrame(self._do_public_request("Assets", asset=asset, aclass=aclass), index=["aclass", "altname", "decimals", "display_decimals"]).T
        info[["decimals", "display_decimals"]] = info[["decimals", "display_decimals"]].astype(int)
        return info


    @callratelimiter(1)
    def get_tradable_asset_pairs(self, pair=None, info=None):
        """
        Public Market Data


        :param info: The info to retrieve (optional)

            - info = all info (default)
            - leverage = leverage info
            - fees = fees schedule
            - margin = margin info

        :type info: str
        :param pair: Comma delimited list of asset pairs to get info on (optional) - default = "all"
        :type pair: str

        :returns: DataFrame of pair names and their info
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_public_request("AssetPairs", info=info, pair=pair)
        pairs =  DataFrame(res, index=["altname", "wsname", "aclass_base", "base", "aclass_quote", "quote", "lot", "pair_decimals", "lot_decimals", "lot_multiplier", "leverage_buy", "leverage_sell", "fees", "fees_maker", "fee_volume_currency", "margin_call", "margin_stop", "ordermin"]).T

        pairs[["pair_decimals", "lot_decimals", "margin_call", "margin_stop"]] = pairs[["pair_decimals", "lot_decimals", "margin_call", "margin_stop"]].astype(int)
        pairs[["lot_multiplier", "ordermin"]] = pairs[["lot_multiplier", "ordermin"]].astype(float)
        return pairs

    @callratelimiter(1)
    def get_ticker_information(self, pair):
        """
        Public Market Data


        :param pair: Comma delimited list of asset pairs to get info on
        :type pair: str

        :returns: DataFrame of pair names and their ticker info
        :rtype: :py:attr:`pandas.DataFrame`
        
        .. note::
            
            Today"s prices start at midnight UTC
        """
        return DataFrame(self._do_public_request("Ticker", pair=pair), index=["a", "b", "c", "h", "l", "o", "p", "t", "v"]).T


    @callratelimiter(2)
    def get_ohlc_data(self, pair, interval=1, since=None):
        """
        Public Market Data

        :param pair: Asset pair to get OHLC data for
        :type pair: str
        :param interval: The time frame interval in minutes (optional):

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
        :param since: Return committed OHLC data since given id (optional.  exclusive)
        :type since: int

        :returns: DataFrame of pair name and OHLC data
        :rtype: :py:attr:`pandas.DataFrame`

        .. note::

            The last entry in the OHLC array is for the current, not-yet-committed frame and will always be present, regardless of the value of since.
        """
        res = self._do_public_request("OHLC", pair=pair, interval=interval, since=since)
        ohlc = DataFrame(res[pair], columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"], dtype="float")

        last = float(res["last"])
        return ohlc, last


    @callratelimiter(1)
    def get_order_book(self, pair, count=100):
        """
        Public Market Data

        :param pair: Asset pair to get market depth for
        :type pair: str
        :param count: Maximum number of asks/bids (optional) - default = 100, Range: [1..500]
        :type count: int

        :returns: Ask and bid DataFrame of pair name and market depth
        :rtype: (:py:attr:`pandas.DataFrame`, :py:attr:`pandas.DataFrame`)
        """
        res = self._do_public_request("Depth", pair=pair, count=count)
        cols = ["price", "volume", "time"]
        asks = DataFrame(res[pair]["asks"], columns=cols, dtype="float")
        bids = DataFrame(res[pair]["bids"], columns=cols, dtype="float")
        return asks, bids


    @callratelimiter(2)
    def get_recent_trades(self, pair, since=None):
        """
        Public Market Data

        Returns the last 1000 trades by default


        :param pair: Asset pair to get trade data for
        :type pair: str
        :param since: Return trade data since given id (optional.  exclusive)
        :type since: int

        :returns: DataFrame of pair name and recent trade data and id to be used as since when polling for new trade data.
        :rtype: (:py:attr:`pandas.DataFrame`, int)
        """
        res = self._do_public_request("Trades", pair=pair, since=since)
        trades = DataFrame(res[pair], columns=["price", "volume", "time", "buy_sell", "market_limit", "misc"], dtype="float")

        last = float(res["last"])
        return trades, last


    @callratelimiter(1)
    def get_recent_spreads(self, pair, since=None):
        """
        Public Market Data

        :param pair: Asset pair to get spread data for
        :type pair: str
        :param since: Return trade data since given id (optional.  exclusive)
        :type since: int

        :returns: DataFrame of pair name and recent spread data and id to be used as since when polling for new spread data
        :rtype: (:py:attr:`pandas.DataFrame`, int)        
        """
        res = self._do_public_request("Spread", pair=pair, since=since)
        spread = DataFrame(res[pair], columns=["time", "bid", "ask"], dtype="float")
        spread["time"] = spread.time.astype(float)
        spread["spread"] = spread.ask - spread.bid

        last = float(res["last"])
        return spread, last





    #Private User Data
    @callratelimiter(1)
    def get_account_balance(self):
        """
        Private User Data

        Retrieve all cash balances, net of pending withdrawals.

        :returns: DataFrame of asset names and balance amount
        :rtype: :py:attr:`pandas.DataFrame`

        
        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("Balance")
        balance = DataFrame(res, index=["vol"], dtype="float").T
        return balance


    @callratelimiter(1)
    def get_extended_balance(self):
        """
        Private User Data

        Retrieve all extended account balances, including credits and held amounts. Balance available for trading is calculated as: available balance = balance + credit - credit_used - hold_trade


        :returns: DataFrame of asset names and balance amount
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("BalanceEx")
        balance = DataFrame(res, dtype="float").T
        return balance


    @callratelimiter(2)
    def get_trade_balance(self, asset="ZEUR"):
        """
        Private User Data

        Retrieve a summary of collateral balances, margin position valuations, equity and margin level.


        :param asset: Base asset used to determine balance - default = "ZEUR"
        :type asset: str

        :returns: DataFrame of trade balance info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query open orders & trades**
        """
        res = self._do_private_request("TradeBalance", asset=asset)
        tradebalance = DataFrame(res, index=[asset], columns=["eb", "tb", "m", "n", "c", "v", "e", "mf", "ml"], dtype="float")
        return tradebalance


    @callratelimiter(1)
    def get_open_orders(self, trades=False, userref=None):
        """
        Private User Data

        Retrieve information about currently open orders.


        :param trades: Whether or not to include trades in output (optional) - default = False
        :type trades: bool
        :param userref: Restrict results to given user reference id (optional)
        :type userref: str

        :returns: DataFrame of open order info with txid as the index
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query open orders & trades**
        """
        res = self._do_private_request("OpenOrders", trades=trades, userref=userref)
        openorders = DataFrame(res["open"], index=["cost", "descr", "expiretm", "fee", "limitprice", "misc", "oflags", "opentm", "price", "refid", "starttm", "status", "stopprice", "userref", "vol", "vol_exec"]).T

        openorders[["expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]] = openorders[["expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]].astype(float)
        return openorders


    @callratelimiter(1)
    def get_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime=None):
        """
        Private User Data

        Retrieve information about orders that have been closed (filled or cancelled). 50 results are returned at a time, the most recent by default.

        :param trades: Whether or not to include trades in output (optional) - default = False
        :type trades: bool
        :param userref: Restrict results to given user reference id (optional)
        :type userref: str
        :param start: Starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: Ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: The result offset
        :type ofs: int
        :param closetime: Which time to use (optional):

            - open
            - close
            - both (default)

        :type closetime: str
        
        :returns: DataFrame of of order info and amount of available order info matching criteria
        :rtype: (:py:attr:`pandas.DataFrame`, int)


        API Key Permissions Required: **Orders and trades - Query closed orders & trades**
        """
        res = self._do_private_request("ClosedOrders", trades=trades, userref=userref, start=start, end=end, ofs=ofs, closetime=closetime)
        closed = DataFrame(res["closed"], index=["refid", "userref", "status", "reason", "opentm", "closetm", "starttm", "expiretm", "descr", "vol", "vol_exec", "cost", "fee", "price", "stopprice", "limitprice", "misc", "oflags", "trades"]).T
        closed[["closetm", "expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]] = closed[["closetm", "expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]].astype(float)

        count = int(res["count"])
        return closed, count


    @callratelimiter(1)
    def query_orders_info(self, txid, trades=False, userref=None):
        """
        Private User Data

        Retrieve information about specific orders.

            
        :param trades: Whether or not to include trades in output (optional) - default = False
        :type trades: bool
        :param userref: Restrict results to given user reference id (optional)
        :type userref: str
        :param txid: Comma delimited list of transaction ids to query info about (50 maximum)
        :type txid: str

        :returns: DataFrame of associative orders info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query open orders & trades** or **Orders and trades - Query closed orders & trades**, depending on status of order
        """
        res = self._do_private_request("QueryOrders", txid=txid, trades=trades, userref=userref)
        orders = DataFrame(res, index=["closetm", "cost", "descr", "expiretm", "fee", "limitprice", "misc", "oflags", "opentm", "price", "reason", "refid", "starttm", "status", "stopprice", "trades", "userref", "vol", "vol_exec"]).T

        orders[["closetm", "expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]] = orders[["closetm", "expiretm", "opentm", "starttm", "cost", "fee", "price", "vol", "vol_exec", "stopprice", "limitprice"]].astype(float)
        return orders


    @callratelimiter(1)
    def get_order_amends(self, order_id):
        """
        Private User Data

        Retrieves an audit trail of amend transactions on the specified order. The list is ordered by ascending amend timestamp.

            
        :param order_id: The Kraken order identifier for the amended order.
        :type order_id: str

        :returns: DataFrame of associative orders info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query open orders & trades** or **Orders and trades - Query closed orders & trades**, depending on status of order
        """
        res = self._do_private_request("OrderAmends", order_id=order_id)
        orders = DataFrame(res["amends"], index=["amend_id", "amend_type", "order_qty", "remaining_qty", "limit_price", "timestamp"])

        orders[["order_qty", "remaining_qty", "limit_price", "timestamp"]] = orders[["order_qty", "remaining_qty", "limit_price", "timestamp"]].astype(float)
        return orders


    @callratelimiter(2)
    def get_trades_history(self, trade_type="all", trades=False, start=None, end=None, ofs=None):
        """
        Private User Data

        Retrieve information about trades/fills. 50 results are returned at a time, the most recent by default.


        :param trade_type: type of trade (optional):

            - all = all types (default)
            - any position = any position (open or closed)
            - closed position = positions that have been closed
            - closing position = any trade closing all or part of a position
            - no position = non-positional trades

        :type trade_type: str
        :param trades: Whether or not to include trades related to position in output (optional) - default = False
        :type trades: bool
        :param start: Starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: Ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: Result offset for pagination
        :type ofs: int

        :returns: DataFrame of trade info and the amount of available trades info matching criteria
        :rtype: (:py:attr:`pandas.DataFrame`, int)


        API Key Permissions Required: **Orders and trades - Query closed orders & trades**
        """
        res = self._do_private_request("TradesHistory", trades=trades, start=start, end=end, ofs=ofs, type=trade_type)
        trades = DataFrame(res["trades"], index=["ordertxid", "postxid", "pair", "time", "type", "ordertype", "price", "cost", "fee", "vol", "margin", "misc"]).T
        trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)

        count = int(res["count"])
        return trades, count


    @callratelimiter(2)
    def query_trades_info(self, txid, trades=False):
        """
        Private User Data

        Retrieve information about specific trades/fills.

        
        :param txid: Comma delimited list of transaction ids to query info about (20 maximum)
        :type txid: str
        :param trades: Whether or not to include trades related to position in output (optional) - default = False
        :type trades: bool
        
        :returns: DataFrame of associative trades info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query closed orders & trades**
        """
        res = self._do_private_request("QueryTrades", txid=txid, trades=trades)
        trades = DataFrame(res, index=["cost", "fee", "margin", "misc", "ordertxid", "ordertype", "pair", "postxid", "price", "time", "type", "vol"]).T
        trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)
        return trades


    @callratelimiter(1)
    def get_open_positions(self, txid=None, docalcs=False, consolidation=None):
        """
        Private User Data

        :param txid: Comma delimited list of transaction ids to restrict output to
        :type txid: str
        :param docalcs: Whether or not to include profit/loss calculations (optional) - default = False
        :type docalcs: bool
        :param consolidation: What to consolidate the positions data around (optional) - "market" = will consolidate positions based on market pair
        :type consolidation: str

        :returns: A DataFrame of open position info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Orders and trades - Query open orders & trades**

        .. note::

            Using the consolidation optional field will result in consolidated view of the data being returned.
        """
        res = self._do_private_request("OpenPositions", txid=txid, docalcs=docalcs, consolidation=consolidation)
        pos = DataFrame(res, index=["ordertxid", "posstatus", "pair", "time", "type", "ordertype", "cost", "fee", "vol", "vol_closed", "margin", "value", "net", "terms", "rollovertm", "misc", "oflags"]).T
        pos[["time", "cost", "fee", "vol", "vol_closed", "margin", "value", "net", "rollovertm"]] = pos[["time", "cost", "fee", "vol", "vol_closed", "margin", "value", "net", "rollovertm"]].astype(float)
        return pos


    @callratelimiter(2)
    def get_ledgers_info(self, asset=None, aclass=None, selection_type="all", start=None, end=None, ofs=None):
        """
        Private User Data

        Retrieve information about ledger entries. 50 results are returned at a time, the most recent by default.

        
        :param asset: Comma delimited list of assets to restrict output to (optional) - default = "all"
        :type asset: str
        :param aclass: Asset class (optional) - default = "currency"
        :type aclass: str
        :param selection_type: Type of trade (optional):

            - all (default)
            - deposit
            - withdrawal
            - trade
            - margin

        :type selection_type: str
        :param start: Starting unix timestamp or order tx id of results (optional.  exclusive)
        :type start: int or str
        :param end: Ending unix timestamp or order tx id of results (optional.  inclusive)
        :type start: int or str
        :param ofs: Result offset for pagination
        :type ofs: int

        :returns: DataFrame of associative ledgers info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Data - Query ledger entries**
        """
        res = self._do_private_request("Ledgers", aclass=aclass, asset=asset, type=selection_type, start=start, end=end, ofs=ofs)
        ledgers = DataFrame(res["ledger"], index=["refid", "time", "type", "subtype", "aclass", "asset", "amount", "fee", "balance"]).T
        ledgers[["time", "amount", "balance", "fee"]] = ledgers[["time", "amount", "balance", "fee"]].astype(float)
        return ledgers


    @callratelimiter(2)
    def query_ledgers(self, id, trades=False):
        """
        Private User Data

        Retrieve information about specific ledger entries.


        :param id: Comma delimited list of ledger ids to query info about (20 maximum)
        :type id: str
        :param trades: Whether or not to include trades related to position in output
        :type trades: bool (optional.) - default = False

        :returns: DataFrame of associative ledgers info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Data - Query ledger entries**
        """
        res = self._do_private_request("QueryLedgers", id=id, trades=trades)
        ledgers = DataFrame(res, index=["aclass", "amount", "asset", "balance", "fee", "refid", "subtype", "time", "type"]).T

        ledgers[["time", "amount", "balance", "fee"]] = ledgers[["time", "amount", "balance", "fee"]].astype(float)
        return ledgers


    @callratelimiter(2)
    def get_trade_volume(self, pair):
        """
        Private User Data

        :param pair: Comma delimited list of asset pairs to get fee info on (optional)
        :type pair: str
        
        :returns: The volume currency, current discount volume, DataFrame of fees and DataFrame of maker fees
        :rtype: (str, float, :py:attr:`pandas.DataFrame`, :py:attr:`pandas.DataFrame`)


        API Key Permissions Required: **Funds permissions - Query**

        ..note:

            If an asset pair is on a maker/taker fee schedule, the taker side is given in fees and maker side in fees_maker. For pairs not on maker/taker, they will only be given in fees.
        """
        res = self._do_private_request("TradeVolume", pair=pair)

        currency = str(res["currency"])
        volume = float(res["volume"])

        fees = DataFrame(res.get("fees"), index=["fee", "maxfee", "minfee", "nextfee", "nextvolume", "tiervolume"]).T
        fees_maker = DataFrame(res.get("fees_maker"), index=["fee", "maxfee", "minfee", "nextfee", "nextvolume", "tiervolume"]).T
        return currency, volume, fees, fees_maker


    def request_export_report(self, description, report, data_format="CSV", fields=None, asset=None, starttm=None, endtm=None):
        """
        Private User Data

        Request export of trades or ledgers.


        :param description: Report description info
        :type description: str
        :param report: Report type

            - trades
            - ledgers

        :type report: str
        :param data_format: The data format

            - CSV (default)
            - TSV

        :type data_format: str
        :param fields: Comma delimited list of fields to include in report (optional).  default = "all" 

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
        :param asset: Comma delimited list of assets to get info on (optional) - default = "all"
        :type asset: str
        :param starttm: Report start unixtime (optional).  default = one year before now
        :type starttm: int
        :param endtm: Report end unixtime (optional).  default = now
        :type endtm: int

        :returns: Report id
        :rtype: str


        API Key Permissions Required: **Data - Export data**

        .. note:: 

            Field options are based on report type.
        """
        return str(self._do_private_request("AddExport", report=report, description=description, format=data_format, fields=fields, asset=asset, starttm=starttm, endtm=endtm)["id"])


    @callratelimiter(1)
    def get_export_report_status(self, report):
        """
        Private User Data

        :param report: Report type:

            - trades
            - ledgers

        :type report: str

        :returns: DataFrame of reports and their info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Data - Export data**
        """
        res = self._do_private_request("ExportStatus", report=report)
        status = DataFrame(res, columns=["id", "descr", "format", "report", "subtype", "status", "flags", "fields", "createdtm", "expiretm", "starttm", "completedtm", "datastarttm", "dataendtm", "aclass", "asset"])
        status[["flags", "createdtm", "expiretm", "starttm", "completedtm", "datastarttm", "dataendtm"]] = status[["flags", "createdtm", "expiretm", "starttm", "completedtm", "datastarttm", "dataendtm"]].astype(int)
        return status


    @callratelimiter(3)
    def retrieve_export_report(self, report_id, return_raw=False, dir=None):
        """
        Private User Data
        
        :param report_id: Report id
        :type report_id: str
        :param return_raw: Weither or not the report is returned as raw binary (optional) - default = False
        :type return_raw: bool
        :param dir: If given a directory the report will be saved there as a zipfile (optional)
        :type dir: str
        
        :returns: None or the binary of the compressed report.zip file
        :rtype: None or raw binary


        API Key Permissions Required: **Data - Export data**
        """
        assert not return_raw and dir == None, "At least one way the Data is returned must be specified"

        report = self._do_private_request("RetrieveExport", id=report_id)
        if dir != None:
            with open("{}Report_{}.zip".format(dir, report_id), "wb") as f:
                    f.write(report)
        if return_raw:
            return report            


    @callratelimiter(1)
    def delete_export_report(self, report_id, remove_type):
        """
        Private User Data
        
        :param report_id: Report id
        :type report_id: str
        :param remove_type: Removal type

            - cancel
            - delete

        :type remove_type: str


        :returns: Returns remove type
        :rtype: dict


        API Key Permissions Required: **Data - Export data**

        .. note::

            The delete remove type can only be used for a report that has already been processed. Use cancel for queued and processing statuses.
        """
        return self._do_private_request("RemoveExport", id=report_id, type=remove_type)

    



    #Private User Trading
    def add_standard_order(self, pair, type, ordertype, volume, displayvol=None, price=None,
                           price2=None, leverage=None, reduce_only=False, stptype="cancel-newest", oflags=None, starttm=0,
                           expiretm=0, userref=None, deadline=None, validate=True,
                           close_ordertype=None, close_price=None,
                           close_price2=None, trading_agreement="agree"):
        """
        Private User Trading

        :param pair: Asset pair
        :type pair: str
        :param type: Type of order

            - buy
            - sell

        :type type: str
        :param ordertype: Order type:

            - market
            - limit (price = limit price)
            - iceberg
            - stop-loss (price = stop loss price)
            - take-profit (price = take profit price)
            - stop-loss-limit (price = stop loss trigger price, price2 = triggered limit price)
            - take-profit-limit (price = take profit trigger price, price2 = triggered limit price)
            - trailing-stop (price = trailing stop offset)
            - trailing-stop-limit (price = trailing stop offset, price2 = triggered limit offset)
            - settle-position

        :type ordertype: str
        :param volume: Order volume in lots
        :type volume: float
        :param displayvol: Used to edit an iceberg order, this is the visible order quantity in terms of the base asset. The rest of the order will be hidden, although the full volume can be filled at any time by any order of that size or larger that matches in the order book. displayvol can only be used with the limit order type, must be greater than 0, and less than volume.
        :type displayvol: float
        :param price: Price (optional.  dependent upon ordertype)
        :type price: float or str
        :param price2: Secondary price (optional.  dependent upon ordertype)
        :type price2: float or str
        :param leverage: Amount of leverage desired (optional.  default = none)
        :type leverage: int
        :param reduce_only: If true, order will only reduce a currently open position, not increase it or open a new position. (optional.  default = False)
        :type reduce_only: boolean
        :param stptype: Self trade prevention behavior definition (optional. default = "cancel-newest"):

            - cancel-newest - if self trade is triggered, arriving order will be canceled
            - cancel-oldest - if self trade is triggered, resting order will be canceled
            - cancel-both - if self trade is triggered, both arriving and resting orders will be canceled

        :type stptype: str
        :param oflags: Comma delimited list of order flags (optional):

            - viqc = volume in quote currency (not available for leveraged orders)
            - fcib = prefer fee in base currency
            - fciq = prefer fee in quote currency
            - nompp = no market price protection
            - post = post only order (available when ordertype = limit)

        :type oflags: str
        :param starttm: Scheduled start time (optional):

            - 0 = now (default)
            - +<n> = schedule start time <n> seconds from now
            - <n> = unix timestamp of start time

        :type starttm: int
        :param expiretm: Expiration time (optional):

            - 0 = no expiration (default)
            - +<n> = expire <n> seconds from now
            - <n> = unix timestamp of expiration time
            
        :type expiretm: int
        :param userref: User reference id. 32-bit signed number.  (optional)
        :type userref: str
        :param deadline: RFC3339 timestamp (e.g. "2023-07-01T00:18:45Z") after which this order would be rejected.  (optional)
        :type deadline: str
        :param validate: Validate inputs only. do not submit order (optional)
        :type validate: bool
        :param close_ordertype: Optional closing order to add to system when order gets filled: order type

            - limit
            - stop-loss
            - take-profit
            - stop-loss-limit
            - take-profit-limit

        :type close_ordertype: str
        :param close_price: Price
        :type close_price: float or int
        :param  close_price2: Secondary price
        :type close_price2: float or int
        
        :returns: Dictionary of order description info
        :rtype: dict


        API Key Permissions Required: **Orders and trades - Create & modify orders**

        .. note::

            - See Get tradable asset pairs for specifications on asset pair prices, lots, and leverage.
            - Prices can be preceded by +, -, or # to signify the price as a relative amount (with the exception of trailing stops, which are always relative). + adds the amount to the current offered price. - subtracts the amount from the current offered price. # will either add or subtract the amount to the current offered price, depending on the type and order type used. Relative prices can be suffixed with a % to signify the relative amount as a percentage of the offered price.
            - For orders using leverage, 0 can be used for the volume to auto-fill the volume needed to close out your position.
            - If you receive the error "EOrder:Trading agreement required", refer to your API key management page for further details.
            - Volume can be specified as 0 for closing margin orders to automatically fill the requisite quantity.
        """
        if validate is False:
            validate = None

        volume = str(volume)
        price = str(price) if price else None
        price2 = str(price2) if price2 else None
        displayvol = str(displayvol) if displayvol else None
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
        return str(res["result"])


    #Private User Trading
    def edit_order(self, txid, pair, volume=None, displayvol=None, price=None, price2=None, oflags=None, userref=None, deadline=None, cancel_response=False, validate=True):
        """
        Private User Trading
        
        :param txid: Transaction id
        :type txid: str
        :param pair: Asset pair
        :type pair: str
        :param volume: Order volume in lots
        :type volume: float
        :param displayvol: Used to edit an iceberg order, this is the visible order quantity in terms of the base asset. The rest of the order will be hidden, although the full volume can be filled at any time by any order of that size or larger that matches in the order book. displayvol can only be used with the limit order type, must be greater than 0, and less than volume.
        :type displayvol: float
        :param price: Price (optional.  dependent upon ordertype)
        :type price: float or str
        :param price2: Secondary price (optional.  dependent upon ordertype)
        :type price2: float or str
        :param oflags: Comma delimited list of order flags (optional):

            - viqc = volume in quote currency (not available for leveraged orders)
            - fcib = prefer fee in base currency
            - fciq = prefer fee in quote currency
            - nompp = no market price protection
            - post = post only order (available when ordertype = limit)

        :type oflags: str
        :param userref: User reference id. 32-bit signed number.  (optional)
        :type userref: str
        :param deadline: RFC3339 timestamp (e.g. "2023-07-01T00:18:45Z") after which this order would be rejected.  (optional)
        :type deadline: str
        :param cancel_response: Used to interpret if client wants to receive pending replace, before the order is completely replaced (optional. Default = False)
        :type cancel_response: bool
        :param validate: Validate inputs only. do not submit order (optional)
        :type validate: bool
        
        
        :returns: Dictionary of order description info
        :rtype: dict


        API Key Permissions Required: **Orders and trades - Create & modify orders**
        """
        if validate is False:
            validate = None

        volume = str(volume)
        price = str(price) if price else None
        price2 = str(price2) if price2 else None
        displayvol = str(displayvol) if displayvol else None
        close_price = str(close_price) if close_price else None
        close_price2 = str(close_price2) if close_price2 else None

        data = {arg: value for arg, value in locals().items() if
                arg != "self" and value is not None}

        res = self._query_private("EditOrder", data=data)
        _check_error(res)
        return str(res["result"])


    def cancel_order(self, txid):
        """
        Private User Trading

        Cancel a particular open order (or set of open orders) by txid

        :param txid: Transaction id
        :type txid: str

        :returns: Number of orders canceled and weither order(s) is/are pending cancellation
        :rtype: (int, bool)


        API Key Permissions Required: **Orders and trades - Create & modify orders** and **Orders and trades - Cancel & close orders**
        """
        data = self._do_private_request("CancelOrder", txid=txid)
        return int(data["count"]), data.get("pending")


    def cancel_all_orders(self):
        """
        Private User Trading

        Cancel all open orders

        :returns: Number of orders canceled
        :rtype: int


        API Key Permissions Required: **Orders and trades - Create & modify orders** and **Orders and trades - Cancel & close orders**
        """
        data = self._do_private_request("CancelAll")
        return int(data["count"])


    def cancel_all_orders_after(self, timeout):
        """
        Private User Trading

        This method provides a "Dead Man"s Switch" mechanism to protect the client from network malfunction, extreme latency or unexpected matching engine downtime. The client can send a request with a timeout (in seconds), that will start a countdown timer which will cancel all client orders when the timer expires. The client has to keep sending new requests to push back the trigger time, or deactivate the mechanism by specifying a timeout of 0. If the timer expires, all orders are cancelled and then the timer remains disabled until the client provides a new (non-zero) timeout.
        The recommended use is to make a call every 15 to 30 seconds, providing a timeout of 60 seconds. This allows the client to keep the orders in place in case of a brief disconnection or transient delay, while keeping them safe in case of a network breakdown. It is also recommended to disable the timer ahead of regularly scheduled trading engine maintenance (if the timer is enabled, all orders will be cancelled when the trading engine comes back from downtime - planned or otherwise).
        
        
        :param timeout: Duration (in seconds) to set/extend the timer by
        :type timeout: int

        :returns: The timestamp when the request was recieved, The timestamp after which all orders will be cancelled, unless the timer is extended or disabled
        :rtype: str, str


        API Key Permissions Required: **Orders and trades - Create & modify orders** and **Orders and trades - Cancel & close orders**

        Example Return: KrakenAPI.cancel_all_orders_after(60) -> ("2021-03-24T17:41:56Z", "2021-03-24T17:42:56Z")
        """
        res = self._do_private_request("CancelAllOrdersAfter", timeout=timeout)
        return res["currentTime"], res["triggertime"]


    def cancel_order_batch(self, orders):
        """
        Private User Trading

        Cancel multiple open orders by txid or userref (maximum 50 total unique IDs/references)
        
        :param orders: List of open order transaction IDs (txid) or user references (userref), up to a maximum of 50 total unique IDs/references.
        :type orders: list of str or int

        :returns: Number of orders canceled
        :rtype: int


        API Key Permissions Required: **Orders and trades - Create & modify orders** and **Orders and trades - Cancel & close orders**
        """
        res = self._do_private_request("CancelOrderBatch", orders=orders)
        return int(res["count"])





    #Private User Funding
    @callratelimiter(1)
    def get_deposit_methods(self, asset):
        """
        Private User Funding

        Retrieve methods available for depositing a particular asset.


        :param asset: Asset being deposited
        :type asset: str

        :returns: DataFrame of deposit methods
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query** and **Funds permissions - Deposit**
        """
        res = self._do_private_request("DepositMethods", asset=asset)
        depo = DataFrame(res, columns=["method", "limit", "fee", "gen-address"])
        depo["fee"] = depo["fee"].astype(float)
        return depo


    @callratelimiter(1)
    def get_deposit_addresses(self, asset, method, new=False):
        """
        Private User Funding

        Retrieve (or generate a new) deposit addresses for a particular asset and method.


        :param asset: Asset being deposited
        :type asset: str
        :param method: Name of the deopsit method
        :type method: str
        :param new: Whether or not to generate a new address (optional.) - default = False
        :type new: bool

        :returns: DataFrame of associative deposit addresses
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("DepositAddresses", asset=asset, method=method, new=new)
        
        depo = DataFrame(res, columns=["address", "expiretm", "new"])
        depo["new"] = depo["new"].fillan(False).astype(bool)
        depo["expiretm"] = depo["expiretm"].astype(int)
        return depo



    @callratelimiter(1)
    def get_deposit_status(self, asset, method=None):
        """
        Private User Funding

        Retrieve information about recent deposits made.


        :param asset: Asset being deposited
        :type asset: str
        :param method: Name of the deopsit method (optional)
        :type method: str

        :returns: DataFrame of deposit status information
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("DepositStatus", asset=asset, method=method)
        depo_status = DataFrame(res, columns=["method", "aclass", "asset", "refid", "txid", "info", "amount", "fee", "time", "status"])
        depo_status[["amount", "fee", "time"]] = depo_status[["amount", "fee", "time"]].astype(float).fillna(0.0)
        return depo_status


    @callratelimiter(1)
    def get_withdrawal_info(self, asset, key, amount):
        """
        Private User Funding

        Retrieve fee information about potential withdrawals for a particular asset, key and amount.

        
        :param asset: Asset being withdrawn
        :type asset: str
        :param key: Withdrawal key name, as set up on your account
        :type key: str
        :param amount: Amount to withdraw
        :type amount: float

        :returns: DataFrame of associative withdrawal info
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query** and **Funds permissions - Withdraw**
        """
        res = self._do_private_request("WithdrawInfo", asset=asset, key=key, amount=amount)
        wd = DataFrame(res, index=[asset], columns=["method", "limit", "amount", "fee"])
        wd[["limit", "amount", "fee"]] = wd[["limit", "amount", "fee"]].astype(float)
        return wd


    @callratelimiter(1)
    def get_withdrawal_methods(self, asset=None, aclass="currency", network=None):
        """
        Private User Funding

        Retrieve a list of withdrawal methods available for the user.

        
        :param asset: Filter methods for specific asset (optional)
        :type asset: str
        :param aclass: Filter methods for specific asset class (optional) - default = "currency"
        :type aclass: str
        :param network: Filter methods for specific network (optional)
        :type network: str

        :returns: DataFrame of withdrawal methods
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query** and **Funds permissions - Withdraw**
        """
        res = self._do_private_request("WithdrawMethods", asset=asset, aclass=aclass, network=network)
        wd = DataFrame(res, columns=["asset", "method", "network", "minimum"])
        wd["minimum"] = wd["minimum"].astype(float)
        return wd


    def withdraw_funds(self, asset, key, amount):
        """
        Private User Funding

        :param asset: Asset being withdrawn
        :type asset: str
        :param key: Withdrawal key name, as set up on your account
        :type key: str
        :param amount: Amount to withdraw
        :type amount: float
        
        :returns: Reference id
        :rtype: str


        API Key Permissions Required: **Funds permissions - Withdraw**
        """
        return str(self._do_private_request("Withdraw", asset=asset, key=key, amount=float(amount))["refid"])


    @callratelimiter(1)
    def get_withdrawal_status(self, asset, method=None):
        """
        Private User Funding

        Retrieve information about recently requests withdrawals.


        :param asset: Asset being withdrawn
        :type asset: str
        :param method: Name of the withdrawal method (optional)
        :type method: str

        :returns: DataFrame of withdrawal status information
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Withdraw** or **Data - Query ledger entries**
        """
        res = self._do_private_request("WithdrawStatus", asset=asset, method=method)
        wd_status = DataFrame(res, columns=["method", "aclass", "asset", "refid", "txid", "info", "amount", "fee", "time", "status", "status-prop"])
        wd_status[["amount", "fee", "time"]] = wd_status[["amount", "fee", "time"]].astype(float)
        return wd_status


    @callratelimiter(1)
    def request_withdrawal_cancel(self, asset, refid):
        """
        Private User Funding
        
        Cancel a recently requested withdrawal, if it has not already been successfully processed.

        :param asset: Asset being withdrawn
        :type asset: str
        :param refid: Withdrawal reference id
        :type refid: str

        :returns: True on success
        :rtype: bool


        API Key Permissions Required: **Funds permissions - Withdraw**, unless withdrawal is a **WalletTransfer**, then no permissions are required.

        .. note::

            **Cancelation cannot be guaranteed.** This will put in a cancelation request. Depending upon how far along the withdrawal process is, it may not be possible to cancel the withdrawal.
        """
        return bool(self._do_private_request("WithdrawCancel", asset=asset, refid=refid))

    
    @callratelimiter(1)
    def wallet_transfer_to_futures(self, asset, amount):
        """
        Private User Funding

        Transfer from Kraken spot wallet to Kraken Futures holding wallet. Note that a transfer in the other direction must be requested via the Kraken Futures API endpoint.


        :param asset: Asset being withdrawn
        :type asset: str
        :param amount: Amount to withdraw
        :type amount: float
        
        :returns: Reference id
        :rtype: str
        """

        data = {"asset": asset, "from": "Spot Wallet", "to": "Futures Wallet", "amount": amount} 
        res = self._query_private("WalletTransfer", data)
        _check_error(res)
        return str(res["result"]["refid"])

    


    #Private User Staking
    @callratelimiter(2)
    def stake_asset(self, asset, amount, method):
        """
        Private User Staking

        Stake an asset from your spot wallet. This operation requires an API key with Withdraw funds permission.

        :param asset: Asset to stake
        :type asset: str
        :param amount: Amount of the asset to stake
        :type amount: float

        :param method: Name of the staking option to use (refer to :py:attr:`KrakenAPI.get_stakeable_assets` for the correct method names for each asset)
        :type method: str

        
        :returns: Reference ID of the Staking Transaction
        :rtype: str


        API Key Permissions Required: **Funds permissions - Withdraw**
        """
        return str(self._do_private_request("Stake", asset=asset, amount=amount, method=method)["refid"])


    @callratelimiter(2)
    def unstake_asset(self, asset, amount):
        """
        Private User Staking

        Unstake an asset from your spot wallet. This operation requires an API key with Withdraw funds permission.

        :param asset: Asset to unstake (asset ID or altname). Must be a valid staking asset (e.g. XBT.M, XTZ.S, ADA.S)
        :type asset: str
        :param amount: Amount of the asset to unstake
        :type amount: float

        
        :returns: Reference ID of the Unstaking Transaction
        :rtype: str


        API Key Permissions Required: **Funds permissions - Withdraw**
        """
        return str(self._do_private_request("Unstake", asset=asset, amount=amount)["refid"])

        
    @callratelimiter(2)
    def get_stakeable_assets(self):
        """
        Private User Staking

        Returns the list of assets that the user is able to stake. This operation requires an API key with both Withdraw funds and Query funds permission.
        
        :returns: DataFrame of stakeable assets
        :rtype: :py:attr:`pandas.DataFrame`
        """
        res = self._do_private_request("Staking/Assets")
        stakeable = json_normalize(res, sep="_")
        if stakeable.empty:
            stakeable = DataFrame(columns=["method", "asset", "staking_asset", "on_chain", "can_stake", "can_unstake", "rewards_reward", "rewards_type", "minimum_amount_staking", "minimum_amount_unstaking"])
        stakeable[["rewards_reward", "minimum_amount_staking", "minimum_amount_unstaking"]] = stakeable[["rewards_reward", "minimum_amount_staking", "minimum_amount_unstaking"]].astype(float)
        return stakeable


    @callratelimiter(2)
    def get_pending_staking_transactions(self):
        """
        Private User Staking

        Returns the list of pending staking transactions. Once resolved, these transactions will appear on the List of Staking Transactions endpoint.
        This operation requires an API key with both Query funds and Withdraw funds permissions.


        :returns: DataFrame of pending staking transactions
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("Staking/Pending")
        pend_stk = DataFrame(res, columns=["method", "aclass", "asset", "refid", "amount", "fee", "time", "status", "type"])
        pend_stk[["amount", "fee", "time"]] = pend_stk[["amount", "fee", "time"]].astype(float)
        return pend_stk



    @callratelimiter(2)
    def get_staking_transactions(self):
        """
        Private User Staking

        Returns the list of all staking transactions. This endpoint can only return up to 1000 of the most recent transactions.
        This operation requires an API key with Query funds permissions.

        
        :returns: DataFrame of all staking transactions
        :rtype: :py:attr:`pandas.DataFrame`


        API Key Permissions Required: **Funds permissions - Query**
        """
        res = self._do_private_request("Staking/Transactions")
        stk = DataFrame(res, columns=["method", "aclass", "asset", "refid", "amount", "fee", "time", "status", "type", "bond_start", "bond_end"])
        stk[["amount", "fee", "time", "bond_start", "bond_end"]] = stk[["amount", "fee", "time", "bond_start", "bond_end"]].astype(float)
        return stk

    
   


    def _update_api_counter(self):
        now = time()
        self.api_counter = max(0, self.api_counter - int(now - self.time_of_last_query))
        self.time_of_last_query = now



def add_dtime(df):
    """
    Extra

    Adds a new column "dtime" (datetime) from the column "time" (unixtime)

    :param df: A DataFrame with a column "time" in unixtime-format
    :type df: :py:attr:`pandas.DataFrame`

    :returns: df with a "dtime" column added
    :rtype: :py:attr:`pandas.DataFrame`
    """
    df["dtime"] = to_datetime(df.time, unit="s")
    return df


def datetime_to_unixtime(dt):
    """
    Extra

    Converts from datetime to unixtime
    
    :param dt: datetime object
    :type dt: :py:attr:`datetime.datetime`

    :returns: the unixtime of dt
    :rtype: int
    """
    return int((dt - datetime(1970, 1, 1)).total_seconds())


def unixtime_to_datetime(ux):
    """
    Extra

    Converts from unixtime to datetime 
    
    :param ux: unixtime timestamp
    :type ux: int

    :returns: the datetime of ux
    :rtype: :py:attr:`datetime.datetime`
    """
    return datetime(1970, 1, 1) + timedelta(0, ux)