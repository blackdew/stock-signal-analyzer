"""
Stock Analyzer

개별 종목의 루브릭 점수를 산출하는 분석기.
MarketDataAgent, FundamentalAgent, NewsAgent의 데이터를 기반으로
RubricEngine을 통해 점수를 계산합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.data.market_data_agent import MarketDataAgent, MarketData
from src.agents.data.fundamental_agent import FundamentalAgent, FundamentalData
from src.agents.data.news_agent import NewsAgent, NewsData
from src.agents.analysis.data_quality import (
    DataQualityValidator,
    DataQualityResult,
    DataQualitySummary,
)
from src.core.rubric import RubricEngine, RubricResult
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

    # 점수 (100점 만점 기준 환산)
    technical_score: float = 0.0
    supply_score: float = 0.0
    fundamental_score: float = 0.0
    market_score: float = 0.0
    risk_score: float = 0.0
    relative_strength_score: float = 0.0

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
            "total_score": self.total_score,
            "investment_grade": self.investment_grade,
            "rank_in_group": self.rank_in_group,
            "final_rank": self.final_rank,
            "data_quality": self.data_quality.to_dict() if self.data_quality else None,
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
    - RubricEngine으로 점수 산출
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
    rubric_engine: RubricEngine = field(default_factory=RubricEngine)
    fetcher: StockDataFetcher = field(default_factory=StockDataFetcher)
    quality_validator: DataQualityValidator = field(default_factory=DataQualityValidator)

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
        group: str = "custom"
    ) -> Dict[str, StockAnalysisResult]:
        """
        여러 종목을 분석합니다.

        Args:
            symbols: 종목 코드 리스트
            group: 그룹명 (kospi_top10, kospi_11_20, kosdaq_top10, sector_{name}, custom)

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        self._log_info(f"Analyzing {len(symbols)} stocks for group: {group}")

        # 데이터 수집
        self._log_info("Phase 1/3: Collecting market data...")
        market_data = await self.market_data_agent.collect(symbols)
        self._log_info("Phase 2/3: Collecting fundamental data...")
        fundamental_data = await self.fundamental_agent.collect(symbols)
        self._log_info("Phase 3/3: Collecting news data...")
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

        self._log_info("Calculating rubric scores...")
        total = len(symbols)
        for i, symbol in enumerate(symbols, 1):
            try:
                self._log_progress(i, total, f"Analyzing {symbol}")
                self._log_debug(f"[{symbol}] Collecting market data...")
                self._log_debug(f"[{symbol}] Collecting fundamental data...")
                self._log_debug(f"[{symbol}] Calculating rubric score...")
                result = self._analyze_single(
                    symbol=symbol,
                    group=group,
                    market_data=market_data.get(symbol),
                    fundamental_data=fundamental_data.get(symbol),
                    news_data=news_data.get(symbol),
                    market_cap=market_caps.get(symbol, 0),
                    data_quality=quality_results.get(symbol),
                )
                if result:
                    results[symbol] = result
            except Exception as e:
                self._log_error(f"Failed to analyze {symbol}: {e}")

        self._log_info(f"Analyzed {len(results)}/{len(symbols)} stocks")
        return results

    def get_quality_summary(self) -> Optional[DataQualitySummary]:
        """마지막 분석의 데이터 품질 요약을 반환합니다."""
        return self._last_quality_summary

    def _analyze_single(
        self,
        symbol: str,
        group: str,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
        news_data: Optional[NewsData],
        market_cap: float,
        data_quality: Optional[DataQualityResult] = None,
    ) -> Optional[StockAnalysisResult]:
        """
        단일 종목을 분석합니다.
        """
        # 종목 정보
        name = self.fetcher.get_stock_name(symbol)
        sector = get_sector_by_symbol(symbol)

        # V2용 추가 데이터 추출
        atr_pct = market_data.atr_pct if market_data and hasattr(market_data, 'atr_pct') else None
        beta = market_data.beta if market_data and hasattr(market_data, 'beta') else None
        max_drawdown_pct = market_data.max_drawdown_pct if market_data and hasattr(market_data, 'max_drawdown_pct') else None
        stock_return_20d = market_data.return_20d if market_data and hasattr(market_data, 'return_20d') else None

        # 52주 최고/최저가 추출
        low_52w = market_data.low_52w if market_data and hasattr(market_data, 'low_52w') else None
        high_52w = market_data.high_52w if market_data and hasattr(market_data, 'high_52w') else None

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
        )

        # StockAnalysisResult 생성
        # CategoryScore 객체에서 weighted_score 추출
        result = StockAnalysisResult(
            symbol=symbol,
            name=name,
            sector=sector if sector != "Unknown" else "",
            group=group,
            market_cap=market_cap,
            rubric_result=rubric_result,
            technical_score=rubric_result.technical.weighted_score,
            supply_score=rubric_result.supply.weighted_score,
            fundamental_score=rubric_result.fundamental.weighted_score,
            market_score=rubric_result.market.weighted_score,
            risk_score=rubric_result.risk.weighted_score if rubric_result.risk else 0.0,
            relative_strength_score=rubric_result.relative_strength.weighted_score if rubric_result.relative_strength else 0.0,
            total_score=rubric_result.total_score,
            investment_grade=rubric_result.grade,
            data_quality=data_quality,
        )

        return result

    def _get_market_caps(self, symbols: List[str]) -> Dict[str, float]:
        """
        종목들의 시가총액을 조회합니다 (네이버 금융).

        1. 먼저 시가총액 순위에서 조회 (KOSPI/KOSDAQ 상위 100개)
        2. 순위에 없는 종목은 개별 페이지에서 조회

        Returns:
            종목코드를 키로 하는 시가총액 딕셔너리 (억원 단위)
        """
        result: Dict[str, float] = {}

        try:
            # 네이버 금융에서 KOSPI, KOSDAQ 시가총액 순위 조회
            kospi_data = self.fetcher.get_market_cap_rank("KOSPI", 100)
            kosdaq_data = self.fetcher.get_market_cap_rank("KOSDAQ", 100)

            # 심볼별 시가총액 매핑
            market_cap_map = {}
            for stock in kospi_data + kosdaq_data:
                market_cap_map[stock.symbol] = stock.market_cap or 0

            # 각 심볼의 시가총액 조회
            missing_symbols = []
            for symbol in symbols:
                if symbol in market_cap_map and market_cap_map[symbol] > 0:
                    result[symbol] = market_cap_map[symbol]
                else:
                    missing_symbols.append(symbol)

            # 순위에 없는 종목은 개별 조회
            if missing_symbols:
                self._log_info(f"개별 시가총액 조회 필요: {len(missing_symbols)}개 종목")
                for symbol in missing_symbols:
                    market_cap = self.fetcher.get_market_cap(symbol)
                    result[symbol] = market_cap if market_cap else 0

        except Exception as e:
            self._log_warning(f"Failed to get market caps from Naver: {e}")
            # 폴백: 개별 조회
            for symbol in symbols:
                if symbol not in result:
                    market_cap = self.fetcher.get_market_cap(symbol)
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

    async def analyze_sector(self, sector_name: str) -> Dict[str, StockAnalysisResult]:
        """
        특정 섹터의 종목들을 분석합니다.

        Args:
            sector_name: 섹터명

        Returns:
            종목코드를 키로 하는 StockAnalysisResult 딕셔너리
        """
        if sector_name not in SECTORS:
            self._log_error(f"Unknown sector: {sector_name}")
            return {}

        symbols = SECTORS[sector_name]
        self._log_info(f"Analyzing sector '{sector_name}' with {len(symbols)} stocks")

        return await self.analyze_symbols(symbols, group=f"sector_{sector_name}")

    async def analyze_all_sectors(self) -> Dict[str, Dict[str, StockAnalysisResult]]:
        """
        모든 섹터의 종목들을 분석합니다.

        Returns:
            섹터명을 키로 하는 딕셔너리 (값은 종목별 분석 결과)
        """
        self._log_info(f"Analyzing all {len(SECTORS)} sectors")

        results: Dict[str, Dict[str, StockAnalysisResult]] = {}

        for sector_name in SECTORS:
            sector_results = await self.analyze_sector(sector_name)
            results[sector_name] = sector_results

        return results
