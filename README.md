# Marko - The Market data pipeline

Python + SQL pipeline that pulls historical stock data, computes technical signals, screens by fundamentals, and backtests a simple momentum strategy. Built this to automate what I was doing manually in spreadsheets.

## What it does

1. **Ingestion** — fetches OHLCV prices + fundamentals from yfinance into SQLite
2. **Signals** — computes rolling returns, volatility, momentum, SMAs, golden/death cross
3. **Screener** — filters stocks by P/E, market cap, beta, and momentum
4. **Backtest** — runs a quarterly-rebalanced equal-weight strategy with transaction costs
5. **Reconciliation** — 7 SQL checks to validate data integrity
6. **Dashboard** — generates a standalone HTML dashboard with all the results

## Backtest results (2020–2025)

| Metric | Strategy | SPY |
|--------|----------|-----|
| Total Return | 477.0% | ~132% |
| CAGR | 34.0% | ~14.9% |
| Sharpe | 1.43 | ~0.78 |
| Max Drawdown | -27.8% | -24.5% |

$100k initial, quarterly rebalancing, 10bps transaction cost.

## Setup

```bash
git clone https://github.com/Darkdoc0/Marko.git
cd Marko
pip install -r requirements.txt
python main.py
```

This runs the full pipeline and opens the dashboard in your browser.

You can also run modules individually:
```bash
python data_ingestion.py
python signal_engine.py
python screener.py
python backtester.py
python reconciliation.py
python dashboard.py
```

## Config

Everything is in `config.py` — tickers, date range, screening thresholds, rebalance frequency, transaction costs, etc.

## Schema

Four tables in `market_data.db`:

- `price_history` — raw OHLCV data, PK on (ticker, date)
- `fundamentals` — P/E, market cap, beta, sector per ticker
- `signals` — computed technical indicators per ticker per day
- `backtest_results` — daily portfolio + benchmark values

## Files

```
config.py            — parameters and thresholds
data_ingestion.py    — yfinance -> SQLite
signal_engine.py     — rolling returns, vol, momentum, SMAs
screener.py          — fundamental + momentum filtering
backtester.py        — strategy simulation
reconciliation.py    — data quality checks
main.py              — runs everything
dashboard.py         — HTML dashboard generator
create_pdf.py        — builds a PDF study guide
reports/             — generated charts
```
