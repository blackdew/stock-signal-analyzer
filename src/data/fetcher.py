"""주식 데이터 가져오기 모듈"""
import pandas as pd
import FinanceDataReader as fdr
import time
from typing import Optional
from src.utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


class StockDataFetcher:
    """FinanceDataReader를 사용하여 주식 데이터를 가져오는 클래스"""

    def __init__(self):
        pass

    def fetch_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        주식 데이터를 가져옵니다. (재시도 로직 포함)

        Args:
            symbol: 종목 코드 (예: '005930' for 삼성전자)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            max_retries: 최대 재시도 횟수 (기본 3회)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Change
            실패시 None 반환
        """
        for attempt in range(max_retries):
            try:
                logger.debug(f"종목 {symbol}: 데이터 가져오기 시도 {attempt + 1}/{max_retries}")
                df = fdr.DataReader(symbol, start_date, end_date)

                # 데이터 검증
                if df is None or df.empty:
                    logger.warning(
                        f"종목 {symbol}: 데이터 없음 (시도 {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 1초 대기 후 재시도
                        continue
                    else:
                        logger.error(f"종목 {symbol}: 최대 재시도 횟수 초과 - 데이터 없음")
                        return None

                # 데이터 정리
                df = df.sort_index()
                logger.info(
                    f"종목 {symbol}: 데이터 가져오기 성공 "
                    f"({len(df)} 행, {start_date} ~ {end_date})"
                )
                return df

            except Exception as e:
                logger.error(
                    f"종목 {symbol}: API 호출 실패 - {str(e)} "
                    f"(시도 {attempt + 1}/{max_retries})"
                )

                if attempt < max_retries - 1:
                    # 지수 백오프 (1초, 2초, 4초)
                    wait_time = 2 ** attempt
                    logger.info(f"종목 {symbol}: {wait_time}초 대기 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"종목 {symbol}: 최대 재시도 횟수 초과 - API 호출 실패")
                    return None

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
            logger.debug(f"종목 {symbol}: 종목명 조회 중...")
            # KRX 상장 종목 리스트 가져오기
            krx = fdr.StockListing('KRX')
            stock_info = krx[krx['Code'] == symbol]

            if not stock_info.empty:
                name = stock_info.iloc[0]['Name']
                logger.debug(f"종목 {symbol}: 종목명 조회 성공 - {name}")
                return name
            else:
                logger.warning(f"종목 {symbol}: 종목명 조회 실패 - 종목 코드 사용")
                return symbol

        except Exception as e:
            logger.warning(f"종목 {symbol}: 종목명 조회 오류 - {str(e)}")
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
