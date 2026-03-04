"""美債殖利率統一介面測試"""
import unittest
from unittest.mock import patch, Mock
import pandas as pd
from data_sources.yield_fetcher import get_treasury_yields


class TestYieldFetcher(unittest.TestCase):

    @patch('data_sources.yield_fetcher.fetch_treasury_yield')
    def test_get_treasury_yields_alpha_vantage_success(self, mock_fetch):
        """測試 Alpha Vantage 成功時使用該資料"""
        mock_fetch.side_effect = [4.52, 4.18, 4.35]  # 3M, 10Y, 30Y

        result = get_treasury_yields()

        self.assertEqual(result['3month'], 4.52)
        self.assertEqual(result['10year'], 4.18)
        self.assertEqual(result['30year'], 4.35)
        self.assertEqual(result['source'], 'alpha_vantage')
        self.assertIn('fetched_at', result)

    @patch('data_sources.yield_fetcher.fetch_treasury_yield')
    @patch('data_sources.yield_fetcher.yf.download')
    def test_get_treasury_yields_fallback_to_yfinance(self, mock_yf, mock_fetch):
        """測試 Alpha Vantage 失敗時 fallback 至 yfinance"""
        mock_fetch.return_value = None  # Alpha Vantage 失敗

        mock_df_3m = pd.DataFrame({'Close': [4.50]}, index=[pd.Timestamp('2026-03-04')])
        mock_df_10y = pd.DataFrame({'Close': [4.15]}, index=[pd.Timestamp('2026-03-04')])
        mock_df_30y = pd.DataFrame({'Close': [4.30]}, index=[pd.Timestamp('2026-03-04')])
        mock_yf.side_effect = [mock_df_3m, mock_df_10y, mock_df_30y]

        result = get_treasury_yields()

        self.assertEqual(result['source'], 'yfinance')
        self.assertAlmostEqual(result['3month'], 4.50)
        self.assertAlmostEqual(result['10year'], 4.15)
        self.assertAlmostEqual(result['30year'], 4.30)

    @patch('data_sources.yield_fetcher.fetch_treasury_yield')
    @patch('data_sources.yield_fetcher.yf.download')
    def test_get_treasury_yields_both_fail(self, mock_yf, mock_fetch):
        """測試兩個來源都失敗時回傳 source='none'"""
        mock_fetch.return_value = None
        mock_yf.return_value = pd.DataFrame()  # empty

        result = get_treasury_yields()

        self.assertEqual(result['source'], 'none')
        self.assertIsNone(result['3month'])

    @patch('data_sources.yield_fetcher.fetch_treasury_yield')
    def test_get_treasury_yields_partial_alpha_vantage_failure(self, mock_fetch):
        """測試 Alpha Vantage 部分成功時 fallback"""
        mock_fetch.side_effect = [4.52, None, 4.35]  # 10Y 失敗

        # Should fallback since not all succeeded
        # Need to mock yfinance too since it will be called
        with patch('data_sources.yield_fetcher.yf.download') as mock_yf:
            mock_yf.return_value = pd.DataFrame()  # yfinance also fails
            result = get_treasury_yields()
            self.assertEqual(result['source'], 'none')
