# 핵심 분석 로직 평가 리포트

작성일: 2026-05-24
평가 범위: 점수·등급 산출의 핵심 분석 로직
대상 파일: `src/core/rubric.py`, `src/core/llm_scorer.py`, `src/core/prompts/`, `src/agents/analysis/{stock_analyzer,sector_analyzer,ranking_agent,data_quality}.py`, `src/agents/data/data_bundle.py`, `src/core/config.py`

---

## 1. 요약 (Executive Summary)

핵심 분석 로직은 구조가 명확하고 모듈 분리가 잘 되어 있으나, **V2 → V3 마이그레이션 과정에서 생긴 정합성 결함**이 여러 곳에 남아 있습니다. 그중 하나는 시스템의 핵심 설계 의도를 무력화하는 수준입니다.

가장 중요한 발견은 **LLM 스코어링 경로가 실제로는 동작하지 않는다**는 점입니다. `StockAnalyzer._llm_result_to_analysis_result`의 호출부와 정의부 인자가 어긋나 있어, LLM 분석이 성공해도 결과를 변환하는 단계에서 `TypeError`가 발생하고, 예외 처리에 의해 매번 조용히 RubricEngine으로 폴백합니다. 즉 `use_llm=True`이고 API 키가 있어도 시스템은 항상 룰 기반(RubricEngine V3) 점수만 사용하며, OpenAI 호출 비용은 발생하지만 그 결과(점수·분석 텍스트)는 전량 폐기됩니다.

그 외에 거래대금 점수가 항상 상수로 고정되는 버그, V3 전환 시 누락된 점수 스케일 보정, 두 스코어링 엔진(LLM 프롬프트 vs RubricEngine)의 카테고리 정의 불일치 등이 점수의 신뢰도를 떨어뜨리고 있습니다.

심각도별 집계: **Critical 1건, High 5건, Medium 9건, Low 7건.**

> 참고: 이 리포트는 코드 정독과 AST 정적 분석에 기반합니다. 샌드박스 환경에 Python 3.12가 없어 `pytest` 실행으로는 검증하지 못했습니다. 각 항목의 "검증 상태"를 함께 표기했으며, 수정 착수 전 CLAUDE.md의 버그 수정 규칙(실패 테스트 선작성 → `uv run pytest`)을 따를 것을 전제로 합니다.

---

## 2. 강점

평가 과정에서 확인한, 유지·강화할 가치가 있는 부분입니다.

- **모듈 경계가 깔끔함**: 데이터 수집(agents/data) → 점수 산출(rubric/llm_scorer) → 분석(agents/analysis) → 리포트(agents/report)의 단방향 의존이 잘 지켜집니다.
- **폴백 설계 자체는 견고함**: LLM 실패 시 RubricEngine으로 떨어지고, `is_fallback`/`fallback_reason`으로 추적합니다. 폴백 비율이 50% 이상이면 에러 로그를 남기는 등 관측 장치가 있습니다. (다만 아래 C1 때문에 이 폴백이 "예외 상황"이 아니라 "상시 경로"가 되어 버린 점이 문제입니다.)
- **점수 기준표가 명시적**: `rubric.py`의 `calc_*` 함수와 프롬프트의 기준표가 구간별로 문서화되어 있어 점수의 근거를 추적하기 쉽습니다.
- **데이터 품질 검증의 분리**: `DataQualityValidator`가 점수 로직과 독립적으로 필수/권장 항목을 검증하고 `--strict` 게이트를 제공합니다.
- **캐싱 계층**: LLM 점수·섹터 결과에 24시간 TTL 캐시가 적용되어 재실행 비용을 줄입니다.

---

## 3. 발견된 문제

심각도: **Critical**(설계 의도 무력화/비용 누수) · **High**(점수 신뢰도 직접 훼손) · **Medium**(정확도·성능·일관성 저하) · **Low**(유지보수성).

### 3.1 Critical

#### C1. LLM 스코어링 경로가 완전히 단절되어 있음

