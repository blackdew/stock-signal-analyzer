#!/bin/bash
# 주식 신호 분석 스케줄러 관리 스크립트

set -e

PROJECT_DIR="/Users/sookbunlee/work/trading"
PLIST_FILE="$HOME/Library/LaunchAgents/com.trading.stock-signals.plist"
SERVICE_NAME="com.trading.stock-signals"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 출력
show_help() {
    echo ""
    echo "======================================"
    echo "주식 신호 분석 스케줄러 관리 도구"
    echo "======================================"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  status    - 스케줄러 상태 확인"
    echo "  start     - 스케줄러 시작 (등록)"
    echo "  stop      - 스케줄러 중지 (해제)"
    echo "  restart   - 스케줄러 재시작"
    echo "  test      - 수동 테스트 실행"
    echo "  logs      - 최근 로그 확인"
    echo "  reports   - 최근 리포트 확인"
    echo "  help      - 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 status     # 현재 상태 확인"
    echo "  $0 start      # 스케줄러 시작"
    echo "  $0 test       # 바로 실행해보기"
    echo ""
}

# 상태 확인
check_status() {
    echo ""
    echo -e "${BLUE}[스케줄러 상태 확인]${NC}"
    echo "========================================"

    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ 스케줄러가 실행 중입니다${NC}"
        echo ""
        launchctl list | grep "$SERVICE_NAME"
        echo ""

        # plist 파일 확인
        if [ -f "$PLIST_FILE" ]; then
            echo -e "${GREEN}✅ plist 파일 존재:${NC} $PLIST_FILE"
        else
            echo -e "${RED}❌ plist 파일 없음${NC}"
        fi

        # 다음 실행 시간
        echo ""
        echo "📅 스케줄: 월~금 오전 10시, 오후 2시"
        echo "📂 리포트 저장: $PROJECT_DIR/reports/"
        echo "📋 로그 저장: $PROJECT_DIR/logs/"
    else
        echo -e "${RED}❌ 스케줄러가 실행 중이 아닙니다${NC}"
        echo ""
        echo "스케줄러를 시작하려면:"
        echo "  $0 start"
    fi
    echo ""
}

# 스케줄러 시작
start_scheduler() {
    echo ""
    echo -e "${BLUE}[스케줄러 시작]${NC}"
    echo "========================================"

    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${YELLOW}⚠️  스케줄러가 이미 실행 중입니다${NC}"
        echo ""
        check_status
        return
    fi

    if [ ! -f "$PLIST_FILE" ]; then
        echo -e "${RED}❌ plist 파일이 없습니다${NC}"
        echo ""
        echo "먼저 스케줄러를 설치하세요:"
        echo "  bash $PROJECT_DIR/scripts/setup_scheduler.sh"
        echo ""
        return 1
    fi

    echo "스케줄러를 시작합니다..."
    launchctl load "$PLIST_FILE"

    sleep 1

    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ 스케줄러가 시작되었습니다${NC}"
        check_status
    else
        echo -e "${RED}❌ 스케줄러 시작 실패${NC}"
        return 1
    fi
}

# 스케줄러 중지
stop_scheduler() {
    echo ""
    echo -e "${BLUE}[스케줄러 중지]${NC}"
    echo "========================================"

    if ! launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${YELLOW}⚠️  스케줄러가 실행 중이 아닙니다${NC}"
        echo ""
        return
    fi

    echo "스케줄러를 중지합니다..."
    launchctl unload "$PLIST_FILE"

    sleep 1

    if ! launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ 스케줄러가 중지되었습니다${NC}"
    else
        echo -e "${RED}❌ 스케줄러 중지 실패${NC}"
        return 1
    fi
    echo ""
}

# 스케줄러 재시작
restart_scheduler() {
    echo ""
    echo -e "${BLUE}[스케줄러 재시작]${NC}"
    echo "========================================"

    stop_scheduler
    sleep 1
    start_scheduler
}

