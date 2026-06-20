# Stock Signal Analyzer

**섹터 순환 투자 전략 분석 시스템 (Sector Rotation Investment Analyzer)**

한국 주식 시장의 13개 주요 섹터와 대표 종목들을 심층 분석하여 루브릭 기반 투자 등급과 실전 매매 가이드를 산출하는 Python 및 React 기반 풀스택 분석 시스템입니다.

---

## 🚀 프로젝트 현재 상태

| 단계 / 기능 | 상태 | 설명 |
| :--- | :---: | :--- |
| **Phase 0~6** | **완료** | 데이터 수집/캐싱, 분석 엔진, 오케스트레이터, 리포트 생성, FastAPI Web API 및 React 웹 대시보드 연동 |
| **V3 알고리즘** | **완료** | 20일 거래대금 가중치, 결측치 이중 리스케일링, V3 가중치 보정 및 동일 섹터 2개 제한 분산투자 가드 |
| **실거래 가이드** | **완료** | ATR% 변동성 및 한국 거래소 가격대별 호가 단위 규격을 준수하는 매수 밴드, 목표가, 손절선 산출 |
| **오프라인 LLM** | **완료** | OpenAI API Key 부재 시 로컬 개발 머신의 `codex` CLI를 탐지해 자동으로 폴백 구동 (비용 0원 연동 가능) |
| **CORS 및 버그픽스** | **완료** | 프론트엔드 포트 우회(3002~3005) CORS 허용, 404 라우팅 오류 해결, 히스토리 선택 렉 오류 완벽 복구 |

### 🧪 테스트 통과 현황
- **총 369개 유닛 테스트 전수 통과** (`369 passed in 3.95s` - 로컬 LLM 호출 Mocking을 통한 테스트 실행 초고속 튜닝 완비)

---

## 🛠️ 로컬 설치 및 설정 가이드 (Local Installation)

본 시스템은 패키지 매니저로 **uv**를 사용하며, 프론트엔드는 **Node.js** 환경에서 구동됩니다.

### 1. 사전 요구사항 (Prerequisites)
- **Python**: 3.12 버전 이상
- **Node.js**: 18.0 버전 이상 (npm 포함)
- **uv**: Python 고속 패키지 관리 도구
  ```bash
  # uv 설치 (macOS / Linux)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. 저장소 클론 및 패키지 설치
```bash
# 1) 저장소 복사 및 이동
git clone <repository-url>
cd trading

# 2) Python 가상환경 및 의존성 고속 설치 (uv)
uv sync

# 3) 프론트엔드 패키지 설치
cd poc-web
npm install
cd ..
```

### 3. 환경 변수 설정
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 예시를 참고하여 필요한 키를 설정합니다.

```env
# 백엔드 API 호스트 및 포트 설정
API_HOST=0.0.0.0
API_PORT=8000

# OpenAI API 키 (상세 리포트 및 요약 생성용)
# 만약 키가 비어있을 경우, 시스템 PATH의 'codex' CLI가 자동 실행되어 로컬에서 비용 없이 분석을 수행합니다.
OPENAI_API_KEY=your_openai_api_key_here

# OpenDART API 키 (선택사항 - 공시 데이터 수집용)
OPENDART_API_KEY=your_opendart_key_here
```

프론트엔드(`poc-web/.env`) 설정 예시:
```env
# 백엔드 FastAPI 서버 URL 설정
VITE_API_URL=http://localhost:8000
```

---

## 💻 실행 및 개발 가이드 (How to Run)

### 1. E2E 통합 실행 (백엔드 서버 + 프론트엔드 정적 빌드)
프론트엔드를 빌드하여 FastAPI가 직접 서빙하도록 하는 가장 가볍고 편리한 로컬 실행 방식입니다.
```bash
# 1) 프론트엔드 소스 빌드 및 백엔드 정적 경로(src/web/static)에 배포
./scripts/build_frontend.sh

