"""포트폴리오 파일 로더

지원 형식:
1. .portfolio 파일 (텍스트 형식)
2. CSV 파일 (myportfolio/{date}.csv)

.portfolio 파일 형식:
- 각 줄에 한 종목씩 기록
- 형식: 종목코드 또는 종목코드:매수가격
- #으로 시작하는 줄은 주석으로 처리
- 빈 줄은 무시

예시:
# 내 포트폴리오
005930:71000  # 삼성전자, 71,000원에 매수
000660        # SK하이닉스
035420:195000 # NAVER

CSV 파일 형식:
종목코드,매수가격,수량,종목명
005930,71000,150,삼성전자
000660,120000,30,SK하이닉스
"""

import os
import csv
from typing import Dict, List, Tuple
from datetime import datetime
from glob import glob


class PortfolioLoader:
    """포트폴리오 파일을 읽어서 종목 리스트와 매수 가격을 반환"""

    @staticmethod
    def load(filepath: str) -> Tuple[List[str], Dict[str, float]]:
        """
        포트폴리오 파일을 읽어서 종목 코드와 매수 가격을 반환

        Args:
            filepath: 포트폴리오 파일 경로

        Returns:
            (종목 코드 리스트, 매수 가격 딕셔너리)

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            ValueError: 파일 형식이 잘못되었을 때
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"포트폴리오 파일을 찾을 수 없습니다: {filepath}")

        symbols = []
        buy_prices = {}

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # 주석과 공백 제거
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 인라인 주석 제거
                if '#' in line:
                    line = line[:line.index('#')].strip()

                try:
                    # 종목코드:가격 형식인지 확인
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) != 2:
                            raise ValueError(f"잘못된 형식: {line}")

                        symbol = parts[0].strip()
                        price = float(parts[1].strip().replace(',', ''))

                        symbols.append(symbol)
                        buy_prices[symbol] = price
                    else:
                        # 종목코드만 있는 경우
                        symbol = line.strip()
                        symbols.append(symbol)

                except ValueError as e:
                    print(f"경고: {filepath} 파일의 {line_num}번째 줄을 파싱할 수 없습니다: {line}")
                    print(f"  이유: {e}")
                    continue

        if not symbols:
            raise ValueError(f"포트폴리오 파일에 유효한 종목이 없습니다: {filepath}")

        return symbols, buy_prices

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """종목 코드 유효성 검사 (간단한 검증)"""
        # 한국 주식 코드는 보통 6자리 숫자
        return symbol.isdigit() and len(symbol) == 6

    @staticmethod
    def load_csv(filepath: str) -> Tuple[List[str], Dict[str, float], Dict[str, int]]:
        """
        CSV 포트폴리오 파일을 읽어서 종목 코드, 매수 가격, 수량을 반환

        Args:
            filepath: CSV 파일 경로

        Returns:
            (종목 코드 리스트, 매수 가격 딕셔너리, 수량 딕셔너리)

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            ValueError: 파일 형식이 잘못되었을 때
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {filepath}")

        symbols = []
        buy_prices = {}
        quantities = {}

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # 필수 컬럼 확인
            if '종목코드' not in reader.fieldnames or '매수가격' not in reader.fieldnames:
                raise ValueError(f"CSV 파일에 '종목코드'와 '매수가격' 컬럼이 필요합니다: {filepath}")

            for row_num, row in enumerate(reader, 2):  # 2부터 시작 (헤더가 1행)
                try:
                    symbol = row['종목코드'].strip()
                    price_str = row['매수가격'].strip().replace(',', '')
                    quantity_str = row.get('수량', '').strip().replace(',', '')

                    if not symbol:
                        continue

                    if price_str:
                        price = float(price_str)
                        buy_prices[symbol] = price

                    if quantity_str:
                        quantity = int(quantity_str)
                        quantities[symbol] = quantity
                    else:
                        quantities[symbol] = 1  # 기본값 1주

                    symbols.append(symbol)

                except (ValueError, KeyError) as e:
                    print(f"경고: {filepath} 파일의 {row_num}번째 줄을 파싱할 수 없습니다")
                    print(f"  이유: {e}")
                    continue

        if not symbols:
            raise ValueError(f"CSV 파일에 유효한 종목이 없습니다: {filepath}")

        return symbols, buy_prices, quantities

    @staticmethod
    def find_latest_csv(directory: str) -> str:
        """
        myportfolio 디렉토리에서 가장 최근 날짜의 CSV 파일을 찾음

        Args:
            directory: myportfolio 디렉토리 경로

        Returns:
            가장 최근 CSV 파일 경로

        Raises:
            FileNotFoundError: CSV 파일이 없을 때
        """
        csv_files = glob(os.path.join(directory, "*.csv"))

        if not csv_files:
            raise FileNotFoundError(f"{directory} 디렉토리에 CSV 파일이 없습니다")

        # YYYYMMDD.csv 형식의 파일만 필터링
        date_files = []
        for f in csv_files:
            basename = os.path.basename(f)
            name_without_ext = os.path.splitext(basename)[0]
            # 8자리 숫자 파일명만 선택 (YYYYMMDD 형식)
            if name_without_ext.isdigit() and len(name_without_ext) == 8:
                date_files.append(f)

        if not date_files:
            # 날짜 형식 파일이 없으면 모든 CSV 파일 중 최신 것 반환
            csv_files.sort(key=os.path.getmtime, reverse=True)
            return csv_files[0]

        # 날짜 형식 파일명을 기준으로 정렬 (최신 날짜가 먼저)
        date_files.sort(reverse=True)
        return date_files[0]

    @staticmethod
    def get_today_csv(directory: str) -> str:
        """
        오늘 날짜의 CSV 파일 경로 반환

        Args:
            directory: myportfolio 디렉토리 경로

        Returns:
            오늘 날짜 CSV 파일 경로 (YYYYMMDD.csv)
        """
        today = datetime.now().strftime("%Y%m%d")
        return os.path.join(directory, f"{today}.csv")

    @staticmethod
    def create_example(filepath: str) -> None:
        """예제 포트폴리오 파일 생성"""
        example_content = """# 내 주식 포트폴리오
# 형식: 종목코드:매수가격 또는 종목코드만
# 종목코드는 6자리 숫자입니다.

# 예시 (실제 보유 종목으로 수정하세요)
005930:71000  # 삼성전자
000660:120000 # SK하이닉스
035420        # NAVER (매수가 미지정)
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(example_content)

        print(f"예제 포트폴리오 파일이 생성되었습니다: {filepath}")

    @staticmethod
    def create_example_csv(filepath: str) -> None:
        """예제 CSV 포트폴리오 파일 생성"""
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['종목코드', '매수가격', '수량', '종목명'])
            writer.writerow(['005930', '71000', '150', '삼성전자'])
            writer.writerow(['000660', '120000', '30', 'SK하이닉스'])
            writer.writerow(['035420', '195000', '40', 'NAVER'])

        print(f"예제 CSV 포트폴리오 파일이 생성되었습니다: {filepath}")
