"""종합 분석 엔진"""
import pandas as pd
from typing import Dict, Optional
from ..data.fetcher import StockDataFetcher
from ..indicators.price_levels import PriceLevelDetector
from ..indicators.buy_signals import BuySignalAnalyzer
from ..indicators.sell_signals import SellSignalAnalyzer


class StockAnalyzer:
    """주식 종합 분석 엔진"""

    def __init__(
        self,
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
        self.fetcher = StockDataFetcher()
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

    def analyze_stock(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        buy_price: Optional[float] = None
    ) -> Dict[str, any]:
        """
        주식을 종합적으로 분석합니다.

        Args:
            symbol: 종목 코드
            start_date: 시작일
            end_date: 종료일
            buy_price: 매수 가격 (선택사항, 수익률 계산용)

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
        # 데이터 가져오기
        df = self.fetcher.fetch_stock_data(symbol, start_date, end_date)

        if df is None or df.empty:
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

        # 매수 신호 분석
        buy_analysis = self.buy_analyzer.analyze_buy_signals(df)
        buy_recommendation = self.buy_analyzer.get_buy_recommendation(buy_analysis)

        # 매도 신호 분석
        sell_analysis = self.sell_analyzer.analyze_sell_signals(df, buy_price)
        sell_recommendation = self.sell_analyzer.get_sell_recommendation(sell_analysis)

        # 종합 추천
        buy_score = buy_analysis.get('buy_score', 0)
        sell_score = sell_analysis.get('sell_score', 0)

        if buy_score > sell_score:
            overall_recommendation = buy_recommendation
            action = 'BUY'
        elif sell_score > buy_score:
            overall_recommendation = sell_recommendation
            action = 'SELL'
        else:
            overall_recommendation = "🟡 관망 - 명확한 신호 없음"
            action = 'HOLD'

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
        buy_prices: Optional[Dict[str, float]] = None
    ) -> list:
        """
        여러 종목을 한 번에 분석합니다.

        Args:
            symbols: 종목 코드 리스트
            start_date: 시작일
            end_date: 종료일
            buy_prices: 종목별 매수 가격 딕셔너리 (선택사항)

        Returns:
            분석 결과 리스트
        """
        results = []

        for symbol in symbols:
            buy_price = buy_prices.get(symbol) if buy_prices else None
            analysis = self.analyze_stock(symbol, start_date, end_date, buy_price)
            results.append(analysis)

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

        # 액션에 맞는 점수로 정렬
        if action == 'BUY':
            sorted_analyses = sorted(
                valid_analyses,
                key=lambda x: x.get('buy_analysis', {}).get('buy_score', 0),
                reverse=True
            )
        elif action == 'SELL':
            sorted_analyses = sorted(
                valid_analyses,
                key=lambda x: x.get('sell_analysis', {}).get('sell_score', 0),
                reverse=True
            )
        else:
            return valid_analyses[:top_n]

        return sorted_analyses[:top_n]
