"""
Data Quality Validator 테스트

데이터 품질 검증 모듈에 대한 단위 테스트.
"""

import pytest
from src.agents.analysis.data_quality import (
    DataQualityValidator,
    DataQualityResult,
    DataQualitySummary,
    DataQualityError,
)
from src.agents.data.market_data_agent import MarketData
from src.agents.data.fundamental_agent import FundamentalData


class TestDataQualityResult:
    """DataQualityResult 테스트"""

    def test_init_defaults(self):
        """기본값 초기화 테스트"""
        result = DataQualityResult(symbol="005930")
        assert result.symbol == "005930"
        assert result.name == ""
        assert result.is_valid is True
        assert result.quality_score == 100.0
        assert result.missing_required == []
        assert result.missing_recommended == []
        assert result.warnings == []

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        result = DataQualityResult(
            symbol="005930",
            name="삼성전자",
            is_valid=True,
            quality_score=85.0,
            missing_required=[],
            missing_recommended=["펀더멘털"],
        )
        d = result.to_dict()
        assert d["symbol"] == "005930"
        assert d["name"] == "삼성전자"
        assert d["is_valid"] is True
        assert d["quality_score"] == 85.0
        assert d["missing_recommended"] == ["펀더멘털"]


class TestDataQualityValidator:
    """DataQualityValidator 테스트"""

    def setup_method(self):
        """테스트 셋업"""
        self.validator = DataQualityValidator()

    def test_validate_complete_data(self):
        """완전한 데이터 검증 테스트"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=4500000,
            ma20=74000,
            rsi=55.0,
            volume=10000000,
            low_52w=50000,
            high_52w=85000,
        )
        fundamental_data = FundamentalData(
            symbol="005930",
            name="삼성전자",
            per=12.5,
            pbr=1.2,
            roe=15.0,
        )
        result = self.validator.validate(market_data, fundamental_data)

        assert result.is_valid is True
        assert result.quality_score == 100.0
        assert result.missing_required == []
        assert result.missing_recommended == []

    def test_validate_missing_market_cap(self):
        """시가총액 누락 검증 테스트"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=0,  # 누락
            ma20=74000,
            rsi=55.0,
            volume=10000000,
            low_52w=50000,
            high_52w=85000,
        )
        result = self.validator.validate(market_data, None)

        assert result.is_valid is False
        assert "시가총액" in result.missing_required

    def test_validate_missing_technical_indicators(self):
        """기술적 지표 누락 검증 테스트"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=4500000,
            ma20=None,  # 누락
            rsi=None,  # 누락
            volume=10000000,
        )
        result = self.validator.validate(market_data, None)

        assert result.is_valid is False
        assert "기술적 지표 (MA20, RSI)" in result.missing_required

    def test_validate_partial_technical_indicators(self):
        """기술적 지표 일부만 있는 경우 (유효)"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=4500000,
            ma20=74000,  # 있음
            rsi=None,  # 누락
            volume=10000000,
            low_52w=50000,
            high_52w=85000,
        )
        fundamental_data = FundamentalData(
            symbol="005930",
            name="삼성전자",
            per=12.5,
        )
        result = self.validator.validate(market_data, fundamental_data)

        # MA20이 있으므로 기술적 지표는 유효
        assert result.is_valid is True
        assert "기술적 지표" not in str(result.missing_required)

    def test_validate_none_market_data(self):
        """market_data가 None인 경우"""
        result = self.validator.validate(None, None)

        assert result.is_valid is False
        assert result.quality_score == 0.0
        assert "market_data (전체 없음)" in result.missing_required

    def test_validate_missing_fundamental(self):
        """펀더멘털 누락 (권장 항목)"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=4500000,
            ma20=74000,
            rsi=55.0,
            volume=10000000,
            low_52w=50000,
            high_52w=85000,
        )
        result = self.validator.validate(market_data, None)

        # 필수 항목은 모두 있으므로 유효
        assert result.is_valid is True
        # 권장 항목 누락
        assert "펀더멘털 (PER/PBR/ROE)" in result.missing_recommended
        # 점수는 권장 항목 점수만큼 감소
        assert result.quality_score < 100.0

    def test_validate_missing_52w_range(self):
        """52주 고저 누락 (권장 항목)"""
        market_data = MarketData(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            current_price=75000,
            market_cap=4500000,
            ma20=74000,
            rsi=55.0,
            volume=10000000,
            low_52w=None,  # 누락
            high_52w=None,  # 누락
        )
        fundamental_data = FundamentalData(
            symbol="005930",
            name="삼성전자",
            per=12.5,
        )
        result = self.validator.validate(market_data, fundamental_data)

        assert result.is_valid is True
        assert "52주 고저" in result.missing_recommended

    def test_validate_batch(self):
        """배치 검증 테스트"""
        market_data_dict = {
            "005930": MarketData(
                symbol="005930",
                name="삼성전자",
                market="KOSPI",
                current_price=75000,
                market_cap=4500000,
                ma20=74000,
                rsi=55.0,
                volume=10000000,
            ),
            "000660": MarketData(
                symbol="000660",
                name="SK하이닉스",
                market="KOSPI",
                current_price=0,  # 무효
                market_cap=0,  # 무효
                ma20=None,
                rsi=None,
                volume=0,
            ),
        }
        fundamental_data_dict = {
            "005930": FundamentalData(symbol="005930", name="삼성전자", per=12.5),
        }
        results = self.validator.validate_batch(market_data_dict, fundamental_data_dict)

        assert "005930" in results
        assert "000660" in results
        assert results["005930"].is_valid is True
        assert results["000660"].is_valid is False

    def test_summarize(self):
        """품질 요약 테스트"""
        results = {
            "005930": DataQualityResult(
                symbol="005930",
                is_valid=True,
                quality_score=100.0,
            ),
            "000660": DataQualityResult(
                symbol="000660",
                is_valid=False,
                quality_score=20.0,
            ),
            "035420": DataQualityResult(
                symbol="035420",
                is_valid=True,
                quality_score=85.0,
            ),
        }
        summary = self.validator.summarize(results)

        assert summary.total_count == 3
        assert summary.valid_count == 2
        assert summary.invalid_count == 1
        assert summary.avg_quality_score == pytest.approx(68.3, rel=0.1)
        assert summary.invalid_symbols == ["000660"]

    def test_summarize_empty(self):
        """빈 결과 요약 테스트"""
        summary = self.validator.summarize({})

        assert summary.total_count == 0
        assert summary.valid_count == 0
        assert summary.invalid_count == 0
        assert summary.avg_quality_score == 0.0


class TestDataQualityError:
    """DataQualityError 테스트"""

    def test_error_with_summary(self):
        """예외에 요약 정보 포함 테스트"""
        summary = DataQualitySummary(
            total_count=10,
            valid_count=8,
            invalid_count=2,
            invalid_symbols=["000000", "111111"],
        )
        error = DataQualityError("품질 기준 미달", summary)

        assert str(error) == "품질 기준 미달"
        assert error.summary.invalid_count == 2
        assert error.summary.invalid_symbols == ["000000", "111111"]


class TestQualityScoreCalculation:
    """품질 점수 계산 테스트"""

    def setup_method(self):
        """테스트 셋업"""
        self.validator = DataQualityValidator()

    def test_required_weights(self):
        """필수 항목 가중치 합계 테스트"""
        total = sum(self.validator.REQUIRED_WEIGHTS.values())
        assert total == 60  # 필수 항목 총 60점

    def test_recommended_weights(self):
        """권장 항목 가중치 합계 테스트"""
        total = sum(self.validator.RECOMMENDED_WEIGHTS.values())
        assert total == 40  # 권장 항목 총 40점

    def test_total_weights(self):
        """전체 가중치 합계 테스트 (100점 만점)"""
        required_total = sum(self.validator.REQUIRED_WEIGHTS.values())
        recommended_total = sum(self.validator.RECOMMENDED_WEIGHTS.values())
        assert required_total + recommended_total == 100
