import sys
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_postgres_connection

with get_postgres_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT UPPER(t.ticker), COUNT(*), MIN(i.date)::text, MAX(i.date)::text
            FROM intraday_chart i
            JOIN ticker t ON t.id = i.id_ticker
            WHERE UPPER(t.ticker) IN ('MU', 'AAPL', 'SPY', 'QQQ', 'NVDA')
            GROUP BY t.ticker;
        """)
        for row in cur.fetchall():
            print(row)
