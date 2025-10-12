"""일일 리포트 생성기"""
from datetime import datetime
from typing import Dict, List, Optional


class ReportGenerator:
    """분석 결과를 보기 좋은 형태로 출력하는 클래스"""

    def __init__(self):
        pass

    def format_price(self, price: float) -> str:
        """가격을 포맷팅합니다."""
        return f"{price:,.0f}원"

    def format_percentage(self, value: float) -> str:
        """퍼센트를 포맷팅합니다."""
        return f"{value*100:+.1f}%"

    def format_date(self, date) -> str:
        """날짜를 포맷팅합니다."""
        if hasattr(date, 'strftime'):
            return date.strftime("%Y-%m-%d")
        return str(date)

    def print_header(self, title: str):
        """헤더를 출력합니다."""
        separator = "=" * 80
        print(f"\n{separator}")
        print(f"  {title}")
        print(f"{separator}\n")

    def print_section(self, title: str):
        """섹션 제목을 출력합니다."""
        print(f"\n[ {title} ]")
        print("-" * 80)

    def print_stock_summary(self, analysis: Dict):
        """
        종목 요약 정보를 출력합니다.

        Args:
            analysis: StockAnalyzer.analyze_stock() 결과
        """
        if 'error' in analysis:
            print(f"❌ {analysis['symbol']}: {analysis['error']}")
            return

        symbol = analysis['symbol']
        name = analysis['name']
        current_price = analysis['current_price']
        price_levels = analysis.get('price_levels', {})

        print(f"\n{'='*80}")
        print(f"📊 {name} ({symbol})")
        print(f"{'='*80}")

        # 현재 가격 및 바닥/천장 정보
        print(f"\n💰 현재가: {self.format_price(current_price)}")

        floor = price_levels.get('floor')
        ceiling = price_levels.get('ceiling')
        floor_date = price_levels.get('floor_date')
        ceiling_date = price_levels.get('ceiling_date')

        if floor:
            print(f"   바닥: {self.format_price(floor)} ({self.format_date(floor_date)})")
        if ceiling:
            print(f"   천장: {self.format_price(ceiling)} ({self.format_date(ceiling_date)})")

        from_floor_pct = price_levels.get('from_floor_pct')
        from_ceiling_pct = price_levels.get('from_ceiling_pct')
        position_in_range = price_levels.get('position_in_range')

        if from_floor_pct is not None:
            print(f"   바닥 대비: {self.format_percentage(from_floor_pct)}")
        if from_ceiling_pct is not None:
            print(f"   천장 대비: {self.format_percentage(from_ceiling_pct)}")
        if position_in_range is not None:
            print(f"   레인지 내 위치: {position_in_range*100:.0f}%")

        # 매수 신호
        self.print_section("매수 신호")
        buy_analysis = analysis.get('buy_analysis', {})
        print(f"점수: {buy_analysis.get('buy_score', 0)}/100")
        print(f"추천: {analysis.get('buy_recommendation', 'N/A')}")

        rsi = buy_analysis.get('rsi')
        if rsi:
            print(f"RSI: {rsi:.1f}")

        stop_loss = buy_analysis.get('stop_loss_price')
        if stop_loss:
            print(f"권장 손절가: {self.format_price(stop_loss)}")

        buy_signals = buy_analysis.get('buy_signals', [])
        if buy_signals:
            print(f"신호: {', '.join(buy_signals)}")

        # 매도 신호
        self.print_section("매도 신호")
        sell_analysis = analysis.get('sell_analysis', {})
        print(f"점수: {sell_analysis.get('sell_score', 0)}/100")
        print(f"추천: {analysis.get('sell_recommendation', 'N/A')}")

        sell_strategy = sell_analysis.get('sell_strategy')
        if sell_strategy:
            print(f"전략: {sell_strategy}")

        profit_rate = sell_analysis.get('profit_rate')
        if profit_rate is not None:
            print(f"수익률: {self.format_percentage(profit_rate)}")

        volatility = sell_analysis.get('volatility')
        if volatility is not None:
            print(f"변동성: {volatility*100:.0f}%")

        sell_signals = sell_analysis.get('sell_signals', [])
        if sell_signals:
            print(f"신호: {', '.join(sell_signals)}")

        # 종합 추천
        self.print_section("종합 추천")
        print(f"⭐ {analysis.get('overall_recommendation', 'N/A')}")

    def generate_daily_report(
        self,
        analyses: List[Dict],
        title: Optional[str] = None
    ):
        """
        일일 리포트를 생성합니다.

        Args:
            analyses: 분석 결과 리스트
            title: 리포트 제목
        """
        if title is None:
            title = f"주식 신호 분석 리포트 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        self.print_header(title)

        # 요약 정보
        total_stocks = len(analyses)
        valid_stocks = len([a for a in analyses if 'error' not in a])

        print(f"분석 종목 수: {total_stocks}")
        print(f"성공: {valid_stocks}, 실패: {total_stocks - valid_stocks}")

        # 각 종목 상세 분석
        for analysis in analyses:
            self.print_stock_summary(analysis)

        print(f"\n{'='*80}")
        print("리포트 생성 완료")
        print(f"{'='*80}\n")

    def generate_priority_report(
        self,
        buy_priorities: List[Dict],
        sell_priorities: List[Dict]
    ):
        """
        우선순위 종목 리포트를 생성합니다.

        Args:
            buy_priorities: 매수 우선순위 종목 리스트
            sell_priorities: 매도 우선순위 종목 리스트
        """
        self.print_header("우선순위 종목 분석")

        # 매수 우선순위
        if buy_priorities:
            self.print_section("🟢 매수 우선순위 종목")
            for i, analysis in enumerate(buy_priorities, 1):
                if 'error' in analysis:
                    continue

                name = analysis['name']
                symbol = analysis['symbol']
                current_price = analysis['current_price']
                buy_score = analysis.get('buy_analysis', {}).get('buy_score', 0)
                recommendation = analysis.get('buy_recommendation', '')

                print(f"{i}. {name} ({symbol}) - {self.format_price(current_price)}")
                print(f"   점수: {buy_score}/100 | {recommendation}")

        # 매도 우선순위
        if sell_priorities:
            self.print_section("🔴 매도 우선순위 종목")
            for i, analysis in enumerate(sell_priorities, 1):
                if 'error' in analysis:
                    continue

                name = analysis['name']
                symbol = analysis['symbol']
                current_price = analysis['current_price']
                sell_score = analysis.get('sell_analysis', {}).get('sell_score', 0)
                recommendation = analysis.get('sell_recommendation', '')

                print(f"{i}. {name} ({symbol}) - {self.format_price(current_price)}")
                print(f"   점수: {sell_score}/100 | {recommendation}")

        print(f"\n{'='*80}\n")

    def save_report_to_file(
        self,
        analyses: List[Dict],
        filename: Optional[str] = None
    ):
        """
        리포트를 파일로 저장합니다.

        Args:
            analyses: 분석 결과 리스트
            filename: 파일명 (None이면 자동 생성)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stock_report_{timestamp}.txt"

        import sys
        from io import StringIO

        # stdout을 캡처
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()

        try:
            self.generate_daily_report(analyses)
            content = buffer.getvalue()
        finally:
            sys.stdout = old_stdout

        # 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"리포트가 저장되었습니다: {filename}")
