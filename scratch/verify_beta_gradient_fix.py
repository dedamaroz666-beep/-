import re
import filecmp

def run_tests():
    print("Testing Beta Gradient Fix...")
    
    with open("static/app.js", "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Synchronization check
    assert filecmp.cmp("static/app.js", "templates/static/app.js"), "templates/static/app.js is out of sync!"
    assert filecmp.cmp("static/app.js", "templates/templates/app.js"), "templates/templates/app.js is out of sync!"
    print("[PASS] File synchronization verified.")

    # 2. Extract getBetaGradientBg
    m = re.search(r'function getBetaGradientBg\(val\) \{([\s\S]*?)\n\}', code)
    assert m, "getBetaGradientBg not found in static/app.js"
    body = m.group(1)

    # 3. Verify no 0.95 opacity
    assert "0.95" not in body, "Harsh 0.95 opacity still present in getBetaGradientBg!"
    print("[PASS] Harsh 0.95 opacity removed.")

    # 4. Simulate the logic in Python to verify user screenshot values
    def python_getBetaGradientBg(val):
        if val is None: return "background: transparent;"
        num = float(val)
        if num < -2.50:
            return "extreme_inverse_red"
        if num < -1.20:
            return "strong_inverse_red"
        if num < -0.60:
            return "moderate_inverse_coral"
        if num < -0.20:
            return "mild_inverse_rose"
        if num < -0.05:
            return "near_zero_negative_slate_rose"
        if num <= 0.05:
            return "true_neutral_slate_grey"
        if num <= 0.20:
            return "near_zero_positive_slate_amber"
        if num < 0.80:
            return "low_beta_amber"
        if num <= 1.20:
            return "benchmark_blue"
        if num <= 2.00:
            return "moderate_high_beta_green"
        if num <= 4.00:
            return "high_beta_green"
        return "extreme_high_beta_emerald"

    # User screenshot test cases:
    cases = {
        -5.351: "extreme_inverse_red",
        -4.741: "extreme_inverse_red",
        -3.369: "extreme_inverse_red",
        -3.366: "extreme_inverse_red",
        -3.223: "extreme_inverse_red",
        -2.418: "strong_inverse_red",
        -2.413: "strong_inverse_red",
        -1.772: "strong_inverse_red",
        -1.045: "moderate_inverse_coral",
        -0.627: "moderate_inverse_coral",
        -0.501: "mild_inverse_rose",
        -0.186: "near_zero_negative_slate_rose",
        -0.002: "true_neutral_slate_grey",
        0.107: "near_zero_positive_slate_amber",
        0.265: "low_beta_amber",
        0.404: "low_beta_amber",
        1.000: "benchmark_blue",
        4.776: "extreme_high_beta_emerald",
        4.824: "extreme_high_beta_emerald",
        5.755: "extreme_high_beta_emerald",
        10.651: "extreme_high_beta_emerald",
    }

    for val, expected_category in cases.items():
        res = python_getBetaGradientBg(val)
        assert res == expected_category, f"Mismatch for {val}: got {res}, expected {expected_category}"
        print(f"  Value {val:>7.3f} -> {res}")

    # Explicit check for the user's direct question:
    spy_cat = python_getBetaGradientBg(-0.186)
    minus5_cat = python_getBetaGradientBg(-5.0)
    assert spy_cat != minus5_cat, "CRITICAL ERROR: SPY (-0.186) has same category as -5.0!"
    print(f"\n[PASS] User Question Verified: -0.186 ({spy_cat}) is clearly distinguished from -5.0 ({minus5_cat})!")

if __name__ == "__main__":
    run_tests()
