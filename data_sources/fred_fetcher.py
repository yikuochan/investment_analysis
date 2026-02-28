"""FRED API 美國總經指標抓取模組

透過 FRED (Federal Reserve Economic Data) API 程式化抓取美國總經數據，
減少對 AI web search 的依賴。
"""
import os
import datetime
import warnings

try:
    from fredapi import Fred
    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False


# FRED Series ID 對應表
FRED_INDICATORS = [
    {
        "series_id": "A191RL1Q225SBEA",
        "name": "國內生產毛額 (GDP)",
        "calc": "direct",
        "suffix": "%",
        "frequency": "quarterly",
    },
    {
        "series_id": "CPIAUCSL",
        "name": "消費者物價指數 (CPI)",
        "calc": "yoy",
        "suffix": "%",
        "frequency": "monthly",
        "note_label": "YoY",
    },
    {
        "series_id": "CPILFESL",
        "name": "核心消費者物價指數 (Core CPI)",
        "calc": "yoy",
        "suffix": "%",
        "frequency": "monthly",
        "note_label": "YoY",
    },
    {
        "series_id": "PPIACO",
        "name": "生產者物價指數 (PPI)",
        "calc": "yoy",
        "suffix": "%",
        "frequency": "monthly",
        "note_label": "YoY",
    },
    {
        "series_id": "RSAFS",
        "name": "零售銷售 (Retail Sales)",
        "calc": "mom",
        "suffix": "%",
        "frequency": "monthly",
        "note_label": "MoM",
    },
    {
        "series_id": "PAYEMS",
        "name": "非農就業人口",
        "calc": "diff",
        "suffix": "萬",
        "frequency": "monthly",
        "divisor": 10,  # 千人 -> 萬人
    },
    {
        "series_id": "UNRATE",
        "name": "失業率",
        "calc": "direct",
        "suffix": "%",
        "frequency": "monthly",
    },
    {
        "series_id": "ICSA",
        "name": "初領失業金人數",
        "calc": "direct_k",
        "suffix": "萬",
        "frequency": "weekly",
        "divisor": 10000,  # 人 -> 萬人
    },
    {
        "series_id": "UMCSENT",
        "name": "密西根消費者信心指數",
        "calc": "direct",
        "suffix": "",
        "frequency": "monthly",
    },
    {
        "series_id": "FEDFUNDS",
        "name": "聯邦基金利率",
        "calc": "direct",
        "suffix": "%",
        "frequency": "monthly",
    },
    {
        "series_id": "M2SL",
        "name": "M2 貨幣供給",
        "calc": "yoy",
        "suffix": "%",
        "frequency": "monthly",
        "note_label": "YoY",
    },
]


def get_fred_api_key(config=None):
    """取得 FRED API key，優先讀取環境變數，其次讀取 config"""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key and config:
        api_key = config.get("api_keys", {}).get("fred", "")
    return api_key


def determine_trend(current, previous):
    """比較前兩期數值決定趨勢方向"""
    if current is None or previous is None:
        return "neutral"
    diff = current - previous
    if abs(diff) < 1e-9:
        return "flat"
    return "up" if diff > 0 else "down"


def format_date_note(date, frequency, note_label=None):
    """根據頻率格式化日期附註"""
    if frequency == "quarterly":
        quarter = (date.month - 1) // 3 + 1
        return f"{date.year} Q{quarter}"
    elif frequency == "weekly":
        return f"截至 {date.month}/{date.day}"
    else:
        base = f"{date.year}-{date.month:02d}"
        if note_label:
            return f"{base} ({note_label})"
        return base


def calc_yoy(series):
    """計算年增率 (YoY%)：最新值 vs 12 個月前"""
    if series is None or len(series) < 13:
        return None, None, None
    latest = series.iloc[-1]
    year_ago = series.iloc[-13]
    prev_latest = series.iloc[-2]
    prev_year_ago = series.iloc[-14] if len(series) >= 14 else None

    if year_ago == 0:
        return None, None, None

    current_yoy = (latest - year_ago) / year_ago * 100

    if prev_year_ago is not None and prev_year_ago != 0:
        prev_yoy = (prev_latest - prev_year_ago) / prev_year_ago * 100
    else:
        prev_yoy = None

    return current_yoy, prev_yoy, series.index[-1]


