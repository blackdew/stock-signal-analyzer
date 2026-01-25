#!/usr/bin/env python3
"""
투자 기회 발굴 시스템 CLI

섹터 순환 투자 전략 분석을 실행하는 CLI 인터페이스.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# .env 파일에서 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

from src.core.logging_config import setup_logging
from src.core.orchestrator import Orchestrator, RunOptions, print_summary
from src.agents.analysis.data_quality import DataQualityError


def run_web_server(host: str, port: int, verbose: bool) -> int:
    """
    API 서버를 시작합니다.

    Args:
        host: 호스트 주소
        port: 포트 번호
        verbose: 상세 로그 출력

    Returns:
        종료 코드
    """
    try:
        import uvicorn
        from src.web.app import create_app

        print(f"🚀 API 서버 시작: http://{host}:{port}")
        print(f"📚 API 문서: http://{host}:{port}/docs")
        print("종료하려면 Ctrl+C를 누르세요.")

        log_level = "debug" if verbose else "info"
        uvicorn.run(
            "src.web.app:app",
            host=host,
            port=port,
            log_level=log_level,
            reload=False,
        )
        return 0

    except ImportError as e:
        print(f"❌ 웹 서버 실행 실패: {e}")
        print("💡 fastapi와 uvicorn을 설치하세요: uv add fastapi uvicorn[standard]")
        return 1

    except Exception as e:
        print(f"❌ 웹 서버 오류: {e}")
        return 1


def parse_args() -> argparse.Namespace:
    """
    CLI 인자를 파싱합니다.

    Returns:
        파싱된 인자
    """
    parser = argparse.ArgumentParser(
        description="투자 기회 발굴 시스템 - 섹터 순환 전략 분석",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  uv run main.py                    # 일간 리포트 생성 (기본값)
  uv run main.py --daily            # 일간 리포트 생성
  uv run main.py --weekly           # 주간 섹터 리포트 생성
  uv run main.py --sector-only      # 섹터 분석만
  uv run main.py --no-cache -v      # 캐시 없이 상세 로그
  uv run main.py --web              # API 서버 시작
  uv run main.py --web --port 8080  # 커스텀 포트로 API 서버 시작
  uv run main.py --help             # 도움말
        """
    )

    # 모드 선택 (상호 배타적)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--daily",
        action="store_true",
        help="일간 리포트 생성 (기본값)"
    )
    mode_group.add_argument(
        "--weekly",
        action="store_true",
        help="주간 섹터 리포트 생성"
    )
    mode_group.add_argument(
        "--web",
        action="store_true",
        help="API 서버 시작"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API 서버 포트 (기본값: 8000)"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API 서버 호스트 (기본값: 0.0.0.0)"
    )

    parser.add_argument(
        "--sector-only",
        action="store_true",
        help="섹터 분석만 실행"
    )

    parser.add_argument(
        "--group",
        choices=["kospi_top10", "kospi_11_20", "kosdaq_top10", "all"],
        default="all",
        help="분석할 그룹 선택 (기본값: all)"
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "json", "both"],
        default="both",
        help="출력 형식 (기본값: both)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="캐시 사용 안 함"
    )

    parser.add_argument(
        "--no-news",
        action="store_true",
        help="뉴스 분석 스킵"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력"
    )

    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="출력 디렉토리 (기본값: output)"
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="데이터 품질 기준 미달 시 실행 중단"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    return parser.parse_args()


def main() -> int:
    """
    메인 함수

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    # 인자 파싱
    args = parse_args()

    # 로깅 설정
    log_dir = Path(args.output_dir) / "logs"
    setup_logging(verbose=args.verbose, log_dir=log_dir)

    # API 서버 모드
    if args.web:
        return run_web_server(args.host, args.port, args.verbose)

    # 모드 결정: --weekly 이면 "weekly", 아니면 "daily" (기본값)
    mode = "weekly" if args.weekly else "daily"

    # 실행 옵션 설정
    options = RunOptions(
        mode=mode,
        sector_only=args.sector_only,
        group=args.group,
        output_format=args.format,
        use_cache=not args.no_cache,
        skip_news=args.no_news,
        output_dir=args.output_dir,
        verbose=args.verbose,
        strict=args.strict,
    )

    # Orchestrator 생성
    orchestrator = Orchestrator(
        use_cache=options.use_cache,
        skip_news=options.skip_news,
        output_dir=options.output_dir
    )

    try:
        # 분석 실행
        if args.sector_only:
            result = asyncio.run(orchestrator.run_sector_only())
        elif mode == "weekly":
            result = asyncio.run(orchestrator.run_weekly())
        else:
            result = asyncio.run(orchestrator.run_daily(options))

        # 결과 출력
        print_summary(result)

        return 0

    except KeyboardInterrupt:
        print("\n\n분석이 사용자에 의해 중단되었습니다.")
        return 1

    except DataQualityError as e:
        print(f"\n🚫 데이터 품질 오류: {e}")
        summary = e.summary
        print(f"   - 전체 종목: {summary.total_count}개")
        print(f"   - 무효 종목: {summary.invalid_count}개")
        print(f"   - 무효 종목 목록: {', '.join(summary.invalid_symbols[:10])}")
        if len(summary.invalid_symbols) > 10:
            print(f"     ... 외 {len(summary.invalid_symbols) - 10}개")
        print("\n💡 --strict 옵션 없이 실행하면 품질 기준 미달 종목을 포함하여 분석합니다.")
        return 2

    except Exception as e:
        print(f"\n오류 발생: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
