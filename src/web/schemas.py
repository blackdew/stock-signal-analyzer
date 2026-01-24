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


class TechnicalDetailsSchema(BaseModel):
    """기술적 분석 세부 정보"""
    trend: Optional[float] = Field(default=None, description="추세 점수")
    rsi: Optional[float] = Field(default=None, description="RSI 점수")
    support_resistance: Optional[float] = Field(default=None, description="지지/저항 점수")
    macd: Optional[float] = Field(default=None, description="MACD 점수")
    adx: Optional[float] = Field(default=None, description="ADX 점수")
    # 원본 값
    ma20_value: Optional[float] = Field(default=None, description="20일 이동평균")
    ma60_value: Optional[float] = Field(default=None, description="60일 이동평균")
    rsi_value: Optional[float] = Field(default=None, description="RSI 값")
    macd_value: Optional[float] = Field(default=None, description="MACD 값")
    macd_signal_value: Optional[float] = Field(default=None, description="MACD 시그널 값")
    adx_value: Optional[float] = Field(default=None, description="ADX 값")
    current_price: Optional[float] = Field(default=None, description="현재가")
    low_52w: Optional[float] = Field(default=None, description="52주 최저가")
    high_52w: Optional[float] = Field(default=None, description="52주 최고가")
    position_52w: Optional[float] = Field(default=None, description="52주 내 위치 (%)")


class SupplyDetailsSchema(BaseModel):
    """수급 분석 세부 정보"""
    foreign: Optional[float] = Field(default=None, description="외국인 점수")
    institution: Optional[float] = Field(default=None, description="기관 점수")
    trading_value: Optional[float] = Field(default=None, description="거래대금 점수")
    # 원본 값
    foreign_consecutive_days: Optional[int] = Field(default=None, description="외국인 연속 순매수 일수")
    institution_consecutive_days: Optional[int] = Field(default=None, description="기관 연속 순매수 일수")
    trading_value_amount: Optional[float] = Field(default=None, description="거래대금 (억원)")


class FundamentalDetailsSchema(BaseModel):
    """펀더멘털 분석 세부 정보"""
    per: Optional[float] = Field(default=None, description="PER 점수")
    pbr: Optional[float] = Field(default=None, description="PBR 점수")
    roe: Optional[float] = Field(default=None, description="ROE 점수")
    growth: Optional[float] = Field(default=None, description="성장성 점수")
    debt: Optional[float] = Field(default=None, description="부채 점수")
    # 원본 값
    per_value: Optional[float] = Field(default=None, description="PER 값")
    pbr_value: Optional[float] = Field(default=None, description="PBR 값")
    roe_value: Optional[float] = Field(default=None, description="ROE 값 (%)")
    sector_avg_per: Optional[float] = Field(default=None, description="업종 평균 PER")
    sector_avg_pbr: Optional[float] = Field(default=None, description="업종 평균 PBR")
    op_growth_value: Optional[float] = Field(default=None, description="영업이익 성장률 (%)")
    debt_ratio_value: Optional[float] = Field(default=None, description="부채비율 (%)")


class MarketDetailsSchema(BaseModel):
    """시장 환경 세부 정보"""
    news: Optional[float] = Field(default=None, description="뉴스 점수")
    sector_momentum: Optional[float] = Field(default=None, description="섹터 모멘텀 점수")
    analyst: Optional[float] = Field(default=None, description="애널리스트 점수")


class RiskDetailsSchema(BaseModel):
    """리스크 평가 세부 정보"""
    volatility: Optional[float] = Field(default=None, description="변동성 점수")
    beta: Optional[float] = Field(default=None, description="베타 점수")
    downside_risk: Optional[float] = Field(default=None, description="하방 리스크 점수")
    # 원본 값
    atr_pct_value: Optional[float] = Field(default=None, description="ATR 퍼센트")
    beta_value: Optional[float] = Field(default=None, description="베타 값")
    max_drawdown_value: Optional[float] = Field(default=None, description="최대 낙폭 (%)")


