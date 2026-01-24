"""
LLM Integration Module

OpenAI API를 통한 LLM 분석 기능을 제공하는 모듈.
종목 분석 리포트의 상세 분석 텍스트를 생성합니다.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.data.cache import CacheManager

logger = logging.getLogger(__name__)


# =============================================================================
# 상수 정의
# =============================================================================

LLM_CACHE_TTL = 24  # LLM 응답 캐시: 24시간

# 기본 모델 설정
DEFAULT_MODEL = "gpt-4o-mini"
MAX_TOKENS = 2000
TEMPERATURE = 0.7


# =============================================================================
# 섹터별 컨텍스트
# =============================================================================

SECTOR_CONTEXTS: Dict[str, str] = {
    "반도체": "HBM(고대역폭메모리), 파운드리, 메모리반도체, AI 반도체, 장비/소재 등 반도체 밸류체인",
    "조선": "LNG선, 컨테이너선, 해양플랜트, 친환경 선박, 조선기자재 등 조선/해양 산업",
    "방산/우주": "방위산업, 우주항공, 위성, 무인기(드론), 국방 ICT 등 방산/우주 산업",
    "전력인프라": "변압기, 전선, 스마트그리드, 전력기기, 에너지저장장치(ESS) 등 전력 인프라",
    "바이오": "신약개발, 바이오시밀러, 의료기기, 진단키트, 세포치료제, CDMO 등 바이오/헬스케어",
    "로봇": "산업용 로봇, 협동 로봇, 서비스 로봇, 자율주행, AI 로봇 등 로봇/자동화",
    "자동차": "전기차, 배터리, 자율주행, 부품사, 타이어 등 자동차 밸류체인",
    "신재생에너지": "태양광, 풍력, 수소, 2차전지, ESS 등 신재생에너지 산업",
    "지주": "대기업 지주회사, 자회사 가치, 지배구조, 배당정책 등 지주회사",
    "뷰티": "화장품, K-뷰티, ODM/OEM, 스킨케어, 색조화장품 등 뷰티/화장품 산업",
    "금융": "은행, 증권, 보험, 카드, 핀테크 등 금융 산업",
    "푸드": "식품, 음료, 건기식, HMR, 외식 등 식품/음료 산업",
    "엔터": "음악(K-POP), 게임, 드라마/영화, IP 비즈니스, 아이돌 등 엔터테인먼트",
}


# =============================================================================
# 프롬프트 템플릿
# =============================================================================

FINANCIAL_ANALYSIS_PROMPT = """당신은 한국 주식 시장 전문 애널리스트입니다.
다음 종목의 재무 및 밸류에이션 분석을 작성해주세요.

## 종목 정보
- 종목명: {name}
- 종목코드: {symbol}
- 섹터: {sector}
- 섹터 특성: {sector_context}

## 수집된 재무 데이터
- PER: {per}배 (업종평균: {sector_avg_per}배)
- PBR: {pbr}배 (업종평균: {sector_avg_pbr}배)
- ROE: {roe}%
- 영업이익 성장률(YoY): {op_growth}%
- 부채비율: {debt_ratio}%
- 시가총액: {market_cap}억원

## 분석 요청
위 데이터를 바탕으로 2-3문단의 재무 & 밸류에이션 분석을 마크다운 형식으로 작성해주세요.
- 현재 밸류에이션 수준 평가 (저평가/적정/고평가)
- 수익성 및 성장성 평가
- 재무 건전성 평가
- 업종 대비 비교 분석

간결하고 핵심적인 내용만 작성하세요. 투자 용어를 적절히 사용하되 이해하기 쉽게 설명하세요."""

TECHNICAL_ANALYSIS_PROMPT = """당신은 한국 주식 시장 전문 기술적 분석가입니다.
다음 종목의 기술적 분석을 작성해주세요.

