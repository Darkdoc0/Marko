
import sqlite3
import pandas as pd
import config

def check_no_missing_dates(conn) -> dict:
    query = """
    SELECT ticker, date
    FROM price_history
    ORDER BY ticker, date
    """
    try:
        df = pd.read_sql_query(query, conn)
        df['date'] = pd.to_datetime(df['date'])
        df['prev_date'] = df.groupby('ticker')['date'].shift(1)
        df['gap'] = (df['date'] - df['prev_date']).dt.days
        
        gaps = df[df['gap'] > 5]
        passed = len(gaps) == 0
        details = f"Found {len(gaps)} gaps > 5 days" if not passed else "No gaps > 5 days"
        return {'name': 'No Missing Dates', 'passed': passed, 'details': details}
    except Exception as e:
        return {'name': 'No Missing Dates', 'passed': False, 'details': str(e)}

def check_price_sanity(conn) -> dict:
    query = """
    SELECT COUNT(*) as bad_rows
    FROM price_history
    WHERE close <= 0 OR high < low OR open <= 0
    """
    try:
        df = pd.read_sql_query(query, conn)
        bad_rows = int(df['bad_rows'].iloc[0])
        passed = bad_rows == 0
        details = f"{bad_rows} invalid price rows" if not passed else "All prices sane"
        return {'name': 'Price Sanity', 'passed': passed, 'details': details}
    except Exception as e:
        return {'name': 'Price Sanity', 'passed': False, 'details': str(e)}

def check_return_consistency(conn) -> dict:
    query = """
    SELECT p.ticker, p.date, p.adj_close, s.daily_return as signal_return
    FROM price_history p
    JOIN signals s ON p.ticker = s.ticker AND p.date = s.date
    WHERE p.ticker IN (SELECT DISTINCT ticker FROM price_history LIMIT 5)
    ORDER BY p.ticker, p.date
    """
    try:
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return {'name': 'Return Consistency', 'passed': False, 'details': 'No data'}
            
        df['calc_return'] = df.groupby('ticker')['adj_close'].pct_change()
        diff = (df['calc_return'] - df['signal_return']).abs()
        max_diff = diff.max()
        
        passed = pd.isna(max_diff) or max_diff < 1e-6
        details = f"max diff: {max_diff:.6f}" if pd.notna(max_diff) else "No data for comparison"
        return {'name': 'Return Consistency', 'passed': bool(passed), 'details': details}
    except Exception as e:
        return {'name': 'Return Consistency', 'passed': False, 'details': str(e)}

def check_volume_check(conn) -> dict:
    query = """
    SELECT COUNT(*) as total_rows, 
           SUM(CASE WHEN volume = 0 THEN 1 ELSE 0 END) as zero_volume_rows 
    FROM price_history
    """
    try:
        df = pd.read_sql_query(query, conn)
        total_rows = int(df['total_rows'].iloc[0])
        zero_vol_rows = int(df['zero_volume_rows'].iloc[0]) if pd.notna(df['zero_volume_rows'].iloc[0]) else 0
        
        pct = zero_vol_rows / total_rows if total_rows > 0 else 0.0
        passed = pct < 0.01
        details = f"{zero_vol_rows} rows ({pct:.2%})"
        return {'name': 'Volume Check', 'passed': passed, 'details': details}
    except Exception as e:
        return {'name': 'Volume Check', 'passed': False, 'details': str(e)}