class RelativeStrengthDetailsSchema(BaseModel):
    """상대 강도 세부 정보"""
    sector_rank: Optional[float] = Field(default=None, description="섹터 내 순위 점수")
    alpha: Optional[float] = Field(default=None, description="알파 점수")
    # 원본 값
    sector_rank_value: Optional[int] = Field(default=None, description="섹터 내 순위")
    sector_total_value: Optional[int] = Field(default=None, description="섹터 내 전체 종목 수")
    stock_return_value: Optional[float] = Field(default=None, description="종목 20일 수익률 (%)")
    market_return_value: Optional[float] = Field(default=None, description="시장 20일 수익률 (%)")
    alpha_value: Optional[float] = Field(default=None, description="알파 값 (%)")


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

    # 52주 고저가
    high_52w: Optional[float] = Field(default=None, description="52주 최고가")
    low_52w: Optional[float] = Field(default=None, description="52주 최저가")

    rank_in_group: int = Field(description="그룹 내 순위")
    final_rank: Optional[int] = Field(default=None, description="최종 순위")

    data_quality: Optional[DataQualitySchema] = Field(default=None, description="데이터 품질")

    # 세부 분석 정보
    technical_details: Optional[TechnicalDetailsSchema] = Field(default=None, description="기술적 분석 세부")
    supply_details: Optional[SupplyDetailsSchema] = Field(default=None, description="수급 분석 세부")
    fundamental_details: Optional[FundamentalDetailsSchema] = Field(default=None, description="펀더멘털 분석 세부")
    market_details: Optional[MarketDetailsSchema] = Field(default=None, description="시장 환경 세부")
    risk_details: Optional[RiskDetailsSchema] = Field(default=None, description="리스크 평가 세부")
    relative_strength_details: Optional[RelativeStrengthDetailsSchema] = Field(default=None, description="상대 강도 세부")

    # LLM 상세 분석 (Phase 1: 리포트 품질 개선)
    summary: Optional[str] = Field(default=None, description="핵심 요약 (1-2문장)", examples=["AI 메모리 반도체(HBM) 시장의 절대적 지배력을 바탕으로 사상 최대 실적 경신이 기대되는 대장주"])
    financial_analysis: Optional[str] = Field(default=None, description="재무 & 밸류에이션 분석 (마크다운)")
    technical_analysis: Optional[str] = Field(default=None, description="기술적 & 차트 분석 (마크다운)")
    market_sentiment: Optional[str] = Field(default=None, description="뉴스 & 시장 센티먼트 분석 (마크다운)")
    comprehensive_analysis: Optional[str] = Field(default=None, description="종합 투자 의견 (마크다운)")
    investment_thesis: Optional[List[str]] = Field(default=None, description="투자 포인트 (3-5개)", examples=[["HBM 시장 지배력", "AI 수혜 기대"]])
    risks: Optional[List[str]] = Field(default=None, description="주요 리스크 요인 (2-4개)", examples=[["글로벌 경기 침체", "반도체 수요 둔화"]])


class StockListResponse(BaseModel):
    """종목 리스트 응답"""
    count: int
    stocks: List[StockAnalysisSchema]


# =============================================================================
# 차트 데이터 스키마
# =============================================================================


class PriceHistoryItem(BaseModel):
    """일별 주가 데이터"""
    date: str = Field(description="날짜 (YYYY-MM-DD)", examples=["2025-01-24"])
    open: float = Field(description="시가")
    high: float = Field(description="고가")
    low: float = Field(description="저가")
    close: float = Field(description="종가")
    volume: int = Field(description="거래량")


class StockHistoryResponse(BaseModel):
    """주가 히스토리 응답"""
    symbol: str = Field(description="종목 코드", examples=["005930"])
    name: str = Field(description="종목명", examples=["삼성전자"])
    history: List[PriceHistoryItem] = Field(description="일별 주가 데이터")


class SupplyItem(BaseModel):
    """일별 수급 데이터"""
    date: str = Field(description="날짜 (YYYY-MM-DD)", examples=["2025-01-24"])
    foreign_net: float = Field(description="외국인 순매수 (억원)")
    institution_net: float = Field(description="기관 순매수 (억원)")


class StockSupplyResponse(BaseModel):
    """수급 데이터 응답"""
    symbol: str = Field(description="종목 코드", examples=["005930"])
    name: str = Field(description="종목명", examples=["삼성전자"])
    supply: List[SupplyItem] = Field(description="일별 수급 데이터")


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
