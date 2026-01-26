"""
LLM Scorer Module

LLM을 활용하여 종목 점수와 분석을 생성하는 모듈.
기존 RubricEngine을 대체하여 더 유연하고 맥락을 고려한 분석을 제공합니다.
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.core.prompts.stock_analysis import build_stock_analysis_prompt
from src.core.prompts.sector_analysis import build_sector_analysis_prompt
from src.core.prompts.schemas import validate_stock_score, validate_sector_score
from src.core.config import get_grade_from_score
from src.core.llm import SECTOR_CONTEXTS
from src.data.cache import CacheManager

if TYPE_CHECKING:
    from src.agents.data.data_bundle import StockDataBundle


logger = logging.getLogger(__name__)


# =============================================================================
# 상수 정의
# =============================================================================

LLM_SCORE_CACHE_TTL = 24  # LLM 점수 캐시: 24시간
DEFAULT_MODEL = "gpt-5.2"
MAX_TOKENS = 8000
TEMPERATURE = 0.3  # 점수 일관성을 위해 낮은 temperature


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class CategoryScore:
    """카테고리별 점수와 판단 근거"""
    name: str
    score: float
    max_score: float
    reasoning: str = ""

    @property
    def weighted_score(self) -> float:
        """가중치 적용 점수 (점수 자체가 가중치 적용된 값)"""
        return self.score


@dataclass
class LLMScoreResult:
    """
    LLM이 생성한 점수+분석 결과

    Attributes:
        symbol: 종목 코드
        name: 종목명

        # 점수 (기존 스키마 호환)
        technical_score: 기술적 분석 점수 (0-25)
        supply_score: 수급 분석 점수 (0-20)
        fundamental_score: 펀더멘털 분석 점수 (0-20)
        market_score: 시장 환경 점수 (0-15)
        risk_score: 리스크 평가 점수 (0-10)
        relative_strength_score: 상대 강도 점수 (0-10)
        total_score: 총점 (0-100)
        grade: 투자 등급

        # 분석 텍스트
        summary: 핵심 요약
        financial_analysis: 재무 분석
        technical_analysis: 기술적 분석
        market_sentiment: 시장 센티먼트
        comprehensive_analysis: 종합 분석
        investment_thesis: 투자 포인트
        risks: 리스크 요인

        # 판단 근거
        category_reasoning: 카테고리별 판단 근거
    """
    symbol: str
    name: str

    # 점수
    technical_score: float = 0.0
    supply_score: float = 0.0
    fundamental_score: float = 0.0
    market_score: float = 0.0
    risk_score: float = 0.0
    relative_strength_score: float = 0.0
    total_score: float = 0.0
    grade: str = "Hold"

    # 분석 텍스트
    summary: str = ""
    financial_analysis: str = ""
    technical_analysis: str = ""
    market_sentiment: str = ""
    comprehensive_analysis: str = ""
    investment_thesis: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    # 판단 근거
    category_reasoning: Dict[str, str] = field(default_factory=dict)

    # LLM 실패로 인한 기본값 여부
    is_fallback: bool = False
    fallback_reason: str = ""

    def to_category_scores(self) -> Dict[str, CategoryScore]:
        """CategoryScore 딕셔너리로 변환 (기존 RubricResult 호환)"""
        return {
            "technical": CategoryScore(
                name="technical",
                score=self.technical_score,
                max_score=25,
                reasoning=self.category_reasoning.get("technical", "")
            ),
            "supply": CategoryScore(
                name="supply",
                score=self.supply_score,
                max_score=20,
                reasoning=self.category_reasoning.get("supply", "")
            ),
            "fundamental": CategoryScore(
                name="fundamental",
                score=self.fundamental_score,
                max_score=20,
                reasoning=self.category_reasoning.get("fundamental", "")
            ),
            "market": CategoryScore(
                name="market",
                score=self.market_score,
                max_score=15,
                reasoning=self.category_reasoning.get("market", "")
            ),
            "risk": CategoryScore(
                name="risk",
                score=self.risk_score,
                max_score=10,
                reasoning=self.category_reasoning.get("risk", "")
            ),
            "relative_strength": CategoryScore(
                name="relative_strength",
                score=self.relative_strength_score,
                max_score=10,
                reasoning=self.category_reasoning.get("relative_strength", "")
            ),
        }


@dataclass
class SectorLLMResult:
    """
    LLM이 생성한 섹터 분석 결과

    Attributes:
        sector_name: 섹터명
        reasoning: 섹터 분석 요약
        outlook: 향후 전망
        key_drivers: 핵심 모멘텀
        investment_strategy: 투자 전략
    """
    sector_name: str
    reasoning: str = ""
    outlook: str = ""
    key_drivers: List[str] = field(default_factory=list)
    investment_strategy: str = ""


# =============================================================================
# LLMScorer
# =============================================================================


class LLMScorer:
    """
    LLM 기반 점수 산출기

    기존 RubricEngine을 대체하여 LLM이 직접 점수와 분석을 생성합니다.

    사용 예시:
        scorer = LLMScorer()
        result = await scorer.analyze_stock(data_bundle)
        sector_result = await scorer.analyze_sector(stock_results, sector_info)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        LLMScorer 초기화

        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 로드)
            model: 사용할 모델명
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.cache = CacheManager()
        self._client = None

    @property
    def client(self):
        """OpenAI 클라이언트 (지연 초기화)"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key is not configured")
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is not installed. Run: pip install openai")
        return self._client

    def is_available(self) -> bool:
        """LLM 서비스 사용 가능 여부"""
        return bool(self.api_key)

    async def analyze_stock(self, data: StockDataBundle) -> LLMScoreResult:
        """
        개별 종목을 분석합니다.

        Args:
            data: StockDataBundle 인스턴스

        Returns:
            LLMScoreResult 인스턴스
        """
        if not self.is_available():
            logger.warning("LLM API key not configured, returning default scores")
            return self._create_default_result(data.symbol, data.name, "API 키 미설정")

        # 캐시 확인
        cache_key = self._generate_cache_key(data)
        cached = self.cache.get(cache_key, max_age_hours=LLM_SCORE_CACHE_TTL)
        if cached:
            logger.debug(f"LLM score cache hit for {data.symbol}")
            return self._dict_to_result(cached)

        try:
            # 프롬프트 생성
            prompt = build_stock_analysis_prompt(data.to_prompt_context())

            # LLM 호출
            response_text = self._call_llm(prompt)

            # JSON 파싱
            result = self._parse_stock_response(response_text, data.symbol, data.name)

            # 캐시 저장
            self.cache.set(cache_key, self._result_to_dict(result), ttl_hours=LLM_SCORE_CACHE_TTL)

            return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                reason = "API 할당량 초과 (크레딧 부족)"
            elif "401" in error_msg or "authentication" in error_msg.lower():
                reason = "API 인증 실패"
            elif "timeout" in error_msg.lower():
                reason = "API 요청 타임아웃"
            else:
                reason = f"API 오류: {error_msg[:100]}"
            logger.error(f"LLM stock analysis failed for {data.symbol}: {e}")
            return self._create_default_result(data.symbol, data.name, reason)

    async def analyze_sector(
        self,
        sector_name: str,
        weighted_score: float,
        simple_score: float,
        technical_score: float,
        supply_score: float,
        fundamental_score: float,
        market_score: float,
        stock_count: int,
        total_market_cap: float,
        top_stocks: List[Dict[str, Any]],
        supply_data: Optional[Dict[str, Any]] = None,
    ) -> SectorLLMResult:
        """
        섹터를 분석합니다.

        Args:
            sector_name: 섹터명
            weighted_score: 시가총액 가중 평균 점수
            simple_score: 단순 평균 점수
            technical_score: 기술적 분석 점수
            supply_score: 수급 분석 점수
            fundamental_score: 펀더멘털 점수
            market_score: 시장 환경 점수
            stock_count: 분석 종목 수
            total_market_cap: 총 시가총액
            top_stocks: 상위 종목 리스트
            supply_data: 섹터 수급 집계 데이터

        Returns:
            SectorLLMResult 인스턴스
        """
        if not self.is_available():
            logger.warning("LLM API key not configured, returning default sector result")
            return self._create_default_sector_result(sector_name)

        # 캐시 키 생성
        cache_key = f"llm_sector_{sector_name}_{weighted_score:.0f}"
        cached = self.cache.get(cache_key, max_age_hours=LLM_SCORE_CACHE_TTL)
        if cached:
            logger.debug(f"LLM sector cache hit for {sector_name}")
            return self._dict_to_sector_result(cached)

        try:
            # 섹터 컨텍스트
            sector_context = SECTOR_CONTEXTS.get(sector_name, f"{sector_name} 관련 산업")

            # 프롬프트 생성
            prompt = build_sector_analysis_prompt(
                sector_name=sector_name,
                sector_context=sector_context,
                stock_count=stock_count,
                total_market_cap=total_market_cap,
                weighted_score=weighted_score,
                simple_score=simple_score,
                technical_score=technical_score,
                supply_score=supply_score,
                fundamental_score=fundamental_score,
                market_score=market_score,
                top_stocks=top_stocks,
                supply_data=supply_data or {},
            )

            # LLM 호출
            response_text = self._call_llm(prompt)

            # JSON 파싱
            result = self._parse_sector_response(response_text, sector_name)

            # 캐시 저장
            self.cache.set(cache_key, self._sector_result_to_dict(result), ttl_hours=LLM_SCORE_CACHE_TTL)

            return result

        except Exception as e:
            logger.error(f"LLM sector analysis failed for {sector_name}: {e}")
            return self._create_default_sector_result(sector_name)

    def _call_llm(self, prompt: str) -> str:
        """LLM API 호출"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Korean stock market analyst. Always respond with valid JSON only. No additional text or explanation."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    def _parse_stock_response(self, response_text: str, symbol: str, name: str) -> LLMScoreResult:
        """LLM 응답을 파싱하여 LLMScoreResult로 변환"""
        try:
            data = json.loads(response_text)

            # 검증
            if not validate_stock_score(data):
                logger.warning(f"Invalid LLM response for {symbol}, using defaults")
                return self._create_default_result(symbol, name)

            categories = data.get("categories", {})

            return LLMScoreResult(
                symbol=symbol,
                name=name,
                technical_score=categories.get("technical", {}).get("score", 0),
                supply_score=categories.get("supply", {}).get("score", 0),
                fundamental_score=categories.get("fundamental", {}).get("score", 0),
                market_score=categories.get("market", {}).get("score", 0),
                risk_score=categories.get("risk", {}).get("score", 0),
                relative_strength_score=categories.get("relative_strength", {}).get("score", 0),
                total_score=data.get("total_score", 50),
                grade=data.get("grade", "Hold"),
                summary=data.get("summary", ""),
                financial_analysis=data.get("financial_analysis", ""),
                technical_analysis=data.get("technical_analysis", ""),
                market_sentiment=data.get("market_sentiment", ""),
                comprehensive_analysis=data.get("comprehensive_analysis", ""),
                investment_thesis=data.get("investment_thesis", []),
                risks=data.get("risks", []),
                category_reasoning={
                    "technical": categories.get("technical", {}).get("reasoning", ""),
                    "supply": categories.get("supply", {}).get("reasoning", ""),
                    "fundamental": categories.get("fundamental", {}).get("reasoning", ""),
                    "market": categories.get("market", {}).get("reasoning", ""),
                    "risk": categories.get("risk", {}).get("reasoning", ""),
                    "relative_strength": categories.get("relative_strength", {}).get("reasoning", ""),
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {symbol}: {e}")
            return self._create_default_result(symbol, name)

    def _parse_sector_response(self, response_text: str, sector_name: str) -> SectorLLMResult:
        """LLM 응답을 파싱하여 SectorLLMResult로 변환"""
        try:
            data = json.loads(response_text)

            # 검증
            if not validate_sector_score(data):
                logger.warning(f"Invalid LLM sector response for {sector_name}, using defaults")
                return self._create_default_sector_result(sector_name)

            return SectorLLMResult(
                sector_name=sector_name,
                reasoning=data.get("reasoning", ""),
                outlook=data.get("outlook", ""),
                key_drivers=data.get("key_drivers", []),
                investment_strategy=data.get("investment_strategy", ""),
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for sector {sector_name}: {e}")
            return self._create_default_sector_result(sector_name)

    def _create_default_result(self, symbol: str, name: str, reason: str = "LLM 분석 실패") -> LLMScoreResult:
        """기본 결과 생성 (LLM 실패 시)"""
        return LLMScoreResult(
            symbol=symbol,
            name=name,
            technical_score=12.5,
            supply_score=10.0,
            fundamental_score=10.0,
            market_score=7.5,
            risk_score=5.0,
            relative_strength_score=5.0,
            total_score=50.0,
            grade="Hold",
            summary="분석 데이터가 제한적입니다.",
            financial_analysis="재무 분석이 필요합니다.",
            technical_analysis="기술적 분석이 필요합니다.",
            market_sentiment="시장 센티먼트 분석이 필요합니다.",
            comprehensive_analysis="종합적인 분석이 필요합니다.",
            investment_thesis=["추가 분석 필요"],
            risks=["데이터 부족으로 인한 분석 한계"],
            is_fallback=True,
            fallback_reason=reason,
        )

    def _create_default_sector_result(self, sector_name: str) -> SectorLLMResult:
        """기본 섹터 결과 생성 (LLM 실패 시)"""
        return SectorLLMResult(
            sector_name=sector_name,
            reasoning="섹터 분석이 필요합니다.",
            outlook="추가 분석이 필요합니다.",
            key_drivers=["추가 분석 필요"],
            investment_strategy="중립적 관망 권고",
        )

    def _generate_cache_key(self, data: StockDataBundle) -> str:
        """데이터 해시 기반 캐시 키 생성"""
        # 주요 데이터를 해시
        hash_data = json.dumps({
            "symbol": data.symbol,
            "price": data.price_data.get("current_price"),
            "technical": data.technical_indicators.get("rsi"),
            "supply_foreign": data.supply_data.get("foreign_total_5d"),
            "fundamental_per": data.fundamental_data.get("per"),
        }, sort_keys=True)
        data_hash = hashlib.md5(hash_data.encode()).hexdigest()[:8]
        return f"llm_score_{data.symbol}_{data_hash}"

    def _result_to_dict(self, result: LLMScoreResult) -> dict:
        """결과를 딕셔너리로 변환"""
        return {
            "symbol": result.symbol,
            "name": result.name,
            "technical_score": result.technical_score,
            "supply_score": result.supply_score,
            "fundamental_score": result.fundamental_score,
            "market_score": result.market_score,
            "risk_score": result.risk_score,
            "relative_strength_score": result.relative_strength_score,
            "total_score": result.total_score,
            "grade": result.grade,
            "summary": result.summary,
            "financial_analysis": result.financial_analysis,
            "technical_analysis": result.technical_analysis,
            "market_sentiment": result.market_sentiment,
            "comprehensive_analysis": result.comprehensive_analysis,
            "investment_thesis": result.investment_thesis,
            "risks": result.risks,
            "category_reasoning": result.category_reasoning,
        }

    def _dict_to_result(self, data: dict) -> LLMScoreResult:
        """딕셔너리를 결과로 변환"""
        return LLMScoreResult(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            technical_score=data.get("technical_score", 0),
            supply_score=data.get("supply_score", 0),
            fundamental_score=data.get("fundamental_score", 0),
            market_score=data.get("market_score", 0),
            risk_score=data.get("risk_score", 0),
            relative_strength_score=data.get("relative_strength_score", 0),
            total_score=data.get("total_score", 50),
            grade=data.get("grade", "Hold"),
            summary=data.get("summary", ""),
            financial_analysis=data.get("financial_analysis", ""),
            technical_analysis=data.get("technical_analysis", ""),
            market_sentiment=data.get("market_sentiment", ""),
            comprehensive_analysis=data.get("comprehensive_analysis", ""),
            investment_thesis=data.get("investment_thesis", []),
            risks=data.get("risks", []),
            category_reasoning=data.get("category_reasoning", {}),
        )

    def _sector_result_to_dict(self, result: SectorLLMResult) -> dict:
        """섹터 결과를 딕셔너리로 변환"""
        return {
            "sector_name": result.sector_name,
            "reasoning": result.reasoning,
            "outlook": result.outlook,
            "key_drivers": result.key_drivers,
            "investment_strategy": result.investment_strategy,
        }

    def _dict_to_sector_result(self, data: dict) -> SectorLLMResult:
        """딕셔너리를 섹터 결과로 변환"""
        return SectorLLMResult(
            sector_name=data.get("sector_name", ""),
            reasoning=data.get("reasoning", ""),
            outlook=data.get("outlook", ""),
            key_drivers=data.get("key_drivers", []),
            investment_strategy=data.get("investment_strategy", ""),
        )
