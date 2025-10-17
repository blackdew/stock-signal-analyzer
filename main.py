"""주식 신호 분석 메인 애플리케이션"""
import argparse
import os
import webbrowser
import http.server
import socketserver
import threading
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from src.analysis.analyzer import StockAnalyzer
from src.report.generator import ReportGenerator
from src.report.json_generator import JsonReportGenerator
from src.report.history_manager import ReportHistoryManager
from src.portfolio.loader import PortfolioLoader
import config


class APIHandler(http.server.SimpleHTTPRequestHandler):
    """API 엔드포인트를 처리하는 커스텀 HTTP Handler"""

    history_manager = None

    def do_GET(self):
        """GET 요청 처리"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # API 엔드포인트 처리
        if path.startswith('/api/'):
            self.handle_api_request(path, parsed_path.query)
        else:
            # 정적 파일 처리
            super().do_GET()

    def handle_api_request(self, path, query):
        """API 요청 처리"""
        try:
            if self.history_manager is None:
                self.send_error(500, "History manager not initialized")
                return

            # /api/reports - 리포트 목록
            if path == '/api/reports':
                reports = self.history_manager.get_report_list()
                self.send_json_response(reports)

            # /api/report?filename=xxx - 특정 리포트
            elif path == '/api/report':
                params = parse_qs(query)
                filename = params.get('filename', [None])[0]

                if not filename:
                    self.send_error(400, "Missing filename parameter")
                    return

                report = self.history_manager.get_report(filename)
                if report:
                    self.send_json_response(report)
                else:
                    self.send_error(404, "Report not found")

            # /api/trends?symbol=xxx&limit=30 - 종목 추이
            elif path == '/api/trends':
                params = parse_qs(query)
                symbol = params.get('symbol', [None])[0]
                limit = int(params.get('limit', [30])[0])

                if not symbol:
                    self.send_error(400, "Missing symbol parameter")
                    return

                trends = self.history_manager.get_stock_trends(symbol, limit)
                self.send_json_response(trends)

            # /api/symbols - 전체 종목 목록
            elif path == '/api/symbols':
                symbols = self.history_manager.get_available_symbols()
                self.send_json_response(symbols)

            else:
                self.send_error(404, "API endpoint not found")

        except Exception as e:
            self.send_error(500, str(e))

    def send_json_response(self, data):
        """JSON 응답 전송"""
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(response.encode('utf-8')))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))


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
    parser.add_argument(
        '--web',
        action='store_true',
        help='웹 대시보드 모드 (JSON 저장 + 웹서버 실행)'
    )

    args = parser.parse_args()

    # 분석할 종목 결정
    symbols = None
    buy_prices = {}
    quantities = {}

    # 1. --portfolio 옵션이 지정된 경우
    if args.portfolio:
        try:
            # CSV 파일인지 확인
            if args.portfolio.endswith('.csv'):
                symbols, buy_prices, quantities = PortfolioLoader.load_csv(args.portfolio)
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
            symbols, buy_prices, quantities = PortfolioLoader.load_csv(latest_csv)
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

    # 웹 대시보드 모드
    if args.web:
        # JSON 리포트 생성 및 저장
        json_reporter = JsonReportGenerator()
        json_path = json_reporter.save_json_report(analyses, buy_prices, quantities)
        print(f"\n✅ JSON 리포트가 생성되었습니다: {json_path}")

        # 웹서버 실행
        web_dir = os.path.join(config.PROJECT_ROOT, "web")
        port = 8002

        # 웹서버를 별도 스레드에서 실행
        def start_server():
            os.chdir(web_dir)
            # History Manager 초기화
            APIHandler.history_manager = ReportHistoryManager()
            handler = APIHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"\n🌐 웹 대시보드 서버가 시작되었습니다: http://localhost:{port}/dashboard.html")
                print(f"   API: http://localhost:{port}/api/reports")
                print("   종료하려면 Ctrl+C를 누르세요.\n")
                httpd.serve_forever()

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # 브라우저 자동 열기
        webbrowser.open(f"http://localhost:{port}/dashboard.html")

        try:
            # 서버가 실행되는 동안 대기
            server_thread.join()
        except KeyboardInterrupt:
            print("\n\n웹서버를 종료합니다.")
        return

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
