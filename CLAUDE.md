# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment analysis automation tool combining Python data processing with AI-powered analysis. Uses a **two-stage architecture**:

1. **Python script** (`investment_analysis.py`): Fetches market data via yfinance, calculates technical indicators (KD, BIAS, DMI/ADX, RSI, MACD, MA), generates K-line charts and yield curve plots as Base64, and renders an HTML report using Jinja2.
2. **AI Agent** (typically Gemini CLI): Reads the raw HTML report, searches for real financial news, collects macroeconomic data from official sources, generates analysis, and injects content into placeholder divs (`#weekly-news-focus`, `#ai-analysis-report`, `#us-macro-placeholder`, `#tw-macro-placeholder`).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis (generates HTML report in report/)
python3 investment_analysis.py
# Or with uv:
uv run investment_analysis.py

# Run tests
pytest tests/

# Run a single test
pytest tests/test_investment_analysis.py::test_determine_trend

# Full automated workflow (requires Gemini CLI)
bash run_analysis.sh
```

## Architecture

### Data Flow
`config.json` -> `investment_analysis.py` -> `templates/report_template.html` (Jinja2) -> `report/invest_analysis_YYYYMMDD.html` + `index.html` (root copy for GitHub Pages)

### Key Files
- **`investment_analysis.py`**: Single-file core script. All logic lives here: data fetching (`get_stock_data`, `get_fundamental_data`), indicator calculation (`calculate_all_indicators`), chart generation (`create_ma_plot_base64`, `create_yield_curve_plot_base64`), HTML rendering (`generate_html_report`), and orchestration (`process_stock_group`, `main`).
- **`config.json`**: Defines `stock_groups` (with symbols per group), `key_indicators` (for market snapshot cards), `inverse_symbols` (VIX-like tickers where color logic inverts), `parameters` (indicator windows, thresholds), and `symbol_name_map` (ticker to Chinese name).
- **`templates/report_template.html`**: Jinja2 template. Contains placeholder divs for AI injection. Embeds market data in `<script id="market-data">`, `<script id="fundamental-data">`, and `<script id="yield-data">` tags for AI consumption.
- **`data_sources/`**: Modular data fetching layer:
  - `fred_fetcher.py`: FRED API for US macro indicators (GDP, CPI, PPI, etc.)
  - `alpha_vantage_fetcher.py`: Alpha Vantage API for treasury yields
  - `yield_fetcher.py`: Unified yield interface with Alpha Vantage primary + yfinance fallback
- **`GEMINI.md`**: System prompt for Gemini CLI defining the full AI workflow (news collection, macro data, analysis generation, HTML injection).

### Technical Indicators Calculated
KD (Stochastic), RSI, MACD/Signal/Histogram, BIAS (5/20/60-day), DMI (+DI/-DI), ADX, Moving Averages (5/20/60), Volume Ratio. All configurable via `config.json` parameters.

### Trend Signal Logic
Trend badges use K/D crossover combined with 20-day BIAS sign:
- K > D & BIAS > 0 -> bullish-strong (多頭排列)
- K > D & BIAS < 0 -> bullish-weak (反彈)
- K < D & BIAS > 0 -> bearish-weak (回檔整理)
- K < D & BIAS < 0 -> bearish-strong (空頭修正)

### Color Convention
Uses **Taiwan stock market convention**: red for up, green for down. Inverse symbols (VIX) flip this logic via `get_color_class(inverse=True)`.

## Project Conventions

- **Language**: Code comments, log messages, and report content are in Traditional Chinese (繁體中文).
- **No Emojis**: Strict no-emoji policy in all code, logs, and report output.
- **Report output**: Reports are saved as dated files AND copied to both `index.html` (root) and `report/index.html`.
- **Dependencies**: yfinance, pandas, matplotlib, mplfinance, pytz, jinja2, requests.
- **API Keys**: FRED (`FRED_API_KEY`), Alpha Vantage (`ALPHA_VANTAGE_API_KEY`) — env var or `config.json > api_keys`.
