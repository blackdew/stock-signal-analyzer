"""
Sector Analyzer

섹터별 점수를 산출하고 상위 섹터를 선정하는 분석기.
StockAnalyzer의 결과를 기반으로 시가총액 가중 평균 점수를 계산합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.analysis.stock_analyzer import StockAnalyzer, StockAnalysisResult
from src.core.config import SECTORS


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class SectorAnalysisResult:
    """
    섹터 분석 결과

    Attributes:
        sector_name: 섹터명
        stock_count: 섹터 내 종목 수
        total_market_cap: 총 시가총액 (억원)

        weighted_score: 시가총액 가중 평균 점수
        simple_score: 단순 평균 점수

        technical_score: 기술적 분석 점수 (가중 평균)
        supply_score: 수급 분석 점수 (가중 평균)
        fundamental_score: 펀더멘털 분석 점수 (가중 평균)
        market_score: 시장 환경 점수 (가중 평균)

        top_stocks: 상위 종목 리스트
        rank: 섹터 순위
    """
    sector_name: str
    stock_count: int
    total_market_cap: float  # 억원

    weighted_score: float  # 시가총액 가중 평균
    simple_score: float    # 단순 평균

    # 카테고리별 가중 평균
    technical_score: float = 0.0
    supply_score: float = 0.0
    fundamental_score: float = 0.0
    market_score: float = 0.0

    # 상위 종목
    top_stocks: List[StockAnalysisResult] = field(default_factory=list)

    # 순위
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "sector_name": self.sector_name,
            "stock_count": self.stock_count,
            "total_market_cap": self.total_market_cap,
            "weighted_score": self.weighted_score,
            "simple_score": self.simple_score,
            "technical_score": self.technical_score,
            "supply_score": self.supply_score,
            "fundamental_score": self.fundamental_score,
            "market_score": self.market_score,
            "top_stocks": [s.to_dict() for s in self.top_stocks],
            "rank": self.rank,
        }


# =============================================================================
# SectorAnalyzer
# =============================================================================


@dataclass
class SectorAnalyzer(BaseAgent):
    """
    섹터 분석기

    주요 기능:
    - 섹터별 시가총액 가중 평균 점수 계산
    - 상위 3개 섹터 선정
    - 섹터 내 상위 종목 추출

    사용 예시:
        analyzer = SectorAnalyzer()
        results = await analyzer.analyze()

        # 상위 섹터 조회
        top3 = analyzer.get_top_sectors(results, top_n=3)
    """

    stock_analyzer: StockAnalyzer = field(default_factory=StockAnalyzer)
    use_weighted_average: bool = True  # True: 시가총액 가중 평균, False: 단순 평균

    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        BaseAgent 인터페이스 구현.
        모든 섹터를 분석합니다.
        """
        results = await self.analyze()
        return {r.sector_name: r.to_dict() for r in results}

    async def analyze(self) -> List[SectorAnalysisResult]:
        """
        모든 섹터를 분석합니다.

        Returns:
            SectorAnalysisResult 리스트 (점수 내림차순)
        """
        self._log_info(f"Analyzing {len(SECTORS)} sectors")

        # 모든 섹터 종목 분석
        all_sector_stocks = await self.stock_analyzer.analyze_all_sectors()

        results: List[SectorAnalysisResult] = []

        for sector_name, stock_results in all_sector_stocks.items():
            if not stock_results:
                self._log_warning(f"No stock results for sector: {sector_name}")
                continue

            sector_result = self._calculate_sector_score(sector_name, stock_results)
            results.append(sector_result)

        # 점수 기준 정렬
        score_key = "weighted_score" if self.use_weighted_average else "simple_score"
        results.sort(key=lambda x: getattr(x, score_key), reverse=True)

        # 순위 부여
        for i, result in enumerate(results, 1):
            result.rank = i

        self._log_info(f"Analyzed {len(results)} sectors")
        return results

    def _calculate_sector_score(
        self,
        sector_name: str,
        stock_results: Dict[str, StockAnalysisResult]
    ) -> SectorAnalysisResult:
        """
        섹터 점수를 계산합니다.

        Args:
            sector_name: 섹터명
            stock_results: 종목별 분석 결과

        Returns:
            SectorAnalysisResult
        """
        stocks = list(stock_results.values())
        stock_count = len(stocks)

        # 총 시가총액
        total_market_cap = sum(s.market_cap for s in stocks)

        # 단순 평균
        simple_score = sum(s.total_score for s in stocks) / stock_count if stock_count > 0 else 0

        # 시가총액 가중 평균
        if total_market_cap > 0:
            weighted_score = sum(
                s.total_score * (s.market_cap / total_market_cap)
                for s in stocks
            )
            technical_weighted = sum(
                s.technical_score * (s.market_cap / total_market_cap)
                for s in stocks
            )
            supply_weighted = sum(
                s.supply_score * (s.market_cap / total_market_cap)
                for s in stocks
            )
            fundamental_weighted = sum(
                s.fundamental_score * (s.market_cap / total_market_cap)
                for s in stocks
            )
            market_weighted = sum(
                s.market_score * (s.market_cap / total_market_cap)
                for s in stocks
            )
        else:
            weighted_score = simple_score
            technical_weighted = sum(s.technical_score for s in stocks) / stock_count if stock_count > 0 else 0
            supply_weighted = sum(s.supply_score for s in stocks) / stock_count if stock_count > 0 else 0
            fundamental_weighted = sum(s.fundamental_score for s in stocks) / stock_count if stock_count > 0 else 0
            market_weighted = sum(s.market_score for s in stocks) / stock_count if stock_count > 0 else 0

        # 상위 종목 (점수 내림차순, 최대 5개)
        sorted_stocks = sorted(stocks, key=lambda x: x.total_score, reverse=True)
        top_stocks = sorted_stocks[:5]

        return SectorAnalysisResult(
            sector_name=sector_name,
            stock_count=stock_count,
            total_market_cap=total_market_cap,
            weighted_score=round(weighted_score, 2),
            simple_score=round(simple_score, 2),
            technical_score=round(technical_weighted, 2),
            supply_score=round(supply_weighted, 2),
            fundamental_score=round(fundamental_weighted, 2),
            market_score=round(market_weighted, 2),
            top_stocks=top_stocks,
        )

    def get_top_sectors(
        self,
        results: List[SectorAnalysisResult],
        top_n: int = 3
    ) -> List[SectorAnalysisResult]:
        """
        상위 N개 섹터를 반환합니다.

        Args:
            results: 섹터 분석 결과 리스트
            top_n: 반환할 섹터 수

        Returns:
            상위 N개 SectorAnalysisResult 리스트
        """
        score_key = "weighted_score" if self.use_weighted_average else "simple_score"
        sorted_results = sorted(results, key=lambda x: getattr(x, score_key), reverse=True)
        return sorted_results[:top_n]

    async def analyze_single_sector(self, sector_name: str) -> Optional[SectorAnalysisResult]:
        """
        단일 섹터를 분석합니다.

        Args:
            sector_name: 섹터명

        Returns:
            SectorAnalysisResult 또는 None
        """
        if sector_name not in SECTORS:
            self._log_error(f"Unknown sector: {sector_name}")
            return None

        stock_results = await self.stock_analyzer.analyze_sector(sector_name)

        if not stock_results:
            self._log_warning(f"No stock results for sector: {sector_name}")
            return None

        return self._calculate_sector_score(sector_name, stock_results)

    def get_sector_stocks_sorted(
        self,
        sector_result: SectorAnalysisResult,
        top_n: Optional[int] = None
    ) -> List[StockAnalysisResult]:
        """
        섹터 내 종목을 점수순으로 반환합니다.

        Args:
            sector_result: 섹터 분석 결과
            top_n: 반환할 종목 수 (None이면 전체)

        Returns:
            StockAnalysisResult 리스트
        """
        if top_n is None:
            return sector_result.top_stocks
        return sector_result.top_stocks[:top_n]
