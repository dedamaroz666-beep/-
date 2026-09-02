/**
 * Stock Analytics & Correlation Platform - Unified Multi-Theme Frontend Engine
 * Tab 1: Correlation & Beta Calculator (Empty initial state by default)
 * Tab 2: FinWhale Dual TradingView Charts & Ticker Analytics
 * Themes: "sand" (Бежевый / FinWhale), "blue" (Синий), "graphite" (Графит)
 */

// ============================================================
// GLOBAL APPLICATION STATE
// ============================================================

// Tab 1 (Calculator) State - Clean empty initial state by default
let groupsState = {};
let calculationResults = null;
let activeBenchmarkView = "SPY";
let availableDbTickers = [];

// Tracker State - Clean empty initial state by default
let trackerItems = [];
let trackerCurrentData = [];
let trackerFilteredData = [];
let trackerSortCol = "correlation";
let trackerSortAsc = false;
let trackerPage = 1;
let trackerPageSize = 50;

// Screener State
let screenerFilteredData = [];
let screenerSortCol = "correlation";
let screenerSortAsc = false;
let screenerPage = 1;
let screenerPageSize = 50;

// Tab 2 (FinWhale Stock Analytics) State
let currentStockTicker = "AAPL";
let activePremarketWindow = "04:00_09:30";
let activeCorrPeriod = "1y";
let activeTfMultiplier = 5;
let currentMarkerDetails = {};
let currentDailyCandlesMap = {};
let currentDailyCandles = [];

// Lightweight Charts Instances
let dailyChart = null;
let dailySeries = null;
let dailyVolumeSeries = null;

let intradayChart = null;
let intradaySeries = null;
let intradayVolumeSeries = null;
let intradayBgSeries = null;

// Theme State
let currentTheme = localStorage.getItem("stock_analytics_theme") || "sand";


// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initGlobalNavigation();
    initCalculatorGroups();
    initCalculatorEvents();
    initMatrixFilterEvents();
    initTrackerEvents();
    initCharts();
    initStockAnalyticsEvents();
    fetchSystemStatus();
    loadStockTickerData(currentStockTicker);
});

function fetchSystemStatus() {
    fetch("/api/tickers")
        .then(res => res.json())
        .then(data => {
            availableDbTickers = data.tickers || [];
        })
        .catch(() => {});
}


// ============================================================
// THEME SWITCHER LOGIC
// ============================================================
const THEME_CONFIGS = {
    sand: {
        chartBg: "#f4efe6",
        grid: "rgba(215, 206, 193, 0.65)",
        text: "#656157",
        border: "#ded7cb",
        crosshair: "#8d867a",
        upColor: "#257a58",
        downColor: "#963838",
        volUp: "rgba(99, 183, 142, 0.72)",
        volDown: "rgba(226, 130, 130, 0.72)",
        preBg: "rgba(0, 0, 0, 0.035)"
    },
    blue: {
        chartBg: "#0a0f1d",
        grid: "rgba(30, 45, 82, 0.5)",
        text: "#94a3b8",
        border: "#1e2d52",
        crosshair: "#38bdf8",
        upColor: "#10b981",
        downColor: "#f43f5e",
        volUp: "rgba(16, 185, 129, 0.55)",
        volDown: "rgba(244, 63, 94, 0.55)",
        preBg: "rgba(255, 255, 255, 0.03)"
    },
    graphite: {
        chartBg: "#07080b",
        grid: "rgba(30, 34, 45, 0.6)",
        text: "#8e95a5",
        border: "#1e222d",
        crosshair: "#0075ff",
        upColor: "#22c55e",
        downColor: "#ef4444",
        volUp: "rgba(34, 197, 94, 0.55)",
        volDown: "rgba(239, 68, 68, 0.55)",
        preBg: "rgba(255, 255, 255, 0.03)"
    }
};

function initTheme() {
    applyTheme(currentTheme, false);

    const pills = document.querySelectorAll("#themePillsContainer .theme-pill");
    pills.forEach(pill => {
        pill.addEventListener("click", () => {
            const chosen = pill.dataset.theme;
            applyTheme(chosen, true);
        });
    });
}

function applyTheme(themeName, updateCharts = true) {
    currentTheme = themeName;
    document.documentElement.setAttribute("data-theme", themeName);
    localStorage.setItem("stock_analytics_theme", themeName);

    // Update pill active class
    const pills = document.querySelectorAll("#themePillsContainer .theme-pill");
    pills.forEach(pill => {
        if (pill.dataset.theme === themeName) {
            pill.classList.add("active");
        } else {
            pill.classList.remove("active");
        }
    });

    if (!updateCharts) return;

    const c = THEME_CONFIGS[themeName] || THEME_CONFIGS.sand;
    const chartOpts = {
        layout: { background: { color: c.chartBg }, textColor: c.text },
        grid: {
            vertLines: { color: c.grid, style: LightweightCharts.LineStyle.Solid },
            horzLines: { color: c.grid, style: LightweightCharts.LineStyle.Solid }
        },
        crosshair: {
            vertLine: { color: c.crosshair, labelBackgroundColor: c.crosshair },
            horzLine: { color: c.crosshair, labelBackgroundColor: c.crosshair }
        },
        rightPriceScale: { borderColor: c.border, textColor: c.text },
        timeScale: { borderColor: c.border, textColor: c.text }
    };

    const seriesOpts = {
        upColor: c.upColor,
        downColor: c.downColor,
        borderVisible: true,
        borderUpColor: c.upColor,
        borderDownColor: c.downColor,
        wickUpColor: c.upColor,
        wickDownColor: c.downColor
    };

    if (dailyChart) {
        dailyChart.applyOptions(chartOpts);
        if (dailySeries) dailySeries.applyOptions(seriesOpts);
    }
    if (intradayChart) {
        intradayChart.applyOptions(chartOpts);
        if (intradaySeries) intradaySeries.applyOptions(seriesOpts);
    }

    // Refresh intraday chart so background bars & candles sync to new theme colors
    const activeDate = document.getElementById("activeIntradayDate")?.textContent?.trim();
    if (currentStockTicker && activeDate) {
        loadStockIntradayChart(currentStockTicker, activeDate);
    }
}


// ============================================================
// GLOBAL TAB NAVIGATION (CALCULATOR VS STOCK ANALYTICS)
// ============================================================
function initGlobalNavigation() {
    const tabs = document.querySelectorAll(".global-tab-btn");
    tabs.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.dataset.targetView;
            tabs.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".tab-view-container").forEach(view => {
                view.classList.remove("active");
            });

            const targetView = document.getElementById(targetId);
            if (targetView) {
                targetView.classList.add("active");
            }

            if (targetId === "viewStockAnalytics") {
                setTimeout(() => {
                    resizeCharts();
                }, 50);
            }
        });
    });
}

function switchToStockAnalytics(ticker) {
    if (ticker) {
        currentStockTicker = ticker.trim().toUpperCase();
    }

    const stockTabBtn = document.querySelector('.global-tab-btn[data-target-view="viewStockAnalytics"]');
    if (stockTabBtn) {
        stockTabBtn.click();
    }

    if (ticker) {
        loadStockTickerData(currentStockTicker);
    }
}

function resizeCharts() {
    const dailyCont = document.getElementById("dailyChartContainer");
    const intraCont = document.getElementById("intradayChartContainer");

    if (dailyChart && dailyCont) {
        dailyChart.applyOptions({ width: dailyCont.clientWidth, height: dailyCont.clientHeight });
        dailyChart.timeScale().fitContent();
    }
    if (intradayChart && intraCont) {
        intradayChart.applyOptions({ width: intraCont.clientWidth, height: intraCont.clientHeight });
        intradayChart.timeScale().fitContent();
    }
}


// ============================================================
// TAB 1: GROUP BUILDER & MANAGEMENT (EMPTY BY DEFAULT)
// ============================================================
function initCalculatorGroups() {
    renderGroups();

    const addGroupBtn = document.getElementById("addGroupButton");
    if (addGroupBtn) {
        addGroupBtn.addEventListener("click", () => {
            const num = Object.keys(groupsState).length + 1;
            const newName = `Group ${num}`;
            groupsState[newName] = [];
            renderGroups();
        });
    }

    const bulkBtn = document.getElementById("bulkTickersButton");
    if (bulkBtn) {
        bulkBtn.addEventListener("click", openBulkImportModal);
    }
}

