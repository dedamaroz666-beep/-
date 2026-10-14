import sys
import time
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_postgres_connection

# Test query for ticker 'MU'
ticker = 'MU'
hold_until = '09:30:00' # or '16:30:00'
threshold_pct = 1.0
min_hold_pct = 0.90 # allow pullbacks down to 0.90%
window_start = '04:00:00'
window_end = '09:30:00'

t0 = time.time()
with get_postgres_connection() as conn:
    with conn.cursor() as cur:
        # 1. Get daily prev_close for ticker
        cur.execute("""
            SELECT d.date::text, d.prev_close::float
            FROM daily d
            JOIN ticker t ON t.id = d.id_ticker
            WHERE UPPER(t.ticker) = %s AND d.prev_close IS NOT NULL AND d.prev_close > 0
              AND d.date >= '2024-01-01'
            ORDER BY d.date ASC;
        """, (ticker,))
        daily_prev_close = dict(cur.fetchall())
        print(f"Fetched {len(daily_prev_close)} daily prev_close records in {time.time() - t0:.3f}s")

        # 2. Test querying intraday bars for 2024 for MU
        t1 = time.time()
        cur.execute("""
            SELECT i.date::text, to_char(i.time, 'HH24:MI:SS') as time_str, i.open::float, i.high::float, i.low::float, i.close::float
            FROM intraday_chart i
            JOIN ticker t ON t.id = i.id_ticker
            WHERE UPPER(t.ticker) = %s
              AND i.date >= '2024-01-01'
              AND i.time <= %s
            ORDER BY i.date ASC, i.time ASC;
        """, (ticker, hold_until))
        rows = cur.fetchall()
        print(f"Fetched {len(rows)} intraday bars in {time.time() - t1:.3f}s")

print(f"Total time: {time.time() - t0:.3f}s")
