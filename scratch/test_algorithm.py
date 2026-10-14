import sys
import time
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_postgres_connection

def find_hold_move_dates(
    ticker: str,
    start_date: str = "2024-01-01",
    end_date: str = "2026-10-10",
    threshold_pct: float = 1.0,
    min_hold_pct: float = 0.90,
    direction: str = "both", # 'both', 'up', 'down'
    window: str = "premarket", # 'any', 'premarket', 'regular', 'postmarket'
    hold_until: str = "09:30" # '09:30', '16:30'
):
    hold_until_time = f"{hold_until}:00" if len(hold_until) == 5 else hold_until
    
    if window == "premarket":
        win_start, win_end = "04:00:00", min("09:30:00", hold_until_time)
    elif window == "regular":
        win_start, win_end = "09:30:00", min("16:00:00", hold_until_time)
    elif window == "postmarket":
        win_start, win_end = "16:00:00", hold_until_time
    else: # 'any'
        win_start, win_end = "04:00:00", hold_until_time

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch daily prev_close
            cur.execute("""
                SELECT d.date::text, d.prev_close::float
                FROM daily d
                JOIN ticker t ON t.id = d.id_ticker
                WHERE UPPER(t.ticker) = %s AND d.prev_close IS NOT NULL AND d.prev_close > 0
                  AND d.date >= %s AND d.date <= %s
                ORDER BY d.date ASC;
            """, (ticker, start_date, end_date))
            daily_prev_close = dict(cur.fetchall())

            if not daily_prev_close:
                return []

            # 2. Candidate days
            cur.execute("""
                SELECT 
                    i.date::text,
                    MAX(i.high)::float,
                    MIN(i.low)::float
                FROM intraday_chart i
                JOIN ticker t ON t.id = i.id_ticker
                WHERE UPPER(t.ticker) = %s
                  AND i.date >= %s AND i.date <= %s
                  AND i.time >= %s AND i.time <= %s
                GROUP BY i.date;
            """, (ticker, start_date, end_date, win_start, win_end))
            
            candidate_days = []
            for d_str, max_h, min_l in cur.fetchall():
                pc = daily_prev_close.get(d_str)
                if not pc or pc <= 0:
                    continue
                max_up = (max_h - pc) / pc * 100.0
                max_down = (min_l - pc) / pc * 100.0
                
                can_up = (direction in ('both', 'up')) and (max_up >= threshold_pct)
                can_down = (direction in ('both', 'down')) and (max_down <= -threshold_pct)
                if can_up or can_down:
                    candidate_days.append(d_str)

            if not candidate_days:
                return []

            # 3. Fetch bars for candidate days up to hold_until_time
            cur.execute("""
                SELECT i.date::text, to_char(i.time, 'HH24:MI:SS'), i.open::float, i.high::float, i.low::float, i.close::float
                FROM intraday_chart i
                JOIN ticker t ON t.id = i.id_ticker
                WHERE UPPER(t.ticker) = %s
                  AND i.date = ANY(%s::date[])
                  AND i.time <= %s
                ORDER BY i.date ASC, i.time ASC;
            """, (ticker, candidate_days, hold_until_time))
            
            bars_by_date = {}
            for r in cur.fetchall():
                d_str, t_str, o, h, l, c = r
                if d_str not in bars_by_date:
                    bars_by_date[d_str] = []
                bars_by_date[d_str].append((t_str, o, h, l, c))

    passed_dates = []
    for d_str in candidate_days:
        pc = daily_prev_close[d_str]
        bars = bars_by_date.get(d_str, [])
        if not bars:
            continue
        
        # We need the cutoff to be reached (at least 1 bar close to hold_until_time, e.g. >= 09:25 or >= 16:25)
        last_t = bars[-1][0]
        # Check if bars reach close to hold_until_time (within 10 minutes)
        
        # Check UP
        up_ok = False
        if direction in ('both', 'up'):
            # Walk backwards from the last bar to find if there is an unbroken run of low >= min_hold_pct
            # that contains a bar with high >= threshold_pct inside [win_start, win_end]
            unbroken_from_idx = len(bars)
            for idx in range(len(bars) - 1, -1, -1):
                t_str, o, h, l, c = bars[idx]
                curr_move = (l - pc) / pc * 100.0
                if curr_move >= min_hold_pct:
                    unbroken_from_idx = idx
                else:
                    break
            
            # Within [unbroken_from_idx, len(bars)-1], did any bar reach threshold_pct inside window?
            for idx in range(unbroken_from_idx, len(bars)):
                t_str, o, h, l, c = bars[idx]
                if win_start <= t_str <= win_end:
                    if (h - pc) / pc * 100.0 >= threshold_pct:
                        up_ok = True
                        break

        # Check DOWN
        down_ok = False
        if direction in ('both', 'down') and not up_ok:
            unbroken_from_idx = len(bars)
            for idx in range(len(bars) - 1, -1, -1):
                t_str, o, h, l, c = bars[idx]
                curr_move = (h - pc) / pc * 100.0
                if curr_move <= -min_hold_pct:
                    unbroken_from_idx = idx
                else:
                    break
            
            for idx in range(unbroken_from_idx, len(bars)):
                t_str, o, h, l, c = bars[idx]
                if win_start <= t_str <= win_end:
                    if (l - pc) / pc * 100.0 <= -threshold_pct:
                        down_ok = True
                        break

        if up_ok or down_ok:
            passed_dates.append(d_str)

    return sorted(passed_dates)

t0 = time.time()
res_mu_opg = find_hold_move_dates('MU', '2024-01-01', '2026-10-10', 1.0, 0.90, 'both', 'premarket', '09:30')
print(f"MU premarket -> 09:30: {len(res_mu_opg)} dates found in {time.time() - t0:.2f}s")
print("First 5:", res_mu_opg[:5])

t1 = time.time()
res_mu_1630 = find_hold_move_dates('MU', '2024-01-01', '2026-10-10', 1.0, 0.90, 'both', 'any', '16:30')
print(f"MU any -> 16:30: {len(res_mu_1630)} dates found in {time.time() - t1:.2f}s")
print("First 5:", res_mu_1630[:5])
