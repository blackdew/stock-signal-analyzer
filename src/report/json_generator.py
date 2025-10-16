"""JSON 형식 리포트 생성기"""
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class JsonReportGenerator:
    """분석 결과를 JSON 형식으로 변환하는 클래스"""

    def __init__(self):
        pass

    def _convert_to_python_type(self, value):
        """numpy 타입을 Python 기본 타입으로 변환"""
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer, np.int64, np.int32)):
            return int(value)
        if isinstance(value, (np.floating, np.float64, np.float32)):
            return float(value)
        return value

    def serialize_analysis(self, analysis: Dict) -> Dict:
        """
        단일 종목 분석 결과를 JSON 직렬화 가능한 형태로 변환

        Args:
            analysis: StockAnalyzer.analyze_stock() 결과

        Returns:
            JSON 직렬화 가능한 딕셔너리
        """
        if 'error' in analysis:
            return {
                'symbol': analysis['symbol'],
                'error': analysis['error']
            }

        # DataFrame을 제외하고 직렬화
        df = analysis.get('data')

        # 최근 가격 데이터 추출 (차트용)
        price_history = []
        if df is not None and not df.empty:
            # 최근 60일 데이터만 추출
            recent_df = df.tail(60)
            price_history = [
                {
                    'date': row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
                    'open': self._convert_to_python_type(row['Open']),
                    'high': self._convert_to_python_type(row['High']),
                    'low': self._convert_to_python_type(row['Low']),
                    'close': self._convert_to_python_type(row['Close']),
                    'volume': self._convert_to_python_type(row['Volume']),
                    'ma20': self._convert_to_python_type(row.get('MA20')) if pd.notna(row.get('MA20')) else None,
                    'ma60': self._convert_to_python_type(row.get('MA60')) if pd.notna(row.get('MA60')) else None,
                }
                for _, row in recent_df.iterrows()
            ]

        return {
            'symbol': analysis['symbol'],
            'name': analysis['name'],
            'current_price': self._convert_to_python_type(analysis['current_price']),
            'price_levels': self._serialize_price_levels(analysis.get('price_levels', {})),
            'volatility_info': self._serialize_volatility_info(analysis.get('volatility_info', {})),
            'knee_info': self._serialize_knee_info(analysis.get('knee_info', {})),
            'shoulder_info': self._serialize_shoulder_info(analysis.get('shoulder_info', {})),
            'buy_analysis': self._serialize_buy_analysis(analysis.get('buy_analysis', {})),
            'buy_recommendation': analysis.get('buy_recommendation', ''),
            'sell_analysis': self._serialize_sell_analysis(analysis.get('sell_analysis', {})),
            'sell_recommendation': analysis.get('sell_recommendation', ''),
            'overall_recommendation': analysis.get('overall_recommendation', ''),
            'action': analysis.get('action', 'HOLD'),
            'price_history': price_history
        }

    def _serialize_price_levels(self, price_levels: Dict) -> Dict:
        """가격 레벨 정보를 직렬화"""
        result = {}
        for key, value in price_levels.items():
            if value is None:
                result[key] = None
            elif key in ['floor_date', 'ceiling_date']:
                result[key] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
            else:
                result[key] = self._convert_to_python_type(value)
        return result

    def _serialize_volatility_info(self, volatility_info: Dict) -> Dict:
        """변동성 정보를 직렬화"""
        return {
            'level': volatility_info.get('level', 'MEDIUM'),
            'current_atr': self._convert_to_python_type(volatility_info.get('current_atr', 0)),
            'avg_atr': self._convert_to_python_type(volatility_info.get('avg_atr', 0)),
            'atr_ratio': self._convert_to_python_type(volatility_info.get('atr_ratio', 1.0)),
            'adjustment_factor': self._convert_to_python_type(volatility_info.get('adjustment_factor', 1.0))
        }

    def _serialize_knee_info(self, knee_info: Dict) -> Dict:
        """무릎 정보를 직렬화"""
        return {
            'is_at_knee': knee_info.get('is_at_knee', False),
            'from_floor_pct': self._convert_to_python_type(knee_info.get('from_floor_pct', 0)),
            'dynamic_knee_price': self._convert_to_python_type(knee_info.get('dynamic_knee_price')),
            'volatility_level': knee_info.get('volatility_level', 'MEDIUM'),
            'current_atr': self._convert_to_python_type(knee_info.get('current_atr', 0)),
            'message': knee_info.get('message', '')
        }

    def _serialize_shoulder_info(self, shoulder_info: Dict) -> Dict:
        """어깨 정보를 직렬화"""
        return {
            'is_at_shoulder': shoulder_info.get('is_at_shoulder', False),
            'from_ceiling_pct': self._convert_to_python_type(shoulder_info.get('from_ceiling_pct', 0)),
            'dynamic_shoulder_price': self._convert_to_python_type(shoulder_info.get('dynamic_shoulder_price')),
            'volatility_level': shoulder_info.get('volatility_level', 'MEDIUM'),
            'current_atr': self._convert_to_python_type(shoulder_info.get('current_atr', 0)),
            'message': shoulder_info.get('message', '')
        }

    def _serialize_buy_analysis(self, buy_analysis: Dict) -> Dict:
        """매수 분석 정보를 직렬화"""
        return {
            'buy_score': self._convert_to_python_type(buy_analysis.get('buy_score', 0)),
            'buy_signals': buy_analysis.get('buy_signals', []),
            'rsi': self._convert_to_python_type(buy_analysis.get('rsi')) if buy_analysis.get('rsi') else None,
            'stop_loss_price': self._convert_to_python_type(buy_analysis.get('stop_loss_price')) if buy_analysis.get('stop_loss_price') else None,
            'at_knee': buy_analysis.get('at_knee', False),
            'is_chase_buy': buy_analysis.get('is_chase_buy', False)
        }

    def _serialize_sell_analysis(self, sell_analysis: Dict) -> Dict:
        """매도 분석 정보를 직렬화"""
        return {
            'sell_score': self._convert_to_python_type(sell_analysis.get('sell_score', 0)),
            'sell_signals': sell_analysis.get('sell_signals', []),
            'sell_strategy': sell_analysis.get('sell_strategy', ''),
            'profit_rate': self._convert_to_python_type(sell_analysis.get('profit_rate')) if sell_analysis.get('profit_rate') is not None else None,
            'volatility': self._convert_to_python_type(sell_analysis.get('volatility')) if sell_analysis.get('volatility') else None,
            'at_shoulder': sell_analysis.get('at_shoulder', False)
        }

    def calculate_portfolio_summary(
        self,
        analyses: List[Dict],
        buy_prices: Optional[Dict[str, float]] = None,
        quantities: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        포트폴리오 전체 요약 정보를 계산

        Args:
            analyses: 분석 결과 리스트
            buy_prices: 종목별 매수 가격 딕셔너리
            quantities: 종목별 수량 딕셔너리

        Returns:
            {
                'total_stocks': 전체 종목 수,
                'total_investment': 총 투자금액,
                'total_valuation': 총 평가금액,
                'total_profit': 총 수익금액,
                'total_profit_rate': 총 수익률,
                'stocks_with_buy_price': 매수가 정보가 있는 종목 수
            }
        """
        if not buy_prices:
            buy_prices = {}
        if not quantities:
            quantities = {}

        total_stocks = len([a for a in analyses if 'error' not in a])
        stocks_with_buy_price = 0
        total_investment = 0
        total_valuation = 0

        for analysis in analyses:
            if 'error' in analysis:
                continue

            symbol = analysis['symbol']
            current_price = analysis['current_price']

            if symbol in buy_prices:
                stocks_with_buy_price += 1
                buy_price = buy_prices[symbol]
                quantity = quantities.get(symbol, 1)  # 기본값 1주

                # 실제 투자금액 = 매수가 × 수량
                total_investment += buy_price * quantity
                # 실제 평가금액 = 현재가 × 수량
                total_valuation += current_price * quantity

        total_profit = total_valuation - total_investment
        total_profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0

        return {
            'total_stocks': total_stocks,
            'stocks_with_buy_price': stocks_with_buy_price,
            'total_investment': total_investment,
            'total_valuation': total_valuation,
            'total_profit': total_profit,
            'total_profit_rate': total_profit_rate
        }

    def generate_json_report(
        self,
        analyses: List[Dict],
        buy_prices: Optional[Dict[str, float]] = None,
        quantities: Optional[Dict[str, int]] = None,
        title: Optional[str] = None
    ) -> Dict:
        """
        전체 분석 결과를 JSON 형식으로 생성

        Args:
            analyses: 분석 결과 리스트
            buy_prices: 종목별 매수 가격 딕셔너리
            quantities: 종목별 수량 딕셔너리
            title: 리포트 제목

        Returns:
            JSON 형식의 리포트
        """
        if title is None:
            title = f"주식 신호 분석 리포트 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 포트폴리오 요약 계산
        portfolio_summary = self.calculate_portfolio_summary(analyses, buy_prices, quantities)

        # 각 종목 분석 결과 직렬화
        stocks = [self.serialize_analysis(a) for a in analyses]

        # 우선순위 종목 추출
        valid_stocks = [s for s in stocks if 'error' not in s]

        buy_priorities = sorted(
            valid_stocks,
            key=lambda x: x['buy_analysis']['buy_score'],
            reverse=True
        )[:5]

        sell_priorities = sorted(
            valid_stocks,
            key=lambda x: x['sell_analysis']['sell_score'],
            reverse=True
        )[:5]

        return {
            'meta': {
                'title': title,
                'generated_at': datetime.now().isoformat(),
                'total_stocks': len(analyses),
                'success_count': len(valid_stocks),
                'error_count': len(analyses) - len(valid_stocks)
            },
            'portfolio_summary': portfolio_summary,
            'stocks': stocks,
            'buy_priorities': [
                {
                    'symbol': s['symbol'],
                    'name': s['name'],
                    'current_price': s['current_price'],
                    'buy_score': s['buy_analysis']['buy_score'],
                    'recommendation': s['buy_recommendation']
                }
                for s in buy_priorities
            ],
            'sell_priorities': [
                {
                    'symbol': s['symbol'],
                    'name': s['name'],
                    'current_price': s['current_price'],
                    'sell_score': s['sell_analysis']['sell_score'],
                    'recommendation': s['sell_recommendation'],
                    'profit_rate': s['sell_analysis']['profit_rate']
                }
                for s in sell_priorities
            ]
        }

    def save_json_report(
        self,
        analyses: List[Dict],
        buy_prices: Optional[Dict[str, float]] = None,
        quantities: Optional[Dict[str, int]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        리포트를 JSON 파일로 저장

        Args:
            analyses: 분석 결과 리스트
            buy_prices: 종목별 매수 가격 딕셔너리
            quantities: 종목별 수량 딕셔너리
            filename: 파일명 (None이면 자동 생성)

        Returns:
            저장된 파일 경로
        """
        import os
        import config

        if filename is None:
            # web/data 디렉토리 자동 생성
            web_data_dir = os.path.join(config.PROJECT_ROOT, "web", "data")
            os.makedirs(web_data_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(web_data_dir, f"stock_report_{timestamp}.json")

        # JSON 리포트 생성
        report = self.generate_json_report(analyses, buy_prices, quantities)

        # 커스텀 JSON encoder (numpy 타입 처리)
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64, np.int32)):
                    return int(obj)
                if isinstance(obj, (np.floating, np.float64, np.float32)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, (np.bool_, bool)):
                    return bool(obj)
                return super().default(obj)

        # 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)

        # latest.json도 함께 생성 (웹 대시보드에서 사용)
        latest_path = os.path.join(os.path.dirname(filename), "latest.json")
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)

        return filename
