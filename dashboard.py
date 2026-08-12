
import os
import base64
import sqlite3
import json
from datetime import datetime

import pandas as pd
import numpy as np

import config

DB_PATH = config.DB_PATH
REPORTS_DIR = config.REPORTS_DIR


def img_to_base64(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(path)[1].lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{data}"


def generate_sparkline_svg(values, width=120, height=30, color="#58a6ff", fill=False):
    if not values or len(values) < 2:
        return ""
    vals = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    points = []
    for i, v in enumerate(vals):
        x = (i / (len(vals) - 1)) * width
        y = height - ((v - mn) / rng) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    fill_el = ""
    if fill:
        fill_points = f"0,{height} " + polyline + f" {width},{height}"
        fill_el = (
            f'<polygon fill="{color}" fill-opacity="0.1" '
            f'points="{fill_points}"/>'
        )
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'{fill_el}'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{polyline}"/>'
        f'</svg>'
    )


def load_data():
    conn = sqlite3.connect(DB_PATH)

    price_stats = pd.read_sql("""
        SELECT ticker, COUNT(*) as rows,
               MIN(date) as first_date, MAX(date) as last_date,
               ROUND(MIN(close), 2) as min_close,
               ROUND(MAX(close), 2) as max_close
        FROM price_history GROUP BY ticker ORDER BY ticker
    """, conn)

    fundamentals = pd.read_sql("SELECT * FROM fundamentals ORDER BY ticker", conn)

    latest_date = pd.read_sql("SELECT MAX(date) as d FROM signals", conn)["d"].iloc[0]
    latest_signals = pd.read_sql(f"""
        SELECT ticker,
               ROUND(daily_return * 100, 2) as daily_ret_pct,
               ROUND(momentum_20 * 100, 2) as mom_20_pct,
               ROUND(momentum_60 * 100, 2) as mom_60_pct,
               ROUND(momentum_252 * 100, 2) as mom_252_pct,
               ROUND(volatility_20 * 100, 2) as vol_20_pct,
               ROUND(volatility_60 * 100, 2) as vol_60_pct,
               ROUND(sma_50, 2) as sma_50,
               ROUND(sma_200, 2) as sma_200,
               ROUND(rolling_return_20 * 100, 2) as roll_ret_20_pct,
               ma_crossover
        FROM signals WHERE date = '{latest_date}' ORDER BY mom_60_pct DESC
    """, conn)

    backtest = pd.read_sql("SELECT * FROM backtest_results ORDER BY date", conn)

    # Per-ticker price series for sparklines (sample every 5th day for performance)
    ticker_prices = {}
    for ticker in config.TICKERS:
        df = pd.read_sql(f"""
            SELECT date, close FROM price_history
            WHERE ticker = '{ticker}' ORDER BY date
        """, conn)
        if not df.empty:
            sampled = df["close"].tolist()[::5]
            ticker_prices[ticker] = sampled

    # Metrics
    metrics = {}
    if not backtest.empty:
        initial = backtest["portfolio_value"].iloc[0]
        final = backtest["portfolio_value"].iloc[-1]
        bench_initial = backtest["benchmark_value"].iloc[0]
        bench_final = backtest["benchmark_value"].iloc[-1]
        total_return = (final / initial - 1) * 100
        bench_return = (bench_final / bench_initial - 1) * 100
        days = (pd.to_datetime(backtest["date"].iloc[-1]) - pd.to_datetime(backtest["date"].iloc[0])).days
        years = days / 365.25 if days > 0 else 1
        cagr = ((final / initial) ** (1 / years) - 1) * 100
        bench_cagr = ((bench_final / bench_initial) ** (1 / years) - 1) * 100
        ann_vol = backtest["daily_return"].std() * np.sqrt(252) * 100
        sharpe = (cagr / 100 - config.RISK_FREE_RATE) / (ann_vol / 100) if ann_vol > 0 else 0
        cum_max = backtest["portfolio_value"].cummax()
        drawdown_series = (backtest["portfolio_value"] - cum_max) / cum_max
        max_dd = drawdown_series.min() * 100
        # Win rate (daily)
        positive_days = (backtest["daily_return"] > 0).sum()
        total_days = len(backtest)
        win_rate = (positive_days / total_days * 100) if total_days > 0 else 0
        metrics = {
            "total_return": round(total_return, 1),
            "bench_return": round(bench_return, 1),
            "cagr": round(cagr, 1),
            "bench_cagr": round(bench_cagr, 1),
            "sharpe": round(sharpe, 2),
            "max_drawdown": round(max_dd, 1),
            "ann_vol": round(ann_vol, 1),
            "win_rate": round(win_rate, 1),
            "initial_capital": initial,
            "final_value": round(final, 2),
            "total_days": total_days,
        }
        # Drawdown series for chart (sampled)
        dd_sampled = drawdown_series.tolist()[::3]
        metrics["drawdown_sparkline"] = dd_sampled

    # Screening funnel
    from screener import get_screening_funnel
    funnel = get_screening_funnel(DB_PATH)

    # Reconciliation
    from reconciliation import run_reconciliation
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        recon = run_reconciliation()

    # Sector distribution
    sector_counts = fundamentals.groupby("sector").size().to_dict() if "sector" in fundamentals.columns else {}

    conn.close()

    return {
        "price_stats": price_stats,
        "fundamentals": fundamentals,
        "latest_signals": latest_signals,
        "latest_date": latest_date,
        "backtest": backtest,
        "metrics": metrics,
        "funnel": funnel,
        "recon": recon,
        "ticker_prices": ticker_prices,
        "sector_counts": sector_counts,
    }


