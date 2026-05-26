#!/bin/bash
# 일간 투자 분석 리포트 스케줄러 설치 스크립트
#
# com.trading.daily-report 작업을 macOS launchd에 등록합니다.
# 매일 오전 7시에 `uv run python main.py --daily`를 실행하여
# 네이버 금융/OpenDART 크롤링 → 분석 → 리포트 생성을 수행합니다.
#
# 사용법:  bash scripts/install_daily_scheduler.sh

set -e

PROJECT_DIR="/Users/sookbunlee/work/trading"
SERVICE_NAME="com.trading.daily-report"
PLIST_SRC="$PROJECT_DIR/launchd/${SERVICE_NAME}.plist"
RUN_SCRIPT="$PROJECT_DIR/scripts/run_daily_report.sh"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/${SERVICE_NAME}.plist"

echo "========================================="
echo "일간 투자 분석 리포트 스케줄러 설치"
echo "========================================="
echo ""

# ---- 0. 사전 점검 ------------------------------------------------------
if [ ! -f "$PLIST_SRC" ]; then
    echo "❌ plist 파일을 찾을 수 없습니다: $PLIST_SRC"
    exit 1
fi
if [ ! -f "$RUN_SCRIPT" ]; then
    echo "❌ 실행 스크립트를 찾을 수 없습니다: $RUN_SCRIPT"
    exit 1
fi

# ---- 1. LaunchAgents 디렉토리 -----------------------------------------
mkdir -p "$LAUNCH_AGENTS_DIR"

# ---- 2. 기존 서비스 중지 (있으면) -------------------------------------
if launchctl list | grep -q "$SERVICE_NAME"; then
    echo "기존 서비스 중지 중..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# ---- 3. plist 복사 및 권한 --------------------------------------------
echo "plist 복사 중: $PLIST_DEST"
cp "$PLIST_SRC" "$PLIST_DEST"
chmod 644 "$PLIST_DEST"
chmod +x "$RUN_SCRIPT"

# ---- 4. 로그 디렉토리 --------------------------------------------------
mkdir -p "$PROJECT_DIR/logs"

# ---- 5. launchd 등록 --------------------------------------------------
echo "launchd 등록 중..."
launchctl load "$PLIST_DEST"

# ---- 6. 등록 확인 -----------------------------------------------------
sleep 1
echo ""
if launchctl list | grep -q "$SERVICE_NAME"; then
    echo "✅ 설치 완료 — 스케줄러가 등록되었습니다."
else
    echo "⚠️  등록 확인 실패. 다음으로 직접 확인하세요:"
    echo "    launchctl list | grep $SERVICE_NAME"
fi

echo ""
echo "스케줄 : 매일 오전 7시 00분"
echo "실행   : uv run python main.py --daily  (네이버/OpenDART 크롤링 포함)"
echo "리포트 : $PROJECT_DIR/output/reports/daily/YYYY-MM-DD/"
echo "로그   : $PROJECT_DIR/logs/daily_report_YYYYMMDD.log"
echo ""
echo "지금 바로 한 번 실행해 검증하려면:"
echo "  launchctl start $SERVICE_NAME"
echo "  # 몇 분 뒤 로그 확인:"
echo "  bash scripts/manage_daily_scheduler.sh logs"
echo ""
echo "상태/로그/테스트 관리:"
echo "  bash scripts/manage_daily_scheduler.sh status"
echo ""
