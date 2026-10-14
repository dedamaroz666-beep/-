import sys
sys.path.insert(0, r'c:\Users\K009\PycharmProjects\Analysis')
from database import get_ticker_reports, get_stock_data
from services.earnings_extra_service import get_ticker_earnings_extra_map, find_matching_earnings_extra
from services.fmp_service import fmp_client
import datetime
import bisect

ticker = 'TSM'
df = get_stock_data(ticker)
candle_dates = set(df['date'].dt.strftime('%Y-%m-%d').tolist())
sorted_candle_dates = sorted(list(candle_dates))

def find_nearest_candle_date(target_date: str):
    if target_date in candle_dates:
        return target_date
    if not sorted_candle_dates or target_date < sorted_candle_dates[0] or target_date > sorted_candle_dates[-1]:
        return None
    idx = bisect.bisect_left(sorted_candle_dates, target_date)
    if idx < len(sorted_candle_dates):
        cand = sorted_candle_dates[idx]
        try:
            d_target = datetime.date.fromisoformat(target_date)
            d_cand = datetime.date.fromisoformat(cand)
            if abs((d_cand - d_target).days) <= 4:
                return cand
        except Exception:
            pass
    return None

def determine_session(time_val):
    if not time_val:
        return 'BMO'
    t_str = str(time_val).lower().strip()
    if 'amc' in t_str or 'after' in t_str:
        return 'AMC'
    if 'bmo' in t_str or 'before' in t_str:
        return 'BMO'
    try:
        parts = t_str.split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if h < 9 or (h == 9 and m <= 30):
            return 'BMO'
        if h >= 16:
            return 'AMC'
    except Exception:
        pass
    return 'BMO'

db_reports_df = get_ticker_reports(ticker)
extra_map = get_ticker_earnings_extra_map(ticker)

processed_dates = []
markers = []

if not db_reports_df.empty:
    for _, r in db_reports_df.iterrows():
        raw_date = str(r['date'])
        c_date = find_nearest_candle_date(raw_date)
        if not c_date and r.get('move_date'):
            c_date = find_nearest_candle_date(str(r['move_date']))
        if not c_date:
            continue
        
        d_c = datetime.date.fromisoformat(c_date)
        if any(abs((d_c - prev_d).days) < 45 for prev_d in processed_dates):
            continue
            
        processed_dates.append(d_c)
        extra_info = find_matching_earnings_extra(extra_map, raw_date)
        session = determine_session(r.get('time'))
        quarter = f"{r.get('fiscal_period', '')} {r.get('fiscal_year', '')}".strip()
        
        markers.append({
            'date': c_date,
            'session': session,
            'quarter': quarter,
            'eps_actual': extra_info.get('eps_actual') if extra_info else None,
            'rev_actual': extra_info.get('revenue_actual') if extra_info else None
        })

for m in markers[:10]:
    print(m)
