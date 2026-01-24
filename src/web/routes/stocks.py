"""
Stocks API Routes

개별 종목 관련 API.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Query

from src.data.fetcher import StockDataFetcher
from src.web.schemas import (
    ErrorResponse,
    PriceHistoryItem,
    StockAnalysisSchema,
    StockHistoryResponse,
    StockListResponse,
    StockSupplyResponse,
    SupplyItem,
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
    # 기술적 분석 세부 정보에서 52주 고저가 추출
    tech_details = stock_dict.get("technical_details", {})
    high_52w = stock_dict.get("high_52w") or tech_details.get("high_52w")
    low_52w = stock_dict.get("low_52w") or tech_details.get("low_52w")

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
        high_52w=high_52w,
        low_52w=low_52w,
        rank_in_group=stock_dict.get("rank_in_group", 0),
        final_rank=stock_dict.get("final_rank"),
        # 세부 분석 정보
        technical_details=stock_dict.get("technical_details"),
        supply_details=stock_dict.get("supply_details"),
        fundamental_details=stock_dict.get("fundamental_details"),
        market_details=stock_dict.get("market_details"),
        risk_details=stock_dict.get("risk_details"),
        relative_strength_details=stock_dict.get("relative_strength_details"),
    )


def _get_all_stocks_from_ranking(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ranking 데이터에서 모든 종목 정보를 추출합니다 (중복 제거)."""
    ranking = data.get("ranking", {})
    seen_symbols = set()
    stocks = []

    # 모든 그룹에서 종목 수집
    for key in ["final_18", "kospi_top10", "kospi_11_20", "kosdaq_top10", "sector_top"]:
        for stock in ranking.get(key, []):
            symbol = stock.get("symbol")
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                stocks.append(stock)

    # top_sectors의 top_stocks에서도 추출
    for sector in ranking.get("top_sectors", []):
        for stock in sector.get("top_stocks", []):
            symbol = stock.get("symbol")
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                stocks.append(stock)

    return stocks


# =============================================================================
# API 엔드포인트
# =============================================================================


