// 전역 변수
let reportData = null;
let currentFilter = 'all';
let charts = {};

// 리포트 불러오기
async function loadReport() {
    const loading = document.getElementById('loading');
    loading.style.display = 'block';

    try {
        const response = await fetch('data/latest.json');
        if (!response.ok) {
            throw new Error('리포트를 불러올 수 없습니다.');
        }

        reportData = await response.json();
        renderDashboard();
    } catch (error) {
        loading.innerHTML = `<div class="error-card">리포트를 불러오는데 실패했습니다.<br>${error.message}</div>`;
    }
}

// 대시보드 렌더링
function renderDashboard() {
    document.getElementById('loading').style.display = 'none';

    // 헤더 정보
    const reportDate = new Date(reportData.meta.generated_at);
    document.getElementById('report-date').textContent =
        `생성일: ${reportDate.toLocaleString('ko-KR')}`;

    // 포트폴리오 요약
    renderPortfolioSummary();

    // 우선순위 종목
    renderPriorities();

    // 종목별 분석
    renderStocks();
}

// 포트폴리오 요약 렌더링
function renderPortfolioSummary() {
    const summary = reportData.portfolio_summary;
    const section = document.getElementById('portfolio-summary');

    if (summary.stocks_with_buy_price === 0) {
        // 매수가 정보가 없으면 요약 섹션 숨김
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    document.getElementById('total-investment').textContent =
        formatPrice(summary.total_investment);
    document.getElementById('total-valuation').textContent =
        formatPrice(summary.total_valuation);

    const profitElement = document.getElementById('total-profit');
    profitElement.textContent = formatPrice(summary.total_profit);
    profitElement.className = 'card-value ' + (summary.total_profit >= 0 ? 'positive' : 'negative');

    const rateElement = document.getElementById('total-profit-rate');
    rateElement.textContent = formatPercentage(summary.total_profit_rate);
    rateElement.className = 'card-value ' + (summary.total_profit_rate >= 0 ? 'positive' : 'negative');

    document.getElementById('total-stocks').textContent =
        `${summary.stocks_with_buy_price} / ${summary.total_stocks}개`;
}

// 우선순위 종목 렌더링
function renderPriorities() {
    const section = document.getElementById('priorities');
    section.style.display = 'grid';

    // 매수 우선순위
    const buyContainer = document.getElementById('buy-priorities');
    buyContainer.innerHTML = reportData.buy_priorities.map((stock, index) => `
        <div class="priority-item">
            <div class="stock-header">
                <div class="stock-name">${index + 1}. ${stock.name} (${stock.symbol})</div>
                <div class="stock-price">${formatPrice(stock.current_price)}</div>
            </div>
            <div class="stock-info">
                <span class="score">${stock.buy_score}점</span>
                ${stock.recommendation}
            </div>
        </div>
    `).join('');

    // 매도 우선순위
    const sellContainer = document.getElementById('sell-priorities');
    sellContainer.innerHTML = reportData.sell_priorities.map((stock, index) => {
        const profitClass = stock.profit_rate !== null && stock.profit_rate >= 0 ? 'profit-positive' : 'profit-negative';
        const profitText = stock.profit_rate !== null ? ` | 수익률: <span class="${profitClass}">${formatPercentage(stock.profit_rate)}</span>` : '';

        return `
            <div class="priority-item">
                <div class="stock-header">
                    <div class="stock-name">${index + 1}. ${stock.name} (${stock.symbol})</div>
                    <div class="stock-price">${formatPrice(stock.current_price)}</div>
                </div>
                <div class="stock-info">
                    <span class="score">${stock.sell_score}점</span>
                    ${stock.recommendation}${profitText}
                </div>
            </div>
        `;
    }).join('');
}

// 종목별 분석 렌더링
function renderStocks() {
    const section = document.getElementById('stocks-section');
    section.style.display = 'block';

    const container = document.getElementById('stocks-container');
    const stocks = reportData.stocks.filter(stock => !stock.error);

    const filteredStocks = currentFilter === 'all'
        ? stocks
        : stocks.filter(stock => stock.action === currentFilter);

    container.innerHTML = filteredStocks.map(stock => renderStockCard(stock)).join('');

    // 차트 렌더링
    filteredStocks.forEach(stock => {
        if (stock.price_history && stock.price_history.length > 0) {
            renderChart(stock);
        }
    });
}

// 종목 카드 렌더링
function renderStockCard(stock) {
    const priceLevels = stock.price_levels;
    const buyAnalysis = stock.buy_analysis;
    const sellAnalysis = stock.sell_analysis;

    const fromFloorClass = priceLevels.from_floor_pct >= 0 ? 'positive' : 'negative';
    const fromCeilingClass = priceLevels.from_ceiling_pct >= 0 ? 'positive' : 'negative';
    const profitClass = sellAnalysis.profit_rate !== null && sellAnalysis.profit_rate >= 0 ? 'positive' : 'negative';

    return `
        <div class="stock-card action-${stock.action}">
            <div class="stock-header-info">
                <div class="stock-title">
                    <div class="stock-name-large">${stock.name}</div>
                    <div class="stock-symbol">${stock.symbol}</div>
                </div>
                <div class="stock-current-price">
                    <div class="price-label">현재가</div>
                    <div class="price-value">${formatPrice(stock.current_price)}</div>
                </div>
            </div>

            <div class="price-levels">
                ${priceLevels.floor ? `
                    <div class="price-level-item">
                        <span class="price-level-label">바닥 (${formatDate(priceLevels.floor_date)})</span>
                        <span class="price-level-value">${formatPrice(priceLevels.floor)}</span>
                    </div>
                ` : ''}
                ${priceLevels.from_floor_pct !== null ? `
                    <div class="price-level-item">
                        <span class="price-level-label">바닥 대비</span>
                        <span class="price-level-value ${fromFloorClass}">${formatPercentage(priceLevels.from_floor_pct * 100)}</span>
                    </div>
                ` : ''}
                ${priceLevels.ceiling ? `
                    <div class="price-level-item">
                        <span class="price-level-label">천장 (${formatDate(priceLevels.ceiling_date)})</span>
                        <span class="price-level-value">${formatPrice(priceLevels.ceiling)}</span>
                    </div>
                ` : ''}
                ${priceLevels.from_ceiling_pct !== null ? `
                    <div class="price-level-item">
                        <span class="price-level-label">천장 대비</span>
                        <span class="price-level-value ${fromCeilingClass}">${formatPercentage(priceLevels.from_ceiling_pct * 100)}</span>
                    </div>
                ` : ''}
                ${sellAnalysis.profit_rate !== null ? `
                    <div class="price-level-item">
                        <span class="price-level-label">수익률</span>
                        <span class="price-level-value ${profitClass}">${formatPercentage(sellAnalysis.profit_rate * 100)}</span>
                    </div>
                ` : ''}
            </div>

            <div class="signals">
                <div class="signal-box">
                    <div class="signal-title">매수 신호</div>
                    <div class="signal-score">${buyAnalysis.buy_score}점</div>
                    <div class="signal-list">
                        ${buyAnalysis.buy_signals.length > 0 ? buyAnalysis.buy_signals.join('<br>') : '신호 없음'}
                    </div>
                    ${buyAnalysis.rsi ? `<div class="signal-list">RSI: ${buyAnalysis.rsi.toFixed(1)}</div>` : ''}
                </div>
                <div class="signal-box">
                    <div class="signal-title">매도 신호</div>
                    <div class="signal-score">${sellAnalysis.sell_score}점</div>
                    <div class="signal-list">
                        ${sellAnalysis.sell_signals.length > 0 ? sellAnalysis.sell_signals.join('<br>') : '신호 없음'}
                    </div>
                    ${sellAnalysis.sell_strategy ? `<div class="signal-list">${sellAnalysis.sell_strategy}</div>` : ''}
                </div>
            </div>

            <div class="chart-container">
                <canvas id="chart-${stock.symbol}"></canvas>
            </div>

            <div class="recommendation">
                ${stock.overall_recommendation}
            </div>
        </div>
    `;
}

// 차트 렌더링
function renderChart(stock) {
    const ctx = document.getElementById(`chart-${stock.symbol}`);
    if (!ctx) return;

    // 기존 차트 제거
    if (charts[stock.symbol]) {
        charts[stock.symbol].destroy();
    }

    const priceHistory = stock.price_history;
    const dates = priceHistory.map(d => d.date);
    const closes = priceHistory.map(d => d.close);
    const ma20 = priceHistory.map(d => d.ma20);
    const ma60 = priceHistory.map(d => d.ma60);

    charts[stock.symbol] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: '종가',
                    data: closes,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    fill: true
                },
                {
                    label: 'MA20',
                    data: ma20,
                    borderColor: '#f39c12',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    tension: 0.1,
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'MA60',
                    data: ma60,
                    borderColor: '#e74c3c',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    tension: 0.1,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatPrice(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: { size: 10 }
                    },
                    grid: { display: false }
                },
                y: {
                    display: true,
                    ticks: {
                        callback: function(value) {
                            return formatPrice(value);
                        },
                        font: { size: 10 }
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// 필터링
function filterStocks(filter) {
    currentFilter = filter;

    // 필터 버튼 활성화 상태 변경
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // 종목 다시 렌더링
    renderStocks();
}

// 유틸리티 함수
function formatPrice(price) {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW',
        maximumFractionDigits: 0
    }).format(price);
}

function formatPercentage(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
}