function renderGroups() {
    const container = document.getElementById("groups");
    if (!container) return;
    container.innerHTML = "";

    const groupKeys = Object.keys(groupsState);
    if (groupKeys.length === 0) {
        const emptyBox = document.createElement("div");
        emptyBox.className = "empty-groups-box";
        emptyBox.innerHTML = `
            <p>Нет созданных групп тикеров. Нажмите «+ Добавить группу» или «Bulk Import» для добавления тикеров.</p>
            <div style="display: flex; gap: 8px;">
                <button class="primary-small-button" id="emptyCreateGroupBtn" type="button">+ Добавить группу</button>
                <button class="secondary-button" id="emptyBulkImportBtn" type="button">Bulk Import (300+)</button>
            </div>
        `;
        emptyBox.querySelector("#emptyCreateGroupBtn").addEventListener("click", () => {
            groupsState["Group 1"] = [];
            renderGroups();
        });
        emptyBox.querySelector("#emptyBulkImportBtn").addEventListener("click", openBulkImportModal);
        container.appendChild(emptyBox);
        return;
    }

    groupKeys.forEach(groupName => {
        const tickers = groupsState[groupName] || [];
        const card = document.createElement("div");
        card.className = "group-card";

        const header = document.createElement("div");
        header.className = "group-card-header";

        const nameInput = document.createElement("input");
        nameInput.className = "group-name-input";
        nameInput.value = groupName;
        nameInput.addEventListener("change", (e) => {
            const newName = e.target.value.trim() || groupName;
            if (newName !== groupName) {
                groupsState[newName] = groupsState[groupName];
                delete groupsState[groupName];
                renderGroups();
            }
        });

        const actions = document.createElement("div");
        actions.className = "group-actions";

        const countBadge = document.createElement("span");
        countBadge.className = "group-badge-count";
        countBadge.textContent = `${tickers.length} тикеров`;

        const removeBtn = document.createElement("button");
        removeBtn.className = "group-btn-icon";
        removeBtn.textContent = "✕";
        removeBtn.title = "Удалить группу";
        removeBtn.addEventListener("click", () => {
            delete groupsState[groupName];
            renderGroups();
        });

        actions.appendChild(countBadge);
        actions.appendChild(removeBtn);
        header.appendChild(nameInput);
        header.appendChild(actions);

        // Chips Container
        const chipsContainer = document.createElement("div");
        chipsContainer.className = "group-chips";

        tickers.forEach((sym, idx) => {
            const chip = document.createElement("span");
            chip.className = "ticker-chip";
            chip.title = "Кликните для перехода к графику";
            chip.innerHTML = `${sym} <span class="ticker-chip-remove" data-idx="${idx}">✕</span>`;

            chip.addEventListener("click", (e) => {
                if (e.target.classList.contains("ticker-chip-remove")) {
                    e.stopPropagation();
                    tickers.splice(idx, 1);
                    renderGroups();
                } else {
                    switchToStockAnalytics(sym);
                }
            });

            chipsContainer.appendChild(chip);
        });

        // Inline Add Ticker Input
        const addInput = document.createElement("input");
        addInput.className = "group-add-ticker-input";
        addInput.placeholder = "+ Тикер (Enter)";
        addInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === ",") {
                e.preventDefault();
                const val = addInput.value.trim().toUpperCase();
                if (val && !tickers.includes(val)) {
                    tickers.push(val);
                    renderGroups();
                }
            }
        });

        chipsContainer.appendChild(addInput);
        card.appendChild(header);
        card.appendChild(chipsContainer);
        container.appendChild(card);
    });
}


// ============================================================
// TAB 1: BULK TICKER IMPORT MODAL
// ============================================================
function openBulkImportModal() {
    const modal = document.getElementById("bulkTickerModal");
    const groupSelect = document.getElementById("bulkTargetGroup");
    const closeBtn = document.getElementById("closeBulkModal");
    const cancelBtn = document.getElementById("cancelBulkModal");
    const addBtn = document.getElementById("addBulkTickers");
    const replaceBtn = document.getElementById("replaceBulkTickers");
    const textarea = document.getElementById("bulkTickerText");
    const countSpan = document.getElementById("bulkTotalCount");

    groupSelect.innerHTML = "";
    const groupKeys = Object.keys(groupsState);
    if (groupKeys.length === 0) {
        groupsState["Group 1"] = [];
        groupKeys.push("Group 1");
    }

    groupKeys.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g;
        opt.textContent = g;
        groupSelect.appendChild(opt);
    });

    const updateCount = () => {
        const text = textarea.value;
        const matches = text.toUpperCase().match(/[A-Z0-9.\-]+/g) || [];
        const unique = [...new Set(matches)];
        countSpan.textContent = `${unique.length} тикеров`;
    };

    textarea.addEventListener("input", updateCount);
    updateCount();

    modal.classList.add("active");

    const closeModal = () => modal.classList.remove("active");
    closeBtn.onclick = closeModal;
    cancelBtn.onclick = closeModal;

    const parseTickers = () => {
        const text = textarea.value;
        const matches = text.toUpperCase().match(/[A-Z0-9.\-]+/g) || [];
        return [...new Set(matches)];
    };

    addBtn.onclick = () => {
        const gName = groupSelect.value || "Group 1";
        const list = parseTickers();
        if (list.length > 0) {
            groupsState[gName] = [...new Set([...(groupsState[gName] || []), ...list])];
            renderGroups();
            closeModal();
        }
    };

    replaceBtn.onclick = () => {
        const gName = groupSelect.value || "Group 1";
        const list = parseTickers();
        if (list.length > 0) {
            groupsState[gName] = list;
            renderGroups();
            closeModal();
        }
    };
}


// ============================================================
// TAB 1: CALCULATE MODELS & MATRIX
// ============================================================
function initCalculatorEvents() {
    const calcBtn = document.getElementById("calculateButton");
    if (calcBtn) {
        calcBtn.addEventListener("click", runGroupCalculation);
    }
}

