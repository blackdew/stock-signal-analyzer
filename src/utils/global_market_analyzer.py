"""
글로벌 시장 분석 모듈
KOSDAQ, NASDAQ, S&P500, 원달러 환율, 미국 10년 국채 금리 데이터 수집 및 분석
"""

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class GlobalMarketAnalyzer:
    """글로벌 시장 지표 분석 클래스 (싱글톤)"""

    _instance = None
    _cache = None
    _cache_time = None
    _cache_duration = timedelta(minutes=10)  # 10분 캐시

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_market_overview(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        글로벌 시장 개요 가져오기

        Returns:
            Dict: {
                'kosdaq': {...},
                'nasdaq': {...},
                'sp500': {...},
                'usd_krw': {...},
                'us_10y': {...},
                'summary': str,
                'timestamp': str
            }
        """
        now = datetime.now()

        # 캐시 확인
        if not force_refresh and self._cache is not None and self._cache_time is not None:
            if now - self._cache_time < self._cache_duration:
                return self._cache

        # 새로운 데이터 수집
        try:
            result = {
                'kosdaq': self._get_kosdaq_data(),
                'nasdaq': self._get_nasdaq_data(),
                'sp500': self._get_sp500_data(),
                'usd_krw': self._get_usd_krw_data(),
                'us_10y': self._get_us_10y_data(),
                'timestamp': now.isoformat()
            }

            # 시장 요약 생성
            result['summary'] = self._generate_market_summary(result)

            # 캐시 저장
            self._cache = result
            self._cache_time = now

            return result

        except Exception as e:
            print(f"글로벌 시장 데이터 수집 중 오류: {e}")
            return self._get_empty_result()

    def _get_kosdaq_data(self) -> Dict[str, Any]:
        """KOSDAQ 데이터 가져오기"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = fdr.DataReader('KQ11', start_date, end_date)
            if df.empty:
                return self._get_empty_index_data('KOSDAQ')

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = latest['Close']
            change = current_price - prev['Close']
            change_pct = (change / prev['Close']) * 100

            # MA20, MA60 계산
            if len(df) >= 20:
                ma20 = df['Close'].tail(20).mean()
            else:
                ma20 = df['Close'].mean()

            if len(df) >= 60:
                ma60 = df['Close'].tail(60).mean()
            else:
                ma60 = df['Close'].mean()

            trend = self._determine_trend(ma20, ma60)

            return {
                'name': 'KOSDAQ',
                'current': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'trend': trend,
                'success': True
            }

        except Exception as e:
            print(f"KOSDAQ 데이터 오류: {e}")
            return self._get_empty_index_data('KOSDAQ')

    def _get_nasdaq_data(self) -> Dict[str, Any]:
        """NASDAQ 데이터 가져오기"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = fdr.DataReader('IXIC', start_date, end_date)  # NASDAQ Composite
            if df.empty:
                return self._get_empty_index_data('NASDAQ')

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = latest['Close']
            change = current_price - prev['Close']
            change_pct = (change / prev['Close']) * 100

            # MA20, MA60 계산
            if len(df) >= 20:
                ma20 = df['Close'].tail(20).mean()
            else:
                ma20 = df['Close'].mean()

            if len(df) >= 60:
                ma60 = df['Close'].tail(60).mean()
            else:
                ma60 = df['Close'].mean()

            trend = self._determine_trend(ma20, ma60)

            return {
                'name': 'NASDAQ',
                'current': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'trend': trend,
                'success': True
            }

        except Exception as e:
            print(f"NASDAQ 데이터 오류: {e}")
            return self._get_empty_index_data('NASDAQ')

    def _get_sp500_data(self) -> Dict[str, Any]:
        """S&P 500 데이터 가져오기"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = fdr.DataReader('SPY', start_date, end_date)  # S&P 500 ETF
            if df.empty:
                return self._get_empty_index_data('S&P 500')

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = latest['Close']
            change = current_price - prev['Close']
            change_pct = (change / prev['Close']) * 100

            # MA20, MA60 계산
            if len(df) >= 20:
                ma20 = df['Close'].tail(20).mean()
            else:
                ma20 = df['Close'].mean()

            if len(df) >= 60:
                ma60 = df['Close'].tail(60).mean()
            else:
                ma60 = df['Close'].mean()

            trend = self._determine_trend(ma20, ma60)

            return {
                'name': 'S&P 500',
                'current': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'trend': trend,
                'success': True
            }

        except Exception as e:
            print(f"S&P 500 데이터 오류: {e}")
            return self._get_empty_index_data('S&P 500')

    def _get_usd_krw_data(self) -> Dict[str, Any]:
        """원달러 환율 데이터 가져오기"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = fdr.DataReader('USD/KRW', start_date, end_date)
            if df.empty:
                return self._get_empty_fx_data('USD/KRW')

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = latest['Close']
            change = current_price - prev['Close']
            change_pct = (change / prev['Close']) * 100

            # MA20 계산
            if len(df) >= 20:
                ma20 = df['Close'].tail(20).mean()
            else:
                ma20 = df['Close'].mean()

            return {
                'name': 'USD/KRW',
                'current': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'ma20': float(ma20),
                'trend': 'UP' if change > 0 else 'DOWN' if change < 0 else 'FLAT',
                'success': True
            }

        except Exception as e:
            print(f"USD/KRW 데이터 오류: {e}")
            return self._get_empty_fx_data('USD/KRW')

    def _get_us_10y_data(self) -> Dict[str, Any]:
        """미국 10년 국채 금리 데이터 가져오기"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = fdr.DataReader('US10YT', start_date, end_date)
            if df.empty:
                return self._get_empty_rate_data('US 10Y')

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_rate = latest['Close']
            change = current_rate - prev['Close']

            # MA20 계산
            if len(df) >= 20:
                ma20 = df['Close'].tail(20).mean()
            else:
                ma20 = df['Close'].mean()

            return {
                'name': 'US 10Y Treasury',
                'current': float(current_rate),
                'change': float(change),
                'ma20': float(ma20),
                'trend': 'UP' if change > 0 else 'DOWN' if change < 0 else 'FLAT',
                'success': True
            }

        except Exception as e:
            print(f"US 10Y 데이터 오류: {e}")
            return self._get_empty_rate_data('US 10Y')

    def _determine_trend(self, ma20: float, ma60: float) -> str:
        """추세 판단"""
        diff_pct = ((ma20 - ma60) / ma60) * 100
        if diff_pct > 2:
            return 'BULL'
        elif diff_pct < -2:
            return 'BEAR'
        else:
            return 'SIDEWAYS'

    def _generate_market_summary(self, data: Dict[str, Any]) -> str:
        """시장 요약 생성"""
        summary_parts = []

        # KOSPI는 기존 분석에서 가져온다고 가정
        kosdaq = data['kosdaq']
        nasdaq = data['nasdaq']
        sp500 = data['sp500']
        usd_krw = data['usd_krw']
        us_10y = data['us_10y']

        # 국내 시장
        if kosdaq['success']:
            trend_emoji = '📈' if kosdaq['trend'] == 'BULL' else '📉' if kosdaq['trend'] == 'BEAR' else '➡️'
            summary_parts.append(
                f"{trend_emoji} KOSDAQ {kosdaq['change_pct']:+.2f}% ({kosdaq['trend'].lower()})"
            )

        # 미국 시장
        us_trends = []
        if nasdaq['success']:
            us_trends.append(f"NASDAQ {nasdaq['change_pct']:+.2f}%")
        if sp500['success']:
            us_trends.append(f"S&P500 {sp500['change_pct']:+.2f}%")

        if us_trends:
            summary_parts.append(f"🇺🇸 미국: {', '.join(us_trends)}")

        # 환율
        if usd_krw['success']:
            fx_emoji = '📈' if usd_krw['change'] > 0 else '📉'
            summary_parts.append(
                f"{fx_emoji} 원달러 환율 {usd_krw['current']:.2f}원 ({usd_krw['change_pct']:+.2f}%)"
            )

        # 금리
        if us_10y['success']:
            rate_emoji = '📈' if us_10y['change'] > 0 else '📉'
            summary_parts.append(
                f"{rate_emoji} 미국 10년물 {us_10y['current']:.2f}% ({us_10y['change']:+.2f}%p)"
            )

        return ' | '.join(summary_parts) if summary_parts else '시장 데이터를 불러올 수 없습니다.'

    def _get_empty_index_data(self, name: str) -> Dict[str, Any]:
        """빈 인덱스 데이터"""
        return {
            'name': name,
            'current': 0.0,
            'change': 0.0,
            'change_pct': 0.0,
            'ma20': 0.0,
            'ma60': 0.0,
            'trend': 'UNKNOWN',
            'success': False
        }

    def _get_empty_fx_data(self, name: str) -> Dict[str, Any]:
        """빈 환율 데이터"""
        return {
            'name': name,
            'current': 0.0,
            'change': 0.0,
            'change_pct': 0.0,
            'ma20': 0.0,
            'trend': 'UNKNOWN',
            'success': False
        }

    def _get_empty_rate_data(self, name: str) -> Dict[str, Any]:
        """빈 금리 데이터"""
        return {
            'name': name,
            'current': 0.0,
            'change': 0.0,
            'ma20': 0.0,
            'trend': 'UNKNOWN',
            'success': False
        }

    def _get_empty_result(self) -> Dict[str, Any]:
        """빈 결과"""
        return {
            'kosdaq': self._get_empty_index_data('KOSDAQ'),
            'nasdaq': self._get_empty_index_data('NASDAQ'),
            'sp500': self._get_empty_index_data('S&P 500'),
            'usd_krw': self._get_empty_fx_data('USD/KRW'),
            'us_10y': self._get_empty_rate_data('US 10Y'),
            'summary': '시장 데이터를 불러올 수 없습니다.',
            'timestamp': datetime.now().isoformat()
        }
