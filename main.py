"""주식 신호 분석 메인 애플리케이션"""
import argparse
import os
from datetime import datetime
from src.analysis.analyzer import StockAnalyzer
from src.report.generator import ReportGenerator
from src.portfolio.loader import PortfolioLoader
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
    parser.add_argument(
        '--scheduled',
        action='store_true',
        help='스케줄 실행 모드 (자동으로 파일 저장)'
    )
    parser.add_argument(
        '--portfolio',
        type=str,
        help='포트폴리오 파일 경로 (기본값: .portfolio)'
    )

    args = parser.parse_args()

    # 분석할 종목 결정
    symbols = None
    buy_prices = {}

    # 1. --portfolio 옵션이 지정된 경우
    if args.portfolio:
        try:
            # CSV 파일인지 확인
            if args.portfolio.endswith('.csv'):
                symbols, buy_prices = PortfolioLoader.load_csv(args.portfolio)
                print(f"📂 CSV 포트폴리오 파일에서 {len(symbols)}개 종목을 불러왔습니다: {args.portfolio}")
            else:
                symbols, buy_prices = PortfolioLoader.load(args.portfolio)
                print(f"📂 포트폴리오 파일에서 {len(symbols)}개 종목을 불러왔습니다: {args.portfolio}")
        except (FileNotFoundError, ValueError) as e:
            print(f"오류: {e}")
            return
    # 2. myportfolio 디렉토리에서 최신 CSV 파일 찾기
    elif os.path.exists(config.MYPORTFOLIO_DIR):
        try:
            latest_csv = PortfolioLoader.find_latest_csv(config.MYPORTFOLIO_DIR)
            symbols, buy_prices = PortfolioLoader.load_csv(latest_csv)
            csv_filename = os.path.basename(latest_csv)
            print(f"📂 최신 CSV 포트폴리오에서 {len(symbols)}개 종목을 불러왔습니다: {csv_filename}")
        except (FileNotFoundError, ValueError) as e:
            print(f"경고: {e}")
            symbols = None
    # 3. 기본 .portfolio 파일이 존재하는 경우
    if not symbols and os.path.exists(config.DEFAULT_PORTFOLIO_FILE):
        try:
            symbols, buy_prices = PortfolioLoader.load(config.DEFAULT_PORTFOLIO_FILE)
            print(f"📂 기본 포트폴리오 파일에서 {len(symbols)}개 종목을 불러왔습니다")
        except ValueError as e:
            print(f"경고: {e}")
            symbols = None
    # 4. --symbols 옵션이 지정된 경우
    if not symbols and args.symbols:
        symbols = args.symbols
    # 5. config.py의 종목 사용
    elif not symbols:
        symbols = config.STOCK_SYMBOLS

    if not symbols:
        print("분석할 종목이 없습니다. config.py에서 STOCK_SYMBOLS를 설정하세요.")
        return

    # --buy-prices 옵션으로 매수 가격 덮어쓰기 (포트폴리오 파일보다 우선)
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
    if args.save or args.scheduled:
        # 스케줄 모드일 경우 reports 디렉토리에 저장
        if args.scheduled:
            os.makedirs(config.REPORTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = os.path.join(config.REPORTS_DIR, f"stock_report_{timestamp}.txt")
            reporter.save_report_to_file(analyses, filename)
            print(f"\n스케줄 실행 완료. 보고서: {filename}")
        else:
            reporter.save_report_to_file(analyses)


if __name__ == "__main__":
    main()
