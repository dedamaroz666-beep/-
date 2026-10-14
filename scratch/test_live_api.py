import urllib.request
import json

def test_live():
    base = 'http://127.0.0.1:8000'

    # 1. Test HTML
    html = urllib.request.urlopen(f'{base}/').read().decode('utf-8')
    assert 'Связность актива с бенчмарками (SPY, QQQ, SOXX, IGV, DRAM) и отраслевыми аналогами' not in html, 'Subtitle still present!'
    assert 'id="addPeerInput"' in html
    assert '+ Добавить тикер(ы)...' in html
    assert 'id="corrBulkModal"' in html
    assert 'id="corrBulkAddBtn"' in html
    assert 'id="corrRemovePartialBtn"' in html
    print("1. HTML endpoints verified successfully: Subtitle removed, multi-ticker input and modal present.")

    # 2. Test API correlations with multiple peers
    url = f'{base}/api/ticker/AAPL/correlations?period=1y&benchmarks=SPY,QQQ&peers=NVDA,AMD,INTC'
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    assert 'ticker_correlations' in data
    symbols = [i['symbol'] for i in data['ticker_correlations']]
    print("2. Correlation API returned symbols:", symbols)
    assert 'NVDA' in symbols
    assert 'AMD' in symbols
    assert 'INTC' in symbols
    for it in data['ticker_correlations']:
        assert 'is_partial' in it
        assert 'partial_reason' in it
        print(f"   Ticker {it['symbol']}: obs={it['observations']}, is_partial={it['is_partial']}, reason={it['partial_reason']}")
    print("All live API assertions passed!")

if __name__ == '__main__':
    test_live()