def build_html(data):

    equity_img = img_to_base64(os.path.join(REPORTS_DIR, "equity_curve.png"))
    heatmap_img = img_to_base64(os.path.join(REPORTS_DIR, "signal_heatmap.png"))
    funnel_img = img_to_base64(os.path.join(REPORTS_DIR, "screening_funnel.png"))

    m = data["metrics"]
    bt = data["backtest"]

    # Build per-ticker mini cards with sparklines
    ticker_cards = ""
    for _, r in data["latest_signals"].iterrows():
        t = r["ticker"]
        spark = generate_sparkline_svg(
            data["ticker_prices"].get(t, []), 100, 28,
            "#10b981" if r.get("mom_60_pct", 0) and r["mom_60_pct"] >= 0 else "#ef4444",
            fill=True
        )
        mom = r.get("mom_60_pct", 0) or 0
        mom_cls = "pos" if mom >= 0 else "neg"
        cross = "BULL" if r.get("ma_crossover") == 1 else "BEAR"
        cross_cls = "badge-bull" if cross == "BULL" else "badge-bear"
        # Get fundamentals for this ticker
        fund_row = data["fundamentals"][data["fundamentals"]["ticker"] == t]
        pe = "N/A"
        mc = "N/A"
        if not fund_row.empty:
            pe_val = fund_row.iloc[0].get("pe_ratio")
            mc_val = fund_row.iloc[0].get("market_cap")
            if pd.notna(pe_val): pe = f"{pe_val:.1f}"
            if pd.notna(mc_val): mc = f"${mc_val/1e9:.0f}B"

        ticker_cards += f"""
        <div class="ticker-card">
          <div class="ticker-card-head">
            <div class="ticker-symbol">{t}</div>
            <span class="badge {cross_cls}">{cross}</span>
          </div>
          <div class="ticker-spark">{spark}</div>
          <div class="ticker-stats">
            <div class="ticker-stat">
              <span class="stat-label">Mom 60d</span>
              <span class="stat-value {mom_cls}">{mom:+.1f}%</span>
            </div>
            <div class="ticker-stat">
              <span class="stat-label">Vol 20d</span>
              <span class="stat-value">{r.get('vol_20_pct', 'N/A')}%</span>
            </div>
            <div class="ticker-stat">
              <span class="stat-label">P/E</span>
              <span class="stat-value">{pe}</span>
            </div>
            <div class="ticker-stat">
              <span class="stat-label">Mkt Cap</span>
              <span class="stat-value">{mc}</span>
            </div>
          </div>
        </div>"""

    # Signals table rows
    sig_rows = ""
    for _, r in data["latest_signals"].iterrows():
        mom60 = r.get("mom_60_pct", 0) or 0
        mom252 = r.get("mom_252_pct", 0) or 0
        daily = r.get("daily_ret_pct", 0) or 0
        vol = r.get("vol_20_pct", 0) or 0
        cross = '<span class="badge badge-bull">BULL</span>' if r.get("ma_crossover") == 1 else '<span class="badge badge-bear">BEAR</span>'
        # Inline bar for momentum
        bar_w = min(abs(mom60) * 2, 100)
        bar_color = "#10b981" if mom60 >= 0 else "#ef4444"
        bar_dir = "right" if mom60 >= 0 else "left"
        sig_rows += (
            f'<tr>'
            f'<td class="ticker">{r["ticker"]}</td>'
            f'<td class="{"pos" if daily >= 0 else "neg"}">{daily:+.2f}%</td>'
            f'<td class="{"pos" if r.get("mom_20_pct", 0) and r["mom_20_pct"] >= 0 else "neg"}">{r.get("mom_20_pct", "N/A")}%</td>'
            f'<td>'
            f'  <div class="bar-cell">'
            f'    <span class="{"pos" if mom60 >= 0 else "neg"}">{mom60:+.1f}%</span>'
            f'    <div class="mini-bar" style="width:{bar_w}%; background:{bar_color};"></div>'
            f'  </div>'
            f'</td>'
            f'<td class="{"pos" if mom252 >= 0 else "neg"}">{mom252:+.1f}%</td>'
            f'<td>{vol:.1f}%</td>'
            f'<td>{cross}</td>'
            f'</tr>\n'
        )

    # Fundamentals table rows
    fund_rows = ""
    for _, r in data["fundamentals"].iterrows():
        pe = f'{r["pe_ratio"]:.1f}' if pd.notna(r["pe_ratio"]) else "N/A"
        mc_val = r["market_cap"]
        mc = f'${mc_val/1e9:.1f}B' if pd.notna(mc_val) else "N/A"
        beta = f'{r["beta"]:.2f}' if pd.notna(r["beta"]) else "N/A"
        sector = r["sector"] if pd.notna(r["sector"]) else "N/A"
        # Pass/Fail badges for screening
        pe_ok = pd.notna(r["pe_ratio"]) and 0 < r["pe_ratio"] <= 25
        mc_ok = pd.notna(mc_val) and mc_val >= 1e10
        beta_ok = pd.notna(r["beta"]) and 0.5 <= r["beta"] <= 1.5
        fund_rows += (
            f'<tr>'
            f'<td class="ticker">{r["ticker"]}</td>'
            f'<td class="{"pos" if pe_ok else "neg"}">{pe}</td>'
            f'<td class="{"pos" if mc_ok else "neg"}">{mc}</td>'
            f'<td class="{"pos" if beta_ok else "neg"}">{beta}</td>'
            f'<td>{sector}</td>'
            f'</tr>\n'
        )

    # Recon rows
    recon_rows = ""
    for r in data["recon"]:
        cls = "pass" if r["passed"] else "fail"
        recon_rows += (
            f'<tr>'
            f'<td><span class="recon-icon recon-icon-{cls}">{"PASS" if r["passed"] else "FAIL"}</span></td>'
            f'<td class="recon-name">{r["name"]}</td>'
            f'<td class="recon-detail">{r["details"]}</td>'
            f'</tr>\n'
        )
    recon_passed = sum(1 for r in data["recon"] if r["passed"])
    recon_total = len(data["recon"])

    # Drawdown sparkline
    dd_spark = generate_sparkline_svg(
        m.get("drawdown_sparkline", []), 200, 36, "#ef4444", fill=True
    )

    # Sector breakdown
    sector_items = ""
    total_s = sum(data["sector_counts"].values()) if data["sector_counts"] else 1
    sector_colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4", "#84cc16"]
    for i, (sector, count) in enumerate(sorted(data["sector_counts"].items(), key=lambda x: -x[1])):
        pct = count / total_s * 100
        color = sector_colors[i % len(sector_colors)]
        sector_items += f"""
        <div class="sector-row">
          <div class="sector-label">{sector}</div>
          <div class="sector-bar-bg">
            <div class="sector-bar" style="width:{pct}%; background:{color};"></div>
          </div>
          <div class="sector-pct">{count} ({pct:.0f}%)</div>
        </div>"""

    # Funnel bars
    funnel_bars = ""
    funnel_colors = ["#10b981", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7"]
    max_count = data["funnel"][0]["count"] if data["funnel"] else 1
    for i, f in enumerate(data["funnel"]):
        pct = f["count"] / max_count * 100 if max_count else 0
        color = funnel_colors[i % len(funnel_colors)]
        funnel_bars += f"""
        <div class="funnel-row">
          <div class="funnel-label">{f['stage']}</div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar" style="width:{max(8, pct)}%; background: linear-gradient(90deg, {color}, {color}dd);">
              <span>{f['count']}</span>
            </div>
          </div>
        </div>"""

    # Price coverage rows
    price_rows = ""
    for _, r in data["price_stats"].iterrows():
        t = r["ticker"]
        spark = generate_sparkline_svg(data["ticker_prices"].get(t, []), 80, 20, "#58a6ff")
        price_rows += (
            f'<tr>'
            f'<td class="ticker">{t}</td>'
            f'<td>{r["rows"]:,}</td>'
            f'<td>{r["first_date"][:10]}</td>'
            f'<td>{r["last_date"][:10]}</td>'
            f'<td>${r["min_close"]:,.2f}</td>'
            f'<td>${r["max_close"]:,.2f}</td>'
            f'<td>{spark}</td>'
            f'</tr>\n'
        )

    nav_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Marko - The Market data pipeline</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{
  --bg:#06080f;--bg2:#0c1120;--card:#111827;--card-hover:#151f33;
  --border:#1e293b;--border-light:#2d3a52;
  --text:#e2e8f0;--text2:#94a3b8;--muted:#64748b;
  --accent:#3b82f6;--accent2:#6366f1;--accent-glow:rgba(59,130,246,0.12);
  --green:#10b981;--green-glow:rgba(16,185,129,0.12);
  --red:#ef4444;--red-glow:rgba(239,68,68,0.12);
  --yellow:#f59e0b;--purple:#8b5cf6;--cyan:#06b6d4;
}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);line-height:1.6;}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
@keyframes slideIn{{from{{opacity:0;transform:translateX(-10px)}}to{{opacity:1;transform:translateX(0)}}}}

