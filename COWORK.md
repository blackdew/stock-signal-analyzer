# COWORK.md

이 파일은 **Cowork 모드**(Claude 데스크톱 앱)가 이 프로젝트에서 작업할 때 참고하는 지침입니다.
코드 구조·모듈 상세는 `CLAUDE.md`에 정리되어 있으며, 이 문서는 그 위에서 **Cowork가 어떤 역할로 무엇을 도와야 하는지**를 정의합니다.

---

## 1. 프로젝트 한 줄 요약

**섹터 순환 투자 전략 분석 시스템** — 한국 주식 시장의 13개 섹터를 분석해 루브릭 기반 점수와 투자 등급(Strong Buy ~ Strong Sell)을 산출하는 Python 애플리케이션입니다.

- 데이터 수집(네이버 금융·OpenDART) → 분석 에이전트 → 루브릭/LLM 스코어링 → 마크다운·JSON 리포트 생성
- FastAPI 기반 웹 API와 React 프론트엔드(`poc-web/`) 포함
- 코드·모듈·API·캐시 정책 등 기술 상세는 모두 `CLAUDE.md` 참조

---

## 2. Cowork의 역할 vs. Claude Code의 역할

이 저장소에는 세 개의 에이전트 가이드가 있습니다. 역할을 혼동하지 마세요.

| 파일 | 대상 | 역할 |
|------|------|------|
| `CLAUDE.md` | Claude Code (터미널) | 코드 작성·수정·테스트 시 따르는 기술 가이드 |
| `AGENTS.md` | Codex | `CLAUDE.md`와 거의 동일한 내용의 Codex용 미러 |
| `COWORK.md` | **Cowork (이 문서)** | 운영·산출물·자동화 중심 작업 지침 |

**Cowork가 주력해야 하는 일** — 비개발/운영 성격의 작업:

- 분석 실행과 리포트 생성·검토·요약
- 리포트를 사용자용 산출물(docx/pptx/xlsx/pdf)로 재가공
- 정기 작업 스케줄링, 결과 모니터링, 상태 점검
- 데이터·로그 확인 및 이상 징후 보고

**코드를 직접 수정할 때**는 반드시 `CLAUDE.md`의 규칙을 그대로 따릅니다(특히 4번 항목). Cowork라고 해서 코드 규칙이 느슨해지지 않습니다.

---

## 3. Cowork가 자주 도울 작업과 실행 방법

모든 명령은 프로젝트 루트에서 `uv`로 실행합니다. (패키지 매니저는 `uv` 고정 — `pip` 직접 사용 금지)

### 분석·리포트 실행
```bash
uv run python main.py --daily       # 일간 리포트 (기본값)
uv run python main.py --weekly      # 주간 섹터 리포트
uv run python main.py --sector-only # 섹터 분석만
uv run python main.py --strict      # 데이터 품질 미달 시 중단
uv run python main.py --no-cache -v # 캐시 없이 상세 로그
```
유효한 모드 인자는 `--daily` / `--weekly` / `--web` **세 가지뿐**입니다. 그 외 보조 인자: `--port`, `--host`, `--sector-only`, `--group`, `--format`, `--no-cache`, `--no-news`, `-v`, `-o`, `--strict`.

### 웹 서버
```bash
uv run python main.py --web                 # http://localhost:8000
uv run python main.py --web --port 8080     # 커스텀 포트
```
API 문서는 `http://localhost:8000/docs`(Swagger), 프론트엔드 빌드는 `./scripts/build_frontend.sh`.

### 리포트 산출물 위치
- 일간: `output/reports/daily/YYYY-MM-DD/` — `01_sector_report.md`, `02_stocks/`, `03_final_report.md`
- 주간: `output/reports/weekly/YYYY-WXX/sector_report.md`
- JSON 데이터: `output/data/analysis_{날짜}.json`

리포트를 검토·요약하거나 사용자용 문서로 재가공할 때는 위 경로의 최신 결과물을 읽어 사용합니다.

### LLM 분석
`OPENAI_API_KEY`(GPT-4o-mini)가 있으면 LLM 기반 점수·분석을, 없으면 `RubricEngine`으로 폴백합니다. 키 부재나 할당량 초과로 폴백된 결과는 `is_fallback` 플래그로 표시되므로, 리포트 요약 시 폴백 여부를 함께 확인하고 사용자에게 알립니다.

