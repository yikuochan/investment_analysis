"""Alpha Vantage API 抓取模組測試"""
import os
import json
import unittest
from unittest.mock import patch, mock_open, Mock
import requests
from data_sources.alpha_vantage_fetcher import get_api_key, fetch_treasury_yield


class TestAlphaVantageAPIKey(unittest.TestCase):

    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_env_key'})
    def test_get_api_key_from_env(self):
        """測試從環境變數載入 API key"""
        key = get_api_key()
        self.assertEqual(key, 'test_env_key')

    @patch.dict(os.environ, {}, clear=True)
    @patch('builtins.open', mock_open(read_data='{"api_keys": {"alpha_vantage": "test_config_key"}}'))
    def test_get_api_key_from_config(self):
        """測試從 config.json 載入 API key"""
        key = get_api_key()
        self.assertEqual(key, 'test_config_key')

    @patch.dict(os.environ, {}, clear=True)
    @patch('builtins.open', mock_open(read_data='{"api_keys": {}}'))
    def test_get_api_key_none_when_missing(self):
        """測試無 API key 時回傳 None"""
        key = get_api_key()
        self.assertIsNone(key)


class TestFetchTreasuryYield(unittest.TestCase):

    @patch('data_sources.alpha_vantage_fetcher.get_api_key')
    @patch('data_sources.alpha_vantage_fetcher.requests.get')
    def test_fetch_treasury_yield_success(self, mock_get, mock_get_key):
        """測試成功抓取美債殖利率"""
        mock_get_key.return_value = 'test_key'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'date': '2026-03-04', 'value': '4.52'}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_treasury_yield('3month')

        self.assertEqual(result, 4.52)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs['params']['function'], 'TREASURY_YIELD')
        self.assertEqual(call_kwargs['params']['maturity'], '3month')

    def test_fetch_treasury_yield_invalid_maturity(self):
        """測試無效期限參數"""
        with self.assertRaises(ValueError):
            fetch_treasury_yield('invalid')

    @patch('data_sources.alpha_vantage_fetcher.get_api_key')
    def test_fetch_treasury_yield_no_api_key(self, mock_get_key):
        """測試無 API key 時回傳 None"""
        mock_get_key.return_value = None
        result = fetch_treasury_yield('3month')
        self.assertIsNone(result)

    @patch('data_sources.alpha_vantage_fetcher.get_api_key')
    @patch('data_sources.alpha_vantage_fetcher.requests.get')
    def test_fetch_treasury_yield_network_error(self, mock_get, mock_get_key):
        """測試網路錯誤時回傳 None"""
        mock_get_key.return_value = 'test_key'
        mock_get.side_effect = requests.Timeout()
        result = fetch_treasury_yield('3month')
        self.assertIsNone(result)

    @patch('data_sources.alpha_vantage_fetcher.get_api_key')
    @patch('data_sources.alpha_vantage_fetcher.requests.get')
    def test_fetch_treasury_yield_empty_data(self, mock_get, mock_get_key):
        """測試空資料回應時回傳 None"""
        mock_get_key.return_value = 'test_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        result = fetch_treasury_yield('3month')
        self.assertIsNone(result)

    @patch('data_sources.alpha_vantage_fetcher.get_api_key')
    @patch('data_sources.alpha_vantage_fetcher.requests.get')
    def test_fetch_treasury_yield_dot_value(self, mock_get, mock_get_key):
        """測試 Alpha Vantage 回傳 '.' 值時回傳 None"""
        mock_get_key.return_value = 'test_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'date': '2026-03-04', 'value': '.'}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        result = fetch_treasury_yield('3month')
        self.assertIsNone(result)
