# Pipeline config

import os
from datetime import date

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "market_data.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Ticker Universe
TICKERS = [
    "AAPL",   # Tech
    "MSFT",   # Tech
    "GOOGL",  # Tech / Communication
    "AMZN",   # Consumer Discretionary
    "NVDA",   # Semiconductors
    "TSLA",   # Consumer Discretionary / Auto
    "JPM",    # Financials
    "BAC",    # Financials
    "V",      # Financials / Payments
    "MA",     # Financials / Payments
    "JNJ",    # Healthcare
    "UNH",    # Healthcare
    "PG",     # Consumer Staples
    "HD",     # Consumer Discretionary
    "XOM",    # Energy
]

BENCHMARK = "SPY"  # S&P 500 ETF for comparison

# Date Range
START_DATE = date(2020, 1, 1)
END_DATE = date(2025, 12, 31)

# Signal Parameters
ROLLING_WINDOWS = {
    "short": 20,     # ~1 month
    "medium": 60,    # ~3 months
    "long": 252,     # ~1 year
}

SMA_WINDOWS = {
    "fast": 50,
    "slow": 200,
}

# Stock Screening Thresholds
SCREEN_RULES = {
    "pe_max": 25.0,          # P/E ratio upper bound
    "pe_min": 0.0,           # Exclude negative earnings
    "market_cap_min": 1e10,  # $10 billion floor
    "beta_min": 0.5,
    "beta_max": 1.5,
    "momentum_60d_min": 0.0, # Require positive 60-day momentum
}

# Backtest Parameters
INITIAL_CAPITAL = 100_000.0
REBALANCE_FREQ = "Q"            # Quarterly rebalancing
TRANSACTION_COST_BPS = 10       # 10 basis points per trade
RISK_FREE_RATE = 0.04           # 4% annual for Sharpe calculation

# Data Ingestion
YFINANCE_PAUSE_SECONDS = 0.5    # Delay between API calls to avoid throttling
MAX_RETRIES = 3                 # Retry count for failed downloads
