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

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
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
        }


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
        market_data = await self.market_data_agent.collect(symbols)
        fundamental_data = await self.fundamental_agent.collect(symbols)
        news_data = await self.news_agent.collect(symbols)

        # 시가총액 조회
        market_caps = self._get_market_caps(symbols)

        results: Dict[str, StockAnalysisResult] = {}

        for symbol in symbols:
            try:
                result = self._analyze_single(
                    symbol=symbol,
                    group=group,
                    market_data=market_data.get(symbol),
                    fundamental_data=fundamental_data.get(symbol),
                    news_data=news_data.get(symbol),
                    market_cap=market_caps.get(symbol, 0),
                )
                if result:
                    results[symbol] = result
            except Exception as e:
                self._log_error(f"Failed to analyze {symbol}: {e}")

        self._log_info(f"Analyzed {len(results)}/{len(symbols)} stocks")
        return results

    def _analyze_single(
        self,
        symbol: str,
        group: str,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
        news_data: Optional[NewsData],
        market_cap: float,
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

        # RubricEngine으로 점수 계산
        rubric_result = self.rubric_engine.calculate(
            symbol=symbol,
            name=name,
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data,
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
        )

        return result

    def _get_market_caps(self, symbols: List[str]) -> Dict[str, float]:
        """
        종목들의 시가총액을 조회합니다.

        Returns:
            종목코드를 키로 하는 시가총액 딕셔너리 (억원 단위)
        """
        result: Dict[str, float] = {}

        try:
            # KRX 상장 종목 정보에서 시가총액 조회
            krx = self.fetcher._get_krx_listing()

            for symbol in symbols:
                stock = krx[krx["Code"] == symbol]
                if not stock.empty and "Marcap" in stock.columns:
                    # Marcap은 원 단위, 억원으로 변환
                    marcap = stock.iloc[0]["Marcap"]
                    result[symbol] = float(marcap) / 100_000_000
                else:
                    result[symbol] = 0
        except Exception as e:
            self._log_warning(f"Failed to get market caps: {e}")

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
            symbols = self.fetcher.get_market_cap_rank(market="KOSPI", top_n=top_n)
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
            symbols = self.fetcher.get_market_cap_rank(market="KOSDAQ", top_n=top_n)
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
