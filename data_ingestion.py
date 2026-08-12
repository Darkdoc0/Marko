
import sqlite3
import time
from datetime import datetime
import pandas as pd
import yfinance as yf


from config import (
    TICKERS, 
    BENCHMARK, 
    START_DATE, 
    END_DATE, 
    DB_PATH, 
    YFINANCE_PAUSE_SECONDS, 
    MAX_RETRIES
)

def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT PRIMARY KEY,
            pe_ratio REAL,
            market_cap REAL,
            beta REAL,
            sector TEXT,
            fetch_date TEXT
        )
    ''')

    conn.commit()
    conn.close()

def _fetch_ticker_data_with_retry(ticker: str, start: str, end: str) -> pd.DataFrame:
    for attempt in range(MAX_RETRIES):
        try:

            df = yf.download(ticker, start=start, end=end, progress=False)
            if not df.empty:

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
            return df
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Failed to fetch {ticker}: {e}. Max retries reached.")
                return pd.DataFrame()
            
            sleep_time = (2 ** attempt)
            print(f"Failed to fetch {ticker}: {e}. Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)
            
    return pd.DataFrame()

def fetch_price_data(tickers: list, start_date: str, end_date: str, db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    total_rows_inserted = 0
    

    all_tickers = list(set(tickers + [BENCHMARK]))

    for ticker in all_tickers:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM price_history WHERE ticker = ?", (ticker,))
        result = cursor.fetchone()
        latest_date_in_db = result[0] if result[0] else None

        fetch_start = start_date
        if latest_date_in_db:
            fetch_start = latest_date_in_db
            if ' ' in fetch_start:
                fetch_start = fetch_start.split(' ')[0]
        
        if fetch_start >= end_date:
            print(f"Skipping {ticker}, already up to date ({latest_date_in_db}).")
            continue

        df = _fetch_ticker_data_with_retry(ticker, fetch_start, end_date)
        
        if df.empty:
            print(f"No data for {ticker} from {fetch_start} to {end_date}.")
            continue
            
        df = df.reset_index()
        col_map = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        }
        df.rename(columns=col_map, inplace=True)
        df['ticker'] = ticker
        


        if 'adj_close' not in df.columns or df['adj_close'].isna().all():
            df['adj_close'] = df['close']
        
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)
            
        cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        for col in cols:
            if col not in df.columns:
                df[col] = None
                
        insert_data = df[cols].values.tolist()
        
        cursor.executemany('''
            INSERT OR IGNORE INTO price_history 
            (ticker, date, open, high, low, close, adj_close, volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        
        conn.commit()
        rows_added = cursor.rowcount
        total_rows_inserted += rows_added
        
        print(f"Fetching {ticker}... {len(insert_data)} rows downloaded, {rows_added} new rows inserted.")
        
        time.sleep(YFINANCE_PAUSE_SECONDS)
        
    conn.close()
    return total_rows_inserted

def fetch_fundamentals(tickers: list, db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    updated_count = 0
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            pe_ratio = info.get('trailingPE')
            market_cap = info.get('marketCap')
            beta = info.get('beta')
            sector = info.get('sector')
            
            cursor.execute('''
                INSERT OR REPLACE INTO fundamentals 
                (ticker, pe_ratio, market_cap, beta, sector, fetch_date) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ticker, pe_ratio, market_cap, beta, sector, current_date))
            
            updated_count += 1
            print(f"Fundamentals: {ticker}.")
            
        except Exception as e:
            print(f"Failed to fetch fundamentals for {ticker}: {e}")
            
        time.sleep(YFINANCE_PAUSE_SECONDS)
        
    conn.commit()
    conn.close()
    return updated_count

def run_ingestion() -> dict:
    print("Running ingestion...")
    init_db(DB_PATH)
    
    total_price_rows = fetch_price_data(TICKERS, str(START_DATE), str(END_DATE), DB_PATH)
    total_fundamentals = fetch_fundamentals(TICKERS, DB_PATH)
    
    print("-" * 40)
    print("Ingestion Summary")
    print(f"Total Tickers Configured: {len(TICKERS)}")
    print(f"Total New Price Rows Inserted: {total_price_rows}")
    print(f"Total Fundamentals Updated: {total_fundamentals}")
    print("-" * 40)
    
    return {
        "tickers_processed": len(TICKERS) + 1,  # +1 for benchmark
        "total_price_rows": total_price_rows,
        "fundamentals_updated": total_fundamentals
    }

if __name__ == '__main__':
    run_ingestion()