.header{{
  background:linear-gradient(135deg,#080c18 0%,#111638 40%,#1a0f30 70%,#080c18 100%);
  border-bottom:1px solid var(--border);
  padding:40px 48px;position:relative;overflow:hidden;
}}
.header::before{{
  content:'';position:absolute;top:-40%;left:10%;width:80%;height:180%;
  background:radial-gradient(ellipse at 25% 50%,rgba(59,130,246,0.06) 0%,transparent 50%),
             radial-gradient(ellipse at 75% 50%,rgba(139,92,246,0.05) 0%,transparent 50%),
             radial-gradient(ellipse at 50% 0%,rgba(6,182,212,0.04) 0%,transparent 40%);
  pointer-events:none;
}}
.header::after{{
  content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),var(--purple),transparent);
}}
.header h1{{
  font-size:32px;font-weight:900;letter-spacing:-0.5px;
  background:linear-gradient(135deg,#60a5fa,#a78bfa,#c084fc);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  position:relative;
}}
.header p{{color:var(--text2);font-size:14px;margin-top:8px;position:relative;}}
.header-meta{{display:flex;gap:12px;margin-top:14px;flex-wrap:wrap;position:relative;}}
.header-meta span{{
  font-size:11px;color:var(--muted);padding:5px 14px;border-radius:20px;
  border:1px solid var(--border);background:rgba(255,255,255,0.03);
  backdrop-filter:blur(4px);
}}
.live-dot{{width:6px;height:6px;border-radius:50%;background:var(--green);display:inline-block;margin-right:6px;animation:pulse 2s infinite;}}

.container{{max-width:1440px;margin:0 auto;padding:28px 36px;}}
.section-title{{
  font-size:18px;font-weight:700;margin:36px 0 18px;padding-left:14px;
  border-left:3px solid var(--accent);color:var(--text);
  animation:fadeUp 0.4s ease;
}}

/* Grids */
.g4{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:24px;}}
.g6{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:24px;}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:24px;}}
@media(max-width:900px){{.g2,.g3{{grid-template-columns:1fr;}}.g6{{grid-template-columns:repeat(2,1fr);}}}}

