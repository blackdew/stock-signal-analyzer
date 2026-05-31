#!/bin/bash
# 주식 신호 분석 스케줄 실행 스크립트 (macOS launchd 스케줄 실행용)
#
# main.py --daily 를 실행하여 output/reports/daily/YYYY-MM-DD/ 에
# 섹터/종목/종합 리포트 및 웹 대시보드용 JSON 데이터(output/data/)를 생성합니다.

set -u

# 프로젝트 루트 디렉토리
PROJECT_DIR="/Users/sookbunlee/work/trading"
UV_BIN="/Users/sookbunlee/.local/bin/uv"
LOG_DIR="$PROJECT_DIR/logs"

# 로그 파일
LOG_FILE="$LOG_DIR/scheduler_$(date +%Y%m%d).log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 실행 시작 로그
{
  echo "========================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 스케줄 실행 시작"
} >> "$LOG_FILE"

# 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR" || {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 오류: 프로젝트 디렉토리 이동 실패 ($PROJECT_DIR)" >> "$LOG_FILE"
  exit 1
}

# uv 경로 확인 (launchd 환경은 PATH가 최소화되어 있어 명시적 확인 필요)
if [ ! -x "$UV_BIN" ]; then
  UV_BIN="$(command -v uv 2>/dev/null)"
fi
if [ -z "$UV_BIN" ] || [ ! -x "$UV_BIN" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 오류: uv 실행 파일을 찾을 수 없습니다 ($UV_BIN)" >> "$LOG_FILE"
  exit 1
fi

# 1. 일간 분석 리포트 및 JSON 대시보드 데이터 생성 실행 (최신 Orchestrator)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 일간 리포트 및 JSON 데이터 통합 생성 중..." >> "$LOG_FILE"
"$UV_BIN" run python main.py --daily >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 실행 결과 로그
if [ $EXIT_CODE -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 성공" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 실패 (종료 코드: $EXIT_CODE)" >> "$LOG_FILE"
fi

{
  echo "========================================"
  echo ""
} >> "$LOG_FILE"

exit $EXIT_CODE
