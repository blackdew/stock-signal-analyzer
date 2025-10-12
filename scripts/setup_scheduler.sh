#!/bin/bash
# 주식 신호 분석 스케줄러 설치 스크립트

set -e  # 오류 발생 시 즉시 종료

PROJECT_DIR="/Users/sookbunlee/work/trading"
PLIST_FILE="$PROJECT_DIR/launchd/com.trading.stock-signals.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
DEST_PLIST="$LAUNCH_AGENTS_DIR/com.trading.stock-signals.plist"

echo "========================================="
echo "주식 신호 분석 스케줄러 설치"
echo "========================================="
echo ""

# LaunchAgents 디렉토리 확인 및 생성
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    echo "LaunchAgents 디렉토리 생성 중..."
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# 기존 서비스가 실행 중이면 중지
if launchctl list | grep -q "com.trading.stock-signals"; then
    echo "기존 서비스 중지 중..."
    launchctl unload "$DEST_PLIST" 2>/dev/null || true
fi

# plist 파일 복사
echo "plist 파일 복사 중..."
cp "$PLIST_FILE" "$DEST_PLIST"

# 권한 설정
echo "권한 설정 중..."
chmod 644 "$DEST_PLIST"
chmod +x "$PROJECT_DIR/scripts/run_scheduled_report.sh"

# 로그 디렉토리 생성
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/reports"

# launchd에 등록
echo "launchd에 서비스 등록 중..."
launchctl load "$DEST_PLIST"

echo ""
echo "========================================="
echo "설치 완료!"
echo "========================================="
echo ""
echo "스케줄: 월~금 오전 10시, 오후 2시"
echo "보고서 저장: $PROJECT_DIR/reports/"
echo "로그 파일: $PROJECT_DIR/logs/"
echo ""
echo "스케줄러 상태 확인:"
echo "  launchctl list | grep stock-signals"
echo ""
echo "스케줄러 중지:"
echo "  launchctl unload ~/Library/LaunchAgents/com.trading.stock-signals.plist"
echo ""
echo "스케줄러 재시작:"
echo "  launchctl unload ~/Library/LaunchAgents/com.trading.stock-signals.plist"
echo "  launchctl load ~/Library/LaunchAgents/com.trading.stock-signals.plist"
echo ""
echo "수동 테스트:"
echo "  $PROJECT_DIR/scripts/run_scheduled_report.sh"
echo ""
