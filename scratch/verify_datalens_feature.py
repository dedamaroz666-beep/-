import urllib.request
import json

base_url = "http://127.0.0.1:8080"

print("--- 1. Testing Root HTML ---")
with urllib.request.urlopen(f"{base_url}/") as response:
    html = response.read().decode("utf-8")
    assert "data-target-view=\"viewDataLens\"" in html, "viewDataLens tab button not in HTML"
    assert "id=\"viewDataLens\"" in html, "viewDataLens main container not in HTML"
    assert "id=\"datalensFilterModalBackdrop\"" in html, "Filter modal not in HTML"
    assert "id=\"datalensTable\"" in html, "DataLens table not in HTML"
    assert "[ DATA ]" in html, "Brand [ DATA ] not in HTML"
    print("HTML verification: PASSED (all elements present)")

print("--- 2. Testing Static Files ---")
with urllib.request.urlopen(f"{base_url}/static/app.js") as response:
    js = response.read().decode("utf-8")
    assert "dataLensState" in js, "dataLensState not in app.js"
    assert "tickers: []" in js, "tickers: [] not in app.js"
    assert "switchToStockAnalytics(ticker, targetDate" in js or "switchToStockAnalytics(ticker," in js, "switchToStockAnalytics not in app.js"
    assert "renderDataLensTable" in js, "renderDataLensTable not in app.js"
    print("app.js verification: PASSED")

with urllib.request.urlopen(f"{base_url}/static/style.css") as response:
    css = response.read().decode("utf-8")
    assert ".datalens-wrapper" in css, "datalens CSS not in style.css"
    assert ".datalens-filter-modal" in css, "filter modal CSS not in style.css"
    assert ".datalens-cell-pct" in css, "cell pct CSS not in style.css"
    print("style.css verification: PASSED")

print("--- 3. Testing API /api/datalens/data ---")
with urllib.request.urlopen(f"{base_url}/api/datalens/data?tickers=SPY,QQQ,MU&period=1y") as response:
    data = json.loads(response.read().decode("utf-8"))
    assert data.get("status") == "ok", "API status not ok"
    assert "SPY" in data.get("tickers", []), "SPY not in tickers"
    assert "QQQ" in data.get("tickers", []), "QQQ not in tickers"
    assert "MU" in data.get("tickers", []), "MU not in tickers"
    assert len(data.get("dates", [])) > 0, "Dates list is empty"
    
    first_date = data["dates"][0]
    first_day = data["data"][first_date]
    print(f"Latest date: {first_date}, tickers: {list(first_day.keys())}")
    for sym in ["SPY", "QQQ", "MU"]:
        assert sym in first_day, f"{sym} missing on {first_date}"
        print(f"  {sym}: cls2cls={first_day[sym]['cls2cls']}%, intra={first_day[sym]['intra']}%, gap={first_day[sym]['gap']}%")
    print("API verification: PASSED")

print("ALL TESTS PASSED SUCCESSFULLY!")
