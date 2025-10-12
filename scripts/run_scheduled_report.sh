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

# uv를 사용하여 main.py 실행 (--scheduled 옵션 사용)
/Users/sookbunlee/.local/bin/uv run main.py --scheduled >> "$LOG_FILE" 2>&1

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
