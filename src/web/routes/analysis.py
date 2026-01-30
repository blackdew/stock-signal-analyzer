"""
Analysis API Routes

분석 결과 및 순위 관련 API.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from src.web.schemas import (
    AnalysisResultSchema,
    AnalysisRunRequest,
    AnalysisStatsSchema,
    AnalysisTaskResponse,
    DataQualitySummarySchema,
    ErrorResponse,
    RankingSchema,
    SectorAnalysisSchema,
    StockAnalysisSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# 헬퍼 함수
# =============================================================================


def _get_all_analysis_files(output_dir: str = "output") -> List[Path]:
    """모든 분석 JSON 파일 목록을 반환합니다 (최신순)."""
    data_dir = Path(output_dir) / "data"
    if not data_dir.exists():
        return []

    json_files = list(data_dir.glob("analysis_*.json"))
    # 날짜순 정렬 (최신 순)
    json_files.sort(reverse=True)
    return json_files


def _get_latest_analysis_path(output_dir: str = "output") -> Optional[Path]:
    """최신 분석 JSON 파일 경로를 찾습니다."""
    files = _get_all_analysis_files(output_dir)
    return files[0] if files else None


def _get_analysis_path_by_date(date: str, output_dir: str = "output") -> Optional[Path]:
    """특정 날짜의 분석 JSON 파일 경로를 찾습니다."""
    data_dir = Path(output_dir) / "data"
    file_path = data_dir / f"analysis_{date}.json"
    return file_path if file_path.exists() else None


def _stock_dict_to_schema(stock_dict: Dict[str, Any]) -> StockAnalysisSchema:
    """딕셔너리를 StockAnalysisSchema로 변환"""
    return StockAnalysisSchema(
        symbol=stock_dict.get("symbol", ""),
        name=stock_dict.get("name", ""),
        sector=stock_dict.get("sector", ""),
        group=stock_dict.get("group", ""),
        market_cap=stock_dict.get("market_cap", 0),
        # V2 카테고리 점수
        technical_score=stock_dict.get("technical_score", 0),
        supply_score=stock_dict.get("supply_score", 0),
        fundamental_score=stock_dict.get("fundamental_score", 0),
        market_score=stock_dict.get("market_score", 0),
        risk_score=stock_dict.get("risk_score", 0),
        relative_strength_score=stock_dict.get("relative_strength_score", 0),
        # V3 8대 핵심 루브릭 점수
        valuation_score=stock_dict.get("valuation_score", 0),
        momentum_score=stock_dict.get("momentum_score", 0),
        sector_score=stock_dict.get("sector_score", 0),
        shareholder_score=stock_dict.get("shareholder_score", 0),
        total_score=stock_dict.get("total_score", 0),
        investment_grade=stock_dict.get("investment_grade", "Hold"),
        rank_in_group=stock_dict.get("rank_in_group", 0),
        final_rank=stock_dict.get("final_rank"),
        # 세부 분석 정보
        technical_details=stock_dict.get("technical_details"),
        supply_details=stock_dict.get("supply_details"),
        fundamental_details=stock_dict.get("fundamental_details"),
        market_details=stock_dict.get("market_details"),
        risk_details=stock_dict.get("risk_details"),
        relative_strength_details=stock_dict.get("relative_strength_details"),
        # V3 세부 분석 정보
        valuation_details=stock_dict.get("valuation_details"),
        momentum_details=stock_dict.get("momentum_details"),
        sector_details=stock_dict.get("sector_details"),
        shareholder_details=stock_dict.get("shareholder_details"),
        # LLM 분석 결과
        summary=stock_dict.get("summary"),
        financial_analysis=stock_dict.get("financial_analysis"),
        technical_analysis=stock_dict.get("technical_analysis"),
        market_sentiment=stock_dict.get("market_sentiment"),
        comprehensive_analysis=stock_dict.get("comprehensive_analysis"),
        investment_thesis=stock_dict.get("investment_thesis"),
        risks=stock_dict.get("risks"),
    )


def _sector_dict_to_schema(sector_dict: Dict[str, Any]) -> SectorAnalysisSchema:
    """딕셔너리를 SectorAnalysisSchema로 변환"""
    top_stocks = [
        _stock_dict_to_schema(s)
        for s in sector_dict.get("top_stocks", [])
    ]
    return SectorAnalysisSchema(
        sector_name=sector_dict.get("sector_name", ""),
        stock_count=sector_dict.get("stock_count", 0),
        total_market_cap=sector_dict.get("total_market_cap", 0),
        weighted_score=sector_dict.get("weighted_score", 0),
        simple_score=sector_dict.get("simple_score", 0),
        technical_score=sector_dict.get("technical_score", 0),
        supply_score=sector_dict.get("supply_score", 0),
        fundamental_score=sector_dict.get("fundamental_score", 0),
        market_score=sector_dict.get("market_score", 0),
        top_stocks=top_stocks,
        rank=sector_dict.get("rank", 0),
    )


def _load_analysis_data(file_path: Path) -> Dict[str, Any]:
    """분석 JSON 파일을 로드합니다."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _merge_top5_with_all_selected(
    final_top5: List[Dict[str, Any]],
    all_selected: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    final_top5 데이터를 all_selected의 전체 데이터로 보강합니다.

    final_top5에는 rank, selection_reason만 있고 LLM 분석이 누락된 경우가 있어,
    all_selected에서 동일 종목의 전체 데이터를 찾아 병합합니다.

    Args:
        final_top5: Top 5 종목 리스트 (rank, selection_reason 포함)
        all_selected: 전체 선정 종목 리스트 (LLM 분석 포함)

    Returns:
        병합된 Top 5 종목 리스트
    """
    if not final_top5 or not all_selected:
        return final_top5

    # all_selected를 symbol로 인덱싱
    selected_by_symbol = {s.get("symbol"): s for s in all_selected if s.get("symbol")}

    merged = []
    for top5_stock in final_top5:
        symbol = top5_stock.get("symbol")
        if symbol and symbol in selected_by_symbol:
            # all_selected의 전체 데이터를 기반으로 하고, top5의 rank/selection_reason만 덮어씀
            full_data = selected_by_symbol[symbol].copy()
            # final_top5에만 있는 필드 (rank, selection_reason, final_rank 등)를 병합
            full_data["rank"] = top5_stock.get("rank", full_data.get("rank"))
            full_data["final_rank"] = top5_stock.get("final_rank", top5_stock.get("rank"))
            full_data["selection_reason"] = top5_stock.get("selection_reason", full_data.get("selection_reason"))
            merged.append(full_data)
        else:
            # all_selected에 없으면 원본 사용
            merged.append(top5_stock)

    return merged


def _build_analysis_result(data: Dict[str, Any]) -> AnalysisResultSchema:
    """분석 데이터를 AnalysisResultSchema로 변환합니다."""
    # RankingSchema 변환 - 실제 JSON 구조에 맞게 수정
    ranking_data = data.get("ranking")
    if ranking_data:
        # 기존 구조 (ranking 키가 있는 경우)
        ranking = RankingSchema(
            kospi_top10=[_stock_dict_to_schema(s) for s in ranking_data.get("kospi_top10", [])],
            kospi_11_20=[_stock_dict_to_schema(s) for s in ranking_data.get("kospi_11_20", [])],
            kosdaq_top10=[_stock_dict_to_schema(s) for s in ranking_data.get("kosdaq_top10", [])],
            sector_top=[_stock_dict_to_schema(s) for s in ranking_data.get("sector_top", [])],
            final_18=[_stock_dict_to_schema(s) for s in ranking_data.get("final_18", [])],
            final_top5=[_stock_dict_to_schema(s) for s in ranking_data.get("final_top5", [])],
            top_sectors=[_sector_dict_to_schema(s) for s in ranking_data.get("top_sectors", [])],
        )
    else:
        # 새 구조 (개별 키로 저장된 경우)
        kospi_top10 = data.get("kospi_top10", [])
        kospi_11_20 = data.get("kospi_11_20", [])
        kosdaq_top10 = data.get("kosdaq_top10", [])

        # sector_stocks는 {섹터명: [종목리스트]} 형태의 딕셔너리
        sector_stocks_dict = data.get("sector_stocks", {})
        sector_stocks = []
        if isinstance(sector_stocks_dict, dict):
            for sector_name, stocks in sector_stocks_dict.items():
                sector_stocks.extend(stocks if isinstance(stocks, list) else [])
        elif isinstance(sector_stocks_dict, list):
            sector_stocks = sector_stocks_dict

        final_top5_raw = data.get("final_top5", [])
        all_selected = data.get("all_selected", [])

        # final_top5를 all_selected의 전체 데이터와 병합 (LLM 분석 포함)
        final_top5 = _merge_top5_with_all_selected(final_top5_raw, all_selected)

        # top_sectors가 문자열 리스트인 경우, sector_rankings에서 상세 정보 매핑
        top_sector_names = data.get("top_sectors", [])
        sector_rankings_list = data.get("sector_rankings", [])
        if top_sector_names and len(top_sector_names) > 0 and isinstance(top_sector_names[0], str):
            sector_map = {s.get("sector_name"): s for s in sector_rankings_list if isinstance(s, dict)}
            top_sectors = [sector_map.get(name) for name in top_sector_names if sector_map.get(name)]
        else:
            top_sectors = top_sector_names if isinstance(top_sector_names, list) else []

        # 데이터가 있는지 확인
        has_data = any([kospi_top10, kospi_11_20, kosdaq_top10, final_top5, all_selected])

        if has_data:
            ranking = RankingSchema(
                kospi_top10=[_stock_dict_to_schema(s) for s in kospi_top10],
                kospi_11_20=[_stock_dict_to_schema(s) for s in kospi_11_20],
                kosdaq_top10=[_stock_dict_to_schema(s) for s in kosdaq_top10],
                sector_top=[_stock_dict_to_schema(s) for s in sector_stocks],
                final_18=[_stock_dict_to_schema(s) for s in all_selected],
                final_top5=[_stock_dict_to_schema(s) for s in final_top5],
                top_sectors=[_sector_dict_to_schema(s) for s in top_sectors if s],
            )
        else:
            ranking = None

    # SectorAnalysisSchema 리스트 변환
    sectors_data = data.get("sectors") or data.get("sector_rankings", [])
    sectors = [_sector_dict_to_schema(s) for s in sectors_data] if sectors_data else None

    # Stats
    stats_data = data.get("stats") or data.get("summary", {})
    final_top5_list = stats_data.get("final_top5") or data.get("final_top5", [])
    stats = AnalysisStatsSchema(
        total_time=stats_data.get("total_time", 0),
        phases=stats_data.get("phases", {}),
        final_stocks=stats_data.get("final_stocks") or len(data.get("all_selected", [])),
        final_top5=final_top5_list if isinstance(final_top5_list, list) else None,
    )

    # DataQuality
    quality_data = data.get("data_quality")
    data_quality = None
    if quality_data:
        data_quality = DataQualitySummarySchema(
            total_count=quality_data.get("total_count", 0),
            valid_count=quality_data.get("valid_count", 0),
            invalid_count=quality_data.get("invalid_count", 0),
            avg_quality_score=quality_data.get("avg_quality_score", 0),
            invalid_symbols=quality_data.get("invalid_symbols", []),
        )

    return AnalysisResultSchema(
        generated_at=datetime.fromisoformat(data.get("generated_at", datetime.now().isoformat())),
        ranking=ranking,
        sectors=sectors,
        report_paths=data.get("report_paths", {}),
        stats=stats,
        data_quality=data_quality,
    )


def _run_analysis_task_sync(
    task_id: str,
    app_state: Any,
    options: AnalysisRunRequest,
):
    """동기적으로 분석을 실행합니다 (별도 스레드에서 실행됨)."""
    from src.core.orchestrator import Orchestrator, RunOptions
    from src.core.logging_config import register_task_log_handler, unregister_task_log_handler
    import time

    start_time = time.time()
    logger.info(f"Analysis task {task_id} started (mode: {options.mode}, use_cache: {options.use_cache})")

    # 태스크 로그 핸들러 등록
    register_task_log_handler(task_id, app_state)

    # 시작 로그 추가
    app_state.add_task_log(task_id, "분석을 시작합니다...", "info")

    try:
        run_options = RunOptions(
            mode=options.mode,
            sector_only=options.sector_only,
            use_cache=options.use_cache,
            skip_news=options.skip_news,
        )

        orchestrator = Orchestrator(
            use_cache=options.use_cache,
            skip_news=options.skip_news,
        )

        # 새 이벤트 루프에서 비동기 작업 실행
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if options.sector_only:
                result = loop.run_until_complete(orchestrator.run_sector_only())
            elif options.mode == "weekly":
                result = loop.run_until_complete(orchestrator.run_weekly())
            else:
                result = loop.run_until_complete(orchestrator.run_daily(run_options))
        finally:
            loop.close()

        duration = time.time() - start_time
        logger.info(f"Analysis task {task_id} completed in {duration:.1f}s")

        # 완료 로그 추가
        app_state.add_task_log(task_id, f"분석 완료! (소요 시간: {duration:.1f}초)", "info")

        app_state.analysis_tasks[task_id] = {
            "status": "completed",
            "started_at": app_state.analysis_tasks[task_id]["started_at"],
            "completed_at": datetime.now(),
            "result": result,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Analysis task {task_id} failed after {duration:.1f}s: {e}")

        # 에러 로그 추가
        app_state.add_task_log(task_id, f"분석 실패: {str(e)}", "error")

        app_state.analysis_tasks[task_id] = {
            "status": "failed",
            "started_at": app_state.analysis_tasks[task_id].get("started_at"),
            "error": str(e),
        }
    finally:
        # 태스크 로그 핸들러 제거
        unregister_task_log_handler(task_id)


# =============================================================================
# API 엔드포인트
# =============================================================================


@router.get(
    "/analysis/history",
    response_model=List[Dict[str, Any]],
)
async def get_analysis_history() -> List[Dict[str, Any]]:
    """
    분석 히스토리 목록을 조회합니다.

    Returns:
        List[Dict]: 분석 파일 목록 (날짜, 파일경로)
    """
    files = _get_all_analysis_files()
    history = []
    for f in files:
        # 파일명에서 날짜 추출 (analysis_2026-01-24.json -> 2026-01-24)
        date_str = f.stem.replace("analysis_", "")
        try:
            data = _load_analysis_data(f)
            generated_at = data.get("generated_at", "")
            final_top5 = data.get("final_top5", [])
            top5_names = [s.get("name", "") for s in final_top5[:3]] if final_top5 else []
        except Exception:
            generated_at = ""
            top5_names = []

        history.append({
            "date": date_str,
            "generated_at": generated_at,
            "preview": ", ".join(top5_names) if top5_names else "데이터 없음",
        })
    return history


@router.get(
    "/analysis/latest",
    response_model=AnalysisResultSchema,
    responses={404: {"model": ErrorResponse}},
)
async def get_latest_analysis() -> AnalysisResultSchema:
    """
    최신 분석 결과를 조회합니다.

    Returns:
        AnalysisResultSchema
    """
    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다. 먼저 분석을 실행하세요.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    return _build_analysis_result(data)


@router.get(
    "/analysis/{date}",
    response_model=AnalysisResultSchema,
    responses={404: {"model": ErrorResponse}},
)
async def get_analysis_by_date(date: str) -> AnalysisResultSchema:
    """
    특정 날짜의 분석 결과를 조회합니다.

    Args:
        date: 날짜 (YYYY-MM-DD 형식)

    Returns:
        AnalysisResultSchema
    """
    file_path = _get_analysis_path_by_date(date)

    if file_path is None:
        raise HTTPException(status_code=404, detail=f"{date} 날짜의 분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    return _build_analysis_result(data)


@router.post(
    "/analysis/run",
    response_model=AnalysisTaskResponse,
)
async def run_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    options: AnalysisRunRequest = AnalysisRunRequest(),
) -> AnalysisTaskResponse:
    """
    분석을 비동기로 실행합니다.

    Args:
        options: 분석 실행 옵션

    Returns:
        AnalysisTaskResponse (task_id, status)
    """
    task_id = str(uuid.uuid4())
    app_state = request.app.state.app_state

    # 태스크 상태 초기화 (응답 전에 설정)
    app_state.analysis_tasks[task_id] = {"status": "running", "started_at": datetime.now()}

    # 별도 스레드에서 분석 실행 (이벤트 루프 블로킹 방지)
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(_run_analysis_task_sync, task_id, app_state, options)

    return AnalysisTaskResponse(
        task_id=task_id,
        status="running",
        message=f"분석이 시작되었습니다. 모드: {options.mode}",
    )


@router.get(
    "/analysis/task/{task_id}",
    response_model=AnalysisTaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_analysis_task_status(
    request: Request,
    task_id: str,
) -> AnalysisTaskResponse:
    """
    분석 태스크 상태를 조회합니다.

    Args:
        task_id: 태스크 ID

    Returns:
        AnalysisTaskResponse
    """
    app_state = request.app.state.app_state

    if task_id not in app_state.analysis_tasks:
        raise HTTPException(status_code=404, detail=f"태스크를 찾을 수 없습니다: {task_id}")

    task = app_state.analysis_tasks[task_id]
    status = task.get("status", "unknown")
    message = None

    if status == "completed":
        message = "분석이 완료되었습니다."
    elif status == "failed":
        message = f"분석 실패: {task.get('error', 'Unknown error')}"
    elif status == "running":
        message = "분석이 진행 중입니다."

    return AnalysisTaskResponse(
        task_id=task_id,
        status=status,
        message=message,
    )


@router.get(
    "/ranking",
    response_model=RankingSchema,
    responses={404: {"model": ErrorResponse}},
)
async def get_ranking() -> RankingSchema:
    """
    Top 18, Top 5 순위를 조회합니다.

    Returns:
        RankingSchema
    """
    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    # 기존 구조 (ranking 키가 있는 경우)
    ranking_data = data.get("ranking")
    if ranking_data:
        return RankingSchema(
            kospi_top10=[_stock_dict_to_schema(s) for s in ranking_data.get("kospi_top10", [])],
            kospi_11_20=[_stock_dict_to_schema(s) for s in ranking_data.get("kospi_11_20", [])],
            kosdaq_top10=[_stock_dict_to_schema(s) for s in ranking_data.get("kosdaq_top10", [])],
            sector_top=[_stock_dict_to_schema(s) for s in ranking_data.get("sector_top", [])],
            final_18=[_stock_dict_to_schema(s) for s in ranking_data.get("final_18", [])],
            final_top5=[_stock_dict_to_schema(s) for s in ranking_data.get("final_top5", [])],
            top_sectors=[_sector_dict_to_schema(s) for s in ranking_data.get("top_sectors", [])],
        )

    # 새 구조 (개별 키로 저장된 경우)
    kospi_top10 = data.get("kospi_top10", [])
    kospi_11_20 = data.get("kospi_11_20", [])
    kosdaq_top10 = data.get("kosdaq_top10", [])

    # sector_stocks는 {섹터명: [종목리스트]} 형태의 딕셔너리
    sector_stocks_dict = data.get("sector_stocks", {})
    sector_stocks = []
    if isinstance(sector_stocks_dict, dict):
        for sector_name, stocks in sector_stocks_dict.items():
            sector_stocks.extend(stocks if isinstance(stocks, list) else [])
    elif isinstance(sector_stocks_dict, list):
        sector_stocks = sector_stocks_dict

    final_top5_raw = data.get("final_top5", [])
    all_selected = data.get("all_selected", [])

    # final_top5를 all_selected의 전체 데이터와 병합 (LLM 분석 포함)
    final_top5 = _merge_top5_with_all_selected(final_top5_raw, all_selected)

    # top_sectors가 문자열 리스트인 경우, sector_rankings에서 상세 정보 매핑
    top_sector_names = data.get("top_sectors", [])
    sector_rankings = data.get("sector_rankings", [])
    if top_sector_names and len(top_sector_names) > 0 and isinstance(top_sector_names[0], str):
        sector_map = {s.get("sector_name"): s for s in sector_rankings if isinstance(s, dict)}
        top_sectors = [sector_map.get(name) for name in top_sector_names if sector_map.get(name)]
    else:
        top_sectors = top_sector_names if isinstance(top_sector_names, list) else []

    # 데이터가 있는지 확인
    has_data = any([kospi_top10, kospi_11_20, kosdaq_top10, final_top5, all_selected])
    if not has_data:
        raise HTTPException(status_code=404, detail="순위 데이터가 없습니다.")

    return RankingSchema(
        kospi_top10=[_stock_dict_to_schema(s) for s in kospi_top10],
        kospi_11_20=[_stock_dict_to_schema(s) for s in kospi_11_20],
        kosdaq_top10=[_stock_dict_to_schema(s) for s in kosdaq_top10],
        sector_top=[_stock_dict_to_schema(s) for s in sector_stocks],
        final_18=[_stock_dict_to_schema(s) for s in all_selected],
        final_top5=[_stock_dict_to_schema(s) for s in final_top5],
        top_sectors=[_sector_dict_to_schema(s) for s in top_sectors if s],
    )


# =============================================================================
# SSE 로그 스트리밍
# =============================================================================


@router.get(
    "/analysis/task/{task_id}/logs",
    responses={404: {"model": ErrorResponse}},
)
async def stream_task_logs(
    request: Request,
    task_id: str,
) -> StreamingResponse:
    """
    분석 태스크 로그를 SSE로 스트리밍합니다.

    Args:
        task_id: 태스크 ID

    Returns:
        StreamingResponse (text/event-stream)
    """
    app_state = request.app.state.app_state

    if task_id not in app_state.analysis_tasks:
        raise HTTPException(status_code=404, detail=f"태스크를 찾을 수 없습니다: {task_id}")

    async def generate_events():
        """SSE 이벤트를 생성합니다."""
        last_index = 0
        heartbeat_interval = 15  # 15초마다 하트비트
        poll_interval = 0.5  # 0.5초마다 로그 확인
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            # 클라이언트 연결 확인
            if await request.is_disconnected():
                break

            # 새 로그 확인
            logs = app_state.get_task_logs(task_id, since_index=last_index)
            if logs:
                for log_entry in logs:
                    data = json.dumps(log_entry, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    last_index += 1

            # 태스크 상태 확인
            task = app_state.analysis_tasks.get(task_id, {})
            status = task.get("status", "unknown")

            if status in ("completed", "failed"):
                # 최종 상태 이벤트 전송
                final_event = {
                    "type": "status",
                    "status": status,
                    "message": "분석이 완료되었습니다." if status == "completed" else f"분석 실패: {task.get('error', 'Unknown error')}",
                }
                yield f"event: status\ndata: {json.dumps(final_event, ensure_ascii=False)}\n\n"
                break

            # 하트비트 전송 (연결 유지)
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                yield f": heartbeat\n\n"
                last_heartbeat = current_time

            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        },
    )
