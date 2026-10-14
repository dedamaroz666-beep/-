import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import psycopg
from psycopg.rows import dict_row
from config import DB_CONFIG, DATABASE_URL
from database import get_ticker_reports, get_stock_data, check_postgres_health, get_postgres_connection
from services.fmp_service import fmp_client
from services.polygon_service import polygon_client
from services.earnings_extra_service import get_ticker_earnings_extra_map, find_matching_earnings_extra


def is_report_already_released(rep: Dict[str, Any]) -> bool:
    """
    Checks if an earnings report has already been officially released.
    Rules:
    1. If report date is in the future (> today ET), it hasn't reported.
    2. If report date is in the past (< today ET), it has already reported.
    3. If report date is TODAY:
       - If actual numbers (eps_actual or revenue_actual) exist -> True (reported).
       - If actual numbers are missing:
         - AMC: regular session ends at 16:00 ET. If current ET time < 16:05 (or still missing actuals before 17:30 ET),
           the company has NOT reported yet -> False.
         - BMO: if before 09:30 ET and no actuals -> False.
         - Otherwise, if no actual numbers and market session for report has not completed -> False.
    """
    if not rep or not isinstance(rep, dict):
        return False
    r_date_raw = rep.get("date")
    if not r_date_raw:
        return False

    if isinstance(r_date_raw, (datetime.date, datetime.datetime, pd.Timestamp)):
        r_date = r_date_raw.date() if hasattr(r_date_raw, "date") else r_date_raw
    else:
        try:
            r_date = datetime.date.fromisoformat(str(r_date_raw).split(" ")[0].split("T")[0])
        except Exception:
            return False

    try:
        import zoneinfo
        now_et = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)
        
    today_et = now_et.date()

def parse_earnings_session(time_val: Any) -> str:
    """
    Determines if an earnings session is BMO (Before Market Open) or AMC (After Market Close).
    US Regular Market Hours: 09:30 - 16:00 ET.
    - Any report before 09:30 ET (including Asian/European night releases 00:00 - 06:00, 07:00, 08:00, 09:00) is BMO.
    - Any report at or after 16:00 ET (e.g., 16:05, 17:00) is AMC.
    """
    if not time_val:
        return "bmo"
    t_str = str(time_val).lower().strip()
    if "amc" in t_str or "after" in t_str or "post" in t_str:
        return "amc"
    if "bmo" in t_str or "before" in t_str or "pre" in t_str:
        return "bmo"
    try:
        parts = t_str.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if h < 9 or (h == 9 and m <= 30):
            return "bmo"
        if h >= 16:
            return "amc"
    except Exception:
        pass
    return "bmo"


def is_report_already_released(rep: Dict[str, Any]) -> bool:
    """
    Checks if an earnings report has already been officially released.
    Rules:
    1. If report date is in the future (> today ET), it hasn't reported.
    2. If report date is in the past (< today ET), it has already reported.
    3. If report date is TODAY:
       - If actual numbers (eps_actual or revenue_actual) exist -> True (reported).
       - If actual numbers are missing:
         - AMC: regular session ends at 16:00 ET. If current ET time < 16:05 (or still missing actuals before 17:30 ET),
           the company has NOT reported yet -> False.
         - BMO: if before 09:30 ET and no actuals -> False.
         - Otherwise, if no actual numbers and market session for report has not completed -> False.
    """
    if not rep or not isinstance(rep, dict):
        return False
    r_date_raw = rep.get("date")
    if not r_date_raw:
        return False

    if isinstance(r_date_raw, (datetime.date, datetime.datetime, pd.Timestamp)):
        r_date = r_date_raw.date() if hasattr(r_date_raw, "date") else r_date_raw
    else:
        try:
            r_date = datetime.date.fromisoformat(str(r_date_raw).split(" ")[0].split("T")[0])
        except Exception:
            return False

    try:
        import zoneinfo
        now_et = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)
        
    today_et = now_et.date()

    if r_date > today_et:
        return False

    if r_date < today_et:
        return True

    # r_date == today_et (Company reports TODAY)
    session_str = parse_earnings_session(rep.get("time"))
    is_bmo = session_str == "bmo"

    current_time_et = now_et.time()

    # If it's AMC and market is still open (before 16:00 ET), it has definitely not reported yet
    if not is_bmo and current_time_et < datetime.time(16, 0):
        return False

    # If it's BMO and before 06:30 ET, it has not reported yet
    if is_bmo and current_time_et < datetime.time(6, 30):
        return False

    # On today's date, require actual numbers (eps_actual or revenue_actual) to confirm official release
    has_actuals = (rep.get("eps_actual") is not None) or (rep.get("revenue_actual") is not None)
    return has_actuals


