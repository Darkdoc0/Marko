import sqlite3
import pandas as pd
import numpy as np
from config import DB_PATH, ROLLING_WINDOWS, SMA_WINDOWS

def create_signals_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            ticker TEXT,
            date TEXT,
            daily_return REAL,
            rolling_return_20 REAL,
            rolling_return_60 REAL,
            rolling_return_252 REAL,
            volatility_20 REAL,
            volatility_60 REAL,
            momentum_20 REAL,
            momentum_60 REAL,
            momentum_252 REAL,
            sma_50 REAL,
            sma_200 REAL,
            ma_crossover INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    conn.commit()

def compute_signals(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    create_signals_table(conn)
    

    tickers_query = "SELECT DISTINCT ticker FROM price_history"
    tickers = pd.read_sql_query(tickers_query, conn)['ticker'].tolist()
    
    total_processed = 0
    total_rows = 0
    total_nans = 0
    
    for ticker in tickers:

        df = pd.read_sql_query(
            "SELECT ticker, date, adj_close FROM price_history WHERE ticker = ? ORDER BY date",
            conn,
            params=(ticker,)
        )
        if df.empty:
            continue
            

        df['daily_return'] = df['adj_close'].pct_change()
        

        for _, window in ROLLING_WINDOWS.items():
            # Rolling product of (1 + daily_return) - 1
            df[f'rolling_return_{window}'] = (1 + df['daily_return']).rolling(window=window).apply(np.prod, raw=True) - 1
            

        for key in ('short', 'medium'):
            window = ROLLING_WINDOWS[key]
            df[f'volatility_{window}'] = df['daily_return'].rolling(window=window).std() * np.sqrt(252)
            

        for _, window in ROLLING_WINDOWS.items():
            df[f'momentum_{window}'] = (df['adj_close'] / df['adj_close'].shift(window)) - 1
            

        for _, window in SMA_WINDOWS.items():
            df[f'sma_{window}'] = df['adj_close'].rolling(window=window).mean()
            

        df['ma_crossover'] = np.where(df['sma_50'] > df['sma_200'], 1, 0)
        # Set to NaN if either SMA is NaN
        df.loc[df['sma_200'].isna() | df['sma_50'].isna(), 'ma_crossover'] = np.nan
        

        df = df.drop(columns=['adj_close'])
        

        total_nans += int(df.isna().sum().sum())
        total_rows += len(df)
        total_processed += 1
        

        cursor = conn.cursor()
        cursor.execute("DELETE FROM signals WHERE ticker = ?", (ticker,))
        

        df.to_sql('signals', conn, if_exists='append', index=False)
        
    conn.commit()
    conn.close()
    
    return {
        'tickers_processed': total_processed,
        'total_signal_rows': total_rows,
        'nan_counts': total_nans
    }

def run_signal_engine():
    print("Starting signal engine computation...")
    stats = compute_signals()
    print("Signal Engine Summary:")
    print(f"  Number of tickers processed: {stats['tickers_processed']}")
    print(f"  Total signal rows generated: {stats['total_signal_rows']}")
    print(f"  NaN counts (warmup period): {stats['nan_counts']}")
    return stats

if __name__ == '__main__':
    run_signal_engine()
