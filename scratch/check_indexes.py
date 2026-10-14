import sys
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_postgres_connection

with get_postgres_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'intraday_chart';
        """)
        for r in cur.fetchall():
            print(r)
