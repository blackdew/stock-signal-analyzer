"""
StockReportAgent 테스트

개별 종목 리포트 생성 에이전트의 단위 테스트.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.agents.report.stock_report_agent import StockReportAgent, GRADE_STARS
from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.core.rubric import RubricResult, CategoryScore


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_rubric_result():
    """Mock 루브릭 결과"""
    return RubricResult(
        symbol="005930",
        name="삼성전자",
        technical=CategoryScore(
            name="technical",
            score=80.0,
            max_score=25,
            weighted_score=20.0,
            details={
                "trend": 5.0,
                "rsi": 5.0,
                "rsi_value": 55.0,
                "support_resistance": 5.0,
                "macd": 3.0,
                "adx": 2.0,
            },
        ),
        supply=CategoryScore(
            name="supply",
            score=80.0,
            max_score=20,
            weighted_score=16.0,
            details={
                "foreign": 6.4,
                "institution": 6.4,
                "trading_value": 3.2,
            },
        ),
        fundamental=CategoryScore(
            name="fundamental",
            score=80.0,
            max_score=20,
            weighted_score=16.0,
            details={
                "per": 3.2,
                "pbr": 3.2,
                "roe": 3.2,
                "growth": 4.0,
                "debt": 2.4,
            },
        ),
        market=CategoryScore(
            name="market",
            score=80.0,
            max_score=15,
            weighted_score=12.0,
            details={
                "news": 6.0,
                "sector_momentum": 3.0,
                "analyst": 3.0,
            },
        ),
        risk=CategoryScore(
            name="risk",
            score=80.0,
            max_score=10,
            weighted_score=8.0,
            details={
                "volatility": 3.2,
                "beta": 2.4,
                "downside": 2.4,
            },
        ),
        relative_strength=CategoryScore(
            name="relative_strength",
            score=80.0,
            max_score=10,
            weighted_score=8.0,
            details={
                "sector_rank": 4.0,
                "alpha": 4.0,
            },
        ),
        total_score=80.0,
        grade="Strong Buy",
    )


@pytest.fixture
def mock_stock_result(mock_rubric_result):
    """Mock 종목 분석 결과"""
    return StockAnalysisResult(
        symbol="005930",
        name="삼성전자",
        sector="반도체",
        group="kospi_top10",
        market_cap=4500000,  # 450조
        rubric_result=mock_rubric_result,
        technical_score=20.0,
        supply_score=16.0,
        fundamental_score=16.0,
        market_score=12.0,
        risk_score=8.0,
        relative_strength_score=8.0,
        total_score=80.0,
        investment_grade="Strong Buy",
        rank_in_group=1,
        final_rank=1,
    )


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# StockReportAgent 테스트
# =============================================================================


class TestStockReportAgent:
    """StockReportAgent 테스트 클래스"""

    def test_init_creates_output_dir(self, temp_output_dir):
        """초기화 시 출력 디렉토리 생성 테스트"""
        output_dir = temp_output_dir / "stocks"
        agent = StockReportAgent(output_dir=output_dir)

        assert output_dir.exists()

    def test_format_market_cap_trillion(self):
        """시가총액 조 단위 포맷 테스트"""
        agent = StockReportAgent()

        result = agent._format_market_cap(45000)  # 4.5조
        assert "4.5조원" in result

    def test_format_market_cap_billion(self):
        """시가총액 억 단위 포맷 테스트"""
        agent = StockReportAgent()

        result = agent._format_market_cap(5000)
        assert "5,000억원" in result

    def test_translate_group_name_kospi_top10(self):
        """그룹명 한글화 테스트 - KOSPI Top 10"""
        agent = StockReportAgent()

        result = agent._translate_group_name("kospi_top10")
        assert "KOSPI" in result
        assert "10" in result

    def test_translate_group_name_sector(self):
        """그룹명 한글화 테스트 - 섹터"""
        agent = StockReportAgent()

        result = agent._translate_group_name("sector_반도체")
        assert "반도체" in result
        assert "섹터" in result

    def test_score_to_verdict_excellent(self):
        """점수 판정 테스트 - 매우 우수"""
        agent = StockReportAgent()

        result = agent._score_to_verdict(8.5, 10)
        assert result == "매우 우수"

    def test_score_to_verdict_neutral(self):
        """점수 판정 테스트 - 중립"""
        agent = StockReportAgent()

        result = agent._score_to_verdict(5.0, 10)
        assert result == "중립"

    def test_score_to_verdict_negative(self):
        """점수 판정 테스트 - 부정적"""
        agent = StockReportAgent()

        result = agent._score_to_verdict(2.5, 10)
        assert result == "부정적"

    def test_rsi_to_verdict_overbought(self):
        """RSI 판정 테스트 - 과매수"""
        agent = StockReportAgent()

        result = agent._rsi_to_verdict(75)
        assert "과매수" in result

    def test_rsi_to_verdict_oversold(self):
        """RSI 판정 테스트 - 과매도"""
        agent = StockReportAgent()

        result = agent._rsi_to_verdict(25)
        assert "과매도" in result

    def test_rsi_to_verdict_neutral(self):
        """RSI 판정 테스트 - 중립"""
        agent = StockReportAgent()

        result = agent._rsi_to_verdict(50)
        assert result == "중립"

    def test_generate_opinion_strong_buy(self, mock_stock_result):
        """투자 의견 생성 테스트 - Strong Buy"""
        agent = StockReportAgent()

        opinion = agent._generate_opinion(mock_stock_result)

        assert "매우 매력적" in opinion or "긍정적" in opinion

    def test_generate_opinion_hold(self, mock_rubric_result):
        """투자 의견 생성 테스트 - Hold"""
        agent = StockReportAgent()
        stock = StockAnalysisResult(
            symbol="000000",
            name="테스트종목",
            sector="테스트",
            group="custom",
            market_cap=1000,
            total_score=50.0,
            investment_grade="Hold",
        )

        opinion = agent._generate_opinion(stock)

        assert "관망" in opinion

    def test_extract_rubric_details_with_data(self, mock_rubric_result):
        """루브릭 상세 정보 추출 테스트 - 데이터 있음"""
        agent = StockReportAgent()

        details = agent._extract_rubric_details(mock_rubric_result)

        assert details["trend_score"] == 5.0
        assert details["rsi_score"] == 5.0
        assert details["foreign_score"] == 6.4

    def test_extract_rubric_details_none(self):
        """루브릭 상세 정보 추출 테스트 - 데이터 없음"""
        agent = StockReportAgent()

        details = agent._extract_rubric_details(None)

        # 기본값 확인
        assert details["trend_score"] == 3.0
        assert details["rsi_score"] == 3.0

    def test_render_markdown(self, mock_stock_result):
        """마크다운 렌더링 테스트"""
        agent = StockReportAgent()

        md = agent._render_markdown(mock_stock_result)

        # 필수 섹션 존재 확인
        assert "삼성전자" in md
        assert "005930" in md
        assert "Strong Buy" in md
        assert "기술적 분석" in md
        assert "수급 분석" in md
        assert "펀더멘털 분석" in md
        assert "시장 환경" in md
        assert "리스크 평가" in md
        assert "상대 강도" in md
        assert "투자 의견" in md

    @pytest.mark.asyncio
    async def test_generate_single_report(self, mock_stock_result, temp_output_dir):
        """단일 리포트 생성 테스트"""
        agent = StockReportAgent(output_dir=temp_output_dir)

        filepath = await agent._generate_single_report(mock_stock_result, "20250118")

        # 파일 생성 확인
        assert Path(filepath).exists()
        assert "005930" in filepath
        assert "삼성전자" in filepath
        assert "20250118" in filepath

        # 파일 내용 확인
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            assert "삼성전자" in content
            assert "Strong Buy" in content

    @pytest.mark.asyncio
    async def test_generate_reports_multiple(self, mock_stock_result, temp_output_dir):
        """다중 리포트 생성 테스트"""
        agent = StockReportAgent(output_dir=temp_output_dir)

        # 두 번째 종목 생성
        stock2 = StockAnalysisResult(
            symbol="000660",
            name="SK하이닉스",
            sector="반도체",
            group="kospi_top10",
            market_cap=1000000,
            total_score=75.0,
            investment_grade="Buy",
            rank_in_group=2,
            final_rank=2,
        )

        result = await agent.generate_reports([mock_stock_result, stock2], "20250118")

        assert len(result) == 2
        assert "005930" in result
        assert "000660" in result


# =============================================================================
# GRADE_STARS 상수 테스트
# =============================================================================


class TestGradeStars:
    """투자 등급 별점 테스트 클래스"""

    def test_strong_buy_has_five_stars(self):
        """Strong Buy는 별 5개"""
        assert GRADE_STARS["Strong Buy"].count("⭐") == 5

    def test_buy_has_four_stars(self):
        """Buy는 별 4개"""
        assert GRADE_STARS["Buy"].count("⭐") == 4

    def test_hold_has_three_stars(self):
        """Hold는 별 3개"""
        assert GRADE_STARS["Hold"].count("⭐") == 3

    def test_sell_has_two_stars(self):
        """Sell은 별 2개"""
        assert GRADE_STARS["Sell"].count("⭐") == 2

    def test_strong_sell_has_one_star(self):
        """Strong Sell은 별 1개"""
        assert GRADE_STARS["Strong Sell"].count("⭐") == 1
