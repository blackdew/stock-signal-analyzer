"""
Stock Analyzer

개별 종목의 점수를 산출하는 분석기.
MarketDataAgent, FundamentalAgent, NewsAgent의 데이터를 기반으로
LLMScorer를 통해 점수와 분석을 생성합니다.

LLM이 사용 불가능한 경우 RubricEngine으로 폴백합니다.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.data.market_data_agent import MarketDataAgent, MarketData
from src.agents.data.fundamental_agent import FundamentalAgent, FundamentalData
from src.agents.data.news_agent import NewsAgent, NewsData
from src.agents.data.data_bundle import StockDataBundle
from src.agents.analysis.data_quality import (
    DataQualityValidator,
    DataQualityResult,
    DataQualitySummary,
)
from src.core.rubric import RubricEngine, RubricResult
from src.core.llm_scorer import LLMScorer, LLMScoreResult
from src.core.config import SECTORS, get_sector_by_symbol
from src.data.fetcher import StockDataFetcher


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class StockAnalysisResult:
    """
    개별 종목 분석 결과

    Attributes:
        symbol: 종목 코드
        name: 종목명
        sector: 섹터명
        group: 그룹명 (kospi_top10, kospi_11_20, kosdaq_top10, sector_{name})
        market_cap: 시가총액 (억원)

        rubric_result: RubricEngine의 전체 결과

        technical_score: 기술적 분석 점수
        supply_score: 수급 분석 점수
        fundamental_score: 펀더멘털 분석 점수
        market_score: 시장 환경 점수
        risk_score: 리스크 점수 (V2)
        relative_strength_score: 상대 강도 점수 (V2)

        # V3 8대 핵심 루브릭 점수
        valuation_score: 밸류에이션 점수 (V3)
        momentum_score: 모멘텀 점수 (V3)
        sector_score: 섹터 점수 (V3)
        shareholder_score: 주주환원 점수 (V3)

        total_score: 총점
        investment_grade: 투자 등급

        rank_in_group: 그룹 내 순위
        final_rank: 최종 18개에서의 순위 (선정된 경우)
    """
    symbol: str
    name: str
    sector: str
    group: str
    market_cap: float  # 억원

    # RubricEngine 결과
    rubric_result: Optional[RubricResult] = None

    # 점수 (100점 만점 기준 환산) - V2 기본 카테고리
    technical_score: float = 0.0
    supply_score: float = 0.0
    fundamental_score: float = 0.0
    market_score: float = 0.0
    risk_score: float = 0.0
    relative_strength_score: float = 0.0

    # V3 8대 핵심 루브릭 점수
    valuation_score: float = 0.0          # 밸류에이션 (20%)
    momentum_score: float = 0.0           # 모멘텀 (15%)
    sector_score: float = 0.0             # 섹터 (10%)
    shareholder_score: float = 0.0        # 주주환원 (5%)

    total_score: float = 0.0
    investment_grade: str = "Hold"

    # 순위
    rank_in_group: int = 0
    final_rank: Optional[int] = None

    # 데이터 품질
    data_quality: Optional[DataQualityResult] = None

    # LLM 분석 결과 (리포트 생성 시 채워짐)
    summary: Optional[str] = None                      # 핵심 요약 (1-2문장)
    financial_analysis: Optional[str] = None          # 재무 & 밸류에이션 분석
    technical_analysis: Optional[str] = None          # 기술적 & 차트 분석
    market_sentiment: Optional[str] = None            # 뉴스 & 시장 센티먼트
    comprehensive_analysis: Optional[str] = None      # 종합 투자 의견
    investment_thesis: Optional[List[str]] = None     # 투자 포인트 (3-5개)
    risks: Optional[List[str]] = None                 # 리스크 요인 (2-4개)
    category_reasoning: Optional[Dict[str, str]] = None  # 카테고리별 판단 근거 (LLM)

    # Raw News Data for Context
    news_items: Optional[List[Dict[str, Any]]] = None

    # LLM 실패로 인한 기본값 여부
    is_fallback: bool = False
    fallback_reason: str = ""

    # 원본 데이터 번들 (LLM 분석 시 to_dict()에서 상세 데이터 추출용)
    data_bundle: Optional[StockDataBundle] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "group": self.group,
            "market_cap": self.market_cap,
            "technical_score": self.technical_score,
            "supply_score": self.supply_score,
            "fundamental_score": self.fundamental_score,
            "market_score": self.market_score,
            "risk_score": self.risk_score,
            "relative_strength_score": self.relative_strength_score,
            # V3 카테고리 점수
            "valuation_score": self.valuation_score,
            "momentum_score": self.momentum_score,
            "sector_score": self.sector_score,
            "shareholder_score": self.shareholder_score,
            "total_score": self.total_score,
            "investment_grade": self.investment_grade,
            "rank_in_group": self.rank_in_group,
            "final_rank": self.final_rank,
            "data_quality": self.data_quality.to_dict() if self.data_quality else None,
            # LLM 폴백 추적 (관측 가능성)
            "is_fallback": self.is_fallback,
            "fallback_reason": self.fallback_reason,
        }

        # rubric_result 세부 정보 추가
        if self.rubric_result:
            rubric = self.rubric_result

            # 기술적 분석 세부
            if rubric.technical and rubric.technical.details:
                result["technical_details"] = rubric.technical.details

            # 수급 분석 세부
            if rubric.supply and rubric.supply.details:
                result["supply_details"] = rubric.supply.details

            # 펀더멘털 분석 세부
            if rubric.fundamental and rubric.fundamental.details:
                result["fundamental_details"] = rubric.fundamental.details

            # 시장 환경 세부
            if rubric.market and rubric.market.details:
                result["market_details"] = rubric.market.details

            # 리스크 평가 세부 (V2)
            if rubric.risk and rubric.risk.details:
                result["risk_details"] = rubric.risk.details

            # 상대 강도 세부 (V2)
            if rubric.relative_strength and rubric.relative_strength.details:
                result["relative_strength_details"] = rubric.relative_strength.details

            # V3 카테고리 세부 정보 + V2 호환 필드 복사
            if rubric.valuation and rubric.valuation.details:
                result["valuation_details"] = rubric.valuation.details
                # V2 호환: fundamental_details에 PER/PBR 복사
                if "fundamental_details" in result:
                    result["fundamental_details"]["per_value"] = rubric.valuation.details.get("per_value")
                    result["fundamental_details"]["pbr_value"] = rubric.valuation.details.get("pbr_value")
                    result["fundamental_details"]["sector_avg_per"] = rubric.valuation.details.get("sector_avg_per")
                    result["fundamental_details"]["sector_avg_pbr"] = rubric.valuation.details.get("sector_avg_pbr")

            if rubric.momentum and rubric.momentum.details:
                result["momentum_details"] = rubric.momentum.details
                # V2 호환: technical_details에 RSI/MACD 복사
                if "technical_details" in result:
                    result["technical_details"]["rsi_value"] = rubric.momentum.details.get("rsi_value")
                    result["technical_details"]["macd_value"] = rubric.momentum.details.get("macd_value")
                    result["technical_details"]["macd_signal_value"] = rubric.momentum.details.get("macd_signal_value")
                # V2 호환: supply_details에 거래대금 복사
                if "supply_details" in result:
                    result["supply_details"]["trading_value_amount"] = rubric.momentum.details.get("trading_value_amount")

            if rubric.sector and rubric.sector.details:
                result["sector_details"] = rubric.sector.details

            if rubric.shareholder and rubric.shareholder.details:
                result["shareholder_details"] = rubric.shareholder.details

        # LLM category_reasoning을 세부 데이터로 변환 (rubric_result가 없는 경우)
        elif self.category_reasoning:
            # data_bundle에서 원본 데이터 추출
            fd = self.data_bundle.fundamental_data if self.data_bundle else {}
            ti = self.data_bundle.technical_indicators if self.data_bundle else {}
            sd = self.data_bundle.supply_data if self.data_bundle else {}
            pd = self.data_bundle.price_data if self.data_bundle else {}

            # 기술적 분석 세부 (원본 값 + reasoning)
            result["technical_details"] = {
                "reasoning": self.category_reasoning.get("technical", ""),
                "ma20": ti.get("ma20"),
                "ma60": ti.get("ma60"),
                "rsi": ti.get("rsi"),
                "macd": ti.get("macd"),
                "macd_signal": ti.get("macd_signal"),
                "adx": ti.get("adx"),
                "atr_pct": ti.get("atr_pct"),
                "beta": ti.get("beta"),
                "return_20d": ti.get("return_20d"),
                "current_price": pd.get("current_price"),
                "price_change_pct": pd.get("price_change_pct"),
                "low_52w": pd.get("low_52w"),
                "high_52w": pd.get("high_52w"),
                "position_52w": pd.get("position_52w"),
            }

            # 수급 분석 세부 (원본 값 + reasoning)
            result["supply_details"] = {
                "reasoning": self.category_reasoning.get("supply", ""),
                "foreign_net_5d": sd.get("foreign_net_5d"),
                "foreign_total_5d": sd.get("foreign_total_5d"),
                "foreign_consecutive_days": sd.get("foreign_consecutive_days"),
                "institution_net_5d": sd.get("institution_net_5d"),
                "institution_total_5d": sd.get("institution_total_5d"),
                "institution_consecutive_days": sd.get("institution_consecutive_days"),
                "volume": sd.get("volume"),
                "avg_volume_20d": sd.get("avg_volume_20d"),
                "trading_value": sd.get("trading_value"),
            }

            # 펀더멘털 분석 세부 (원본 값 + reasoning)
            result["fundamental_details"] = {
                "reasoning": self.category_reasoning.get("fundamental", ""),
                "per_value": fd.get("per"),
                "pbr_value": fd.get("pbr"),
                "roe_value": fd.get("roe"),
                "operating_margin": fd.get("operating_margin"),
                "revenue_growth": fd.get("revenue_growth"),
                "op_growth_value": fd.get("operating_profit_growth"),
                "debt_ratio_value": fd.get("debt_ratio"),
                "sector_avg_per": fd.get("sector_avg_per"),
                "sector_avg_pbr": fd.get("sector_avg_pbr"),
            }

            # 시장 환경 세부 (뉴스 센티먼트 원본 값 + reasoning)
            nd = self.data_bundle.news_data if self.data_bundle else {}
            result["market_details"] = {
                "reasoning": self.category_reasoning.get("market", ""),
                "news_total_count": nd.get("total_count"),
                "news_positive_count": nd.get("positive_count"),
                "news_negative_count": nd.get("negative_count"),
                "news_neutral_count": nd.get("neutral_count"),
                "avg_sentiment_score": nd.get("avg_sentiment_score"),
            }

            # 리스크 평가 세부 (원본 값 + reasoning)
            result["risk_details"] = {
                "reasoning": self.category_reasoning.get("risk", ""),
                "atr_pct": ti.get("atr_pct"),
                "beta": ti.get("beta"),
                "max_drawdown_pct": ti.get("max_drawdown_pct"),
            }

            # 상대 강도 세부 (원본 값 + reasoning)
            result["relative_strength_details"] = {
                "reasoning": self.category_reasoning.get("relative_strength", ""),
                "return_20d": ti.get("return_20d"),
            }
            result["category_reasoning"] = self.category_reasoning

        # LLM 분석 결과 추가
        if self.summary:
            result["summary"] = self.summary
        if self.financial_analysis:
            result["financial_analysis"] = self.financial_analysis
        if self.technical_analysis:
            result["technical_analysis"] = self.technical_analysis
        if self.market_sentiment:
            result["market_sentiment"] = self.market_sentiment
        if self.comprehensive_analysis:
            result["comprehensive_analysis"] = self.comprehensive_analysis
        if self.investment_thesis:
            result["investment_thesis"] = self.investment_thesis
        if self.risks:
            result["risks"] = self.risks

        if self.news_items:
            result["news_items"] = self.news_items

        return result


# =============================================================================
# StockAnalyzer
# =============================================================================


@dataclass
class StockAnalyzer(BaseAgent):
    """
    개별 종목 분석기

    주요 기능:
    - 4개 그룹별 종목 분석:
      - KOSPI Top 10 (시총 1~10위)
      - KOSPI 11~20 (시총 11~20위)
      - KOSDAQ Top 10 (시총 1~10위)
      - 섹터별 종목
    - LLMScorer로 점수 및 분석 생성 (RubricEngine 폴백)
    - 시가총액 조회

    사용 예시:
        analyzer = StockAnalyzer()
        results = await analyzer.analyze_symbols(["005930", "000660"])

        # 그룹별 분석
        kospi_results = await analyzer.analyze_kospi_top(20)
        kosdaq_results = await analyzer.analyze_kosdaq_top(10)
        sector_results = await analyzer.analyze_sector("반도체")
    """

    market_data_agent: MarketDataAgent = field(default_factory=MarketDataAgent)
    fundamental_agent: FundamentalAgent = field(default_factory=FundamentalAgent)
    news_agent: NewsAgent = field(default_factory=NewsAgent)
    rubric_engine: RubricEngine = field(default_factory=lambda: RubricEngine(use_v3=True))
    llm_scorer: LLMScorer = field(default_factory=LLMScorer)
    fetcher: StockDataFetcher = field(default_factory=StockDataFetcher)
    quality_validator: DataQualityValidator = field(default_factory=DataQualityValidator)

    # LLM 사용 여부 (True: LLM 우선, False: RubricEngine만)
    use_llm: bool = True

    # LLM 동시 호출 한도 (보수적 기본값 5 — OpenAI rate limit 안전)
    max_concurrent_llm: int = 5

    # 마지막 분석의 품질 요약 (Orchestrator에서 참조)
    _last_quality_summary: Optional[DataQualitySummary] = field(default=None, init=False)

    async def collect(self, symbols: List[str]) -> Dict[str, StockAnalysisResult]:
        """
        BaseAgent 인터페이스 구현.
        여러 종목의 분석 결과를 수집합니다.
        """
        return await self.analyze_symbols(symbols)

    async def analyze_symbols(
        self,
        symbols: List[str],
        group: str = "custom",
        sector_ranks: Optional[Dict[str, Dict[str, Any]]] = None,
        sector_return_5d: Optional[float] = None,
    ) -> Dict[str, StockAnalysisResult]:
        """
        여러 종목을 분석합니다.

        Args:
            symbols: 종목 코드 리스트
            group: 그룹명 (kospi_top10, kospi_11_20, kosdaq_top10, sector_{name}, custom)
            sector_ranks: 섹터 내 순위 정보 (symbol -> {"rank": int, "total": int})
            sector_return_5d: 섹터 5일 수익률 (%)

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        group_display = group.replace("_", " ").replace("sector ", "")
        self._log_info(f"📊 {group_display} 분석 시작 ({len(symbols)}개 종목)")

        # 데이터 수집
        self._log_debug("Collecting market data...")
        market_data = await self.market_data_agent.collect(symbols)
        self._log_debug("Collecting fundamental data...")
        fundamental_data = await self.fundamental_agent.collect(symbols)
        self._log_debug("Collecting news data...")
        news_data = await self.news_agent.collect(symbols)

        # 데이터 품질 검증
        quality_results = self.quality_validator.validate_batch(
            market_data, fundamental_data
        )
        self._last_quality_summary = self.quality_validator.summarize(quality_results)

        # 품질 로그 출력
        summary = self._last_quality_summary
        if summary.invalid_count > 0:
            self._log_warning(
                f"Data quality issues: {summary.invalid_count}/{summary.total_count} "
                f"stocks have invalid data (avg score: {summary.avg_quality_score})"
            )
            for symbol in summary.invalid_symbols[:5]:  # 최대 5개만 표시
                qr = quality_results.get(symbol)
                if qr:
                    self._log_warning(f"  - {symbol}: missing {qr.missing_required}")

        # 시가총액 조회
        market_caps = self._get_market_caps(symbols)

        results: Dict[str, StockAnalysisResult] = {}

        # LLM 사용 가능 여부 확인
        use_llm = self.use_llm and self.llm_scorer.is_available()
        analysis_method = "LLM" if use_llm else "RubricEngine"
        self._log_debug(f"Calculating scores using {analysis_method}...")

        total = len(symbols)

        def _sector_info(symbol: str) -> tuple[Optional[int], Optional[int]]:
            info = sector_ranks.get(symbol, {}) if sector_ranks else {}
            return info.get("rank"), info.get("total")

        if use_llm:
            # LLM 경로: asyncio.gather + Semaphore로 병렬화
            # (gpt-5.2 reasoning model 응답이 길어 직렬 처리 시 6시간+ 소요)
            semaphore = asyncio.Semaphore(self.max_concurrent_llm)
            completed = 0

            async def analyze_one(symbol: str) -> tuple[str, Optional[StockAnalysisResult]]:
                nonlocal completed
                async with semaphore:
                    try:
                        sector_rank, sector_total = _sector_info(symbol)
                        result = await self._analyze_single_async(
                            symbol=symbol,
                            group=group,
                            market_data=market_data.get(symbol),
                            fundamental_data=fundamental_data.get(symbol),
                            news_data=news_data.get(symbol),
                            market_cap=market_caps.get(symbol, 0),
                            data_quality=quality_results.get(symbol),
                            sector_rank=sector_rank,
                            sector_total=sector_total,
                            sector_return_5d=sector_return_5d,
                        )
                        completed += 1
                        self._log_progress(completed, total, f"Analyzed {symbol}")
                        return symbol, result
                    except Exception as e:
                        self._log_error(f"Failed to analyze {symbol}: {e}")
                        return symbol, None

            pairs = await asyncio.gather(*(analyze_one(s) for s in symbols))
            for symbol, result in pairs:
                if result:
                    results[symbol] = result
        else:
            # RubricEngine 경로: 동기 처리 (이미 빠름, 병렬화 가치 없음)
            for i, symbol in enumerate(symbols, 1):
                try:
                    self._log_progress(i, total, f"Analyzing {symbol}")
                    sector_rank, sector_total = _sector_info(symbol)
                    result = self._analyze_single(
                        symbol=symbol,
                        group=group,
                        market_data=market_data.get(symbol),
                        fundamental_data=fundamental_data.get(symbol),
                        news_data=news_data.get(symbol),
                        market_cap=market_caps.get(symbol, 0),
                        data_quality=quality_results.get(symbol),
                        sector_rank=sector_rank,
                        sector_total=sector_total,
                        sector_return_5d=sector_return_5d,
                    )
                    if result:
                        results[symbol] = result
                except Exception as e:
                    self._log_error(f"Failed to analyze {symbol}: {e}")

        # LLM 폴백 체크 및 경고
        if results:
            fallbacks = [r for r in results.values() if r.is_fallback]
            if fallbacks:
                fallback_pct = len(fallbacks) / len(results) * 100
                first_reason = fallbacks[0].fallback_reason
                if fallback_pct >= 50:
                    self._log_error(f"⚠️ LLM 분석 실패: {len(fallbacks)}/{len(results)}개 종목 ({fallback_pct:.0f}%) - {first_reason}")
                elif fallback_pct > 0:
                    self._log_warning(f"⚠️ LLM 분석 일부 실패: {len(fallbacks)}개 종목 - {first_reason}")

        # 분석 완료 요약
        if results:
            scores = [r.total_score for r in results.values()]
            avg_score = sum(scores) / len(scores)
            top_stock = max(results.values(), key=lambda x: x.total_score)
            self._log_info(f"✅ {group_display} 완료: {len(results)}개 (평균 {avg_score:.0f}점, 최고: {top_stock.name})")
        return results

    def get_quality_summary(self) -> Optional[DataQualitySummary]:
        """마지막 분석의 데이터 품질 요약을 반환합니다."""
        return self._last_quality_summary

    async def _analyze_single_async(
        self,
        symbol: str,
        group: str,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
        news_data: Optional[NewsData],
        market_cap: float,
        data_quality: Optional[DataQualityResult] = None,
        sector_rank: Optional[int] = None,
        sector_total: Optional[int] = None,
        sector_return_5d: Optional[float] = None,
    ) -> Optional[StockAnalysisResult]:
        """
        단일 종목을 비동기로 분석합니다 (LLM 사용).
        """
        # 종목 정보
        name = self.fetcher.get_stock_name(symbol)
        sector = get_sector_by_symbol(symbol)
        if sector == "Unknown":
            sector = ""

        # StockDataBundle 생성
        data_bundle = StockDataBundle.from_collected_data(
            symbol=symbol,
            name=name,
            sector=sector,
            market_cap=market_cap,
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data,
        )

        # LLM 분석 시도
        if self.use_llm and self.llm_scorer.is_available():
            try:
                llm_result = await self.llm_scorer.analyze_stock(data_bundle)
                return self._llm_result_to_analysis_result(
                    llm_result, symbol, name, sector, group, market_cap, data_quality, news_data,
                    market_data, fundamental_data, data_bundle,
                    sector_rank=sector_rank, sector_total=sector_total, sector_return_5d=sector_return_5d,
                )
            except Exception as e:
                self._log_warning(f"LLM analysis failed for {symbol}, falling back to RubricEngine: {e}")

        # RubricEngine 폴백
        return self._analyze_single_rubric(
            symbol, name, sector, group, market_data, fundamental_data, news_data,
            market_cap, data_quality
        )

    def _analyze_single(
        self,
        symbol: str,
        group: str,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
        news_data: Optional[NewsData],
        market_cap: float,
        data_quality: Optional[DataQualityResult] = None,
        sector_rank: Optional[int] = None,
        sector_total: Optional[int] = None,
        sector_return_5d: Optional[float] = None,
    ) -> Optional[StockAnalysisResult]:
        """
        단일 종목을 분석합니다 (RubricEngine 사용, 동기).
        """
        # 종목 정보
        name = self.fetcher.get_stock_name(symbol)
        sector = get_sector_by_symbol(symbol)
        if sector == "Unknown":
            sector = ""

        return self._analyze_single_rubric(
            symbol, name, sector, group, market_data, fundamental_data, news_data,
            market_cap, data_quality,
            sector_rank=sector_rank, sector_total=sector_total, sector_return_5d=sector_return_5d,
        )

    def _analyze_single_rubric(
        self,
        symbol: str,
        name: str,
        sector: str,
        group: str,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
        news_data: Optional[NewsData],
        market_cap: float,
        data_quality: Optional[DataQualityResult] = None,
        sector_rank: Optional[int] = None,
        sector_total: Optional[int] = None,
        sector_return_5d: Optional[float] = None,
    ) -> Optional[StockAnalysisResult]:
        """
        RubricEngine을 사용한 단일 종목 분석.
        """
        # V2용 추가 데이터 추출
        atr_pct = market_data.atr_pct if market_data and hasattr(market_data, 'atr_pct') else None
        beta = market_data.beta if market_data and hasattr(market_data, 'beta') else None
        max_drawdown_pct = market_data.max_drawdown_pct if market_data and hasattr(market_data, 'max_drawdown_pct') else None
        stock_return_20d = market_data.return_20d if market_data and hasattr(market_data, 'return_20d') else None

        # 52주 최고/최저가 추출
        low_52w = market_data.low_52w if market_data and hasattr(market_data, 'low_52w') else None
        high_52w = market_data.high_52w if market_data and hasattr(market_data, 'high_52w') else None

        # V3용 추가 데이터 추출
        dividend_yield = fundamental_data.dividend_yield if fundamental_data and hasattr(fundamental_data, 'dividend_yield') else None

        # RubricEngine으로 점수 계산
        rubric_result = self.rubric_engine.calculate(
            symbol=symbol,
            name=name,
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data,
            low_52w=low_52w,
            high_52w=high_52w,
            atr_pct=atr_pct,
            beta=beta,
            max_drawdown_pct=max_drawdown_pct,
            stock_return_20d=stock_return_20d,
            dividend_yield=dividend_yield,
            sector_rank=sector_rank,
            sector_total=sector_total,
            sector_return_5d=sector_return_5d,
        )

        # StockAnalysisResult 생성
        result = StockAnalysisResult(
            symbol=symbol,
            name=name,
            sector=sector,
            group=group,
            market_cap=market_cap,
            rubric_result=rubric_result,
            technical_score=rubric_result.technical.weighted_score,
            supply_score=rubric_result.supply.weighted_score,
            fundamental_score=rubric_result.fundamental.weighted_score,
            market_score=rubric_result.market.weighted_score,
            risk_score=rubric_result.risk.weighted_score if rubric_result.risk else 0.0,
            relative_strength_score=rubric_result.relative_strength.weighted_score if rubric_result.relative_strength else 0.0,
            # V3 카테고리 점수
            valuation_score=rubric_result.valuation.weighted_score if rubric_result.valuation else 0.0,
            momentum_score=rubric_result.momentum.weighted_score if rubric_result.momentum else 0.0,
            sector_score=rubric_result.sector.weighted_score if rubric_result.sector else 0.0,
            shareholder_score=rubric_result.shareholder.weighted_score if rubric_result.shareholder else 0.0,
            total_score=rubric_result.total_score,
            investment_grade=rubric_result.grade,
            data_quality=data_quality,
            news_items=[
                {"title": item.title, "sentiment": item.sentiment}
                for item in news_data.news_items[:5]
            ] if news_data else [],
        )

        return result

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
        data_bundle: Optional[StockDataBundle] = None,
        sector_rank: Optional[int] = None,
        sector_total: Optional[int] = None,
        sector_return_5d: Optional[float] = None,
    ) -> StockAnalysisResult:
        """
        LLMScoreResult를 StockAnalysisResult로 변환합니다.
        V3 8대 루브릭 점수도 계산하여 포함합니다.

        LLM이 fallback인 경우(API 실패 등) RubricEngine의 실제 점수를 사용합니다.
        """
        # RubricEngine으로 점수 계산 (V3 포함)
        rubric_result = None
        low_52w = market_data.low_52w if market_data and hasattr(market_data, 'low_52w') else None
        high_52w = market_data.high_52w if market_data and hasattr(market_data, 'high_52w') else None
        atr_pct = market_data.atr_pct if market_data and hasattr(market_data, 'atr_pct') else None
        beta = market_data.beta if market_data and hasattr(market_data, 'beta') else None
        max_drawdown_pct = market_data.max_drawdown_pct if market_data and hasattr(market_data, 'max_drawdown_pct') else None
        stock_return_20d = market_data.return_20d if market_data and hasattr(market_data, 'return_20d') else None
        dividend_yield = fundamental_data.dividend_yield if fundamental_data and hasattr(fundamental_data, 'dividend_yield') else None

        try:
            rubric_result = self.rubric_engine.calculate(
                symbol=symbol,
                name=name,
                market_data=market_data,
                fundamental_data=fundamental_data,
                news_data=news_data,
                low_52w=low_52w,
                high_52w=high_52w,
                atr_pct=atr_pct,
                beta=beta,
                max_drawdown_pct=max_drawdown_pct,
                stock_return_20d=stock_return_20d,
                dividend_yield=dividend_yield,
                sector_rank=sector_rank,
                sector_total=sector_total,
                sector_return_5d=sector_return_5d,
            )
        except Exception as e:
            self._log_debug(f"RubricEngine 점수 계산 실패 for {symbol}: {e}")

        # LLM이 fallback인 경우 RubricEngine 점수 사용
        if llm_result.is_fallback and rubric_result:
            self._log_debug(f"LLM fallback for {symbol}, using RubricEngine scores")
            return StockAnalysisResult(
                symbol=symbol,
                name=name,
                sector=sector,
                group=group,
                market_cap=market_cap,
                rubric_result=rubric_result,
                # V2 카테고리 점수 (RubricEngine에서)
                technical_score=rubric_result.technical.weighted_score,
                supply_score=rubric_result.supply.weighted_score,
                fundamental_score=rubric_result.fundamental.weighted_score,
                market_score=rubric_result.market.weighted_score,
                risk_score=rubric_result.risk.weighted_score if rubric_result.risk else 5.0,
                relative_strength_score=rubric_result.relative_strength.weighted_score if rubric_result.relative_strength else 5.0,
                # V3 8대 루브릭 점수
                valuation_score=rubric_result.valuation.weighted_score if rubric_result.valuation else 0.0,
                momentum_score=rubric_result.momentum.weighted_score if rubric_result.momentum else 0.0,
                sector_score=rubric_result.sector.weighted_score if rubric_result.sector else 0.0,
                shareholder_score=rubric_result.shareholder.weighted_score if rubric_result.shareholder else 0.0,
                total_score=rubric_result.total_score,
                investment_grade=rubric_result.grade,
                data_quality=data_quality,
                # Fallback 템플릿 분석 (RubricEngine 기반)
                summary=f"{rubric_result.grade} 등급 (총점: {rubric_result.total_score:.1f}점)",
                financial_analysis=None,  # apiService에서 템플릿 생성
                technical_analysis=None,
                market_sentiment=None,
                comprehensive_analysis=None,
                investment_thesis=None,
                risks=None,
                category_reasoning=None,
                news_items=[
                    {"title": item.title, "sentiment": item.sentiment}
                    for item in news_data.news_items[:5]
                ] if news_data else [],
                is_fallback=True,
                fallback_reason=llm_result.fallback_reason,
            )

        # LLM 분석 성공 시 LLM V3 점수 직접 사용
        return StockAnalysisResult(
            symbol=symbol,
            name=name,
            sector=sector,
            group=group,
            market_cap=market_cap,
            rubric_result=rubric_result,  # 참고용 (to_dict에서 details 추출)
            # V3 8대 핵심 루브릭 점수 (LLM에서 직접)
            technical_score=llm_result.technical_score,
            supply_score=llm_result.supply_score,
            fundamental_score=llm_result.fundamental_score,
            market_score=0.0,  # V3에서는 미사용 (V2 호환성 유지)
            risk_score=llm_result.risk_score,
            relative_strength_score=0.0,  # V3에서는 미사용 (V2 호환성 유지)
            # V3 전용 카테고리 점수 (LLM에서 직접)
            valuation_score=llm_result.valuation_score,
            momentum_score=llm_result.momentum_score,
            sector_score=llm_result.sector_score,
            shareholder_score=llm_result.shareholder_score,
            total_score=llm_result.total_score,
            investment_grade=llm_result.grade,
            data_quality=data_quality,
            # LLM 분석 결과
            summary=llm_result.summary,
            financial_analysis=llm_result.financial_analysis,
            technical_analysis=llm_result.technical_analysis,
            market_sentiment=llm_result.market_sentiment,
            comprehensive_analysis=llm_result.comprehensive_analysis,
            investment_thesis=llm_result.investment_thesis,
            risks=llm_result.risks,
            category_reasoning=llm_result.category_reasoning,
            news_items=[
                {"title": item.title, "sentiment": item.sentiment}
                for item in news_data.news_items[:5]
            ] if news_data else [],
            is_fallback=llm_result.is_fallback,
            fallback_reason=llm_result.fallback_reason,
            data_bundle=data_bundle,  # 원본 데이터 번들 저장
        )

    def _get_market_caps(self, symbols: List[str]) -> Dict[str, float]:
        """
        종목들의 시가총액을 조회합니다 (네이버 금융).
        파일 캐시(market_data_{symbol} 및 market_cap_{symbol})를 최우선으로 사용하여 웹 요청을 완전 배제합니다.
        
        Returns:
            종목코드를 키로 하는 시가총액 딕셔너리 (억원 단위)
        """
        result: Dict[str, float] = {}
        missing_symbols = []

        # 1. 파일 캐시 우선 조회
        for symbol in symbols:
            # A. market_data_{symbol} 캐시 확인 (4시간 TTL)
            cache_key = f"market_data_{symbol}"
            cached_md = self.cache.get(cache_key, max_age_hours=4)
            if cached_md and cached_md.get("market_cap"):
                result[symbol] = cached_md["market_cap"]
                continue

            # B. market_cap_{symbol} 전용 캐시 확인 (24시간 TTL)
            cap_key = f"market_cap_{symbol}"
            cached_cap = self.cache.get(cap_key, max_age_hours=24)
            if cached_cap is not None:
                result[symbol] = cached_cap
                continue

            missing_symbols.append(symbol)

        # 모든 종목이 캐시 히트했으면 즉시 반환
        if not missing_symbols:
            return result

        # 2. 캐시 미스된 종목들에 한해서만 순위 목록 또는 개별 조회
        try:
            self._log_info(f"개별 시가총액 조회 필요: {len(missing_symbols)}개 종목 (캐시 미스)")
            
            # 네이버 금융에서 KOSPI, KOSDAQ 시가총액 순위 조회 (상위 100개)
            kospi_data = self.fetcher.get_market_cap_rank("KOSPI", 100)
            kosdaq_data = self.fetcher.get_market_cap_rank("KOSDAQ", 100)

            market_cap_map = {}
            for stock in kospi_data + kosdaq_data:
                market_cap_map[stock.symbol] = stock.market_cap or 0

            still_missing = []
            for symbol in missing_symbols:
                if symbol in market_cap_map and market_cap_map[symbol] > 0:
                    val = market_cap_map[symbol]
                    result[symbol] = val
                    self.cache.set(f"market_cap_{symbol}", val, ttl_hours=24)
                else:
                    still_missing.append(symbol)

            # 3. 순위 목록에도 없는 종목은 파일 캐시-또는-개별 크롤링
            if still_missing:
                for symbol in still_missing:
                    market_cap = self._get_cached_or_fetch(
                        f"market_cap_{symbol}",
                        self.fetcher.get_market_cap,
                        ttl_hours=24,
                        symbol=symbol
                    )
                    result[symbol] = market_cap if market_cap else 0

        except Exception as e:
            self._log_warning(f"Failed to get market caps from Naver: {e}")
            # 폴백: 개별 조회
            for symbol in missing_symbols:
                if symbol not in result:
                    market_cap = self._get_cached_or_fetch(
                        f"market_cap_{symbol}",
                        self.fetcher.get_market_cap,
                        ttl_hours=24,
                        symbol=symbol
                    )
                    result[symbol] = market_cap if market_cap else 0

        return result

    async def analyze_kospi_top(self, top_n: int = 20) -> Dict[str, StockAnalysisResult]:
        """
        KOSPI 시총 상위 종목을 분석합니다.

        Args:
            top_n: 분석할 종목 수 (기본 20개)

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        self._log_info(f"Analyzing KOSPI top {top_n} stocks")

        try:
            stock_infos = self.fetcher.get_market_cap_rank(market="KOSPI", top_n=top_n)
            symbols = [si.symbol for si in stock_infos]
        except Exception as e:
            self._log_error(f"Failed to get KOSPI rankings: {e}")
            return {}

        # Top 10과 11~20 구분
        results: Dict[str, StockAnalysisResult] = {}

        if len(symbols) >= 10:
            top10_results = await self.analyze_symbols(symbols[:10], group="kospi_top10")
            results.update(top10_results)

        if len(symbols) >= 20:
            next10_results = await self.analyze_symbols(symbols[10:20], group="kospi_11_20")
            results.update(next10_results)

        return results

    async def analyze_kosdaq_top(self, top_n: int = 10) -> Dict[str, StockAnalysisResult]:
        """
        KOSDAQ 시총 상위 종목을 분석합니다.

        Args:
            top_n: 분석할 종목 수 (기본 10개)

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        self._log_info(f"Analyzing KOSDAQ top {top_n} stocks")

        try:
            stock_infos = self.fetcher.get_market_cap_rank(market="KOSDAQ", top_n=top_n)
            symbols = [si.symbol for si in stock_infos]
        except Exception as e:
            self._log_error(f"Failed to get KOSDAQ rankings: {e}")
            return {}

        return await self.analyze_symbols(symbols, group="kosdaq_top10")

    async def analyze_sector(
        self,
        sector_name: str,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, StockAnalysisResult]:
        """
        특정 섹터의 종목들을 분석합니다.

        Args:
            sector_name: 섹터명
            symbols: 분석할 종목 코드 리스트 (None이면 config.SECTORS에서 가져옴)

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        if symbols is None:
            if sector_name not in SECTORS:
                self._log_error(f"Unknown sector: {sector_name}")
                return {}
            symbols = SECTORS[sector_name]

        self._log_info(f"Analyzing sector '{sector_name}' with {len(symbols)} stocks")

        # 섹터 내 시총 기반 순위 계산
        sector_ranks = self._calculate_sector_ranks(symbols)

        # 섹터 5일 수익률 계산 (시총 가중 평균)
        sector_return_5d = self._calculate_sector_return_5d(symbols)

        return await self.analyze_symbols(
            symbols,
            group=f"sector_{sector_name}",
            sector_ranks=sector_ranks,
            sector_return_5d=sector_return_5d,
        )

    def _calculate_sector_ranks(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        섹터 내 시총 기반 순위를 계산합니다.

        Args:
            symbols: 섹터 내 종목 코드 리스트

        Returns:
            종목코드를 키로 하는 순위 정보 딕셔너리 {symbol: {"rank": int, "total": int}}
        """
        market_caps = self._get_market_caps(symbols)
        total = len(symbols)

        # 시총 내림차순 정렬
        sorted_symbols = sorted(
            symbols,
            key=lambda s: market_caps.get(s, 0),
            reverse=True
        )

        return {
            symbol: {"rank": rank, "total": total}
            for rank, symbol in enumerate(sorted_symbols, 1)
        }

    def _calculate_sector_return_5d(self, symbols: List[str]) -> Optional[float]:
        """
        섹터의 5일 수익률을 계산합니다 (시총 가중 평균).
        필수 파라미터 start_date와 end_date를 넘겨주어 TypeError를 수정합니다.

        Args:
            symbols: 섹터 내 종목 코드 리스트

        Returns:
            섹터 5일 수익률 (%), 계산 불가 시 None
        """
        try:
            market_caps = self._get_market_caps(symbols)

            total_market_cap = 0
            weighted_return = 0

            # 최근 15거래일 치의 날짜 범위 계산
            latest_trading_date = self.fetcher._get_latest_trading_date()
            end_date = datetime.strptime(latest_trading_date, "%Y%m%d")
            start_date = end_date - timedelta(days=15)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            for symbol in symbols:
                market_cap = market_caps.get(symbol, 0)
                if market_cap <= 0:
                    continue

                # 주가 변동률 조회 (start_date, end_date 인자 필수 전달)
                try:
                    stock_data = self.fetcher.fetch_stock_data(symbol, start_str, end_str)
                    if stock_data is not None and len(stock_data) >= 5:
                        # 5일 수익률 = (현재가 - 5일전 종가) / 5일전 종가 * 100
                        current_close = stock_data['Close'].iloc[-1]
                        close_5d_ago = stock_data['Close'].iloc[-5]
                        return_5d = (current_close - close_5d_ago) / close_5d_ago * 100

                        weighted_return += return_5d * market_cap
                        total_market_cap += market_cap
                except Exception as e:
                    self._log_debug(f"Failed to calculate return for {symbol}: {e}")
                    continue

            if total_market_cap > 0:
                return weighted_return / total_market_cap

            return None

        except Exception as e:
            self._log_warning(f"Failed to calculate sector return: {e}")
            return None

    async def analyze_all_sectors(
        self,
        dynamic_sectors: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Dict[str, StockAnalysisResult]]:
        """
        모든 섹터의 종목들을 분석합니다.

        Args:
            dynamic_sectors: 동적으로 가져온 섹터별 종목 코드 딕셔너리
                            (None이면 config.SECTORS 사용)

        Returns:
            섹터명을 키로 하는 딕셔너리 (값은 종목별 분석 결과)
        """
        sector_map = dynamic_sectors if dynamic_sectors else SECTORS
        self._log_info(f"Analyzing all {len(sector_map)} sectors")

        results: Dict[str, Dict[str, StockAnalysisResult]] = {}

        for sector_name, symbols in sector_map.items():
            sector_results = await self.analyze_sector(sector_name, symbols)
            results[sector_name] = sector_results

        return results
