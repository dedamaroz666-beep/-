import filecmp
import re

def verify_all():
    print("--- 1. Checking HTML files synchronization ---")
    assert filecmp.cmp("static/index.html", "templates/index.html"), "static and templates index.html must be identical!"
    print("HTML files are identical: OK")

    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Verify that chart header curtains were removed
    assert '<div class="chart-header">' not in html, "chart-header div still found in HTML!"
    assert 'Дневной (D) — События [E] & [D]' not in html, "Old daily heading still found in HTML!"
    assert 'Интрадей — <span id="activeIntradayDate"' not in html, "Old intraday heading still found in HTML!"
    print("Curtain headers removed: OK")

    # Verify that VOL buttons exist inside floating toolbars
    assert 'id="toggleDailyVolBtn"' in html, "toggleDailyVolBtn missing in HTML"
    assert 'id="toggleIntradayVolBtn"' in html, "toggleIntradayVolBtn missing in HTML"
    assert 'class="chart-tool-btn chart-float-btn active"' in html, "chart-float-btn class missing in HTML"
    print("Floating VOL buttons present: OK")

    # Verify that activeIntradayDate is preserved (hidden) for JS compatibility
    assert 'id="activeIntradayDate"' in html, "activeIntradayDate span missing in HTML"
    print("activeIntradayDate preserved: OK")

    # Verify TradingView ruler elements
    assert 'id="dailyRulerSvg"' in html, "dailyRulerSvg missing in HTML"
    assert 'id="dailyRulerBadge"' in html, "dailyRulerBadge missing in HTML"
    assert 'id="intradayRulerSvg"' in html, "intradayRulerSvg missing in HTML"
    assert 'id="intradayRulerBadge"' in html, "intradayRulerBadge missing in HTML"
    print("Ruler SVG and badge elements in HTML: OK")

    print("\n--- 2. Checking CSS ---")
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert '.chart-floating-toolbar' in css, "chart-floating-toolbar missing in CSS"
    assert '.chart-float-btn' in css, "chart-float-btn missing in CSS"
    assert '.chart-ruler-svg' in css, "chart-ruler-svg missing in CSS"
    assert '.chart-ruler-rect' in css, "chart-ruler-rect missing in CSS"
    assert '.chart-ruler-line' in css, "chart-ruler-line missing in CSS"
    assert '.chart-ruler-dot' in css, "chart-ruler-dot missing in CSS"
    assert '.chart-ruler-badge' in css, "chart-ruler-badge missing in CSS"
    assert '.ruler-pct' in css, "ruler-pct missing in CSS"
    assert '.ruler-diff' in css, "ruler-diff missing in CSS"
    assert '.chart-container.ruler-measuring' in css, "ruler-measuring cursor missing in CSS"
    print("All CSS styles present: OK")

    print("\n--- 3. Checking JavaScript ---")
    with open("static/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert 'let dailyRulerInstance = null;' in js, "dailyRulerInstance variable missing in app.js"
    assert 'let intradayRulerInstance = null;' in js, "intradayRulerInstance variable missing in app.js"
    assert 'let suppressChartClickAction = false;' in js, "suppressChartClickAction variable missing in app.js"
    assert 'setupChartRuler' in js, "setupChartRuler function missing in app.js"
    assert 'dailyRulerInstance = setupChartRuler(' in js, "dailyRulerInstance initialization missing in app.js"
    assert 'intradayRulerInstance = setupChartRuler(' in js, "intradayRulerInstance initialization missing in app.js"
    assert 'e.ctrlKey || e.shiftKey' in js, "Ctrl/Shift key combination missing in setupChartRuler"
    assert 'ruler-close-btn' in js, "close button handler missing in setupChartRuler"
    assert 'subscribeVisibleLogicalRangeChange' in js, "zoom/pan sync missing in setupChartRuler"
    assert 'dailyHudCard' in js, "dailyHudCard check in app.js"
    print("All JS logic present: OK")

    print("\n=== ALL CHECKS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    verify_all()
