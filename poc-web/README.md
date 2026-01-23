<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Stock Signal Analyzer - Web PoC

섹터 순환 투자 전략 분석 시스템의 프론트엔드 PoC입니다.
Python 백엔드 API와 연동하여 분석 결과를 시각화합니다.

View your app in AI Studio: https://ai.studio/apps/drive/1bzz1rFZEqYcYDxOcOC41rOv5GlNiYmIc

## Run Locally

**Prerequisites:**
- Node.js
- Python 백엔드 서버 실행 필요 (`uv run python main.py --web`)

### 1. 환경 변수 설정

`.env.example`을 복사하여 `.env.local` 파일을 생성합니다:

```bash
cp .env.example .env.local
```

환경 변수:
- `VITE_API_URL`: Python 백엔드 API URL (기본값: `http://localhost:8000`)
- `GEMINI_API_KEY`: Gemini API 키 (채팅 기능에 필요)

### 2. 의존성 설치 및 실행

```bash
npm install
npm run dev
```

### 3. 백엔드 서버 실행

프론트엔드가 분석 결과를 가져오려면 백엔드 API 서버가 실행 중이어야 합니다:

```bash
# 프로젝트 루트에서 실행
uv run python main.py --web
```

## API 연동

### apiService.ts

Python 백엔드 API와 통신하는 서비스입니다. 주요 함수:

- `getLatestAnalysis()`: 최신 분석 결과 조회
- `runAnalysis()`: 분석 비동기 실행
- `getAnalysisTaskStatus()`: 분석 태스크 상태 조회
- `pollAnalysisTask()`: 분석 완료까지 폴링
- `getRanking()`: Top 18, Top 5 순위 조회
- `getSectors()`: 섹터 목록 조회
- `getStockDetail()`: 특정 종목 상세 정보 조회
- `getTopStocks()`: 상위 N개 종목 조회

### geminiService.ts

Gemini API를 사용한 채팅 기능을 제공합니다.
