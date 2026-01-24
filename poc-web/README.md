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
- `getAnalysisHistory()`: 분석 히스토리 목록 조회
- `getAnalysisByDate(date)`: 특정 날짜 분석 결과 조회
- `runAnalysis()`: 분석 비동기 실행
- `getAnalysisTaskStatus()`: 분석 태스크 상태 조회
- `pollAnalysisTask()`: 분석 완료까지 폴링
- `getRanking()`: Top 18, Top 5 순위 조회
- `getSectors()`: 섹터 목록 조회
- `getSectorDetail(sectorName)`: 특정 섹터 상세 정보 조회
- `getStockDetail(symbol)`: 특정 종목 상세 정보 조회
- `getTopStocks(n)`: 상위 N개 종목 조회
- `getStockHistory(symbol, days)`: 종목 주가 히스토리 조회 (OHLCV)
- `getStockSupply(symbol, days)`: 종목 수급 데이터 조회 (외국인/기관)

### geminiService.ts

Gemini API를 사용한 채팅 기능을 제공합니다.

## 컴포넌트 목록

### 핵심 UI 컴포넌트
- `StockCard.tsx`: 종목 카드 (점수, 등급 표시)
- `StockModal.tsx`: 종목 상세 모달 (차트 탭 포함)
- `RubricChart.tsx`: 루브릭 점수 레이더 차트 (6개 카테고리)
- `SectorBarChart.tsx`: 섹터별 점수 바 차트
- `ChatSidebar.tsx`: AI 채팅 사이드바 (Gemini 연동)

### 차트 컴포넌트
- `PriceChart.tsx`: 주가 캔들스틱 차트 (OHLCV + 이동평균선)
- `SupplyChart.tsx`: 외국인/기관 순매수 차트 (누적 그래프)
- `PriceRangeIndicator.tsx`: 52주 고저 대비 현재가 위치 표시

### 유틸리티 컴포넌트
- `Skeleton.tsx`: 로딩 스켈레톤 UI
- `ErrorState.tsx`: 에러 상태 표시 컴포넌트
