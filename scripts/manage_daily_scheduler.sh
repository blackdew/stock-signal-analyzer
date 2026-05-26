#!/bin/bash
# 일간 투자 분석 리포트 스케줄러 관리 스크립트
#
# com.trading.daily-report 작업의 상태 확인/시작/중지/테스트/로그 관리.
#
# 사용법:  bash scripts/manage_daily_scheduler.sh [status|start|stop|restart|test|logs|reports|help]

set -e

PROJECT_DIR="/Users/sookbunlee/work/trading"
SERVICE_NAME="com.trading.daily-report"
PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
DAILY_DIR="$PROJECT_DIR/output/reports/daily"
LOG_DIR="$PROJECT_DIR/logs"
RUN_SCRIPT="$PROJECT_DIR/scripts/run_daily_report.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

show_help() {
    echo ""
    echo "======================================"
    echo "일간 투자 분석 리포트 스케줄러 관리"
    echo "======================================"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "  status   - 스케줄러 등록 상태 확인"
    echo "  start    - 스케줄러 등록 (plist load)"
    echo "  stop     - 스케줄러 해제 (plist unload)"
    echo "  restart  - 스케줄러 재시작"
    echo "  test     - 지금 즉시 한 번 실행 (크롤링+분석+리포트)"
    echo "  logs     - 최근 실행 로그 확인"
    echo "  reports  - 최근 생성된 리포트 확인"
    echo "  help     - 도움말"
    echo ""
}

check_status() {
    echo ""
    echo -e "${BLUE}[스케줄러 상태]${NC}"
    echo "========================================"
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ 등록됨 (매일 오전 7시 실행)${NC}"
        launchctl list | grep "$SERVICE_NAME" || true
        [ -f "$PLIST_FILE" ] && echo -e "${GREEN}✅ plist:${NC} $PLIST_FILE" \
                              || echo -e "${RED}❌ plist 파일 없음${NC}"
    else
        echo -e "${RED}❌ 등록되지 않음${NC}"
        echo "설치: bash $PROJECT_DIR/scripts/install_daily_scheduler.sh"
    fi
    echo ""
}

start_scheduler() {
    echo -e "${BLUE}[스케줄러 시작]${NC}"
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${YELLOW}⚠️  이미 등록되어 있습니다${NC}"; return
    fi
    if [ ! -f "$PLIST_FILE" ]; then
        echo -e "${RED}❌ plist가 없습니다. 먼저 설치하세요:${NC}"
        echo "  bash $PROJECT_DIR/scripts/install_daily_scheduler.sh"
        return 1
    fi
    launchctl load "$PLIST_FILE"
    sleep 1
    launchctl list | grep -q "$SERVICE_NAME" \
        && echo -e "${GREEN}✅ 시작됨${NC}" \
        || { echo -e "${RED}❌ 시작 실패${NC}"; return 1; }
}

stop_scheduler() {
    echo -e "${BLUE}[스케줄러 중지]${NC}"
    if ! launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${YELLOW}⚠️  등록되어 있지 않습니다${NC}"; return
    fi
    launchctl unload "$PLIST_FILE"
    sleep 1
    launchctl list | grep -q "$SERVICE_NAME" \
        && { echo -e "${RED}❌ 중지 실패${NC}"; return 1; } \
        || echo -e "${GREEN}✅ 중지됨${NC}"
}

restart_scheduler() {
    stop_scheduler || true
    sleep 1
    start_scheduler
}

run_test() {
    echo -e "${BLUE}[수동 테스트 실행]${NC}"
    if [ ! -f "$RUN_SCRIPT" ]; then
        echo -e "${RED}❌ 실행 스크립트 없음: $RUN_SCRIPT${NC}"; return 1
    fi
    echo "크롤링 → 분석 → 리포트 생성을 즉시 실행합니다..."
    echo ""
    bash "$RUN_SCRIPT"
    echo ""
    echo -e "${GREEN}✅ 테스트 완료${NC} — 아래에서 결과를 확인하세요:"
    show_reports
}

show_logs() {
    echo -e "${BLUE}[최근 로그]${NC}"
    echo "========================================"
    local latest_log
    latest_log=$(ls -t "$LOG_DIR"/daily_report_*.log 2>/dev/null | head -1 || true)
    if [ -n "$latest_log" ]; then
        echo -e "${GREEN}📋 $latest_log (최근 40줄):${NC}"
        echo "--------------------------------------"
        tail -40 "$latest_log"
    else
        echo -e "${YELLOW}⚠️  실행 로그가 아직 없습니다${NC}"
    fi
    echo ""
    if [ -f "$LOG_DIR/launchd_daily_stderr.log" ]; then
        echo -e "${RED}📋 launchd 에러 로그 (최근 20줄):${NC}"
        echo "--------------------------------------"
        tail -20 "$LOG_DIR/launchd_daily_stderr.log" 2>/dev/null || echo "(비어있음)"
    fi
    echo ""
}

show_reports() {
    echo -e "${BLUE}[최근 리포트]${NC}"
    echo "========================================"
    if [ ! -d "$DAILY_DIR" ]; then
        echo -e "${YELLOW}⚠️  아직 생성된 리포트가 없습니다 ($DAILY_DIR)${NC}"
        echo ""
        return
    fi
    local latest_dir
    latest_dir=$(ls -dt "$DAILY_DIR"/*/ 2>/dev/null | head -1 || true)
    if [ -z "$latest_dir" ]; then
        echo -e "${YELLOW}⚠️  날짜별 리포트 폴더가 없습니다${NC}"
        echo ""
        return
    fi
    echo -e "${GREEN}📂 최신 리포트 폴더:${NC} $latest_dir"
    ls -la "$latest_dir"
    local final="$latest_dir/03_final_report.md"
    if [ -f "$final" ]; then
        echo ""
        echo -e "${GREEN}📄 03_final_report.md 미리보기 (앞 30줄):${NC}"
        echo "--------------------------------------"
        head -30 "$final"
        echo "..."
    fi
    echo ""
}

case "${1:-help}" in
    status)  check_status ;;
    start)   start_scheduler ;;
    stop)    stop_scheduler ;;
    restart) restart_scheduler ;;
    test)    run_test ;;
    logs)    show_logs ;;
    reports) show_reports ;;
    help|--help|-h) show_help ;;
    *) echo -e "${RED}❌ 알 수 없는 명령어: $1${NC}"; show_help; exit 1 ;;
esac

exit 0
