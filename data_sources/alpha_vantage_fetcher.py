"""Alpha Vantage API 資料抓取模組

透過 Alpha Vantage API 抓取美債殖利率資料，作為 yfinance 的備援數據源。
"""
import os
import json
import requests
from pathlib import Path


def get_api_key():
    """取得 Alpha Vantage API key

    優先順序：
    1. 環境變數 ALPHA_VANTAGE_API_KEY
    2. config.json > api_keys.alpha_vantage

    Returns:
        str or None: API key，若都不存在則回傳 None
    """
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    if api_key:
        return api_key

    try:
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            api_key = config.get('api_keys', {}).get('alpha_vantage')
            if api_key:
                return api_key
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    return None


VALID_MATURITIES = {'3month', '2year', '5year', '7year', '10year', '30year'}

API_BASE_URL = 'https://www.alphavantage.co/query'


def fetch_treasury_yield(maturity, timeout=10):
    """抓取美債殖利率

    Args:
        maturity (str): 期限，可選 '3month', '2year', '5year', '7year', '10year', '30year'
        timeout (int): 請求超時時間（秒）

    Returns:
        float or None: 殖利率（百分比），失敗時回傳 None
    """
    if maturity not in VALID_MATURITIES:
        raise ValueError(f"Invalid maturity: {maturity}. Must be one of {VALID_MATURITIES}")

    api_key = get_api_key()
    if not api_key:
        return None

    params = {
        'function': 'TREASURY_YIELD',
        'interval': 'daily',
        'maturity': maturity,
        'apikey': api_key
    }

    try:
        response = requests.get(API_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            latest = data['data'][0]
            value = latest.get('value', '.')
            if value == '.':
                return None
            return float(value)

        return None

    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None
