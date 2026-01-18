#!/usr/bin/env python3
"""
리포트 생성 테스트 스크립트

날짜별 폴더 구조로 리포트가 올바르게 생성되는지 검증합니다.

사용법:
    uv run scripts/test_report_generation.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.agents.analysis.sector_analyzer import SectorAnalysisResult
from src.agents.report.stock_report_agent import StockReportAgent
from src.agents.report.sector_report_agent import SectorReportAgent
from src.agents.report.summary_agent import SummaryAgent
from src.agents.analysis.ranking_agent import RankingResult
from src.core.rubric import RubricResult, CategoryScore


def create_mock_rubric_result(
    symbol: str,
    name: str,
    total_score: float,
) -> RubricResult:
    """테스트용 RubricResult 생성 - 실제 지표 값 포함"""
    # 기술적 분석
    technical = CategoryScore(
        name="technical",
        score=75.0,
        max_score=25,
        weighted_score=total_score * 0.25,
        details={
            "trend": 4.5, "rsi": 5.0, "support_resistance": 4.0, "macd": 3.0, "adx": 2.0,
            "ma20_value": 55000, "ma60_value": 52000,
            "rsi_value": 55.5, "macd_value": 150.5, "macd_signal_value": 120.3,
            "adx_value": 28.5,
            "current_price": 56000, "low_52w": 45000, "high_52w": 65000,
            "position_52w": 55.0,
        }
    )

    # 수급 분석
    supply = CategoryScore(
        name="supply",
        score=70.0,
        max_score=20,
        weighted_score=total_score * 0.20,
        details={
            "foreign": 6.0, "institution": 5.0, "trading_value": 3.0,
            "foreign_net_5d": [100, 150, 80, 120, 90],
            "foreign_consecutive_days": 5,
            "institution_net_5d": [50, -20, 30, 80, 60],
            "institution_consecutive_days": 2,
            "trading_value_amount": 1250.5,
        }
    )

    # 펀더멘털 분석
    fundamental = CategoryScore(
        name="fundamental",
        score=72.0,
        max_score=20,
        weighted_score=total_score * 0.20,
        details={
            "per": 3.0, "pbr": 2.8, "roe": 3.2, "growth": 3.5, "debt": 2.0,
            "per_value": 12.5, "pbr_value": 1.2, "roe_value": 15.3,
            "sector_avg_per": 15.0, "sector_avg_pbr": 1.5,
            "op_growth_value": 25.5, "debt_ratio_value": 45.2,
        }
    )

    # 시장 환경
    market = CategoryScore(
        name="market",
        score=68.0,
        max_score=15,
        weighted_score=total_score * 0.15,
        details={
            "news": 5.5, "sector_momentum": 3.0, "analyst": 3.5,
        }
    )

    # 리스크 평가
    risk = CategoryScore(
        name="risk",
        score=75.0,
        max_score=10,
        weighted_score=total_score * 0.10,
        details={
            "volatility": 3.0, "beta": 2.5, "downside_risk": 2.0,
            "atr_pct_value": 2.5, "beta_value": 1.05, "max_drawdown_value": 12.5,
        }
    )

    # 상대 강도
    relative_strength = CategoryScore(
        name="relative_strength",
        score=70.0,
        max_score=10,
        weighted_score=total_score * 0.10,
        details={
            "sector_rank": 4.0, "alpha": 3.5,
            "sector_rank_value": 2, "sector_total_value": 10,
            "stock_return_value": 8.5, "market_return_value": 3.2, "alpha_value": 5.3,
        }
    )

    return RubricResult(
        symbol=symbol,
        name=name,
        technical=technical,
        supply=supply,
        fundamental=fundamental,
        market=market,
        risk=risk,
        relative_strength=relative_strength,
        total_score=total_score,
        grade="Buy" if total_score >= 60 else "Hold",
        rubric_version="v2",
    )


def create_mock_stock_result(
    symbol: str,
    name: str,
    sector: str,
    total_score: float,
    group: str = "kospi_top10",
) -> StockAnalysisResult:
    """테스트용 종목 분석 결과 생성"""
    rubric_result = create_mock_rubric_result(symbol, name, total_score)

    return StockAnalysisResult(
        symbol=symbol,
        name=name,
        sector=sector,
        market_cap=10000.0,
        total_score=total_score,
        investment_grade="Buy" if total_score >= 60 else "Hold",
        technical_score=total_score * 0.25,
        supply_score=total_score * 0.20,
        fundamental_score=total_score * 0.20,
        market_score=total_score * 0.15,
        risk_score=total_score * 0.10,
        relative_strength_score=total_score * 0.10,
        group=group,
        rank_in_group=1,
        final_rank=1,
        rubric_result=rubric_result,
    )


def create_mock_sector_result(
    sector_name: str,
    rank: int,
    weighted_score: float,
    stocks: list,
) -> SectorAnalysisResult:
    """테스트용 섹터 분석 결과 생성"""
    return SectorAnalysisResult(
        sector_name=sector_name,
        rank=rank,
        weighted_score=weighted_score,
        simple_score=weighted_score - 2,
        total_market_cap=50000.0,
        stock_count=len(stocks),
        technical_score=weighted_score * 0.25,
        supply_score=weighted_score * 0.20,
        fundamental_score=weighted_score * 0.20,
        market_score=weighted_score * 0.15,
        top_stocks=stocks,
    )


async def test_report_generation():
    """리포트 생성 테스트"""
    print("=" * 60)
    print("리포트 생성 테스트 시작")
    print("=" * 60)

    # 날짜별 폴더 생성
    date_str = datetime.now().strftime("%Y-%m-%d")
    test_output_dir = project_root / "output" / "reports" / date_str
    test_output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n테스트 출력 디렉토리: {test_output_dir}")

    # 테스트용 종목 데이터 생성
    mock_stocks = [
        create_mock_stock_result("005930", "삼성전자", "반도체", 75.5, "kospi_top10"),
        create_mock_stock_result("000660", "SK하이닉스", "반도체", 72.3, "kospi_top10"),
        create_mock_stock_result("207940", "삼성바이오로직스", "바이오", 68.7, "sector_바이오"),
    ]

    # 테스트용 섹터 데이터 생성
    mock_sectors = [
        create_mock_sector_result("반도체", 1, 73.5, mock_stocks[:2]),
        create_mock_sector_result("바이오", 2, 65.2, [mock_stocks[2]]),
        create_mock_sector_result("조선", 3, 62.1, []),
    ]

    # 1. 섹터 리포트 테스트 (01_sector_report.md)
    print("\n1. 섹터 통합 리포트 테스트...")
    sector_agent = SectorReportAgent(output_dir=test_output_dir)
    sector_path = await sector_agent.generate_unified_report(mock_sectors)
    print(f"   생성됨: {sector_path}")
    assert Path(sector_path).exists(), "섹터 리포트 파일이 생성되지 않음"
    assert Path(sector_path).name == "01_sector_report.md", "파일명이 올바르지 않음"
    print("   OK")

    # 2. 종목 리포트 테스트 (02_stocks/)
    print("\n2. 종목 리포트 테스트...")
    stocks_dir = test_output_dir / "02_stocks"
    stocks_dir.mkdir(parents=True, exist_ok=True)
    stock_agent = StockReportAgent(output_dir=stocks_dir)
    stock_paths = await stock_agent.generate_reports(mock_stocks)
    print(f"   생성됨: {len(stock_paths)}개 리포트")
    for symbol, path in stock_paths.items():
        assert Path(path).exists(), f"{symbol} 리포트 파일이 생성되지 않음"
        # 파일명에 날짜가 없는지 확인
        assert datetime.now().strftime("%Y") not in Path(path).name or \
               "2026" not in Path(path).name, f"파일명에 날짜가 포함됨: {Path(path).name}"
        print(f"   - {Path(path).name}")
    print("   OK")

    # 3. 종합 리포트 테스트 (03_final_report.md)
    print("\n3. 종합 리포트 테스트...")

    # RankingResult 목 데이터 생성
    mock_ranking = RankingResult(
        kospi_top10=mock_stocks[:2],
        kospi_11_20=[],
        kosdaq_top10=[],
        sector_top=[mock_stocks[2]],
        top_sectors=mock_sectors,
        final_18=mock_stocks,
        final_top3=mock_stocks[:3],
    )

    summary_agent = SummaryAgent(
        summary_dir=test_output_dir,
        data_dir=project_root / "output" / "data"
    )
    summary_paths = await summary_agent.generate_summary(mock_ranking)
    print(f"   생성됨: {summary_paths}")

    # 마크다운 파일 확인
    md_path = summary_paths.get("markdown")
    assert md_path and Path(md_path).exists(), "종합 리포트 파일이 생성되지 않음"
    assert Path(md_path).name == "03_final_report.md", f"파일명이 올바르지 않음: {Path(md_path).name}"
    print(f"   - {Path(md_path).name}")
    print("   OK")

    # 4. 폴더 구조 검증
    print("\n4. 폴더 구조 검증...")
    expected_structure = [
        test_output_dir / "01_sector_report.md",
        test_output_dir / "02_stocks",
        test_output_dir / "03_final_report.md",
    ]

    for path in expected_structure:
        assert path.exists(), f"경로가 존재하지 않음: {path}"
        print(f"   - {path.name}: 존재")

    # 종목 리포트 수 확인
    stock_reports = list((test_output_dir / "02_stocks").glob("*.md"))
    print(f"   - 02_stocks/: {len(stock_reports)}개 리포트")

    print("\n" + "=" * 60)
    print("모든 테스트 통과!")
    print("=" * 60)

    # 생성된 파일 목록 출력
    print("\n생성된 파일 목록:")
    print(f"  {test_output_dir}/")
    for item in sorted(test_output_dir.iterdir()):
        if item.is_dir():
            print(f"    {item.name}/")
            for sub_item in sorted(item.iterdir()):
                print(f"      {sub_item.name}")
        else:
            print(f"    {item.name}")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_report_generation())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