# 2) 통합 웹 서버 실행
uv run python main.py --web
# 브라우저 접속 주소: http://localhost:8000
```

### 2. 개발 모드 실행 (Hot Reload 지원)
개발 및 소스 변경 사항의 실시간 반영을 원할 때는 백엔드와 프론트엔드를 독립 터미널에서 구동합니다.

* **터미널 1: 백엔드 API 서버**
  ```bash
  uv run python main.py --web
  # API Docs 주소: http://localhost:8000/docs
  ```
* **터미널 2: 프론트엔드 Vite 개발 서버 (Hot Reload)**
  ```bash
  cd poc-web
  npm run dev
  # 브라우저 접속 주소: http://localhost:3002 (CORS 3002~3005 포트 자동 대응 완료)
  ```

### 3. CLI 분석 실행 명령어
```bash
# 일간 전체 종목 분석 및 보고서 파일 드랍 (기본값)
uv run python main.py --daily

# 캐시 데이터를 무시하고 실시간 API 크롤링 강제 수행 (상세 로그 모드)
uv run python main.py --no-cache -v

# 주간 섹터 자금 흐름 리포트 생성
uv run python main.py --weekly

# 데이터 품질 검사 시 에러 발생 시 즉각 실행을 중단하는 Strict 모드
uv run python main.py --strict
```

### 4. 알고리즘 개선 성과 비교 백테스트 실행
새로운 V3 랭킹 로직과 분산투자 가드가 이전 알고리즘 대비 거둔 실제 후행 수익률과 리스크 분산 지표를 비교 분석합니다.
```bash
uv run python scripts/compare_recommendation_algorithms.py
# 상세 대조 리포트 산출 위치: docs/issues/algo_comparison_report.md
```

---

## 📈 핵심 알고리즘 V3 루브릭 가중치

시스템은 100점 만점으로 주식을 평가하며, V3에서는 자산 배분 안정성과 밸류에이션 정합성을 위해 가중치가 아래와 같이 튜닝되었습니다.

- **기술적 분석 (25점)**: 추세(6), RSI(6), 지지/저항(6), MACD(4), ADX(3)
- **수급 분석 (20점)**: 외국인 순매수(8), 기관 순매수(8), 거래대금(4)
- **펀더멘털 분석 (20점)**: PER(4), PBR(4), ROE(4), 영업이익성장률(5), 부채비율(3)
- **시장 환경 (15점)**: 뉴스 감정(7.5), 섹터 모멘텀(3.75), 애널리스트 의견(3.75)
- **리스크 평가 (10점)**: 변동성(4), 베타(3), 하방리스크(3)
- **상대 강도 (10점)**: 섹터내순위(5), 시장대비알파(5)

**분산투자 가드 (Concentration Cap)**: 동일 섹터(예: 반도체) 내 종목은 Top 5 추천 포트폴리오에 최대 **2개**까지만 선정될 수 있으며, 쏠림 현상을 차단하고 금융/자동차 등으로 리스크가 자동 분산됩니다.

---

## 📁 프로젝트 폴더 구조

```
trading/
├── src/
│   ├── core/               # 알고리즘 설정, 루브릭 엔진, 오케스트레이터, 로컬 CLI Fallback 코어
│   ├── data/               # 네이버 금융 고속 수집 및 파일 캐싱(TTL) 엔진
│   ├── agents/
│   │   ├── data/           # 데이터 수집 에이전트 (Market, Fundamental, News)
│   │   ├── analysis/       # 분석 에이전트 (Stock, Sector, Ranking)
│   │   └── report/         # 리포트 에이전트 (Stock, Sector, Weekly, Summary)
│   └── web/                # FastAPI 라우터 및 SSE 로그 스트리머
├── tests/                  # 369개 유닛 테스트
├── scripts/                # 빌드 및 백테스트/비교 분석 유틸리티 스크립트
├── docs/                   # 설계 아키텍처 및 개선 검증 보고서
├── poc-web/                # React + Vite 대시보드 소스 코드
└── pyproject.toml          # uv 패키지 의존성 파일
```

---

## ⚠️ 주의사항 및 면책
- 본 프로젝트는 기술적 분석 및 퀀트 루브릭에 의거한 참고용 투자 정보만을 제공합니다. 
- 모든 투자 결정의 최종 책임은 전적으로 투자자 본인에게 있습니다.
