#!/bin/bash
# 주식 신호 분석 스케줄 실행 스크립트

# 프로젝트 루트 디렉토리
PROJECT_DIR="/Users/sookbunlee/work/trading"
LOG_DIR="$PROJECT_DIR/logs"

# 로그 파일
LOG_FILE="$LOG_DIR/scheduler_$(date +%Y%m%d).log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 실행 시작 로그
echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 스케줄 실행 시작" >> "$LOG_FILE"

# 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR" || exit 1

# uv를 사용하여 main.py 실행
# 1. 텍스트 리포트 생성 (--scheduled)
/Users/sookbunlee/.local/bin/uv run main.py --scheduled >> "$LOG_FILE" 2>&1

# 2. JSON 리포트 생성 (웹 대시보드용)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] JSON 리포트 생성 중..." >> "$LOG_FILE"
/Users/sookbunlee/.local/bin/uv run python3 -c "
from src.analysis.analyzer import StockAnalyzer
from src.report.json_generator import JsonReportGenerator
from src.portfolio.loader import PortfolioLoader
import config
import os

# 최신 CSV 포트폴리오 로드
try:
    latest_csv = PortfolioLoader.find_latest_csv(config.MYPORTFOLIO_DIR)
    symbols, buy_prices, quantities = PortfolioLoader.load_csv(latest_csv)
except:
    symbols = config.STOCK_SYMBOLS
    buy_prices = {}
    quantities = {}

# 분석 실행
analyzer = StockAnalyzer(
    knee_threshold=config.BUY_KNEE_THRESHOLD,
    shoulder_threshold=config.SELL_SHOULDER_THRESHOLD,
    stop_loss_pct=config.STOP_LOSS_PERCENTAGE,
    chase_risk_threshold=config.CHASE_BUY_RISK_THRESHOLD,
    profit_target_full=config.PROFIT_TARGET_FULL_SELL,
    profit_target_partial=config.PROFIT_TARGET_PARTIAL_SELL,
    rsi_period=config.RSI_PERIOD,
    rsi_oversold=config.RSI_OVERSOLD,
    rsi_overbought=config.RSI_OVERBOUGHT,
    lookback_period=config.FLOOR_CEILING_LOOKBACK
)

analyses = analyzer.analyze_multiple_stocks(
    symbols,
    config.START_DATE,
    config.END_DATE,
    buy_prices if buy_prices else None
)

# JSON 리포트 생성
json_reporter = JsonReportGenerator()
json_path = json_reporter.save_json_report(analyses, buy_prices, quantities)
print(f'JSON 리포트 생성 완료: {json_path}')
" >> "$LOG_FILE" 2>&1

# 실행 결과 로그
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 성공" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 실패 (종료 코드: $EXIT_CODE)" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE
