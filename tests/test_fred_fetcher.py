"""FRED fetcher 單元測試"""
import datetime
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from data_sources.fred_fetcher import (
    calc_direct,
    calc_direct_k,
    calc_diff,
    calc_mom,
    calc_yoy,
    determine_trend,
    fetch_all_us_macro,
    fetch_single_indicator,
    format_date_note,
    format_value,
    get_fred_api_key,
)


# --- determine_trend ---

class TestDetermineTrend:
    def test_up(self):
        assert determine_trend(3.5, 2.1) == "up"

    def test_down(self):
        assert determine_trend(2.1, 3.5) == "down"

    def test_flat(self):
        assert determine_trend(3.0, 3.0) == "flat"

    def test_none_current(self):
        assert determine_trend(None, 3.0) == "neutral"

    def test_none_previous(self):
        assert determine_trend(3.0, None) == "neutral"

    def test_both_none(self):
        assert determine_trend(None, None) == "neutral"


# --- calc_yoy ---

class TestCalcYoy:
    def _make_series(self, values, start="2024-01-01", freq="MS"):
        dates = pd.date_range(start=start, periods=len(values), freq=freq)
        return pd.Series(values, index=dates)

    def test_basic_yoy(self):
        # 14 months: index 0..13, latest=index[-1], year_ago=index[-13]
        values = [100.0] * 13 + [105.0]
        series = self._make_series(values)
        current, previous, date = calc_yoy(series)
        assert current == pytest.approx(5.0)
        assert previous is not None
        assert date == series.index[-1]

    def test_insufficient_data(self):
        series = self._make_series([100.0] * 10)
        assert calc_yoy(series) == (None, None, None)

    def test_zero_year_ago(self):
        values = [0.0] * 13 + [105.0]
        series = self._make_series(values)
        assert calc_yoy(series) == (None, None, None)


# --- calc_mom ---

class TestCalcMom:
    def _make_series(self, values):
        dates = pd.date_range(start="2025-01-01", periods=len(values), freq="MS")
        return pd.Series(values, index=dates)

    def test_basic_mom(self):
        series = self._make_series([100.0, 102.0, 105.0])
        current, previous, date = calc_mom(series)
        # (105-102)/102 * 100 = 2.941...
        assert current == pytest.approx(2.9411, rel=1e-2)
        # (102-100)/100 * 100 = 2.0
        assert previous == pytest.approx(2.0)

    def test_insufficient_data(self):
        series = self._make_series([100.0, 102.0])
        assert calc_mom(series) == (None, None, None)

    def test_zero_prev(self):
        series = self._make_series([100.0, 0.0, 105.0])
        assert calc_mom(series) == (None, None, None)


# --- calc_diff ---

class TestCalcDiff:
    def _make_series(self, values):
        dates = pd.date_range(start="2025-01-01", periods=len(values), freq="MS")
        return pd.Series(values, index=dates)

    def test_basic_diff(self):
        series = self._make_series([150000, 150100, 150250])
        current, previous, date = calc_diff(series, divisor=10)
        # (150250 - 150100) / 10 = 15.0
        assert current == pytest.approx(15.0)
        # (150100 - 150000) / 10 = 10.0
        assert previous == pytest.approx(10.0)

    def test_insufficient_data(self):
        series = self._make_series([150000, 150100])
        assert calc_diff(series) == (None, None, None)


# --- calc_direct ---

class TestCalcDirect:
    def _make_series(self, values):
        dates = pd.date_range(start="2025-01-01", periods=len(values), freq="MS")
        return pd.Series(values, index=dates)

    def test_basic_direct(self):
        series = self._make_series([4.1, 4.3])
        current, previous, date = calc_direct(series)
        assert current == pytest.approx(4.3)
        assert previous == pytest.approx(4.1)

    def test_insufficient_data(self):
        series = self._make_series([4.1])
        assert calc_direct(series) == (None, None, None)


# --- calc_direct_k ---

class TestCalcDirectK:
    def _make_series(self, values):
        dates = pd.date_range(start="2025-01-01", periods=len(values), freq="W")
        return pd.Series(values, index=dates)

    def test_with_divisor(self):
        series = self._make_series([210000, 206000])
        current, previous, date = calc_direct_k(series, divisor=10000)
        assert current == pytest.approx(20.6)
        assert previous == pytest.approx(21.0)


# --- format_date_note ---

class TestFormatDateNote:
    def test_quarterly(self):
        date = pd.Timestamp("2025-10-15")
        assert format_date_note(date, "quarterly") == "2025 Q4"

    def test_quarterly_q1(self):
        date = pd.Timestamp("2026-01-31")
        assert format_date_note(date, "quarterly") == "2026 Q1"

    def test_monthly_with_label(self):
        date = pd.Timestamp("2026-01-15")
        result = format_date_note(date, "monthly", "YoY")
        assert result == "2026-01 (YoY)"

    def test_monthly_no_label(self):
        date = pd.Timestamp("2026-02-28")
        result = format_date_note(date, "monthly")
        assert result == "2026-02"

    def test_weekly(self):
        date = pd.Timestamp("2026-02-14")
        result = format_date_note(date, "weekly")
        assert result == "截至 2/14"


# --- format_value ---