async function runGroupCalculation() {
    const benchmark = document.getElementById("benchmark").value.trim().toUpperCase() || "SPY";
    const benchmarkMove = parseFloat(document.getElementById("benchmarkMove").value) || 1.0;
    const period = document.getElementById("period").value || "1y";

    const errorEl = document.getElementById("error");
    const warningEl = document.getElementById("warning");
    const loadingEl = document.getElementById("loading");
    const resultsSection = document.getElementById("results");

    errorEl.style.display = "none";
    warningEl.style.display = "none";

    // Validate groups
    const activeGroups = {};
    Object.keys(groupsState).forEach(g => {
        if (groupsState[g] && groupsState[g].length > 0) {
            activeGroups[g] = groupsState[g];
        }
    });

    if (Object.keys(activeGroups).length === 0) {
        errorEl.textContent = "Добавьте хотя бы одну группу с тикерами для расчета моделей.";
        errorEl.style.display = "block";
        return;
    }

    loadingEl.style.display = "flex";

    try {
        const payload = {
            groups: activeGroups,
            benchmark: benchmark,
            benchmark_move: benchmarkMove,
            period: period
        };

        const res = await fetch("/api/calculate-groups", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        loadingEl.style.display = "none";

        if (!res.ok) {
            errorEl.textContent = data.detail || data.error || "Ошибка расчета моделей.";
            errorEl.style.display = "block";
            return;
        }

        calculationResults = data;
        resultsSection.style.display = "block";

        if (data.warning) {
            warningEl.textContent = data.warning;
            warningEl.style.display = "block";
        }

        renderCalculationOverview(data);
        renderScreenerTable(data);
        renderPearsonMatrix(data);
        renderBetaMatrix(data);

        // Also update tracker calculation
        runTrackerCalculation();

        resultsSection.scrollIntoView({ behavior: "smooth" });

    } catch (e) {
        loadingEl.style.display = "none";
        errorEl.textContent = `Ошибка сети или сервера: ${e.message}`;
        errorEl.style.display = "block";
    }
}

function renderCalculationOverview(data) {
    document.getElementById("resultBenchmark").textContent = data.benchmarks ? data.benchmarks.join(", ") : data.benchmark;
    document.getElementById("resultPeriod").textContent = data.period ? data.period.toUpperCase() : "1Y";
    document.getElementById("resultDateRange").textContent = `${data.period_start || "—"} по ${data.period_end || "—"}`;
    document.getElementById("resultTotalAssets").textContent = `${data.total_analyzed || 0} из ${data.total_requested || 0}`;
}

function renderScreenerTable(data) {
    const tbody = document.getElementById("benchmarkResultsTable");
    tbody.innerHTML = "";

    const rows = [];
    const tickers = data.tickers || [];
    const bm = data.primary_benchmark || "SPY";
    const corrMap = data.correlation || {};
    const betaMap = data.beta || {};
    const expRange = data.expected_range || {};

    tickers.forEach(t => {
        const corrVal = corrMap[t] ? corrMap[t][bm] : null;
        const betaVal = betaMap[t] ? betaMap[t][bm] : null;
        const metrics = expRange[t] || {};

        rows.push({
            ticker: t,
            correlation: corrVal,
            beta: betaVal,
            expected_move: metrics.expected_move,
            actual_move: metrics.actual_move,
            difference: metrics.difference,
            normalized: metrics.normalized_difference,
            volatility: metrics.volatility,
            residual_volatility: metrics.residual_volatility,
            observations: metrics.observations
        });
    });

    screenerFilteredData = rows;
    updateScreenerView();
}

function updateScreenerView() {
    const tbody = document.getElementById("benchmarkResultsTable");
    tbody.innerHTML = "";

    const countEl = document.getElementById("benchmarkResultCount");
    const totalEl = document.getElementById("benchmarkResultTotal");
    countEl.textContent = screenerFilteredData.length;
    totalEl.textContent = `/ ${calculationResults ? (calculationResults.tickers || []).length : 0}`;

    if (screenerFilteredData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="loading-cell">Нет тикеров, удовлетворяющих условиям фильтра.</td></tr>`;
        return;
    }

    screenerFilteredData.forEach(r => {
        const tr = document.createElement("tr");

        const corrFmt = formatCorrBadge(r.correlation);
        const betaFmt = r.beta !== null && r.beta !== undefined ? Number(r.beta).toFixed(3) : "—";
        const expMoveFmt = formatPctBadge(r.expected_move);
        const actMoveFmt = formatPctBadge(r.actual_move);
        const diffFmt = formatPctBadge(r.difference);
        const normFmt = r.normalized !== null && r.normalized !== undefined ? `${Number(r.normalized).toFixed(2)}σ` : "—";
        const volFmt = r.volatility ? `${(r.volatility * 100).toFixed(2)}%` : "—";
        const resVolFmt = r.residual_volatility ? `${(r.residual_volatility * 100).toFixed(2)}%` : "—";

        tr.innerHTML = `
            <td><span class="clickable-ticker" data-ticker="${r.ticker}">${r.ticker}</span></td>
            <td>${corrFmt}</td>
            <td><strong>${betaFmt}</strong></td>
            <td>${expMoveFmt}</td>
            <td>${actMoveFmt}</td>
            <td>${diffFmt}</td>
            <td>${normFmt}</td>
            <td>${volFmt}</td>
            <td>${resVolFmt}</td>
            <td>${r.observations || "—"}</td>
            <td>
                <button class="secondary-button" style="padding: 2px 6px; font-size: 11px;" data-view-ticker="${r.ticker}">График</button>
            </td>
        `;

        tr.querySelector(".clickable-ticker").addEventListener("click", () => switchToStockAnalytics(r.ticker));
        tr.querySelector("[data-view-ticker]").addEventListener("click", () => switchToStockAnalytics(r.ticker));

        tbody.appendChild(tr);
    });
}


// ============================================================
// MATRIX FILTERING & RENDERING (PEARSON & BETA)
// ============================================================
function initMatrixFilterEvents() {
    // 1. Pearson Correlation Matrix Filters
    const opSelect = document.getElementById("matrixCorrOperator");
    const threshInput = document.getElementById("matrixCorrThreshold");
    const threshMaxInput = document.getElementById("matrixCorrThresholdMax");
    const maxField = document.getElementById("matrixCorrMaxField");
    const modeSelect = document.getElementById("matrixCorrFilterMode");
    const searchInput = document.getElementById("matrixCorrSearch");
    const applyBtn = document.getElementById("applyMatrixCorrFilterBtn");

    if (opSelect) {
        opSelect.addEventListener("change", () => {
            const val = opSelect.value;
            if (maxField) maxField.style.display = val === "between" ? "block" : "none";
            applyMatrixCorrFilter();
        });
    }

    if (applyBtn) {
        applyBtn.addEventListener("click", applyMatrixCorrFilter);
    }

    if (searchInput) {
        searchInput.addEventListener("input", debounce(applyMatrixCorrFilter, 200));
    }

    if (threshInput) {
        threshInput.addEventListener("change", applyMatrixCorrFilter);
    }
    if (threshMaxInput) {
        threshMaxInput.addEventListener("change", applyMatrixCorrFilter);
    }
    if (modeSelect) {
        modeSelect.addEventListener("change", applyMatrixCorrFilter);
    }

    document.querySelectorAll(".matrix-corr-preset").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".matrix-corr-preset").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const op = btn.dataset.op;
            const val = btn.dataset.val;

            if (opSelect) opSelect.value = op;
            if (maxField) maxField.style.display = op === "between" ? "block" : "none";
            if (threshInput && val !== "all") threshInput.value = val;

            applyMatrixCorrFilter();
        });
    });

    // 2. Beta Matrix Filters
    const betaOpSelect = document.getElementById("matrixBetaOperator");
    const betaThreshInput = document.getElementById("matrixBetaThreshold");
    const betaThreshMaxInput = document.getElementById("matrixBetaThresholdMax");
    const betaMaxField = document.getElementById("matrixBetaMaxField");
    const betaSearchInput = document.getElementById("matrixBetaSearch");
    const betaApplyBtn = document.getElementById("applyMatrixBetaFilterBtn");

    if (betaOpSelect) {
        betaOpSelect.addEventListener("change", () => {
            const val = betaOpSelect.value;
            if (betaMaxField) betaMaxField.style.display = val === "between" ? "block" : "none";
            applyMatrixBetaFilter();
        });
    }

    if (betaApplyBtn) {
        betaApplyBtn.addEventListener("click", applyMatrixBetaFilter);
    }

    if (betaSearchInput) {
        betaSearchInput.addEventListener("input", debounce(applyMatrixBetaFilter, 200));
    }
    if (betaThreshInput) {
        betaThreshInput.addEventListener("change", applyMatrixBetaFilter);
    }
    if (betaThreshMaxInput) {
        betaThreshMaxInput.addEventListener("change", applyMatrixBetaFilter);
    }

    document.querySelectorAll(".matrix-beta-preset").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".matrix-beta-preset").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const op = btn.dataset.op;
            const val = btn.dataset.val;

            if (betaOpSelect) betaOpSelect.value = op;
            if (betaMaxField) betaMaxField.style.display = op === "between" ? "block" : "none";
            if (betaThreshInput && val !== "all") betaThreshInput.value = val;

            applyMatrixBetaFilter();
        });
    });
}

function applyMatrixCorrFilter() {
    if (!calculationResults) return;
    renderPearsonMatrix(calculationResults);
}

function checkCorrCondition(val, op, threshold, thresholdMax) {
    if (val === null || val === undefined || isNaN(val)) return false;
    const num = Number(val);
    if (op === "all") return true;
    if (op === "gte") return num >= threshold;
    if (op === "lte") return num <= threshold;
    if (op === "between") return num >= threshold && num <= thresholdMax;
    if (op === "abs_gte") return Math.abs(num) >= threshold;
    return true;
}

function renderPearsonMatrix(data) {
    const table = document.getElementById("correlationMatrix");
    if (!table) return;
    table.innerHTML = "";

    const allSymbols = data.all_symbols || data.tickers || [];
    const corrMap = data.correlation || {};

    const opSelect = document.getElementById("matrixCorrOperator");
    const threshInput = document.getElementById("matrixCorrThreshold");
    const threshMaxInput = document.getElementById("matrixCorrThresholdMax");
    const modeSelect = document.getElementById("matrixCorrFilterMode");
    const searchInput = document.getElementById("matrixCorrSearch");

    const op = opSelect ? opSelect.value : "gte";
    const threshold = threshInput ? parseFloat(threshInput.value) : 0.5;
    const thresholdMax = threshMaxInput ? parseFloat(threshMaxInput.value) : 1.0;
    const mode = modeSelect ? modeSelect.value : "any_pair";
    const search = searchInput ? searchInput.value.trim().toUpperCase() : "";

    // Filter symbols
    let displaySymbols = allSymbols;
    if (search) {
        displaySymbols = displaySymbols.filter(s => s.toUpperCase().includes(search));
    }

    if (mode === "any_pair" && op !== "all") {
        displaySymbols = displaySymbols.filter(s => {
            return allSymbols.some(other => {
                if (s === other) return false;
                const val = corrMap[s] ? corrMap[s][other] : null;
                return checkCorrCondition(val, op, threshold, thresholdMax);
            });
        });
    }

    const matchCountEl = document.getElementById("matrixCorrMatchCount");
    const matchTotalEl = document.getElementById("matrixCorrMatchTotal");
    const badgeEl = document.getElementById("matrixCorrActiveFilterBadge");

    if (matchCountEl) matchCountEl.textContent = displaySymbols.length;
    if (matchTotalEl) matchTotalEl.textContent = `/ ${allSymbols.length} активов`;
    if (badgeEl) {
        if (op === "all") badgeEl.textContent = "Все";
        else if (op === "between") badgeEl.textContent = `r ∈ [${threshold}, ${thresholdMax}]`;
        else if (op === "abs_gte") badgeEl.textContent = `|r| ≥ ${threshold}`;
        else if (op === "lte") badgeEl.textContent = `r ≤ ${threshold}`;
        else badgeEl.textContent = `r ≥ ${threshold}`;
    }

    if (displaySymbols.length === 0) {
        table.innerHTML = `<tr><td class="loading-cell" style="padding: 24px;">Нет активов, удовлетворяющих условиям фильтра.</td></tr>`;
        return;
    }

    const thead = document.createElement("thead");
    const htr = document.createElement("tr");
    htr.innerHTML = `<th>Тикер</th>` + displaySymbols.map(s => `<th>${s}</th>`).join("");
    thead.appendChild(htr);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    displaySymbols.forEach(rowSym => {
        const tr = document.createElement("tr");
        let rowHtml = `<td><strong><span class="clickable-ticker" data-ticker="${rowSym}">${rowSym}</span></strong></td>`;

        displaySymbols.forEach(colSym => {
            if (rowSym === colSym) {
                rowHtml += `<td class="corr-cell" style="background: rgba(37, 122, 88, 0.2); font-weight: 800;">1.000</td>`;
            } else {
                const val = corrMap[rowSym] ? corrMap[rowSym][colSym] : null;
                if (val !== null && val !== undefined) {
                    const meets = checkCorrCondition(val, op, threshold, thresholdMax);
                    const bg = getCorrBgColor(val);
                    if (mode === "dim_cells" && !meets && op !== "all") {
                        rowHtml += `<td class="corr-cell" style="background: transparent; color: var(--text-muted); opacity: 0.22;">${Number(val).toFixed(3)}</td>`;
                    } else {
                        rowHtml += `<td class="corr-cell" style="background: ${bg};">${Number(val).toFixed(3)}</td>`;
                    }
                } else {
                    rowHtml += `<td class="corr-cell" style="color: var(--text-muted);">—</td>`;
                }
            }
        });

        tr.innerHTML = rowHtml;
        tr.querySelector(".clickable-ticker").addEventListener("click", () => switchToStockAnalytics(rowSym));
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
}

function applyMatrixBetaFilter() {
    if (!calculationResults) return;
    renderBetaMatrix(calculationResults);
}

function checkBetaCondition(val, op, threshold, thresholdMax) {
    if (val === null || val === undefined || isNaN(val)) return false;
    const num = Number(val);
    if (op === "all") return true;
    if (op === "gte") return num >= threshold;
    if (op === "lte") return num <= threshold;
    if (op === "between") return num >= threshold && num <= thresholdMax;
    return true;
}

function renderBetaMatrix(data) {
    const table = document.getElementById("betaMatrix");
    if (!table) return;
    table.innerHTML = "";

    const tickers = data.tickers || [];
    const benchmarks = data.benchmarks || [data.primary_benchmark || "SPY"];
    const betaMap = data.beta || {};

    const opSelect = document.getElementById("matrixBetaOperator");
    const threshInput = document.getElementById("matrixBetaThreshold");
    const threshMaxInput = document.getElementById("matrixBetaThresholdMax");
    const searchInput = document.getElementById("matrixBetaSearch");

    const op = opSelect ? opSelect.value : "gte";
    const threshold = threshInput ? parseFloat(threshInput.value) : 1.0;
    const thresholdMax = threshMaxInput ? parseFloat(threshMaxInput.value) : 2.0;
    const search = searchInput ? searchInput.value.trim().toUpperCase() : "";

    let displayTickers = tickers;
    if (search) {
        displayTickers = displayTickers.filter(t => t.toUpperCase().includes(search));
    }

    if (op !== "all") {
        displayTickers = displayTickers.filter(t => {
            return benchmarks.some(bm => {
                const val = betaMap[t] ? betaMap[t][bm] : null;
                return checkBetaCondition(val, op, threshold, thresholdMax);
            });
        });
    }

    const matchCountEl = document.getElementById("matrixBetaMatchCount");
    const matchTotalEl = document.getElementById("matrixBetaMatchTotal");
    const badgeEl = document.getElementById("matrixBetaActiveFilterBadge");

    if (matchCountEl) matchCountEl.textContent = displayTickers.length;
    if (matchTotalEl) matchTotalEl.textContent = `/ ${tickers.length} активов`;
    if (badgeEl) {
        if (op === "all") badgeEl.textContent = "Все";
        else if (op === "between") badgeEl.textContent = `β ∈ [${threshold}, ${thresholdMax}]`;
        else if (op === "lte") badgeEl.textContent = `β ≤ ${threshold}`;
        else badgeEl.textContent = `β ≥ ${threshold}`;
    }

    if (displayTickers.length === 0) {
        table.innerHTML = `<tr><td class="loading-cell" style="padding: 24px;">Нет активов, удовлетворяющих условиям фильтра Beta.</td></tr>`;
        return;
    }

    const thead = document.createElement("thead");
    const htr = document.createElement("tr");
    htr.innerHTML = `<th>Тикер</th>` + benchmarks.map(bm => `<th>Beta (${bm})</th>`).join("");
    thead.appendChild(htr);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    displayTickers.forEach(t => {
        const tr = document.createElement("tr");
        let rowHtml = `<td><strong><span class="clickable-ticker" data-ticker="${t}">${t}</span></strong></td>`;

        benchmarks.forEach(bm => {
            const val = betaMap[t] ? betaMap[t][bm] : null;
            if (val !== null && val !== undefined) {
                const bg = getBetaBgColor(val);
                rowHtml += `<td class="corr-cell" style="background: ${bg};">${Number(val).toFixed(3)}</td>`;
            } else {
                rowHtml += `<td class="corr-cell" style="color: var(--text-muted);">—</td>`;
            }
        });

        tr.innerHTML = rowHtml;
        tr.querySelector(".clickable-ticker").addEventListener("click", () => switchToStockAnalytics(t));
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
}


// ============================================================
// TAB 1: CUSTOM MOVE TRACKER (EMPTY BY DEFAULT)
// ============================================================
function initTrackerEvents() {
    const addBtn = document.getElementById("trackerAddAssetBtn");
    const clearBtn = document.getElementById("trackerClearBtn");
    const bulkBtn = document.getElementById("trackerBulkModalBtn");
    const copyBtn = document.getElementById("trackerCopyTickersBtn");
    const exportBtn = document.getElementById("trackerExportExcelBtn");

    if (addBtn) {
        addBtn.addEventListener("click", () => {
            const sym = document.getElementById("trackerNewTicker").value.trim().toUpperCase();
            const move = parseFloat(document.getElementById("trackerNewMove").value) || 0.0;
            if (sym) {
                trackerItems.push({ ticker: sym, actual_move: move });
                document.getElementById("trackerNewTicker").value = "";
                runTrackerCalculation();
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            trackerItems = [];
            runTrackerCalculation();
        });
    }

    if (bulkBtn) {
        bulkBtn.addEventListener("click", openTrackerBulkModal);
    }

    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const list = trackerItems.map(i => i.ticker).join(", ");
            navigator.clipboard.writeText(list).then(() => {
                alert(`Скопировано ${trackerItems.length} тикеров в буфер обмена.`);
            });
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener("click", exportTrackerExcel);
    }

    document.querySelectorAll(".tracker-preset").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tracker-preset").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            filterTrackerTable(btn.dataset.op, btn.dataset.val);
        });
    });

    renderTrackerTable([]);
}

async function runTrackerCalculation() {
    const ref = document.getElementById("trackerReference").value.trim().toUpperCase() || "SPY";
    const refMove = parseFloat(document.getElementById("trackerReferenceMove").value) || 0.8;
    const period = document.getElementById("trackerPeriod").value || "1y";

    if (trackerItems.length === 0) {
        trackerCurrentData = [];
        renderTrackerTable([]);
        return;
    }

    const tickers = trackerItems.map(i => i.ticker);
    const assetMoves = {};
    trackerItems.forEach(i => {
        assetMoves[i.ticker] = i.actual_move;
    });

    try {
        const payload = {
            groups: { "Tracker": tickers },
            benchmark: ref,
            benchmark_move: refMove,
            period: period,
            asset_moves: assetMoves
        };

        const res = await fetch("/api/calculate-groups", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            const rows = [];
            const corrMap = data.correlation || {};
            const betaMap = data.beta || {};
            const expRange = data.expected_range || {};

            tickers.forEach(t => {
                const item = trackerItems.find(i => i.ticker === t) || {};
                const corrVal = corrMap[t] ? corrMap[t][ref] : null;
                const betaVal = betaMap[t] ? betaMap[t][ref] : null;
                const metrics = expRange[t] || {};

                rows.push({
                    ticker: t,
                    correlation: corrVal,
                    beta: betaVal,
                    expected_move: metrics.expected_move,
                    actual_move: item.actual_move !== undefined ? item.actual_move : metrics.actual_move,
                    difference: metrics.difference,
                    normalized: metrics.normalized_difference,
                    volatility: metrics.volatility,
                    residual_volatility: metrics.residual_volatility,
                    observations: metrics.observations
                });
            });

            trackerCurrentData = rows;
            trackerFilteredData = rows;
            renderTrackerTable(trackerFilteredData);
        }
    } catch (e) {
        console.error("Tracker calc error:", e);
    }
}

function renderTrackerTable(rows) {
    const tbody = document.getElementById("trackerTableBody");
    tbody.innerHTML = "";

    document.getElementById("trackerMatchCount").textContent = rows.length;
    document.getElementById("trackerMatchTotal").textContent = `/ ${trackerItems.length} активов`;

    if (rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="loading-cell">В трекере пока нет тикеров. Добавьте тикер выше или используйте Bulk вставку.</td></tr>`;
        return;
    }

    rows.forEach((r, idx) => {
        const tr = document.createElement("tr");

        const corrFmt = formatCorrBadge(r.correlation);
        const betaFmt = r.beta !== null && r.beta !== undefined ? Number(r.beta).toFixed(3) : "—";
        const expMoveFmt = formatPctBadge(r.expected_move);
        const diffFmt = formatPctBadge(r.difference);
        const normFmt = r.normalized !== null && r.normalized !== undefined ? `${Number(r.normalized).toFixed(2)}σ` : "—";
        const volFmt = r.volatility ? `${(r.volatility * 100).toFixed(2)}%` : "—";
        const resVolFmt = r.residual_volatility ? `${(r.residual_volatility * 100).toFixed(2)}%` : "—";

        tr.innerHTML = `
            <td><span class="clickable-ticker" data-ticker="${r.ticker}">${r.ticker}</span></td>
            <td>${corrFmt}</td>
            <td><strong>${betaFmt}</strong></td>
            <td>${expMoveFmt}</td>
            <td>
                <input class="editable-cell-input" type="number" step="0.1" value="${r.actual_move !== null ? r.actual_move : ''}" data-ticker="${r.ticker}">
            </td>
            <td>${diffFmt}</td>
            <td>${normFmt}</td>
            <td>${volFmt}</td>
            <td>${resVolFmt}</td>
            <td>${r.observations || "—"}</td>
            <td>
                <button class="action-btn danger" style="padding: 2px 6px; font-size: 11px;" data-remove-idx="${idx}">✕</button>
            </td>
        `;

        tr.querySelector(".clickable-ticker").addEventListener("click", () => switchToStockAnalytics(r.ticker));

        const inp = tr.querySelector(".editable-cell-input");
        inp.addEventListener("change", (e) => {
            const val = parseFloat(e.target.value);
            const found = trackerItems.find(i => i.ticker === r.ticker);
            if (found) {
                found.actual_move = isNaN(val) ? 0.0 : val;
                runTrackerCalculation();
            }
        });

        tr.querySelector("[data-remove-idx]").addEventListener("click", () => {
            trackerItems.splice(idx, 1);
            runTrackerCalculation();
        });

        tbody.appendChild(tr);
    });
}

function filterTrackerTable(op, val) {
    if (op === "all") {
        trackerFilteredData = trackerCurrentData;
    } else {
        const threshold = parseFloat(val);
        trackerFilteredData = trackerCurrentData.filter(r => {
            if (r.correlation === null || r.correlation === undefined) return false;
            if (op === "gte") return r.correlation >= threshold;
            if (op === "lte") return r.correlation <= threshold;
            return true;
        });
    }
    renderTrackerTable(trackerFilteredData);
}

function openTrackerBulkModal() {
    const modal = document.getElementById("trackerBulkModal");
    const closeBtn = document.getElementById("closeTrackerBulkModal");
    const cancelBtn = document.getElementById("cancelTrackerBulkModal");
    const replaceBtn = document.getElementById("submitTrackerBulkReplace");
    const appendBtn = document.getElementById("submitTrackerBulkAppend");
    const textarea = document.getElementById("trackerBulkText");
    const countSpan = document.getElementById("trackerBulkCount");

    modal.classList.add("active");

    const parseLines = () => {
        const text = textarea.value;
        const lines = text.split(/[\r\n,;]+/);
        const parsed = [];
        lines.forEach(l => {
            const parts = l.trim().split(/\s+/);
            if (parts.length >= 1 && parts[0]) {
                const sym = parts[0].toUpperCase();
                let move = 0.0;
                if (parts.length >= 2) {
                    move = parseFloat(parts[1].replace("%", "")) || 0.0;
                }
                parsed.push({ ticker: sym, actual_move: move });
            }
        });
        return parsed;
    };

    textarea.oninput = () => {
        countSpan.textContent = `${parseLines().length} записей`;
    };

    const closeModal = () => modal.classList.remove("active");
    closeBtn.onclick = closeModal;
    cancelBtn.onclick = closeModal;

    replaceBtn.onclick = () => {
        trackerItems = parseLines();
        runTrackerCalculation();
        closeModal();
    };

    appendBtn.onclick = () => {
        trackerItems.push(...parseLines());
        runTrackerCalculation();
        closeModal();
    };
}

async function exportTrackerExcel() {
    if (trackerCurrentData.length === 0) return;
    const ref = document.getElementById("trackerReference").value.trim().toUpperCase() || "SPY";
    const period = document.getElementById("trackerPeriod").value || "1y";

    try {
        const payload = {
            rows: trackerCurrentData,
            benchmark: ref,
            period: period
        };

        const res = await fetch("/api/export-excel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Tracker_Analysis_${ref}_${period}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    } catch (e) {
        console.error("Export error:", e);
    }
}


// ============================================================
// TAB 2: FINWHALE STOCK & DUAL CHART ANALYTICS
// ============================================================
function initCharts() {
    const c = THEME_CONFIGS[currentTheme] || THEME_CONFIGS.sand;

    const chartCommonOptions = {
        layout: {
            background: { color: c.chartBg },
            textColor: c.text,
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
        },
        grid: {
            vertLines: { color: c.grid, style: LightweightCharts.LineStyle.Solid },
            horzLines: { color: c.grid, style: LightweightCharts.LineStyle.Solid },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                color: c.crosshair,
                width: 1,
                style: LightweightCharts.LineStyle.Dashed,
                labelBackgroundColor: c.crosshair,
            },
            horzLine: {
                color: c.crosshair,
                width: 1,
                style: LightweightCharts.LineStyle.Dashed,
                labelBackgroundColor: c.crosshair,
            },
        },
        rightPriceScale: {
            borderColor: c.border,
            textColor: c.text,
            scaleMargins: { top: 0.08, bottom: 0.08 },
        },
        timeScale: {
            borderColor: c.border,
            textColor: c.text,
            timeVisible: true,
            secondsVisible: false,
        },
    };

    // 1. Initialize Daily Chart
    const dailyContainer = document.getElementById("dailyChartContainer");
    const hudCard = document.getElementById("dailyHudCard");

    if (dailyContainer) {
        dailyChart = LightweightCharts.createChart(dailyContainer, {
            ...chartCommonOptions,
            autoSize: true,
        });

        dailySeries = dailyChart.addCandlestickSeries({
            upColor: c.upColor,
            downColor: c.downColor,
            borderVisible: true,
            borderUpColor: c.upColor,
            borderDownColor: c.downColor,
            wickUpColor: c.upColor,
            wickDownColor: c.downColor,
        });

        // Hover visibility for Daily HUD Card
        dailyContainer.addEventListener("mouseenter", () => {
            if (hudCard) hudCard.classList.add("visible");
        });

        dailyContainer.addEventListener("mouseleave", () => {
            if (hudCard) hudCard.classList.remove("visible");
            const tooltip = document.getElementById("eventTooltip");
            if (tooltip) tooltip.classList.add("hidden");
        });

        let lastClickTimestamp = 0;
        let lastHoveredDateStr = "";
        let isChartsSynced = true;

        const syncBtn = document.getElementById("syncChartsBtn");
        if (syncBtn) {
            syncBtn.addEventListener("click", () => {
                isChartsSynced = !isChartsSynced;
                syncBtn.classList.toggle("active", isChartsSynced);
                if (isChartsSynced && lastHoveredDateStr) {
                    loadStockIntradayChart(currentStockTicker, lastHoveredDateStr);
                }
            });
        }

        // Native Double Click on daily chart container
        dailyContainer.addEventListener("dblclick", () => {
            if (lastHoveredDateStr) {
                loadStockIntradayChart(currentStockTicker, lastHoveredDateStr);
            }
        });

        // Click / Double Click -> Sync & Load exact Intraday Chart Day
        dailyChart.subscribeClick((param) => {
            if (!param || !param.time) return;
            let dateStr = "";
            if (typeof param.time === "string") {
                dateStr = param.time;
            } else if (typeof param.time === "object" && param.time.year) {
                const y = param.time.year;
                const m = String(param.time.month).padStart(2, "0");
                const d = String(param.time.day).padStart(2, "0");
                dateStr = `${y}-${m}-${d}`;
            }

            if (dateStr && currentDailyCandlesMap[dateStr]) {
                updateDailyHudCard(currentDailyCandlesMap[dateStr]);
            }

            const now = Date.now();
            const isDouble = (now - lastClickTimestamp < 450);
            lastClickTimestamp = now;

            // Load intraday on double click or when sync is active
            if (dateStr && (isDouble || isChartsSynced)) {
                loadStockIntradayChart(currentStockTicker, dateStr);
            }
        });

        // Hover -> Update Floating HUD Card & Event Tooltip
        dailyChart.subscribeCrosshairMove((param) => {
            const tooltip = document.getElementById("eventTooltip");

            if (!param || !param.time || !param.point) {
                if (tooltip) tooltip.classList.add("hidden");
                return;
            }

            let dateStr = "";
            if (typeof param.time === "string") {
                dateStr = param.time;
            } else if (typeof param.time === "object" && param.time.year) {
                const y = param.time.year;
                const m = String(param.time.month).padStart(2, "0");
                const d = String(param.time.day).padStart(2, "0");
                dateStr = `${y}-${m}-${d}`;
            }

            if (dateStr) {
                lastHoveredDateStr = dateStr;
            }

            if (dateStr && currentDailyCandlesMap[dateStr]) {
                updateDailyHudCard(currentDailyCandlesMap[dateStr]);
                if (hudCard) hudCard.classList.add("visible");
            }

            const eKey = `e_${dateStr}`;
            const dKey = `d_${dateStr}`;
            const eventData = currentMarkerDetails[eKey] || currentMarkerDetails[dKey];

            if (eventData && tooltip) {
                renderEventTooltip(tooltip, eventData, param.point, dailyContainer);
            } else if (tooltip) {
                tooltip.classList.add("hidden");
            }
        });
    }

    // 2. Initialize Intraday Chart (Soft Layered Background)
    const intradayContainer = document.getElementById("intradayChartContainer");
    if (intradayContainer) {
        intradayChart = LightweightCharts.createChart(intradayContainer, {
            ...chartCommonOptions,
            autoSize: true,
        });

        intradayBgSeries = intradayChart.addHistogramSeries({
            priceScaleId: "session_bg_scale",
            priceFormat: { type: "volume" },
            scaleMargins: { top: 0, bottom: 0 },
            lastValueVisible: false,
            priceLineVisible: false,
            base: 0,
        });
        intradayChart.priceScale("session_bg_scale").applyOptions({
            scaleMargins: { top: 0, bottom: 0 },
            visible: false,
        });

        intradaySeries = intradayChart.addCandlestickSeries({
            upColor: c.upColor,
            downColor: c.downColor,
            borderVisible: true,
            borderUpColor: c.upColor,
            borderDownColor: c.downColor,
            wickUpColor: c.upColor,
            wickDownColor: c.downColor,
        });
    }

    window.addEventListener("resize", resizeCharts);
}

function updateDailyHudCard(candleData) {
    if (!candleData) return;

    document.getElementById("hudTicker").textContent = currentStockTicker;
    
    let dateDisplay = candleData.time;
    try {
        const dt = new Date(candleData.time);
        if (!isNaN(dt.getTime())) {
            dateDisplay = dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase();
        }
    } catch (e) {}
    document.getElementById("hudDate").textContent = dateDisplay;

    document.getElementById("hudOpen").textContent = Number(candleData.open).toFixed(2);
    document.getElementById("hudHigh").textContent = Number(candleData.high).toFixed(2);
    document.getElementById("hudLow").textContent = Number(candleData.low).toFixed(2);
    document.getElementById("hudClose").textContent = Number(candleData.close).toFixed(2);

    const intraDiff = candleData.close - candleData.open;
    const intraPct = (intraDiff / (candleData.open || 1)) * 100;
    renderHudMetric("hudIntra", intraDiff, intraPct);

    const volVal = candleData.volume || 0;
    document.getElementById("hudVol").textContent = formatVolumeReadable(volVal);
}

function renderHudMetric(elementId, diffVal, pctVal) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const isPos = diffVal >= 0;
    const sign = isPos ? "+" : "";
    const cls = isPos ? "positive" : "negative";
    el.innerHTML = `<span class="${cls}">${sign}${diffVal.toFixed(2)} (${sign}${pctVal.toFixed(2)}%)</span>`;
}

