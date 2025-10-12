"""주식 신호 분석 메인 애플리케이션"""
import argparse
from src.analysis.analyzer import StockAnalyzer
from src.report.generator import ReportGenerator
import config


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='주식 신호 분석 앱')
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='분석할 종목 코드 (공백으로 구분)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='리포트를 파일로 저장'
    )
    parser.add_argument(
        '--priority',
        action='store_true',
        help='우선순위 종목만 표시'
    )
    parser.add_argument(
        '--buy-prices',
        nargs='+',
        help='매수 가격 (종목코드:가격 형식, 예: 005930:70000)'
    )

    args = parser.parse_args()

    # 분석할 종목 결정
    symbols = args.symbols if args.symbols else config.STOCK_SYMBOLS

    if not symbols:
        print("분석할 종목이 없습니다. config.py에서 STOCK_SYMBOLS를 설정하세요.")
        return

    # 매수 가격 파싱
    buy_prices = {}
    if args.buy_prices:
        for item in args.buy_prices:
            try:
                symbol, price = item.split(':')
                buy_prices[symbol] = float(price)
            except ValueError:
                print(f"경고: 잘못된 매수 가격 형식: {item}")

    print(f"\n📈 주식 신호 분석을 시작합니다...")
    print(f"분석 종목: {', '.join(symbols)}")
    print(f"분석 기간: {config.START_DATE} ~ {config.END_DATE}\n")

    # 분석기 초기화
    analyzer = StockAnalyzer(
        knee_threshold=config.BUY_KNEE_THRESHOLD,
        shoulder_threshold=config.SELL_SHOULDER_THRESHOLD,
        stop_loss_pct=config.STOP_LOSS_PERCENTAGE,
        chase_risk_threshold=config.CHASE_BUY_RISK_THRESHOLD,
        profit_target_full=config.PROFIT_TARGET_FULL_SELL,
        profit_target_partial=config.PROFIT_TARGET_PARTIAL_SELL,
        rsi_period=config.RSI_PERIOD,
        rsi_oversold=config.RSI_OVERSOLD,
        rsi_overbought=config.RSI_OVERBOUGHT,
        lookback_period=config.FLOOR_CEILING_LOOKBACK
    )

    # 분석 실행
    analyses = analyzer.analyze_multiple_stocks(
        symbols,
        config.START_DATE,
        config.END_DATE,
        buy_prices if buy_prices else None
    )

    # 리포트 생성기 초기화
    reporter = ReportGenerator()

    if args.priority:
        # 우선순위 종목만 표시
        buy_priorities = analyzer.get_priority_stocks(analyses, action='BUY', top_n=5)
        sell_priorities = analyzer.get_priority_stocks(analyses, action='SELL', top_n=5)
        reporter.generate_priority_report(buy_priorities, sell_priorities)
    else:
        # 전체 리포트
        reporter.generate_daily_report(analyses)

    # 파일로 저장
    if args.save:
        reporter.save_report_to_file(analyses)


if __name__ == "__main__":
    main()
