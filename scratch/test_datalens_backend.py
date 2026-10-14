import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
import datetime
from database import get_stock_data, get_postgres_connection

def test_datalens_data(tickers=["SPY", "QQQ", "MU"]):
    df = get_stock_data(*tickers)
    if df.empty:
        print("Empty df")
        return
    
    print("Fetched df shape:", df.shape)
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    
    # Calculate intra % if not present: (close - open) / open * 100
    df["intra"] = np.where(df["open"] > 0, (df["close"] - df["open"]) / df["open"] * 100.0, 0.0)
    
    # Fetch earnings dates
    earnings_dates = set()
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT UPPER(t.ticker), r.date::text, r.move_date::text
            FROM reports r
            JOIN ticker t ON t.id = r.id_ticker
            WHERE UPPER(t.ticker) = ANY(%s)
        """, (tickers,))
        for row in cur.fetchall():
            sym, r_date, m_date = row
            if r_date: earnings_dates.add((sym, r_date))
            if m_date: earnings_dates.add((sym, m_date))
        print("Found earnings events count:", len(earnings_dates))
    except Exception as e:
        print("Earnings query error:", e)

    import sqlite3
    from config import CACHE_DB_PATH
    ex_div_dates = set()
    pay_dates = set()
    try:
        s_conn = sqlite3.connect(CACHE_DB_PATH)
        s_cur = s_conn.cursor()
        q_marks = ",".join(["?"] * len(tickers))
        s_cur.execute(f"SELECT ticker, ex_date, pay_date FROM dividends WHERE ticker IN ({q_marks})", tickers)
        for row in s_cur.fetchall():
            t_sym, ex_d, pay_d = row
            if ex_d: ex_div_dates.add((t_sym.upper(), ex_d))
            if pay_d: pay_dates.add((t_sym.upper(), pay_d))
        print(f"Found ex-div dates: {len(ex_div_dates)}, pay dates: {len(pay_dates)}")
    except Exception as e:
        print("Dividends query error:", e)


    # Pivot / group by date
    dates = sorted(df["date_str"].unique(), reverse=True)
    print("Total unique dates:", len(dates), "Latest date:", dates[0] if dates else "None")
    
    # Test filter: MU |cls2cls| >= 2
    sample_filter_ticker = "MU"
    mu_df = df[df["ticker"] == sample_filter_ticker]
    filtered_dates = set(mu_df[mu_df["cls2cls"].abs() >= 2.0]["date_str"])
    print(f"Dates where |{sample_filter_ticker} cls2cls| >= 2%: {len(filtered_dates)}")
    
    matched_dates = [d for d in dates if d in filtered_dates]
    print("Sample matched dates:", matched_dates[:5])

if __name__ == "__main__":
    test_datalens_data()