function renderEventTooltip(tooltip, eventData, point, container) {
    if (eventData.type === "Earnings") {
        const surprise = eventData.eps_surprise_pct;
        let surpriseHtml = "—";
        if (surprise !== null && surprise !== undefined) {
            const isPos = surprise >= 0;
            const cls = isPos ? "positive" : "negative";
            const prefix = isPos ? "+" : "";
            surpriseHtml = `<span class="tooltip-surprise-badge ${cls}">${prefix}${Number(surprise).toFixed(2)}%</span>`;
        }

        const sessionClass = eventData.session === "BMO" ? "session-bmo" : "session-amc";

        tooltip.innerHTML = `
            <div class="tooltip-title-row">
                <div class="tooltip-title-left">
                    <span class="tooltip-tag earnings">EARNINGS</span>
                    <span class="tooltip-date">${eventData.date}</span>
                </div>
                <span class="tooltip-session-pill ${sessionClass}">${eventData.session || "AMC"}</span>
            </div>
            <div class="tooltip-grid">
                <span class="tooltip-lbl">EPS Факт:</span>
                <span class="tooltip-val">${eventData.eps_actual !== null ? "$" + Number(eventData.eps_actual).toFixed(2) : "—"}</span>

                <span class="tooltip-lbl">EPS Ожид.:</span>
                <span class="tooltip-val">${eventData.eps_estimate !== null ? "$" + Number(eventData.eps_estimate).toFixed(2) : "—"}</span>

                <span class="tooltip-lbl">Сюрприз EPS:</span>
                <div style="text-align: right;">${surpriseHtml}</div>

                <span class="tooltip-lbl">Выручка Факт:</span>
                <span class="tooltip-val">${eventData.revenue_actual ? formatCurrency(eventData.revenue_actual) : "—"}</span>

                <span class="tooltip-lbl">Выручка Ожид.:</span>
                <span class="tooltip-val">${eventData.revenue_estimate ? formatCurrency(eventData.revenue_estimate) : "—"}</span>
            </div>
        `;
    } else if (eventData.type === "Dividend") {
        tooltip.innerHTML = `
            <div class="tooltip-title-row">
                <div class="tooltip-title-left">
                    <span class="tooltip-tag dividend">DIVIDEND</span>
                    <span class="tooltip-date">${eventData.ex_date}</span>
                </div>
                <span class="tooltip-session-pill session-bmo">${eventData.frequency || "Quarterly"}</span>
            </div>
            <div class="tooltip-grid">
                <span class="tooltip-lbl">Дивиденд:</span>
                <span class="tooltip-val positive">$${Number(eventData.amount || 0).toFixed(4)}</span>

                <span class="tooltip-lbl">Дата выплаты:</span>
                <span class="tooltip-val">${eventData.pay_date || "—"}</span>

                <span class="tooltip-lbl">Доходность:</span>
                <span class="tooltip-val">${eventData.yield !== null && eventData.yield !== undefined ? Number(eventData.yield).toFixed(2) + "%" : "—"}</span>
            </div>
        `;
    }

    const maxLeft = (container ? container.clientWidth : window.innerWidth) - 240;
    const targetLeft = Math.max(10, Math.min(point.x + 14, maxLeft));
    const targetTop = Math.max(10, point.y - 24);

    tooltip.style.left = `${targetLeft}px`;
    tooltip.style.top = `${targetTop}px`;
    tooltip.classList.remove("hidden");
}

