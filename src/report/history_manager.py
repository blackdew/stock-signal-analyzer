"""리포트 히스토리 관리 모듈"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import config


class ReportHistoryManager:
    """리포트 히스토리를 관리하는 클래스"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: 리포트 JSON 파일이 저장된 디렉토리 (기본: web/data)
        """
        if data_dir is None:
            self.data_dir = Path(config.PROJECT_ROOT) / "web" / "data"
        else:
            self.data_dir = Path(data_dir)

    def get_report_list(self) -> List[Dict]:
        """
        저장된 모든 리포트 목록을 가져옵니다.

        Returns:
            리포트 목록 (날짜 역순 정렬)
            [
                {
                    'filename': 파일명,
                    'date': 생성 날짜,
                    'total_stocks': 종목 수,
                    'profit_rate': 수익률,
                    'filesize': 파일 크기
                },
                ...
            ]
        """
        if not self.data_dir.exists():
            return []

        reports = []

        # JSON 파일만 찾기 (latest.json 제외)
        for file_path in self.data_dir.glob("stock_report_*.json"):
            try:
                # 파일 메타데이터 읽기
                stat = file_path.stat()
                filesize = stat.st_size

                # JSON 파일 읽기 (메타 정보만)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                meta = data.get('meta', {})
                portfolio = data.get('portfolio_summary', {})

                reports.append({
                    'filename': file_path.name,
                    'date': meta.get('generated_at', ''),
                    'title': meta.get('title', ''),
                    'total_stocks': meta.get('total_stocks', 0),
                    'success_count': meta.get('success_count', 0),
                    'profit_rate': portfolio.get('total_profit_rate', 0),
                    'total_profit': portfolio.get('total_profit', 0),
                    'stocks_with_buy_price': portfolio.get('stocks_with_buy_price', 0),
                    'filesize': filesize
                })
            except Exception as e:
                print(f"Error reading {file_path.name}: {e}")
                continue

        # 날짜 역순 정렬 (최신이 먼저)
        reports.sort(key=lambda x: x['date'], reverse=True)

        return reports

    def get_report(self, filename: str) -> Optional[Dict]:
        """
        특정 리포트를 로드합니다.

        Args:
            filename: 리포트 파일명

        Returns:
            리포트 전체 데이터 또는 None
        """
        file_path = self.data_dir / filename

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading report {filename}: {e}")
            return None

    def get_stock_trends(self, symbol: str, limit: int = 30) -> Dict:
        """
        특정 종목의 매수/매도 점수 및 가격 추이를 가져옵니다.

        Args:
            symbol: 종목 코드
            limit: 최근 N개의 리포트 (기본 30개)

        Returns:
            {
                'symbol': 종목 코드,
                'name': 종목명,
                'data': [
                    {
                        'date': 날짜,
                        'price': 가격,
                        'buy_score': 매수 점수,
                        'sell_score': 매도 점수,
                        'buy_adjusted_score': 시장 조정 매수 점수,
                        'sell_adjusted_score': 시장 조정 매도 점수,
                        'action': 액션 (BUY/SELL/HOLD),
                        'profit_rate': 수익률
                    },
                    ...
                ]
            }
        """
        reports = self.get_report_list()[:limit]
        trend_data = []
        stock_name = None

        for report_info in reports:
            report = self.get_report(report_info['filename'])
            if not report:
                continue

            # 해당 종목 찾기
            stock = next((s for s in report.get('stocks', []) if s.get('symbol') == symbol), None)
            if not stock or 'error' in stock:
                continue

            if stock_name is None:
                stock_name = stock.get('name', symbol)

            buy_analysis = stock.get('buy_analysis', {})
            sell_analysis = stock.get('sell_analysis', {})

            trend_data.append({
                'date': report_info['date'],
                'price': stock.get('current_price', 0),
                'buy_score': buy_analysis.get('buy_score', 0),
                'sell_score': sell_analysis.get('sell_score', 0),
                'buy_adjusted_score': buy_analysis.get('market_adjusted_score', buy_analysis.get('buy_score', 0)),
                'sell_adjusted_score': sell_analysis.get('market_adjusted_score', sell_analysis.get('sell_score', 0)),
                'action': stock.get('action', 'HOLD'),
                'profit_rate': sell_analysis.get('profit_rate'),
                'market_trend': buy_analysis.get('market_trend', 'UNKNOWN')
            })

        # 날짜 정순 정렬 (오래된 것부터)
        trend_data.sort(key=lambda x: x['date'])

        return {
            'symbol': symbol,
            'name': stock_name or symbol,
            'data': trend_data
        }

    def get_available_symbols(self) -> List[Dict[str, str]]:
        """
        모든 리포트에서 등장한 종목 목록을 가져옵니다.

        Returns:
            [{'symbol': 종목코드, 'name': 종목명}, ...]
        """
        symbols = {}

        # 최신 리포트에서 종목 목록 추출
        reports = self.get_report_list()[:5]  # 최근 5개 리포트만 확인

        for report_info in reports:
            report = self.get_report(report_info['filename'])
            if not report:
                continue

            for stock in report.get('stocks', []):
                if 'error' in stock:
                    continue
                symbol = stock.get('symbol')
                name = stock.get('name', symbol)
                if symbol and symbol not in symbols:
                    symbols[symbol] = name

        # 리스트로 변환 (종목명 순 정렬)
        result = [{'symbol': sym, 'name': name} for sym, name in symbols.items()]
        result.sort(key=lambda x: x['name'])

        return result
