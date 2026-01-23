/**
 * API Service
 *
 * Python 백엔드 API와 통신하는 서비스.
 * 기존 geminiService.ts를 대체합니다.
 */

import { StockAnalysis, SectorAnalysis, AnalysisReport, RubricScore, getGradeFromScore, InvestmentGrade } from '../types';

// API Base URL from environment variable
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// =============================================================================
// Backend API Types
// =============================================================================

interface BackendStockAnalysis {
  symbol: string;
  name: string;
  sector: string;
  group: string;
  market_cap: number;
  technical_score: number;
  supply_score: number;
  fundamental_score: number;
  market_score: number;
  risk_score: number;
  relative_strength_score: number;
  total_score: number;
  investment_grade: string;
  rank_in_group: number;
  final_rank?: number;
}

interface BackendSectorAnalysis {
  sector_name: string;
  stock_count: number;
  total_market_cap: number;
  weighted_score: number;
  simple_score: number;
  technical_score: number;
  supply_score: number;
  fundamental_score: number;
  market_score: number;
  top_stocks: BackendStockAnalysis[];
  rank: number;
}

interface BackendRanking {
  kospi_top10: BackendStockAnalysis[];
  kospi_11_20: BackendStockAnalysis[];
  kosdaq_top10: BackendStockAnalysis[];
  sector_top: BackendStockAnalysis[];
  final_18: BackendStockAnalysis[];
  final_top5: BackendStockAnalysis[];
  top_sectors: BackendSectorAnalysis[];
}

interface BackendAnalysisResult {
  generated_at: string;
  ranking?: BackendRanking;
  sectors?: BackendSectorAnalysis[];
  report_paths: Record<string, string>;
  stats: {
    total_time: number;
    phases: Record<string, unknown>;
    final_stocks?: number;
    final_top5?: unknown[];
  };
}

interface AnalysisTaskResponse {
  task_id: string;
  status: 'running' | 'completed' | 'failed' | 'unknown';
  message?: string;
}

interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// Transform Functions
// =============================================================================

/**
 * 백엔드 종목 분석 결과를 프론트엔드 RubricScore로 변환합니다.
 * 백엔드와 프론트엔드 타입이 이제 동일한 6개 카테고리를 사용합니다.
 */
const transformRubric = (backend: BackendStockAnalysis): RubricScore => {
  const grade = getGradeFromScore(backend.total_score);

  return {
    technical: backend.technical_score,
    supply: backend.supply_score,
    fundamental: backend.fundamental_score,
    market: backend.market_score,
    risk: backend.risk_score,
    relative_strength: backend.relative_strength_score,
    total: backend.total_score,
    grade: grade,
  };
};

/**
 * 백엔드 종목 분석 결과를 프론트엔드 타입으로 변환합니다.
 */
const transformStock = (backend: BackendStockAnalysis): StockAnalysis => ({
  ticker: backend.symbol,
  name: backend.name,
  currentPrice: '', // 백엔드에서 제공하지 않음
  sector: backend.sector,
  summary: `${backend.investment_grade} 등급 (총점: ${backend.total_score}점)`,
  investmentThesis: [
    `기술적 분석 점수: ${backend.technical_score.toFixed(1)}점`,
    `수급 분석 점수: ${backend.supply_score.toFixed(1)}점`,
    `펀더멘털 분석 점수: ${backend.fundamental_score.toFixed(1)}점`,
  ],
  risks: backend.risk_score < 5
    ? ['리스크 점수가 낮아 변동성 주의 필요']
    : [],
  newsSummary: '',
  financialAnalysis: `시가총액: ${(backend.market_cap / 10000).toFixed(0)}조원`,
  technicalAnalysis: `기술적 분석 점수: ${backend.technical_score.toFixed(1)}점 / 그룹 내 ${backend.rank_in_group}위`,
  marketSentiment: `시장 환경 점수: ${backend.market_score.toFixed(1)}점`,
  comprehensiveAnalysis: `투자 등급: **${backend.investment_grade}**\n\n총점 ${backend.total_score.toFixed(1)}점으로 ${backend.sector} 섹터 내 유망 종목입니다.`,
  rubric: transformRubric(backend),
});

/**
 * 백엔드 섹터 분석 결과를 프론트엔드 타입으로 변환합니다.
 */
const transformSector = (backend: BackendSectorAnalysis): SectorAnalysis => ({
  name: backend.sector_name,
  reasoning: `가중 평균 점수: ${backend.weighted_score.toFixed(1)}점 / 단순 평균: ${backend.simple_score.toFixed(1)}점 / 총 시가총액: ${(backend.total_market_cap / 10000).toFixed(1)}조원`,
  topStocks: backend.top_stocks.map(s => s.name),
  weightedScore: backend.weighted_score,
  rank: backend.rank,
});

/**
 * 백엔드 분석 결과를 프론트엔드 AnalysisReport로 변환합니다.
 */
