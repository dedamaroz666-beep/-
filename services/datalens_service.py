import datetime
import time
from typing import Dict, List, Any, Optional
import pandas as pd
from database import get_postgres_connection, check_postgres_health

# In-memory cache for fast reuse: key -> (timestamp, result_list)
_HOLD_MOVE_CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300


def calculate_hold_move_dates(
    ticker: str,
    period: str = "1y",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    threshold_pct: float = 1.0,
    min_hold_pct: float = 0.90,
    direction: str = "both",
    window: str = "any",
    hold_until: str = "09:30"
) -> List[str]:
    """
    Finds trading dates where `ticker` moved by at least `threshold_pct` from `prev_close`
    during the specified session window, and maintained at least `min_hold_pct` (noise tolerance)
    continuously until `hold_until` (e.g. 09:30 OPG or 16:30).
    """
    ticker = str(ticker).strip().upper()
    direction = str(direction).strip().lower()
    if direction not in ("both", "up", "down"):
        direction = "both"
    window = str(window).strip().lower()
    if window not in ("any", "premarket", "regular", "postmarket"):
        window = "any"
    hold_until = str(hold_until).strip()
    if hold_until not in ("09:30", "16:30"):
        hold_until = "09:30"

    threshold_pct = float(threshold_pct)
    min_hold_pct = float(min_hold_pct)
    if min_hold_pct > threshold_pct:
        min_hold_pct = threshold_pct

    # Determine date range from period if not given
    today = datetime.date.today()
    if not start_date or not end_date:
        p = str(period).lower().strip()
        if p == "1w":
            s_dt = today - datetime.timedelta(days=7)
        elif p == "1m":
            s_dt = today - datetime.timedelta(days=30)
        elif p == "3m":
            s_dt = today - datetime.timedelta(days=91)
        elif p == "6m":
            s_dt = today - datetime.timedelta(days=182)
        elif p == "ytd":
            s_dt = datetime.date(today.year, 1, 1)
        elif p == "1y":
            s_dt = today - datetime.timedelta(days=365)
        elif p == "2y":
            s_dt = today - datetime.timedelta(days=730)
        elif p == "5y":
            s_dt = today - datetime.timedelta(days=1825)
        elif p == "max":
            s_dt = datetime.date(2015, 1, 1)
        else:
            s_dt = today - datetime.timedelta(days=365)
        start_date = start_date or s_dt.isoformat()
        end_date = end_date or today.isoformat()

    cache_key = f"{ticker}_{start_date}_{end_date}_{threshold_pct}_{min_hold_pct}_{direction}_{window}_{hold_until}"
    now_ts = time.time()
    if cache_key in _HOLD_MOVE_CACHE:
        cached_ts, cached_res = _HOLD_MOVE_CACHE[cache_key]
        if now_ts - cached_ts < CACHE_TTL_SECONDS:
            return cached_res

    hold_until_time = f"{hold_until}:00" if len(hold_until) == 5 else hold_until

    if window == "premarket":
        win_start, win_end = "04:00:00", min("09:30:00", hold_until_time)
    elif window == "regular":
        win_start, win_end = "09:30:00", min("16:00:00", hold_until_time)
    elif window == "postmarket":
        win_start, win_end = "16:00:00", hold_until_time
    else:  # 'any'
        win_start, win_end = "04:00:00", hold_until_time

    # If win_start > win_end (e.g. regular window with 09:30 hold_until), return empty
    if win_start >= win_end:
        return []

    if not check_postgres_health():
        return []

    try:
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

                # 2. Filter candidate days that reached threshold during [win_start, win_end]
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

                    can_up = (direction in ("both", "up")) and (max_up >= threshold_pct)
                    can_down = (direction in ("both", "down")) and (max_down <= -threshold_pct)
                    if can_up or can_down:
                        candidate_days.append(d_str)

                if not candidate_days:
                    _HOLD_MOVE_CACHE[cache_key] = (now_ts, [])
                    return []

                # 3. Fetch 1-min bars for candidate days up to hold_until_time
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
            pc = daily_prev_close.get(d_str)
            bars = bars_by_date.get(d_str, [])
            if not pc or not bars:
                continue

            # Ensure the session actually traded up to the target hold_until cutoff
            last_bar_time = bars[-1][0]
            min_cutoff_time = "09:20:00" if hold_until == "09:30" else "16:20:00"
            if last_bar_time < min_cutoff_time:
                continue


            # Check UP (+)
            up_ok = False
            if direction in ("both", "up"):
                unbroken_from_idx = len(bars)
                for idx in range(len(bars) - 1, -1, -1):
                    t_str, o, h, l, c = bars[idx]
                    curr_move = (l - pc) / pc * 100.0
                    if curr_move >= min_hold_pct:
                        unbroken_from_idx = idx
                    else:
                        break

                for idx in range(unbroken_from_idx, len(bars)):
                    t_str, o, h, l, c = bars[idx]
                    if win_start <= t_str <= win_end:
                        if (h - pc) / pc * 100.0 >= threshold_pct:
                            up_ok = True
                            break

            # Check DOWN (-)
            down_ok = False
            if direction in ("both", "down") and not up_ok:
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

        res = sorted(passed_dates)
        _HOLD_MOVE_CACHE[cache_key] = (now_ts, res)
        return res
    except Exception as e:
        print(f"[DataLensService] Error calculating hold-move dates for {ticker}:", e)
        return []