class TestFormatValue:
    def test_none(self):
        assert format_value(None, "%", "direct") == "N/A"

    def test_diff_positive(self):
        assert format_value(13.5, "萬", "diff") == "+13.5萬"

    def test_diff_negative(self):
        assert format_value(-5.2, "萬", "diff") == "-5.2萬"

    def test_yoy(self):
        assert format_value(3.1, "%", "yoy") == "3.1%"

    def test_direct_percent(self):
        assert format_value(4.3, "%", "direct") == "4.3%"

    def test_direct_no_suffix(self):
        assert format_value(52.6, "", "direct") == "52.6"


# --- get_fred_api_key ---

class TestGetFredApiKey:
    def test_env_var_priority(self):
        with patch.dict("os.environ", {"FRED_API_KEY": "env_key"}):
            config = {"api_keys": {"fred": "config_key"}}
            assert get_fred_api_key(config) == "env_key"

    def test_config_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure FRED_API_KEY is not set
            import os
            env_backup = os.environ.pop("FRED_API_KEY", None)
            try:
                config = {"api_keys": {"fred": "config_key"}}
                assert get_fred_api_key(config) == "config_key"
            finally:
                if env_backup is not None:
                    os.environ["FRED_API_KEY"] = env_backup

    def test_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            env_backup = os.environ.pop("FRED_API_KEY", None)
            try:
                assert get_fred_api_key(None) == ""
            finally:
                if env_backup is not None:
                    os.environ["FRED_API_KEY"] = env_backup


# --- fetch_single_indicator ---

class TestFetchSingleIndicator:
    def _make_monthly_series(self, values, start="2024-01-01"):
        dates = pd.date_range(start=start, periods=len(values), freq="MS")
        return pd.Series(values, index=dates)

    def test_direct_indicator(self):
        fred_mock = MagicMock()
        series = self._make_monthly_series([4.0, 4.1, 4.3])
        fred_mock.get_series.return_value = series

        indicator = {
            "series_id": "UNRATE",
            "name": "失業率",
            "calc": "direct",
            "suffix": "%",
            "frequency": "monthly",
        }
        result = fetch_single_indicator(fred_mock, indicator)
        assert result is not None
        assert result["name"] == "失業率"
        assert result["value"] == "4.3%"
        assert result["trend"] == "up"

    def test_yoy_indicator(self):
        fred_mock = MagicMock()
        # 14 months: index 0 = 100, ..., index 12 = 100, index 13 = 103
        values = [100.0] * 13 + [103.0]
        series = self._make_monthly_series(values)
        fred_mock.get_series.return_value = series

        indicator = {
            "series_id": "CPIAUCSL",
            "name": "消費者物價指數 (CPI)",
            "calc": "yoy",
            "suffix": "%",
            "frequency": "monthly",
            "note_label": "YoY",
        }
        result = fetch_single_indicator(fred_mock, indicator)
        assert result is not None
        assert "3.0%" in result["value"]
        assert result["note"].endswith("(YoY)")

    def test_insufficient_data_returns_none(self):
        fred_mock = MagicMock()
        series = pd.Series([100.0], index=[pd.Timestamp("2025-01-01")])
        fred_mock.get_series.return_value = series

        indicator = {
            "series_id": "TEST",
            "name": "Test",
            "calc": "direct",
            "suffix": "",
            "frequency": "monthly",
        }
        result = fetch_single_indicator(fred_mock, indicator)
        assert result is None


# --- fetch_all_us_macro ---

class TestFetchAllUsMacro:
    def test_no_api_key_returns_empty(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            env_backup = os.environ.pop("FRED_API_KEY", None)
            try:
                result = fetch_all_us_macro(api_key="", config={})
                assert result == []
            finally:
                if env_backup is not None:
                    os.environ["FRED_API_KEY"] = env_backup

    @patch("data_sources.fred_fetcher.FREDAPI_AVAILABLE", False)
    def test_fredapi_not_installed(self):
        result = fetch_all_us_macro(api_key="test_key")
        assert result == []

    @patch("data_sources.fred_fetcher.Fred")
    def test_partial_failure_still_returns_results(self, mock_fred_cls):
        """單一指標失敗不影響其他指標"""
        mock_fred = MagicMock()
        mock_fred_cls.return_value = mock_fred

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("API error")
            dates = pd.date_range(start="2024-01-01", periods=15, freq="MS")
            return pd.Series([100.0] * 14 + [103.0], index=dates)

        mock_fred.get_series.side_effect = side_effect

        result = fetch_all_us_macro(api_key="test_key")
        # 第一個指標失敗，其餘應該成功
        assert len(result) >= 1
        assert len(result) < 11  # 不可能全部成功因為 diff/direct_k 需要不同邏輯

    @patch("data_sources.fred_fetcher.Fred")
    def test_output_format(self, mock_fred_cls):
        """測試輸出格式符合 macro_cache.json 規範"""
        mock_fred = MagicMock()
        mock_fred_cls.return_value = mock_fred

        dates = pd.date_range(start="2024-01-01", periods=15, freq="MS")
        mock_fred.get_series.return_value = pd.Series(
            [100.0] * 14 + [103.0], index=dates
        )

        result = fetch_all_us_macro(api_key="test_key")
        for item in result:
            assert "name" in item
            assert "value" in item
            assert "trend" in item
            assert "note" in item
            assert "last_updated" in item
            assert item["trend"] in ("up", "down", "flat", "neutral")
