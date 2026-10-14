import sys
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
import yfinance as yf
import sqlite3
from database import CACHE_DB_PATH
import pandas as pd

t = yf.Ticker('TSM')
ed = t.earnings_dates
if ed is not None and not ed.empty:
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        for dt_idx, row in ed.iterrows():
            d_str = dt_idx.strftime('%Y-%m-%d')
            eps_act = row.get('Reported EPS')
            eps_est = row.get('EPS Estimate')
            surp = row.get('Surprise(%)')
            conn.execute('''
                INSERT INTO reports_extra (ticker, date, eps_actual, eps_estimate, eps_surprise_pct, time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                    eps_actual = excluded.eps_actual,
                    eps_estimate = excluded.eps_estimate,
                    eps_surprise_pct = excluded.eps_surprise_pct,
                    time = excluded.time
            ''', (
                'TSM',
                d_str,
                float(eps_act) if pd.notnull(eps_act) else None,
                float(eps_est) if pd.notnull(eps_est) else None,
                float(surp) if pd.notnull(surp) else None,
                'BMO'
            ))
        conn.execute("DELETE FROM reports_extra WHERE ticker = 'TSM' AND date IN ('2024-08-14', '2024-11-14', '2025-05-15')")
        conn.commit()
print('Cache successfully updated with yfinance dates for TSM')
