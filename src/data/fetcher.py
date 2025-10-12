"""주식 데이터 가져오기 모듈"""
import pandas as pd
import FinanceDataReader as fdr
from typing import Optional


class StockDataFetcher:
    """FinanceDataReader를 사용하여 주식 데이터를 가져오는 클래스"""

    def __init__(self):
        pass

    def fetch_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        주식 데이터를 가져옵니다.

        Args:
            symbol: 종목 코드 (예: '005930' for 삼성전자)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Change
            실패시 None 반환
        """
        try:
            df = fdr.DataReader(symbol, start_date, end_date)

            if df is None or df.empty:
                print(f"경고: {symbol}에 대한 데이터가 없습니다.")
                return None

            # 데이터 정리
            df = df.sort_index()

            return df

        except Exception as e:
            print(f"오류: {symbol} 데이터 가져오기 실패 - {str(e)}")
            return None

    def get_stock_name(self, symbol: str) -> str:
        """
        종목 코드로부터 종목명을 가져옵니다.

        Args:
            symbol: 종목 코드

        Returns:
            종목명 (실패시 종목 코드 반환)
        """
        try:
            # KRX 상장 종목 리스트 가져오기
            krx = fdr.StockListing('KRX')
            stock_info = krx[krx['Code'] == symbol]

            if not stock_info.empty:
                return stock_info.iloc[0]['Name']
            else:
                return symbol

        except Exception as e:
            print(f"경고: {symbol} 종목명 조회 실패 - {str(e)}")
            return symbol

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기본적인 기술적 지표를 계산합니다.

        Args:
            df: 주가 데이터 DataFrame

        Returns:
            기술적 지표가 추가된 DataFrame
        """
        if df is None or df.empty:
            return df

        # 데이터 복사
        df = df.copy()

        # 이동평균선 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 거래량 이동평균
        df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()

        return df
