"""
StockAnalyzer 테스트

개별 종목 분석기의 단위 테스트.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

from src.agents.analysis.stock_analyzer import StockAnalyzer, StockAnalysisResult
from src.agents.data.market_data_agent import MarketData
from src.agents.data.fundamental_agent import FundamentalData
from src.agents.data.news_agent import NewsData
from src.core.rubric import RubricResult


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_market_data():
    """Mock 시장 데이터"""
    return MarketData(
        symbol="005930",
        name="삼성전자",
        market="KOSPI",
        current_price=70000,
        price_change_pct=1.5,
        volume=10000000,
        avg_volume_20d=8000000,
        rsi=55,
        ma20=68000,
        ma60=65000,
        macd=500,
        macd_signal=300,
        adx=25,
        atr=1500,
        atr_pct=2.1,
        beta=1.1,
        max_drawdown_pct=-15.0,
        return_20d=5.0,
    )


@pytest.fixture
def mock_fundamental_data():
    """Mock 펀더멘털 데이터"""
    return FundamentalData(
        symbol="005930",
        name="삼성전자",
        sector="반도체",
        per=12.5,
        pbr=1.2,
        roe=15.0,
        operating_margin=18.0,
        revenue_growth=10.0,
        operating_profit_growth=12.0,
        debt_ratio=35.0,
    )


@pytest.fixture
def mock_news_data():
    """Mock 뉴스 데이터"""
    return NewsData(
        symbol="005930",
        name="삼성전자",
        total_count=15,
        positive_count=10,
        negative_count=3,
        neutral_count=2,
        avg_sentiment_score=0.6,
    )


@pytest.fixture
def mock_rubric_result():
    """Mock 루브릭 결과"""
    from src.core.rubric import CategoryScore

    return RubricResult(
        symbol="005930",
        name="삼성전자",
        technical=CategoryScore(name="technical", score=80.0, max_score=25, weighted_score=20.0),
        supply=CategoryScore(name="supply", score=80.0, max_score=20, weighted_score=16.0),
        fundamental=CategoryScore(name="fundamental", score=80.0, max_score=20, weighted_score=16.0),
        market=CategoryScore(name="market", score=80.0, max_score=15, weighted_score=12.0),
        risk=CategoryScore(name="risk", score=80.0, max_score=10, weighted_score=8.0),
        relative_strength=CategoryScore(name="relative_strength", score=80.0, max_score=10, weighted_score=8.0),
        total_score=80.0,
        grade="Strong Buy",
    )


# =============================================================================
# StockAnalysisResult 테스트
# =============================================================================


class TestStockAnalysisResult:
    """StockAnalysisResult 데이터 클래스 테스트"""

    def test_create_result(self):
        """결과 생성 테스트"""
        result = StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="kospi_top10",
            market_cap=4000000,
            total_score=75.5,
            investment_grade="Buy",
        )

        assert result.symbol == "005930"
        assert result.name == "삼성전자"
        assert result.sector == "반도체"
        assert result.group == "kospi_top10"
        assert result.market_cap == 4000000
        assert result.total_score == 75.5
        assert result.investment_grade == "Buy"

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        result = StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="kospi_top10",
            market_cap=4000000,
            technical_score=20.0,
            supply_score=16.0,
            fundamental_score=16.0,
            market_score=12.0,
            total_score=75.5,
            investment_grade="Buy",
            rank_in_group=1,
        )

        d = result.to_dict()

        assert d["symbol"] == "005930"
        assert d["name"] == "삼성전자"
        assert d["technical_score"] == 20.0
        assert d["rank_in_group"] == 1
        assert d["final_rank"] is None

    def test_default_values(self):
        """기본값 테스트"""
        result = StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="custom",
            market_cap=0,
        )

        assert result.technical_score == 0.0
        assert result.supply_score == 0.0
        assert result.total_score == 0.0
        assert result.investment_grade == "Hold"
        assert result.rank_in_group == 0
        assert result.final_rank is None


# =============================================================================
# StockAnalyzer 테스트
# =============================================================================


class TestStockAnalyzer:
    """StockAnalyzer 테스트"""

    @pytest.fixture
    def analyzer(self):
        """테스트용 분석기"""
        return StockAnalyzer()

    def test_init(self, analyzer):
        """초기화 테스트"""
        assert analyzer.market_data_agent is not None
        assert analyzer.fundamental_agent is not None
        assert analyzer.news_agent is not None
        assert analyzer.rubric_engine is not None
        assert analyzer.fetcher is not None

    @pytest.mark.asyncio
    async def test_analyze_single_with_mock(
        self,
        analyzer,
        mock_market_data,
        mock_fundamental_data,
        mock_news_data,
        mock_rubric_result,
    ):
        """단일 종목 분석 테스트 (Mock 사용)"""
        # Mock 설정
        with patch.object(analyzer.fetcher, 'get_stock_name', return_value="삼성전자"):
            with patch.object(analyzer.rubric_engine, 'calculate', return_value=mock_rubric_result):
                result = analyzer._analyze_single(
                    symbol="005930",
                    group="kospi_top10",
                    market_data=mock_market_data,
                    fundamental_data=mock_fundamental_data,
                    news_data=mock_news_data,
                    market_cap=4000000,
                )

        assert result is not None
        assert result.symbol == "005930"
        assert result.name == "삼성전자"
        assert result.group == "kospi_top10"
        assert result.market_cap == 4000000
        assert result.total_score == 80.0
        assert result.investment_grade == "Strong Buy"

    @pytest.mark.asyncio
    async def test_analyze_symbols_with_mock(self, analyzer):
        """여러 종목 분석 테스트 (Mock 사용)"""
        # Mock 에이전트들 설정
        mock_market_data = {
            "005930": MarketData(symbol="005930", name="삼성전자", market="KOSPI", current_price=70000),
            "000660": MarketData(symbol="000660", name="SK하이닉스", market="KOSPI", current_price=150000),
        }
        mock_fundamental_data = {
            "005930": FundamentalData(symbol="005930", name="삼성전자"),
            "000660": FundamentalData(symbol="000660", name="SK하이닉스"),
        }
        mock_news_data = {
            "005930": NewsData(symbol="005930", name="삼성전자", avg_sentiment_score=0.5),
            "000660": NewsData(symbol="000660", name="SK하이닉스", avg_sentiment_score=0.6),
        }

        analyzer.market_data_agent.collect = AsyncMock(return_value=mock_market_data)
        analyzer.fundamental_agent.collect = AsyncMock(return_value=mock_fundamental_data)
        analyzer.news_agent.collect = AsyncMock(return_value=mock_news_data)

        with patch.object(analyzer, '_get_market_caps', return_value={"005930": 4000000, "000660": 1000000}):
            with patch.object(analyzer.fetcher, 'get_stock_name', side_effect=lambda x: "삼성전자" if x == "005930" else "SK하이닉스"):
                results = await analyzer.analyze_symbols(["005930", "000660"], group="test_group")

        assert len(results) == 2
        assert "005930" in results
        assert "000660" in results

    def test_get_market_caps(self, analyzer):
        """시가총액 조회 테스트"""
        # Mock KRX 리스팅
        import pandas as pd

        mock_krx = pd.DataFrame({
            "Code": ["005930", "000660"],
            "Marcap": [400000000000000, 100000000000000],  # 원 단위
        })

        with patch.object(analyzer.fetcher, '_get_krx_listing', return_value=mock_krx):
            result = analyzer._get_market_caps(["005930", "000660"])

        assert "005930" in result
        assert "000660" in result
        # 억원 단위로 변환
        assert result["005930"] == 4000000
        assert result["000660"] == 1000000


# =============================================================================
# 그룹별 분석 테스트
# =============================================================================


class TestStockAnalyzerGroups:
    """그룹별 분석 테스트"""

    @pytest.fixture
    def analyzer(self):
        """테스트용 분석기"""
        return StockAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_kospi_top_mock(self, analyzer):
        """KOSPI Top 분석 테스트 (Mock)"""
        mock_symbols = [f"00000{i}" for i in range(20)]

        with patch.object(analyzer.fetcher, 'get_market_cap_rank', return_value=mock_symbols):
            with patch.object(analyzer, 'analyze_symbols', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {}
                await analyzer.analyze_kospi_top(20)

        # analyze_symbols가 두 번 호출됨 (top10, 11-20)
        assert mock_analyze.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_kosdaq_top_mock(self, analyzer):
        """KOSDAQ Top 분석 테스트 (Mock)"""
        mock_symbols = [f"00000{i}" for i in range(10)]

        with patch.object(analyzer.fetcher, 'get_market_cap_rank', return_value=mock_symbols):
            with patch.object(analyzer, 'analyze_symbols', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {}
                await analyzer.analyze_kosdaq_top(10)

        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args.kwargs.get('group') == "kosdaq_top10"

    @pytest.mark.asyncio
    async def test_analyze_sector_valid(self, analyzer):
        """유효한 섹터 분석 테스트"""
        with patch.object(analyzer, 'analyze_symbols', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {}
            await analyzer.analyze_sector("반도체")

        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args.kwargs.get('group') == "sector_반도체"

    @pytest.mark.asyncio
    async def test_analyze_sector_invalid(self, analyzer):
        """유효하지 않은 섹터 분석 테스트"""
        result = await analyzer.analyze_sector("존재하지않는섹터")
        assert result == {}

    @pytest.mark.asyncio
    async def test_analyze_all_sectors(self, analyzer):
        """모든 섹터 분석 테스트"""
        with patch.object(analyzer, 'analyze_sector', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {}
            results = await analyzer.analyze_all_sectors()

        # 11개 섹터가 분석되어야 함
        assert mock_analyze.call_count == 11


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================


class TestStockAnalyzerEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.fixture
    def analyzer(self):
        return StockAnalyzer()

    def test_analyze_single_no_market_data(self, analyzer):
        """시장 데이터 없이 분석"""
        with patch.object(analyzer.fetcher, 'get_stock_name', return_value="테스트종목"):
            result = analyzer._analyze_single(
                symbol="999999",
                group="test",
                market_data=None,
                fundamental_data=None,
                news_data=None,
                market_cap=0,
            )

        assert result is not None
        assert result.symbol == "999999"

    def test_analyze_single_partial_data(self, analyzer, mock_market_data):
        """부분 데이터로 분석"""
        with patch.object(analyzer.fetcher, 'get_stock_name', return_value="테스트종목"):
            result = analyzer._analyze_single(
                symbol="005930",
                group="test",
                market_data=mock_market_data,
                fundamental_data=None,
                news_data=None,
                market_cap=1000,
            )

        assert result is not None
        assert result.market_cap == 1000

    @pytest.mark.asyncio
    async def test_collect_interface(self, analyzer):
        """BaseAgent collect 인터페이스 테스트"""
        with patch.object(analyzer, 'analyze_symbols', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"005930": StockAnalysisResult(
                symbol="005930",
                name="삼성전자",
                sector="반도체",
                group="custom",
                market_cap=4000000,
            )}
            result = await analyzer.collect(["005930"])

        assert "005930" in result
        mock_analyze.assert_called_once_with(["005930"])