async function loadStockTickerData(ticker) {
    ticker = ticker.trim().toUpperCase();
    currentStockTicker = ticker;

    document.getElementById("tickerInput").value = ticker;
    document.getElementById("stockViewSymbolBadge").textContent = ticker;
    document.getElementById("tickerAvatar").textContent = ticker.slice(0, 2);

    try {
        await Promise.all([
            loadCompanyProfile(ticker),
            loadStockDailyChart(ticker),
            loadEarningsMoves(ticker, activePremarketWindow),
            loadTickerCorrelations(ticker, activeCorrPeriod),
            loadDividends(ticker)
        ]);
    } catch (err) {
        console.error("Error loading ticker data:", err);
    }
}

async function loadCompanyProfile(ticker) {
    try {
        const res = await fetch(`/api/ticker/${ticker}/profile`);
        const data = await res.json();

        document.getElementById("profileSymbol").textContent = data.symbol || data.ticker || ticker;
        document.getElementById("profileName").textContent = data.companyName || data.company_name || ticker;
        document.getElementById("profileExchange").textContent = data.exchange || "US";
        document.getElementById("profilePrice").textContent = data.price ? `$${Number(data.price).toFixed(2)}` : "—";
        document.getElementById("profileSector").textContent = data.sector || "—";
        document.getElementById("profileIndustry").textContent = data.industry || "—";
        document.getElementById("profileMktCap").textContent = (data.mktCap || data.mkt_cap) ? formatCurrency(data.mktCap || data.mkt_cap) : "—";
        document.getElementById("profileBeta").textContent = data.beta !== null && data.beta !== undefined ? Number(data.beta).toFixed(2) : "—";

        const descBox = document.getElementById("profileDescRu");
        const descText = data.descriptionRu || data.description_ru || data.description || "";
        descBox.textContent = descText.trim() ? descText : "Описание деятельности компании отсутствует в базе данных.";

        const businessPeersList = document.getElementById("businessPeersList");
        businessPeersList.innerHTML = "";
        const peers = data.business_peers || [];
        if (peers.length > 0) {
            peers.forEach(peer => {
                const chip = createPeerChip(peer.symbol, peer.companyName, peer.correlation);
                businessPeersList.appendChild(chip);
            });
        } else {
            businessPeersList.innerHTML = `<span class="peers-placeholder">Прямые конкуренты не найдены в базе.</span>`;
        }
    } catch (e) {
        console.error("Profile load error:", e);
    }
}