- **위치**: `src/agents/analysis/stock_analyzer.py` — 호출부 518~522행, 정의부 640~654행, 본문 773행
- **검증 상태**: AST 정적 분석으로 확인 (호출 인자 ≠ 정의 인자), 런타임 재현 테스트는 미실행
- **내용**:
  - `_llm_result_to_analysis_result`의 정의 파라미터는 `self` 제외 13개입니다: `llm_result, symbol, name, sector, group, market_cap, data_quality, news_data, market_data, fundamental_data, sector_rank, sector_total, sector_return_5d`.
  - 호출부는 위치 인자 11개(마지막이 `data_bundle`)와 키워드 인자 3개(`sector_rank`, `sector_total`, `sector_return_5d`)를 전달합니다.
  - 11번째 위치 인자 `data_bundle` 값이 11번째 파라미터 `sector_rank`에 바인딩되고, 동시에 키워드 `sector_rank=`가 또 전달되어 **`TypeError: got multiple values for argument 'sector_rank'`**가 발생합니다.
  - 더해서, 함수 본문 773행은 `data_bundle`을 참조하지만 `data_bundle`은 파라미터 목록에 없어 호출이 성립하더라도 **`NameError`**가 납니다. (즉 이중으로 깨져 있음)
- **영향**:
  - `analyze_stock`(OpenAI 호출)은 정상 수행되어 **API 비용은 발생**하지만, 직후 변환에서 예외가 나고 524행 `except`가 이를 잡아 "LLM analysis failed, falling back to RubricEngine"으로 처리합니다.
  - 결과적으로 `use_llm=True` + API 키 설정 상태에서도 **모든 종목이 RubricEngine V3 점수로 산출**됩니다. LLM이 생성한 점수와 분석 텍스트(`summary`, `financial_analysis`, `comprehensive_analysis`, `investment_thesis` 등)는 전량 버려지고, 리포트에는 폴백 템플릿 텍스트가 들어갑니다.
  - 프로젝트의 핵심 기능("LLM 기반 점수 산출")이 사실상 비활성 상태입니다.
- **권고**: 최우선 수정. 단, CLAUDE.md 규칙대로 **먼저 이 호출을 재현하는 실패 테스트**(예: `_llm_result_to_analysis_result`에 현재 호출 시그니처로 인자를 넘겨 `TypeError` 발생을 확인)를 작성한 뒤, 정의에 `data_bundle` 파라미터를 추가하고 호출 인자 순서를 시그니처에 맞게 정렬합니다. 수정 후 LLM 경로가 살아나면 아래 H1·H5가 즉시 영향권에 들어오므로 함께 다뤄야 합니다.

### 3.2 High

#### H1. 두 스코어링 엔진의 "V3 8대 루브릭" 정의가 서로 다름

- **위치**: `src/core/prompts/stock_analysis.py`(LLM 기준표) vs `src/core/rubric.py` `_calculate_v3`(룰 기준)
- **검증 상태**: 양쪽 코드 정독으로 확인
- **내용**: 같은 "V3 8대 루브릭"이라는 이름을 쓰지만 8개 중 4개 카테고리의 내부 구성이 다릅니다.

  | 카테고리 | LLM 프롬프트 | RubricEngine V3 | 불일치 |
  |---|---|---|---|
  | 밸류에이션(20) | PER 10 + PBR 10 | PER 10 + PBR 10 | 일치 |
  | 펀더멘털(15) | ROE 6 + 성장률 6 + 부채 3 | ROE 5 + 성장률 6 + 부채 4 | 세부 가중치 상이 |
  | 수급(15) | 외국인 6 + 기관 6 + **거래대금 3** | 외국인 7.5 + 기관 7.5 | 거래대금 위치/구조 상이 |
  | 모멘텀(15) | RSI 5 + MACD 5 + **20일수익률 5** | RSI 5 + MACD 5 + **거래대금 5** | 3번째 지표가 완전히 다름 |
  | 기술적(10) | 추세 5 + 52주위치 5 | 추세 4 + 52주위치 3 + **ADX 3** | ADX 포함 여부 상이 |
  | 섹터(10) | 모멘텀 5 + 순위 5 | 순위 5 + 모멘텀 5 | 일치 |
  | 리스크(10) | 변동성 4 + 베타 3 + 낙폭 3 | 동일 | 일치 |
  | 주주환원(5) | 배당 5 | 배당 5 | 일치 |

