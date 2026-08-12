
import os
import sys
import time
import sqlite3

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for chart saving
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import config
from data_ingestion import run_ingestion
from signal_engine import run_signal_engine
from screener import run_screener, get_screening_funnel
from backtester import run_backtester
from reconciliation import run_reconciliation


# ---
# Helpers
# ---

def _elapsed(start: float) -> str:
    secs = time.time() - start
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{secs / 60:.1f}m"


def _ensure_reports_dir():
    os.makedirs(config.REPORTS_DIR, exist_ok=True)


# ---
# Report Generation
# ---

def generate_equity_curve(db_path: str, save_path: str):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM backtest_results ORDER BY date", conn)
    conn.close()

    if df.empty:
        print("Warning: No backtest results to chart.")
        return

    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    # Normalize to $100 start for visual comparison
    port_norm = 100 * df["portfolio_value"] / df["portfolio_value"].iloc[0]
    bench_norm = 100 * df["benchmark_value"] / df["benchmark_value"].iloc[0]

    ax.plot(df["date"], port_norm, color="#58a6ff", linewidth=1.8,
            label="Strategy Portfolio", zorder=3)
    ax.plot(df["date"], bench_norm, color="#8b949e", linewidth=1.2,
            linestyle="--", label="SPY Benchmark", alpha=0.8, zorder=2)

    ax.fill_between(df["date"], port_norm, bench_norm,
                     where=(port_norm >= bench_norm),
                     color="#58a6ff", alpha=0.08, interpolate=True)
    ax.fill_between(df["date"], port_norm, bench_norm,
                     where=(port_norm < bench_norm),
                     color="#f85149", alpha=0.08, interpolate=True)

    ax.set_title("Portfolio vs. SPY Benchmark", fontsize=16,
                 color="#c9d1d9", fontweight="bold", pad=15)
    ax.set_xlabel("Date", fontsize=11, color="#8b949e")
    ax.set_ylabel("Normalized Value ($100 start)", fontsize=11, color="#8b949e")

    ax.legend(fontsize=10, loc="upper left",
              facecolor="#161b22", edgecolor="#30363d",
              labelcolor="#c9d1d9")

    ax.tick_params(colors="#8b949e")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#30363d")
    ax.spines["bottom"].set_color("#30363d")
    ax.grid(True, alpha=0.15, color="#30363d")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    print(f"Saved equity curve to {save_path}")


