import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_postgres_connection
conn = get_postgres_connection()
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'reports'")
print("Columns in reports:", cur.fetchall())
cur.execute("SELECT r.* FROM reports r JOIN ticker t ON t.id = r.id_ticker WHERE UPPER(t.ticker) = 'MU' LIMIT 5")
print("Sample MU reports:", cur.fetchall())

