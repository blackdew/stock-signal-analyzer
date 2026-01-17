#!/usr/bin/env python3
"""
투자 기회 발굴 시스템 CLI

섹터 순환 투자 전략 분석을 실행하는 CLI 인터페이스.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from src.core.logging_config import setup_logging
from src.core.orchestrator import Orchestrator, RunOptions, print_summary


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
  uv run main.py                    # 전체 분석 실행
  uv run main.py --sector-only      # 섹터 분석만
  uv run main.py --no-cache -v      # 캐시 없이 상세 로그
  uv run main.py --format json      # JSON만 출력
  uv run main.py --help             # 도움말
        """
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

    # 실행 옵션 설정
    options = RunOptions(
        sector_only=args.sector_only,
        group=args.group,
        output_format=args.format,
        use_cache=not args.no_cache,
        skip_news=args.no_news,
        output_dir=args.output_dir,
        verbose=args.verbose
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
        else:
            result = asyncio.run(orchestrator.run(options))

        # 결과 출력
        print_summary(result)

        return 0

    except KeyboardInterrupt:
        print("\n\n분석이 사용자에 의해 중단되었습니다.")
        return 1

    except Exception as e:
        print(f"\n오류 발생: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
