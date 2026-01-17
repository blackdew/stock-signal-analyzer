"""
Ranking Agent

4개 그룹에서 상위 종목을 선정하고 최종 18개 종목과 Top 3를 선정하는 에이전트.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.analysis.stock_analyzer import StockAnalyzer, StockAnalysisResult
from src.agents.analysis.sector_analyzer import SectorAnalyzer, SectorAnalysisResult
from src.core.config import SECTORS


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class RankingResult:
    """
    순위 산정 결과

    Attributes:
        kospi_top10: KOSPI 시총 Top 10 그룹 상위 종목
        kospi_11_20: KOSPI 시총 11~20 그룹 상위 종목
        kosdaq_top10: KOSDAQ 시총 Top 10 그룹 상위 종목
        sector_top: 섹터별 상위 종목 (상위 3개 섹터의 상위 종목)

        final_18: 최종 선정된 18개 종목
        final_top3: 최종 Top 3 종목

        top_sectors: 상위 3개 섹터
    """
    kospi_top10: List[StockAnalysisResult] = field(default_factory=list)
    kospi_11_20: List[StockAnalysisResult] = field(default_factory=list)
    kosdaq_top10: List[StockAnalysisResult] = field(default_factory=list)
    sector_top: List[StockAnalysisResult] = field(default_factory=list)

    final_18: List[StockAnalysisResult] = field(default_factory=list)
    final_top3: List[StockAnalysisResult] = field(default_factory=list)

    top_sectors: List[SectorAnalysisResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "kospi_top10": [s.to_dict() for s in self.kospi_top10],
            "kospi_11_20": [s.to_dict() for s in self.kospi_11_20],
            "kosdaq_top10": [s.to_dict() for s in self.kosdaq_top10],
            "sector_top": [s.to_dict() for s in self.sector_top],
            "final_18": [s.to_dict() for s in self.final_18],
            "final_top3": [s.to_dict() for s in self.final_top3],
            "top_sectors": [s.to_dict() for s in self.top_sectors],
        }

    def get_summary(self) -> Dict[str, Any]:
        """요약 정보 반환"""
        return {
            "total_candidates": len(self.final_18),
            "top_sectors": [s.sector_name for s in self.top_sectors],
            "top3_stocks": [
                {"symbol": s.symbol, "name": s.name, "score": s.total_score}
                for s in self.final_top3
            ],
            "group_counts": {
                "kospi_top10": len(self.kospi_top10),
                "kospi_11_20": len(self.kospi_11_20),
                "kosdaq_top10": len(self.kosdaq_top10),
                "sector_top": len(self.sector_top),
            },
        }


# =============================================================================
# RankingAgent
# =============================================================================


@dataclass
class RankingAgent(BaseAgent):
    """
    순위 산정 에이전트

    주요 기능:
    - 4개 그룹별 상위 종목 선정:
      - KOSPI Top 10에서 3개
      - KOSPI 11~20에서 3개
      - KOSDAQ Top 10에서 3개
      - 상위 3개 섹터에서 각 3개 (9개)
    - 최종 18개 종목 선정
    - 최종 Top 3 선정 (가중치: 총점 70%, 수급 15%, 성장성 15%)

    사용 예시:
        agent = RankingAgent()
        result = await agent.rank()

        print(result.final_top3)
    """

    stock_analyzer: StockAnalyzer = field(default_factory=StockAnalyzer)
    sector_analyzer: SectorAnalyzer = field(default_factory=SectorAnalyzer)

    # 그룹별 선정 개수
    stocks_per_market_group: int = 3  # KOSPI Top10, 11-20, KOSDAQ Top10 각각
    stocks_per_sector: int = 3        # 섹터별
    top_sector_count: int = 3         # 상위 섹터 수

    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        BaseAgent 인터페이스 구현.
        전체 순위 산정 결과를 반환합니다.
        """
        result = await self.rank()
        return result.to_dict()

    async def rank(self) -> RankingResult:
        """
        전체 순위를 산정합니다.

        Returns:
            RankingResult
        """
        self._log_info("Starting ranking process")

        result = RankingResult()

        # 1. KOSPI Top 20 분석
        self._log_info("Analyzing KOSPI top 20")
        kospi_results = await self.stock_analyzer.analyze_kospi_top(20)

        # KOSPI Top 10에서 상위 선정
        kospi_top10_stocks = [s for s in kospi_results.values() if s.group == "kospi_top10"]
        result.kospi_top10 = self.select_top_from_group(
            kospi_top10_stocks, self.stocks_per_market_group
        )

        # KOSPI 11~20에서 상위 선정
        kospi_11_20_stocks = [s for s in kospi_results.values() if s.group == "kospi_11_20"]
        result.kospi_11_20 = self.select_top_from_group(
            kospi_11_20_stocks, self.stocks_per_market_group
        )

        # 2. KOSDAQ Top 10 분석
        self._log_info("Analyzing KOSDAQ top 10")
        kosdaq_results = await self.stock_analyzer.analyze_kosdaq_top(10)
        kosdaq_stocks = list(kosdaq_results.values())
        result.kosdaq_top10 = self.select_top_from_group(
            kosdaq_stocks, self.stocks_per_market_group
        )

        # 3. 섹터 분석 및 상위 3개 섹터 선정
        self._log_info("Analyzing sectors")
        sector_results = await self.sector_analyzer.analyze()
        result.top_sectors = self.sector_analyzer.get_top_sectors(
            sector_results, self.top_sector_count
        )

        # 상위 섹터별 상위 종목 선정
        sector_top_stocks: List[StockAnalysisResult] = []
        for sector_result in result.top_sectors:
            top_stocks = self.sector_analyzer.get_sector_stocks_sorted(
                sector_result, self.stocks_per_sector
            )
            sector_top_stocks.extend(top_stocks)
        result.sector_top = sector_top_stocks

        # 4. 최종 18개 종목 집계
        self._log_info("Compiling final 18 stocks")
        all_selected = (
            result.kospi_top10 +
            result.kospi_11_20 +
            result.kosdaq_top10 +
            result.sector_top
        )

        # 중복 제거 (같은 종목이 여러 그룹에 포함될 수 있음)
        seen_symbols = set()
        unique_stocks: List[StockAnalysisResult] = []
        for stock in all_selected:
            if stock.symbol not in seen_symbols:
                seen_symbols.add(stock.symbol)
                unique_stocks.append(stock)

        # 점수순 정렬 및 순위 부여
        unique_stocks.sort(key=lambda x: x.total_score, reverse=True)
        for i, stock in enumerate(unique_stocks, 1):
            stock.final_rank = i

        result.final_18 = unique_stocks[:18]

        # 5. 최종 Top 3 선정
        self._log_info("Selecting final top 3")
        result.final_top3 = self.select_final_top3(result.final_18)

        self._log_info(f"Ranking complete: {len(result.final_18)} stocks, top 3 selected")
        return result

    def select_top_from_group(
        self,
        stocks: List[StockAnalysisResult],
        top_n: int = 3
    ) -> List[StockAnalysisResult]:
        """
        그룹 내 상위 N개 종목을 선정합니다.

        Args:
            stocks: 종목 리스트
            top_n: 선정할 종목 수

        Returns:
            상위 N개 StockAnalysisResult 리스트
        """
        # 점수순 정렬
        sorted_stocks = sorted(stocks, key=lambda s: s.total_score, reverse=True)

        # 그룹 내 순위 부여
        for i, stock in enumerate(sorted_stocks, 1):
            stock.rank_in_group = i

        return sorted_stocks[:top_n]

    def select_final_top3(
        self,
        all_selected: List[StockAnalysisResult]
    ) -> List[StockAnalysisResult]:
        """
        최종 Top 3를 선정합니다.

        선정 기준:
        - 총점 (70% 가중치)
        - 수급 점수 (15% 가중치)
        - 성장성 점수 (15% 가중치)

        동점 처리:
        1. 수급 점수 높은 종목
        2. 거래대금 (시가총액으로 대체)
        3. 시가총액 높은 종목

        Args:
            all_selected: 선정된 종목 리스트

        Returns:
            Top 3 StockAnalysisResult 리스트
        """
        def final_score(stock: StockAnalysisResult) -> float:
            """
            최종 점수 계산
            - 총점: 70%
            - 수급: 15% (20점 만점 → 100점 환산)
            - 성장성 (fundamental): 15% (20점 만점 → 100점 환산)
            """
            supply_normalized = stock.supply_score * 5  # 20점 → 100점
            fundamental_normalized = stock.fundamental_score * 5  # 20점 → 100점

            return (
                stock.total_score * 0.70 +
                supply_normalized * 0.15 +
                fundamental_normalized * 0.15
            )

        def tiebreaker(stock: StockAnalysisResult) -> tuple:
            """
            동점 시 우선순위:
            1. 수급 점수 (높을수록 좋음)
            2. 시가총액 (높을수록 좋음)
            """
            return (stock.supply_score, stock.market_cap)

        # 최종 점수 계산 및 정렬
        scored_stocks = [
            (stock, final_score(stock), tiebreaker(stock))
            for stock in all_selected
        ]

        # 1차: 최종 점수 내림차순, 2차: 동점자 처리
        scored_stocks.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return [stock for stock, _, _ in scored_stocks[:3]]

    async def get_group_details(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        각 그룹별 상세 정보를 반환합니다.

        Returns:
            그룹명을 키로 하는 종목 정보 딕셔너리
        """
        result = await self.rank()

        return {
            "kospi_top10": [s.to_dict() for s in result.kospi_top10],
            "kospi_11_20": [s.to_dict() for s in result.kospi_11_20],
            "kosdaq_top10": [s.to_dict() for s in result.kosdaq_top10],
            "sector_top": [s.to_dict() for s in result.sector_top],
        }
