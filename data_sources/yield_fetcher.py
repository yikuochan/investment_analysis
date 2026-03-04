"""美債殖利率統一介面

整合 Alpha Vantage 與 yfinance，提供 fallback 機制。
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from data_sources.alpha_vantage_fetcher import fetch_treasury_yield


MATURITY_CONFIG = {
    '3month': {'alpha_vantage': '3month', 'yfinance': '^IRX'},
    '10year': {'alpha_vantage': '10year', 'yfinance': '^TNX'},
    '30year': {'alpha_vantage': '30year', 'yfinance': '^TYX'}
}


def get_treasury_yields():
    """取得美債殖利率（含 fallback 機制）

    優先使用 Alpha Vantage，失敗時自動切換至 yfinance。

    Returns:
        dict: {
            '3month': float or None,
            '10year': float or None,
            '30year': float or None,
            'source': str,  # 'alpha_vantage', 'yfinance', 或 'none'
            'fetched_at': str  # ISO 8601 時間戳
        }
    """
    result = {
        '3month': None,
        '10year': None,
        '30year': None,
        'source': 'none',
        'fetched_at': datetime.now(timezone.utc).isoformat()
    }

    # 1. 嘗試 Alpha Vantage
    alpha_vantage_success = True
    for maturity_key, config in MATURITY_CONFIG.items():
        value = fetch_treasury_yield(config['alpha_vantage'])
        if value is not None:
            result[maturity_key] = value
        else:
            alpha_vantage_success = False
            break

    if alpha_vantage_success and result['3month'] is not None:
        result['source'] = 'alpha_vantage'
        print("[Info] 美債殖利率已透過 Alpha Vantage API 取得")
        return result

    # 重設失敗的部分結果
    for key in MATURITY_CONFIG:
        result[key] = None

    # 2. Fallback 至 yfinance
    print("[Warning] Alpha Vantage API 失敗，已切換至 yfinance 備援")

    yfinance_success = True
    for maturity_key, config in MATURITY_CONFIG.items():
        try:
            symbol = config['yfinance']
            df = yf.download(symbol, period='5d', progress=False, auto_adjust=True)

            if df.empty:
                yfinance_success = False
                break

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            latest_value = df['Close'].iloc[-1]
            result[maturity_key] = float(latest_value)

        except Exception:
            yfinance_success = False
            break

    if yfinance_success and result['3month'] is not None:
        result['source'] = 'yfinance'
        return result

    # 3. 完全失敗
    for key in MATURITY_CONFIG:
        result[key] = None
    print("[Error] 無法取得美債殖利率資料 (Alpha Vantage 和 yfinance 皆失敗)")
    return result