## 종목 정보
- 종목명: {name}
- 종목코드: {symbol}
- 현재가: {current_price}원
- 52주 최고가: {high_52w}원
- 52주 최저가: {low_52w}원
- 52주 내 위치: {position_52w}%

## 기술적 지표
- MA20: {ma20}원
- MA60: {ma60}원
- RSI(14): {rsi}
- MACD: {macd}
- MACD Signal: {macd_signal}
- ADX: {adx}

## 분석 요청
위 데이터를 바탕으로 2-3문단의 기술적 분석을 마크다운 형식으로 작성해주세요.
- 현재 추세 판단 (상승/하락/횡보)
- 이동평균선 배열 분석
- 모멘텀 지표(RSI, MACD) 해석
- 지지/저항 구간 분석
- 매매 타이밍 관점에서의 시사점

간결하고 핵심적인 내용만 작성하세요."""

MARKET_SENTIMENT_PROMPT = """당신은 한국 주식 시장 전문 애널리스트입니다.
다음 종목의 시장 센티먼트 분석을 작성해주세요.

## 종목 정보
- 종목명: {name}
- 섹터: {sector}
- 섹터 특성: {sector_context}

## 수급 데이터
- 외국인 연속 순매수: {foreign_consecutive}일
- 기관 연속 순매수: {institution_consecutive}일
- 거래대금: {trading_value}억원

## 뉴스 센티먼트
- 최근 뉴스 건수: {news_count}건
- 긍정 뉴스: {positive_news}건
- 부정 뉴스: {negative_news}건
- 평균 센티먼트 점수: {sentiment_score} (-1.0 ~ 1.0)

## 분석 요청
위 데이터를 바탕으로 2-3문단의 뉴스 & 시장 센티먼트 분석을 마크다운 형식으로 작성해주세요.
- 외국인/기관 수급 동향 해석
- 시장 분위기 및 투자자 심리 평가
- 섹터 전반의 모멘텀 판단
- 수급 관점에서의 매매 시사점

간결하고 핵심적인 내용만 작성하세요."""

COMPREHENSIVE_ANALYSIS_PROMPT = """당신은 한국 주식 시장 전문 투자 전략가입니다.
다음 종목에 대한 종합 투자 의견을 작성해주세요.

## 종목 정보
- 종목명: {name}
- 종목코드: {symbol}
- 섹터: {sector}
- 섹터 특성: {sector_context}
- 현재가: {current_price}원
- 시가총액: {market_cap}억원

## 루브릭 점수 (100점 만점)
- 종합점수: {total_score}점
- 투자등급: {grade}
- 기술적 분석: {technical_score}/25점
- 수급 분석: {supply_score}/20점
- 펀더멘털: {fundamental_score}/20점
- 시장환경: {market_score}/15점
- 리스크: {risk_score}/10점
- 상대강도: {relative_strength_score}/10점

## 주요 강점
{strengths}

## 주요 약점
{weaknesses}

## 분석 요청
위 정보를 종합하여 3-4문단의 종합 투자 의견을 마크다운 형식으로 작성해주세요.

포함할 내용:
1. **핵심 투자 포인트** - 이 종목의 핵심 투자 매력 (섹터 테마, 성장 스토리 포함)
2. **주요 리스크 요인** - 투자 시 유의해야 할 리스크
3. **매매 전략 제안** - 진입/청산 타이밍 관점
4. **최종 투자 의견** - 투자등급({grade})에 맞는 결론

전문적이면서도 이해하기 쉽게 작성하세요. 구체적인 수치와 근거를 포함하세요."""

SUMMARY_PROMPT = """당신은 한국 주식 시장 전문 애널리스트입니다.
다음 종목의 핵심 요약을 1-2문장으로 작성해주세요.

## 종목 정보
- 종목명: {name}
- 섹터: {sector}
- 섹터 특성: {sector_context}
- 투자등급: {grade}
- 종합점수: {total_score}점

## 주요 강점
{strengths}

