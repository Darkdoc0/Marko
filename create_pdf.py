import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(letter[0]/2.0, 0.5 * inch, text)
    canvas.restoreState()

def create_study_guide(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    primary_color = colors.HexColor("#2563eb")
    text_color = colors.HexColor("#0f172a")
    secondary_color = colors.HexColor("#475569")
    code_bg = colors.HexColor("#f1f5f9")
    
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=12,
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=secondary_color,
        spaceAfter=24,
        alignment=1 # Center
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=primary_color,
        spaceBefore=16,
        spaceAfter=12,
        keepWithNext=True
    )
    
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=text_color,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        spaceAfter=8,
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        spaceAfter=6,
        leading=14,
        leftIndent=15,
        bulletIndent=5
    )
    
    code_style = ParagraphStyle(
        'CodeText',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=9,
        textColor=text_color,
        backColor=code_bg,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=6,
        leading=12
    )

    story = []

    def section_header(text):
        story.append(Paragraph(text, heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceBefore=0, spaceAfter=12))

    def create_table(data, col_widths=None):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        return table

    # --- TITLE PAGE / SECTION 1 ---
    story.append(Paragraph("Marko - The Market data pipeline", title_style))
    story.append(Paragraph("Python, SQL | Comprehensive Interview Study Guide | Feb 2026 - Mar 2026", subtitle_style))
    
    section_header("SECTION 1: PROJECT OVERVIEW & RESUME BULLETS")
    
    resume_bullets = [
        "Built a Python pipeline to fetch and process historical equity price data, automating what was previously manual spreadsheet work into a repeatable SQL/Python workflow, computing rolling returns, volatility, and momentum signals across multiple tickers.",
        "Automated rule-based screening logic to filter stocks by financial ratios (P/E, market cap, beta), simulating structured selection criteria comparable to standardized business-rule processes.",
        "Validated pipeline outputs using SQL reconciliation scripts, as measured by data integrity across time periods and rebalancing intervals, ensuring accuracy consistent with quality-assurance standards for recurring data operations."
    ]
    
    for bullet in resume_bullets:
        story.append(Paragraph(f"• {bullet}", bullet_style))
        
    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 2 ---
    section_header("SECTION 2: ARCHITECTURE & DATA FLOW")
    story.append(Paragraph("6-Stage Pipeline:", subheading_style))
    
    stages = [
        "1. <b>Data Ingestion:</b> yfinance API -> Exponential Backoff Retry -> SQLite (price_history, fundamentals tables)",
        "2. <b>Signal Engine:</b> SQL Read -> Pandas Vectorized -> SQLite (signals table) - 12 technical signals",
        "3. <b>Screener:</b> Fundamentals + Signals JOIN -> Sequential Funnel Filter (P/E, Market Cap, Beta, Momentum)",
        "4. <b>Backtester:</b> Quarterly Rebalance Calendar -> Equal-Weight Allocation -> Transaction Costs -> SQLite (backtest_results)",
        "5. <b>Reconciliation:</b> 7 SQL-First Integrity Checks -> Pass/Fail Report",
        "6. <b>Dashboard:</b> SQLite Data + Charts -> Self-Contained HTML Dashboard -> Auto Browser Launch"
    ]
    for stage in stages:
        story.append(Paragraph(stage, body_style))
        
    story.append(Spacer(1, 0.1*inch))
    
    stack_data = [
        ["Component", "Technology / Details"],
        ["Data Source", "yfinance (free historical OHLCV + fundamentals)"],
        ["Storage", "SQLite (serverless, portable, SQL-capable)"],
        ["Compute", "pandas/numpy (vectorized C-backend operations)"],
        ["Visualization", "matplotlib (dark-themed charts)"],
        ["Dashboard", "Self-contained HTML with embedded base64 charts"],
        ["Config", "config.py (single source of truth)"]
    ]
    story.append(create_table(stack_data, [1.5*inch, 4.5*inch]))
    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 3 ---
    section_header("SECTION 3: DATABASE SCHEMA")
    
    schema_data = [
        ["Table", "Columns & Primary Keys"],
        ["price_history", "ticker, date, open, high, low, close, adj_close, volume\nPK(ticker, date)"],
        ["fundamentals", "ticker PK, pe_ratio, market_cap, beta, sector, fetch_date"],
        ["signals", "ticker, date, daily_return, rolling_return_20/60/252,\nvolatility_20/60, momentum_20/60/252, sma_50, sma_200, ma_crossover\nPK(ticker, date)"],
        ["backtest_results", "date PK, portfolio_value, benchmark_value, daily_return"]
    ]
    story.append(create_table(schema_data, [1.5*inch, 4.5*inch]))
    story.append(PageBreak())

    # --- SECTION 4 ---
    section_header("SECTION 4: SIGNAL FORMULAS & FINANCE CONCEPTS")
    
    story.append(Paragraph("Technical Signals", subheading_style))
    signals = [
        ("Daily Return", "R_t = (P_t / P_{t-1}) - 1"),
        ("Rolling Return", "product(1 + R_i, window) - 1, for 20d/60d/252d"),
        ("Annualized Volatility", "std(daily_returns, window) * sqrt(252), for 20d/60d"),
        ("Momentum (ROC)", "(P_t / P_{t-N}) - 1, for 20d/60d/252d"),
        ("SMA", "mean(close, window), for 50d/200d"),
        ("MA Crossover", "1 if SMA50 > SMA200 else 0 (Golden Cross = bullish, Death Cross = bearish)")
    ]
    
    for name, formula in signals:
        story.append(Paragraph(f"<b>{name}:</b> {formula}", body_style))
        
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Fundamental Ratios", subheading_style))
    ratios = [
        ("P/E Ratio", "Price / Earnings per Share. Lower = cheaper."),
        ("Market Cap", "Share Price * Shares Outstanding. We require > $10B."),
        ("Beta", "Covariance(stock, market) / Variance(market). Beta=1 moves with market.")
    ]
    for name, desc in ratios:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", body_style))

    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Performance Metrics", subheading_style))
    metrics = [
        ("CAGR", "(ending/starting)^(1/years) - 1"),
        ("Sharpe Ratio", "(CAGR - risk_free_rate) / annualized_volatility. >1.0 good, >2.0 excellent"),
        ("Max Drawdown", "largest peak-to-trough decline. Computed as: (current - peak) / peak. Shows worst-case loss from highest point."),
        ("Win Rate", "Percentage of trading days with positive returns. Calculated as: (days with daily_return > 0) / total_days * 100. Our strategy: ~53%."),
        ("Annualized Volatility", "Standard deviation of daily returns * sqrt(252). Measures total portfolio risk over a year."),
        ("Basis Points", "1 bps = 0.01%. 10 bps = 0.10%. Used for transaction cost modeling.")
    ]
    for name, desc in metrics:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", body_style))
    
    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 5 ---
    section_header("SECTION 5: CONFIGURATION & PARAMETERS TABLE")
    config_data = [
        ["Parameter Group", "Values"],
        ["TICKERS", "15 large-cap US stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, JPM,\nV, MA, UNH, JNJ, PG, HD, XOM, BAC) + SPY benchmark"],
        ["DATE RANGE", "START_DATE: 2020-01-01, END_DATE: 2025-12-31\n(5+ years, covers COVID crash, recovery, rate hikes)"],
        ["ROLLING_WINDOWS", "short=20d, medium=60d, long=252d (trading days in a year)"],
        ["SMA_WINDOWS", "fast=50d, slow=200d"],
        ["SCREEN_RULES", "pe_max=25, pe_min=0, market_cap_min=$10B, beta_min=0.5,\nbeta_max=1.5, momentum_60d_min=0"],
        ["BACKTEST PARAMS", "REBALANCE_FREQ: 'Q' (quarterly), INITIAL_CAPITAL: $100,000\nTRANSACTION_COST_BPS: 10 bps, RISK_FREE_RATE: 0.04 (4%)"]
    ]
    story.append(create_table(config_data, [2.0*inch, 4.0*inch]))
    story.append(PageBreak())

    # --- SECTION 6 ---
    section_header("SECTION 6: BACKTEST RESULTS & PERFORMANCE")
    bt_data = [
        ["Metric", "Strategy", "SPY (Benchmark)"],
        ["Total Return", "477.0%", "~132%"],
        ["CAGR", "34.0%", "~14.9%"],
        ["Sharpe Ratio", "1.43", "~0.78"],
        ["Max Drawdown", "-27.8%", "~-24.5%"],
        ["Ann. Volatility", "~23.7%", "~20%"],
        ["Win Rate", "~53%", "~53%"],
        ["Rebalances", "24 quarterly", "N/A"],
        ["Avg Holdings", "2.7 tickers per quarter", "N/A"]
    ]
    story.append(create_table(bt_data, [2*inch, 2*inch, 2*inch]))
    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 6B: DASHBOARD VISUAL GUIDE ---
    section_header("SECTION 6B: DASHBOARD VISUAL GUIDE")
    story.append(Paragraph(
        "The HTML dashboard (dashboard.html) displays all pipeline results in an interactive web interface. "
        "Below is an explanation of every visual element, chart, and data table shown on the dashboard.",
        body_style
    ))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Performance Metric Cards (Top Row)", subheading_style))
    dash_metrics = [
        ["Card", "What It Shows", "How It Is Computed"],
        ["Total Return", "Overall % gain from start to end", "(final_value / initial_capital - 1) * 100. Delta badge shows outperformance vs SPY."],
        ["CAGR", "Compound Annual Growth Rate", "(final/initial)^(1/years) - 1. Smoothed annual equivalent return."],
        ["Sharpe Ratio", "Risk-adjusted return per unit of volatility", "(CAGR - risk_free_rate) / annualized_volatility. Higher = better."],
        ["Max Drawdown", "Worst peak-to-trough loss + drawdown sparkline", "Series: (value - cummax) / cummax. The embedded mini-chart shows drawdown over time."],
        ["Ann. Volatility", "Annualized portfolio risk", "std(daily_returns) * sqrt(252) * 100. Lower = less risky."],
        ["Win Rate", "% of positive trading days", "count(daily_return > 0) / total_days * 100."]
    ]
    story.append(create_table(dash_metrics, [1.2*inch, 1.6*inch, 3.2*inch]))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Charts & Graphs", subheading_style))
    dash_charts = [
        ("Equity Curve", "Line chart comparing portfolio value vs SPY benchmark over time. "
         "X-axis = dates (2020-2025), Y-axis = dollar value starting from $100,000. "
         "Shows how the strategy grew relative to passive SPY buy-and-hold. "
         "Generated by matplotlib in main.py using backtest_results table data."),
        ("Drawdown Sparkline", "Embedded mini SVG chart inside the Max Drawdown metric card. "
         "Shows the drawdown series over time as a red filled area. "
         "Deeper dips = larger temporary losses. Helps visualize drawdown recovery periods."),
        ("Signal Heatmap", "Color-coded matrix showing the latest values of all 12 signals "
         "for each ticker. Red = negative momentum/returns, Green = positive. "
         "Allows quick visual scan of which stocks are strong vs weak across all signal dimensions."),
        ("Screening Funnel", "Horizontal bar chart showing how many stocks pass each screening stage. "
         "Starts with full universe (15 tickers), then narrows through P/E filter, "
         "Market Cap filter, Beta filter, and Momentum filter. Each bar shows surviving count."),
        ("Per-Ticker Sparklines", "Small inline SVG line charts on each ticker card and in the Data Coverage table. "
         "Show the stock's price trend over the full date range. Green = positive 60d momentum, Red = negative. "
         "Filled area beneath the line adds visual weight.")
    ]
    for name, desc in dash_charts:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", body_style))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Data Tables", subheading_style))
    dash_tables = [
        ("Individual Stock Signal Cards", "Grid of mini-cards for each ticker showing: symbol, BULL/BEAR badge "
         "(from ma_crossover), price sparkline, 60d momentum, 20d volatility, P/E ratio, and market cap. "
         "Sorted by momentum descending."),
        ("Signal Detail Table", "Full table with columns: Ticker, Daily Return, Momentum 20d/60d/252d, "
         "Volatility 20d, and Trend (BULL/BEAR). The 60d Momentum column includes inline colored bars "
         "proportional to momentum magnitude. Green = positive, Red = negative."),
        ("Fundamentals Table", "Shows P/E, Market Cap, Beta, and Sector for each ticker. "
         "Values are color-coded: Green = passes the screening threshold, Red = fails. "
         "This lets you instantly see which stocks would survive screening."),
        ("Sector Distribution", "Horizontal bar breakdown showing how many tickers belong to each sector "
         "(Technology, Healthcare, Financial Services, etc.). Provides portfolio diversification context."),
        ("Data Coverage Table", "Per-ticker row showing: total data rows, first date, last date, "
         "minimum close price, maximum close price, and a price sparkline. "
         "Confirms data completeness and shows each stock's historical price range."),
        ("Reconciliation Report", "Table listing all 7 SQL data quality checks with PASS/FAIL badges, "
         "check names, and detail messages. Visual confirmation that the entire pipeline is healthy.")
    ]
    for name, desc in dash_tables:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", body_style))

    # --- SECTION 7 ---
    story.append(PageBreak())
    section_header("SECTION 7: SQL RECONCILIATION CHECKS (ALL 7)")
    checks = [
        ("1. No Missing Dates", "Gaps > 5 calendar days per ticker.", "LAG window function on dates.", "zero gaps."),
        ("2. Price Sanity", "close > 0, high >= low, open > 0.", "WHERE clause filter.", "zero violations."),
        ("3. Return Consistency", "Recompute daily_return from adj_close in price_history, compare to signals table.", "JOIN + ABS(diff).", "max diff < 1e-6."),
        ("4. Volume Check", "Count zero-volume rows.", "WHERE volume = 0.", "< 1% of total."),
        ("5. Fundamental Completeness", "Every ticker has pe_ratio, market_cap, beta populated.", "LEFT JOIN + IS NULL.", "all present."),
        ("6. Signal NaN Audit", "NULLs only in first 252 rows per ticker (warmup).", "COUNT NULLs with ROW_NUMBER window.", "zero NULLs outside warmup."),
        ("7. Backtest Integrity", "portfolio_value > 0, dates monotonically increasing.", "LAG comparison.", "all positive, all increasing.")
    ]
    
    for name, validates, sql, pass_crit in checks:
        story.append(Paragraph(f"<b>{name}</b>", subheading_style))
        story.append(Paragraph(f"<b>Validates:</b> {validates}", body_style))
        story.append(Paragraph(f"<b>SQL Approach:</b> {sql}", body_style))
        story.append(Paragraph(f"<b>Pass Criteria:</b> {pass_crit}", body_style))
    
    story.append(PageBreak())

    # --- SECTION 8 ---
    section_header("SECTION 8: KEY SQL QUERIES")
    
    queries = [
        ("1. Get latest prices for all tickers", '''SELECT ticker, date, close 
FROM price_history 
WHERE date = (SELECT MAX(date) FROM price_history) 
ORDER BY ticker;'''),
        ("2. Find top momentum stocks", '''SELECT ticker, momentum_60d 
FROM signals 
WHERE date = (SELECT MAX(date) FROM signals) 
ORDER BY momentum_60d DESC 
LIMIT 5;'''),
        ("3. Reconcile returns between tables", '''SELECT p.ticker, p.date, p.adj_close, s.daily_return,
       (p.adj_close / LAG(p.adj_close) OVER (PARTITION BY p.ticker ORDER BY p.date) - 1) as calc_ret
FROM price_history p
JOIN signals s ON p.ticker = s.ticker AND p.date = s.date;'''),
        ("4. Screen stocks with SQL only", '''SELECT f.ticker 
FROM fundamentals f
JOIN signals s ON f.ticker = s.ticker
WHERE s.date = '2025-12-31'
  AND f.pe_ratio BETWEEN 0 AND 25
  AND f.market_cap > 10000000000
  AND f.beta BETWEEN 0.5 AND 1.5
  AND s.momentum_60d > 0;'''),
        ("5. Check data completeness", '''SELECT ticker, COUNT(*) as days, MIN(date) as first_dt, MAX(date) as last_dt 
FROM price_history 
GROUP BY ticker;''')
    ]
    
    for q_name, q_sql in queries:
        story.append(KeepTogether([
            Paragraph(q_name, subheading_style),
            Paragraph(q_sql.replace('\n', '<br/>'), code_style)
        ]))

    story.append(PageBreak())

    # --- SECTION 9 ---
    section_header("SECTION 9: DESIGN DECISIONS & ENGINEERING PRINCIPLES")
    
    principles = [
        ("Idempotency", "INSERT OR IGNORE + MAX(date) delta fetching. Running twice = same result."),
        ("Vectorization", "pandas rolling ops use numpy C backend. 24K rows in 0.6s vs minutes with loops."),
        ("Separation of Concerns", "config.py holds all parameters. No magic numbers in code."),
        ("Modularity", "Each stage is independently runnable (python screener.py)."),
        ("Error Resilience", "Exponential backoff on API failures. try/except per stage in main.py."),
        ("Data Lineage", "Raw data (price_history) -> Computed (signals) -> Filtered (screener output) -> Simulated (backtest_results). Full traceability.")
    ]
    
    for name, desc in principles:
        story.append(Paragraph(f"<b>{name}:</b> {desc}", body_style))

    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 10 ---
    section_header("SECTION 10: INTERVIEW Q&A")
    
    qna = [
        ("Q1: Walk me through the architecture.", "A1: 6-stage modular pipeline. Ingestion fetches OHLCV from yfinance into SQLite with idempotent INSERT OR IGNORE. Signal engine computes 12 vectorized indicators. Screener applies 4-stage fundamental filter. Backtester simulates quarterly equal-weight rebalancing with 10bps costs. Reconciliation runs 7 SQL checks. Dashboard generates interactive HTML report."),
        ("Q2: Why SQLite over PostgreSQL?", "A2: Single-user analytical pipeline. No concurrent writes, no server overhead. File-based = portable + version-controllable. Full SQL for reconciliation. Production migration to Postgres trivial (same SQL)."),
        ("Q3: How do you ensure data quality?", "A3: 7 automated SQL reconciliation checks. Return consistency recomputes from raw data. Gap detection uses LAG window functions. NaN audit validates warmup boundaries. All 7/7 pass."),
        ("Q4: What's idempotency and how does your pipeline achieve it?", "A4: Running multiple times = same result. Ingestion checks MAX(date) per ticker, only fetches delta. INSERT OR IGNORE with composite PK (ticker, date) prevents duplicates."),
        ("Q5: Why vectorized operations?", "A5: pandas rolling() uses numpy C backend. 24K rows x 12 signals in 0.6s. Python for-loop would be 10-100x slower due to interpreter overhead."),
        ("Q6: What does a Sharpe of 1.43 mean?", "A6: 1.43 units of excess return per unit of risk. Above 1.0 = good, above 2.0 = excellent. Caveat: in-sample backtest, real-world Sharpe would be lower."),
        ("Q7: Explain the screening logic.", "A7: 4 sequential filters: P/E 0-25 (excludes unprofitable/overvalued), Market Cap >$10B (liquidity), Beta 0.5-1.5 (controlled volatility), Momentum >0 (uptrend only). Sequential approach = transparent funnel diagnostics."),
        ("Q8: What's a Golden Cross?", "A8: 50-day SMA crosses above 200-day SMA. Bullish signal. Death Cross = opposite (bearish). Captured as ma_crossover = 1 or 0."),
        ("Q9: How would you improve this pipeline?", "A9: (1) Out-of-sample testing to detect overfitting. (2) Add RSI, Bollinger Bands. (3) Risk parity instead of equal weight. (4) Slippage modeling. (5) Airflow for scheduling. (6) PostgreSQL for team access. (7) Python logging module."),
        ("Q10: How do you handle the adj_close issue?", "A10: Newer yfinance removed 'Adj Close' column (prices are already adjusted). Code detects this: if adj_close is None/NaN, falls back to close column. Documented design decision for API version compatibility.")
    ]
    
    for q, a in qna:
        story.append(KeepTogether([
            Paragraph(f"<b>{q}</b>", body_style),
            Paragraph(f"{a}", body_style),
            Spacer(1, 0.05*inch)
        ]))

    story.append(PageBreak())

    # --- SECTION 11 ---
    section_header("SECTION 11: VOCABULARY QUICK REFERENCE")
    
    vocab_data = [
        ["Term", "Definition/Context"],
        ["OHLCV", "Open, High, Low, Close, Volume"],
        ["ETL", "Extract, Transform, Load (Data pipeline process)"],
        ["Idempotent", "Running multiple times produces the same result"],
        ["Vectorization", "Performing operations on entire arrays (no loops)"],
        ["Rolling Window", "A moving time frame applied across a dataset"],
        ["Warmup Period", "Initial rows (e.g. 252 days) needed to compute long-term signals"],
        ["Rebalancing", "Adjusting portfolio weights back to target (e.g., quarterly)"],
        ["Basis Points", "1/100th of 1%. Used for transaction costs."],
        ["Turnover", "How frequently portfolio assets are bought/sold"],
        ["Drawdown", "Peak-to-trough decline in portfolio value"],
        ["CAGR", "Compound Annual Growth Rate"],
        ["Sharpe Ratio", "Risk-adjusted return metric"],
        ["P/E Ratio", "Price-to-Earnings fundamental ratio"],
        ["Beta", "Measure of volatility relative to the broader market"],
        ["Market Cap", "Total value of outstanding shares"],
        ["SMA", "Simple Moving Average"],
        ["Golden Cross", "50d SMA > 200d SMA (Bullish indicator)"],
        ["Death Cross", "50d SMA < 200d SMA (Bearish indicator)"],
        ["Momentum/ROC", "Rate of Change over N periods"],
        ["Reconciliation", "Data validation against a source of truth"],
        ["Composite PK", "Primary Key spanning multiple columns (e.g., ticker + date)"],
        ["Exp. Backoff", "Retrying failed requests with increasing delays"],
        ["Ann. Volatility", "Standard deviation of returns scaled to a year"],
        ["Risk-Free Rate", "Theoretical return with zero risk (e.g. T-bills)"]
    ]
    
    story.append(create_table(vocab_data, [1.5*inch, 4.5*inch]))
    story.append(Spacer(1, 0.2*inch))

    # --- SECTION 12 ---
    section_header("SECTION 12: PROJECT FILE STRUCTURE")
    
    files_data = [
        ["Filename", "Purpose", "Line Count"],
        ["config.py", "Central configuration & parameters", "~55"],
        ["data_ingestion.py", "yfinance ETL to SQLite", "~220"],
        ["signal_engine.py", "Vectorized signal computation", "~120"],
        ["screener.py", "Rule-based stock filtering", "~170"],
        ["backtester.py", "Strategy simulation engine", "~210"],
        ["reconciliation.py", "7 SQL integrity checks", "~240"],
        ["main.py", "Pipeline orchestrator + chart generation", "~410"],
        ["dashboard.py", "HTML dashboard generator", "~750"],
        ["create_pdf.py", "PDF study guide compiler", "~300"],
        ["requirements.txt", "yfinance, pandas, numpy, matplotlib", "~5"]
    ]
    
    story.append(create_table(files_data, [1.5*inch, 3.5*inch, 1*inch]))
    
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Study guide PDF generated successfully at {output_path}")

if __name__ == "__main__":
    out_path = r"C:\Users\feate\.gemini\antigravity\scratch\market-data-pipeline\Market_Data_Pipeline_Study_Guide.pdf"
    create_study_guide(out_path)