- **특히 심각한 부분**: 20일 수익률(`return_20d`)은 LLM 프롬프트에서 모멘텀의 1/3(5점)을 차지하지만, RubricEngine V3에서는 가중치 0짜리 호환용 `relative_strength` 필드에만 쓰여 **총점에 전혀 반영되지 않습니다**. 같은 지표를 한쪽 엔진은 핵심 점수로, 다른 쪽은 무시합니다.
- **영향**: LLM 경로(C1 수정 후)와 폴백 경로가 산출하는 카테고리 점수가 구조적으로 비교 불가능합니다. 또한 `to_dict()`의 V2 호환 필드 복사 로직이 이 정렬을 암묵적으로 가정하고 있어, 리포트의 세부 점수가 잘못 짝지어질 수 있습니다.
- **권고**: "V3 루브릭"을 **단일 사양 문서(SSOT)**로 정의하고, 프롬프트 기준표와 `_calculate_v3`가 그 사양을 똑같이 따르도록 통일합니다.

#### H2. 거래대금 점수가 항상 상수(2.5/5)로 고정됨

- **위치**: `src/core/rubric.py` 805행(`avg_trading_value = None` 하드코딩), 810행, 1248행(`calc_trading_value_score(trading_value, None)`)
- **검증 상태**: 코드 정독으로 확인
- **내용**: `calc_trading_value_score`는 `avg_trading_value`가 `None`이면 무조건 중간값 2.5를 반환합니다. 그런데 호출부가 항상 `avg_trading_value=None`을 넘기므로(`_calculate_supply`는 주석으로 "MarketData에 avg_trading_value가 없음"이라 명시), **거래대금 세부 점수는 모든 종목에서 항상 2.5**입니다.
- **영향**: V2 수급의 거래대금 축(5점), V3 모멘텀의 거래대금 축(5점)이 변별력 0인 죽은 지표입니다. V3 모멘텀은 사실상 RSI + MACD + 상수로 동작합니다.
- **권고**: `MarketData`에 `avg_trading_value_20d`(20일 평균 거래대금)를 추가 수집하거나, 이미 있는 `avg_volume_20d × 현재가`로 근사 계산하여 실제 비율이 점수에 반영되도록 합니다.

#### H3. 누락 데이터를 "중간값"으로 채우는 방식이 순위를 왜곡함

- **위치**: `rubric.py`의 모든 `calc_*` 함수(데이터 `None` 시 만점의 50% 반환), 프롬프트 23행("N/A이면 만점의 50%")
- **검증 상태**: 코드·프롬프트 정독으로 확인
- **내용**: 모든 세부 점수가 데이터 부재 시 중간값을 반환합니다. 절대 점수 산출에서는 "중립"으로 보일 수 있으나, **종목 간 순위를 매기는 맥락에서는 중립이 아닙니다**. 실제 점수 분포의 중앙값이 만점의 50%가 아닌 항목이 많기 때문입니다. 예를 들어 `calc_rsi_score`는 양호한 구간에서 8~10점을 주는데 누락 시 5점을 줍니다. 그 결과 **데이터가 누락된 종목이, 펀더멘털이 나쁘지만 데이터가 있는 종목보다 더 높게 점수화**될 수 있습니다. 시스템이 데이터 공백을 보상하는 셈입니다.
- **영향**: 데이터 수집이 부실한 종목(주로 중소형주)이 부당하게 상위 랭크로 올라올 수 있습니다. `final_18`/`Top 5` 선정 신뢰도에 직접 영향.
- **권고**: (1) 누락 항목은 점수에서 제외하고 **존재하는 항목만으로 카테고리 점수를 재정규화**하거나, (2) 누락에 소폭의 페널티(예: 만점의 40%)를 주고, (3) `DataQualityResult.quality_score`를 최종 점수의 신뢰도 지표로 리포트에 노출합니다.

#### H4. `select_final_top5`의 점수 스케일이 V2 기준에 멈춰 있음

- **위치**: `src/agents/analysis/ranking_agent.py` 262~263행
- **검증 상태**: 코드 정독으로 확인
- **내용**: Top 5 선정 공식에서 `supply_normalized = stock.supply_score * 5`, `fundamental_normalized = stock.fundamental_score * 5`를 쓰고 주석에 "20점 → 100점"이라 적혀 있습니다. 이는 V2 가중치(수급 20, 펀더멘털 20) 기준입니다. 그러나 **V3에서 수급·펀더멘털의 만점은 각각 15점**이므로, `× 5`는 0~75점으로만 환산됩니다(0~100이 아님).
- **영향**: Top 5 가중식이 의도한 "수급 15% / 성장성 15%"가 실제로는 약 11.25%씩으로 축소됩니다. 총점 비중이 상대적으로 과대평가되어 선정 결과가 의도와 다르게 나옵니다.
- **권고**: V3 만점에 맞춰 `× (100/15)`로 환산하거나, 더 견고하게 `rubric_result`의 각 카테고리 `score`(이미 0~100 정규화 값)를 직접 사용합니다.

