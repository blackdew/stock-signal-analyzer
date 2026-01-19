"""
Data Quality Validator

데이터 품질 검증 모듈.
주식 분석에 필요한 필수/권장 데이터의 유효성을 검증합니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.data.market_data_agent import MarketData
from src.agents.data.fundamental_agent import FundamentalData


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class DataQualityResult:
    """
    데이터 품질 검증 결과

    Attributes:
        symbol: 종목 코드
        name: 종목명
        is_valid: 필수 항목 모두 충족 여부
        quality_score: 품질 점수 (0-100)
        missing_required: 누락된 필수 항목 리스트
        missing_recommended: 누락된 권장 항목 리스트
        warnings: 경고 메시지 리스트
    """
    symbol: str
    name: str = ""
    is_valid: bool = True
    quality_score: float = 100.0
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "is_valid": self.is_valid,
            "quality_score": self.quality_score,
            "missing_required": self.missing_required,
            "missing_recommended": self.missing_recommended,
            "warnings": self.warnings,
        }


@dataclass
class DataQualitySummary:
    """
    전체 데이터 품질 요약

    Attributes:
        total_count: 전체 종목 수
        valid_count: 유효 종목 수
        invalid_count: 무효 종목 수
        avg_quality_score: 평균 품질 점수
        invalid_symbols: 무효 종목 코드 리스트
        results: 종목별 품질 검증 결과
    """
    total_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    avg_quality_score: float = 0.0
    invalid_symbols: List[str] = field(default_factory=list)
    results: Dict[str, DataQualityResult] = field(default_factory=dict)


# =============================================================================
# DataQualityValidator
# =============================================================================


class DataQualityValidator:
    """
    데이터 품질 검증기

    필수 항목:
    - 현재가 (current_price > 0)
    - 시가총액 (market_cap > 0)
    - 기술적 지표 (MA20, RSI 중 1개 이상)
    - 거래량 (volume > 0)

    권장 항목:
    - 펀더멘털 (PER, PBR, ROE 중 1개 이상)
    - 52주 고저 (low_52w, high_52w 둘 다 존재)

    사용 예시:
        validator = DataQualityValidator()
        result = validator.validate(market_data, fundamental_data)
        summary = validator.summarize(results)
    """

    # 필수 항목별 점수 가중치 (총 60점)
    REQUIRED_WEIGHTS = {
        "current_price": 20,
        "market_cap": 15,
        "technical_indicators": 15,  # MA20, RSI 중 1개
        "volume": 10,
    }

    # 권장 항목별 점수 가중치 (총 40점)
    RECOMMENDED_WEIGHTS = {
        "fundamentals": 25,  # PER, PBR, ROE 중 1개
        "price_range_52w": 15,  # 52주 고저
    }

    def validate(
        self,
        market_data: Optional[MarketData],
        fundamental_data: Optional[FundamentalData],
    ) -> DataQualityResult:
        """
        단일 종목의 데이터 품질을 검증합니다.

        Args:
            market_data: 시장 데이터
            fundamental_data: 재무제표 데이터

        Returns:
            DataQualityResult
        """
        if market_data is None:
            return DataQualityResult(
                symbol="unknown",
                is_valid=False,
                quality_score=0.0,
                missing_required=["market_data (전체 없음)"],
                warnings=["시장 데이터를 수집할 수 없습니다"],
            )

        symbol = market_data.symbol
        name = market_data.name
        missing_required: List[str] = []
        missing_recommended: List[str] = []
        warnings: List[str] = []
        quality_score = 0.0

        # === 필수 항목 검증 ===

        # 1. 현재가 검증
        if market_data.current_price and market_data.current_price > 0:
            quality_score += self.REQUIRED_WEIGHTS["current_price"]
        else:
            missing_required.append("현재가")
            warnings.append(f"현재가가 유효하지 않습니다: {market_data.current_price}")

        # 2. 시가총액 검증
        if market_data.market_cap and market_data.market_cap > 0:
            quality_score += self.REQUIRED_WEIGHTS["market_cap"]
        else:
            missing_required.append("시가총액")

        # 3. 기술적 지표 검증 (MA20, RSI 중 1개 이상)
        has_technical = (
            (market_data.ma20 is not None) or
            (market_data.rsi is not None)
        )
        if has_technical:
            quality_score += self.REQUIRED_WEIGHTS["technical_indicators"]
        else:
            missing_required.append("기술적 지표 (MA20, RSI)")
            warnings.append("기술적 지표를 계산할 수 없습니다")

        # 4. 거래량 검증
        if market_data.volume and market_data.volume > 0:
            quality_score += self.REQUIRED_WEIGHTS["volume"]
        else:
            missing_required.append("거래량")

        # === 권장 항목 검증 ===

        # 5. 펀더멘털 검증 (PER, PBR, ROE 중 1개 이상)
        has_fundamental = False
        if fundamental_data:
            has_fundamental = (
                (fundamental_data.per is not None) or
                (fundamental_data.pbr is not None) or
                (fundamental_data.roe is not None)
            )

        if has_fundamental:
            quality_score += self.RECOMMENDED_WEIGHTS["fundamentals"]
        else:
            missing_recommended.append("펀더멘털 (PER/PBR/ROE)")

        # 6. 52주 고저 검증
        has_52w_range = (
            market_data.low_52w is not None and
            market_data.high_52w is not None
        )
        if has_52w_range:
            quality_score += self.RECOMMENDED_WEIGHTS["price_range_52w"]
        else:
            missing_recommended.append("52주 고저")

        # 필수 항목 모두 충족 여부
        is_valid = len(missing_required) == 0

        return DataQualityResult(
            symbol=symbol,
            name=name,
            is_valid=is_valid,
            quality_score=quality_score,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            warnings=warnings,
        )

    def validate_batch(
        self,
        market_data_dict: Dict[str, MarketData],
        fundamental_data_dict: Dict[str, FundamentalData],
    ) -> Dict[str, DataQualityResult]:
        """
        여러 종목의 데이터 품질을 검증합니다.

        Args:
            market_data_dict: 종목코드를 키로 하는 MarketData 딕셔너리
            fundamental_data_dict: 종목코드를 키로 하는 FundamentalData 딕셔너리

        Returns:
            종목코드를 키로 하는 DataQualityResult 딕셔너리
        """
        results: Dict[str, DataQualityResult] = {}

        for symbol, market_data in market_data_dict.items():
            fundamental_data = fundamental_data_dict.get(symbol)
            results[symbol] = self.validate(market_data, fundamental_data)

        return results

    def summarize(
        self,
        results: Dict[str, DataQualityResult]
    ) -> DataQualitySummary:
        """
        품질 검증 결과를 요약합니다.

        Args:
            results: 종목코드를 키로 하는 DataQualityResult 딕셔너리

        Returns:
            DataQualitySummary
        """
        total_count = len(results)
        if total_count == 0:
            return DataQualitySummary()

        valid_count = sum(1 for r in results.values() if r.is_valid)
        invalid_count = total_count - valid_count
        avg_quality_score = sum(r.quality_score for r in results.values()) / total_count
        invalid_symbols = [r.symbol for r in results.values() if not r.is_valid]

        return DataQualitySummary(
            total_count=total_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            avg_quality_score=round(avg_quality_score, 1),
            invalid_symbols=invalid_symbols,
            results=results,
        )


class DataQualityError(Exception):
    """데이터 품질 오류 예외"""

    def __init__(self, message: str, summary: DataQualitySummary):
        super().__init__(message)
        self.summary = summary
