"""
Sectors API Routes

섹터 분석 관련 API.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from src.core.config import SECTORS
from src.web.schemas import (
    ErrorResponse,
    SectorAnalysisSchema,
    SectorListResponse,
    StockAnalysisSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# 헬퍼 함수
# =============================================================================


def _get_latest_analysis_path(output_dir: str = "output") -> Optional[Path]:
    """최신 분석 JSON 파일 경로를 찾습니다."""
    data_dir = Path(output_dir) / "data"
    if not data_dir.exists():
        return None

    json_files = list(data_dir.glob("analysis_*.json"))
    if not json_files:
        return None

    json_files.sort(reverse=True)
    return json_files[0]


def _load_analysis_data(file_path: Path) -> Dict[str, Any]:
    """분석 JSON 파일을 로드합니다."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _stock_dict_to_schema(stock_dict: Dict[str, Any]) -> StockAnalysisSchema:
    """딕셔너리를 StockAnalysisSchema로 변환"""
    return StockAnalysisSchema(
        symbol=stock_dict.get("symbol", ""),
        name=stock_dict.get("name", ""),
        sector=stock_dict.get("sector", ""),
        group=stock_dict.get("group", ""),
        market_cap=stock_dict.get("market_cap", 0),
        technical_score=stock_dict.get("technical_score", 0),
        supply_score=stock_dict.get("supply_score", 0),
        fundamental_score=stock_dict.get("fundamental_score", 0),
        market_score=stock_dict.get("market_score", 0),
        risk_score=stock_dict.get("risk_score", 0),
        relative_strength_score=stock_dict.get("relative_strength_score", 0),
        total_score=stock_dict.get("total_score", 0),
        investment_grade=stock_dict.get("investment_grade", "Hold"),
        rank_in_group=stock_dict.get("rank_in_group", 0),
        final_rank=stock_dict.get("final_rank"),
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


def _get_sector_data_from_ranking(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ranking 데이터에서 섹터 정보를 추출합니다."""
    ranking = data.get("ranking", {})
    return ranking.get("top_sectors", [])


# =============================================================================
# API 엔드포인트
# =============================================================================


@router.get(
    "/sectors",
    response_model=SectorListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_sectors() -> SectorListResponse:
    """
    섹터별 분석 결과를 조회합니다.

    Returns:
        SectorListResponse
    """
    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다. 먼저 분석을 실행하세요.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    # sectors 또는 ranking.top_sectors에서 섹터 데이터 추출
    sectors_data = data.get("sectors")
    if not sectors_data:
        sectors_data = _get_sector_data_from_ranking(data)

    if not sectors_data:
        raise HTTPException(status_code=404, detail="섹터 분석 결과가 없습니다.")

    sectors = [_sector_dict_to_schema(s) for s in sectors_data]

    return SectorListResponse(
        count=len(sectors),
        sectors=sectors,
    )


@router.get(
    "/sectors/available",
    response_model=List[str],
)
async def get_available_sectors() -> List[str]:
    """
    분석 가능한 섹터 목록을 조회합니다.

    Returns:
        섹터명 리스트
    """
    return list(SECTORS.keys())


@router.get(
    "/sectors/{sector_name}",
    response_model=SectorAnalysisSchema,
    responses={404: {"model": ErrorResponse}},
)
async def get_sector_detail(sector_name: str) -> SectorAnalysisSchema:
    """
    특정 섹터의 상세 정보를 조회합니다.

    Args:
        sector_name: 섹터명

    Returns:
        SectorAnalysisSchema
    """
    # 섹터 존재 여부 확인
    if sector_name not in SECTORS:
        available = list(SECTORS.keys())
        raise HTTPException(
            status_code=404,
            detail=f"존재하지 않는 섹터입니다: {sector_name}. 사용 가능한 섹터: {available}",
        )

    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다. 먼저 분석을 실행하세요.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    # sectors 또는 ranking.top_sectors에서 섹터 데이터 추출
    sectors_data = data.get("sectors")
    if not sectors_data:
        sectors_data = _get_sector_data_from_ranking(data)

    # 해당 섹터 찾기
    for sector_dict in sectors_data:
        if sector_dict.get("sector_name") == sector_name:
            return _sector_dict_to_schema(sector_dict)

    raise HTTPException(
        status_code=404,
        detail=f"섹터 '{sector_name}'의 분석 결과가 없습니다. 분석이 아직 실행되지 않았을 수 있습니다.",
    )


@router.get(
    "/sectors/{sector_name}/stocks",
    response_model=List[StockAnalysisSchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_sector_stocks(sector_name: str) -> List[StockAnalysisSchema]:
    """
    특정 섹터의 종목 리스트를 조회합니다.

    Args:
        sector_name: 섹터명

    Returns:
        StockAnalysisSchema 리스트
    """
    # 섹터 존재 여부 확인
    if sector_name not in SECTORS:
        available = list(SECTORS.keys())
        raise HTTPException(
            status_code=404,
            detail=f"존재하지 않는 섹터입니다: {sector_name}. 사용 가능한 섹터: {available}",
        )

    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    # sectors 또는 ranking.top_sectors에서 섹터 데이터 추출
    sectors_data = data.get("sectors")
    if not sectors_data:
        sectors_data = _get_sector_data_from_ranking(data)

    # 해당 섹터 찾기
    for sector_dict in sectors_data:
        if sector_dict.get("sector_name") == sector_name:
            top_stocks = sector_dict.get("top_stocks", [])
            return [_stock_dict_to_schema(s) for s in top_stocks]

    raise HTTPException(
        status_code=404,
        detail=f"섹터 '{sector_name}'의 종목 정보가 없습니다.",
    )