def generate_signal_heatmap(db_path: str, save_path: str):
    conn = sqlite3.connect(db_path)

    # Get latest date
    latest = pd.read_sql(
        "SELECT MAX(date) as d FROM signals", conn
    )["d"].iloc[0]

    if latest is None:
        print("Warning: No signals data for heatmap.")
        conn.close()
        return

    df = pd.read_sql(
        f"""
        SELECT ticker, momentum_20, momentum_60, momentum_252,
               volatility_20, rolling_return_20
        FROM signals
        WHERE date = '{latest}'
        ORDER BY ticker
        """,
        conn,
    )
    conn.close()

    if df.empty:
        print("Warning: No signal rows found for heatmap.")
        return

    df = df.set_index("ticker")
    df.columns = ["Mom 20d", "Mom 60d", "Mom 252d", "Vol 20d", "Roll Ret 20d"]

    fig, ax = plt.subplots(figsize=(12, max(5, len(df) * 0.45)))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    # Custom diverging colormap
    data = df.values.astype(float)
    vmax = max(abs(np.nanmin(data)), abs(np.nanmax(data)), 0.01)

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto",
                   vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(len(df.columns)))
    ax.set_xticklabels(df.columns, fontsize=10, color="#c9d1d9")
    ax.set_yticks(range(len(df.index)))
    ax.set_yticklabels(df.index, fontsize=10, color="#c9d1d9")

    # Annotate cells
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            val = data[i, j]
            if not np.isnan(val):
                txt = f"{val:.1%}" if abs(val) < 10 else f"{val:.0f}"
                text_color = "#0d1117" if abs(val) > vmax * 0.6 else "#c9d1d9"
                ax.text(j, i, txt, ha="center", va="center",
                        fontsize=9, color=text_color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.ax.tick_params(colors="#8b949e")
    cbar.outline.set_edgecolor("#30363d")

    ax.set_title(f"Signal Heatmap — {latest}", fontsize=14,
                 color="#c9d1d9", fontweight="bold", pad=12)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    print(f"Saved heatmap to {save_path}")


def generate_screening_funnel(db_path: str, save_path: str):
    funnel = get_screening_funnel(db_path)

    if not funnel:
        print("Warning: No screening data for funnel chart.")
        return

    stages = [f["stage"] for f in funnel]
    counts = [f["count"] for f in funnel]
    max_count = max(counts) if counts else 1

    # Color gradient from blue to green
    colors = []
    for i, c in enumerate(counts):
        ratio = c / max_count if max_count > 0 else 0
        r = int(88 * (1 - ratio) + 35 * ratio)
        g = int(166 * ratio + 100 * (1 - ratio))
        b = int(255 * (1 - ratio) + 134 * ratio)
        colors.append(f"#{r:02x}{g:02x}{b:02x}")

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    bars = ax.barh(stages[::-1], counts[::-1], color=colors[::-1],
                   edgecolor="#30363d", linewidth=0.5, height=0.6)

    for bar, count in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=12,
                color="#c9d1d9", fontweight="bold")

    ax.set_title("Stock Screening Funnel", fontsize=14,
                 color="#c9d1d9", fontweight="bold", pad=12)
    ax.set_xlabel("Number of Tickers", fontsize=11, color="#8b949e")

    ax.tick_params(colors="#8b949e")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#30363d")
    ax.spines["bottom"].set_color("#30363d")
    ax.set_xlim(0, max_count + 2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    print(f"Saved funnel to {save_path}")


# ---
# Pipeline Orchestrator
# ---

def run_pipeline():

    print("\n=== Marko - The Market data pipeline ===")
    print(f"Running {len(config.TICKERS)} tickers | {config.START_DATE} to {config.END_DATE}\n")
    print(f"  Tickers:    {len(config.TICKERS)} + benchmark ({config.BENCHMARK})")
    print(f"  Date range: {config.START_DATE} -> {config.END_DATE}")
    print(f"  Database:   {config.DB_PATH}")
    print()

    stages = []
    overall_start = time.time()

    # Stage 1: Data Ingestion
    print("[1/6] Data Ingestion")
    t0 = time.time()
    try:
        ingest_result = run_ingestion()
        status = "OK"
        detail = (
            f"fetched {ingest_result.get('tickers_processed', '?')} tickers, "
            f"{ingest_result.get('total_price_rows', '?')} price rows"
        )
    except Exception as e:
        status = "FAIL"
        detail = str(e)
        print(f"[1/6] ERROR: {e}")
    stages.append(("Data Ingestion", status, detail, _elapsed(t0)))
    print()

    # Stage 2: Signal Computation
    print("[2/6] Signal Computation")
    t0 = time.time()
    try:
        signal_result = run_signal_engine()
        status = "OK"
        detail = (
            f"{signal_result.get('tickers_processed', '?')} tickers, "
            f"{signal_result.get('total_signal_rows', '?')} signal rows"
        )
    except Exception as e:
        status = "FAIL"
        detail = str(e)
        print(f"[2/6] ERROR: {e}")
    stages.append(("Signal Computation", status, detail, _elapsed(t0)))
    print()

    # Stage 3: Stock Screening
    print("[3/6] Stock Screening")
    t0 = time.time()
    try:
        screened_df = run_screener()
        status = "OK"
        detail = f"{len(screened_df)}/{len(config.TICKERS)} tickers passed"
    except Exception as e:
        status = "FAIL"
        detail = str(e)
        print(f"[3/6] ERROR: {e}")
    stages.append(("Stock Screening", status, detail, _elapsed(t0)))
    print()

    # Stage 4: Backtesting
    print("[4/6] Backtesting")
    t0 = time.time()
    try:
        bt_result = run_backtester()
        status = "OK"
        metrics = bt_result.get("metrics", {})
        detail = (
            f"{metrics.get('num_rebalances', '?')} rebalances, "
            f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}"
        )
    except Exception as e:
        status = "FAIL"
        detail = str(e)
        print(f"[4/6] ERROR: {e}")
    stages.append(("Backtesting", status, detail, _elapsed(t0)))
    print()

    # Stage 5: Reconciliation
    print("[5/6] Reconciliation")
    t0 = time.time()
    try:
        recon_results = run_reconciliation()
        passed = sum(1 for r in recon_results if r["passed"])
        total = len(recon_results)
        status = "OK" if passed == total else "WARN"
        detail = f"{passed}/{total} checks passed"
    except Exception as e:
        status = "FAIL"
        detail = str(e)
        print(f"[5/6] ERROR: {e}")
    stages.append(("Reconciliation", status, detail, _elapsed(t0)))
    print()

    # Stage 6: Report Generation
    print("[6/6] Report Generation")
    t0 = time.time()
    _ensure_reports_dir()
    n_charts = 0
    try:
        generate_equity_curve(
            config.DB_PATH,
            os.path.join(config.REPORTS_DIR, "equity_curve.png"),
        )
        n_charts += 1
    except Exception as e:
        print(f"Warning: failed to generate equity curve: {e}")

    try:
        generate_signal_heatmap(
            config.DB_PATH,
            os.path.join(config.REPORTS_DIR, "signal_heatmap.png"),
        )
        n_charts += 1
    except Exception as e:
        print(f"Warning: failed to generate signal heatmap: {e}")

    try:
        generate_screening_funnel(
            config.DB_PATH,
            os.path.join(config.REPORTS_DIR, "screening_funnel.png"),
        )
        n_charts += 1
    except Exception as e:
        print(f"Warning: failed to generate screening funnel: {e}")

    try:
        import dashboard
        dashboard.main()
    except Exception as e:
        print(f"Warning: failed to generate HTML dashboard: {e}")

    status = "OK" if n_charts == 3 else "WARN"
    detail = f"{n_charts}/3 charts + dashboard"
    stages.append(("Report Generation", status, detail, _elapsed(t0)))
    print()

    # --- Pipeline Summary ---
    print("\nPipeline Summary:")
    for name, status, detail, elapsed in stages:
        print(f"[{status}] {name} - {detail} ({elapsed})")
    print(f"Total time: {_elapsed(overall_start)}\n")


if __name__ == "__main__":
    run_pipeline()