# 수동 테스트 실행
run_test() {
    echo ""
    echo -e "${BLUE}[수동 테스트 실행]${NC}"
    echo "========================================"
    echo ""

    if [ ! -f "$PROJECT_DIR/scripts/run_scheduled_report.sh" ]; then
        echo -e "${RED}❌ 실행 스크립트를 찾을 수 없습니다${NC}"
        return 1
    fi

    echo "리포트를 생성합니다..."
    echo ""

    bash "$PROJECT_DIR/scripts/run_scheduled_report.sh"

    echo ""
    echo -e "${GREEN}✅ 테스트 완료${NC}"
    echo ""
    echo "생성된 리포트:"
    ls -lht "$PROJECT_DIR/reports/" | head -3
    echo ""
}

# 로그 확인
show_logs() {
    echo ""
    echo -e "${BLUE}[최근 로그]${NC}"
    echo "========================================"
    echo ""

    STDOUT_LOG="$PROJECT_DIR/logs/launchd_stdout.log"
    STDERR_LOG="$PROJECT_DIR/logs/launchd_stderr.log"

    if [ -f "$STDOUT_LOG" ]; then
        echo -e "${GREEN}📋 표준 출력 로그 (최근 20줄):${NC}"
        echo "--------------------------------------"
        tail -20 "$STDOUT_LOG" 2>/dev/null || echo "로그가 비어있습니다"
        echo ""
    else
        echo -e "${YELLOW}⚠️  표준 출력 로그가 없습니다${NC}"
        echo ""
    fi

    if [ -f "$STDERR_LOG" ]; then
        echo -e "${RED}📋 에러 로그 (최근 20줄):${NC}"
        echo "--------------------------------------"
        tail -20 "$STDERR_LOG" 2>/dev/null || echo "로그가 비어있습니다"
        echo ""
    else
        echo -e "${YELLOW}⚠️  에러 로그가 없습니다${NC}"
        echo ""
    fi
}

# 리포트 확인
show_reports() {
    echo ""
    echo -e "${BLUE}[최근 리포트]${NC}"
    echo "========================================"
    echo ""

    REPORTS_DIR="$PROJECT_DIR/reports"

    if [ ! -d "$REPORTS_DIR" ]; then
        echo -e "${YELLOW}⚠️  리포트 디렉토리가 없습니다${NC}"
        echo ""
        return
    fi

    REPORT_COUNT=$(ls -1 "$REPORTS_DIR"/*.txt 2>/dev/null | wc -l)

    if [ "$REPORT_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  생성된 리포트가 없습니다${NC}"
        echo ""
        return
    fi

    echo -e "${GREEN}총 ${REPORT_COUNT}개의 리포트가 있습니다${NC}"
    echo ""
    echo "최근 10개 리포트:"
    echo "--------------------------------------"
    ls -lht "$REPORTS_DIR"/*.txt 2>/dev/null | head -10 | awk '{print $9, $6, $7, $8}'
    echo ""

    # 최신 리포트 미리보기
    LATEST_REPORT=$(ls -t "$REPORTS_DIR"/*.txt 2>/dev/null | head -1)
    if [ -n "$LATEST_REPORT" ]; then
        echo -e "${GREEN}📄 최신 리포트 미리보기:${NC} $(basename "$LATEST_REPORT")"
        echo "--------------------------------------"
        head -30 "$LATEST_REPORT"
        echo "..."
        echo ""
    fi
}

# 메인 로직
case "${1:-help}" in
    status)
        check_status
        ;;
    start)
        start_scheduler
        ;;
    stop)
        stop_scheduler
        ;;
    restart)
        restart_scheduler
        ;;
    test)
        run_test
        ;;
    logs)
        show_logs
        ;;
    reports)
        show_reports
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ 알 수 없는 명령어: $1${NC}"
        show_help
        exit 1
        ;;
esac

exit 0
