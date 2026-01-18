"""
Orchestrator

전체 분석 워크플로우를 관리하는 오케스트레이터.
데이터 수집 → 섹터 분석 → 종목 분석 → 리포트 생성의 전체 파이프라인을 실행합니다.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.data.cache import CacheManager
from src.agents.data.market_data_agent import MarketDataAgent
from src.agents.data.fundamental_agent import FundamentalAgent
from src.agents.data.news_agent import NewsAgent
from src.agents.analysis.stock_analyzer import StockAnalyzer, StockAnalysisResult
from src.agents.analysis.sector_analyzer import SectorAnalyzer, SectorAnalysisResult
from src.agents.analysis.ranking_agent import RankingAgent, RankingResult
from src.agents.report.stock_report_agent import StockReportAgent
from src.agents.report.sector_report_agent import SectorReportAgent
from src.agents.report.summary_agent import SummaryAgent
from src.agents.report.weekly_sector_report_agent import WeeklySectorReportAgent


# =============================================================================
# 설정 데이터 클래스
# =============================================================================


@dataclass
class RunOptions:
    """
    실행 옵션

    Attributes:
        mode: 실행 모드 (daily, weekly)
        sector_only: 섹터 분석만 실행
        group: 분석할 그룹 (kospi_top10, kospi_11_20, kosdaq_top10, all)
        output_format: 출력 형식 (markdown, json, both)
        use_cache: 캐시 사용 여부
        skip_news: 뉴스 분석 스킵
        output_dir: 출력 디렉토리
        verbose: 상세 로그 출력
    """
    mode: str = "daily"
    sector_only: bool = False
    group: str = "all"
    output_format: str = "both"
    use_cache: bool = True
    skip_news: bool = False
    output_dir: str = "output"
    verbose: bool = False


@dataclass
class RetryPolicy:
    """
    재시도 정책

    Attributes:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exponential_base: 지수 백오프 기준
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


@dataclass
class AnalysisOutput:
    """
    분석 출력 결과

    Attributes:
        generated_at: 생성 시각
        ranking_result: 순위 산정 결과
        report_paths: 생성된 리포트 파일 경로
        stats: 실행 통계
    """
    generated_at: datetime
    ranking_result: Optional[RankingResult] = None
    sector_results: Optional[List[SectorAnalysisResult]] = None
    report_paths: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Orchestrator
# =============================================================================


