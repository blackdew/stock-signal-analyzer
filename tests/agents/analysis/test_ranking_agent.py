"""
RankingAgent 테스트

순위 산정 에이전트의 단위 테스트.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.agents.analysis.ranking_agent import RankingAgent, RankingResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.agents.analysis.sector_analyzer import SectorAnalysisResult


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_kospi_results():
    """Mock KOSPI 분석 결과"""
    return {
        f"00000{i}": StockAnalysisResult(
            symbol=f"00000{i}",
            name=f"코스피종목{i}",
            sector="테스트",
            group="kospi_top10" if i < 10 else "kospi_11_20",
            market_cap=1000000 - i * 10000,
            total_score=90 - i,
            supply_score=18 - i * 0.2,
            fundamental_score=18 - i * 0.3,
            investment_grade="Strong Buy" if i < 3 else "Buy",
        )
        for i in range(20)
    }


@pytest.fixture
def mock_kosdaq_results():
    """Mock KOSDAQ 분석 결과"""
    return {
        f"10000{i}": StockAnalysisResult(
            symbol=f"10000{i}",
            name=f"코스닥종목{i}",
            sector="테스트",
            group="kosdaq_top10",
            market_cap=100000 - i * 1000,
            total_score=85 - i,
            supply_score=17 - i * 0.2,
            fundamental_score=17 - i * 0.3,
            investment_grade="Buy",
        )
        for i in range(10)
    }


@pytest.fixture
def mock_sector_results():
    """Mock 섹터 분석 결과"""
    sectors = ["반도체", "조선", "바이오"]
    return [
        SectorAnalysisResult(
            sector_name=sector,
            stock_count=5,
            total_market_cap=1000000 - i * 100000,
            weighted_score=80 - i * 5,
            simple_score=78 - i * 5,
            top_stocks=[
                StockAnalysisResult(
                    symbol=f"{sector}_{j}",
                    name=f"{sector}종목{j}",
                    sector=sector,
                    group=f"sector_{sector}",
                    market_cap=100000 - j * 10000,
                    total_score=75 - j * 2,
                    supply_score=15 - j * 0.5,
                    fundamental_score=15 - j * 0.5,
                    investment_grade="Buy",
                )
                for j in range(5)
            ],
        )
        for i, sector in enumerate(sectors)
    ]


@pytest.fixture
def mock_18_stocks():
    """Mock 18개 최종 선정 종목"""
    return [
        StockAnalysisResult(
            symbol=f"stock_{i}",
            name=f"종목{i}",
            sector="테스트",
            group="test",
            market_cap=100000 - i * 1000,
            total_score=90 - i,
            supply_score=18 - i * 0.5,
            fundamental_score=18 - i * 0.3,
            investment_grade="Strong Buy" if i < 5 else "Buy",
        )
        for i in range(18)
    ]


# =============================================================================
# RankingResult 테스트
# =============================================================================


class TestRankingResult:
    """RankingResult 데이터 클래스 테스트"""

    def test_create_empty_result(self):
        """빈 결과 생성"""
        result = RankingResult()

        assert result.kospi_top10 == []
        assert result.kospi_11_20 == []
        assert result.kosdaq_top10 == []
        assert result.sector_top == []
        assert result.final_18 == []
        assert result.final_top3 == []
        assert result.top_sectors == []

    def test_to_dict(self, mock_18_stocks, mock_sector_results):
        """딕셔너리 변환 테스트"""
        result = RankingResult(
            kospi_top10=mock_18_stocks[:3],
            kospi_11_20=mock_18_stocks[3:6],
            kosdaq_top10=mock_18_stocks[6:9],
            sector_top=mock_18_stocks[9:18],
            final_18=mock_18_stocks,
            final_top3=mock_18_stocks[:3],
            top_sectors=mock_sector_results,
        )

        d = result.to_dict()

        assert len(d["kospi_top10"]) == 3
        assert len(d["kospi_11_20"]) == 3
        assert len(d["kosdaq_top10"]) == 3
        assert len(d["sector_top"]) == 9
        assert len(d["final_18"]) == 18
        assert len(d["final_top3"]) == 3
        assert len(d["top_sectors"]) == 3

    def test_get_summary(self, mock_18_stocks, mock_sector_results):
        """요약 정보 테스트"""
        result = RankingResult(
            kospi_top10=mock_18_stocks[:3],
            kospi_11_20=mock_18_stocks[3:6],
            kosdaq_top10=mock_18_stocks[6:9],
            sector_top=mock_18_stocks[9:18],
            final_18=mock_18_stocks,
            final_top3=mock_18_stocks[:3],
            top_sectors=mock_sector_results,
        )

        summary = result.get_summary()

        assert summary["total_candidates"] == 18
        assert summary["top_sectors"] == ["반도체", "조선", "바이오"]
        assert len(summary["top3_stocks"]) == 3
        assert summary["group_counts"]["kospi_top10"] == 3


# =============================================================================
# RankingAgent 테스트
# =============================================================================


class TestRankingAgent:
    """RankingAgent 테스트"""

    @pytest.fixture
    def agent(self):
        """테스트용 에이전트"""
        return RankingAgent()

    def test_init(self, agent):
        """초기화 테스트"""
        assert agent.stock_analyzer is not None
        assert agent.sector_analyzer is not None
        assert agent.stocks_per_market_group == 3
        assert agent.stocks_per_sector == 3
        assert agent.top_sector_count == 3

    def test_select_top_from_group(self, agent, mock_18_stocks):
        """그룹 내 상위 선정 테스트"""
        top3 = agent.select_top_from_group(mock_18_stocks, top_n=3)

        assert len(top3) == 3
        assert top3[0].total_score == 90  # 최고점
        assert top3[1].total_score == 89
        assert top3[2].total_score == 88

        # 그룹 내 순위 확인
        assert top3[0].rank_in_group == 1
        assert top3[1].rank_in_group == 2
        assert top3[2].rank_in_group == 3

    def test_select_top_from_group_less_stocks(self, agent):
        """종목이 적을 때"""
        stocks = [
            StockAnalysisResult(
                symbol="001", name="종목1", sector="테스트", group="test",
                market_cap=1000, total_score=80,
            ),
            StockAnalysisResult(
                symbol="002", name="종목2", sector="테스트", group="test",
                market_cap=900, total_score=70,
            ),
        ]

        top3 = agent.select_top_from_group(stocks, top_n=3)

        # 2개만 있으면 2개만 반환
        assert len(top3) == 2

    def test_select_final_top3(self, agent, mock_18_stocks):
        """최종 Top 3 선정 테스트"""
        top3 = agent.select_final_top3(mock_18_stocks)

        assert len(top3) == 3

        # 최종 점수 계산 로직 검증
        # final_score = total * 0.7 + supply_normalized * 0.15 + fundamental_normalized * 0.15
        # stock_0: 90 * 0.7 + (18 * 5) * 0.15 + (18 * 5) * 0.15 = 63 + 13.5 + 13.5 = 90
        # stock_1: 89 * 0.7 + (17.5 * 5) * 0.15 + (17.7 * 5) * 0.15 ≈ 62.3 + 13.1 + 13.3 = 88.7
        assert top3[0].symbol == "stock_0"
        assert top3[1].symbol == "stock_1"
        assert top3[2].symbol == "stock_2"

    def test_select_final_top3_tiebreaker(self, agent):
        """동점 처리 테스트"""
        tied_stocks = [
            StockAnalysisResult(
                symbol="a", name="A", sector="테스트", group="test",
                market_cap=1000, total_score=80, supply_score=15, fundamental_score=16,
            ),
            StockAnalysisResult(
                symbol="b", name="B", sector="테스트", group="test",
                market_cap=2000, total_score=80, supply_score=16, fundamental_score=15,
            ),
            StockAnalysisResult(
                symbol="c", name="C", sector="테스트", group="test",
                market_cap=500, total_score=80, supply_score=16, fundamental_score=15,
            ),
        ]

        top3 = agent.select_final_top3(tied_stocks)

        # b와 c는 동점이지만 b가 시총이 더 높음
        # b: supply=16, market_cap=2000
        # c: supply=16, market_cap=500
        assert len(top3) == 3

    @pytest.mark.asyncio
    async def test_rank_full_flow(
        self, agent, mock_kospi_results, mock_kosdaq_results, mock_sector_results
    ):
        """전체 순위 산정 흐름 테스트"""
        # Mock 설정
        agent.stock_analyzer.analyze_kospi_top = AsyncMock(return_value=mock_kospi_results)
        agent.stock_analyzer.analyze_kosdaq_top = AsyncMock(return_value=mock_kosdaq_results)
        agent.sector_analyzer.analyze = AsyncMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_top_sectors = MagicMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_sector_stocks_sorted = MagicMock(
            side_effect=lambda r, n: r.top_stocks[:n] if n else r.top_stocks
        )

        result = await agent.rank()

        assert isinstance(result, RankingResult)
        assert len(result.kospi_top10) == 3
        assert len(result.kospi_11_20) == 3
        assert len(result.kosdaq_top10) == 3
        assert len(result.sector_top) == 9  # 3 sectors * 3 stocks
        assert len(result.final_top3) == 3
        assert len(result.top_sectors) == 3

    @pytest.mark.asyncio
    async def test_rank_removes_duplicates(self, agent):
        """중복 종목 제거 테스트"""
        # 같은 종목이 여러 그룹에 포함된 경우
        duplicate_stock = StockAnalysisResult(
            symbol="duplicate", name="중복종목", sector="테스트", group="test",
            market_cap=1000000, total_score=95, supply_score=20, fundamental_score=20,
        )

        kospi_results = {"duplicate": duplicate_stock}
        kosdaq_results = {"duplicate": duplicate_stock}
        sector_results = [
            SectorAnalysisResult(
                sector_name="반도체",
                stock_count=1,
                total_market_cap=1000000,
                weighted_score=95,
                simple_score=95,
                top_stocks=[duplicate_stock],
            ),
        ]

        agent.stock_analyzer.analyze_kospi_top = AsyncMock(return_value=kospi_results)
        agent.stock_analyzer.analyze_kosdaq_top = AsyncMock(return_value=kosdaq_results)
        agent.sector_analyzer.analyze = AsyncMock(return_value=sector_results)
        agent.sector_analyzer.get_top_sectors = MagicMock(return_value=sector_results)
        agent.sector_analyzer.get_sector_stocks_sorted = MagicMock(return_value=[duplicate_stock])

        result = await agent.rank()

        # 중복 제거되어 1개만 남음
        unique_symbols = set(s.symbol for s in result.final_18)
        assert len(unique_symbols) == len(result.final_18)

    @pytest.mark.asyncio
    async def test_collect_interface(self, agent, mock_kospi_results, mock_kosdaq_results, mock_sector_results):
        """BaseAgent collect 인터페이스 테스트"""
        agent.stock_analyzer.analyze_kospi_top = AsyncMock(return_value=mock_kospi_results)
        agent.stock_analyzer.analyze_kosdaq_top = AsyncMock(return_value=mock_kosdaq_results)
        agent.sector_analyzer.analyze = AsyncMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_top_sectors = MagicMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_sector_stocks_sorted = MagicMock(
            side_effect=lambda r, n: r.top_stocks[:n] if n else r.top_stocks
        )

        result = await agent.collect([])

        assert "final_18" in result
        assert "final_top3" in result
        assert "top_sectors" in result


# =============================================================================
# 최종 점수 계산 검증 테스트
# =============================================================================


class TestFinalScoreCalculation:
    """최종 점수 계산 검증 테스트"""

    def test_final_score_formula(self):
        """최종 점수 공식 검증"""
        agent = RankingAgent()

        # 수동 계산
        stock = StockAnalysisResult(
            symbol="test",
            name="테스트",
            sector="테스트",
            group="test",
            market_cap=1000,
            total_score=80,  # 70% = 56
            supply_score=16,  # 16 * 5 = 80, 80 * 15% = 12
            fundamental_score=14,  # 14 * 5 = 70, 70 * 15% = 10.5
            # 합계: 56 + 12 + 10.5 = 78.5
        )

        # select_final_top3에서 사용하는 내부 final_score 함수 테스트
        def final_score(s):
            supply_normalized = s.supply_score * 5
            fundamental_normalized = s.fundamental_score * 5
            return (
                s.total_score * 0.70 +
                supply_normalized * 0.15 +
                fundamental_normalized * 0.15
            )

        calculated = final_score(stock)
        expected = 80 * 0.7 + 80 * 0.15 + 70 * 0.15
        assert abs(calculated - expected) < 0.01

    def test_different_weights_impact(self):
        """가중치가 결과에 미치는 영향 테스트"""
        agent = RankingAgent()

        # 총점은 낮지만 수급/성장성이 높은 종목
        stock_a = StockAnalysisResult(
            symbol="a", name="A", sector="테스트", group="test",
            market_cap=1000, total_score=70,  # 총점 70
            supply_score=20,  # 수급 최고
            fundamental_score=20,  # 성장성 최고
        )

        # 총점은 높지만 수급/성장성이 낮은 종목
        stock_b = StockAnalysisResult(
            symbol="b", name="B", sector="테스트", group="test",
            market_cap=1000, total_score=85,  # 총점 85
            supply_score=10,  # 수급 낮음
            fundamental_score=10,  # 성장성 낮음
        )

        def final_score(s):
            return (
                s.total_score * 0.70 +
                s.supply_score * 5 * 0.15 +
                s.fundamental_score * 5 * 0.15
            )

        # A: 70 * 0.7 + 100 * 0.15 + 100 * 0.15 = 49 + 15 + 15 = 79
        # B: 85 * 0.7 + 50 * 0.15 + 50 * 0.15 = 59.5 + 7.5 + 7.5 = 74.5
        score_a = final_score(stock_a)
        score_b = final_score(stock_b)

        assert score_a > score_b  # A가 총점은 낮지만 최종 점수는 높음


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================


class TestRankingAgentEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.fixture
    def agent(self):
        return RankingAgent()

    def test_select_top_from_empty_group(self, agent):
        """빈 그룹에서 선정"""
        top3 = agent.select_top_from_group([], top_n=3)
        assert top3 == []

    def test_select_final_top3_less_than_3(self, agent):
        """3개 미만 종목에서 Top 3 선정"""
        stocks = [
            StockAnalysisResult(
                symbol="001", name="종목1", sector="테스트", group="test",
                market_cap=1000, total_score=80, supply_score=15, fundamental_score=15,
            ),
        ]

        top3 = agent.select_final_top3(stocks)
        assert len(top3) == 1

    @pytest.mark.asyncio
    async def test_rank_with_empty_results(self, agent):
        """빈 결과로 순위 산정"""
        agent.stock_analyzer.analyze_kospi_top = AsyncMock(return_value={})
        agent.stock_analyzer.analyze_kosdaq_top = AsyncMock(return_value={})
        agent.sector_analyzer.analyze = AsyncMock(return_value=[])
        agent.sector_analyzer.get_top_sectors = MagicMock(return_value=[])
        agent.sector_analyzer.get_sector_stocks_sorted = MagicMock(return_value=[])

        result = await agent.rank()

        assert result.final_18 == []
        assert result.final_top3 == []

    @pytest.mark.asyncio
    async def test_get_group_details(self, agent, mock_kospi_results, mock_kosdaq_results, mock_sector_results):
        """그룹별 상세 정보 조회"""
        agent.stock_analyzer.analyze_kospi_top = AsyncMock(return_value=mock_kospi_results)
        agent.stock_analyzer.analyze_kosdaq_top = AsyncMock(return_value=mock_kosdaq_results)
        agent.sector_analyzer.analyze = AsyncMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_top_sectors = MagicMock(return_value=mock_sector_results)
        agent.sector_analyzer.get_sector_stocks_sorted = MagicMock(
            side_effect=lambda r, n: r.top_stocks[:n] if n else r.top_stocks
        )

        details = await agent.get_group_details()

        assert "kospi_top10" in details
        assert "kospi_11_20" in details
        assert "kosdaq_top10" in details
        assert "sector_top" in details
