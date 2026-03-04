"""Alpha Vantage API 抓取模組測試"""
import os
import json
import unittest
from unittest.mock import patch, mock_open
from data_sources.alpha_vantage_fetcher import get_api_key


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
