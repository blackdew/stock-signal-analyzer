"""
SummaryAgent 테스트

종합 리포트 및 JSON 데이터 생성 에이전트의 단위 테스트.
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.agents.report.summary_agent import SummaryAgent, GRADE_STARS
from src.agents.analysis.ranking_agent import RankingResult
from src.agents.analysis.sector_analyzer import SectorAnalysisResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult


# =============================================================================
# Mock 데이터 Fixtures
# =============================================================================


@pytest.fixture
def mock_stocks():
    """Mock 종목 리스트"""
    return [
        StockAnalysisResult(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            group="kospi_top10",
            market_cap=4500000,
            total_score=80.0,
            technical_score=20.0,
            supply_score=16.0,
            fundamental_score=16.0,
            market_score=12.0,
            risk_score=8.0,
            relative_strength_score=8.0,
            investment_grade="Strong Buy",
            rank_in_group=1,
            final_rank=1,
        ),
        StockAnalysisResult(
            symbol="000660",
            name="SK하이닉스",
            sector="반도체",
            group="kospi_top10",
            market_cap=1000000,
            total_score=75.0,
            technical_score=18.0,
            supply_score=15.0,
            fundamental_score=15.0,
            market_score=11.0,
            risk_score=7.0,
            relative_strength_score=9.0,
            investment_grade="Buy",
            rank_in_group=2,
            final_rank=2,
        ),
        StockAnalysisResult(
            symbol="207940",
            name="삼성바이오로직스",
            sector="바이오",
            group="kospi_top10",
            market_cap=800000,
            total_score=72.0,
            technical_score=17.0,
            supply_score=14.0,
            fundamental_score=15.0,
            market_score=11.0,
            risk_score=7.0,
            relative_strength_score=8.0,
            investment_grade="Buy",
            rank_in_group=3,
            final_rank=3,
        ),
    ]


@pytest.fixture
def mock_sectors():
    """Mock 섹터 리스트"""
    return [
        SectorAnalysisResult(
            sector_name="반도체",
            stock_count=5,
            total_market_cap=5700000,
            weighted_score=78.5,
            simple_score=75.0,
            technical_score=19.5,
            supply_score=15.0,
            fundamental_score=15.0,
            market_score=11.0,
            rank=1,
        ),
        SectorAnalysisResult(
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
        ),
        SectorAnalysisResult(
            sector_name="방산",
            stock_count=5,
            total_market_cap=300000,
            weighted_score=68.0,
            simple_score=66.0,
            technical_score=16.0,
            supply_score=13.0,
            fundamental_score=14.0,
            market_score=10.0,
            rank=3,
        ),
    ]


@pytest.fixture
def mock_ranking_result(mock_stocks, mock_sectors):
    """Mock RankingResult"""
    return RankingResult(
        kospi_top10=mock_stocks[:2],
        kospi_11_20=[mock_stocks[2]],
        kosdaq_top10=[],
        sector_top=[],
        final_18=mock_stocks,
        final_top3=mock_stocks,
        top_sectors=mock_sectors,
    )


@pytest.fixture
def temp_dirs():
    """임시 출력 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        summary_dir = Path(tmpdir) / "summary"
        data_dir = Path(tmpdir) / "data"
        yield summary_dir, data_dir


# =============================================================================
# SummaryAgent 테스트
# =============================================================================


