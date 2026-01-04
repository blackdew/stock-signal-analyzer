"""투자자별 매매동향 분석기

네이버 금융에서 외국인/기관 순매수 데이터를 스크래핑합니다.

조건:
    - 최근 5거래일 중 3일 이상 외국인 OR 기관 순매수
"""

import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 네이버 금융 URL
NAVER_INVESTOR_URL = "https://finance.naver.com/item/frgn.naver"

# HTTP 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}


class InvestorFlowAnalyzer:
    """투자자별 매매동향 분석기"""

    def __init__(
        self,
        min_net_buy_days: int = 3,
        lookback_days: int = 5,
        delay: float = 0.5,  # 요청 간 지연 (초)
    ):
        """
        Args:
            min_net_buy_days: 최소 순매수 일수 (기본 3일)
            lookback_days: 확인할 거래일 수 (기본 5일)
            delay: API 요청 간 지연 시간 (초)
        """
        self.min_net_buy_days = min_net_buy_days
        self.lookback_days = lookback_days
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_investor_trading(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        종목의 투자자별 매매동향을 조회합니다.

        Args:
            stock_code: 종목코드 (예: '005930')

        Returns:
            매매동향 딕셔너리 또는 None
            {
                'stock_code': '005930',
                'data': [
                    {'date': '2024.01.15', 'foreign_net': 1000, 'institution_net': 500},
                    ...
                ],
                'foreign_net_buy_days': 3,
                'institution_net_buy_days': 2,
            }
        """
        try:
            url = f"{NAVER_INVESTOR_URL}?code={stock_code}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'euc-kr'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 테이블 찾기
            tables = soup.find_all('table', class_='type2')
            if not tables:
                return None

            # 첫 번째 테이블이 투자자별 매매동향
            table = tables[0]
            rows = table.find_all('tr')

            data = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 6:
                    continue

                try:
                    # 날짜
                    date_text = cols[0].get_text(strip=True)
                    if not date_text or '.' not in date_text:
                        continue

                    # 외국인 순매수 (4번째 컬럼)
                    foreign_text = cols[4].get_text(strip=True).replace(',', '')
                    foreign_net = int(foreign_text) if foreign_text.lstrip('-').isdigit() else 0

                    # 기관 순매수 (5번째 컬럼)
                    institution_text = cols[5].get_text(strip=True).replace(',', '')
                    institution_net = int(institution_text) if institution_text.lstrip('-').isdigit() else 0

                    data.append({
                        'date': date_text,
                        'foreign_net': foreign_net,
                        'institution_net': institution_net,
                    })

                except (ValueError, IndexError) as e:
                    continue

            if not data:
                return None

            # 최근 N일 데이터만 사용
            recent_data = data[:self.lookback_days]

            # 순매수 일수 계산
            foreign_net_buy_days = sum(1 for d in recent_data if d['foreign_net'] > 0)
            institution_net_buy_days = sum(1 for d in recent_data if d['institution_net'] > 0)

            return {
                'stock_code': stock_code,
                'data': recent_data,
                'foreign_net_buy_days': foreign_net_buy_days,
                'institution_net_buy_days': institution_net_buy_days,
                'total_foreign_net': sum(d['foreign_net'] for d in recent_data),
                'total_institution_net': sum(d['institution_net'] for d in recent_data),
            }

        except Exception as e:
            logger.debug(f"Error fetching investor data for {stock_code}: {e}")
            return None

    def check_smart_money_flow(self, stock_code: str) -> Dict[str, Any]:
        """
        스마트 머니(외국인/기관) 유입 여부를 확인합니다.

        Args:
            stock_code: 종목코드

        Returns:
            분석 결과 딕셔너리
        """
        result = {
            'stock_code': stock_code,
            'has_smart_money_flow': False,
            'foreign_signal': False,
            'institution_signal': False,
            'foreign_net_buy_days': 0,
            'institution_net_buy_days': 0,
            'total_foreign_net': 0,
            'total_institution_net': 0,
        }

        trading_data = self.get_investor_trading(stock_code)

        if trading_data is None:
            return result

        result['foreign_net_buy_days'] = trading_data['foreign_net_buy_days']
        result['institution_net_buy_days'] = trading_data['institution_net_buy_days']
        result['total_foreign_net'] = trading_data['total_foreign_net']
        result['total_institution_net'] = trading_data['total_institution_net']

        # 조건: 최근 N일 중 M일 이상 순매수
        result['foreign_signal'] = trading_data['foreign_net_buy_days'] >= self.min_net_buy_days
        result['institution_signal'] = trading_data['institution_net_buy_days'] >= self.min_net_buy_days

        # 외국인 OR 기관 조건 충족
        result['has_smart_money_flow'] = result['foreign_signal'] or result['institution_signal']

        return result

    def screen(
        self,
        stock_codes: List[str],
        require_both: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        수급 조건으로 종목을 필터링합니다.

        Args:
            stock_codes: 분석할 종목코드 리스트
            require_both: True면 외국인+기관 모두 조건 충족 필요

        Returns:
            (통과 종목 DataFrame, 전체 분석 결과 DataFrame)
        """
        logger.info(f"Analyzing investor flow for {len(stock_codes)} stocks...")

        results = []
        passed_codes = []

        for i, code in enumerate(stock_codes):
            try:
                analysis = self.check_smart_money_flow(code)
                results.append(analysis)

                if require_both:
                    if analysis['foreign_signal'] and analysis['institution_signal']:
                        passed_codes.append(code)
                else:
                    if analysis['has_smart_money_flow']:
                        passed_codes.append(code)

                # 진행 상황
                if (i + 1) % 20 == 0:
                    logger.info(f"Investor flow progress: {i + 1}/{len(stock_codes)} (passed: {len(passed_codes)})")

                # 요청 간 지연
                time.sleep(self.delay)

            except Exception as e:
                logger.warning(f"Error analyzing {code}: {e}")

        all_df = pd.DataFrame(results) if results else pd.DataFrame()
        passed_df = all_df[all_df['stock_code'].isin(passed_codes)] if not all_df.empty else pd.DataFrame()

        logger.info(f"Investor flow screening: {len(passed_codes)}/{len(stock_codes)} passed")

        return passed_df, all_df

    def get_summary(self, analysis_df: pd.DataFrame) -> Dict[str, Any]:
        """
        분석 결과 요약을 반환합니다.

        Args:
            analysis_df: screen()의 결과 DataFrame

        Returns:
            요약 정보 딕셔너리
        """
        if analysis_df.empty:
            return {
                'total_analyzed': 0,
                'foreign_signal_count': 0,
                'institution_signal_count': 0,
                'both_signal_count': 0,
            }

        return {
            'total_analyzed': len(analysis_df),
            'foreign_signal_count': analysis_df['foreign_signal'].sum(),
            'institution_signal_count': analysis_df['institution_signal'].sum(),
            'both_signal_count': ((analysis_df['foreign_signal']) & (analysis_df['institution_signal'])).sum(),
            'avg_foreign_net_buy_days': round(analysis_df['foreign_net_buy_days'].mean(), 1),
            'avg_institution_net_buy_days': round(analysis_df['institution_net_buy_days'].mean(), 1),
        }