#### H5. LLM 응답 검증이 점수 범위·정합성을 확인하지 않음

- **위치**: `src/core/prompts/schemas.py` `validate_stock_score` 210~252행, `src/core/llm_scorer.py` 429행
- **검증 상태**: 코드 정독으로 확인
- **내용**: `validate_stock_score`는 필드 존재 여부, `total_score`의 0~100 범위, `grade` enum만 확인합니다. **카테고리별 점수의 상한(밸류에이션 0~20 등)은 검사하지 않으며**(`STOCK_SCORE_SCHEMA` 딕셔너리에 min/max가 정의돼 있지만 검증 함수가 이를 사용하지 않음), **카테고리 합 = 총점 정합성도 확인하지 않습니다**. 또 `total_score`와 `grade`는 LLM이 자체 산출한 값을 그대로 신뢰합니다(`data.get("total_score")`, `data.get("grade")`).
- **영향**: LLM이 `valuation.score = 95`(상한 20 초과)를 반환하거나, 카테고리 합이 73인데 `total_score=88`, `grade`는 그와 모순되게 반환해도 모두 통과합니다. LLM은 산술에 약하므로 실제로 자주 발생합니다. C1이 수정되어 LLM 경로가 살아나는 순간 이 결함이 점수 신뢰도에 직접 타격을 줍니다.
- **권고**: (1) `jsonschema`로 `STOCK_SCORE_SCHEMA`를 실제 적용하거나 카테고리 상한을 명시 검사, (2) **`total_score`는 코드에서 카테고리 합으로 재계산**, (3) **`grade`는 `get_grade_from_score`로 코드에서 도출**하여 LLM 자체 값은 버립니다.

### 3.3 Medium

#### M1. LLM 호출에 재시도/백오프가 없음

- **위치**: `llm_scorer.py` 282~293행
- 일시적 오류(429 rate limit, 타임아웃)도 1회 실패 즉시 50점/Hold 폴백으로 처리됩니다. 일배치(수십 종목)에서 레이트리밋이 걸리면 다수 종목이 조용히 "Hold"로 강등됩니다. 지수 백오프 재시도(2~3회)를 권고합니다.

#### M2. 종목 분석 루프가 순차 실행

- **위치**: `stock_analyzer.py` 415~456행
- `analyze_symbols`가 `for symbol ...: await self._analyze_single_async(...)`로 종목을 한 건씩 직렬 처리합니다. `asyncio.gather`(동시성 제한 세마포어 포함)로 묶으면 일배치 시간이 크게 단축됩니다.

#### M3. 시가총액 조회가 중복 호출됨

- **위치**: `stock_analyzer.py` — `_calculate_sector_ranks`(922행), `_calculate_sector_return_5d`(948행), `analyze_symbols`(405행)가 각각 `_get_market_caps`를 호출
- 섹터 1개 분석에 시가총액 크롤이 3회 발생하고, 13개 섹터면 39회입니다. 또 삼성전자 등은 KOSPI 그룹과 섹터 그룹에서 **이중 분석**되어 크롤·LLM 비용이 2배가 됩니다. 호출 결과를 분석 1회 범위에서 메모이즈하고, 종목 중복 분석을 제거할 것을 권고합니다.

#### M4. LLM 성공 시 표시 점수와 세부 내역의 출처가 다름

- **위치**: `stock_analyzer.py` 736~774행
- LLM 경로가 살아나면, 표시 점수는 LLM가 산출하지만 `to_dict()`의 세부 내역(`technical_details` 등)은 별도로 계산한 `rubric_result`에서 가져옵니다. 사용자는 LLM 점수와 RubricEngine 세부 합계가 어긋난 리포트를 보게 됩니다. 한 출처로 통일해야 합니다.