function createPeerChip(symbol, title, correlation = null) {
    const chip = document.createElement("div");
    chip.className = "peer-chip";
    chip.title = title || symbol;

    let corrHtml = "";
    if (correlation !== null && correlation !== undefined && !isNaN(correlation)) {
        const corrNum = Number(correlation);
        const prefix = corrNum >= 0 ? "+" : "";
        corrHtml = ` <span class="corr-val">${prefix}${corrNum.toFixed(2)}</span>`;
    }

    chip.innerHTML = `<span class="peer-chip-sym">${symbol}</span>${corrHtml}`;
    chip.addEventListener("click", () => switchToStockAnalytics(symbol));
    return chip;
}

async function loadStockDailyChart(ticker) {
    if (!dailySeries) return;

    try {
        const res = await fetch(`/api/ticker/${ticker}/chart/daily`);
        const data = await res.json();

        const rawCandles = data.candles || [];
        currentDailyCandles = [];
        currentDailyCandlesMap = {};

        const candles = [];
        const volumes = [];
        const c = THEME_CONFIGS[currentTheme] || THEME_CONFIGS.sand;

        for (let i = 0; i < rawCandles.length; i++) {
            const candle = rawCandles[i];
            const prevClose = i > 0 ? rawCandles[i - 1].close : candle.open;
            const isUp = candle.close >= candle.open;

            const candleObj = {
                time: candle.time,
                open: candle.open,
                high: candle.high,
                low: candle.low,
                close: candle.close,
                volume: candle.volume || 0,
                prevClose: prevClose
            };

            currentDailyCandles.push(candleObj);
            currentDailyCandlesMap[candle.time] = candleObj;

            candles.push({
                time: candle.time,
                open: candle.open,
                high: candle.high,
                low: candle.low,
                close: candle.close,
            });

            volumes.push({
                time: candle.time,
                value: candle.volume || 0,
                color: isUp ? c.volUp : c.volDown,
            });
        }

        dailySeries.setData(candles);

        currentMarkerDetails = data.marker_details || {};
        const markers = (data.markers || []).sort((a, b) => a.time.localeCompare(b.time));
        const formattedMarkers = markers.map(m => {
            const isEarnings = m.text === "E";
            return {
                time: m.time,
                position: m.position || "belowBar",
                color: isEarnings ? c.upColor : "#a36816",
                shape: isEarnings ? "square" : "circle",
                text: m.text || "E",
                size: 1.2
            };
        });
        dailySeries.setMarkers(formattedMarkers);
        dailyChart.timeScale().fitContent();

        // Initially link to the latest daily candle
        if (currentDailyCandles.length > 0) {
            const latest = currentDailyCandles[currentDailyCandles.length - 1];
            updateDailyHudCard(latest);
            loadStockIntradayChart(ticker, latest.time);
        }
    } catch (e) {
        console.error("Daily chart load error:", e);
    }
}