class TestSummaryAgent:
    """SummaryAgent 테스트 클래스"""

    def test_init_creates_output_dirs(self, temp_dirs):
        """초기화 시 출력 디렉토리 생성 테스트"""
        summary_dir, data_dir = temp_dirs
        agent = SummaryAgent(summary_dir=summary_dir, data_dir=data_dir)

        assert summary_dir.exists()
        assert data_dir.exists()

    def test_format_market_cap_trillion(self):
        """시가총액 조 단위 포맷 테스트"""
        agent = SummaryAgent()

        result = agent._format_market_cap(45000)
        assert "4.5조원" in result

    def test_format_market_cap_billion(self):
        """시가총액 억 단위 포맷 테스트"""
        agent = SummaryAgent()

        result = agent._format_market_cap(5000)
        assert "5,000억원" in result

    def test_translate_group_name(self):
        """그룹명 한글화 테스트"""
        agent = SummaryAgent()

        assert agent._translate_group_name("kospi_top10") == "KOSPI Top10"
        assert agent._translate_group_name("kospi_11_20") == "KOSPI 11~20"
        assert agent._translate_group_name("kosdaq_top10") == "KOSDAQ Top10"
        assert "반도체" in agent._translate_group_name("sector_반도체")

    def test_generate_selection_reason_rank1(self, mock_stocks):
        """선정 이유 생성 테스트 - 1위"""
        agent = SummaryAgent()

        reason = agent._generate_selection_reason(mock_stocks[0], 1)

        assert "최고 점수" in reason or "선정" in reason
        assert "수급" in reason  # 수급 점수가 높음

    def test_generate_selection_reason_with_strengths(self, mock_stocks):
        """선정 이유 생성 테스트 - 강점 포함"""
        agent = SummaryAgent()

        reason = agent._generate_selection_reason(mock_stocks[0], 1)

        # 강점이 나열되어야 함
        assert len(reason) > 20

    def test_group_by_sector(self, mock_stocks):
        """섹터별 그룹화 테스트"""
        agent = SummaryAgent()

        grouped = agent._group_by_sector(mock_stocks)

        assert "반도체" in grouped
        assert "바이오" in grouped
        assert len(grouped["반도체"]) == 2
        assert len(grouped["바이오"]) == 1

    def test_build_stock_detail(self, mock_stocks):
        """종목 상세 정보 빌드 테스트"""
        agent = SummaryAgent()

        detail = agent._build_stock_detail(mock_stocks[0], 1)

        assert detail["rank"] == 1
        assert detail["symbol"] == "005930"
        assert detail["name"] == "삼성전자"
        assert detail["total_score"] == 80.0
        assert detail["technical_score"] == 20.0
        assert "selection_reason" in detail

    def test_build_json_data(self, mock_ranking_result):
        """JSON 데이터 구조 빌드 테스트"""
        agent = SummaryAgent()

        data = agent._build_json_data(mock_ranking_result)

        assert "generated_at" in data
        assert "sector_rankings" in data
        assert "top_sectors" in data
        assert "final_top3" in data
        assert "all_selected" in data
        assert "summary" in data

        # 상위 섹터 목록 확인
        assert "반도체" in data["top_sectors"]
        assert "조선" in data["top_sectors"]
        assert "방산" in data["top_sectors"]

    def test_render_top3_table(self, mock_stocks):
        """Top 3 테이블 렌더링 테스트"""
        agent = SummaryAgent()

        table = agent._render_top3_table(mock_stocks)

        assert "삼성전자" in table
        assert "SK하이닉스" in table
        assert "005930" in table
        assert "Strong Buy" in table

    def test_render_top3_details(self, mock_stocks):
        """Top 3 상세 분석 렌더링 테스트"""
        agent = SummaryAgent()

        details = agent._render_top3_details(mock_stocks)

        assert "1위" in details
        assert "2위" in details
        assert "3위" in details
        assert "삼성전자" in details
        assert "선정 이유" in details

    def test_render_sectors_table(self, mock_sectors):
        """섹터 테이블 렌더링 테스트"""
        agent = SummaryAgent()

        table = agent._render_sectors_table(mock_sectors)

        assert "반도체" in table
        assert "조선" in table
        assert "방산" in table
        assert "78.5" in table

    def test_render_stock_list(self, mock_stocks):
        """종목 리스트 테이블 렌더링 테스트"""
        agent = SummaryAgent()

        table = agent._render_stock_list(mock_stocks)

        assert "삼성전자" in table
        assert "SK하이닉스" in table
        assert "80.0" in table

    def test_render_final_18_table(self, mock_stocks):
        """최종 18개 테이블 렌더링 테스트"""
        agent = SummaryAgent()

        table = agent._render_final_18_table(mock_stocks)

        assert "삼성전자" in table
        assert "KOSPI Top10" in table

    def test_render_markdown(self, mock_ranking_result):
        """마크다운 렌더링 테스트"""
        agent = SummaryAgent()

        md = agent._render_markdown(mock_ranking_result)

        # 필수 섹션 존재 확인
        assert "투자 종합 분석 리포트" in md
        assert "Top 3 추천 종목" in md
        assert "Top 3 상세 분석" in md
        assert "상위 섹터" in md
        assert "그룹별 선정 종목" in md
        assert "최종" in md
        assert "평가 기준" in md
        assert "투자 등급" in md

    @pytest.mark.asyncio
    async def test_save_json_data(self, mock_ranking_result, temp_dirs):
        """JSON 데이터 저장 테스트"""
        summary_dir, data_dir = temp_dirs
        agent = SummaryAgent(summary_dir=summary_dir, data_dir=data_dir)

        filepath = await agent._save_json_data(mock_ranking_result, "20250118")

        # 파일 생성 확인
        assert Path(filepath).exists()
        assert "analysis_20250118.json" in filepath

        # JSON 구조 확인
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "final_top3" in data
            assert "all_selected" in data

    @pytest.mark.asyncio
    async def test_save_markdown_report(self, mock_ranking_result, temp_dirs):
        """마크다운 리포트 저장 테스트"""
        summary_dir, data_dir = temp_dirs
        agent = SummaryAgent(summary_dir=summary_dir, data_dir=data_dir)

        filepath = await agent._save_markdown_report(mock_ranking_result, "20250118")

        # 파일 생성 확인
        assert Path(filepath).exists()
        assert "종합리포트_20250118.md" in filepath

        # 파일 내용 확인
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            assert "삼성전자" in content
            assert "Top 3" in content

    @pytest.mark.asyncio
    async def test_generate_summary(self, mock_ranking_result, temp_dirs):
        """종합 리포트 생성 테스트"""
        summary_dir, data_dir = temp_dirs
        agent = SummaryAgent(summary_dir=summary_dir, data_dir=data_dir)

        result = await agent.generate_summary(mock_ranking_result, "20250118")

        assert "json" in result
        assert "markdown" in result
        assert Path(result["json"]).exists()
        assert Path(result["markdown"]).exists()


# =============================================================================
# GRADE_STARS 상수 테스트
# =============================================================================


class TestGradeStars:
    """투자 등급 별점 테스트 클래스"""

    def test_all_grades_have_stars(self):
        """모든 등급에 별점 존재 확인"""
        expected_grades = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]

        for grade in expected_grades:
            assert grade in GRADE_STARS
            assert "⭐" in GRADE_STARS[grade]
