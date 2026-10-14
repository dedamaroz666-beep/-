import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filecmp
import re
from services.quant_service import quant_client

def test_all():
    print("==================================================")
    print("STARTING CORRELATION MATRIX ENHANCEMENTS VERIFICATION")
    print("==================================================")

    # 1. Test HTML
    print("\n--- 1. Testing HTML files ---")
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Check that subtitle is removed
    assert "Связность актива с бенчмарками (SPY, QQQ, SOXX, IGV, DRAM) и отраслевыми аналогами" not in html, "Subtitle still present in static/index.html!"
    print("Subtitle removed from static/index.html: OK")

    # Check multi-ticker input and buttons
    assert 'id="addPeerInput"' in html, "addPeerInput missing"
    assert '+ Добавить тикер(ы)...' in html, "addPeerInput placeholder not updated"
    assert 'id="addPeerBtn"' in html, "addPeerBtn missing"
    assert 'id="corrBulkAddBtn"' in html, "corrBulkAddBtn missing"
    assert 'id="corrRemovePartialBtn"' in html, "corrRemovePartialBtn missing"
    assert 'id="corrBulkModal"' in html, "corrBulkModal missing"
    assert 'id="corrBulkTickerText"' in html, "corrBulkTickerText missing"
    assert 'id="submitCorrBulkTickers"' in html, "submitCorrBulkTickers missing"
    print("All toolbar controls and modal in static/index.html: OK")

    # Check templates/index.html
    with open("templates/index.html", "r", encoding="utf-8") as f:
        tmpl_html = f.read()
    assert "Связность актива с бенчмарками (SPY, QQQ, SOXX, IGV, DRAM) и отраслевыми аналогами" not in tmpl_html
    assert 'id="corrBulkModal"' in tmpl_html
    print("templates/index.html synchronized: OK")

    # 2. Test CSS
    print("\n--- 2. Testing CSS ---")
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".row-partial-period" in css, "row-partial-period missing in style.css"
    assert ".badge-partial-period" in css, "badge-partial-period missing in style.css"
    assert ".corr-remove-partial-btn" in css, "corr-remove-partial-btn missing in style.css"
    assert "#corrTable th[data-sort]" in css, "corrTable th[data-sort] missing in style.css"
    print("CSS classes present in static/style.css: OK")

    # 3. Test JS
    print("\n--- 3. Testing static/app.js ---")
    with open("static/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "function parseTickersInput(" in js, "parseTickersInput missing in app.js"
    assert "function addPeerTickers(" in js, "addPeerTickers missing in app.js"
    assert "function removePartialCorrTickers(" in js, "removePartialCorrTickers missing in app.js"
    assert "row-partial-period" in js, "row-partial-period not handled in renderCorrTableRows"
    assert "badge-partial-period" in js, "badge-partial-period not handled in renderCorrTableRows"
    assert "corrRemovePartialBtn" in js, "corrRemovePartialBtn not handled in app.js"
    assert "corrBulkAddBtn" in js, "corrBulkAddBtn not handled in app.js"
    print("JavaScript functions and event handlers present in static/app.js: OK")

    # 4. Test Backend Quant Service
    print("\n--- 4. Testing Quant Service Backend ---")
    print("Calculating correlations for AAPL (period=1y)...")
    res_1y = quant_client.calculate_ticker_correlations(
        ticker="AAPL",
        period="1y",
        benchmarks=["SPY", "QQQ"],
        peers=["MSFT", "GOOGL"]
    )
    assert "ticker_correlations" in res_1y, "ticker_correlations missing from response"
    items = res_1y["ticker_correlations"]
    print(f"Received {len(items)} correlation items:")
    for it in items:
        print(f" - {it['symbol']} ({it['type']}): obs={it.get('observations')}, is_partial={it.get('is_partial')}, reason={it.get('partial_reason')}")
        assert "is_partial" in it, f"is_partial flag missing for {it['symbol']}"
        assert "partial_reason" in it, f"partial_reason missing for {it['symbol']}"
        assert "first_trade_date" in it, f"first_trade_date missing for {it['symbol']}"

    print("\nCalculating correlations for AAPL (period=earnings_8q)...")
    res_8q = quant_client.calculate_ticker_correlations(
        ticker="AAPL",
        period="earnings_8q",
        benchmarks=["SPY", "QQQ"],
        peers=["MSFT"]
    )
    for it in res_8q["ticker_correlations"]:
        print(f" - {it['symbol']} ({it['type']}): obs={it.get('observations')}, is_partial={it.get('is_partial')}, reason={it.get('partial_reason')}")
        assert "is_partial" in it

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
