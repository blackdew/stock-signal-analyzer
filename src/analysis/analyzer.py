"""종합 분석 엔진"""
import pandas as pd
from typing import Dict, Optional
import config
from ..data.fetcher import StockDataFetcher
from ..indicators.price_levels import PriceLevelDetector
from ..indicators.buy_signals import BuySignalAnalyzer
from ..indicators.sell_signals import SellSignalAnalyzer
from ..utils.market_analyzer import get_market_analyzer
from ..utils.logger import setup_logger

# 로거 초기화
logger = setup_logger(__name__)


class StockAnalyzer:
    """주식 종합 분석 엔진"""

    def __init__(
        self,
        fetcher=None,
        knee_threshold: float = 0.15,
        shoulder_threshold: float = 0.15,
        stop_loss_pct: float = 0.07,
        chase_risk_threshold: float = 0.25,
        profit_target_full: float = 0.30,
        profit_target_partial: float = 0.15,
        rsi_period: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        lookback_period: int = 60
    ):
        """
        Args:
            fetcher: StockDataFetcher 인스턴스 (None이면 자동 생성)
            knee_threshold: 무릎 판단 기준
            shoulder_threshold: 어깨 판단 기준
            stop_loss_pct: 손절가 비율
            chase_risk_threshold: 추격매수 위험 기준
            profit_target_full: 전량 매도 권장 수익률
            profit_target_partial: 분할 매도 권장 수익률
            rsi_period: RSI 계산 기간
            rsi_oversold: RSI 과매도 기준
            rsi_overbought: RSI 과매수 기준
            lookback_period: 바닥/천장 lookback 기간
        """
        self.fetcher = fetcher if fetcher is not None else StockDataFetcher()
        self.price_detector = PriceLevelDetector(lookback_period)
        self.buy_analyzer = BuySignalAnalyzer(
            knee_threshold,
            stop_loss_pct,
            chase_risk_threshold,
            rsi_period,
            rsi_oversold
        )
        self.sell_analyzer = SellSignalAnalyzer(
            shoulder_threshold,
            profit_target_full,
            profit_target_partial,
            rsi_period,
            rsi_overbought
        )
        self.market_analyzer = get_market_analyzer()

    def analyze_stock(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        buy_price: Optional[float] = None,
        highest_price: Optional[float] = None
    ) -> Dict[str, any]:
        """
        주식을 종합적으로 분석합니다.

        Args:
            symbol: 종목 코드
            start_date: 시작일
            end_date: 종료일
            buy_price: 매수 가격 (선택사항, 수익률 계산용)
            highest_price: 보유 중 최고가 (선택사항, 추적 손절 계산용)

        Returns:
            {
                'symbol': 종목 코드,
                'name': 종목명,
                'current_price': 현재 가격,
                'price_levels': 바닥/천장 정보,
                'buy_analysis': 매수 신호 분석,
                'sell_analysis': 매도 신호 분석,
                'recommendation': 종합 추천,
                'data': 주가 데이터 DataFrame
            }
        """
        logger.info(f"종목 분석 시작: {symbol}")

        # 데이터 가져오기
        df = self.fetcher.fetch_stock_data(symbol, start_date, end_date)

        if df is None or df.empty:
            logger.error(f"종목 {symbol}: 데이터를 가져올 수 없습니다")
            return {
                'symbol': symbol,
                'error': '데이터를 가져올 수 없습니다.'
            }

        # 기술적 지표 추가
        df = self.fetcher.calculate_technical_indicators(df)

        # 종목명 가져오기
        stock_name = self.fetcher.get_stock_name(symbol)

        # 현재 가격
        current_price = df['Close'].iloc[-1]

        # 바닥/천장 분석
        price_levels = self.price_detector.detect_floor_ceiling(df)
        position_metrics = self.price_detector.calculate_position_metrics(df)

        # 변동성 분석 추가
        volatility_info = self.price_detector.calculate_volatility_level(df)
        knee_info = self.price_detector.is_at_knee(df, use_dynamic_threshold=True)
        shoulder_info = self.price_detector.is_at_shoulder(df, use_dynamic_threshold=True)

        # 시장 추세 분석
        market_trend = self.market_analyzer.analyze_trend()
        market_summary = self.market_analyzer.get_market_summary()

        # 매수 신호 분석 (시장 추세 전달)
        buy_analysis = self.buy_analyzer.analyze_buy_signals(df, market_trend)
        buy_recommendation = self.buy_analyzer.get_buy_recommendation(buy_analysis)

        # 매도 신호 분석 (시장 추세 및 최고가 전달)
        sell_analysis = self.sell_analyzer.analyze_sell_signals(df, buy_price, market_trend, highest_price)
        sell_recommendation = self.sell_analyzer.get_sell_recommendation(sell_analysis)

        # 종합 추천 (시장 조정 점수 기반 + 임계값 필터)
        buy_score = buy_analysis.get('market_adjusted_score', buy_analysis.get('buy_score', 0))
        sell_score = sell_analysis.get('market_adjusted_score', sell_analysis.get('sell_score', 0))

        # 액션 결정: 임계값과 점수 차이를 모두 고려
        buy_threshold = config.ACTION_BUY_THRESHOLD
        sell_threshold = config.ACTION_SELL_THRESHOLD
        score_diff_threshold = config.ACTION_SCORE_DIFF_THRESHOLD

        if buy_score >= buy_threshold and buy_score > sell_score + score_diff_threshold:
            # 매수 신호가 충분히 강하고, 매도 신호보다 명확히 우위
            overall_recommendation = buy_recommendation
            action = 'BUY'
        elif sell_score >= sell_threshold and sell_score > buy_score + score_diff_threshold:
            # 매도 신호가 충분히 강하고, 매수 신호보다 명확히 우위
            overall_recommendation = sell_recommendation
            action = 'SELL'
        else:
            # 신호가 약하거나 애매한 경우 관망
            overall_recommendation = "🟡 관망 - 명확한 신호 없음"
            action = 'HOLD'

        logger.info(f"종목 분석 완료: {symbol} ({stock_name}) - 액션: {action}, 매수점수: {buy_score:.1f}, 매도점수: {sell_score:.1f}")

        return {
            'symbol': symbol,
            'name': stock_name,
            'current_price': current_price,
            'price_levels': {
                **price_levels,
                **position_metrics
            },
            'volatility_info': volatility_info,
            'knee_info': knee_info,
            'shoulder_info': shoulder_info,
            'market_summary': market_summary,
            'buy_analysis': buy_analysis,
            'buy_recommendation': buy_recommendation,
            'sell_analysis': sell_analysis,
            'sell_recommendation': sell_recommendation,
            'overall_recommendation': overall_recommendation,
            'action': action,
            'data': df
        }

    def analyze_multiple_stocks(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        buy_prices: Optional[Dict[str, float]] = None,
        highest_prices: Optional[Dict[str, float]] = None
    ) -> list:
        """
        여러 종목을 한 번에 분석합니다.

        Args:
            symbols: 종목 코드 리스트
            start_date: 시작일
            end_date: 종료일
            buy_prices: 종목별 매수 가격 딕셔너리 (선택사항)
            highest_prices: 종목별 최고가 딕셔너리 (선택사항)

        Returns:
            분석 결과 리스트
        """
        logger.info(f"다중 종목 분석 시작: {len(symbols)}개 종목")
        results = []

        for symbol in symbols:
            buy_price = buy_prices.get(symbol) if buy_prices else None
            highest_price = highest_prices.get(symbol) if highest_prices else None
            analysis = self.analyze_stock(symbol, start_date, end_date, buy_price, highest_price)
            results.append(analysis)

        success_count = sum(1 for r in results if 'error' not in r)
        logger.info(f"다중 종목 분석 완료: {success_count}/{len(symbols)}개 성공")
        return results

    def get_priority_stocks(
        self,
        analyses: list,
        action: str = 'BUY',
        top_n: int = 5
    ) -> list:
        """
        분석 결과에서 우선순위 종목을 추출합니다.

        Args:
            analyses: analyze_multiple_stocks() 결과
            action: 'BUY' 또는 'SELL'
            top_n: 상위 N개 종목

        Returns:
            우선순위 종목 리스트
        """
        # 에러가 있는 종목 제외
        valid_analyses = [a for a in analyses if 'error' not in a]

        # 액션에 맞는 점수로 정렬 (시장 조정 점수 우선 사용)
        if action == 'BUY':
            sorted_analyses = sorted(
                valid_analyses,
                key=lambda x: x.get('buy_analysis', {}).get(
                    'market_adjusted_score',
                    x.get('buy_analysis', {}).get('buy_score', 0)
                ),
                reverse=True
            )
        elif action == 'SELL':
            sorted_analyses = sorted(
                valid_analyses,
                key=lambda x: x.get('sell_analysis', {}).get(
                    'market_adjusted_score',
                    x.get('sell_analysis', {}).get('sell_score', 0)
                ),
                reverse=True
            )
        else:
            return valid_analyses[:top_n]

        return sorted_analyses[:top_n]