const transformToReport = (backend: BackendAnalysisResult): AnalysisReport => {
  const ranking = backend.ranking;

  if (!ranking) {
    throw new Error('순위 데이터가 없습니다.');
  }

  // Top 3 섹터 추출
  const topSectors = ranking.top_sectors
    .slice(0, 3)
    .map(transformSector);

  // KOSPI Top 10에서 상위 3개 선정
  const kospiTop10Picks = ranking.kospi_top10
    .slice(0, 3)
    .map(transformStock);

  // KOSPI 11-20에서 상위 3개 선정
  const kospiMidPicks = ranking.kospi_11_20
    .slice(0, 3)
    .map(transformStock);

  // KOSDAQ Top 10에서 상위 3개 선정
  const kosdaqTop10Picks = ranking.kosdaq_top10
    .slice(0, 3)
    .map(transformStock);

  // 섹터별 상위 종목
  const sectorBestPicks = ranking.sector_top
    .slice(0, 9)
    .map(transformStock);

  // 최종 Top 5 선정
  const finalTop5 = ranking.final_top5
    .slice(0, 5)
    .map(transformStock);

  // 최종 18개 종목
  const final18 = ranking.final_18
    .map(transformStock);

  // 전체 섹터 (차트 시각화용)
  const allSectors = ranking.top_sectors
    .map(transformSector);

  return {
    timestamp: backend.generated_at,
    topSectors,
    allSectors,
    kospiTop10Picks,
    kospiMidPicks,
    kosdaqTop10Picks,
    sectorBestPicks,
    finalTop5,
    final18,
  };
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * API 에러 처리 헬퍼
 */
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

  try {
    const errorBody: ErrorResponse = await response.json();
    errorMessage = errorBody.message || errorBody.error || errorMessage;
  } catch {
    // JSON 파싱 실패 시 기본 메시지 사용
  }

  throw new Error(errorMessage);
};

/**
 * 최신 분석 결과를 조회합니다.
 */
export const getLatestAnalysis = async (): Promise<AnalysisReport> => {
  const response = await fetch(`${API_BASE}/api/analysis/latest`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data: BackendAnalysisResult = await response.json();
  return transformToReport(data);
};

/**
 * 분석을 비동기로 실행합니다.
 */
export const runAnalysis = async (options?: {
  mode?: 'daily' | 'weekly';
  use_cache?: boolean;
}): Promise<AnalysisTaskResponse> => {
  const response = await fetch(`${API_BASE}/api/analysis/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mode: options?.mode || 'daily',
      use_cache: options?.use_cache ?? true,
    }),
  });

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};

/**
 * 분석 태스크 상태를 조회합니다.
 */
export const getAnalysisTaskStatus = async (taskId: string): Promise<AnalysisTaskResponse> => {
  const response = await fetch(`${API_BASE}/api/analysis/task/${taskId}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};

/**
 * 분석 태스크 완료까지 폴링합니다.
 */
export const pollAnalysisTask = async (
  taskId: string,
  onProgress?: (status: string, message?: string) => void,
  intervalMs: number = 2000,
  timeoutMs: number = 300000, // 5분 타임아웃
): Promise<AnalysisReport> => {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const task = await getAnalysisTaskStatus(taskId);

    if (task.status === 'completed') {
      return await getLatestAnalysis();
    }

    if (task.status === 'failed') {
      throw new Error(task.message || '분석이 실패했습니다.');
    }

    onProgress?.(task.status, task.message);

    // 대기
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }

  throw new Error('분석 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.');
};

/**
 * 순위 결과를 조회합니다.
 */
export const getRanking = async (): Promise<AnalysisReport> => {
  const response = await fetch(`${API_BASE}/api/ranking`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data: BackendRanking = await response.json();

  // BackendAnalysisResult 형태로 래핑하여 변환
  return transformToReport({
    generated_at: new Date().toISOString(),
    ranking: data,
    report_paths: {},
    stats: { total_time: 0, phases: {} },
  });
};

/**
 * 섹터 목록을 조회합니다.
 */
export const getSectors = async (): Promise<SectorAnalysis[]> => {
  const response = await fetch(`${API_BASE}/api/sectors`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data = await response.json();
  return data.sectors.map(transformSector);
};

/**
 * 특정 섹터의 상세 정보를 조회합니다.
 */
export const getSectorDetail = async (sectorName: string): Promise<SectorAnalysis> => {
  const response = await fetch(`${API_BASE}/api/sectors/${encodeURIComponent(sectorName)}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data: BackendSectorAnalysis = await response.json();
  return transformSector(data);
};

/**
 * 특정 종목의 상세 정보를 조회합니다.
 */
export const getStockDetail = async (symbol: string): Promise<StockAnalysis> => {
  const response = await fetch(`${API_BASE}/api/stocks/${encodeURIComponent(symbol)}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data: BackendStockAnalysis = await response.json();
  return transformStock(data);
};

/**
 * 상위 N개 종목을 조회합니다.
 */
export const getTopStocks = async (n: number = 5): Promise<StockAnalysis[]> => {
  const response = await fetch(`${API_BASE}/api/stocks/top/${n}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  const data = await response.json();
  return data.stocks.map(transformStock);
};
