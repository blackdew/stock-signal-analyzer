# [Bug] LLM 스코어링 경로가 인자 불일치로 항상 RubricEngine으로 폴백됨

**라벨(제안):** `bug`, `critical`, `analysis`
**관련 파일:** `src/agents/analysis/stock_analyzer.py`
**발견 경위:** 핵심 분석 로직 평가 (`docs/analysis_logic_evaluation.md`, 항목 C1)

---

## 현상 (Summary)

`use_llm=True`이고 `OPENAI_API_KEY`가 설정되어 있어도, 모든 종목 분석이 LLM 점수 대신 **RubricEngine 점수로 산출**된다. LLM이 생성한 점수와 분석 텍스트(`summary`, `financial_analysis`, `comprehensive_analysis`, `investment_thesis` 등)는 리포트에 반영되지 않는다. OpenAI API 호출은 실제로 수행되어 **비용은 발생하지만 결과는 전량 폐기**된다.

프로젝트의 핵심 기능인 "LLM 기반 점수 산출(LLMScorer)"이 사실상 비활성 상태다.

## 원인 (Root Cause)

`StockAnalyzer._analyze_single_async`가 LLM 분석 성공 후 호출하는 `_llm_result_to_analysis_result`의 **호출부 인자와 정의부 시그니처가 어긋나 있다.**

정의부 파라미터 (`self` 제외 13개):

```
llm_result, symbol, name, sector, group, market_cap, data_quality,
news_data, market_data, fundamental_data, sector_rank, sector_total, sector_return_5d
```

호출부 (`stock_analyzer.py` 518~522행):

```python
return self._llm_result_to_analysis_result(
    llm_result, symbol, name, sector, group, market_cap, data_quality, news_data,
    market_data, fundamental_data, data_bundle,        # ← 위치 인자 11개 (마지막이 data_bundle)
    sector_rank=sector_rank, sector_total=sector_total, sector_return_5d=sector_return_5d,
)
```

- 11번째 위치 인자 `data_bundle` 값이 11번째 파라미터 **`sector_rank`** 에 바인딩된다.
- 동시에 키워드 인자 `sector_rank=`가 전달되어 **`TypeError: _llm_result_to_analysis_result() got multiple values for argument 'sector_rank'`** 가 발생한다.
- 추가로, 함수 본문 773행이 `data_bundle`을 참조하지만 `data_bundle`은 파라미터 목록에 존재하지 않는다 → 호출이 성립하더라도 `NameError`가 난다. (이중으로 깨져 있음)

발생한 `TypeError`는 `_analyze_single_async`의 `except Exception as e:` (523~524행)가 잡아 `"LLM analysis failed ... falling back to RubricEngine"` 경고만 남기고, 매 종목 RubricEngine 폴백 경로로 처리된다.

> AST 정적 분석으로 호출 인자 수(위치 11 + 키워드 3)와 정의 파라미터(13)의 불일치, 본문의 `data_bundle` 미정의 참조를 확인함.

## 재현 (Reproduction)

`OPENAI_API_KEY`를 설정하고 분석을 실행하면, 로그에 모든 종목에 대해 다음 경고가 반복된다.

```
LLM analysis failed for {symbol}, falling back to RubricEngine: got multiple values for argument 'sector_rank'
```

단위 테스트로는 `tests/agents/analysis/test_stock_analyzer.py`의 `TestLLMResultConversion`이 호출부와 동일한 인자 형태로 `_llm_result_to_analysis_result`를 호출하여 이 결함을 재현/검증한다.

## 영향 (Impact)

- LLM 기반 점수·분석이 전혀 사용되지 않음 (핵심 기능 비활성).
- OpenAI API 비용은 발생하나 결과 폐기 → 비용 누수.
- 리포트의 분석 텍스트가 폴백 템플릿으로 대체됨.

## 해결 방안 (Proposed Fix)

`_llm_result_to_analysis_result` 정의에 `data_bundle` 파라미터를 호출부 위치(`fundamental_data` 다음, `sector_rank` 앞)에 추가한다.

```python
def _llm_result_to_analysis_result(
    self,
    llm_result: LLMScoreResult,
    symbol: str,
    name: str,
    sector: str,
    group: str,
    market_cap: float,
    data_quality: Optional[DataQualityResult],
    news_data: Optional[NewsData],
    market_data: Optional[MarketData] = None,
    fundamental_data: Optional[FundamentalData] = None,
    data_bundle: Optional[StockDataBundle] = None,   # ← 추가
    sector_rank: Optional[int] = None,
    sector_total: Optional[int] = None,
    sector_return_5d: Optional[float] = None,
) -> StockAnalysisResult:
```

`StockDataBundle`은 이미 `stock_analyzer.py`에 import되어 있으며, 본문 773행의 `data_bundle=data_bundle` 참조가 정상화된다.

## 검증 (Verification)

1. `tests/agents/analysis/test_stock_analyzer.py::TestLLMResultConversion` 추가 (수정 전 실패 → 수정 후 통과).
2. `uv run pytest` 전체 통과 확인.
3. `OPENAI_API_KEY` 설정 후 분석 실행 시 `"falling back to RubricEngine"` 경고가 사라지고 `is_fallback=False` 결과가 산출되는지 확인.

## 후속 (Follow-up)

이 수정으로 LLM 경로가 처음으로 실제 가동되므로, 평가 리포트의 다음 항목이 곧바로 영향권에 든다 (별도 이슈 권장):

- **H1**: LLM 프롬프트와 RubricEngine V3의 카테고리 정의 불일치
- **H5**: LLM 응답의 카테고리 점수 범위·총점 정합성 미검증
- **M4**: LLM 점수와 RubricEngine 세부내역의 출처 불일치
