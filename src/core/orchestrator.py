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
from src.agents.analysis.data_quality import DataQualityError, DataQualitySummary
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
        strict: 데이터 품질 기준 미달 시 실행 중단
    """
    mode: str = "daily"
    sector_only: bool = False
    group: str = "all"
    output_format: str = "both"
    use_cache: bool = True
    skip_news: bool = False
    output_dir: str = "output"
    verbose: bool = False
    strict: bool = False


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
        data_quality_summary: 데이터 품질 요약
    """
    generated_at: datetime
    ranking_result: Optional[RankingResult] = None
    sector_results: Optional[List[SectorAnalysisResult]] = None
    report_paths: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    data_quality_summary: Optional[Dict[str, Any]] = None


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

        self.logger.info("🚀 투자 기회 분석 시작")

        try:
            # Phase 0: 분석 대상 확정
            phase_start = time.time()
            self.logger.info("Phase 0: 분석 대상 확정")
            target_info = await self._confirm_analysis_targets()
            phase_time = time.time() - phase_start
            stats["phases"]["target_confirmation"] = {"time": round(phase_time, 2)}
            stats["targets"] = target_info
            self.logger.info(f"Phase 0 완료 ({phase_time:.1f}초)")

            # Phase 1: 순위 산정 (데이터 수집 + 분석 통합)
            phase_start = time.time()
            self.logger.info("Phase 1: 데이터 수집 및 순위 산정 시작")

            # 동적으로 가져온 섹터별 종목 코드 추출
            dynamic_sectors = None
            if "sectors" in target_info:
                dynamic_sectors = {
                    sector_name: sector_data.get("symbols", [])
                    for sector_name, sector_data in target_info["sectors"].items()
                    if sector_data.get("symbols")
                }
                self.logger.info(f"동적 섹터 데이터 사용: {len(dynamic_sectors)}개 섹터")

            ranking_result = await self._run_with_retry(
                lambda: self.ranking_agent.rank(dynamic_sectors),
                "순위 산정"
            )

            phase_time = time.time() - phase_start
            stats["phases"]["ranking"] = {"time": round(phase_time, 2)}
            self.logger.info(f"Phase 1 완료 ({phase_time:.1f}초)")

            # 데이터 품질 요약
            quality_summary = self.ranking_agent.get_quality_summary()
            quality_summary_dict = None

            if quality_summary:
                quality_summary_dict = {
                    "total_count": quality_summary.total_count,
                    "valid_count": quality_summary.valid_count,
                    "invalid_count": quality_summary.invalid_count,
                    "avg_quality_score": quality_summary.avg_quality_score,
                    "invalid_symbols": quality_summary.invalid_symbols,
                }

                # 품질 요약은 간단히 1줄로
                self.logger.info(
                    f"📊 데이터 품질: {quality_summary.valid_count}/{quality_summary.total_count} 유효 "
                    f"(평균 {quality_summary.avg_quality_score:.0f}점)"
                )

                if quality_summary.invalid_symbols:
                    self.logger.warning(
                        f"⚠️ 품질 미달: {', '.join(quality_summary.invalid_symbols[:3])}"
                        + (" 외" if len(quality_summary.invalid_symbols) > 3 else "")
                    )

                # --strict 모드: 품질 기준 미달 시 실행 중단
                if options.strict and quality_summary.invalid_count > 0:
                    error_msg = (
                        f"데이터 품질 기준 미달: {quality_summary.invalid_count}개 종목이 "
                        f"필수 데이터 항목을 충족하지 못했습니다."
                    )
                    self.logger.error(f"🚫 [STRICT MODE] {error_msg}")
                    raise DataQualityError(error_msg, quality_summary)

            stats["data_quality"] = quality_summary_dict

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

            # 완료 요약
            top5_str = ", ".join([f"{s.name}({s.total_score:.0f})" for s in ranking_result.final_top5])
            self.logger.info(f"✅ 분석 완료 ({total_time:.1f}초) - {len(ranking_result.final_18)}개 종목")
            self.logger.info(f"🏆 Top 5: {top5_str}")

            return AnalysisOutput(
                generated_at=datetime.now(),
                ranking_result=ranking_result,
                sector_results=ranking_result.top_sectors,
                report_paths=report_paths,
                stats=stats,
                data_quality_summary=quality_summary_dict,
            )

        except DataQualityError:
            raise  # strict 모드에서 데이터 품질 오류는 그대로 전파
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

        self.logger.info(f"🚀 주간 섹터 분석 시작 ({week_str})")

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

            top3_str = ", ".join([f"{s.sector_name}({s.weighted_score:.0f})" for s in sector_results[:3]])
            self.logger.info(f"✅ 주간 섹터 분석 완료 ({total_time:.1f}초) - {len(sector_results)}개 섹터")
            self.logger.info(f"🏆 상위 3: {top3_str}")

            return AnalysisOutput(
                generated_at=datetime.now(),
                sector_results=sector_results,
                report_paths=report_paths,
                stats=stats
            )

        except Exception as e:
            self.logger.error(f"주간 섹터 분석 실패: {e}")
            raise

    async def _confirm_analysis_targets(self) -> Dict[str, Any]:
        """
        분석 대상을 확정하고 로그에 출력합니다.

        Returns:
            대상 정보 딕셔너리
        """
        from src.data.fetcher import StockDataFetcher
        from src.data.sector_fetcher import SectorFetcher, SECTOR_TO_NAVER_CODES

        fetcher = StockDataFetcher()
        sector_fetcher = SectorFetcher()
        target_info: Dict[str, Any] = {}

        # 1. KOSPI Top 20 확정
        try:
            kospi_stocks = fetcher.get_market_cap_rank("KOSPI", top_n=20)
            kospi_top10 = kospi_stocks[:10]
            kospi_11_20 = kospi_stocks[10:20]

            target_info["kospi_top10"] = [
                {"symbol": s.symbol, "name": s.name} for s in kospi_top10
            ]
            target_info["kospi_11_20"] = [
                {"symbol": s.symbol, "name": s.name} for s in kospi_11_20
            ]
        except Exception as e:
            self.logger.error(f"KOSPI 종목 조회 실패: {e}")
            target_info["kospi_top10"] = []
            target_info["kospi_11_20"] = []

        # 2. KOSDAQ Top 10 확정
        try:
            kosdaq_stocks = fetcher.get_market_cap_rank("KOSDAQ", top_n=10)
            target_info["kosdaq_top10"] = [
                {"symbol": s.symbol, "name": s.name} for s in kosdaq_stocks
            ]
        except Exception as e:
            self.logger.error(f"KOSDAQ 종목 조회 실패: {e}")
            target_info["kosdaq_top10"] = []

        # 3. 섹터별 종목 확정 (동적 조회)
        target_info["sectors"] = {}
        sector_count = 0
        total_sector_stocks = 0
        sector_list = list(SECTOR_TO_NAVER_CODES.keys())
        total_sectors = len(sector_list)

        self.logger.info(f"📡 {total_sectors}개 섹터 데이터 수집 시작")

        for i, sector_name in enumerate(sector_list, 1):
            try:
                # 시총 상위 10개 종목 조회 (시총 조회 포함)
                stocks = sector_fetcher.get_sector_stocks(
                    sector_name, top_n=10, fetch_market_cap=True
                )
                symbols = [s.symbol for s in stocks]
                names = [s.name for s in stocks]

                target_info["sectors"][sector_name] = {
                    "symbols": symbols,
                    "names": names,
                    "count": len(stocks)
                }
                sector_count += 1
                total_sector_stocks += len(stocks)

                # 섹터 수집 진행 로그 (3개마다)
                if i % 3 == 0 or i == total_sectors:
                    self.logger.info(f"📡 섹터 수집 [{i}/{total_sectors}] {sector_name} ({len(stocks)}개)")

            except Exception as e:
                self.logger.debug(f"{sector_name}: 조회 실패 ({e})")
                target_info["sectors"][sector_name] = {
                    "symbols": [],
                    "names": [],
                    "count": 0
                }

        # 총 분석 대상 수
        kospi_count = len(target_info.get("kospi_top10", [])) + len(target_info.get("kospi_11_20", []))
        kosdaq_count = len(target_info.get("kosdaq_top10", []))
        total_count = kospi_count + kosdaq_count + total_sector_stocks
        target_info["total_count"] = total_count

        # 요약 로그 (1줄)
        self.logger.info(
            f"📋 분석 대상: KOSPI {kospi_count}개, KOSDAQ {kosdaq_count}개, "
            f"섹터 {sector_count}개({total_sector_stocks}종목) → 총 {total_count}개"
        )

        return target_info

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
