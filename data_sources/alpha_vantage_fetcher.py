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
