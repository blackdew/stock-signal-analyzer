"""
Pydantic Schemas

API 요청/응답용 Pydantic 스키마 정의.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# 공통 스키마
# =============================================================================


class HealthResponse(BaseModel):
    """서버 상태 응답"""
    status: str = Field(description="서버 상태", examples=["ok"])
    version: str = Field(description="API 버전", examples=["1.0.0"])


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(description="에러 타입")
    message: str = Field(description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="추가 정보")


# =============================================================================
# 데이터 품질 스키마
# =============================================================================


class DataQualitySchema(BaseModel):
    """데이터 품질 결과"""
    symbol: str
    is_valid: bool
    quality_score: float
    missing_required: List[str] = []
    missing_recommended: List[str] = []


class DataQualitySummarySchema(BaseModel):
    """데이터 품질 요약"""
    total_count: int
    valid_count: int
    invalid_count: int
    avg_quality_score: float
    invalid_symbols: List[str] = []


# =============================================================================
# 종목 분석 스키마
# =============================================================================


class StockAnalysisSchema(BaseModel):
    """개별 종목 분석 결과"""
    symbol: str = Field(description="종목 코드", examples=["005930"])
    name: str = Field(description="종목명", examples=["삼성전자"])
    sector: str = Field(description="섹터명", examples=["반도체"])
    group: str = Field(description="그룹명", examples=["kospi_top10"])
    market_cap: float = Field(description="시가총액 (억원)")

    technical_score: float = Field(description="기술적 분석 점수")
    supply_score: float = Field(description="수급 분석 점수")
    fundamental_score: float = Field(description="펀더멘털 분석 점수")
    market_score: float = Field(description="시장 환경 점수")
    risk_score: float = Field(default=0.0, description="리스크 점수 (V2)")
    relative_strength_score: float = Field(default=0.0, description="상대 강도 점수 (V2)")

    total_score: float = Field(description="총점 (100점 만점)")
    investment_grade: str = Field(description="투자 등급", examples=["Buy"])

    rank_in_group: int = Field(description="그룹 내 순위")
    final_rank: Optional[int] = Field(default=None, description="최종 순위")

    data_quality: Optional[DataQualitySchema] = Field(default=None, description="데이터 품질")


class StockListResponse(BaseModel):
    """종목 리스트 응답"""
    count: int
    stocks: List[StockAnalysisSchema]


# =============================================================================
# 섹터 분석 스키마
# =============================================================================


class SectorAnalysisSchema(BaseModel):
    """섹터 분석 결과"""
    sector_name: str = Field(description="섹터명", examples=["반도체"])
    stock_count: int = Field(description="섹터 내 종목 수")
    total_market_cap: float = Field(description="총 시가총액 (억원)")

    weighted_score: float = Field(description="시가총액 가중 평균 점수")
    simple_score: float = Field(description="단순 평균 점수")

    technical_score: float = Field(description="기술적 분석 점수 (가중 평균)")
    supply_score: float = Field(description="수급 분석 점수 (가중 평균)")
    fundamental_score: float = Field(description="펀더멘털 분석 점수 (가중 평균)")
    market_score: float = Field(description="시장 환경 점수 (가중 평균)")

    top_stocks: List[StockAnalysisSchema] = Field(default=[], description="상위 종목")
    rank: int = Field(description="섹터 순위")


class SectorListResponse(BaseModel):
    """섹터 리스트 응답"""
    count: int
    sectors: List[SectorAnalysisSchema]


# =============================================================================
# 순위 스키마
# =============================================================================


class RankingSchema(BaseModel):
    """순위 결과"""
    kospi_top10: List[StockAnalysisSchema] = Field(description="KOSPI Top 10 상위 종목")
    kospi_11_20: List[StockAnalysisSchema] = Field(description="KOSPI 11-20 상위 종목")
    kosdaq_top10: List[StockAnalysisSchema] = Field(description="KOSDAQ Top 10 상위 종목")
    sector_top: List[StockAnalysisSchema] = Field(description="섹터별 상위 종목")

    final_18: List[StockAnalysisSchema] = Field(description="최종 18개 종목")
    final_top5: List[StockAnalysisSchema] = Field(description="최종 Top 5")

    top_sectors: List[SectorAnalysisSchema] = Field(description="상위 3개 섹터")


# =============================================================================
# 분석 요청/응답 스키마
# =============================================================================


class AnalysisRunRequest(BaseModel):
    """분석 실행 요청"""
    mode: str = Field(default="daily", description="실행 모드", examples=["daily", "weekly"])
    sector_only: bool = Field(default=False, description="섹터 분석만 실행")
    use_cache: bool = Field(default=True, description="캐시 사용 여부")
    skip_news: bool = Field(default=False, description="뉴스 분석 스킵")


class AnalysisTaskResponse(BaseModel):
    """분석 태스크 응답"""
    task_id: str = Field(description="태스크 ID")
    status: str = Field(description="태스크 상태", examples=["running", "completed", "failed"])
    message: Optional[str] = Field(default=None, description="추가 메시지")


class AnalysisStatsSchema(BaseModel):
    """분석 통계"""
    total_time: float = Field(description="총 소요 시간 (초)")
    phases: Dict[str, Any] = Field(default={}, description="단계별 통계")
    final_stocks: Optional[int] = Field(default=None, description="최종 선정 종목 수")
    final_top5: Optional[List[Dict[str, Any]]] = Field(default=None, description="Top 5 요약")


class AnalysisResultSchema(BaseModel):
    """분석 결과"""
    generated_at: datetime = Field(description="생성 시각")
    ranking: Optional[RankingSchema] = Field(default=None, description="순위 결과")
    sectors: Optional[List[SectorAnalysisSchema]] = Field(default=None, description="섹터 결과")
    report_paths: Dict[str, Any] = Field(default={}, description="리포트 파일 경로")
    stats: AnalysisStatsSchema = Field(description="실행 통계")
    data_quality: Optional[DataQualitySummarySchema] = Field(default=None, description="데이터 품질 요약")