/* Cards */
.card{{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:22px 26px;transition:all 0.25s ease;animation:fadeUp 0.5s ease;
}}
.card:hover{{border-color:rgba(59,130,246,0.35);box-shadow:0 0 30px var(--accent-glow);transform:translateY(-2px);}}
.card-full{{grid-column:1/-1;}}
.card h2{{
  font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;
  color:var(--muted);margin-bottom:16px;display:flex;align-items:center;gap:8px;
}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block;}}
.dot-b{{background:var(--accent);}}.dot-g{{background:var(--green);}}.dot-r{{background:var(--red);}}
.dot-p{{background:var(--purple);}}.dot-y{{background:var(--yellow);}}.dot-c{{background:var(--cyan);}}

/* Metric cards */
.metric-card{{text-align:center;padding:24px 16px;position:relative;overflow:hidden;}}
.metric-card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0;
}}
.mc-green::before{{background:linear-gradient(90deg,var(--green),#34d399);}}
.mc-blue::before{{background:linear-gradient(90deg,var(--accent),#60a5fa);}}
.mc-purple::before{{background:linear-gradient(90deg,var(--purple),#a78bfa);}}
.mc-red::before{{background:linear-gradient(90deg,var(--red),#f87171);}}
.mc-yellow::before{{background:linear-gradient(90deg,var(--yellow),#fbbf24);}}
.mc-cyan::before{{background:linear-gradient(90deg,var(--cyan),#22d3ee);}}
.metric-value{{font-size:36px;font-weight:900;letter-spacing:-1.5px;margin-bottom:2px;}}
.metric-label{{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);font-weight:600;}}
.metric-sub{{font-size:12px;color:var(--text2);margin-top:8px;}}
.metric-delta{{font-size:11px;font-weight:600;margin-top:4px;padding:2px 8px;border-radius:12px;display:inline-block;}}
.delta-up{{background:var(--green-glow);color:var(--green);}}
.delta-down{{background:var(--red-glow);color:var(--red);}}
.v-green{{color:var(--green);}}.v-red{{color:var(--red);}}.v-blue{{color:var(--accent);}}
.v-purple{{color:var(--purple);}}.v-yellow{{color:var(--yellow);}}.v-cyan{{color:var(--cyan);}}

/* Tables */
table{{width:100%;border-collapse:collapse;font-size:13px;}}
th{{
  text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.8px;color:var(--muted);padding:10px 14px;
  border-bottom:1px solid var(--border);background:rgba(255,255,255,0.015);
  position:sticky;top:0;
}}
td{{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.03);color:var(--text2);transition:background 0.15s;}}
tr:hover td{{background:rgba(255,255,255,0.02);}}
.ticker{{font-weight:700;color:var(--text);font-family:'Inter',monospace;letter-spacing:0.5px;}}
.pos{{color:var(--green);font-weight:600;}}.neg{{color:var(--red);font-weight:600;}}
.badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:9px;font-weight:700;letter-spacing:0.8px;}}
.badge-bull{{background:var(--green-glow);color:var(--green);border:1px solid rgba(16,185,129,0.3);}}
.badge-bear{{background:var(--red-glow);color:var(--red);border:1px solid rgba(239,68,68,0.3);}}
.table-scroll{{overflow-x:auto;max-height:450px;overflow-y:auto;border-radius:8px;}}
.table-scroll::-webkit-scrollbar{{width:5px;height:5px;}}
.table-scroll::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px;}}

/* Bar cells */
.bar-cell{{display:flex;align-items:center;gap:8px;}}
.mini-bar{{height:4px;border-radius:2px;min-width:2px;opacity:0.7;}}

/* Ticker cards grid */
.ticker-card{{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:16px;transition:all 0.2s ease;animation:slideIn 0.4s ease;
}}
.ticker-card:hover{{border-color:rgba(59,130,246,0.3);box-shadow:0 0 20px var(--accent-glow);transform:translateY(-2px);}}
.ticker-card-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}}
.ticker-symbol{{font-size:16px;font-weight:800;letter-spacing:0.5px;}}
.ticker-spark{{margin:6px 0;}}
.ticker-stats{{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;}}
.ticker-stat{{display:flex;justify-content:space-between;}}
.stat-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;}}
.stat-value{{font-size:11px;font-weight:600;}}

/* Chart image */
.chart-img{{width:100%;border-radius:10px;margin-top:8px;}}

/* Recon */
.recon-icon{{
  display:inline-block;padding:3px 12px;border-radius:6px;
  font-size:10px;font-weight:700;letter-spacing:0.8px;
}}
.recon-icon-pass{{background:var(--green-glow);color:var(--green);border:1px solid rgba(16,185,129,0.2);}}
.recon-icon-fail{{background:var(--red-glow);color:var(--red);border:1px solid rgba(239,68,68,0.2);}}
.recon-name{{font-weight:600;color:var(--text);}}
.recon-detail{{font-size:11px;color:var(--muted);max-width:550px;word-break:break-word;}}

/* Funnel */
.funnel-row{{display:flex;align-items:center;margin-bottom:10px;gap:14px;animation:slideIn 0.5s ease;}}
.funnel-label{{min-width:130px;font-size:13px;color:var(--text2);text-align:right;font-weight:500;}}
.funnel-bar-bg{{flex:1;height:32px;background:rgba(255,255,255,0.03);border-radius:8px;overflow:hidden;}}
.funnel-bar{{
  height:100%;border-radius:8px;display:flex;align-items:center;
  justify-content:flex-end;padding-right:12px;
  font-size:13px;font-weight:700;color:white;
  transition:width 0.8s ease;
}}

/* Sector */
.sector-row{{display:flex;align-items:center;gap:12px;margin-bottom:8px;}}
.sector-label{{min-width:120px;font-size:12px;color:var(--text2);text-align:right;}}
.sector-bar-bg{{flex:1;height:22px;background:rgba(255,255,255,0.03);border-radius:6px;overflow:hidden;}}
.sector-bar{{height:100%;border-radius:6px;transition:width 0.6s ease;}}
.sector-pct{{font-size:11px;color:var(--muted);min-width:60px;}}

/* Footer */
.footer{{
  text-align:center;padding:40px 0 24px;color:var(--muted);font-size:11px;
  border-top:1px solid var(--border);margin-top:32px;
}}
.footer a{{color:var(--accent);text-decoration:none;}}
</style>
</head>
<body>

<div class="header">
  <h1>Marko - The Market data pipeline</h1>
  <p>Pipeline Results</p>
  <div class="header-meta">
    <span><span class="live-dot"></span>Pipeline Healthy</span>
    <span>Python + SQL</span>
    <span>{len(config.TICKERS)} Tickers + SPY</span>
    <span>{config.START_DATE} to {config.END_DATE}</span>
    <span>{nav_time}</span>
  </div>
</div>

<div class="container">

  <!-- ═══════ KEY METRICS ═══════ -->
  <div class="section-title">Performance Overview</div>
  <div class="g6">
    <div class="card metric-card mc-green">
      <div class="metric-value v-green">{m.get('total_return', 0)}%</div>
      <div class="metric-label">Total Return</div>
      <div class="metric-delta delta-up">+{m.get('total_return', 0) - m.get('bench_return', 0):.0f}% vs SPY</div>
    </div>
    <div class="card metric-card mc-blue">
      <div class="metric-value v-blue">{m.get('cagr', 0)}%</div>
      <div class="metric-label">CAGR</div>
      <div class="metric-sub">SPY: {m.get('bench_cagr', 0)}%</div>
    </div>
    <div class="card metric-card mc-purple">
      <div class="metric-value v-purple">{m.get('sharpe', 0)}</div>
      <div class="metric-label">Sharpe Ratio</div>
      <div class="metric-sub">Risk-adjusted return</div>
    </div>
    <div class="card metric-card mc-red">
      <div class="metric-value v-red">{m.get('max_drawdown', 0)}%</div>
      <div class="metric-label">Max Drawdown</div>
      <div class="metric-sub">{dd_spark}</div>
    </div>
    <div class="card metric-card mc-yellow">
      <div class="metric-value v-yellow">{m.get('ann_vol', 0)}%</div>
      <div class="metric-label">Ann. Volatility</div>
      <div class="metric-sub">Annualized risk</div>
    </div>
    <div class="card metric-card mc-cyan">
      <div class="metric-value v-cyan">{m.get('win_rate', 0)}%</div>
      <div class="metric-label">Win Rate</div>
      <div class="metric-sub">{m.get('total_days', 0)} trading days</div>
    </div>
  </div>

  <!-- ═══════ EQUITY CURVE ═══════ -->
  <div class="section-title">Equity Curve</div>
  <div class="card card-full">
    <h2><span class="dot dot-b"></span> Portfolio vs. SPY Benchmark &mdash; ${m.get('initial_capital', 100000):,.0f} Initial Capital</h2>
    {"<img class='chart-img' src='" + equity_img + "' alt='Equity Curve'>" if equity_img else "<p>No chart available</p>"}
    <div style="display:flex;gap:32px;margin-top:14px;align-items:center;">
      <div><span style="color:var(--accent);font-weight:700;">Strategy</span> <span style="color:var(--text2);">&rarr; ${m.get('final_value', 0):,.0f}</span></div>
      <div><span style="color:var(--muted);font-weight:700;">SPY</span> <span style="color:var(--text2);">&rarr; {m.get('bench_return', 0)}% return</span></div>
    </div>
  </div>

  <!-- ═══════ TICKER CARDS ═══════ -->
  <div class="section-title">Individual Stock Signals ({data['latest_date'][:10] if data['latest_date'] else 'N/A'})</div>
  <div class="g6">
    {ticker_cards}
  </div>

  <!-- ═══════ SIGNALS TABLE ═══════ -->
  <div class="section-title">Signal Detail Table</div>
  <div class="card">
    <h2><span class="dot dot-b"></span> Momentum, Volatility &amp; Trend</h2>
    <div class="table-scroll">
      <table>
        <thead>
          <tr><th>Ticker</th><th>Daily</th><th>Mom 20d</th><th>Mom 60d</th><th>Mom 252d</th><th>Vol 20d</th><th>Trend</th></tr>
        </thead>
        <tbody>{sig_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- ═══════ HEATMAP + FUNNEL ═══════ -->
  <div class="section-title">Screening &amp; Signal Analysis</div>
  <div class="g2">
    <div class="card">
      <h2><span class="dot dot-p"></span> Signal Heatmap</h2>
      {"<img class='chart-img' src='" + heatmap_img + "' alt='Heatmap'>" if heatmap_img else "<p>No chart</p>"}
    </div>
    <div class="card">
      <h2><span class="dot dot-y"></span> Screening Funnel</h2>
      {funnel_bars}
      {"<img class='chart-img' style='margin-top:16px;' src='" + funnel_img + "' alt='Funnel'>" if funnel_img else ""}
    </div>
  </div>

  <!-- ═══════ FUNDAMENTALS + SECTORS ═══════ -->
  <div class="section-title">Fundamentals &amp; Sector Breakdown</div>
  <div class="g2">
    <div class="card">
      <h2><span class="dot dot-g"></span> Financial Ratios (Green = Passes Screen)</h2>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Ticker</th><th>P/E</th><th>Mkt Cap</th><th>Beta</th><th>Sector</th></tr></thead>
          <tbody>{fund_rows}</tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <h2><span class="dot dot-c"></span> Sector Distribution</h2>
      {sector_items if sector_items else "<p style='color:var(--muted);'>No sector data available</p>"}
    </div>
  </div>

  <!-- ═══════ DATA COVERAGE ═══════ -->
  <div class="section-title">Data Coverage</div>
  <div class="card">
    <h2><span class="dot dot-y"></span> Price History &amp; Range per Ticker</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th>Ticker</th><th>Rows</th><th>From</th><th>To</th><th>Low</th><th>High</th><th>Trend</th></tr></thead>
        <tbody>{price_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- ═══════ RECONCILIATION ═══════ -->
  <div class="section-title">Data Quality &mdash; {recon_passed}/{recon_total} Checks Passed</div>
  <div class="card">
    <h2><span class="dot {"dot-g" if recon_passed == recon_total else "dot-r"}"></span> Automated SQL Reconciliation</h2>
    <table>
      <thead><tr><th style="width:80px;">Status</th><th>Check Name</th><th>Details</th></tr></thead>
      <tbody>{recon_rows}</tbody>
    </table>
  </div>

  <div class="footer">
    <strong>Marko - The Market data pipeline</strong> &nbsp;|&nbsp; Python + SQL &nbsp;|&nbsp; {nav_time}
    
  </div>

</div>
</body>
</html>"""

    return html


def main():
    print("[Dashboard] Loading data from SQLite...")
    data = load_data()

    print("[Dashboard] Building HTML dashboard...")
    html = build_html(data)

    output_path = os.path.join(config.BASE_DIR, "dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Dashboard] Saved to {output_path}")
    print("[Dashboard] Opening in browser...")

    import webbrowser
    webbrowser.open(f"file:///{output_path.replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