class EarningsReactionService:
    def __init__(self):
        self._cache = {}

    def get_earnings_reaction_matrix(
        self,
        ticker: str,
        limit: int = 8,
        premarket_window: str = "04:00_09:30"
    ) -> List[Dict[str, Any]]:
        """
        Calculates the comprehensive Earnings Reaction Matrix for the last `limit` quarters.
        Uses single-query batch optimization for high performance.
        """
        ticker = str(ticker).strip().upper()
        # 5-minute rolling TTL to keep cache fresh when reports are released
        cache_key = f"{ticker}_{limit}_{premarket_window}_{int(datetime.datetime.now().timestamp() // 300)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Fetch reports from DB (primary) or FMP (fallback)
        db_reports_df = get_ticker_reports(ticker)
        extra_map = get_ticker_earnings_extra_map(ticker)

        reports_list = []
        seen_dates = set()
        seen_date_objs = []

        if not db_reports_df.empty:
            for _, row in db_reports_df.iterrows():
                r_date = str(row["date"])
                try:
                    d_obj = datetime.date.fromisoformat(r_date)
                    if any(abs((d_obj - prev).days) < 45 for prev in seen_date_objs):
                        continue
                    seen_date_objs.append(d_obj)
                except Exception:
                    if r_date in seen_dates:
                        continue
                seen_dates.add(r_date)

                extra_info = find_matching_earnings_extra(extra_map, r_date)
                if not extra_info and row.get("move_date"):
                    extra_info = find_matching_earnings_extra(extra_map, str(row["move_date"]))

                session_str = parse_earnings_session(row.get("time"))
                quarter_name = f"{row.get('fiscal_period', '')} {row.get('fiscal_year', '')}".strip() or None
                reports_list.append({
                    "ticker": ticker,
                    "date": r_date,
                    "time": session_str,
                    "quarter": quarter_name,
                    "eps_actual": extra_info.get("eps_actual") if extra_info else None,
                    "eps_estimate": extra_info.get("eps_estimate") if extra_info else None,
                    "eps_surprise_pct": extra_info.get("eps_surprise_pct") if extra_info else None,
                    "revenue_actual": extra_info.get("revenue_actual") if extra_info else None,
                    "revenue_estimate": extra_info.get("revenue_estimate") if extra_info else None
                })
        else:
            fmp_reports = fmp_client.get_earnings_history(ticker, limit=limit + 4)
            for fr in fmp_reports:
                r_date = fr.get("date")
                if not r_date:
                    continue
                try:
                    d_obj = datetime.date.fromisoformat(r_date)
                    if any(abs((d_obj - prev).days) < 45 for prev in seen_date_objs):
                        continue
                    seen_date_objs.append(d_obj)
                except Exception:
                    if r_date in seen_dates:
                        continue
                seen_dates.add(r_date)

                extra_info = find_matching_earnings_extra(extra_map, r_date)
                session_str = parse_earnings_session(fr.get("time"))
                reports_list.append({
                    "ticker": ticker,
                    "date": r_date,
                    "time": session_str,
                    "quarter": None,
                    "eps_actual": fr.get("eps_actual") if fr.get("eps_actual") is not None else (extra_info.get("eps_actual") if extra_info else None),
                    "eps_estimate": fr.get("eps_estimate") if fr.get("eps_estimate") is not None else (extra_info.get("eps_estimate") if extra_info else None),
                    "eps_surprise_pct": fr.get("eps_surprise_pct") if fr.get("eps_surprise_pct") is not None else (extra_info.get("eps_surprise_pct") if extra_info else None),
                    "revenue_actual": fr.get("revenue_actual") if fr.get("revenue_actual") is not None else (extra_info.get("revenue_actual") if extra_info else None),
                    "revenue_estimate": fr.get("revenue_estimate") if fr.get("revenue_estimate") is not None else (extra_info.get("revenue_estimate") if extra_info else None)
                })

        # Sort descending by date and take last `limit` past/released reports (strictly excluding unreleased reports)
        past_reports = [r for r in reports_list if is_report_already_released(r)]
        past_reports.sort(key=lambda x: x.get("date", ""), reverse=True)
        target_reports = past_reports[:limit]

        if not target_reports:
            return []

        # 2. Fetch daily OHLCV
        daily_df = get_stock_data(ticker)
        if daily_df.empty:
            poly_daily = polygon_client.fetch_daily_bars(ticker, start_date="2021-01-01")
            if poly_daily:
                daily_df = pd.DataFrame(poly_daily)
                daily_df["date"] = pd.to_datetime(daily_df["date"])

        if not daily_df.empty:
            daily_df["date_str"] = pd.to_datetime(daily_df["date"]).dt.strftime("%Y-%m-%d")
            daily_df = daily_df.sort_values("date_str").reset_index(drop=True)

        # 3. Collect all needed dates for batch intraday query (R-1, R, R+1, R+2)
        all_reaction_dates = []
        reports_trading_indices = []

        for rep in target_reports:
            rep_date = rep["date"]
            session_time = parse_earnings_session(rep.get("time"))
            is_bmo = session_time == "bmo"

            # Find matching or nearest daily index
            r_idx = None
            if not daily_df.empty:
                matches = daily_df.index[daily_df["date_str"] == rep_date].tolist()
                if matches:
                    r_idx = matches[0]
                else:
                    prior_matches = daily_df.index[daily_df["date_str"] <= rep_date].tolist()
                    if prior_matches:
                        r_idx = prior_matches[-1]

            reports_trading_indices.append((rep, r_idx, is_bmo))

            if r_idx is not None:
                for offset in [-1, 0, 1, 2]:
                    target_idx = r_idx + offset
                    if 0 <= target_idx < len(daily_df):
                        all_reaction_dates.append(daily_df.iloc[target_idx]["date_str"])

        all_reaction_dates = list(set(all_reaction_dates))

        # Single batch query to PostgreSQL for all intraday dates
        intraday_by_date = {}
        if check_postgres_health() and all_reaction_dates:
            try:
                sql = """
                    SELECT 
                        i.date::text as date,
                        to_char(i.time, 'HH24:MI') as time_str,
                        i.open::float as open,
                        i.high::float as high,
                        i.low::float as low,
                        i.close::float as close,
                        i.volume::float as volume
                    FROM intraday_chart i
                    JOIN ticker t ON t.id = i.id_ticker
                    WHERE UPPER(t.ticker) = %s
                      AND i.date = ANY(%s::date[])
                    ORDER BY i.date ASC, i.time ASC;
                """
                with get_postgres_connection() as conn:
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute(sql, (ticker, all_reaction_dates))
                        rows = cur.fetchall()
                        for r in rows:
                            d_str = r["date"]
                            if d_str not in intraday_by_date:
                                intraday_by_date[d_str] = []
                            intraday_by_date[d_str].append(r)
            except Exception as e:
                print(f"[EarningsReactionService] Batch intraday query error: {e}")

        # 4. Build results
        results = []

        for rep, r_idx, is_bmo in reports_trading_indices:
            rep_date = rep["date"]

            days_metrics = {}
            day_keys = [("R-1", -1), ("R", 0), ("R+1", 1), ("R+2", 2)]

            if r_idx is not None and not daily_df.empty:
                for label, offset in day_keys:
                    curr_i = r_idx + offset
                    if 0 <= curr_i < len(daily_df):
                        curr_row = daily_df.iloc[curr_i]
                        curr_date = curr_row["date_str"]
                        curr_open = float(curr_row["open"])
                        curr_close = float(curr_row["close"])
                        curr_high = float(curr_row["high"])
                        curr_low = float(curr_row["low"])

                        prev_close = None
                        if curr_i > 0:
                            prev_close = float(daily_df.iloc[curr_i - 1]["close"])

                        # 1. Close-to-Close %
                        c2c_pct = None
                        if prev_close and prev_close > 0:
                            c2c_pct = round(((curr_close - prev_close) / prev_close) * 100.0, 2)

                        # 2. Intraday % (Open to Close)
                        intra_pct = None
                        if curr_open > 0:
                            intra_pct = round(((curr_close - curr_open) / curr_open) * 100.0, 2)

                        # 3. Premarket % (04:00 - 09:30 or Open vs PrevClose)
                        pre_pct = None
                        bars_for_day = intraday_by_date.get(curr_date, [])
                        pre_bars = [b for b in bars_for_day if "04:00" <= b["time_str"] <= "09:30"]
                        if pre_bars and prev_close and prev_close > 0:
                            pre_close_val = float(pre_bars[-1]["close"])
                            pre_pct = round(((pre_close_val - prev_close) / prev_close) * 100.0, 2)
                        elif prev_close and curr_open and prev_close > 0:
                            pre_pct = round(((curr_open - prev_close) / prev_close) * 100.0, 2)

                        # 4. Postmarket % (16:00 - 20:00 vs Regular Close)
                        post_pct = None
                        pm_bars = [b for b in bars_for_day if "16:00" <= b["time_str"] <= "20:00"]
                        if pm_bars and curr_close > 0:
                            pm_close_val = float(pm_bars[-1]["close"])
                            post_pct = round(((pm_close_val - curr_close) / curr_close) * 100.0, 2)
                        elif curr_i + 1 < len(daily_df) and curr_close > 0:
                            next_open = float(daily_df.iloc[curr_i + 1]["open"])
                            post_pct = round(((next_open - curr_close) / curr_close) * 0.85, 2)

                        days_metrics[label] = {
                            "date": curr_date,
                            "open": curr_open,
                            "close": curr_close,
                            "high": curr_high,
                            "low": curr_low,
                            "prev_close": prev_close,
                            "close_to_close": c2c_pct,
                            "premarket": pre_pct,
                            "intraday": intra_pct,
                            "postmarket": post_pct
                        }
                    else:
                        days_metrics[label] = {
                            "date": None,
                            "open": None,
                            "close": None,
                            "high": None,
                            "low": None,
                            "prev_close": None,
                            "close_to_close": None,
                            "premarket": None,
                            "intraday": None,
                            "postmarket": None
                        }

            # Backward-compatible fields
            r_day = days_metrics.get("R", {})
            r_minus_1 = days_metrics.get("R-1", {})
            r_plus_1 = days_metrics.get("R+1", {})

            # Reaction date
            reaction_date = rep_date if is_bmo else (r_plus_1.get("date") or rep_date)

            if rep.get("quarter"):
                quarter_label = rep["quarter"]
            else:
                try:
                    dt_obj = datetime.date.fromisoformat(rep_date)
                    quarter = (dt_obj.month - 1) // 3 + 1
                    quarter_label = f"Q{quarter} {dt_obj.year}"
                except Exception:
                    quarter_label = rep_date

            results.append({
                "date": rep_date,
                "reaction_date": reaction_date,
                "quarter": quarter_label,
                "session": "BMO" if is_bmo else "AMC",
                "prev_close": r_day.get("prev_close"),
                "rep_open": r_day.get("open"),
                "rep_close": r_day.get("close"),
                "eps_actual": rep.get("eps_actual"),
                "eps_estimate": rep.get("eps_estimate"),
                "eps_surprise_pct": rep.get("eps_surprise_pct"),
                "revenue_actual": rep.get("revenue_actual"),
                "revenue_estimate": rep.get("revenue_estimate"),
                "postmarket_1d_pct": r_minus_1.get("postmarket") or r_day.get("postmarket"),
                "premarket_0d_pct": r_day.get("premarket"),
                "open_to_close_pct": r_day.get("intraday"),
                "cls2cls_pct": r_day.get("close_to_close"),
                "days": days_metrics
            })

        self._cache[cache_key] = results
        return results


# Singleton instance
earnings_reaction_client = EarningsReactionService()
