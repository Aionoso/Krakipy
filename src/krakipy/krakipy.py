from pandas import to_datetime, DataFrame, Series, concat
from datetime import datetime, timedelta
from requests import Session, HTTPError
from base64 import b64encode, b64decode
from urllib.parse import urlencode
from hashlib import sha256, sha512
from time import time, sleep
from functools import wraps 
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


class KrakenAPI(object):
    def __init__(self, key="", secret="", retry=0.5, limit=20):
        self._key = key
        self._secret = secret
        self.uri = "https://api.kraken.com"
        self.apiversion = "0"
        self.session = Session()
        self.session.headers.update({"User-Agent": "krakipy/" + version.__version__ + " (+" + version.__url__ + ")"})
        self.response = None

        self.time_of_last_query = time()
        self.api_counter = 0
        self.counter = 0
        self.limit = limit
        self.retry = retry

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def __del__(self):
        self.session.close()

    def close(self):
        self.session.close()

    def __str__(self):
        return f"[{__class__.__name__}]\nVERSION:         {self.apiversion}\nURI:             {self.uri}\nAPI-Key:         {'*' * len(self._key) if self._key else '-'}\nAPI-Secretkey:   {'*' * len(self._secret) if self._secret else '-'}\nAPI-Counter:     {self.api_counter}\nRequest-Counter: {self.counter}\nRequest-Limit:   {self.limit}\nRequest-Retry:   {self.retry} s"

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
        headers = {"API-Key": self._key, "API-Sign": self._sign(data, urlpath)}
        return self._query(urlpath, data, headers, timeout = timeout)

    def _do_public_request(self, action, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        res = self._query_public(action, data = kwargs)
        check_error(res)
        return res["result"]

    def _do_private_request(self, action, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        res = self._query_private(action, data = kwargs)
        check_error(res)
        return res["result"]

    @callratelimiter(1)
    def get_server_time(self):
        res = self._query_public("Time")
        check_error(res)
        return res["result"]["rfc1123"], res["result"]["unixtime"]

    @callratelimiter(1)
    def get_asset_info(self, info=None, aclass=None, asset=None):
        return DataFrame(self._do_public_request("Assets", info=info, aclass = aclass, asset = asset)).T

    @callratelimiter(1)
    def get_tradable_asset_pairs(self, info=None, pair=None):
        return DataFrame(self._do_public_request("AssetPairs", info=info, pair=pair)).T

    @callratelimiter(1)
    def get_ticker_information(self, pair):
        return DataFrame(self._do_public_request("Ticker", pair=pair)).T

    @callratelimiter(1)
    def get_open_positions(self, txid=None, docalcs=False):
        return self._do_private_request("OpenPositions", txid=txid, docalcs=docalcs)

    def cancel_open_order(self, txid):
        return self._do_private_request("CancelOrder", txid=txid)

    @callratelimiter(1)
    def get_withdraw_info(self, asset, key, amount, aclass="currency"):
        return self._do_private_request("WithdrawInfo", asset=asset, aclass=aclass, key=key, amount=amount)

    def withdraw_funds(self, asset, amount, key = "Manager Wallet"):
        return self._do_private_request("Withdraw", asset=asset, key=key, amount=float(amount))

    @callratelimiter(1)
    def get_withdraw_status(self, asset):
        return self._do_private_request("WithdrawStatus", asset=asset)

    @callratelimiter(1)
    def request_withdraw_cancel(self, refid, asset, aclass = "currency"):
        return self._do_private_request("WithdrawCancel", asset=asset, aclass=aclass, refid=refid)

    @callratelimiter(1)
    def get_deposit_status(self, asset):
        return self._do_private_request("DepositStatus", asset=asset)

    @callratelimiter(1)
    def get_deposit_adress(self, asset, method):
        return self._do_private_request("DepositAddresses", asset=asset, method=method)

    @callratelimiter(1)
    def get_deposit_method(self, asset : str):
        return self._do_private_request("DepositMethods", asset=asset)

    @callratelimiter(1)
    def wallet_transfer(self, asset, to_address, from_address, amount):
        data = {"asset": asset,"to": to_address, "from": from_address, "amount": amount} 
        res = self._query_private("WalletTransfer", data)
        check_error(res)
        return res["result"]["refid"]

    def request_export_report(self, report, description):# report : trades/ledgers
        return self._do_private_request("AddExport", report=report, description=description)

    @callratelimiter(1)
    def get_export_statuses(self):
        return self._do_private_request("ExportStatus", report="trades")

    @callratelimiter(1)
    def remove_export_report(self, report_id):
        return self._do_private_request("RemoveExport", id=report_id, type="delete")

    @callratelimiter(2)
    def get_ohlc_data(self, pair, interval=1, since=None):
        res = self._do_public_request("OHLC", pair=pair, interval=interval, since=since)
        ohlc = DataFrame(res[pair], dtype="float")
        last = int(res["last"])

        if not ohlc.empty:
            ohlc.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
            ohlc["time"] = ohlc["time"].astype(int)
        return ohlc, last

    @callratelimiter(1)
    def get_order_book(self, pair, count=100):
        res = self._do_public_request("Depth", pair=pair, count=count)
        cols = ["price", "volume", "time"]
        asks = DataFrame(res[pair]["asks"], columns=cols, dtype="float")
        bids = DataFrame(res[pair]["bids"], columns=cols, dtype="float")
        asks["time"] = asks["time"].astype(int)
        bids["time"] = bids["time"].astype(int)
        return asks, bids

    @callratelimiter(2)
    def get_recent_trades(self, pair, since=None):
        res = self._do_public_request("Trades", pair=pair, since=since)
        trades = DataFrame(res[pair])
        last = int(res["last"])

        if not trades.empty:
            trades.columns = ["price", "volume", "time", "buy_sell", "market_limit", "misc"]
            trades = trades.astype({"price": float, "volume": float, "time": int})
        return trades, last

    @callratelimiter(1)
    def get_recent_spread_data(self, pair, since=None):
        res = self._do_public_request("Spread", pair=pair, since=since)
        spread = DataFrame(res[pair], columns=["time", "bid", "ask"], dtype="float")
        last = int(res["last"])
        spread["time"] = spread.time.astype(int)
        spread["spread"] = spread.ask - spread.bid
        return spread, last

    @callratelimiter(1)
    def get_account_balance(self):
        res = self._do_private_request("Balance")
        balance = DataFrame(res, index=["vol"], dtype="float").T
        return balance

    @callratelimiter(2)
    def get_trade_balance(self, aclass="currency", asset="ZEUR"):
        res = self._do_private_request("TradeBalance", aclass=aclass, asset=asset)
        tradebalance = DataFrame(res, index=[asset], dtype="float").T
        return tradebalance

    @callratelimiter(1)
    def get_open_orders(self, trades=False, userref=None):
        res = self._do_private_request("OpenOrders", trades=trades, userref=userref)
        openorders = DataFrame(res["open"]).T
        if not openorders.empty:
            openorders[["expiretm", "opentm", "starttm"]] = openorders[["expiretm", "opentm", "starttm"]].astype(int)
            openorders[["cost", "fee", "price", "vol", "vol_exec"]] = openorders[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return openorders

    @callratelimiter(1)
    def get_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime=None):
        res = self._do_private_request("ClosedOrders", trades=trades, userref=userref, start=start, end=end, ofs=ofs, closetime=closetime)
        closed = DataFrame(res["closed"]).T
        count = int(res["count"])
        if not closed.empty:
            closed[["closetm", "expiretm", "opentm", "starttm"]] = closed[["closetm", "expiretm", "opentm", "starttm"]].astype(int)
            closed[["cost", "fee", "price", "vol", "vol_exec"]] = closed[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return closed, count

    @callratelimiter(1)
    def query_orders_info(self, txid, trades=False, userref=None):
        res = self._do_private_request("QueryOrders", txid=txid, trades=trades, userref=userref)
        orders = DataFrame(res).T

        if not orders.empty:
            orders[["closetm", "expiretm", "opentm", "starttm"]] = orders[["closetm", "expiretm", "opentm", "starttm"]].astype(int)
            orders[["cost", "fee", "price", "vol", "vol_exec"]] = orders[["cost", "fee", "price", "vol", "vol_exec"]].astype(float)
        return orders

    @callratelimiter(2)
    def get_trades_history(self, type="all", trades=False, start=None, end=None, ofs=None):
        res = self._do_private_request("TradesHistory", trades=trades, start=start, end=end, ofs=ofs)
        trades = DataFrame(res["trades"]).T
        count = int(res["count"])
        if not trades.empty:
            trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)
        return trades, count

    @callratelimiter(2)
    def query_trades_info(self, txid, trades=False):
        res = self._do_private_request("QueryTrades", txid=txid, trades=trades)
        trades = DataFrame(res).T
        if not trades.empty:
            trades[["cost", "fee", "margin", "price", "time", "vol"]] = trades[["cost", "fee", "margin", "price", "time", "vol"]].astype(float)
        return trades

    @callratelimiter(2)
    def get_ledgers_info(self, aclass=None, asset=None, selection_type="all", start=None, end=None, ofs=None):
        res = self._do_private_request("Ledgers", aclass=aclass, asset=asset, type=selection_type, start=start, end=end, ofs=ofs)
        ledgers = pd.DataFrame(res["ledger"]).T
        count = int(res["count"])
        if not ledgers.empty:
            ledgers[["amount", "balance", "fee"]] = ledgers[["amount", "balance", "fee"]].astype(float)
            ledgers["time"] = ledgers["time"].astype(int)
        return ledgers, count

    @callratelimiter(2)
    def query_ledgers(self, id):
        res = self._do_private_request("QueryLedgers", id=id)
        ledgers = pd.DataFrame(res).T
        if not ledgers.empty:
            ledgers[["amount", "balance", "fee"]] = ledgers[["amount", "balance", "fee"]].astype(float)
            ledgers["time"] = ledgers["time"].astype(int)
        return ledgers

    @callratelimiter(2)
    def get_trade_volume(self, pair):
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
        if validate is False:
            validate = None

        data = {arg: value for arg, value in locals().items() if
                arg != "self" and value is not None}
        if close_ordertype != None:
            data["close[ordertype]"] = data.pop("close_ordertype")

        if close_price != None:
            data["close[price]"] = data.pop("close_price")

        if close_price2 != None:
            data["close[price2]"] = data.pop("close_price2")

        res = self._query_private("AddOrder", data=data)
        check_error(res)
        return res["result"]

    
    @callratelimiter(3)
    def get_export_report(self, report_id, path="", return_raw=False):
        report = self._do_private_request("RetrieveExport", id=report_id)
        if return_raw:
            return report
        else:
            with open("{}Report_{}.zip".format(path, report_id), "wb") as f:
                f.write(report)

    def _update_api_counter(self):
        now = time()
        self.api_counter = min(0, self.api_counter - int(now - self.time_of_last_query))
        self.time_of_last_query = now



def add_dtime(df, unit = "s"):
    df["dtime"] = to_datetime(df.time, unit=unit)
    return df

def check_error(result):
    if len(result["error"]) > 0:
        raise KrakenAPIError(result["error"])

def datetime_to_unixtime(self, dt):
        return int((dt - datetime(1970, 1, 1)).total_seconds())

def unixtime_to_datetime(self, unixtime):
    return datetime(1970, 1, 1) + timedelta(0, unixtime)