#### M5. 섹터 카테고리 입력이 LLM 프롬프트에 빠져 있음

- **위치**: `data_bundle.py` `to_prompt_context`
- 프롬프트는 LLM에게 "섹터 내 순위(5점)"와 "섹터 모멘텀(5점)"을 채점하라고 요구하지만, `to_prompt_context`는 `sector_rank`/`sector_total`/`sector_return_5d`를 컨텍스트에 포함하지 않습니다. LLM은 데이터 없이 추정(환각)하게 됩니다. 해당 값을 프롬프트 컨텍스트에 추가해야 합니다.

#### M6. 섹터 점수가 1~2개 메가캡에 지배됨

- **위치**: `sector_analyzer.py` 204~224행
- 섹터 점수는 시가총액 가중 평균이라 반도체는 삼성전자·SK하이닉스가, 자동차는 현대차·기아가 점수를 사실상 결정합니다. 섹터 내 8개 중소형주는 거의 영향이 없습니다. "섹터 순환 투자 기회"를 보려는 목적과 상충할 수 있으므로, 가중 평균과 단순 평균을 함께 노출하거나 상한 가중(capped weight)을 도입하는 방안을 검토할 것을 권고합니다.

#### M7. `round(x, n) if x else None` 패턴이 합법적 0 값을 버림

- **위치**: `rubric.py` 다수 (예: 748·752·904·1269행 등)
- `if x`는 `0.0`도 거짓으로 처리합니다. 영업이익 성장률 0%(정체)나 MACD 0.0 같은 **유효한 0 값이 `None`(N/A)으로 표시**됩니다. `if x is not None`으로 바꿔야 합니다.

#### M8. 외국인/기관 수급 점수가 금액 규모를 무시함

- **위치**: `rubric.py` `calc_foreign_score`/`calc_institution_score`
- 누적 금액은 부호(양/음)만 봅니다. +1억 순매수와 +1조 순매수가 동일 점수입니다. 시가총액 대비 또는 거래대금 대비로 정규화하면 변별력이 올라갑니다.

#### M9. 연속 순매수 일수 계산이 리스트 정렬 순서에 의존

- **위치**: `rubric.py` 820~834·1213~1226행, `data_bundle.py` 133~145행 (3곳 중복)
- `for amount in net: if >0 count else break`는 리스트 인덱스 0부터 셉니다. `foreign_net_buy`가 과거→최신 순이면 이 코드는 "최근 연속 순매수"가 아니라 "5일 전부터의 연속"을 셉니다. `market_data_agent.py`의 리스트 정렬 순서를 확인해야 하며, 최신→과거가 아니라면 버그입니다. (이번 평가 범위 밖이라 미확인 — **검증 필요**)

### 3.4 Low

- **L1.** `calc_foreign_score`와 `calc_institution_score`가 완전히 동일한 코드입니다. 하나의 함수로 통합 가능.
- **L2.** V2 `_calculate_technical`의 "비율 환산"(0-10 → 6/6/6/4/3)은 선형 재척도라 최종 결과에 영향이 없습니다. 불필요한 복잡성으로, V3로 일원화 시 정리 대상.
- **L3.** `DataQualityValidator`가 `market_data.market_cap`으로 시가총액 필수 항목을 검사하는데, 시가총액은 별도로 `_get_market_caps`에서 조회됩니다. `MarketData.market_cap`이 항상 비어 있으면 전 종목이 `is_valid=False`가 되고 `--strict`가 항상 중단됩니다. (**검증 필요** — `market_data_agent.py` 미확인)
- **L4.** `_create_default_result`의 `total_score=50.0`이 카테고리 기본값과 별개로 하드코딩되어 있어, 카테고리 기본값 변경 시 동기화가 깨질 수 있습니다. 합산으로 도출하도록 권고.
- **L5.** `CLAUDE.md`는 V2(6개 카테고리) 기준으로 작성돼 있으나 실제 코드는 V3(8개 카테고리)가 기본입니다. 문서 최신화 필요.
- **L6.** `_analyze_single_async`가 LLM 미사용 시 호출하는 RubricEngine 폴백(527~530행)에 `sector_rank`/`sector_total`/`sector_return_5d`를 전달하지 않아, 동기 경로(`_analyze_single`)와 달리 섹터 점수가 중간값으로 떨어집니다.
- **L7.** `calc_per_score`는 PER 음수(적자) 시 0점을 줍니다. 적자 성장주(바이오·로봇 다수)에 과한 페널티이며, 펀더멘털의 성장률 항목과 이중 계상 소지가 있습니다. 적자 기업은 PBR/성장률 위주로 평가하는 분기 처리를 검토.

