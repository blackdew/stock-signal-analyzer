"""
SectorAnalyzer 테스트

섹터 분석기의 단위 테스트.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.agents.analysis.sector_analyzer import SectorAnalyzer, SectorAnalysisResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_stock_results():
    """Mock 종목 분석 결과"""
    return {
        "005930": StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="sector_반도체",
            market_cap=4000000,
            technical_score=20.0,
            supply_score=16.0,
            fundamental_score=18.0,
            market_score=12.0,
            total_score=80.0,
            investment_grade="Strong Buy",
        ),
        "000660": StockAnalysisResult(
            symbol="000660",
            name="SK하이닉스",
            sector="반도체",
            group="sector_반도체",
            market_cap=1000000,
            technical_score=18.0,
            supply_score=14.0,
            fundamental_score=15.0,
            market_score=10.0,
            total_score=70.0,
            investment_grade="Buy",
        ),
        "042700": StockAnalysisResult(
            symbol="042700",
            name="한미반도체",
            sector="반도체",
            group="sector_반도체",
            market_cap=200000,
            technical_score=15.0,
            supply_score=12.0,
            fundamental_score=14.0,
            market_score=8.0,
            total_score=60.0,
            investment_grade="Buy",
        ),
    }


@pytest.fixture
def mock_all_sector_results(mock_stock_results):
    """모든 섹터의 Mock 결과"""
    return {
        "반도체": mock_stock_results,
        "조선": {
            "010140": StockAnalysisResult(
                symbol="010140",
                name="삼성중공업",
                sector="조선",
                group="sector_조선",
                market_cap=300000,
                total_score=65.0,
                investment_grade="Buy",
            ),
        },
    }


# =============================================================================
# SectorAnalysisResult 테스트
# =============================================================================


class TestSectorAnalysisResult:
    """SectorAnalysisResult 데이터 클래스 테스트"""

    def test_create_result(self):
        """결과 생성 테스트"""
        result = SectorAnalysisResult(
            sector_name="반도체",
            stock_count=5,
            total_market_cap=5500000,
            weighted_score=75.5,
            simple_score=70.0,
        )

        assert result.sector_name == "반도체"
        assert result.stock_count == 5
        assert result.total_market_cap == 5500000
        assert result.weighted_score == 75.5
        assert result.simple_score == 70.0

    def test_to_dict(self, mock_stock_results):
        """딕셔너리 변환 테스트"""
        stocks = list(mock_stock_results.values())
        result = SectorAnalysisResult(
            sector_name="반도체",
            stock_count=3,
            total_market_cap=5200000,
            weighted_score=76.92,
            simple_score=70.0,
            technical_score=19.0,
            supply_score=15.0,
            fundamental_score=16.5,
            market_score=11.0,
            top_stocks=stocks[:2],
            rank=1,
        )

        d = result.to_dict()

        assert d["sector_name"] == "반도체"
        assert d["weighted_score"] == 76.92
        assert d["rank"] == 1
        assert len(d["top_stocks"]) == 2

    def test_default_values(self):
        """기본값 테스트"""
        result = SectorAnalysisResult(
            sector_name="테스트",
            stock_count=0,
            total_market_cap=0,
            weighted_score=0,
            simple_score=0,
        )

        assert result.technical_score == 0.0
        assert result.supply_score == 0.0
        assert result.top_stocks == []
        assert result.rank == 0


# =============================================================================
# SectorAnalyzer 테스트
# =============================================================================


class TestSectorAnalyzer:
    """SectorAnalyzer 테스트"""

    @pytest.fixture
    def analyzer(self):
        """테스트용 분석기"""
        return SectorAnalyzer()

    def test_init(self, analyzer):
        """초기화 테스트"""
        assert analyzer.stock_analyzer is not None
        assert analyzer.use_weighted_average is True

    def test_init_with_simple_average(self):
        """단순 평균 모드 초기화"""
        analyzer = SectorAnalyzer(use_weighted_average=False)
        assert analyzer.use_weighted_average is False

    def test_calculate_sector_score(self, analyzer, mock_stock_results):
        """섹터 점수 계산 테스트"""
        result = analyzer._calculate_sector_score("반도체", mock_stock_results)

        assert result.sector_name == "반도체"
        assert result.stock_count == 3

        # 총 시가총액: 4,000,000 + 1,000,000 + 200,000 = 5,200,000
        assert result.total_market_cap == 5200000

        # 단순 평균: (80 + 70 + 60) / 3 = 70
        assert result.simple_score == 70.0

        # 가중 평균 계산
        # 80 * (4M/5.2M) + 70 * (1M/5.2M) + 60 * (0.2M/5.2M)
        # = 80 * 0.769 + 70 * 0.192 + 60 * 0.038
        # = 61.52 + 13.44 + 2.28 = 77.24
        assert 76.0 <= result.weighted_score <= 78.0

        # 상위 종목 확인 (점수순)
        assert len(result.top_stocks) <= 5
        assert result.top_stocks[0].total_score >= result.top_stocks[1].total_score

    def test_calculate_sector_score_zero_market_cap(self, analyzer):
        """시가총액이 0인 경우"""
        zero_cap_results = {
            "001": StockAnalysisResult(
                symbol="001",
                name="테스트1",
                sector="테스트",
                group="test",
                market_cap=0,
                total_score=70.0,
            ),
            "002": StockAnalysisResult(
                symbol="002",
                name="테스트2",
                sector="테스트",
                group="test",
                market_cap=0,
                total_score=80.0,
            ),
        }

        result = analyzer._calculate_sector_score("테스트", zero_cap_results)

        # 시가총액이 0이면 단순 평균 사용
        assert result.weighted_score == 75.0
        assert result.simple_score == 75.0

    def test_get_top_sectors(self, analyzer):
        """상위 섹터 조회 테스트"""
        sector_results = [
            SectorAnalysisResult(
                sector_name="반도체",
                stock_count=5,
                total_market_cap=5000000,
                weighted_score=80.0,
                simple_score=75.0,
            ),
            SectorAnalysisResult(
                sector_name="조선",
                stock_count=5,
                total_market_cap=1000000,
                weighted_score=70.0,
                simple_score=68.0,
            ),
            SectorAnalysisResult(
                sector_name="바이오",
                stock_count=5,
                total_market_cap=2000000,
                weighted_score=75.0,
                simple_score=72.0,
            ),
        ]

        top3 = analyzer.get_top_sectors(sector_results, top_n=3)
        assert len(top3) == 3
        assert top3[0].sector_name == "반도체"  # 80점
        assert top3[1].sector_name == "바이오"  # 75점
        assert top3[2].sector_name == "조선"    # 70점

    def test_get_top_sectors_simple_average(self):
        """단순 평균 모드에서 상위 섹터 조회"""
        analyzer = SectorAnalyzer(use_weighted_average=False)

        sector_results = [
            SectorAnalysisResult(
                sector_name="반도체",
                stock_count=5,
                total_market_cap=5000000,
                weighted_score=80.0,
                simple_score=70.0,  # 단순 평균은 더 낮음
            ),
            SectorAnalysisResult(
                sector_name="바이오",
                stock_count=5,
                total_market_cap=2000000,
                weighted_score=75.0,
                simple_score=78.0,  # 단순 평균은 더 높음
            ),
        ]

        top2 = analyzer.get_top_sectors(sector_results, top_n=2)
        assert top2[0].sector_name == "바이오"  # 단순 평균 78점
        assert top2[1].sector_name == "반도체"  # 단순 평균 70점

    @pytest.mark.asyncio
    async def test_analyze(self, analyzer, mock_all_sector_results):
        """전체 섹터 분석 테스트"""
        with patch.object(
            analyzer.stock_analyzer,
            'analyze_all_sectors',
            new_callable=AsyncMock,
            return_value=mock_all_sector_results
        ):
            results = await analyzer.analyze()

        assert len(results) == 2

        # 순위가 부여됨
        assert results[0].rank == 1
        assert results[1].rank == 2

        # 점수순 정렬됨
        assert results[0].weighted_score >= results[1].weighted_score

    @pytest.mark.asyncio
    async def test_analyze_single_sector(self, analyzer, mock_stock_results):
        """단일 섹터 분석 테스트"""
        with patch.object(
            analyzer.stock_analyzer,
            'analyze_sector',
            new_callable=AsyncMock,
            return_value=mock_stock_results
        ):
            result = await analyzer.analyze_single_sector("반도체")

        assert result is not None
        assert result.sector_name == "반도체"
        assert result.stock_count == 3

    @pytest.mark.asyncio
    async def test_analyze_single_sector_invalid(self, analyzer):
        """유효하지 않은 섹터 분석"""
        result = await analyzer.analyze_single_sector("존재하지않는섹터")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_single_sector_no_results(self, analyzer):
        """결과가 없는 섹터 분석"""
        with patch.object(
            analyzer.stock_analyzer,
            'analyze_sector',
            new_callable=AsyncMock,
            return_value={}
        ):
            result = await analyzer.analyze_single_sector("반도체")

        assert result is None

    def test_get_sector_stocks_sorted(self, analyzer, mock_stock_results):
        """섹터 내 종목 정렬 테스트"""
        stocks = list(mock_stock_results.values())
        sector_result = SectorAnalysisResult(
            sector_name="반도체",
            stock_count=3,
            total_market_cap=5200000,
            weighted_score=76.0,
            simple_score=70.0,
            top_stocks=sorted(stocks, key=lambda x: x.total_score, reverse=True),
        )

        # 전체
        all_stocks = analyzer.get_sector_stocks_sorted(sector_result)
        assert len(all_stocks) == 3

        # Top 2
        top2 = analyzer.get_sector_stocks_sorted(sector_result, top_n=2)
        assert len(top2) == 2
        assert top2[0].total_score >= top2[1].total_score

    @pytest.mark.asyncio
    async def test_collect_interface(self, analyzer, mock_all_sector_results):
        """BaseAgent collect 인터페이스 테스트"""
        with patch.object(
            analyzer.stock_analyzer,
            'analyze_all_sectors',
            new_callable=AsyncMock,
            return_value=mock_all_sector_results
        ):
            result = await analyzer.collect([])

        assert "반도체" in result
        assert "조선" in result


# =============================================================================
# 가중 평균 계산 검증 테스트
# =============================================================================


class TestWeightedAverageCalculation:
    """가중 평균 계산 정확성 테스트"""

    def test_weighted_average_large_cap_dominance(self):
        """대형주가 지배적인 경우"""
        analyzer = SectorAnalyzer()

        results = {
            "large": StockAnalysisResult(
                symbol="large",
                name="대형주",
                sector="테스트",
                group="test",
                market_cap=9000,  # 90%
                total_score=90.0,
                technical_score=22.0,
            ),
            "small": StockAnalysisResult(
                symbol="small",
                name="소형주",
                sector="테스트",
                group="test",
                market_cap=1000,  # 10%
                total_score=50.0,
                technical_score=12.0,
            ),
        }

        sector_result = analyzer._calculate_sector_score("테스트", results)

        # 가중 평균: 90 * 0.9 + 50 * 0.1 = 81 + 5 = 86
        assert 85.0 <= sector_result.weighted_score <= 87.0

        # 단순 평균: (90 + 50) / 2 = 70
        assert sector_result.simple_score == 70.0

    def test_weighted_average_equal_caps(self):
        """시가총액이 같은 경우"""
        analyzer = SectorAnalyzer()

        results = {
            "a": StockAnalysisResult(
                symbol="a",
                name="A",
                sector="테스트",
                group="test",
                market_cap=1000,
                total_score=80.0,
            ),
            "b": StockAnalysisResult(
                symbol="b",
                name="B",
                sector="테스트",
                group="test",
                market_cap=1000,
                total_score=60.0,
            ),
        }

        sector_result = analyzer._calculate_sector_score("테스트", results)

        # 가중 평균 = 단순 평균 (시총이 같으므로)
        assert sector_result.weighted_score == sector_result.simple_score == 70.0