---

## 4. 코드 작업 시 반드시 지킬 규칙

`CLAUDE.md`의 "버그 수정 규칙"을 Cowork에서도 그대로 적용합니다.

- 수정 전 **실패하는 테스트를 먼저 작성**해 버그를 재현할 것
- 수정 완료를 주장하기 전 반드시 **`uv run pytest`** 를 실행해 검증할 것
- **git history를 먼저 확인**(`git log`, `git diff`)해 regression 여부를 판단할 것
- 테스트를 **절대 skip 처리하지 말 것** — 실행이 안 되면 원인을 보고하고 지시를 요청할 것
- `.py` 파일을 Edit/Write 하면 PostToolUse 훅이 자동으로 `py_compile` 문법 검증을 실행함 — 훅 오류가 나면 문법부터 고칠 것
- 새 모듈 추가 후에는 `uv run python -c "from src.모듈 import 클래스; print('OK')"` 로 import 테스트

현재 작업 브랜치는 `feature/enhanced-report-ui`입니다. 커밋·푸시는 사용자가 명시적으로 요청할 때만 수행합니다.

---

## 5. 작업 환경·관례

- **언어**: 리포트·문서·커밋 메시지·사용자 응답은 한국어로 작성
- **패키지 관리**: `uv` 사용 (`uv add`, `uv remove`, `uv sync`, `uv run`)
- **출력물**: 분석 결과는 `output/` 아래, Cowork가 따로 만든 사용자용 문서는 작업 폴더 루트에 저장하고 링크 제공
- **민감 정보**: `.env`(OPENDART/OpenAI 키)는 출력·커밋·로그에 노출하지 말 것
- **면책**: 이 시스템은 투자 참고용입니다. 리포트나 요약을 전달할 때 "투자 판단은 본인 책임"이라는 점을 유지하고, 단정적 매수·매도 권유로 표현하지 말 것

---

## 6. 알려진 이슈 (Known Issues)

> ⚠️ **launchd 자동 스케줄러가 고장난 상태입니다 (미수정).**
>
> - **증상**: 마지막 정상 일간 리포트는 `output/reports/daily/2026-01-31`. 이후 스케줄러 로그(`logs/scheduler_*.log`)는 2026-05-22까지 전부 실패로 남아 있습니다.
> - **원인 1**: `scripts/run_scheduled_report.sh`가 `main.py --scheduled`를 호출하지만, `main.py`에 `--scheduled` 인자가 없습니다(유효 모드는 `--daily`/`--weekly`/`--web`).
> - **원인 2**: 같은 스크립트의 인라인 Python과 `scripts/performance_test.py`가 리팩터링 **이전 구(舊) 아키텍처**(`src.analysis.analyzer`, `src.report.json_generator`, `src.portfolio.loader`, `config.STOCK_SYMBOLS` 등)를 참조합니다. 현재 구조는 `src/agents/...` 기반이라 해당 경로가 모두 존재하지 않습니다. 단순 import 경로 한 줄이 아니라 스케줄러 스크립트 전체를 현 아키텍처에 맞춰 재작성해야 합니다.
> - **스케줄 설정**: `launchd/com.trading.stock-signals.plist` — 월~금 10:00 / 14:00 실행.
> - **수정 시**: `CLAUDE.md`의 버그 수정 규칙(실패 테스트 선작성 → `uv run pytest` 검증 → git history 확인)을 따를 것. 별도 작업으로 다루며, 사용자 요청 전까지는 손대지 않습니다.

리포트가 "오래됐다"는 인상을 받으면 위 이슈를 떠올리고, 최신 리포트 날짜를 먼저 확인해 사용자에게 현황을 알립니다.

---

## 7. 빠른 점검 체크리스트

Cowork 세션 시작 시 상황 파악이 필요하면:

```bash
git status && git branch --show-current        # 작업 트리·브랜치 상태
ls -t output/reports/daily | head -3           # 최신 일간 리포트 날짜
ls -t logs/scheduler_*.log | head -1 | xargs tail -20   # 스케줄러 최근 실행 결과
uv run pytest -q                                # 테스트 통과 여부
```
