"""OpenDART API 클라이언트

금융감독원 전자공시시스템(DART) Open API를 통해 재무제표 데이터를 조회합니다.

주요 기능:
    - 기업 고유번호(corp_code) 조회
    - 3년치 재무제표 조회 (매출액, 영업이익, 부채비율)
    - 연속 적자 여부 확인
"""

import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import pandas as pd
import time
from typing import Optional, Dict, List, Any
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# OpenDART API 설정
OPENDART_API_KEY = 'bdea2d013558292c23243e5f25a2b7a09243627d'
OPENDART_BASE_URL = 'https://opendart.fss.or.kr/api'


class OpenDartClient:
    """OpenDART API 클라이언트"""

    def __init__(self, api_key: str = OPENDART_API_KEY):
        self.api_key = api_key
        self.corp_codes: Dict[str, str] = {}  # 종목코드 -> corp_code 매핑
        self._load_corp_codes()

    def _load_corp_codes(self) -> None:
        """기업 고유번호 목록을 로드합니다."""
        cache_path = Path(__file__).parent / 'corp_codes.pkl'

        # 캐시된 데이터가 있으면 로드
        if cache_path.exists():
            try:
                import pickle
                with open(cache_path, 'rb') as f:
                    self.corp_codes = pickle.load(f)
                logger.info(f"Corp codes loaded from cache: {len(self.corp_codes)} companies")
                return
            except Exception as e:
                logger.warning(f"Failed to load corp codes from cache: {e}")

        # API에서 다운로드
        try:
            logger.info("Downloading corp codes from OpenDART...")
            url = f"{OPENDART_BASE_URL}/corpCode.xml"
            params = {'crtfc_key': self.api_key}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                xml_content = zf.read('CORPCODE.xml')

            # XML 파싱
            root = ET.fromstring(xml_content)
            for item in root.findall('.//list'):
                stock_code = item.findtext('stock_code', '').strip()
                corp_code = item.findtext('corp_code', '').strip()

                if stock_code:  # 상장기업만
                    self.corp_codes[stock_code] = corp_code

            logger.info(f"Corp codes downloaded: {len(self.corp_codes)} companies")

            # 캐시 저장
            try:
                import pickle
                with open(cache_path, 'wb') as f:
                    pickle.dump(self.corp_codes, f)
                logger.info("Corp codes cached successfully")
            except Exception as e:
                logger.warning(f"Failed to cache corp codes: {e}")

        except Exception as e:
            logger.error(f"Failed to download corp codes: {e}")

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드로 기업 고유번호를 조회합니다."""
        return self.corp_codes.get(stock_code)

    def get_financial_statements(
        self,
        stock_code: str,
        years: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        최근 N년간 재무제표를 조회합니다.

        Args:
            stock_code: 종목코드 (예: '005930')
            years: 조회할 연도 수 (기본 3년)

        Returns:
            재무제표 데이터 딕셔너리 또는 None
            {
                'stock_code': '005930',
                'years': [
                    {'year': 2024, 'revenue': 1000, 'operating_income': 100, 'debt_ratio': 50.0},
                    {'year': 2023, ...},
                    {'year': 2022, ...},
                ]
            }
        """
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            logger.warning(f"Corp code not found for {stock_code}")
            return None

        current_year = pd.Timestamp.now().year
        financial_data = {
            'stock_code': stock_code,
            'years': []
        }

        for i in range(years):
            year = current_year - i
            bsns_year = str(year)

            # 연간 재무제표 조회 (11013: 연결재무제표, 11012: 별도재무제표)
            data = self._fetch_financial_data(corp_code, bsns_year, '11011')

            if data:
                financial_data['years'].append(data)

            # API 호출 간격 조절
            time.sleep(0.1)

        return financial_data if financial_data['years'] else None

    def _fetch_financial_data(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = '11011'  # 11011: 사업보고서
    ) -> Optional[Dict[str, Any]]:
        """
        특정 연도의 재무제표를 조회합니다.

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (예: '2024')
            reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기, 11014: 3분기)
        """
        url = f"{OPENDART_BASE_URL}/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != '000':
                # 데이터 없음 (정상적인 상황일 수 있음)
                return None

            items = data.get('list', [])
            if not items:
                return None

            # 재무제표 항목 추출
            result = {
                'year': int(bsns_year),
                'revenue': None,          # 매출액
                'operating_income': None,  # 영업이익
                'total_assets': None,      # 자산총계
                'total_liabilities': None, # 부채총계
                'total_equity': None,      # 자본총계
                'debt_ratio': None,        # 부채비율
            }

            for item in items:
                account_nm = item.get('account_nm', '')
                # 당기 금액 (연결재무제표 우선)
                thstrm_amount = item.get('thstrm_amount', '')

                # 금액 파싱
                try:
                    amount = int(thstrm_amount.replace(',', '')) if thstrm_amount else None
                except ValueError:
                    amount = None

                # 항목 매핑
                if '매출액' in account_nm or '수익(매출액)' in account_nm:
                    result['revenue'] = amount
                elif '영업이익' in account_nm and '손실' not in account_nm:
                    result['operating_income'] = amount
                elif account_nm == '자산총계':
                    result['total_assets'] = amount
                elif account_nm == '부채총계':
                    result['total_liabilities'] = amount
                elif account_nm == '자본총계':
                    result['total_equity'] = amount

            # 부채비율 계산
            if result['total_liabilities'] and result['total_equity'] and result['total_equity'] > 0:
                result['debt_ratio'] = round(
                    (result['total_liabilities'] / result['total_equity']) * 100, 2
                )

            return result

        except Exception as e:
            logger.error(f"Failed to fetch financial data for {corp_code}/{bsns_year}: {e}")
            return None

    def check_consecutive_losses(
        self,
        stock_code: str,
        years: int = 3
    ) -> Dict[str, Any]:
        """
        연속 적자 여부를 확인합니다.

        Args:
            stock_code: 종목코드
            years: 확인할 연도 수

        Returns:
            {
                'has_consecutive_losses': True/False,
                'loss_years': [2024, 2023, 2022],
                'operating_incomes': {2024: -100, 2023: -50, 2022: -30}
            }
        """
        financial_data = self.get_financial_statements(stock_code, years)

        result = {
            'has_consecutive_losses': False,
            'loss_years': [],
            'operating_incomes': {}
        }

        if not financial_data or not financial_data.get('years'):
            return result

        for year_data in financial_data['years']:
            year = year_data['year']
            op_income = year_data.get('operating_income')

            if op_income is not None:
                result['operating_incomes'][year] = op_income
                if op_income < 0:
                    result['loss_years'].append(year)

        # 연속 적자 확인
        if len(result['loss_years']) >= years:
            result['has_consecutive_losses'] = True

        return result

    def get_debt_ratio(self, stock_code: str) -> Optional[float]:
        """
        최신 부채비율을 조회합니다.

        Args:
            stock_code: 종목코드

        Returns:
            부채비율 (%) 또는 None
        """
        financial_data = self.get_financial_statements(stock_code, years=1)

        if financial_data and financial_data.get('years'):
            latest = financial_data['years'][0]
            return latest.get('debt_ratio')

        return None

    def get_financial_summary(
        self,
        stock_code: str,
        years: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        재무 요약 정보를 조회합니다.

        Args:
            stock_code: 종목코드
            years: 조회할 연도 수

        Returns:
            재무 요약 딕셔너리
        """
        financial_data = self.get_financial_statements(stock_code, years)

        if not financial_data or not financial_data.get('years'):
            return None

        loss_check = self.check_consecutive_losses(stock_code, years)

        summary = {
            'stock_code': stock_code,
            'financial_years': financial_data['years'],
            'has_consecutive_losses': loss_check['has_consecutive_losses'],
            'loss_years': loss_check['loss_years'],
            'latest_debt_ratio': financial_data['years'][0].get('debt_ratio') if financial_data['years'] else None,
        }

        return summary


def get_opendart_client() -> OpenDartClient:
    """OpenDartClient 싱글톤 인스턴스를 반환합니다."""
    if not hasattr(get_opendart_client, '_instance'):
        get_opendart_client._instance = OpenDartClient()
    return get_opendart_client._instance