async function loadStockIntradayChart(ticker, dateStr) {
    if (!intradaySeries) return;
    const dateEl = document.getElementById("activeIntradayDate");
    if (dateEl) dateEl.textContent = dateStr;

    try {
        const res = await fetch(`/api/ticker/${ticker}/chart/intraday?date=${dateStr}&multiplier=${activeTfMultiplier}`);
        const data = await res.json();

        const rawCandles = data.candles || [];
        if (rawCandles.length === 0) {
            if (intradayBgSeries) intradayBgSeries.setData([]);
            intradaySeries.setData([]);
            return;
        }

        const c = THEME_CONFIGS[currentTheme] || THEME_CONFIGS.sand;

        // Map-based deduplication guaranteeing strictly ascending, unique timestamps
        const candleMap = new Map();
        const bgMap = new Map();

        rawCandles.forEach(candle => {
            let timeVal = candle.timestamp;
            if (!timeVal) {
                const dt = new Date(`${candle.time.replace(" ", "T")}Z`);
                timeVal = Math.floor(dt.getTime() / 1000);
            }
            if (isNaN(timeVal)) return;

            bgMap.set(timeVal, {
                time: timeVal,
                value: (candle.session_type === "premarket" || candle.session_type === "postmarket") ? 1000000 : 0,
                color: (candle.session_type === "premarket" || candle.session_type === "postmarket") ? c.preBg : "transparent"
            });

            candleMap.set(timeVal, {
                time: timeVal,
                open: candle.open,
                high: candle.high,
                low: candle.low,
                close: candle.close
            });
        });

        const sortedTimes = Array.from(candleMap.keys()).sort((a, b) => a - b);
        const candles = sortedTimes.map(t => candleMap.get(t));
        const bgBars = sortedTimes.map(t => bgMap.get(t));

        if (intradayBgSeries) intradayBgSeries.setData(bgBars);
        intradaySeries.setData(candles);
        intradayChart.timeScale().fitContent();

    } catch (e) {
        console.error("Intraday chart load error:", e);
    }
}

