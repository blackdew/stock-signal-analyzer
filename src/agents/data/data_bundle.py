"""
Stock Data Bundle

LLM 분석을 위한 종합 데이터 번들.
MarketData, FundamentalData, NewsData를 통합하여
LLM에게 전달하기 위한 포맷으로 변환합니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.data.market_data_agent import MarketData
from src.agents.data.fundamental_agent import FundamentalData
from src.agents.data.news_agent import NewsData
from src.core.llm import SECTOR_CONTEXTS


@dataclass
class StockDataBundle:
    """
    LLM 분석을 위한 종합 데이터 번들

    모든 수집된 데이터를 LLM이 분석하기 좋은 형태로 통합합니다.

    Attributes:
        symbol: 종목 코드
        name: 종목명
        sector: 섹터명
        market_cap: 시가총액 (억원)

        price_data: 가격 관련 데이터
        technical_indicators: 기술적 지표
        supply_data: 수급 데이터
        fundamental_data: 재무 데이터
        news_data: 뉴스 센티먼트 데이터

        sector_context: 섹터별 분석 컨텍스트
    """
    symbol: str
    name: str
    sector: str
    market_cap: float  # 억원

    # 가격 데이터
    price_data: Dict[str, Any] = field(default_factory=dict)

    # 기술적 지표
    technical_indicators: Dict[str, Any] = field(default_factory=dict)

    # 수급 데이터
    supply_data: Dict[str, Any] = field(default_factory=dict)

    # 재무 데이터
    fundamental_data: Dict[str, Any] = field(default_factory=dict)

    # 뉴스 센티먼트
    news_data: Dict[str, Any] = field(default_factory=dict)

    # 섹터 컨텍스트
    sector_context: str = ""

    @classmethod
    def from_collected_data(
        cls,
        symbol: str,
        name: str,
        sector: str,
        market_cap: float,
        market_data: Optional[MarketData] = None,
        fundamental_data: Optional[FundamentalData] = None,
        news_data: Optional[NewsData] = None,
    ) -> "StockDataBundle":
        """
        수집된 데이터로부터 StockDataBundle을 생성합니다.

        Args:
            symbol: 종목 코드
            name: 종목명
            sector: 섹터명
            market_cap: 시가총액 (억원)
            market_data: MarketData 객체
            fundamental_data: FundamentalData 객체
            news_data: NewsData 객체

        Returns:
            StockDataBundle 인스턴스
        """
        # 섹터 컨텍스트
        sector_context = SECTOR_CONTEXTS.get(sector, f"{sector} 관련 산업")

        # 가격 데이터 추출
        price = {}
        technical = {}
        supply = {}

        if market_data:
            price = {
                "current_price": market_data.current_price,
                "price_change_pct": market_data.price_change_pct,
                "low_52w": market_data.low_52w,
                "high_52w": market_data.high_52w,
                "market_cap": market_data.market_cap,
                "market_cap_rank": market_data.market_cap_rank,
            }

            # 52주 내 위치 계산
            if market_data.low_52w and market_data.high_52w and market_data.current_price:
                if market_data.high_52w != market_data.low_52w:
                    position = (market_data.current_price - market_data.low_52w) / (
                        market_data.high_52w - market_data.low_52w
                    ) * 100
                    price["position_52w"] = round(position, 1)

            technical = {
                "ma20": market_data.ma20,
                "ma60": market_data.ma60,
                "rsi": market_data.rsi,
                "macd": market_data.macd,
                "macd_signal": market_data.macd_signal,
                "adx": market_data.adx,
                "atr": market_data.atr,
                "atr_pct": market_data.atr_pct,
                "beta": market_data.beta,
                "max_drawdown_pct": market_data.max_drawdown_pct,
                "return_20d": market_data.return_20d,
            }

            # 수급 데이터
            foreign_net = market_data.foreign_net_buy or []
            inst_net = market_data.institution_net_buy or []

            # 연속 순매수 일수 계산
            foreign_consecutive = 0
            for amount in foreign_net:
                if amount > 0:
                    foreign_consecutive += 1
                else:
                    break

            inst_consecutive = 0
            for amount in inst_net:
                if amount > 0:
                    inst_consecutive += 1
                else:
                    break

            supply = {
                "foreign_net_5d": foreign_net,
                "foreign_total_5d": sum(foreign_net) if foreign_net else 0,
                "foreign_consecutive_days": foreign_consecutive,
                "institution_net_5d": inst_net,
                "institution_total_5d": sum(inst_net) if inst_net else 0,
                "institution_consecutive_days": inst_consecutive,
                "volume": market_data.volume,
                "avg_volume_20d": market_data.avg_volume_20d,
                "trading_value": market_data.trading_value,
            }

        # 재무 데이터 추출
        fundamental = {}
        if fundamental_data:
            fundamental = {
                "per": fundamental_data.per,
                "pbr": fundamental_data.pbr,
                "roe": fundamental_data.roe,
                "operating_margin": fundamental_data.operating_margin,
                "revenue_growth": fundamental_data.revenue_growth,
                "operating_profit_growth": fundamental_data.operating_profit_growth,
                "debt_ratio": fundamental_data.debt_ratio,
                "dividend_yield": fundamental_data.dividend_yield,
                "sector_avg_per": fundamental_data.sector_avg_per,
                "sector_avg_pbr": fundamental_data.sector_avg_pbr,
            }

        # 뉴스 데이터 추출
        news = {}
        if news_data:
            news = {
                "total_count": news_data.total_count,
                "positive_count": news_data.positive_count,
                "negative_count": news_data.negative_count,
                "neutral_count": news_data.neutral_count,
                "avg_sentiment_score": news_data.avg_sentiment_score,
                "headlines": [
                    {"title": item.title, "sentiment": item.sentiment}
                    for item in news_data.news_items[:5]
                ],
            }

        return cls(
            symbol=symbol,
            name=name,
            sector=sector,
            market_cap=market_cap,
            price_data=price,
            technical_indicators=technical,
            supply_data=supply,
            fundamental_data=fundamental,
            news_data=news,
            sector_context=sector_context,
        )

    def to_prompt_context(self) -> str:
        """
        LLM 프롬프트에 포함할 컨텍스트 문자열을 생성합니다.

        Returns:
            프롬프트용 컨텍스트 문자열
        """
        lines = []

        # 기본 정보
        lines.append(f"## 종목 정보")
        lines.append(f"- 종목명: {self.name}")
        lines.append(f"- 종목코드: {self.symbol}")
        lines.append(f"- 섹터: {self.sector}")
        lines.append(f"- 섹터 특성: {self.sector_context}")
        lines.append(f"- 시가총액: {self.market_cap:,.0f}억원")
        lines.append("")

        # 가격 데이터
        if self.price_data:
            lines.append("## 가격 데이터")
            lines.append(f"- 현재가: {self._fmt(self.price_data.get('current_price'))}원")
            lines.append(f"- 전일대비: {self._fmt(self.price_data.get('price_change_pct'))}%")
            lines.append(f"- 52주 최고가: {self._fmt(self.price_data.get('high_52w'))}원")
            lines.append(f"- 52주 최저가: {self._fmt(self.price_data.get('low_52w'))}원")
            lines.append(f"- 52주 내 위치: {self._fmt(self.price_data.get('position_52w'))}%")
            lines.append("")

        # 기술적 지표
        if self.technical_indicators:
            ti = self.technical_indicators
            lines.append("## 기술적 지표")
            lines.append(f"- MA20: {self._fmt(ti.get('ma20'))}원")
            lines.append(f"- MA60: {self._fmt(ti.get('ma60'))}원")
            lines.append(f"- RSI(14): {self._fmt(ti.get('rsi'))}")
            lines.append(f"- MACD: {self._fmt(ti.get('macd'))}")
            lines.append(f"- MACD Signal: {self._fmt(ti.get('macd_signal'))}")
            lines.append(f"- ADX: {self._fmt(ti.get('adx'))}")
            lines.append(f"- ATR%: {self._fmt(ti.get('atr_pct'))}%")
            lines.append(f"- Beta: {self._fmt(ti.get('beta'))}")
            lines.append(f"- 20일 수익률: {self._fmt(ti.get('return_20d'))}%")
            lines.append(f"- 최대낙폭: {self._fmt(ti.get('max_drawdown_pct'))}%")
            lines.append("")

        # 수급 데이터
        if self.supply_data:
            sd = self.supply_data
            lines.append("## 수급 데이터 (최근 5일)")
            lines.append(f"- 외국인 순매수: {sd.get('foreign_net_5d', [])} (합계: {self._fmt(sd.get('foreign_total_5d'))}억원)")
            lines.append(f"- 외국인 연속 순매수: {sd.get('foreign_consecutive_days', 0)}일")
            lines.append(f"- 기관 순매수: {sd.get('institution_net_5d', [])} (합계: {self._fmt(sd.get('institution_total_5d'))}억원)")
            lines.append(f"- 기관 연속 순매수: {sd.get('institution_consecutive_days', 0)}일")
            lines.append(f"- 거래대금: {self._fmt(sd.get('trading_value'))}억원")
            lines.append("")

        # 재무 데이터
        if self.fundamental_data:
            fd = self.fundamental_data
            lines.append("## 재무 데이터")
            lines.append(f"- PER: {self._fmt(fd.get('per'))}배 (섹터평균: {self._fmt(fd.get('sector_avg_per'))}배)")
            lines.append(f"- PBR: {self._fmt(fd.get('pbr'))}배 (섹터평균: {self._fmt(fd.get('sector_avg_pbr'))}배)")
            lines.append(f"- ROE: {self._fmt(fd.get('roe'))}%")
            lines.append(f"- 영업이익률: {self._fmt(fd.get('operating_margin'))}%")
            lines.append(f"- 영업이익 성장률(YoY): {self._fmt(fd.get('operating_profit_growth'))}%")
            lines.append(f"- 부채비율: {self._fmt(fd.get('debt_ratio'))}%")
            lines.append(f"- 배당수익률: {self._fmt(fd.get('dividend_yield'))}%")
            lines.append("")

        # 뉴스 센티먼트
        if self.news_data:
            nd = self.news_data
            lines.append("## 뉴스 센티먼트")
            lines.append(f"- 총 뉴스: {nd.get('total_count', 0)}건")
            lines.append(f"- 긍정: {nd.get('positive_count', 0)}건 / 부정: {nd.get('negative_count', 0)}건 / 중립: {nd.get('neutral_count', 0)}건")
            lines.append(f"- 평균 센티먼트: {self._fmt(nd.get('avg_sentiment_score'))} (-1.0 ~ 1.0)")

            headlines = nd.get("headlines", [])
            if headlines:
                lines.append("- 주요 헤드라인:")
                for h in headlines[:3]:
                    sentiment_tag = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(
                        h.get("sentiment", "neutral"), "⚪"
                    )
                    lines.append(f"  {sentiment_tag} {h.get('title', '')}")

        return "\n".join(lines)

    def _fmt(self, value: Any) -> str:
        """값 포맷팅"""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            if abs(value) >= 1000:
                return f"{value:,.0f}"
            return f"{value:.2f}"
        return str(value)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "market_cap": self.market_cap,
            "price_data": self.price_data,
            "technical_indicators": self.technical_indicators,
            "supply_data": self.supply_data,
            "fundamental_data": self.fundamental_data,
            "news_data": self.news_data,
            "sector_context": self.sector_context,
        }