## 분석 요청
위 정보를 바탕으로 이 종목의 핵심 투자 테마와 매력을 1-2문장으로 요약해주세요.
예시: "AI 메모리 반도체(HBM) 시장의 절대적 지배력을 바탕으로 사상 최대 실적 경신이 기대되는 대장주"

간결하고 임팩트 있게 작성하세요. 섹터 특성을 반영한 핵심 투자 스토리를 담아주세요."""


# =============================================================================
# LLMAnalyzer 클래스
# =============================================================================

@dataclass
class LLMAnalysisResult:
    """LLM 분석 결과"""
    summary: str                    # 핵심 요약 (1-2문장)
    financial_analysis: str         # 재무 & 밸류에이션 분석
    technical_analysis: str         # 기술적 & 차트 분석
    market_sentiment: str           # 뉴스 & 시장 센티먼트
    comprehensive_analysis: str     # 종합 투자 의견
    investment_thesis: List[str]    # 투자 포인트 (3-5개)
    risks: List[str]                # 리스크 요인 (2-4개)


class LLMAnalyzer:
    """
    LLM 기반 종목 분석 생성기

    OpenAI API를 사용하여 종목 분석 리포트의 상세 텍스트를 생성합니다.

    사용 예시:
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze(stock_data)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        LLM 분석기 초기화

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

    async def analyze(
        self,
        symbol: str,
        name: str,
        sector: str,
        market_cap: float,
        total_score: float,
        grade: str,
        technical_score: float,
        supply_score: float,
        fundamental_score: float,
        market_score: float,
        risk_score: float,
        relative_strength_score: float,
        technical_details: Optional[Dict[str, Any]] = None,
        supply_details: Optional[Dict[str, Any]] = None,
        fundamental_details: Optional[Dict[str, Any]] = None,
        news_data: Optional[Dict[str, Any]] = None,
        strengths: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
    ) -> Optional[LLMAnalysisResult]:
        """
        종목 분석 수행

        Args:
            symbol: 종목 코드
            name: 종목명
            sector: 섹터명
            market_cap: 시가총액 (억원)
            total_score: 종합 점수
            grade: 투자 등급
            technical_score: 기술적 분석 점수
            supply_score: 수급 분석 점수
            fundamental_score: 펀더멘털 점수
            market_score: 시장 환경 점수
            risk_score: 리스크 점수
            relative_strength_score: 상대 강도 점수
            technical_details: 기술적 분석 세부 데이터
            supply_details: 수급 분석 세부 데이터
            fundamental_details: 펀더멘털 분석 세부 데이터
            news_data: 뉴스 데이터
            strengths: 강점 리스트
            weaknesses: 약점 리스트

        Returns:
            LLMAnalysisResult 또는 None (실패 시)
        """
        if not self.is_available():
            logger.warning("LLM API key not configured, skipping LLM analysis")
            return None

        # 캐시 확인
        cache_key = f"llm_analysis_{symbol}_{total_score:.0f}"
        cached = self.cache.get(cache_key, max_age_hours=LLM_CACHE_TTL)
        if cached:
            logger.debug(f"LLM analysis cache hit for {symbol}")
            return self._dict_to_result(cached)

        try:
            # 섹터 컨텍스트
            sector_context = SECTOR_CONTEXTS.get(sector, f"{sector} 관련 산업")

            # 기본값 설정
            technical_details = technical_details or {}
            supply_details = supply_details or {}
            fundamental_details = fundamental_details or {}
            news_data = news_data or {}
            strengths = strengths or []
            weaknesses = weaknesses or []

            # 각 분석 생성
            summary = await self._generate_summary(
                name, sector, sector_context, grade, total_score, strengths
            )

            financial_analysis = await self._generate_financial_analysis(
                name, symbol, sector, sector_context, market_cap, fundamental_details
            )

            technical_analysis = await self._generate_technical_analysis(
                name, symbol, technical_details
            )

            market_sentiment = await self._generate_market_sentiment(
                name, sector, sector_context, supply_details, news_data
            )

            comprehensive_analysis = await self._generate_comprehensive_analysis(
                name, symbol, sector, sector_context,
                technical_details.get("current_price"),
                market_cap, total_score, grade,
                technical_score, supply_score, fundamental_score,
                market_score, risk_score, relative_strength_score,
                strengths, weaknesses
            )

            # 투자 포인트 및 리스크 추출
            investment_thesis = self._extract_investment_thesis(strengths, sector_context)
            risks = self._extract_risks(weaknesses, sector_context)

            result = LLMAnalysisResult(
                summary=summary,
                financial_analysis=financial_analysis,
                technical_analysis=technical_analysis,
                market_sentiment=market_sentiment,
                comprehensive_analysis=comprehensive_analysis,
                investment_thesis=investment_thesis,
                risks=risks,
            )

            # 캐시 저장
            self.cache.set(cache_key, self._result_to_dict(result), ttl_hours=LLM_CACHE_TTL)

            return result

        except Exception as e:
            logger.error(f"LLM analysis failed for {symbol}: {e}")
            return None

    async def _generate_summary(
        self, name: str, sector: str, sector_context: str,
        grade: str, total_score: float, strengths: List[str]
    ) -> str:
        """핵심 요약 생성"""
        prompt = SUMMARY_PROMPT.format(
            name=name,
            sector=sector,
            sector_context=sector_context,
            grade=grade,
            total_score=total_score,
            strengths="\n".join(f"- {s}" for s in strengths) if strengths else "- 분석 중",
        )
        return self._call_llm(prompt)

    async def _generate_financial_analysis(
        self, name: str, symbol: str, sector: str, sector_context: str,
        market_cap: float, fundamental_details: Dict[str, Any]
    ) -> str:
        """재무 & 밸류에이션 분석 생성"""
        prompt = FINANCIAL_ANALYSIS_PROMPT.format(
            name=name,
            symbol=symbol,
            sector=sector,
            sector_context=sector_context,
            market_cap=f"{market_cap:,.0f}" if market_cap else "N/A",
            per=self._fmt(fundamental_details.get("per_value"), "배"),
            sector_avg_per=self._fmt(fundamental_details.get("sector_avg_per"), "배"),
            pbr=self._fmt(fundamental_details.get("pbr_value"), "배"),
            sector_avg_pbr=self._fmt(fundamental_details.get("sector_avg_pbr"), "배"),
            roe=self._fmt(fundamental_details.get("roe_value"), "%"),
            op_growth=self._fmt(fundamental_details.get("op_growth_value"), "%"),
            debt_ratio=self._fmt(fundamental_details.get("debt_ratio_value"), "%"),
        )
        return self._call_llm(prompt)

    async def _generate_technical_analysis(
        self, name: str, symbol: str, technical_details: Dict[str, Any]
    ) -> str:
        """기술적 분석 생성"""
        prompt = TECHNICAL_ANALYSIS_PROMPT.format(
            name=name,
            symbol=symbol,
            current_price=self._fmt(technical_details.get("current_price"), "원"),
            high_52w=self._fmt(technical_details.get("high_52w"), "원"),
            low_52w=self._fmt(technical_details.get("low_52w"), "원"),
            position_52w=self._fmt(technical_details.get("position_52w"), "%"),
            ma20=self._fmt(technical_details.get("ma20_value"), "원"),
            ma60=self._fmt(technical_details.get("ma60_value"), "원"),
            rsi=self._fmt(technical_details.get("rsi_value")),
            macd=self._fmt(technical_details.get("macd_value")),
            macd_signal=self._fmt(technical_details.get("macd_signal_value")),
            adx=self._fmt(technical_details.get("adx_value")),
        )
        return self._call_llm(prompt)

    async def _generate_market_sentiment(
        self, name: str, sector: str, sector_context: str,
        supply_details: Dict[str, Any], news_data: Dict[str, Any]
    ) -> str:
        """시장 센티먼트 분석 생성"""
        prompt = MARKET_SENTIMENT_PROMPT.format(
            name=name,
            sector=sector,
            sector_context=sector_context,
            foreign_consecutive=supply_details.get("foreign_consecutive_days", 0),
            institution_consecutive=supply_details.get("institution_consecutive_days", 0),
            trading_value=self._fmt(supply_details.get("trading_value_amount"), "억원"),
            news_count=news_data.get("total_count", 0),
            positive_news=news_data.get("positive_count", 0),
            negative_news=news_data.get("negative_count", 0),
            sentiment_score=news_data.get("avg_sentiment_score", 0.0),
        )
        return self._call_llm(prompt)

    async def _generate_comprehensive_analysis(
        self, name: str, symbol: str, sector: str, sector_context: str,
        current_price: Optional[float], market_cap: float,
        total_score: float, grade: str,
        technical_score: float, supply_score: float, fundamental_score: float,
        market_score: float, risk_score: float, relative_strength_score: float,
        strengths: List[str], weaknesses: List[str]
    ) -> str:
        """종합 투자 의견 생성"""
        prompt = COMPREHENSIVE_ANALYSIS_PROMPT.format(
            name=name,
            symbol=symbol,
            sector=sector,
            sector_context=sector_context,
            current_price=self._fmt(current_price, "원"),
            market_cap=f"{market_cap:,.0f}" if market_cap else "N/A",
            total_score=total_score,
            grade=grade,
            technical_score=technical_score,
            supply_score=supply_score,
            fundamental_score=fundamental_score,
            market_score=market_score,
            risk_score=risk_score,
            relative_strength_score=relative_strength_score,
            strengths="\n".join(f"- {s}" for s in strengths) if strengths else "- 분석 중",
            weaknesses="\n".join(f"- {w}" for w in weaknesses) if weaknesses else "- 특이사항 없음",
        )
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        """LLM API 호출"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return "분석 데이터를 생성할 수 없습니다."

    def _fmt(self, value: Any, suffix: str = "") -> str:
        """값 포맷팅"""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            if suffix == "원":
                return f"{value:,.0f}{suffix}"
            return f"{value:.2f}{suffix}"
        return f"{value}{suffix}"

    def _extract_investment_thesis(self, strengths: List[str], sector_context: str) -> List[str]:
        """투자 포인트 추출"""
        if not strengths:
            return [f"{sector_context} 관련 성장 기대"]
        return strengths[:5]

    def _extract_risks(self, weaknesses: List[str], sector_context: str) -> List[str]:
        """리스크 요인 추출"""
        if not weaknesses:
            return ["시장 변동성에 따른 주가 조정 가능성"]
        return weaknesses[:4]

    def _result_to_dict(self, result: LLMAnalysisResult) -> dict:
        """결과를 딕셔너리로 변환"""
        return {
            "summary": result.summary,
            "financial_analysis": result.financial_analysis,
            "technical_analysis": result.technical_analysis,
            "market_sentiment": result.market_sentiment,
            "comprehensive_analysis": result.comprehensive_analysis,
            "investment_thesis": result.investment_thesis,
            "risks": result.risks,
        }

    def _dict_to_result(self, data: dict) -> LLMAnalysisResult:
        """딕셔너리를 결과로 변환"""
        return LLMAnalysisResult(
            summary=data.get("summary", ""),
            financial_analysis=data.get("financial_analysis", ""),
            technical_analysis=data.get("technical_analysis", ""),
            market_sentiment=data.get("market_sentiment", ""),
            comprehensive_analysis=data.get("comprehensive_analysis", ""),
            investment_thesis=data.get("investment_thesis", []),
            risks=data.get("risks", []),
        )
