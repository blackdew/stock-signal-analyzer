"""뉴스/재료 분석기

웹 검색을 통해 종목의 재료와 리스크를 분석합니다.

분석 항목:
    - 긍정적 재료: 정책 수혜, 신기술, 공장 증설, 턴어라운드, 수주, 인수합병
    - 부정적 재료 (오버행): CB, BW, 유상증자, 대주주 매도, 락업 해제
    - 재료 지속성 평가: 상/중/하
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Any
from datetime import datetime
import time
import re
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 네이버 뉴스 검색 URL
NAVER_NEWS_SEARCH_URL = "https://search.naver.com/search.naver"

# HTTP 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# 키워드 분류
POSITIVE_KEYWORDS = [
    '수주', '계약', '공급', '신기술', '개발', '특허', '인수', '합병', 'M&A',
    '증설', '투자', '확장', '턴어라운드', '흑자전환', '실적개선',
    '정책수혜', '국책사업', '정부지원', 'AI', '반도체', '2차전지',
    '신사업', '진출', '협력', '제휴', 'MOU', '납품',
]

NEGATIVE_KEYWORDS = [
    '전환사채', 'CB', '신주인수권', 'BW', '유상증자', '증자',
    '대주주매도', '블록딜', '락업해제', '보호예수', '매각',
    '적자', '손실', '하락', '감소', '부진', '악화',
    '소송', '횡령', '배임', '분식', '상폐', '관리종목',
]

# 재료 지속성 키워드
LONG_TERM_KEYWORDS = ['공장증설', '대규모투자', '신사업진출', '인수합병', '정책수혜']
MID_TERM_KEYWORDS = ['수주', '계약', '납품', '신제품', '특허']
SHORT_TERM_KEYWORDS = ['테마', '급등', '작전', '루머', '관심']


class NewsAnalyzer:
    """뉴스/재료 분석기"""

    def __init__(self, delay: float = 1.0):
        """
        Args:
            delay: 검색 요청 간 지연 시간 (초)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def search_news(
        self,
        query: str,
        days: int = 30,
        max_results: int = 10
    ) -> List[Dict[str, str]]:
        """
        네이버 뉴스를 검색합니다.

        Args:
            query: 검색어
            days: 검색 기간 (일)
            max_results: 최대 결과 수

        Returns:
            뉴스 리스트 [{'title': '', 'description': '', 'link': '', 'date': ''}]
        """
        try:
            params = {
                'where': 'news',
                'query': query,
                'sort': 1,  # 최신순
                'pd': 4,    # 기간 지정
                'ds': (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y.%m.%d'),
                'de': datetime.now().strftime('%Y.%m.%d'),
            }

            response = self.session.get(NAVER_NEWS_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 뉴스 항목 추출
            news_items = soup.select('div.news_area')[:max_results]

            results = []
            for item in news_items:
                try:
                    title_elem = item.select_one('a.news_tit')
                    desc_elem = item.select_one('div.news_dsc')

                    if title_elem:
                        results.append({
                            'title': title_elem.get_text(strip=True),
                            'link': title_elem.get('href', ''),
                            'description': desc_elem.get_text(strip=True) if desc_elem else '',
                        })
                except Exception:
                    continue

            return results

        except Exception as e:
            logger.debug(f"Error searching news for '{query}': {e}")
            return []

    def analyze_stock_news(
        self,
        stock_code: str,
        stock_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        종목의 뉴스를 분석합니다.

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            days: 검색 기간

        Returns:
            분석 결과 딕셔너리
        """
        result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'positive_news': [],
            'negative_news': [],
            'overhang_risks': [],
            'material_score': 0,  # 재료 점수 (-100 ~ +100)
            'material_durability': '하',  # 상/중/하
            'key_themes': [],
        }

        # 종목명으로 뉴스 검색
        news_list = self.search_news(stock_name, days=days, max_results=20)

        if not news_list:
            return result

        time.sleep(self.delay)

        # 오버행 키워드로 추가 검색
        overhang_news = self.search_news(f"{stock_name} 전환사채 유상증자 대주주매도", days=days, max_results=10)
        news_list.extend(overhang_news)

        # 뉴스 분류
        positive_count = 0
        negative_count = 0
        themes = set()
        durability_score = 0

        for news in news_list:
            text = f"{news['title']} {news['description']}".lower()

            # 긍정적 재료 체크
            for keyword in POSITIVE_KEYWORDS:
                if keyword.lower() in text:
                    result['positive_news'].append({
                        'title': news['title'],
                        'keyword': keyword,
                    })
                    positive_count += 1
                    themes.add(keyword)

                    # 재료 지속성 체크
                    if keyword in LONG_TERM_KEYWORDS:
                        durability_score += 3
                    elif keyword in MID_TERM_KEYWORDS:
                        durability_score += 2
                    elif keyword in SHORT_TERM_KEYWORDS:
                        durability_score -= 1

            # 부정적 재료 체크
            for keyword in NEGATIVE_KEYWORDS:
                if keyword.lower() in text:
                    is_overhang = keyword in ['전환사채', 'CB', '신주인수권', 'BW', '유상증자', '증자',
                                              '대주주매도', '블록딜', '락업해제', '보호예수']

                    news_entry = {
                        'title': news['title'],
                        'keyword': keyword,
                    }

                    if is_overhang:
                        result['overhang_risks'].append(news_entry)
                    else:
                        result['negative_news'].append(news_entry)

                    negative_count += 1

        # 재료 점수 계산 (-100 ~ +100)
        total = positive_count + negative_count
        if total > 0:
            result['material_score'] = int((positive_count - negative_count) / total * 100)

        # 재료 지속성 평가
        if durability_score >= 5:
            result['material_durability'] = '상'
        elif durability_score >= 2:
            result['material_durability'] = '중'
        else:
            result['material_durability'] = '하'

        # 핵심 테마
        result['key_themes'] = list(themes)[:5]

        return result

    def check_overhang_risk(
        self,
        stock_code: str,
        stock_name: str
    ) -> Dict[str, Any]:
        """
        오버행(잠재적 매도 물량) 리스크를 체크합니다.

        Args:
            stock_code: 종목코드
            stock_name: 종목명

        Returns:
            오버행 리스크 분석 결과
        """
        result = {
            'stock_code': stock_code,
            'has_overhang_risk': False,
            'cb_bw_risk': False,
            'capital_increase_risk': False,
            'major_shareholder_risk': False,
            'risks': [],
        }

        # 오버행 관련 뉴스 검색
        queries = [
            f"{stock_name} 전환사채",
            f"{stock_name} 유상증자",
            f"{stock_name} 대주주 매도",
        ]

        for query in queries:
            news = self.search_news(query, days=90, max_results=5)
            time.sleep(self.delay * 0.5)

            for n in news:
                text = n['title'].lower()

                if any(kw in text for kw in ['전환사채', 'cb', '신주인수권', 'bw']):
                    result['cb_bw_risk'] = True
                    result['risks'].append({'type': 'CB/BW', 'title': n['title']})

                if any(kw in text for kw in ['유상증자', '증자']):
                    result['capital_increase_risk'] = True
                    result['risks'].append({'type': '유상증자', 'title': n['title']})

                if any(kw in text for kw in ['대주주', '블록딜', '매각']):
                    result['major_shareholder_risk'] = True
                    result['risks'].append({'type': '대주주매도', 'title': n['title']})

        result['has_overhang_risk'] = any([
            result['cb_bw_risk'],
            result['capital_increase_risk'],
            result['major_shareholder_risk'],
        ])

        return result

    def batch_analyze(
        self,
        stocks: List[Dict[str, str]],  # [{'code': '005930', 'name': '삼성전자'}, ...]
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        여러 종목의 뉴스를 분석합니다.

        Args:
            stocks: 종목 리스트
            days: 검색 기간

        Returns:
            분석 결과 리스트
        """
        logger.info(f"News analysis for {len(stocks)} stocks...")

        results = []

        for i, stock in enumerate(stocks):
            try:
                code = stock.get('code') or stock.get('Code') or stock.get('종목코드')
                name = stock.get('name') or stock.get('Name') or stock.get('종목명')

                if not code or not name:
                    continue

                analysis = self.analyze_stock_news(code, name, days)
                results.append(analysis)

                if (i + 1) % 10 == 0:
                    logger.info(f"News analysis progress: {i + 1}/{len(stocks)}")

                time.sleep(self.delay)

            except Exception as e:
                logger.warning(f"Error analyzing news for {stock}: {e}")

        logger.info(f"News analysis complete: {len(results)} stocks analyzed")

        return results

    def get_analysis_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        분석 결과 요약을 반환합니다.

        Args:
            results: batch_analyze 결과

        Returns:
            요약 정보
        """
        if not results:
            return {
                'total_analyzed': 0,
                'positive_material_count': 0,
                'negative_material_count': 0,
                'overhang_risk_count': 0,
            }

        positive_count = sum(1 for r in results if r['material_score'] > 0)
        negative_count = sum(1 for r in results if r['material_score'] < 0)
        overhang_count = sum(1 for r in results if r['overhang_risks'])

        return {
            'total_analyzed': len(results),
            'positive_material_count': positive_count,
            'negative_material_count': negative_count,
            'neutral_count': len(results) - positive_count - negative_count,
            'overhang_risk_count': overhang_count,
            'high_durability_count': sum(1 for r in results if r['material_durability'] == '상'),
            'avg_material_score': round(sum(r['material_score'] for r in results) / len(results), 1),
        }