def calc_mom(series):
    """計算月增率 (MoM%)：最新值 vs 上個月"""
    if series is None or len(series) < 3:
        return None, None, None
    latest = series.iloc[-1]
    prev = series.iloc[-2]
    prev_prev = series.iloc[-3]

    if prev == 0:
        return None, None, None

    current_mom = (latest - prev) / prev * 100

    if prev_prev != 0:
        prev_mom = (prev - prev_prev) / prev_prev * 100
    else:
        prev_mom = None

    return current_mom, prev_mom, series.index[-1]


def calc_diff(series, divisor=1):
    """計算差值（如非農就業月變化）"""
    if series is None or len(series) < 3:
        return None, None, None
    current_diff = (series.iloc[-1] - series.iloc[-2]) / divisor
    prev_diff = (series.iloc[-2] - series.iloc[-3]) / divisor
    return current_diff, prev_diff, series.index[-1]


def calc_direct(series):
    """直接取最新值"""
    if series is None or len(series) < 2:
        return None, None, None
    return series.iloc[-1], series.iloc[-2], series.index[-1]


def calc_direct_k(series, divisor=1):
    """直接取最新值並除以指定倍率"""
    if series is None or len(series) < 2:
        return None, None, None
    return series.iloc[-1] / divisor, series.iloc[-2] / divisor, series.index[-1]


def format_value(value, suffix, calc_type):
    """將數值格式化為顯示字串"""
    if value is None:
        return "N/A"
    if calc_type == "diff":
        return f"{value:+.1f}{suffix}"
    elif calc_type in ("yoy", "mom"):
        return f"{value:.1f}{suffix}"
    elif calc_type == "direct_k":
        return f"{value:.1f}{suffix}"
    elif calc_type == "direct":
        if suffix == "%":
            return f"{value:.1f}{suffix}"
        return f"{value:.1f}{suffix}" if suffix else f"{value:.1f}"
    return f"{value}{suffix}"


def fetch_single_indicator(fred, indicator):
    """抓取單一指標的 FRED 數據並計算結果"""
    series_id = indicator["series_id"]
    calc_type = indicator["calc"]
    suffix = indicator["suffix"]
    frequency = indicator.get("frequency", "monthly")
    note_label = indicator.get("note_label")
    divisor = indicator.get("divisor", 1)

    # 抓取足夠長的歷史資料以計算 YoY
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=800)  # ~2 年多的資料

    series = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
    series = series.dropna()

    if len(series) < 2:
        return None

    if calc_type == "yoy":
        current, previous, date = calc_yoy(series)
    elif calc_type == "mom":
        current, previous, date = calc_mom(series)
    elif calc_type == "diff":
        current, previous, date = calc_diff(series, divisor)
    elif calc_type == "direct_k":
        current, previous, date = calc_direct_k(series, divisor)
    else:
        current, previous, date = calc_direct(series)

    if current is None:
        return None

    trend = determine_trend(current, previous)
    value_str = format_value(current, suffix, calc_type)
    note_str = format_date_note(date, frequency, note_label)
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    return {
        "name": indicator["name"],
        "value": value_str,
        "trend": trend,
        "note": note_str,
        "last_updated": today_str,
    }


def fetch_all_us_macro(api_key=None, config=None):
    """主函式：抓取所有美國總經指標

    Args:
        api_key: FRED API key，若為 None 則從環境變數/config 讀取
        config: config.json 的內容 dict

    Returns:
        list: US_MACRO 格式的指標清單，失敗時回傳空 list
    """
    if not FREDAPI_AVAILABLE:
        print("[Warning] fredapi 套件未安裝，跳過 FRED 資料抓取。請執行: pip install fredapi")
        return []

    if api_key is None:
        api_key = get_fred_api_key(config)

    if not api_key:
        print("[Warning] 未設定 FRED API key，跳過美國總經資料抓取。")
        print("[Info] 請設定環境變數 FRED_API_KEY 或在 config.json 中設定 api_keys.fred")
        return []

    fred = Fred(api_key=api_key)
    results = []

    for indicator in FRED_INDICATORS:
        try:
            result = fetch_single_indicator(fred, indicator)
            if result:
                results.append(result)
                print(f"  [OK] {indicator['name']}: {result['value']} ({result['trend']})")
            else:
                print(f"  [Warning] {indicator['name']}: 資料不足，跳過")
        except Exception as e:
            print(f"  [Warning] {indicator['name']} 抓取失敗: {e}")

    print(f"[Info] FRED 資料抓取完成，共 {len(results)}/{len(FRED_INDICATORS)} 項指標")
    return results