async function loadEarningsMoves(ticker, windowFilter = "04:00_09:30") {
    const tbody = document.getElementById("earningsTableBody");
    const premarketHeader = document.getElementById("premarketHeaderCol");
    
    const windowLabels = {
        "04:00_07:00": "0-D Премаркет (04:00-07:00)",
        "04:00_09:00": "0-D Премаркет (04:00-09:00)",
        "04:00_09:30": "0-D Премаркет (04:00-09:30)"
    };
    premarketHeader.textContent = windowLabels[windowFilter] || "0-D Премаркет";

    try {
        const res = await fetch(`/api/ticker/${ticker}/earnings-moves?window=${windowFilter}&limit=8`);
        const data = await res.json();
        const matrix = data.matrix || [];

        if (matrix.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" class="loading-cell">Нет данных по отчетности за последние 8 кварталов.</td></tr>`;
            return;
        }

        tbody.innerHTML = "";
        matrix.forEach(row => {
            const tr = document.createElement("tr");

            const postMove = formatPctBadge(row.postmarket_1d_pct);
            const preMove = formatPctBadge(row.premarket_0d_pct);
            const o2cMove = formatPctBadge(row.open_to_close_pct);
            const c2cMove = formatPctBadge(row.cls2cls_pct);
            const surpriseMove = formatPctBadge(row.eps_surprise_pct);
            const sessionBadge = `<span class="tooltip-session-pill">${row.session || 'AMC'}</span>`;

            const epsStr = row.eps_actual !== null 
                ? `$${Number(row.eps_actual).toFixed(2)} / $${Number(row.eps_estimate || 0).toFixed(2)}`
                : "—";

            const revStr = row.revenue_actual 
                ? `${formatCurrency(row.revenue_actual)} / ${formatCurrency(row.revenue_estimate)}`
                : "—";

            tr.innerHTML = `
                <td><strong>${row.quarter}</strong></td>
                <td>${row.date}</td>
                <td>${sessionBadge}</td>
                <td>${epsStr}</td>
                <td>${surpriseMove}</td>
                <td>${revStr}</td>
                <td>${postMove}</td>
                <td>${preMove}</td>
                <td>${o2cMove}</td>
                <td>${c2cMove}</td>
                <td>
                    <button class="secondary-button" style="padding: 2px 6px; font-size: 11px;" data-date="${row.reaction_date || row.date}">5m График</button>
                </td>
            `;

            tr.querySelector("button").addEventListener("click", (e) => {
                e.stopPropagation();
                const targetDate = row.reaction_date || row.date;
                loadStockIntradayChart(ticker, targetDate);
                document.querySelector(".charts-section").scrollIntoView({ behavior: "smooth" });
            });

            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="11" class="loading-cell">Ошибка загрузки матрицы отчетов.</td></tr>`;
    }
}

async function loadTickerCorrelations(ticker, period = "1y") {
    const tbody = document.getElementById("corrTableBody");
    const industryCorrList = document.getElementById("industryCorrList");
    const industryCorrCount = document.getElementById("industryCorrCount");

    try {
        const res = await fetch(`/api/ticker/${ticker}/correlations?period=${period}`);
        const data = await res.json();

        const highCorrs = data.high_corr_industry || [];
        const topPositives = data.top_positive_industry || [];
        industryCorrList.innerHTML = "";

        if (highCorrs.length > 0) {
            industryCorrCount.textContent = `${highCorrs.length} тикеров (r ≥ 0.60)`;
            highCorrs.forEach(item => {
                const chip = createPeerChip(item.symbol, `Correlation: ${Number(item.correlation).toFixed(3)}`, item.correlation);
                industryCorrList.appendChild(chip);
            });
        } else if (topPositives.length > 0) {
            industryCorrCount.textContent = `Макс. за период (${period}):`;
            topPositives.forEach(item => {
                const chip = createPeerChip(item.symbol, `Correlation: ${Number(item.correlation).toFixed(3)}`, item.correlation);
                industryCorrList.appendChild(chip);
            });
        } else {
            industryCorrCount.textContent = "Нет связей";
            industryCorrList.innerHTML = `<span class="peers-placeholder">Нет активов с положительной корреляцией.</span>`;
        }

        const multiSummary = data.multi_period_summary || {};
        const activeSummary = multiSummary[period] || {};

        document.getElementById("spyCorrVal").textContent = activeSummary.spy_correlation !== undefined && activeSummary.spy_correlation !== null 
            ? Number(activeSummary.spy_correlation).toFixed(2) : "—";
        document.getElementById("spyBetaVal").textContent = activeSummary.spy_beta !== undefined && activeSummary.spy_beta !== null
            ? `Beta: ${Number(activeSummary.spy_beta).toFixed(2)}` : "Beta: —";

        document.getElementById("qqqCorrVal").textContent = activeSummary.qqq_correlation !== undefined && activeSummary.qqq_correlation !== null
            ? Number(activeSummary.qqq_correlation).toFixed(2) : "—";
        document.getElementById("qqqBetaVal").textContent = activeSummary.qqq_beta !== undefined && activeSummary.qqq_beta !== null
            ? `Beta: ${Number(activeSummary.qqq_beta).toFixed(2)}` : "Beta: —";

        const dailyVol = data.target_volatility;
        document.getElementById("targetVolVal").textContent = dailyVol ? `${(dailyVol * 100).toFixed(2)}%` : "—";
        document.getElementById("targetVolAnn").textContent = dailyVol ? `Годовая: ${(dailyVol * Math.sqrt(252) * 100).toFixed(1)}%` : "Годовая: —";

        const list = data.ticker_correlations || [];
        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Нет данных для расчета корреляций.</td></tr>`;
            return;
        }

        tbody.innerHTML = "";
        list.forEach(item => {
            const tr = document.createElement("tr");
            const typeBadge = `<span class="group-badge-count">${item.type}</span>`;
            const corrBadge = formatCorrHeatmap(item.correlation);
            const betaStr = item.beta !== null ? Number(item.beta).toFixed(3) : "—";
            const volStr = item.volatility !== null ? `${(item.volatility * 100).toFixed(2)}%` : "—";

            tr.innerHTML = `
                <td><strong><span class="clickable-ticker" data-ticker="${item.symbol}">${item.symbol}</span></strong></td>
                <td>${typeBadge}</td>
                <td>${corrBadge}</td>
                <td>${betaStr}</td>
                <td>${volStr}</td>
                <td>${item.observations || "—"} дн.</td>
            `;

            tr.querySelector(".clickable-ticker").addEventListener("click", () => switchToStockAnalytics(item.symbol));
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Ошибка расчета матрицы корреляций.</td></tr>`;
    }
}

async function loadDividends(ticker) {
    const tbody = document.getElementById("dividendsTableBody");

    try {
        const res = await fetch(`/api/ticker/${ticker}/dividends`);
        const data = await res.json();
        const divs = data.dividends || [];

        if (divs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Нет данных о выплате дивидендов для тикера ${ticker}.</td></tr>`;
            return;
        }

        tbody.innerHTML = "";
        divs.forEach(d => {
            const tr = document.createElement("tr");
            const yieldStr = d.yield !== null && d.yield !== undefined ? `${Number(d.yield).toFixed(2)}%` : "—";

            tr.innerHTML = `
                <td><strong>${d.ex_date || d.date}</strong></td>
                <td class="positive">$${Number(d.amount || d.dividend || 0).toFixed(4)}</td>
                <td>${d.pay_date || d.paymentDate || "—"}</td>
                <td>${d.record_date || d.recordDate || "—"}</td>
                <td>${yieldStr}</td>
                <td><span class="group-badge-count">${d.frequency || "Quarterly"}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Ошибка загрузки дивидендов.</td></tr>`;
    }
}

function initStockAnalyticsEvents() {
    const input = document.getElementById("tickerInput");
    const searchBtn = document.getElementById("searchBtn");
    const syncBtn = document.getElementById("syncBtn");
    const dropdown = document.getElementById("tickerDropdown");

    const triggerSearch = () => {
        const val = input.value.trim().toUpperCase();
        if (val && val !== currentStockTicker) {
            dropdown.classList.add("hidden");
            loadStockTickerData(val);
        }
    };

    if (searchBtn) searchBtn.addEventListener("click", triggerSearch);
    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") triggerSearch();
        });

        input.addEventListener("input", debounce(async () => {
            const val = input.value.trim().toUpperCase();
            if (val.length < 1) {
                dropdown.classList.add("hidden");
                return;
            }
            try {
                const res = await fetch(`/api/tickers?q=${val}`);
                const data = await res.json();
                const tickers = data.tickers || [];

                if (tickers.length > 0) {
                    dropdown.innerHTML = "";
                    tickers.slice(0, 10).forEach(t => {
                        const item = document.createElement("div");
                        item.className = "ticker-option";
                        item.textContent = t;
                        item.addEventListener("click", () => {
                            input.value = t;
                            dropdown.classList.add("hidden");
                            loadStockTickerData(t);
                        });
                        dropdown.appendChild(item);
                    });
                    dropdown.classList.remove("hidden");
                } else {
                    dropdown.classList.add("hidden");
                }
            } catch (e) {}
        }, 150));
    }

    document.addEventListener("click", (e) => {
        if (input && dropdown && !input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add("hidden");
        }
    });

    if (syncBtn) {
        syncBtn.addEventListener("click", async () => {
            syncBtn.disabled = true;
            syncBtn.textContent = "Синхронизация...";
            try {
                await fetch(`/api/ticker/${currentStockTicker}/sync`, { method: "POST" });
                await loadStockTickerData(currentStockTicker);
            } catch (e) {
                console.error("Sync error:", e);
            } finally {
                syncBtn.disabled = false;
                syncBtn.textContent = "Синхронизация";
            }
        });
    }

    document.querySelectorAll("#premarketPillGroup .pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#premarketPillGroup .pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activePremarketWindow = btn.dataset.window;
            loadEarningsMoves(currentStockTicker, activePremarketWindow);
        });
    });

    document.querySelectorAll("#periodPillGroup .pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#periodPillGroup .pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeCorrPeriod = btn.dataset.period;
            loadTickerCorrelations(currentStockTicker, activeCorrPeriod);
        });
    });

    document.querySelectorAll(".analytics-workspace .tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".analytics-workspace .tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".analytics-workspace .tab-content").forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            const target = document.getElementById(btn.dataset.tab);
            if (target) target.classList.add("active");
        });
    });
}


// ============================================================
// HELPER FORMATTERS
// ============================================================
function formatPctBadge(val) {
    if (val === null || val === undefined || isNaN(val)) return `<span style="color: var(--text-muted);">—</span>`;
    const num = Number(val);
    const cls = num >= 0 ? "positive" : "negative";
    const prefix = num >= 0 ? "+" : "";
    return `<span class="${cls}">${prefix}${num.toFixed(2)}%</span>`;
}

function formatCorrBadge(val) {
    if (val === null || val === undefined || isNaN(val)) return `<span style="color: var(--text-muted);">—</span>`;
    const num = Number(val);
    let color = "var(--text-secondary)";
    if (num >= 0.5) color = "var(--text-green)";
    else if (num <= -0.2) color = "var(--text-red)";
    const prefix = num >= 0 ? "+" : "";
    return `<span style="color: ${color}; font-weight: 700;">${prefix}${num.toFixed(3)}</span>`;
}

function getCorrBgColor(val) {
    const num = Number(val);
    if (isNaN(num)) return "transparent";
    if (num >= 0.6) return "rgba(37, 122, 88, 0.22)";
    if (num >= 0.3) return "rgba(37, 122, 88, 0.12)";
    if (num <= -0.4) return "rgba(150, 56, 56, 0.22)";
    if (num < 0) return "rgba(150, 56, 56, 0.10)";
    return "transparent";
}

function getBetaBgColor(val) {
    const num = Number(val);
    if (isNaN(num)) return "transparent";
    if (num >= 1.5) return "rgba(37, 122, 88, 0.22)";
    if (num >= 1.0) return "rgba(37, 122, 88, 0.12)";
    if (num <= 0) return "rgba(150, 56, 56, 0.22)";
    return "transparent";
}

function formatCorrHeatmap(val) {
    if (val === null || val === undefined || isNaN(val)) return `<span style="color: var(--text-muted);">—</span>`;
    const num = Number(val);
    let color = "var(--text-secondary)";
    if (num >= 0.6) color = "var(--text-green)";
    else if (num >= 0.3) color = "var(--accent-blue)";
    else if (num <= -0.2) color = "var(--text-red)";
    const prefix = num >= 0 ? "+" : "";
    return `<span style="color: ${color}; font-weight: 700;">${prefix}${num.toFixed(3)}</span>`;
}

function formatCurrency(val) {
    if (!val || isNaN(val)) return "—";
    const num = Number(val);
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    return `$${num.toLocaleString()}`;
}

function formatVolumeReadable(vol) {
    if (!vol || isNaN(vol)) return "0";
    const num = Number(vol);
    if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
    return num.toLocaleString();
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
