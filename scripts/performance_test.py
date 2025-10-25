#!/usr/bin/env python3
"""
성능 테스트 스크립트

10개 종목을 분석하여 성능을 측정합니다.
목표: 종목당 3초 이내
"""

import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config
from src.analysis.analyzer import StockAnalyzer


def test_performance():
    """성능 테스트 실행"""

    # 테스트할 종목 (10개)
    test_symbols = [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "035420",  # NAVER
        "035720",  # 카카오
        "051910",  # LG화학
        "006400",  # 삼성SDI
        "207940",  # 삼성바이오로직스
        "005380",  # 현대차
        "005490",  # POSCO홀딩스
        "068270",  # 셀트리온
    ]

    # 날짜 설정
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=config.ANALYSIS_PERIOD_DAYS)).strftime("%Y-%m-%d")

    print("=" * 60)
    print("📊 성능 테스트 시작")
    print("=" * 60)
    print(f"종목 수: {len(test_symbols)}개")
    print(f"분석 기간: {start_date} ~ {end_date}")
    print(f"목표: 종목당 3초 이내")
    print("=" * 60)
    print()

    # Analyzer 초기화
    analyzer = StockAnalyzer()

    # 개별 종목 성능 측정
    individual_times = []

    print("📈 개별 종목 분석 속도:")
    print("-" * 60)

    for i, symbol in enumerate(test_symbols, 1):
        start_time = time.time()

        result = analyzer.analyze_stock(symbol, start_date, end_date)

        elapsed = time.time() - start_time
        individual_times.append(elapsed)

        if 'error' in result:
            status = "❌ FAIL"
            name = "오류"
        else:
            status = "✅ OK" if elapsed < 3.0 else "⚠️ SLOW"
            name = result.get('name', symbol)

        print(f"{i:2d}. {symbol} ({name:15s}) : {elapsed:5.2f}초 {status}")

    print("-" * 60)
    print()

    # 다중 종목 분석 성능 측정
    print("📊 다중 종목 일괄 분석 속도:")
    print("-" * 60)

    start_time = time.time()
    results = analyzer.analyze_multiple_stocks(test_symbols, start_date, end_date)
    total_elapsed = time.time() - start_time

    success_count = sum(1 for r in results if 'error' not in r)

    print(f"총 소요 시간: {total_elapsed:.2f}초")
    print(f"성공 종목: {success_count}/{len(test_symbols)}개")
    print(f"종목당 평균: {total_elapsed/len(test_symbols):.2f}초")
    print("-" * 60)
    print()

    # 통계 계산
    avg_time = sum(individual_times) / len(individual_times)
    max_time = max(individual_times)
    min_time = min(individual_times)

    print("📈 통계:")
    print("-" * 60)
    print(f"평균 시간: {avg_time:.2f}초")
    print(f"최대 시간: {max_time:.2f}초")
    print(f"최소 시간: {min_time:.2f}초")
    print(f"목표 달성: {'✅ YES' if avg_time < 3.0 else '❌ NO'}")
    print("-" * 60)
    print()

    # 결과 평가
    print("=" * 60)
    if avg_time < 3.0:
        print("✅ 성능 테스트 통과!")
        print(f"   종목당 평균 {avg_time:.2f}초 (목표: 3초 이내)")
    else:
        print("⚠️ 성능 개선 필요")
        print(f"   종목당 평균 {avg_time:.2f}초 (목표: 3초 이내)")
        print(f"   초과 시간: {avg_time - 3.0:.2f}초")
    print("=" * 60)

    return avg_time < 3.0


if __name__ == "__main__":
    success = test_performance()
    sys.exit(0 if success else 1)