---

## 4. 개선안 (우선순위별 로드맵)

각 단계는 CLAUDE.md 버그 수정 규칙(① 실패 테스트 선작성 → ② 수정 → ③ `uv run pytest` 검증 → ④ git history 확인)을 준수합니다.

### Phase 1 — 즉시 (점수가 틀리거나 기능이 죽은 항목)

1. **C1 LLM 경로 복구** — 재현 테스트 작성 후 `_llm_result_to_analysis_result` 시그니처에 `data_bundle` 추가, 호출 인자 정렬. 수정 후 LLM 경로가 실제로 점수를 생성하는지 통합 테스트로 확인.
2. **H4 Top 5 스케일 보정** — `× 5` → V3 만점 기준 환산 또는 `rubric_result` 카테고리 `score` 직접 사용.
3. **H2 거래대금 지표 활성화** — 평균 거래대금 수집/근사 추가.
4. **M7 `if x` → `if x is not None`** — 0 값 손실 제거 (저비용, 광범위).

### Phase 2 — 점수 정합성 (C1 수정으로 LLM 경로가 살아난 직후 필수)

5. **H1 V3 루브릭 사양 통일** — 단일 사양 문서를 만들고 프롬프트 기준표와 `_calculate_v3`를 동일 구조로 맞춤.
6. **H5 LLM 응답 검증 강화** — 카테고리 상한 검사, 총점은 카테고리 합으로 재계산, 등급은 코드로 도출.
7. **H3 누락 데이터 처리 재설계** — 존재 항목만으로 재정규화 + 신뢰도 지표 리포트 노출.
8. **M4 점수/세부내역 출처 일원화.**

### Phase 3 — 견고성·성능

9. **M1 LLM 재시도/백오프 도입.**
10. **M2 종목 분석 병렬화**(세마포어로 동시성 제한).
11. **M3 시가총액 조회 메모이즈 + 종목 중복 분석 제거.**
12. **M5 섹터 입력을 LLM 프롬프트 컨텍스트에 추가.**
13. **M9 / L3 검증** — `market_data_agent.py`를 확인해 수급 리스트 정렬 순서와 `MarketData.market_cap` 채움 여부를 점검(필요 시 실패 테스트 후 수정).

### Phase 4 — 정성적 강화 (선택)

14. **M6 섹터 점수 설계 개선** — 단순/가중 평균 병기 또는 상한 가중.
15. **M8 수급 점수의 금액 정규화.**
16. **L1·L2·L4·L7 리팩터링**, **L5 문서 최신화**.
17. **백테스트 기반 가중치 검증** — 현재 가중치(밸류 20·펀더 15·수급 15…)와 구간 임계값은 경험적으로 설정된 값입니다. 과거 데이터로 점수와 후행 수익률의 상관을 측정해 가중치를 보정하는 절차를 추가하면 루브릭의 근거가 강화됩니다.

---

## 5. 검증 권고

- **이번 평가에서 확인하지 못한 항목**: 샌드박스에 Python 3.12가 없어 `pytest`를 실행하지 못했습니다. C1은 AST 정적 분석으로 확정했으나, "항상 폴백된다"는 런타임 동작과 M9·L3는 실행 검증이 필요합니다.
- **수정 착수 시**: 항목별로 먼저 실패 테스트를 작성해 결함을 재현하고, 수정 후 `uv run pytest` 전체(279개)가 통과하는지 확인하십시오. 특히 C1 수정은 LLM 경로를 처음으로 실제 가동시키므로 회귀 영향이 큽니다.
- **우선 점검 파일**: `src/agents/data/market_data_agent.py`(M9·L3·H2의 데이터 구조 확인), `src/agents/report/`(C1 수정 후 LLM 텍스트가 리포트에 제대로 반영되는지).

---

*이 리포트는 코드 품질 평가 목적이며, 산출되는 투자 점수·등급은 참고용입니다. 실제 투자 결정은 사용자 본인의 판단에 따라야 합니다.*
