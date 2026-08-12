import sqlite3
import pandas as pd
import numpy as np
from config import (
    DB_PATH,
    INITIAL_CAPITAL,
    REBALANCE_FREQ,
    TRANSACTION_COST_BPS,
    RISK_FREE_RATE,
    BENCHMARK
)

def get_rebalance_dates(db_path, freq='Q'):
    with sqlite3.connect(db_path) as conn:
        df_dates = pd.read_sql_query("SELECT DISTINCT date FROM price_history ORDER BY date", conn)
    
    if df_dates.empty:
        return []

    df_dates['date_dt'] = pd.to_datetime(df_dates['date'])
    df_dates.set_index('date_dt', inplace=True)
    
    # Resample to specified frequency and get the last available date in each period
    rebal_dates = df_dates.groupby(df_dates.index.to_period(freq)).apply(lambda x: x.index.max())
    
    return [date.strftime('%Y-%m-%d') for date in rebal_dates]

def run_backtest(db_path, initial_capital=100000.0, freq='Q', cost_bps=10.0):
    import screener
    
    with sqlite3.connect(db_path) as conn:
        query = "SELECT date, ticker, adj_close FROM price_history"
        prices = pd.read_sql_query(query, conn)
        
        if prices.empty:
            return {"error": "No price data found"}
        
    prices['date'] = pd.to_datetime(prices['date'])
    

    wide_prices = prices.pivot(index='date', columns='ticker', values='adj_close')
    wide_prices.sort_index(inplace=True)
    
    wide_prices.ffill(inplace=True)
    wide_prices.fillna(0, inplace=True)
    

    if BENCHMARK in wide_prices.columns:
        benchmark_prices = wide_prices[[BENCHMARK]].copy()
    else:
        benchmark_prices = pd.DataFrame(index=wide_prices.index)
        benchmark_prices[BENCHMARK] = 100.0 
        
    benchmark_returns = benchmark_prices[BENCHMARK].pct_change().fillna(0)
    
    rebal_dates = get_rebalance_dates(db_path, freq)
    
    portfolio_value = float(initial_capital)
    shares_held = pd.Series(dtype=float)
    
    equity_curve = []
    
    num_rebalances = 0
    total_holdings_count = 0
    
    for i, current_date in enumerate(wide_prices.index):
        date_str = current_date.strftime('%Y-%m-%d')
        

        if not shares_held.empty:
            current_prices = wide_prices.loc[current_date, shares_held.index]
            current_prices.fillna(0, inplace=True)
            portfolio_value = (shares_held * current_prices).sum()
        

        if date_str in rebal_dates:
            # Rebalance
            eligible_df = screener.screen_stocks(db_path, as_of_date=date_str)
            
            if eligible_df is not None and not eligible_df.empty:
                eligible_tickers = eligible_df['ticker'].tolist()
            else:
                eligible_tickers = []
                
            num_rebalances += 1
            total_holdings_count += len(eligible_tickers)
            
            eligible_tickers = [t for t in eligible_tickers if t in wide_prices.columns and wide_prices.at[current_date, t] > 0]
            
            if not eligible_tickers:
                target_weights = pd.Series(dtype=float)
            else:
                weight = 1.0 / len(eligible_tickers)
                target_weights = pd.Series(weight, index=eligible_tickers)
            
            target_values = target_weights * portfolio_value
            
            if not shares_held.empty:
                current_values = shares_held * wide_prices.loc[current_date, shares_held.index]
                current_values.fillna(0, inplace=True)
            else:
                current_values = pd.Series(dtype=float)
                
            all_assets = list(set(target_values.index) | set(current_values.index))
            t_vals = target_values.reindex(all_assets).fillna(0)
            c_vals = current_values.reindex(all_assets).fillna(0)
            
            traded_value = (t_vals - c_vals).abs().sum()
            tx_costs = traded_value * (cost_bps / 10000.0)
            portfolio_value -= tx_costs
            
            target_values = target_weights * portfolio_value
            current_prices = wide_prices.loc[current_date, target_values.index]
            shares_held = target_values / current_prices
            shares_held.replace([np.inf, -np.inf], 0, inplace=True)
            shares_held.fillna(0, inplace=True)
            
        equity_curve.append({
            'date': date_str,
            'portfolio_value': portfolio_value
        })
        
    df_equity = pd.DataFrame(equity_curve)
    df_equity.set_index('date', inplace=True)
    df_equity.index = pd.to_datetime(df_equity.index)
    
    df_equity['daily_return'] = df_equity['portfolio_value'].pct_change().fillna(0)
    

    df_equity['benchmark_value'] = initial_capital * (1 + benchmark_returns).cumprod()
    if len(df_equity) > 0:
        df_equity['benchmark_value'] = df_equity['benchmark_value'] / df_equity['benchmark_value'].iloc[0] * initial_capital
    
    if len(df_equity) == 0:
        return {"error": "Empty equity curve"}
        
    total_return = (df_equity['portfolio_value'].iloc[-1] / initial_capital) - 1.0
    
    days = (df_equity.index[-1] - df_equity.index[0]).days
    years = days / 365.25 if days > 0 else 1.0
    
    cagr = (1 + total_return) ** (1 / years) - 1.0 if years > 0 else 0.0
    
    annualized_vol = df_equity['daily_return'].std() * np.sqrt(252)
    sharpe_ratio = (cagr - RISK_FREE_RATE) / annualized_vol if annualized_vol > 0 else 0.0
    
    cumulative_max = df_equity['portfolio_value'].cummax()
    drawdown = (df_equity['portfolio_value'] - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    
    avg_holdings = total_holdings_count / num_rebalances if num_rebalances > 0 else 0
    
    metrics = {
        'total_return': total_return,
        'cagr': cagr,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'num_rebalances': num_rebalances,
        'avg_holdings': avg_holdings
    }
    
    with sqlite3.connect(db_path) as conn:
        df_out = df_equity.reset_index().copy()
        df_out['date'] = df_out['date'].dt.strftime('%Y-%m-%d')
        # set date as PK in sqlite
        df_out.to_sql('backtest_results', conn, if_exists='replace', index=False)
        # Create unique index to enforce PK constraint mentally/functionally if needed
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_backtest_date ON backtest_results (date)')
        
    return {
        'metrics': metrics,
        'equity_curve': df_equity
    }

def run_backtester():
    results = run_backtest(DB_PATH, INITIAL_CAPITAL, REBALANCE_FREQ, TRANSACTION_COST_BPS)
    
    if 'error' in results:
        print(f"Error running backtest: {results['error']}")
        return results
        
    metrics = results['metrics']
    
    print("[Backtest] ======================================")
    print("[Backtest]  Performance Summary")
    print("[Backtest] --------------------------------------")
    print(f"[Backtest]  Total Return:      {metrics['total_return']*100:6.1f}%")
    print(f"[Backtest]  CAGR:               {metrics['cagr']*100:6.1f}%")
    print(f"[Backtest]  Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
    print(f"[Backtest]  Max Drawdown:      {metrics['max_drawdown']*100:6.1f}%")
    print(f"[Backtest]  Rebalances:            {metrics['num_rebalances']}")
    print(f"[Backtest]  Avg Holdings:         {metrics['avg_holdings']:.1f}")
    print("[Backtest] ======================================")
    
    return results

if __name__ == '__main__':
    run_backtester()
