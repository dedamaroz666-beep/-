import sys
import time
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_postgres_connection

ticker = 'MU'
hold_until = '09:30:00'
window_start = '04:00:00'
window_end = '09:30:00'
threshold_pct = 1.0
min_hold_pct = 0.90 # allow pullbacks down to 0.90%
direction = 'both' # 'both', 'up', 'down'

t0 = time.time()
with get_postgres_connection() as conn:
    with conn.cursor() as cur:
        # Step 1: Get daily prev_close
        cur.execute("""
            SELECT d.date::text, d.prev_close::float
            FROM daily d
            JOIN ticker t ON t.id = d.id_ticker
            WHERE UPPER(t.ticker) = %s AND d.prev_close IS NOT NULL AND d.prev_close > 0
              AND d.date >= '2024-01-01'
        """, (ticker,))
        daily_prev_close = dict(cur.fetchall())

        # Step 2: In SQL, find dates that reached the threshold during the window
        cur.execute("""
            SELECT 
                i.date::text,
                MAX(i.high)::float as max_high,
                MIN(i.low)::float as min_low
            FROM intraday_chart i
            JOIN ticker t ON t.id = i.id_ticker
            WHERE UPPER(t.ticker) = %s
              AND i.date >= '2024-01-01'
              AND i.time >= %s AND i.time <= %s
            GROUP BY i.date;
        """, (ticker, window_start, window_end))
        candidate_days = []
        for d_str, max_h, min_l in cur.fetchall():
            pc = daily_prev_close.get(d_str)
            if not pc or pc <= 0:
                continue
            max_move_up = (max_h - pc) / pc * 100.0
            max_move_down = (min_l - pc) / pc * 100.0
            
            can_up = (direction in ('both', 'up')) and (max_move_up >= threshold_pct)
            can_down = (direction in ('both', 'down')) and (max_move_down <= -threshold_pct)
            if can_up or can_down:
                candidate_days.append(d_str)

        print(f"Candidate days count: {len(candidate_days)} in {time.time() - t0:.3f}s")

        # Step 3: For candidate days, check holding condition until hold_until
        cur.execute("""
            SELECT i.date::text, to_char(i.time, 'HH24:MI:SS') as time_str, i.open::float, i.high::float, i.low::float, i.close::float
            FROM intraday_chart i
            JOIN ticker t ON t.id = i.id_ticker
            WHERE UPPER(t.ticker) = %s
              AND i.date = ANY(%s::date[])
              AND i.time <= %s
            ORDER BY i.date ASC, i.time ASC;
        """, (ticker, candidate_days, hold_until))
        
        bars_by_date = {}
        for r in cur.fetchall():
            d_str, t_str, o, h, l, c = r
            if d_str not in bars_by_date:
                bars_by_date[d_str] = []
            bars_by_date[d_str].append((t_str, o, h, l, c))

passed_days = []
for d_str in candidate_days:
    pc = daily_prev_close[d_str]
    bars = bars_by_date.get(d_str, [])
    if not bars:
        continue
    
    # Check UP:
    # First reached +threshold_pct during window (window_start <= time <= window_end)
    # Then from that bar until hold_until (all subsequent bars up to hold_until),
    # low does not fall below +min_hold_pct
    up_passed = False
    if direction in ('both', 'up'):
        reached_idx = None
        for idx, (t_str, o, h, l, c) in enumerate(bars):
            if window_start <= t_str <= window_end:
                if (h - pc) / pc * 100.0 >= threshold_pct:
                    reached_idx = idx
                    break
        if reached_idx is not None:
            # Check holding from reached_idx to the end of bars (which are <= hold_until)
            held = True
            for idx in range(reached_idx, len(bars)):
                t_str, o, h, l, c = bars[idx]
                curr_move = (l - pc) / pc * 100.0
                if curr_move < min_hold_pct:
                    held = False
                    break
            if held:
                up_passed = True

    # Check DOWN:
    # First reached -threshold_pct during window
    # Then from that bar until hold_until, high does not exceed -min_hold_pct
    down_passed = False
    if direction in ('both', 'down') and not up_passed:
        reached_idx = None
        for idx, (t_str, o, h, l, c) in enumerate(bars):
            if window_start <= t_str <= window_end:
                if (l - pc) / pc * 100.0 <= -threshold_pct:
                    reached_idx = idx
                    break
        if reached_idx is not None:
            held = True
            for idx in range(reached_idx, len(bars)):
                t_str, o, h, l, c = bars[idx]
                curr_move = (h - pc) / pc * 100.0
                if curr_move > -min_hold_pct:
                    held = False
                    break
            if held:
                down_passed = True

    if up_passed or down_passed:
        passed_days.append((d_str, 'UP' if up_passed else 'DOWN'))

t_end = time.time()
print(f"Passed days count: {len(passed_days)} out of {len(candidate_days)}")
print(f"Sample passed days: {passed_days[:10]}")
print(f"Total calculation time: {t_end - t0:.3f}s")