def check_fundamental_completeness(conn) -> dict:
    tickers = getattr(config, 'TICKERS', [])
    if not tickers:
        return {'name': 'Fundamental Completeness', 'passed': False, 'details': 'config.TICKERS is empty'}
        
    query = f"""
    SELECT ticker, pe_ratio, market_cap, beta
    FROM fundamentals
    WHERE ticker IN ({','.join(['?']*len(tickers))})
    """
    try:
        df = pd.read_sql_query(query, conn, params=tickers)
        
        missing = set(tickers) - set(df['ticker'])
        df['all_null'] = df[['pe_ratio', 'market_cap', 'beta']].isnull().all(axis=1)
        all_null_tickers = set(df[df['all_null']]['ticker'])
        
        passed = len(missing) == 0 and len(all_null_tickers) == 0
        
        details_list = []
        if missing:
            details_list.append(f"Missing: {missing}")
        if all_null_tickers:
            details_list.append(f"All NULLs: {all_null_tickers}")
            
        details = "; ".join(details_list) if details_list else "All tickers present & populated"
        return {'name': 'Fundamental Completeness', 'passed': passed, 'details': details}
    except Exception as e:
        return {'name': 'Fundamental Completeness', 'passed': False, 'details': str(e)}

def check_signal_nan_audit(conn) -> dict:
    warmup_period = max(config.ROLLING_WINDOWS.values()) if hasattr(config, 'ROLLING_WINDOWS') else 252
    
    query = "SELECT * FROM signals ORDER BY ticker, date"
    try:
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return {'name': 'Signal NaN Audit', 'passed': False, 'details': 'signals is empty'}
            
        signal_cols = [c for c in df.columns if c not in ('ticker', 'date')]
        null_counts = df[signal_cols].isnull().sum().to_dict()
        
        df['row_num'] = df.groupby('ticker').cumcount() + 1
        outside_warmup = df[df['row_num'] > warmup_period]
        nulls_outside = outside_warmup[signal_cols].isnull().sum().sum()
        
        passed = nulls_outside == 0
        details = f"NULLs outside warmup: {nulls_outside} | Total NULLs: {null_counts}"
        return {'name': 'Signal NaN Audit', 'passed': bool(passed), 'details': details}
    except Exception as e:
        return {'name': 'Signal NaN Audit', 'passed': False, 'details': str(e)}

def check_backtest_integrity(conn) -> dict:
    query = "SELECT date, portfolio_value FROM backtest_results ORDER BY date"
    try:
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return {'name': 'Backtest Integrity', 'passed': False, 'details': 'backtest_results is empty'}
            
        neg_val = (df['portfolio_value'] <= 0).sum()
        
        df['date'] = pd.to_datetime(df['date'])
        dates_monotonic = df['date'].is_monotonic_increasing
        
        passed = (neg_val == 0) and dates_monotonic
        
        details_list = []
        if neg_val > 0:
            details_list.append(f"{neg_val} rows <= 0 portfolio value")
        if not dates_monotonic:
            details_list.append("Dates not monotonic")
            
        details = "; ".join(details_list) if details_list else "Healthy"
        return {'name': 'Backtest Integrity', 'passed': bool(passed), 'details': details}
    except Exception as e:
        return {'name': 'Backtest Integrity', 'passed': False, 'details': str(e)}

def run_reconciliation(db_path=None) -> list[dict]:
    db_path = db_path or config.DB_PATH
    
    checks = [
        check_no_missing_dates,
        check_price_sanity,
        check_return_consistency,
        check_volume_check,
        check_fundamental_completeness,
        check_signal_nan_audit,
        check_backtest_integrity
    ]
    
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"Failed to connect to database at {db_path}: {e}")
        return []

    results = []
    for check_func in checks:
        results.append(check_func(conn))
        
    conn.close()
    
    print("[Reconciliation] =============================================")
    print("[Reconciliation]  Data Integrity Report")
    print("[Reconciliation] ---------------------------------------------")
    
    passed_count = 0
    for r in results:
        status = "+ PASS" if r['passed'] else "x FAIL"
        print(f"[Reconciliation]  {status}  {r['name']} -- {r['details']}")
        if r['passed']:
            passed_count += 1
            
    print("[Reconciliation] ---------------------------------------------")
    print(f"[Reconciliation]  Result: {passed_count}/{len(checks)} checks passed")
    print("[Reconciliation] =============================================")
    
    return results

if __name__ == '__main__':
    run_reconciliation()
