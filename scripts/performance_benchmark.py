#!/usr/bin/env python3
"""
Performance Benchmark Tool

각 데이터 수집 및 분석 에이전트 모듈의 실행 속도와 병목 현상을 
기존 코드 수정 없이 몽키패칭(Monkey Patching) 기법으로 가로채어 계측합니다.
"""

import asyncio
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()

from src.core.orchestrator import Orchestrator, RunOptions
from src.data.fetcher import StockDataFetcher
from src.agents.data.fundamental_agent import FundamentalAgent
from src.agents.data.news_agent import NewsAgent
from src.agents.analysis.stock_analyzer import StockAnalyzer
from src.agents.report.stock_report_agent import StockReportAgent

# 로깅 설정
logger = logging.getLogger("PerformanceBenchmark")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")

# 글로벌 성능 측정 지표 딕셔너리
metrics: Dict[str, List[float]] = {
    "StockDataFetcher.fetch_stock_data_with_info": [],
    "FundamentalAgent.collect": [],
    "NewsAgent.collect": [],
    "StockAnalyzer.analyze_symbols": [],
    "StockReportAgent.generate_reports": [],
}

# 몽키패칭을 적용할 래퍼 헬퍼 함수
def patch_async_method(obj, method_name: str, metric_key: str):
    original_method = getattr(obj, method_name)
    
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await original_method(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        metrics[metric_key].append(duration_ms)
        logger.debug(f"⏱️ {metric_key} 실행 완료: {duration_ms:.1f}ms")
        return result
        
    setattr(obj, method_name, async_wrapper)

def patch_sync_method(obj, method_name: str, metric_key: str):
    original_method = getattr(obj, method_name)
    
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = original_method(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        metrics[metric_key].append(duration_ms)
        logger.debug(f"⏱️ {metric_key} 실행 완료: {duration_ms:.1f}ms")
        return result
        
    setattr(obj, method_name, sync_wrapper)

def apply_monkey_patches():
    """
    핵심 클래스의 데이터 수집/분석 메서드에 몽키패치를 적용합니다.
    """
    logger.info("🔧 핵심 모듈 몽키패치(Monkey Patching) 적용 중...")
    
    # 1. Market Data Fetcher (Sync)
    patch_sync_method(StockDataFetcher, "fetch_stock_data_with_info", "StockDataFetcher.fetch_stock_data_with_info")
    
    # 2. Fundamental Agent (Async)
    patch_async_method(FundamentalAgent, "collect", "FundamentalAgent.collect")
    
    # 3. News Agent (Async)
    patch_async_method(NewsAgent, "collect", "NewsAgent.collect")
    
    # 4. Stock Analyzer (Async)
    patch_async_method(StockAnalyzer, "analyze_symbols", "StockAnalyzer.analyze_symbols")
    
    # 5. Stock Report Agent (Async)
    patch_async_method(StockReportAgent, "generate_reports", "StockReportAgent.generate_reports")
    
    logger.info("✅ 몽키패칭 완료")

async def run_benchmark(group: str = "kospi_top10", use_cache: bool = True):
    """
    지정된 그룹(기본 KOSPI 10대 종목)에 대해 성능 측정을 진행합니다.
    """
    logger.info(f"🚀 성능 벤치마크 시작 (대상 그룹: {group}, 캐시 사용: {use_cache})")
    
    apply_monkey_patches()
    
    # 캐시/뉴스 옵션 등 최적화된 설정으로 벤치마크 구동
    options = RunOptions(
        mode="daily",
        group=group,
        output_format="both",
        use_cache=use_cache,
        skip_news=False,
        verbose=False,
        strict=False
    )
    
    orchestrator = Orchestrator(use_cache=use_cache)
    
    total_start = time.time()
    result = await orchestrator.run_daily(options)
    total_duration_ms = (time.time() - total_start) * 1000
    
    logger.info(f"🎉 벤치마크 파이프라인 구동 완료: {total_duration_ms/1000:.2f}초")
    
    # 통계 보고서 작성
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_group": group,
        "use_cache": use_cache,
        "total_duration_ms": round(total_duration_ms, 2),
        "total_duration_sec": round(total_duration_ms / 1000, 2),
        "metrics": {}
    }
    
    for metric_name, values in metrics.items():
        if values:
            report["metrics"][metric_name] = {
                "call_count": len(values),
                "total_time_ms": round(sum(values), 2),
                "avg_time_ms": round(sum(values) / len(values), 2),
                "min_time_ms": round(min(values), 2),
                "max_time_ms": round(max(values), 2)
            }
        else:
            report["metrics"][metric_name] = {
                "call_count": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "min_time_ms": 0.0,
                "max_time_ms": 0.0
            }
            
    # 파일 저장
    output_dir = Path(orchestrator.output_dir) / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "performance_report.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    logger.info(f"📊 성능 보고서 저장 완료: {report_file}")
    
    # 콘솔 가독용 요약 보고서 출력
    print("\n" + "=" * 60)
    print("⚡ 성능 요약 리포트")
    print("=" * 60)
    print(f"총 분석 시간: {report['total_duration_sec']}초")
    for k, v in report["metrics"].items():
        if v["call_count"] > 0:
            print(f"- {k}:")
            print(f"  └ 호출 횟수: {v['call_count']}회")
            print(f"  └ 평균 속도: {v['avg_time_ms']:.1f}ms")
            print(f"  └ 합산 시간: {v['total_time_ms']:.1f}ms")
    print("=" * 60 + "\n")
    
    return report

if __name__ == "__main__":
    asyncio.run(run_benchmark())
