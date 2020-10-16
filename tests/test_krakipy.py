from pandas import DataFrame
from src import KrakenAPI
import pytest

def assert_type(value, value_types):
        if type(value_types) != type:
            assert type(value) == type(value_types), f"Not the right type, expected {type(value_types).__name__}"
        else:
            assert type(value) == value_types, f"Not the right type, expected {value_types.__name__}"
            
def assert_len(value, value_length):
    assert len(value) == value_length, f"Not the right length, expected length of {value_length}"

def assert_format(value, value_format):
    assert_type(value, value_format)
    if type(value_format) != type:
        if len(value_format) > 1:
            assert_len(value, len(value_format))
            for i in range(len(value_format)):
                assert_format(value[i], value_format[i])

def assert_dataformat(value, value_format):
    shape = value.shape
    for i in range(len(value_format)):
        if value_format[i] != None:
            assert shape[i] == value_format[i], f"The DataFrame shape {value.shape} does not match {value_format}"
            
from time import sleep


class KrakipyTest(object):
    def __init__(self):
        self.api_public = KrakenAPI()
        
    def test_get_server_time(self):
        res = self.api_public.get_server_time()
        assert_format(res, (str, int))
        
    def test_get_asset_info(self):
        res = self.api_public.get_asset_info()
        assert_format(res, DataFrame)
        assert_dataformat(res, (None, 4))
        
    def test_get_tradable_asset_pairs(self):
        res = self.api_public.get_tradable_asset_pairs()
        assert_format(res, DataFrame)
        assert_dataformat(res, (None, 18))

    def test_get_ticker_information(self):
        res = self.api_public.get_ticker_information("XTZEUR")
        assert_format(res, DataFrame)
        assert_dataformat(res, (1, 9))
        
    def test_get_ohlc_data(self):
        res = self.api_public.get_ohlc_data("XXBTZEUR")
        assert_format(res, (DataFrame, int))
        assert_dataformat(res[0], (720, 8))
    
    def test_get_order_book(self):
        res = self.api_public.get_order_book("XTZEUR")
        assert_format(res, (DataFrame, DataFrame))
        assert_dataformat(res[0], (100, 3))
        assert_dataformat(res[1], (100, 3))
    
    def test_get_recent_trades(self):
        res = self.api_public.get_recent_trades("XTZEUR")
        assert_format(res, (DataFrame, int))
        assert_dataformat(res[0], (1000, 6))
        
    def test_get_recent_spread_data(self):
        res = self.api_public.get_recent_spread_data("XTZEUR")
        assert_format(res, (DataFrame, int))
        assert_dataformat(res[0], (None, 4))
        
    def test_get_recent_spread_data(self):
        res = self.api_public.get_recent_spread_data("XTZEUR")
        assert_format(res, (DataFrame, int))
        assert_dataformat(res[0], (None, 4))
        
if __name__ == "__main__":
    test = KrakipyTest()
    sleep(0.5)
    test.test_get_server_time()
    sleep(0.5)
    test.test_get_asset_info()
    sleep(0.5)
    test.test_get_tradable_asset_pairs()
    sleep(0.5)
    test.test_get_ticker_information()
    sleep(0.5)
    test.test_get_ohlc_data()
    sleep(0.5)
    test.test_get_order_book()
    sleep(0.5)
    test.test_get_recent_trades()
    sleep(0.5)
    test.test_get_recent_spread_data()