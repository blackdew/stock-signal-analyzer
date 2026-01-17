"""
SectorReportAgent 테스트

섹터 리포트 생성 에이전트의 단위 테스트.
"""

import pytest
import tempfile
from pathlib import Path

from src.agents.report.sector_report_agent import SectorReportAgent
from src.agents.analysis.sector_analyzer import SectorAnalysisResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_stock_results():
    """Mock 상위 종목 리스트"""
    return [
        StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="sector_반도체",
            market_cap=4500000,
            total_score=80.0,
            investment_grade="Strong Buy",
            rank_in_group=1,
        ),
        StockAnalysisResult(
            symbol="000660",
            name="SK하이닉스",
            sector="반도체",
            group="sector_반도체",
            market_cap=1000000,
            total_score=75.0,
            investment_grade="Buy",
            rank_in_group=2,
        ),
        StockAnalysisResult(
            symbol="042700",
            name="한미반도체",
            sector="반도체",
            group="sector_반도체",
            market_cap=100000,
            total_score=70.0,
            investment_grade="Buy",
            rank_in_group=3,
        ),
    ]


@pytest.fixture
def mock_sector_result(mock_stock_results):
    """Mock 섹터 분석 결과"""
    return SectorAnalysisResult(
        sector_name="반도체",
        stock_count=5,
        total_market_cap=5700000,
        weighted_score=78.5,
        simple_score=75.0,
        technical_score=19.5,
        supply_score=15.0,
        fundamental_score=15.0,
        market_score=11.0,
        top_stocks=mock_stock_results,
        rank=1,
    )


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# SectorReportAgent 테스트
# =============================================================================


class TestSectorReportAgent:
    """SectorReportAgent 테스트 클래스"""

    def test_init_creates_output_dir(self, temp_output_dir):
        """초기화 시 출력 디렉토리 생성 테스트"""
        output_dir = temp_output_dir / "sectors"
        agent = SectorReportAgent(output_dir=output_dir)

        assert output_dir.exists()

    def test_format_market_cap_trillion(self):
        """시가총액 조 단위 포맷 테스트"""
        agent = SectorReportAgent()

        result = agent._format_market_cap(57000)  # 5.7조
        assert "5.7조원" in result

    def test_format_market_cap_billion(self):
        """시가총액 억 단위 포맷 테스트"""
        agent = SectorReportAgent()

        result = agent._format_market_cap(5000)
        assert "5,000억원" in result

    def test_render_top_stocks_table(self, mock_stock_results):
        """상위 종목 테이블 렌더링 테스트"""
        agent = SectorReportAgent()

        table = agent._render_top_stocks_table(mock_stock_results)

        assert "삼성전자" in table
        assert "SK하이닉스" in table
        assert "005930" in table
        assert "000660" in table

    def test_render_top_stocks_table_empty(self):
        """상위 종목 테이블 렌더링 테스트 - 빈 리스트"""
        agent = SectorReportAgent()

        table = agent._render_top_stocks_table([])

        assert "상위 종목 정보가 없습니다" in table

    def test_analyze_category_strengths_strong(self, mock_sector_result):
        """카테고리 강/약점 분석 테스트 - 강점"""
        agent = SectorReportAgent()

        analysis = agent._analyze_category_strengths(mock_sector_result)

        # 기술적 분석 78%는 강점
        assert "기술적 분석" in analysis

    def test_analyze_category_strengths_weak(self):
        """카테고리 강/약점 분석 테스트 - 약점"""
        agent = SectorReportAgent()
        weak_sector = SectorAnalysisResult(
            sector_name="테스트",
            stock_count=3,
            total_market_cap=1000,
            weighted_score=30.0,
            simple_score=30.0,
            technical_score=5.0,
            supply_score=4.0,
            fundamental_score=4.0,
            market_score=3.0,
            rank=10,
        )

        analysis = agent._analyze_category_strengths(weak_sector)

        # 약점이 포함되어야 함
        assert "약점" in analysis

    def test_generate_outlook_positive(self, mock_sector_result):
        """섹터 전망 생성 테스트 - 긍정적"""
        agent = SectorReportAgent()

        outlook = agent._generate_outlook(mock_sector_result)

        assert "긍정적" in outlook or "양호" in outlook

    def test_generate_outlook_neutral(self):
        """섹터 전망 생성 테스트 - 중립"""
        agent = SectorReportAgent()
        neutral_sector = SectorAnalysisResult(
            sector_name="테스트",
            stock_count=3,
            total_market_cap=1000,
            weighted_score=45.0,
            simple_score=45.0,
            technical_score=11.0,
            supply_score=9.0,
            fundamental_score=9.0,
            market_score=7.0,
            rank=5,
        )

        outlook = agent._generate_outlook(neutral_sector)

        assert "중립" in outlook

    def test_generate_outlook_negative(self):
        """섹터 전망 생성 테스트 - 부정적"""
        agent = SectorReportAgent()
        negative_sector = SectorAnalysisResult(
            sector_name="테스트",
            stock_count=3,
            total_market_cap=1000,
            weighted_score=30.0,
            simple_score=30.0,
            technical_score=7.0,
            supply_score=5.0,
            fundamental_score=5.0,
            market_score=4.0,
            rank=10,
        )

        outlook = agent._generate_outlook(negative_sector)

        assert "부정적" in outlook

    def test_render_markdown(self, mock_sector_result):
        """마크다운 렌더링 테스트"""
        agent = SectorReportAgent()

        md = agent._render_markdown(mock_sector_result)

        # 필수 섹션 존재 확인
        assert "반도체" in md
        assert "섹터 개요" in md
        assert "섹터 점수" in md
        assert "상위 종목" in md
        assert "강/약점 분석" in md
        assert "섹터 전망" in md
        assert "78.5" in md  # weighted_score

    @pytest.mark.asyncio
    async def test_generate_single_report(self, mock_sector_result, temp_output_dir):
        """단일 리포트 생성 테스트"""
        agent = SectorReportAgent(output_dir=temp_output_dir)

        filepath = await agent._generate_single_report(mock_sector_result, "20250118")

        # 파일 생성 확인
        assert Path(filepath).exists()
        assert "반도체" in filepath
        assert "20250118" in filepath

        # 파일 내용 확인
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            assert "반도체" in content
            assert "78.5" in content

    @pytest.mark.asyncio
    async def test_generate_reports_multiple(self, mock_sector_result, temp_output_dir):
        """다중 리포트 생성 테스트"""
        agent = SectorReportAgent(output_dir=temp_output_dir)

        # 두 번째 섹터 생성
        sector2 = SectorAnalysisResult(
            sector_name="조선",
            stock_count=5,
            total_market_cap=500000,
            weighted_score=72.0,
            simple_score=70.0,
            technical_score=18.0,
            supply_score=14.0,
            fundamental_score=14.0,
            market_score=10.0,
            rank=2,
        )

        result = await agent.generate_reports([mock_sector_result, sector2], "20250118")

        assert len(result) == 2
        assert "반도체" in result
        assert "조선" in result
