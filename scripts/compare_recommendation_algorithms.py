#!/usr/bin/env python3
"""
Algorithm Comparison Backtest Tool

과거 생성된 분석 결과 JSON 파일(analysis_YYYY-MM-DD.json)을 기반으로,
1) 개선 전 알고리즘(가중치 누락 + 섹터 제한 없음)이 선정한 Top 5 포트폴리오
2) 개선 후 알고리즘(V3 루브릭 가중치 보정 + 섹터 쏠림 가드 탑재)이 선정한 Top 5 포트폴리오
두 그룹의 후행 수익률과 섹터 분산도를 나란히 비교(Side-by-Side)하여 알고리즘 개선 효과를 정량적으로 실증합니다.
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.fetcher import StockDataFetcher
from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.agents.analysis.ranking_agent import RankingAgent

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("AlgoComparison")

# 벤치마크 ETF (KODEX 200)
BENCHMARK_SYMBOL = "069500"
BENCHMARK_NAME = "KODEX 200 ETF"

def load_analysis_files() -> list:
    """output/data/ 디렉토리에서 분석 파일 목록을 날짜 순으로 로드합니다."""
    data_dir = Path("output/data")
    files = list(data_dir.glob("analysis_*.json"))
    files = [f for f in files if f.name != "analysis_test.json"]
    files.sort(key=lambda x: x.name)
    return files

def dict_to_stock_result(d: dict) -> StockAnalysisResult:
    """Dict 데이터를 StockAnalysisResult 객체로 복원합니다."""
    kwargs = {}
    for field_name in StockAnalysisResult.__dataclass_fields__:
        if field_name in d:
            kwargs[field_name] = d[field_name]
    return StockAnalysisResult(**kwargs)

def get_closest_price(df: pd.DataFrame, target_date_str: str, search_forward: bool = True) -> tuple:
    """지정된 날짜와 가장 가까운 영업일의 종가를 가져옵니다."""
    if df is None or df.empty:
        return None, None
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    df_sorted = df.sort_index()
    
    if search_forward:
        available_dates = df_sorted.index[df_sorted.index >= target_dt]
        if len(available_dates) > 0:
            closest_dt = available_dates[0]
            return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])
    else:
        available_dates = df_sorted.index[df_sorted.index <= target_dt]
        if len(available_dates) > 0:
            closest_dt = available_dates[-1]
            return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])
            
    deltas = [abs(idx - target_dt) for idx in df_sorted.index]
    min_idx = deltas.index(min(deltas))
    closest_dt = df_sorted.index[min_idx]
    return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])

def evaluate_portfolio(fetcher: StockDataFetcher, symbols: list, names_dict: dict, start_date: str, end_date: str) -> list:
    """주어진 포트폴리오 종목들의 후행 수익률을 계산합니다."""
    results = []
    # 주말/공휴일 감안하여 앞뒤로 5일씩 여유를 둠
    start_ext = (datetime.strptime(start_date, "%Y-%m-%d") - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end_ext = (datetime.strptime(end_date, "%Y-%m-%d") + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    
    for symbol in symbols:
        name = names_dict.get(symbol, symbol)
        df = fetcher.fetch_stock_data(symbol, start_ext, end_ext)
        if df is None or df.empty:
            continue
            
        _, buy_price = get_closest_price(df, start_date, search_forward=True)
        _, sell_price = get_closest_price(df, end_date, search_forward=False)
        
        if buy_price and sell_price:
            ret = (sell_price - buy_price) / buy_price * 100
            results.append({
                "symbol": symbol,
                "name": name,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "return_pct": round(ret, 2)
            })
    return results

def compare_algorithms():
    files = load_analysis_files()
    if not files:
        logger.error("❌ 분석 결과 JSON 파일이 존재하지 않습니다.")
        return
        
    fetcher = StockDataFetcher()
    ranking_agent = RankingAgent()
    
    latest_trading_date = fetcher._get_latest_trading_date()
    end_date_str = datetime.strptime(latest_trading_date, "%Y%m%d").strftime("%Y-%m-%d")
    
    # 보유 기간이 최소 7일 이상인 분석 데이터 파일들을 필터링 (단기 노이즈 배제)
    target_files = []
    for f in files:
        rec_date_str = f.name.split("_")[1].split(".")[0]
        try:
            rec_dt = datetime.strptime(rec_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            days = (end_dt - rec_dt).days
            if days >= 7:
                target_files.append(f)
        except Exception:
            continue
            
    if not target_files:
        target_files = files[:5]
    else:
        target_files = target_files[-7:]
    
    comparison_results = []
    
    print("\n" + "=" * 80)
    print("🧪 [알고리즘 비교 검증 백테스트] 개선 전 vs 개선 후 포트폴리오 성과 비교")
    print("=" * 80)
    print(f"평가 최종일 (현재 시점): {end_date_str}")
    print(f"대상 분석 기간: {target_files[0].stem.split('_')[1]} ~ {target_files[-1].stem.split('_')[1]}")
    print("=" * 80 + "\n")

    for file_path in target_files:
        rec_date_str = file_path.stem.split("_")[1]
        
        # 주말인 경우 다음 영업일 주가 수정을 위해 해당 날짜부터 end_date_str까지 벤치마크 조회
        bm_df = fetcher.fetch_stock_data(BENCHMARK_SYMBOL, rec_date_str, end_date_str)
        if bm_df is None or bm_df.empty:
            start_extended = (datetime.strptime(rec_date_str, "%Y-%m-%d") - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            end_extended = (datetime.strptime(end_date_str, "%Y-%m-%d") + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            bm_df = fetcher.fetch_stock_data(BENCHMARK_SYMBOL, start_extended, end_extended)
            
        _, bm_buy = get_closest_price(bm_df, rec_date_str, search_forward=True)
        _, bm_sell = get_closest_price(bm_df, end_date_str, search_forward=False)
        bm_return = (bm_sell - bm_buy) / bm_buy * 100 if bm_buy and bm_sell else 0.0

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # 1. 개선 전 포트폴리오 (기존 JSON에 저장되어 있던 final_top5)
        before_top5_raw = data.get("final_top5", [])
        if not before_top5_raw:
            before_top5_raw = data.get("all_selected", [])[:5]
            
        before_symbols = [s.get("symbol") for s in before_top5_raw if s.get("symbol")]
        before_names = {s.get("symbol"): s.get("name") for s in before_top5_raw}
        before_sectors = [s.get("sector", "Unknown") for s in before_top5_raw]
        
        # 2. 개선 후 포트폴리오 (RankingAgent를 통해 새로 산정)
        all_selected_raw = data.get("all_selected", [])
        all_selected_objs = [dict_to_stock_result(s) for s in all_selected_raw]
        
        # RankingAgent에 더미 stock_analyzer를 mock 하여 V3가 강제 설정되게 바인딩 (V3 알고리즘 검증 목적)
        ranking_agent.stock_analyzer = type('MockAnalyzer', (object,), {'rubric_engine': type('MockEngine', (object,), {'use_v3': True})()})()
        
        after_top5_objs = ranking_agent.select_final_top5(all_selected_objs)
        after_symbols = [s.symbol for s in after_top5_objs]
        after_names = {s.symbol: s.name for s in after_top5_objs}
        after_sectors = [s.sector or "Unknown" for s in after_top5_objs]

        # 수익률 연산
        before_eval = evaluate_portfolio(fetcher, before_symbols, before_names, rec_date_str, end_date_str)
        after_eval = evaluate_portfolio(fetcher, after_symbols, after_names, rec_date_str, end_date_str)
        
        before_avg = sum(x["return_pct"] for x in before_eval) / len(before_eval) if before_eval else 0.0
        after_avg = sum(x["return_pct"] for x in after_eval) / len(after_eval) if after_eval else 0.0
        
        # 섹터 쏠림 지표 (동일 섹터 최대 중복 수)
        def max_sector_concentration(sectors):
            if not sectors:
                return 0
            counts = {}
            for sec in sectors:
                counts[sec] = counts.get(sec, 0) + 1
            return max(counts.values())

        before_max_con = max_sector_concentration(before_sectors)
        after_max_con = max_sector_concentration(after_sectors)

        comparison_results.append({
            "date": rec_date_str,
            "benchmark_return": round(bm_return, 2),
            "before": {
                "symbols": before_symbols,
                "names": list(before_names.values()),
                "sectors": before_sectors,
                "max_concentration": before_max_con,
                "avg_return": round(before_avg, 2),
                "alpha": round(before_avg - bm_return, 2),
                "details": before_eval
            },
            "after": {
                "symbols": after_symbols,
                "names": list(after_names.values()),
                "sectors": after_sectors,
                "max_concentration": after_max_con,
                "avg_return": round(after_avg, 2),
                "alpha": round(after_avg - bm_return, 2),
                "details": after_eval
            }
        })
        
        # 개별 날짜 결과 출력
        print(f"📅 [분석 기준일: {rec_date_str}] (보유일 약 {(datetime.strptime(end_date_str, '%Y-%m-%d') - datetime.strptime(rec_date_str, '%Y-%m-%d')).days}일)")
        print(f"  ▪️ KODEX 200 벤치마크 수익률: {bm_return:+.2f}%")
        print(f"  ▪️ [개선 전] Top 5 평균 수익률: {before_avg:+.2f}% (Alpha: {before_avg-bm_return:+.2f}%) | 최대 섹터 집중도: {before_max_con}개 종목")
        print(f"    - 종목: {', '.join([f'{name}({sec})' for name, sec in zip(before_names.values(), before_sectors)])}")
        print(f"  ▪️ [개선 후] Top 5 평균 수익률: {after_avg:+.2f}% (Alpha: {after_avg-bm_return:+.2f}%) | 최대 섹터 집중도: {after_max_con}개 종목")
        print(f"    - 종목: {', '.join([f'{name}({sec})' for name, sec in zip(after_names.values(), after_sectors)])}")
        
        improvement = after_avg - before_avg
        con_improvement = before_max_con - after_max_con
        print(f"  📈 성과 차이: 수익률 {improvement:+.2f}%p 개선 | 섹터 쏠림 {con_improvement:+.0f}개 종목 완화")
        print("-" * 80)

    # 전체 기간 종합 평가
    total_before_avg = sum(x["before"]["avg_return"] for x in comparison_results) / len(comparison_results)
    total_after_avg = sum(x["after"]["avg_return"] for x in comparison_results) / len(comparison_results)
    total_bm_avg = sum(x["benchmark_return"] for x in comparison_results) / len(comparison_results)
    total_before_con = sum(x["before"]["max_concentration"] for x in comparison_results) / len(comparison_results)
    total_after_con = sum(x["after"]["max_concentration"] for x in comparison_results) / len(comparison_results)

    print("\n" + "=" * 80)
    print("🏆 [종합 백테스트 결과] 개선 전 vs 개선 후 알고리즘 비교 피드백")
    print("=" * 80)
    print(f"🔹 벤치마크 평균 수익률:   {total_bm_avg:+.2f}%")
    print(f"🔹 [개선 전] 평균 수익률:   {total_before_avg:+.2f}% (벤치마크 대비 Alpha: {total_before_avg - total_bm_avg:+.2f}%)")
    print(f"🔹 [개선 후] 평균 수익률:   {total_after_avg:+.2f}% (벤치마크 대비 Alpha: {total_after_avg - total_bm_avg:+.2f}%)")
    print(f"👉 알고리즘 개선에 따른 최종 수익률 증분: {total_after_avg - total_before_avg:+.2f}%p 상승")
    print("-" * 80)
    print(f"🔹 [개선 전] 평균 섹터 최대 집중도: {total_before_con:.1f}개 종목 (동일 섹터 내)")
    print(f"🔹 [개선 후] 평균 섹터 최대 집중도: {total_after_con:.1f}개 종목 (동일 섹터 내)")
    print(f"👉 알고리즘 개선에 따른 포트폴리오 위험 분산도: 평균 {total_before_con - total_after_con:.1f}개 종목 완화 (안정성 강화)")
    print("=" * 80 + "\n")

    # 결과를 마크다운 리포트로 저장
    markdown_report_path = Path("docs/issues/algo_comparison_report.md")
    with open(markdown_report_path, "w", encoding="utf-8") as f:
        f.write(f"# 알고리즘 추천 포트폴리오 성과 비교 검증 보고서\n\n")
        f.write(f"- **평가 기준 최종일 (현재 시점)**: {end_date_str}\n")
        f.write(f"- **백테스트 대상 시점 수**: {len(comparison_results)}개 영업일\n")
        f.write(f"- **벤치마크**: {BENCHMARK_NAME} (069500)\n\n")
        
        f.write(f"## 1. 종합 성과 비교 요약\n\n")
        f.write(f"| 평가 지표 | 개선 전 알고리즘 | 개선 후 알고리즘 | 개선 효과 (Delta) |\n")
        f.write(f"|---|---|---|---|\n")
        f.write(f"| **평균 수익률 (Avg Return)** | {total_before_avg:+.2f}% | {total_after_avg:+.2f}% | **{total_after_avg - total_before_avg:+.2f}%p** |\n")
        f.write(f"| **초과 수익률 (Alpha vs BM)** | {total_before_avg - total_bm_avg:+.2f}% | {total_after_avg - total_bm_avg:+.2f}% | **{total_after_avg - total_before_avg:+.2f}%p** |\n")
        f.write(f"| **평균 섹터 최대 집중도** | {total_before_con:.1f}개 | {total_after_con:.1f}개 | **{total_before_con - total_after_con:+.1f}개 완화 (분산)** |\n\n")
        
        f.write(f"## 2. 일자별 상세 백테스트 결과\n\n")
        for rep in comparison_results:
            f.write(f"### 📅 {rep['date']} 추천 시점 성과 (보유일 약 {(datetime.strptime(end_date_str, '%Y-%m-%d') - datetime.strptime(rep['date'], '%Y-%m-%d')).days}일)\n")
            f.write(f"- **벤치마크 수익률**: {rep['benchmark_return']:+.2f}%\n")
            f.write(f"- **[개선 전]** 평균 수익률: {rep['before']['avg_return']:+.2f}% (Alpha: {rep['before']['alpha']:+.2f}%) | 최대 섹터 집중도: {rep['before']['max_concentration']}개\n")
            f.write(f"  - 종목 구성: " + ", ".join([f"`{n}({s})`" for n, s in zip(rep['before']['names'], rep['before']['sectors'])]) + "\n")
            f.write(f"- **[개선 후]** 평균 수익률: {rep['after']['avg_return']:+.2f}% (Alpha: {rep['after']['alpha']:+.2f}%) | 최대 섹터 집중도: {rep['after']['max_concentration']}개\n")
            f.write(f"  - 종목 구성: " + ", ".join([f"`{n}({s})`" for n, s in zip(rep['after']['names'], rep['after']['sectors'])]) + "\n")
            f.write(f"- **개선 결과**: 수익률 **{rep['after']['avg_return'] - rep['before']['avg_return']:+.2f}%p** 향상, 섹터 집중도 **{rep['before']['max_concentration'] - rep['after']['max_concentration']:.0f}개** 감소\n\n")

    logger.info(f"💾 종합 보고서 저장 완료: {markdown_report_path}")

if __name__ == "__main__":
    compare_algorithms()
