import sys
sys.path.insert(0, ".")
from database import get_postgres_connection, check_postgres_health
if check_postgres_health():
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.ticker, i.date, MAX(i.high), MIN(i.low), COUNT(*)
                FROM intraday_chart i
                JOIN ticker t ON t.id = i.id_ticker
                WHERE i.high > 1000
                GROUP BY t.ticker, i.date
                ORDER BY i.date DESC
                LIMIT 10;
            """)
            for row in cur.fetchall():
                print(row)
else:
    print("Postgres health check failed")
