#!/usr/bin/env python3
"""
Investment Performance Backtest Tool

과거 생성된 분석 결과 JSON 파일(analysis_YYYY-MM-DD.json)을 기반으로,
당시 추천된 포트폴리오(Top 5, Top 18)의 후행 수익률을 KODEX 200 ETF(069500) 벤치마크 및 
우주(Universe) 전체 평균과 대조하여 정량적으로 평가합니다.
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

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("InvestmentBacktest")

# 벤치마크 ETF (KODEX 200)
BENCHMARK_SYMBOL = "069500"
BENCHMARK_NAME = "KODEX 200 ETF"

def load_analysis_files() -> list:
    """output/data/ 디렉토리에서 분석 파일 목록을 날짜 순으로 로드합니다."""
    data_dir = Path("output/data")
    files = list(data_dir.glob("analysis_*.json"))
    
    # 임시 테스트 파일 제외 및 정렬
    files = [f for f in files if f.name != "analysis_test.json"]
    files.sort(key=lambda x: x.name)
    return files

def get_closest_price(df: pd.DataFrame, target_date_str: str, search_forward: bool = True) -> tuple:
    """
    지정된 날짜와 가장 가까운 영업일의 종가를 가져옵니다.
    주말/공휴일인 경우 그 이전 또는 이후 날짜를 탐색합니다.
    """
    if df is None or df.empty:
        return None, None
        
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # 인덱스(DatetimeIndex) 정렬
    df_sorted = df.sort_index()
    
    if search_forward:
        # target_dt 이후의 첫 거래일
        available_dates = df_sorted.index[df_sorted.index >= target_dt]
        if len(available_dates) > 0:
            closest_dt = available_dates[0]
            return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])
    else:
        # target_dt 이전의 첫 거래일
        available_dates = df_sorted.index[df_sorted.index <= target_dt]
        if len(available_dates) > 0:
            closest_dt = available_dates[-1]
            return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])
            
    # 정밀 매칭이 안 되면 가장 인접한 날짜
    deltas = [abs(idx - target_dt) for idx in df_sorted.index]
    min_idx = deltas.index(min(deltas))
    closest_dt = df_sorted.index[min_idx]
    return closest_dt.strftime("%Y-%m-%d"), float(df_sorted.loc[closest_dt, "Close"])

def backtest_portfolio(fetcher: StockDataFetcher, analysis_file: Path, end_date_str: str):
    """지정된 분석 파일에 대해 추천 포트폴리오의 후행 수익률을 계산합니다."""
    logger.info(f"📁 분석 파일 로드 중: {analysis_file.name}")
    
    # 파일명에서 날짜 추출 (analysis_2026-05-31.json -> 2026-05-31)
    rec_date_str = analysis_file.stem.split("_")[1]
    
    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 포트폴리오 추출
    # 1. Top 5 추천
    top5_list = data.get("final_top5", [])
    if not top5_list:
        # final_top5가 비어있으면 all_selected의 상위 5개 사용
        all_sel = data.get("all_selected", [])
        top5_list = all_sel[:5]
        
    top5_symbols = [s.get("symbol") for s in top5_list if s.get("symbol")]
    top5_names = {s.get("symbol"): s.get("name") for s in top5_list}
    
    # 2. Top 18 추천
    all_selected = data.get("all_selected", [])
    top18_symbols = [s.get("symbol") for s in all_selected if s.get("symbol")]
    top18_names = {s.get("symbol"): s.get("name") for s in all_selected}
    
    if not top5_symbols:
        logger.warning(f"⚠️ {analysis_file.name} 에 유효한 추천 종목이 없습니다.")
        return None
        
    logger.info(f"🗓️ 추천 기준일: {rec_date_str} | 평가 종료일: {end_date_str}")
    logger.info(f"👉 Top 5 추천 종목: {list(top5_names.values())}")
    
    # 벤치마크 ETF 데이터 가져오기
    bm_df = fetcher.fetch_stock_data(BENCHMARK_SYMBOL, rec_date_str, end_date_str)
    if bm_df is None or bm_df.empty:
        # 기간이 너무 짧거나 주말인 경우 날짜 범위를 조금 늘려서 가져오기
        start_extended = (datetime.strptime(rec_date_str, "%Y-%m-%d") - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        end_extended = (datetime.strptime(end_date_str, "%Y-%m-%d") + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        bm_df = fetcher.fetch_stock_data(BENCHMARK_SYMBOL, start_extended, end_extended)
        
    bm_buy_date, bm_buy_price = get_closest_price(bm_df, rec_date_str, search_forward=True)
    bm_sell_date, bm_sell_price = get_closest_price(bm_df, end_date_str, search_forward=False)
    
    if bm_buy_price is None or bm_sell_price is None:
        logger.error("❌ 벤치마크 가격 정보를 수집할 수 없습니다.")
        return None
        
    bm_return = (bm_sell_price - bm_buy_price) / bm_buy_price * 100
    
    logger.info(f"📊 벤치마크 {BENCHMARK_NAME}: {bm_buy_price:,.0f}원 -> {bm_sell_price:,.0f}원 (수익률: {bm_return:.2f}%)")
    
    # 개별 종목 수익률 연산
    def evaluate_symbols(symbols, names):
        results = []
        for symbol in symbols:
            name = names.get(symbol, symbol)
            # 날짜 여유분을 두고 조회 후 인접일 매칭
            start_ext = (datetime.strptime(rec_date_str, "%Y-%m-%d") - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            end_ext = (datetime.strptime(end_date_str, "%Y-%m-%d") + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            
            df = fetcher.fetch_stock_data(symbol, start_ext, end_ext)
            if df is None or df.empty:
                logger.warning(f"❌ {name}({symbol}) 주가 데이터를 가져오지 못했습니다.")
                continue
                
            buy_date, buy_price = get_closest_price(df, rec_date_str, search_forward=True)
            sell_date, sell_price = get_closest_price(df, end_date_str, search_forward=False)
            
            if buy_price and sell_price:
                ret = (sell_price - buy_price) / buy_price * 100
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "buy_date": buy_date,
                    "buy_price": buy_price,
                    "sell_date": sell_date,
                    "sell_price": sell_price,
                    "return_pct": round(ret, 2)
                })
        return results

    top5_eval = evaluate_symbols(top5_symbols, top5_names)
    top18_eval = evaluate_symbols(top18_symbols, top18_names)
    
    # 수익률 평균 및 지표 계산
    def get_portfolio_summary(eval_list):
        if not eval_list:
            return {}
        returns = [x["return_pct"] for x in eval_list]
        avg_return = sum(returns) / len(returns)
        win_vs_bm = sum(1 for x in returns if x > bm_return)
        win_rate_pct = (win_vs_bm / len(returns)) * 100
        pos_return = sum(1 for x in returns if x > 0)
        pos_rate_pct = (pos_return / len(returns)) * 100
        
        return {
            "avg_return": round(avg_return, 2),
            "alpha": round(avg_return - bm_return, 2),
            "win_rate_vs_benchmark": round(win_rate_pct, 1),
            "win_rate_absolute": round(pos_rate_pct, 1),
            "details": eval_list
        }
        
    top5_summary = get_portfolio_summary(top5_eval)
    top18_summary = get_portfolio_summary(top18_eval)
    
    return {
        "analysis_date": rec_date_str,
        "evaluation_date": end_date_str,
        "benchmark": {
            "name": BENCHMARK_NAME,
            "buy_price": bm_buy_price,
            "sell_price": bm_sell_price,
            "return_pct": round(bm_return, 2)
        },
        "top5_portfolio": top5_summary,
        "top18_portfolio": top18_summary
    }

def run_backtest():
    """전체 과거 데이터 수익률 평가 백테스트를 실행합니다."""
    files = load_analysis_files()
    if not files:
        logger.error("❌ 분석 결과 JSON 파일이 존재하지 않습니다.")
        return
        
    fetcher = StockDataFetcher()
    
    # 최신 영업일 확인
    latest_trading_date = fetcher._get_latest_trading_date()
    end_date_str = datetime.strptime(latest_trading_date, "%Y%m%d").strftime("%Y-%m-%d")
    
    logger.info("=" * 60)
    logger.info("📈 과거 데이터 기반 알고리즘 수익률 백테스트 시작")
    logger.info("=" * 60)
    logger.info(f"검출된 분석 일자 수: {len(files)}개")
    logger.info(f"평가 기준 최종일: {end_date_str}")
    logger.info("=" * 60)
    
    reports = []
    
    for f in files:
        rep = backtest_portfolio(fetcher, f, end_date_str)
        if rep:
            reports.append(rep)
            
    # 전체 백테스트 종합 보고서 생성
    backtest_report_file = Path("output/data/backtest_report.json")
    with open(backtest_report_file, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=4, ensure_ascii=False)
        
    # 콘솔에 마크다운 테이블 형식으로 보고서 출력
    print("\n" + "=" * 80)
    print("🏆 알고리즘 추천 포트폴리오 수익률 성과 보고서 (과거 추천 시점 대비)")
    print("=" * 80)
    print(f"기준일자: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"벤치마크: {BENCHMARK_NAME} (069500)")
    print("=" * 80 + "\n")
    
    for rep in reports:
        print(f"📅 [추천 시점: {rep['analysis_date']}] ➡️ [평가일: {rep['evaluation_date']}] (보유일 약 {(datetime.strptime(rep['evaluation_date'], '%Y-%m-%d') - datetime.strptime(rep['analysis_date'], '%Y-%m-%d')).days}일)")
        print("-" * 80)
        print(f"| 포트폴리오 | 평균 수익률 | 벤치마크 수익률 | 초과수익률 (Alpha) | Win Rate (vs BM) | absolute Win |")
        print(f"|------------|-------------|-----------------|--------------------|------------------|--------------|")
        
        t5 = rep["top5_portfolio"]
        t18 = rep["top18_portfolio"]
        bm_ret = rep["benchmark"]["return_pct"]
        
        if t5:
            print(f"| **Top 5**  | {t5['avg_return']:+6.2f}% | {bm_ret:+6.2f}% | {t5['alpha']:+18.2f}% | {t5['win_rate_vs_benchmark']:15.1f}% | {t5['win_rate_absolute']:11.1f}% |")
        if t18:
            print(f"| **Top 18** | {t18['avg_return']:+6.2f}% | {bm_ret:+6.2f}% | {t18['alpha']:+18.2f}% | {t18['win_rate_vs_benchmark']:15.1f}% | {t18['win_rate_absolute']:11.1f}% |")
            
        print("-" * 80)
        
        # 상세 종목 수익률 출력
        if t5:
            print("  📌 Top 5 추천 개별 종목 성과:")
            for item in t5["details"]:
                print(f"    - {item['name']} ({item['symbol']}): 구매가 {item['buy_price']:,.0f}원 ➡️ 현재가 {item['sell_price']:,.0f}원 (수익률: {item['return_pct']:+6.2f}%)")
        print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    run_backtest()
