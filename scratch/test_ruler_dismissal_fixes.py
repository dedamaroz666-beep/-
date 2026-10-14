import urllib.request
from bs4 import BeautifulSoup

def test_ruler_and_intraday_fixes():
    print("=== Testing Ruler Dismissal and Intraday Upper-Left Cleanup ===")

    # 1. Check live server response
    url = "http://127.0.0.1:8000/"
    req = urllib.request.urlopen(url, timeout=5)
    assert req.status == 200, f"Expected 200, got {req.status}"
    live_html = req.read().decode("utf-8")
    
    # 2. Check HTML structure
    soup = BeautifulSoup(live_html, "html.parser")
    
    daily_badge = soup.find(id="dailyRulerBadge")
    assert daily_badge is not None, "dailyRulerBadge not found in live HTML"
    assert "hidden" in daily_badge.get("class", []), "dailyRulerBadge must have 'hidden' class"
    assert "display: none" in daily_badge.get("style", ""), "dailyRulerBadge must have inline display: none"
    
    daily_svg = soup.find(id="dailyRulerSvg")
    assert daily_svg is not None, "dailyRulerSvg not found in live HTML"
    assert "hidden" in daily_svg.get("class", []), "dailyRulerSvg must have 'hidden' class"
    assert "display: none" in daily_svg.get("style", ""), "dailyRulerSvg must have inline display: none"
    
    intraday_badge = soup.find(id="intradayRulerBadge")
    assert intraday_badge is not None, "intradayRulerBadge not found in live HTML"
    assert "hidden" in intraday_badge.get("class", []), "intradayRulerBadge must have 'hidden' class"
    assert "display: none" in intraday_badge.get("style", ""), "intradayRulerBadge must have inline display: none"
    
    intraday_svg = soup.find(id="intradayRulerSvg")
    assert intraday_svg is not None, "intradayRulerSvg not found in live HTML"
    assert "hidden" in intraday_svg.get("class", []), "intradayRulerSvg must have 'hidden' class"
    assert "display: none" in intraday_svg.get("style", ""), "intradayRulerSvg must have inline display: none"
    
    active_date = soup.find(id="activeIntradayDate")
    assert active_date is not None, "activeIntradayDate not found in live HTML"
    assert "display: none" in active_date.get("style", ""), "activeIntradayDate must have inline display: none"
    
    daily_hud = soup.find(id="dailyHudCard")
    assert daily_hud is not None, "dailyHudCard should be present in daily chart"
    
    print("Live HTML checks: OK")
    
    # 3. Check CSS rules in static/style.css
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()
        
    assert ".hidden" in css, ".hidden class missing in style.css"
    assert "display: none !important;" in css, "display: none !important; missing in style.css"
    assert "#dailyRulerBadge.hidden" in css, "#dailyRulerBadge.hidden missing in style.css"
    assert "#intradayRulerBadge.hidden" in css, "#intradayRulerBadge.hidden missing in style.css"
    assert "#dailyRulerSvg.hidden" in css, "#dailyRulerSvg.hidden missing in style.css"
    assert "#intradayRulerSvg.hidden" in css, "#intradayRulerSvg.hidden missing in style.css"
    assert "#activeIntradayDate" in css, "#activeIntradayDate rule missing in style.css"
    
    print("CSS rules checks: OK")
    
    # 4. Check JS implementation in static/app.js
    with open("static/app.js", "r", encoding="utf-8") as f:
        js = f.read()
        
    assert 'svg.style.display = "none";' in js, "svg.style.display = 'none'; missing in clear()"
    assert 'badge.style.display = "none";' in js, "badge.style.display = 'none'; missing in clear()"
    assert 'lineEl.removeAttribute("x1");' in js, "line cleanup missing in clear()"
    assert 'dotStartEl.removeAttribute("cx");' in js, "dot cleanup missing in clear()"
    assert 'clear();' in js, "clear() call on init missing"
    assert 'ruler-close-btn' in js, "ruler-close-btn handler missing"
    assert 'e.stopImmediatePropagation();' in js, "stopImmediatePropagation missing in close button handlers"
    assert 'svg.style.display = "block";' in js, "svg display block missing in draw()"
    assert 'badge.style.display = "block";' in js, "badge display block missing in draw()"
    
    print("JavaScript implementation checks: OK")
    print("\n=== ALL COMPREHENSIVE TESTS PASSED! ===")

if __name__ == "__main__":
    test_ruler_and_intraday_fixes()
