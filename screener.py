import sqlite3
import pandas as pd
from config import DB_PATH, SCREEN_RULES, TICKERS

def screen_stocks(db_path, as_of_date=None, rules=None):
    if rules is None:
        rules = SCREEN_RULES
        
    conn = sqlite3.connect(db_path)
    

    query_fundamentals = "SELECT * FROM fundamentals"
    df_fund = pd.read_sql_query(query_fundamentals, conn)
    

    if as_of_date is None:
        latest_date_query = "SELECT MAX(date) FROM signals"
        latest_date_cursor = conn.cursor()
        latest_date_cursor.execute(latest_date_query)
        res = latest_date_cursor.fetchone()
        as_of_date = res[0] if res and res[0] else None
        
    if as_of_date:
        query_signals = "SELECT ticker, momentum_60 FROM signals WHERE date = ?"
        df_sig = pd.read_sql_query(query_signals, conn, params=(as_of_date,))
    else:
        df_sig = pd.DataFrame(columns=['ticker', 'momentum_60'])
    
    conn.close()
    

    if not df_fund.empty and not df_sig.empty:
        df = pd.merge(df_fund, df_sig, on='ticker', how='left')
    elif not df_fund.empty:
        df = df_fund.copy()
        df['momentum_60'] = float('nan')
    else:
        df = pd.DataFrame(columns=['ticker', 'pe_ratio', 'market_cap', 'beta', 'sector', 'fetch_date', 'momentum_60'])
        
    universe_count = len(df)
    print(f"Starting universe: {universe_count} tickers")
    
    if df.empty:
        print("Screening OK: 0 tickers passed all screens")
        return df
    

    pe_min = rules.get('pe_min', 0.0)
    pe_max = rules.get('pe_max', 25.0)
    df = df[(df['pe_ratio'] > pe_min) & (df['pe_ratio'] <= pe_max)]
    print(f"After P/E: {len(df)}")
    

    mc_min = rules.get('market_cap_min', 1e10)
    df = df[df['market_cap'] >= mc_min]
    print(f"After MktCap: {len(df)}")
    

    beta_min = rules.get('beta_min', 0.5)
    beta_max = rules.get('beta_max', 1.5)
    df = df[(df['beta'] >= beta_min) & (df['beta'] <= beta_max)]
    print(f"After Beta: {len(df)}")
    

    mom_min = rules.get('momentum_60d_min', 0.0)
    df = df[df['momentum_60'] >= mom_min]
    mom_count = len(df)
    print(f"After Mom: {mom_count}")
    print(f"Screening OK: {mom_count} tickers passed all screens")
    
    return df

def screen_at_dates(db_path, dates, rules=None):
    results = {}
    for d in dates:
        results[d] = screen_stocks(db_path, as_of_date=d, rules=rules)
    return results

def get_screening_funnel(db_path, as_of_date=None, rules=None):
    if rules is None:
        rules = SCREEN_RULES
        
    conn = sqlite3.connect(db_path)
    
    query_fundamentals = "SELECT * FROM fundamentals"
    df_fund = pd.read_sql_query(query_fundamentals, conn)
    
    if as_of_date is None:
        latest_date_query = "SELECT MAX(date) FROM signals"
        latest_date_cursor = conn.cursor()
        latest_date_cursor.execute(latest_date_query)
        res = latest_date_cursor.fetchone()
        as_of_date = res[0] if res and res[0] else None
        
    if as_of_date:
        query_signals = "SELECT ticker, momentum_60 FROM signals WHERE date = ?"
        df_sig = pd.read_sql_query(query_signals, conn, params=(as_of_date,))
    else:
        df_sig = pd.DataFrame(columns=['ticker', 'momentum_60'])
        
    conn.close()
    
    if not df_fund.empty and not df_sig.empty:
        df = pd.merge(df_fund, df_sig, on='ticker', how='left')
    elif not df_fund.empty:
        df = df_fund.copy()
        df['momentum_60'] = float('nan')
    else:
        df = pd.DataFrame(columns=['ticker', 'pe_ratio', 'market_cap', 'beta', 'sector', 'fetch_date', 'momentum_60'])
        
    funnel = [{'stage': 'Universe', 'count': len(df)}]
    
    if not df.empty:

        pe_min = rules.get('pe_min', 0.0)
        pe_max = rules.get('pe_max', 25.0)
        df = df[(df['pe_ratio'] > pe_min) & (df['pe_ratio'] <= pe_max)]
        funnel.append({'stage': 'P/E Filter', 'count': len(df)})
        

        mc_min = rules.get('market_cap_min', 1e10)
        df = df[df['market_cap'] >= mc_min]
        funnel.append({'stage': 'Market Cap Filter', 'count': len(df)})
        

        beta_min = rules.get('beta_min', 0.5)
        beta_max = rules.get('beta_max', 1.5)
        df = df[(df['beta'] >= beta_min) & (df['beta'] <= beta_max)]
        funnel.append({'stage': 'Beta Filter', 'count': len(df)})
        

        mom_min = rules.get('momentum_60d_min', 0.0)
        df = df[df['momentum_60'] >= mom_min]
        funnel.append({'stage': 'Momentum Filter', 'count': len(df)})
    else:
        funnel.extend([
            {'stage': 'P/E Filter', 'count': 0},
            {'stage': 'Market Cap Filter', 'count': 0},
            {'stage': 'Beta Filter', 'count': 0},
            {'stage': 'Momentum Filter', 'count': 0}
        ])
        
    return funnel

def run_screener():
    df = screen_stocks(DB_PATH)
    return df

if __name__ == '__main__':
    run_screener()
