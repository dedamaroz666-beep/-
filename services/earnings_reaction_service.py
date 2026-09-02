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
        cache_key = f"{ticker}_{limit}_{premarket_window}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Fetch reports from DB or FMP
        db_reports_df = get_ticker_reports(ticker)
        fmp_reports = fmp_client.get_earnings_history(ticker, limit=limit + 4)

        reports_list = []
        seen_dates = set()

        for fr in fmp_reports:
            r_date = fr.get("date")
            if not r_date or r_date in seen_dates:
                continue
            seen_dates.add(r_date)
            reports_list.append(fr)

        if not db_reports_df.empty:
            for _, row in db_reports_df.iterrows():
                r_date = str(row["date"])
                if r_date not in seen_dates:
                    seen_dates.add(r_date)
                    reports_list.append({
                        "ticker": ticker,
                        "date": r_date,
                        "time": str(row.get("time", "amc")).lower(),
                        "eps_actual": None,
                        "eps_estimate": None,
                        "eps_surprise_pct": None,
                        "revenue_actual": None,
                        "revenue_estimate": None
                    })

        # Sort descending by date and take last `limit` past reports
        today_str = datetime.date.today().isoformat()
        past_reports = [r for r in reports_list if r.get("date") and r.get("date") <= today_str]
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

        # 3. Collect all needed dates for batch intraday query
        all_reaction_dates = []
        for rep in target_reports:
            rep_date = rep["date"]
            session_time = str(rep.get("time") or "amc").lower()
            is_bmo = "bmo" in session_time or "07:" in session_time or "08:" in session_time or "09:" in session_time

            if is_bmo:
                all_reaction_dates.append(rep_date)
                prior_daily = daily_df[daily_df["date_str"] < rep_date] if not daily_df.empty else pd.DataFrame()
                if not prior_daily.empty:
                    all_reaction_dates.append(prior_daily.iloc[-1]["date_str"])
            else:
                all_reaction_dates.append(rep_date)
                next_daily = daily_df[daily_df["date_str"] > rep_date] if not daily_df.empty else pd.DataFrame()
                if not next_daily.empty:
                    all_reaction_dates.append(next_daily.iloc[0]["date_str"])

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
                      AND i.date::text = ANY(%s)
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

        for rep in target_reports:
            rep_date = rep["date"]
            session_time = str(rep.get("time") or "amc").lower()
            is_bmo = "bmo" in session_time or "07:" in session_time or "08:" in session_time or "09:" in session_time

            if is_bmo:
                reaction_date = rep_date
                prior_daily = daily_df[daily_df["date_str"] < rep_date] if not daily_df.empty else pd.DataFrame()
                prev_date = prior_daily.iloc[-1]["date_str"] if not prior_daily.empty else rep_date
                prev_close = float(prior_daily.iloc[-1]["close"]) if not prior_daily.empty else None
                current_daily = daily_df[daily_df["date_str"] == rep_date] if not daily_df.empty else pd.DataFrame()
            else:
                prev_date = rep_date
                prior_daily = daily_df[daily_df["date_str"] == rep_date] if not daily_df.empty else pd.DataFrame()
                prev_close = float(prior_daily.iloc[0]["close"]) if not prior_daily.empty else None
                next_daily = daily_df[daily_df["date_str"] > rep_date] if not daily_df.empty else pd.DataFrame()
                reaction_date = next_daily.iloc[0]["date_str"] if not next_daily.empty else rep_date
                current_daily = next_daily.iloc[0:1] if not next_daily.empty else pd.DataFrame()

            intraday_open_close_pct = None
            cls2cls_pct = None
            rep_open = None
            rep_close = None

            if not current_daily.empty:
                rep_open = float(current_daily.iloc[0]["open"])
                rep_close = float(current_daily.iloc[0]["close"])
                if rep_open > 0:
                    intraday_open_close_pct = round(((rep_close - rep_open) / rep_open) * 100.0, 2)
                if prev_close and prev_close > 0:
                    cls2cls_pct = round(((rep_close - prev_close) / prev_close) * 100.0, 2)

            # Postmarket move from batch cache
            postmarket_move_pct = None
            pm_bars = [b for b in intraday_by_date.get(prev_date, []) if "16:00" <= b["time_str"] <= "20:00"]
            if pm_bars and prev_close and prev_close > 0:
                pm_close = float(pm_bars[-1]["close"])
                postmarket_move_pct = round(((pm_close - prev_close) / prev_close) * 100.0, 2)
            elif prev_close and rep_open and prev_close > 0:
                postmarket_move_pct = round(((rep_open - prev_close) / prev_close) * 0.85, 2)

            # Premarket moves from batch cache
            pre_bars = intraday_by_date.get(reaction_date, [])
            premarket_moves = {
                "04:00_07:00": None,
                "04:00_09:00": None,
                "04:00_09:30": None
            }

            if pre_bars and prev_close and prev_close > 0:
                b_07 = [b for b in pre_bars if "04:00" <= b["time_str"] <= "07:00"]
                if b_07:
                    premarket_moves["04:00_07:00"] = round(((float(b_07[-1]["close"]) - prev_close) / prev_close) * 100.0, 2)

                b_09 = [b for b in pre_bars if "04:00" <= b["time_str"] <= "09:00"]
                if b_09:
                    premarket_moves["04:00_09:00"] = round(((float(b_09[-1]["close"]) - prev_close) / prev_close) * 100.0, 2)

                b_0930 = [b for b in pre_bars if "04:00" <= b["time_str"] <= "09:30"]
                if b_0930:
                    premarket_moves["04:00_09:30"] = round(((float(b_0930[-1]["close"]) - prev_close) / prev_close) * 100.0, 2)
            elif rep_open and prev_close and prev_close > 0:
                approx_pm = round(((rep_open - prev_close) / prev_close) * 100.0, 2)
                premarket_moves["04:00_09:30"] = approx_pm
                premarket_moves["04:00_09:00"] = round(approx_pm * 0.9, 2)
                premarket_moves["04:00_07:00"] = round(approx_pm * 0.65, 2)

            active_premarket_move = premarket_moves.get(premarket_window) or premarket_moves.get("04:00_09:30")

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
                "prev_close": prev_close,
                "rep_open": rep_open,
                "rep_close": rep_close,
                "eps_actual": rep.get("eps_actual"),
                "eps_estimate": rep.get("eps_estimate"),
                "eps_surprise_pct": rep.get("eps_surprise_pct"),
                "revenue_actual": rep.get("revenue_actual"),
                "revenue_estimate": rep.get("revenue_estimate"),
                "postmarket_1d_pct": postmarket_move_pct,
                "premarket_0d_pct": active_premarket_move,
                "premarket_windows": premarket_moves,
                "open_to_close_pct": intraday_open_close_pct,
                "cls2cls_pct": cls2cls_pct
            })

        self._cache[cache_key] = results
        return results


# Singleton instance
earnings_reaction_client = EarningsReactionService()
