#!/bin/bash
# 프론트엔드 빌드 및 정적 파일 배포 스크립트
#
# 사용법:
#   ./scripts/build_frontend.sh
#
# 이 스크립트는 poc-web 프론트엔드를 빌드하고
# 결과물을 src/web/static/ 디렉토리로 복사합니다.

set -e  # 에러 발생 시 중단

# 스크립트 디렉토리 기준으로 프로젝트 루트 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

FRONTEND_DIR="$PROJECT_ROOT/poc-web"
STATIC_DIR="$PROJECT_ROOT/src/web/static"

echo "🔧 프론트엔드 빌드 시작..."

# poc-web 디렉토리 확인
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ 에러: $FRONTEND_DIR 디렉토리가 존재하지 않습니다."
    exit 1
fi

# node_modules 확인 및 설치
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 의존성 설치 중..."
    cd "$FRONTEND_DIR" && npm install
fi

# 빌드 실행
echo "🏗️  빌드 중..."
cd "$FRONTEND_DIR" && npm run build

# 빌드 결과 확인
if [ ! -d "$FRONTEND_DIR/dist" ]; then
    echo "❌ 에러: 빌드 실패 - dist 디렉토리가 생성되지 않았습니다."
    exit 1
fi

# 기존 static 디렉토리 정리
if [ -d "$STATIC_DIR" ]; then
    echo "🗑️  기존 정적 파일 정리 중..."
    rm -rf "$STATIC_DIR"
fi

# 빌드 결과물 복사
echo "📁 정적 파일 복사 중..."
cp -r "$FRONTEND_DIR/dist" "$STATIC_DIR"

echo "✅ 프론트엔드 빌드 완료!"
echo "   정적 파일 위치: $STATIC_DIR"
echo ""
echo "💡 웹 서버 실행:"
echo "   uv run python main.py --web"