@dataclass
class Orchestrator:
    """
    분석 워크플로우 오케스트레이터

    주요 기능:
    - 전체 분석 파이프라인 실행
    - 에이전트 통합 관리
    - 에러 핸들링 및 재시도
    - 부분 실패 처리

    사용 예시:
        orchestrator = Orchestrator()
        result = await orchestrator.run(RunOptions())
    """

    # 설정
    use_cache: bool = True
    skip_news: bool = False
    output_dir: str = "output"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    # 에이전트 (lazy initialization)
    _cache: Optional[CacheManager] = field(default=None, init=False)
    _ranking_agent: Optional[RankingAgent] = field(default=None, init=False)
    _stock_report_agent: Optional[StockReportAgent] = field(default=None, init=False)
    _sector_report_agent: Optional[SectorReportAgent] = field(default=None, init=False)
    _summary_agent: Optional[SummaryAgent] = field(default=None, init=False)

    def __post_init__(self):
        """로거 초기화"""
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def cache(self) -> CacheManager:
        """캐시 매니저 (lazy)"""
        if self._cache is None:
            self._cache = CacheManager()
        return self._cache

    @property
    def ranking_agent(self) -> RankingAgent:
        """RankingAgent (lazy)"""
        if self._ranking_agent is None:
            self._ranking_agent = RankingAgent()
        return self._ranking_agent

    @property
    def stock_report_agent(self) -> StockReportAgent:
        """StockReportAgent (lazy)"""
        if self._stock_report_agent is None:
            output_dir = Path(self.output_dir) / "reports" / "stocks"
            self._stock_report_agent = StockReportAgent(output_dir=output_dir)
        return self._stock_report_agent

    @property
    def sector_report_agent(self) -> SectorReportAgent:
        """SectorReportAgent (lazy)"""
        if self._sector_report_agent is None:
            output_dir = Path(self.output_dir) / "reports" / "sectors"
            self._sector_report_agent = SectorReportAgent(output_dir=output_dir)
        return self._sector_report_agent

    @property
    def summary_agent(self) -> SummaryAgent:
        """SummaryAgent (lazy)"""
        if self._summary_agent is None:
            summary_dir = Path(self.output_dir) / "reports" / "summary"
            data_dir = Path(self.output_dir) / "data"
            self._summary_agent = SummaryAgent(
                summary_dir=summary_dir,
                data_dir=data_dir
            )
        return self._summary_agent

    async def run(self, options: Optional[RunOptions] = None) -> AnalysisOutput:
        """
        전체 분석 파이프라인을 실행합니다. (하위 호환성)

        기본적으로 일간 분석을 실행합니다.
        주간 분석은 run_weekly()를 사용하세요.

        Args:
            options: 실행 옵션 (None이면 기본값 사용)

        Returns:
            AnalysisOutput
        """
        return await self.run_daily(options)

    async def run_daily(self, options: Optional[RunOptions] = None) -> AnalysisOutput:
        """
        일간 분석 파이프라인을 실행합니다.

        Args:
            options: 실행 옵션 (None이면 기본값 사용)

        Returns:
            AnalysisOutput
        """
        if options is None:
            options = RunOptions()

        start_time = time.time()
        stats: Dict[str, Any] = {"phases": {}}
        report_paths: Dict[str, Any] = {}

        # 날짜별 폴더 생성 (output/reports/daily/YYYY-MM-DD)
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_report_dir = Path(self.output_dir) / "reports" / "daily" / date_str
        date_report_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("=" * 60)
        self.logger.info("투자 기회 분석 시작")
        self.logger.info("=" * 60)

        try:
            # Phase 1: 순위 산정 (데이터 수집 + 분석 통합)
            phase_start = time.time()
            self.logger.info("Phase 1: 데이터 수집 및 순위 산정 시작")

            ranking_result = await self._run_with_retry(
                self.ranking_agent.rank,
                "순위 산정"
            )

            phase_time = time.time() - phase_start
            stats["phases"]["ranking"] = {"time": round(phase_time, 2)}
            self.logger.info(f"Phase 1 완료 ({phase_time:.1f}초)")

            # Phase 2: 섹터 리포트 생성 (01_sector_report.md)
            if options.output_format in ("markdown", "both"):
                phase_start = time.time()
                self.logger.info("Phase 2: 섹터 리포트 생성 시작")

                # SectorReportAgent에 날짜 폴더 전달
                sector_report_agent = SectorReportAgent(output_dir=date_report_dir)
                sector_path = await sector_report_agent.generate_unified_report(
                    ranking_result.top_sectors
                )
                report_paths["sectors"] = sector_path

                phase_time = time.time() - phase_start
                stats["phases"]["sector_reports"] = {
                    "time": round(phase_time, 2),
                    "count": len(ranking_result.top_sectors)
                }
                self.logger.info(f"Phase 2 완료: 섹터 통합 리포트 생성 ({phase_time:.1f}초)")

            # Phase 3: 종목 리포트 생성 (02_stocks/)
            if options.output_format in ("markdown", "both"):
                phase_start = time.time()
                self.logger.info("Phase 3: 종목 리포트 생성 시작")

                # StockReportAgent에 날짜/stocks 폴더 전달
                stocks_dir = date_report_dir / "02_stocks"
                stock_report_agent = StockReportAgent(output_dir=stocks_dir)
                stock_paths = await stock_report_agent.generate_reports(
                    ranking_result.final_18
                )
                report_paths["stocks"] = stock_paths

                phase_time = time.time() - phase_start
                stats["phases"]["stock_reports"] = {
                    "time": round(phase_time, 2),
                    "count": len(stock_paths)
                }
                self.logger.info(f"Phase 3 완료: {len(stock_paths)}개 종목 리포트 ({phase_time:.1f}초)")

            # Phase 4: 종합 리포트 생성 (03_final_report.md)
            phase_start = time.time()
            self.logger.info("Phase 4: 종합 리포트 생성 시작")

            # SummaryAgent에 날짜 폴더 전달
            summary_agent = SummaryAgent(
                summary_dir=date_report_dir,
                data_dir=Path(self.output_dir) / "data"
            )
            summary_paths = await summary_agent.generate_summary(ranking_result)
            report_paths["summary"] = summary_paths

            phase_time = time.time() - phase_start
            stats["phases"]["summary"] = {"time": round(phase_time, 2)}
            self.logger.info(f"Phase 4 완료 ({phase_time:.1f}초)")

            # 전체 통계
            total_time = time.time() - start_time
            stats["total_time"] = round(total_time, 2)
            stats["final_stocks"] = len(ranking_result.final_18)
            stats["final_top5"] = [
                {"symbol": s.symbol, "name": s.name, "score": s.total_score}
                for s in ranking_result.final_top5
            ]

            self.logger.info("=" * 60)
            self.logger.info(f"분석 완료 (총 {total_time:.1f}초)")
            self.logger.info(f"최종 {len(ranking_result.final_18)}개 종목 선정")
            self.logger.info("Top 5:")
            for i, stock in enumerate(ranking_result.final_top5, 1):
                self.logger.info(f"  {i}. {stock.name} ({stock.symbol}): {stock.total_score:.1f}점")
            self.logger.info("=" * 60)

            return AnalysisOutput(
                generated_at=datetime.now(),
                ranking_result=ranking_result,
                sector_results=ranking_result.top_sectors,
                report_paths=report_paths,
                stats=stats
            )

        except Exception as e:
            self.logger.error(f"분석 실패: {e}")
            raise

    async def run_sector_only(self) -> AnalysisOutput:
        """
        섹터 분석만 실행합니다.

        Returns:
            AnalysisOutput (섹터 결과만 포함)
        """
        start_time = time.time()
        self.logger.info("섹터 분석 시작")

        try:
            sector_analyzer = SectorAnalyzer()
            sector_results = await sector_analyzer.analyze()

            total_time = time.time() - start_time
            self.logger.info(f"섹터 분석 완료 ({total_time:.1f}초)")
            self.logger.info("상위 섹터:")
            for sector in sector_results[:3]:
                self.logger.info(f"  - {sector.sector_name}: {sector.weighted_score:.1f}점")

            return AnalysisOutput(
                generated_at=datetime.now(),
                sector_results=sector_results,
                stats={"total_time": round(total_time, 2)}
            )

        except Exception as e:
            self.logger.error(f"섹터 분석 실패: {e}")
            raise

    async def run_weekly(self) -> AnalysisOutput:
        """
        주간 섹터 리포트를 생성합니다.

        Returns:
            AnalysisOutput (주간 섹터 리포트 포함)
        """
        start_time = time.time()
        stats: Dict[str, Any] = {"phases": {}}
        report_paths: Dict[str, Any] = {}

        # 주차별 폴더 생성 (output/reports/weekly/YYYY-WXX)
        now = datetime.now()
        week_str = now.strftime("%G-W%V")
        weekly_report_dir = Path(self.output_dir) / "reports" / "weekly" / week_str
        weekly_report_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("=" * 60)
        self.logger.info(f"주간 섹터 분석 시작 ({week_str})")
        self.logger.info("=" * 60)

        try:
            # Phase 1: 섹터 분석
            phase_start = time.time()
            self.logger.info("Phase 1: 섹터 분석 시작")

            sector_analyzer = SectorAnalyzer()
            sector_results = await sector_analyzer.analyze()

            phase_time = time.time() - phase_start
            stats["phases"]["sector_analysis"] = {"time": round(phase_time, 2)}
            self.logger.info(f"Phase 1 완료 ({phase_time:.1f}초)")

            # Phase 2: 주간 섹터 리포트 생성
            phase_start = time.time()
            self.logger.info("Phase 2: 주간 섹터 리포트 생성 시작")

            weekly_report_agent = WeeklySectorReportAgent(output_dir=weekly_report_dir)
            report_path = await weekly_report_agent.generate_weekly_report(
                sector_results, week_str
            )
            report_paths["weekly_sector"] = report_path

            phase_time = time.time() - phase_start
            stats["phases"]["weekly_report"] = {"time": round(phase_time, 2)}
            self.logger.info(f"Phase 2 완료: 주간 섹터 리포트 생성 ({phase_time:.1f}초)")

            # 전체 통계
            total_time = time.time() - start_time
            stats["total_time"] = round(total_time, 2)
            stats["sectors_analyzed"] = len(sector_results)

            self.logger.info("=" * 60)
            self.logger.info(f"주간 섹터 분석 완료 (총 {total_time:.1f}초)")
            self.logger.info(f"분석 섹터: {len(sector_results)}개")
            self.logger.info("상위 3개 섹터:")
            for i, sector in enumerate(sector_results[:3], 1):
                self.logger.info(f"  {i}. {sector.sector_name}: {sector.weighted_score:.1f}점")
            self.logger.info(f"리포트: {report_path}")
            self.logger.info("=" * 60)

            return AnalysisOutput(
                generated_at=datetime.now(),
                sector_results=sector_results,
                report_paths=report_paths,
                stats=stats
            )

        except Exception as e:
            self.logger.error(f"주간 섹터 분석 실패: {e}")
            raise

    async def _run_with_retry(
        self,
        func,
        task_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        재시도 로직을 적용하여 함수를 실행합니다.

        Args:
            func: 실행할 함수 (async)
            task_name: 작업 이름 (로깅용)
            *args, **kwargs: 함수 인자

        Returns:
            함수 실행 결과
        """
        policy = self.retry_policy

        for attempt in range(policy.max_retries):
            try:
                return await func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if attempt == policy.max_retries - 1:
                    self.logger.error(f"{task_name} 최종 실패: {e}")
                    raise

                delay = min(
                    policy.base_delay * (policy.exponential_base ** attempt),
                    policy.max_delay
                )
                self.logger.warning(
                    f"{task_name} 재시도 {attempt + 1}/{policy.max_retries}, "
                    f"{delay:.1f}초 후"
                )
                await asyncio.sleep(delay)
            except Exception as e:
                # 재시도 대상이 아닌 에러는 즉시 전파
                self.logger.error(f"{task_name} 에러: {e}")
                raise

        # 이 코드에 도달하면 안 됨
        raise RuntimeError(f"{task_name} 재시도 로직 오류")


# =============================================================================
# 유틸리티 함수
# =============================================================================


def print_summary(result: AnalysisOutput) -> None:
    """
    분석 결과 요약을 출력합니다.

    Args:
        result: 분석 출력 결과
    """
    print("\n" + "=" * 60)
    print("📊 투자 기회 분석 결과")
    print("=" * 60)

    if result.ranking_result:
        print(f"\n🏆 Top 5 추천 종목:")
        for i, stock in enumerate(result.ranking_result.final_top5, 1):
            print(f"  {i}. {stock.name} ({stock.symbol})")
            print(f"     점수: {stock.total_score:.1f}/100 | 등급: {stock.investment_grade}")

        print(f"\n📈 최종 선정: {len(result.ranking_result.final_18)}개 종목")

    if result.sector_results:
        print(f"\n🌍 상위 섹터:")
        for sector in result.sector_results[:3]:
            print(f"  - {sector.sector_name}: {sector.weighted_score:.1f}점")

    if result.report_paths:
        print(f"\n📁 생성된 리포트:")
        if "summary" in result.report_paths:
            paths = result.report_paths["summary"]
            if "markdown" in paths:
                print(f"  - 종합 리포트: {paths['markdown']}")
            if "json" in paths:
                print(f"  - JSON 데이터: {paths['json']}")
        if "weekly_sector" in result.report_paths:
            print(f"  - 주간 섹터 리포트: {result.report_paths['weekly_sector']}")

    print(f"\n⏱️ 총 소요 시간: {result.stats.get('total_time', 0):.1f}초")
    print("=" * 60)