@router.get(
    "/stocks",
    response_model=StockListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_stocks(
    group: Optional[str] = Query(
        None,
        description="그룹 필터 (kospi_top10, kospi_11_20, kosdaq_top10, sector_*)",
    ),
    limit: int = Query(50, ge=1, le=200, description="최대 반환 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
) -> StockListResponse:
    """
    분석된 종목 리스트를 조회합니다.

    Args:
        group: 그룹 필터 (선택)
        limit: 최대 반환 개수
        offset: 시작 위치

    Returns:
        StockListResponse
    """
    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    all_stocks = _get_all_stocks_from_ranking(data)

    # 그룹 필터 적용
    if group:
        all_stocks = [s for s in all_stocks if s.get("group") == group]

    # 점수순 정렬
    all_stocks.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    # 페이지네이션
    total = len(all_stocks)
    paginated = all_stocks[offset:offset + limit]

    stocks = [_stock_dict_to_schema(s) for s in paginated]

    return StockListResponse(
        count=total,
        stocks=stocks,
    )


@router.get(
    "/stocks/{symbol}",
    response_model=StockAnalysisSchema,
    responses={404: {"model": ErrorResponse}},
)
async def get_stock_detail(symbol: str) -> StockAnalysisSchema:
    """
    특정 종목의 상세 정보를 조회합니다.

    Args:
        symbol: 종목 코드 (예: 005930)

    Returns:
        StockAnalysisSchema
    """
    # 종목 코드 정규화 (6자리 맞추기)
    symbol = symbol.zfill(6)

    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    all_stocks = _get_all_stocks_from_ranking(data)

    # 종목 찾기
    for stock_dict in all_stocks:
        if stock_dict.get("symbol") == symbol:
            return _stock_dict_to_schema(stock_dict)

    raise HTTPException(
        status_code=404,
        detail=f"종목 '{symbol}'의 분석 결과가 없습니다. 해당 종목이 분석 대상에 포함되지 않았을 수 있습니다.",
    )


@router.get(
    "/stocks/top/{n}",
    response_model=List[StockAnalysisSchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_top_stocks(n: int = 5) -> List[StockAnalysisSchema]:
    """
    상위 N개 종목을 조회합니다.

    Args:
        n: 반환할 종목 수 (기본값: 5)

    Returns:
        StockAnalysisSchema 리스트
    """
    if n < 1 or n > 50:
        raise HTTPException(status_code=400, detail="n은 1~50 범위여야 합니다.")

    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    # final_top5 또는 final_18에서 상위 N개 추출
    ranking = data.get("ranking", {})

    if n <= 5:
        top_stocks = ranking.get("final_top5", [])[:n]
    else:
        top_stocks = ranking.get("final_18", [])[:n]

    if not top_stocks:
        raise HTTPException(status_code=404, detail="순위 데이터가 없습니다.")

    return [_stock_dict_to_schema(s) for s in top_stocks]


@router.get(
    "/stocks/group/{group}",
    response_model=List[StockAnalysisSchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_stocks_by_group(group: str) -> List[StockAnalysisSchema]:
    """
    특정 그룹의 종목 리스트를 조회합니다.

    Args:
        group: 그룹명 (kospi_top10, kospi_11_20, kosdaq_top10, sector_*)

    Returns:
        StockAnalysisSchema 리스트
    """
    valid_groups = ["kospi_top10", "kospi_11_20", "kosdaq_top10", "sector_top"]

    if group not in valid_groups and not group.startswith("sector_"):
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 그룹입니다. 사용 가능: {valid_groups}",
        )

    file_path = _get_latest_analysis_path()

    if file_path is None:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")

    try:
        data = _load_analysis_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 결과 로드 실패: {e}")

    ranking = data.get("ranking", {})

    # 그룹에 해당하는 종목 추출
    stocks = ranking.get(group, [])

    if not stocks:
        raise HTTPException(
            status_code=404,
            detail=f"그룹 '{group}'의 종목이 없습니다.",
        )

    return [_stock_dict_to_schema(s) for s in stocks]


# =============================================================================
# 차트 데이터 API
# =============================================================================


@router.get(
    "/stocks/{symbol}/history",
    response_model=StockHistoryResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_stock_history(
    symbol: str,
    days: int = Query(60, ge=1, le=365, description="조회할 일수 (기본값: 60, 최대: 365)"),
) -> StockHistoryResponse:
    """
    특정 종목의 일별 주가 히스토리를 조회합니다.

    Args:
        symbol: 종목 코드 (예: 005930)
        days: 조회할 일수 (기본값: 60)

    Returns:
        StockHistoryResponse
    """
    # 종목 코드 정규화
    symbol = symbol.zfill(6)

    fetcher = StockDataFetcher()

    # 종목명 조회
    name = fetcher.get_stock_name(symbol)
    if name == symbol:
        # 종목명 조회 실패 시 종목 코드 유효성 확인
        logger.warning(f"종목명 조회 실패: {symbol}")

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 30)  # 여유분 추가
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    # 주가 데이터 조회
    df = fetcher.fetch_stock_data(symbol, start_str, end_str)

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"종목 '{symbol}'의 주가 데이터를 찾을 수 없습니다.",
        )

    # 최근 N일만 선택
    df = df.tail(days)

    # 응답 데이터 구성
    history = [
        PriceHistoryItem(
            date=row.name.strftime("%Y-%m-%d"),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"]),
        )
        for _, row in df.iterrows()
    ]

    return StockHistoryResponse(
        symbol=symbol,
        name=name,
        history=history,
    )


@router.get(
    "/stocks/{symbol}/supply",
    response_model=StockSupplyResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_stock_supply(
    symbol: str,
    days: int = Query(20, ge=1, le=60, description="조회할 일수 (기본값: 20, 최대: 60)"),
) -> StockSupplyResponse:
    """
    특정 종목의 외국인/기관 순매수 추이를 조회합니다.

    Args:
        symbol: 종목 코드 (예: 005930)
        days: 조회할 일수 (기본값: 20)

    Returns:
        StockSupplyResponse
    """
    # 종목 코드 정규화
    symbol = symbol.zfill(6)

    fetcher = StockDataFetcher()

    # 종목명 조회
    name = fetcher.get_stock_name(symbol)
    if name == symbol:
        logger.warning(f"종목명 조회 실패: {symbol}")

    # 수급 데이터 조회 (네이버 금융에서 직접 크롤링)
    supply_data = _fetch_supply_data(symbol, days, fetcher)

    if not supply_data:
        raise HTTPException(
            status_code=404,
            detail=f"종목 '{symbol}'의 수급 데이터를 찾을 수 없습니다.",
        )

    return StockSupplyResponse(
        symbol=symbol,
        name=name,
        supply=supply_data,
    )


def _fetch_supply_data(symbol: str, days: int, fetcher: StockDataFetcher) -> List[SupplyItem]:
    """
    네이버 금융에서 외국인/기관 수급 데이터를 크롤링합니다.
    """
    result = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        # 페이지 수 계산 (한 페이지당 약 10개 행)
        pages_needed = (days // 10) + 2

        for page in range(1, pages_needed + 1):
            url = f"https://finance.naver.com/item/frgn.naver?code={symbol}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")

            # 외국인/기관 매매 테이블 파싱 (두 번째 type2 테이블)
            tables = soup.select("table.type2")
            table = tables[1] if len(tables) > 1 else tables[0] if tables else None
            if not table:
                break

            rows = table.select("tr")
            for row in rows:
                tds = row.select("td")
                if len(tds) >= 9:
                    try:
                        date_text = tds[0].text.strip()
                        if not date_text or "." not in date_text:
                            continue

                        # 날짜 파싱 (2025.01.24 -> 2025-01-24)
                        date_str = date_text.replace(".", "-")

                        # 종가
                        close_text = tds[1].text.strip().replace(",", "")
                        close = int(close_text) if close_text else 0

                        # 기관 순매매 (6번째 컬럼) - 주 단위
                        inst_text = tds[5].text.strip().replace(",", "").replace("+", "")
                        inst_value = int(inst_text) if inst_text and inst_text != "-" else 0

                        # 외국인 순매매 (7번째 컬럼) - 주 단위
                        foreign_text = tds[6].text.strip().replace(",", "").replace("+", "")
                        foreign_value = int(foreign_text) if foreign_text and foreign_text != "-" else 0

                        # 억원 단위로 변환 (주 * 종가 / 1억)
                        foreign_net = round(foreign_value * close / 100_000_000, 2) if close else 0
                        inst_net = round(inst_value * close / 100_000_000, 2) if close else 0

                        result.append(SupplyItem(
                            date=date_str,
                            foreign_net=foreign_net,
                            institution_net=inst_net,
                        ))

                        if len(result) >= days:
                            return result

                    except (ValueError, IndexError):
                        continue

            time.sleep(0.1)  # 요청 간격

    except Exception as e:
        logger.error(f"수급 데이터 조회 실패 for {symbol}: {e}")

    return result
