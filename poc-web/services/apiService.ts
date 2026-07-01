/**
 * API Service
 *
 * Python 백엔드 API와 통신하는 서비스.
 * 기존 geminiService.ts를 대체합니다.
 */

import {
  StockAnalysis,
  SectorAnalysis,
  AnalysisReport,
  RubricScore,
  getGradeFromScore,
  InvestmentGrade,
  StockHistoryResponse,
  StockSupplyResponse,
  TechnicalDetails,
  SupplyDetails,
  FundamentalDetails,
  MarketDetails,
  RiskDetails,
  RelativeStrengthDetails,
  SectorFlowResult,
} from '../types';

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
  // V2 점수 (하위 호환)
  technical_score: number;
  supply_score: number;
  fundamental_score: number;
  market_score: number;
  risk_score: number;
  relative_strength_score: number;
  // V3 8대 핵심 루브릭 점수 (선택적)
  valuation_score?: number;
  momentum_score?: number;
  sector_score?: number;
  shareholder_score?: number;
  total_score: number;
  investment_grade: string;
  rank_in_group: number;
  final_rank?: number;
  high_52w?: number;
  low_52w?: number;
  // 세부 분석 정보
  technical_details?: TechnicalDetails;
  supply_details?: SupplyDetails;
  fundamental_details?: FundamentalDetails;
  market_details?: MarketDetails;
  risk_details?: RiskDetails;
  relative_strength_details?: RelativeStrengthDetails;
  // LLM 분석 결과
  summary?: string;
  financial_analysis?: string;
  technical_analysis?: string;
  market_sentiment?: string;
  comprehensive_analysis?: string;
  investment_thesis?: string[];
  risks?: string[];
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

export interface AnalysisHistoryItem {
  date: string;
  generated_at: string;
  preview: string;
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
 * V2(6개 카테고리)와 V3(8대 핵심 루브릭) 모두 지원합니다.
 */
const transformRubric = (backend: BackendStockAnalysis): RubricScore => {
  const grade = getGradeFromScore(backend.total_score);

  return {
    // V2 기존 카테고리 (하위 호환)
    technical: backend.technical_score,
    supply: backend.supply_score,
    fundamental: backend.fundamental_score,
    market: backend.market_score,
    risk: backend.risk_score,
    relative_strength: backend.relative_strength_score,
    // V3 8대 핵심 루브릭 (선택적)
    valuation: backend.valuation_score,
    momentum: backend.momentum_score,
    sector: backend.sector_score,
    shareholder: backend.shareholder_score,
    total: backend.total_score,
    grade: grade,
  };
};

/**
 * 시가총액을 포맷팅합니다.
 */
const formatMarketCap = (marketCap: number): string => {
  if (marketCap >= 10000) {
    return `${(marketCap / 10000).toFixed(1)}조원`;
  }
  return `${marketCap.toLocaleString()}억원`;
};

/**
 * 가격을 포맷팅합니다.
 */
const formatPrice = (price?: number): string => {
  if (!price) return 'N/A';
  return `${price.toLocaleString()}원`;
};

/**
 * 퍼센트를 포맷팅합니다.
 */
const formatPct = (value?: number): string => {
  if (value === undefined || value === null) return 'N/A';
  return `${value.toFixed(1)}%`;
};

/**
 * RSI 판정을 생성합니다.
 */
const getRsiVerdict = (rsi?: number): string => {
  if (!rsi) return '데이터 없음';
  if (rsi >= 70) return '과매수 구간 - 단기 조정 가능성';
  if (rsi >= 60) return '강세 구간';
  if (rsi >= 40) return '중립 구간';
  if (rsi >= 30) return '약세 구간';
  return '과매도 구간 - 반등 가능성';
};

/**
 * 기술적 분석 마크다운을 생성합니다.
 */
const generateTechnicalAnalysis = (backend: BackendStockAnalysis): string => {
  const details = backend.technical_details;
  if (!details) {
    return `기술적 분석 점수: ${backend.technical_score.toFixed(1)}점`;
  }

  const lines: string[] = [];
  lines.push(`**기술적 분석 점수: ${backend.technical_score.toFixed(1)}/25점**\n`);

  // 현재가 및 이동평균
  if (details.current_price) {
    lines.push(`- 현재가: ${formatPrice(details.current_price)}`);
  }
  if (details.ma20_value || details.ma60_value) {
    const ma20 = details.ma20_value ? formatPrice(details.ma20_value) : 'N/A';
    const ma60 = details.ma60_value ? formatPrice(details.ma60_value) : 'N/A';
    lines.push(`- 이동평균: MA20 ${ma20} / MA60 ${ma60}`);
  }

  // 추세 판단
  if (details.ma20_value && details.ma60_value) {
    const trend = details.ma20_value > details.ma60_value ? '상승 추세 (정배열)' : '하락 추세 (역배열)';
    lines.push(`- 추세: ${trend}`);
  }

  // RSI
  if (details.rsi_value) {
    lines.push(`- RSI(14): ${details.rsi_value.toFixed(1)} - ${getRsiVerdict(details.rsi_value)}`);
  }

  // 52주 가격 범위
  if (details.low_52w && details.high_52w) {
    lines.push(`- 52주 범위: ${formatPrice(details.low_52w)} ~ ${formatPrice(details.high_52w)}`);
    if (details.position_52w != null) {
      lines.push(`- 52주 내 위치: ${details.position_52w.toFixed(1)}%`);
    }
  }

  // MACD
  if (details.macd_value != null) {
    const macdSignal = details.macd_signal_value != null ? details.macd_signal_value.toFixed(2) : 'N/A';
    const macdStatus = details.macd_value > (details.macd_signal_value || 0) ? '매수 신호' : '매도 신호';
    lines.push(`- MACD: ${details.macd_value.toFixed(2)} (시그널: ${macdSignal}) - ${macdStatus}`);
  }

  // ADX
  if (details.adx_value) {
    const adxStrength = details.adx_value >= 30 ? '강한 추세' : details.adx_value >= 20 ? '보통 추세' : '약한 추세';
    lines.push(`- ADX: ${details.adx_value.toFixed(1)} - ${adxStrength}`);
  }

  return lines.join('\n');
};

/**
 * 재무 분석 마크다운을 생성합니다.
 */
const generateFinancialAnalysis = (backend: BackendStockAnalysis): string => {
  const details = backend.fundamental_details;
  const lines: string[] = [];

  lines.push(`**펀더멘털 분석 점수: ${backend.fundamental_score.toFixed(1)}/20점**\n`);
  lines.push(`- 시가총액: ${formatMarketCap(backend.market_cap)}`);

  if (!details) {
    return lines.join('\n');
  }

  // PER
  if (details.per_value != null) {
    const perStatus = details.per_value < 0 ? '적자' :
      details.per_value < 10 ? '저평가' :
        details.per_value < 20 ? '적정' : '고평가';
    lines.push(`- PER: ${details.per_value.toFixed(2)}배 (${perStatus})`);
    if (details.sector_avg_per != null) {
      lines.push(`  - 업종 평균: ${details.sector_avg_per.toFixed(2)}배`);
    }
  }

  // PBR
  if (details.pbr_value != null) {
    const pbrStatus = details.pbr_value < 1 ? '저평가' : details.pbr_value < 2 ? '적정' : '고평가';
    lines.push(`- PBR: ${details.pbr_value.toFixed(2)}배 (${pbrStatus})`);
  }

  // ROE
  if (details.roe_value != null) {
    const roeStatus = details.roe_value >= 15 ? '우수' : details.roe_value >= 10 ? '양호' : details.roe_value >= 5 ? '보통' : '미흡';
    lines.push(`- ROE: ${formatPct(details.roe_value)} (${roeStatus})`);
  }

  // 영업이익 성장률
  if (details.op_growth_value != null) {
    const growthStatus = details.op_growth_value >= 20 ? '고성장' :
      details.op_growth_value >= 10 ? '성장' :
        details.op_growth_value >= 0 ? '정체' : '역성장';
    lines.push(`- 영업이익 성장률: ${formatPct(details.op_growth_value)} (${growthStatus})`);
  }

  // 부채비율
  if (details.debt_ratio_value != null) {
    const debtStatus = details.debt_ratio_value <= 50 ? '매우 건전' :
      details.debt_ratio_value <= 100 ? '건전' :
        details.debt_ratio_value <= 200 ? '보통' : '주의';
    lines.push(`- 부채비율: ${formatPct(details.debt_ratio_value)} (${debtStatus})`);
  }

  return lines.join('\n');
};

/**
 * 시장 센티먼트 마크다운을 생성합니다.
 */
const generateMarketSentiment = (backend: BackendStockAnalysis): string => {
  const supplyDetails = backend.supply_details;
  const lines: string[] = [];

  lines.push(`**시장 환경 점수: ${backend.market_score.toFixed(1)}/15점**\n`);
  lines.push(`**수급 분석 점수: ${backend.supply_score.toFixed(1)}/20점**\n`);

  if (supplyDetails) {
    // 외국인 수급
    if (supplyDetails.foreign_consecutive_days != null) {
      const foreignStatus = supplyDetails.foreign_consecutive_days >= 3 ? '강한 매수세' :
        supplyDetails.foreign_consecutive_days >= 1 ? '매수세' : '매도세 또는 관망';
      lines.push(`- 외국인: ${supplyDetails.foreign_consecutive_days}일 연속 순매수 (${foreignStatus})`);
    }

    // 기관 수급
    if (supplyDetails.institution_consecutive_days != null) {
      const instStatus = supplyDetails.institution_consecutive_days >= 3 ? '강한 매수세' :
        supplyDetails.institution_consecutive_days >= 1 ? '매수세' : '매도세 또는 관망';
      lines.push(`- 기관: ${supplyDetails.institution_consecutive_days}일 연속 순매수 (${instStatus})`);
    }

    // 거래대금
    if (supplyDetails.trading_value_amount) {
      lines.push(`- 거래대금: ${supplyDetails.trading_value_amount.toLocaleString()}억원`);
    }
  }

  return lines.join('\n');
};

/**
 * 종합 투자 의견을 생성합니다.
 */
const generateComprehensiveAnalysis = (backend: BackendStockAnalysis): string => {
  const lines: string[] = [];
  const score = backend.total_score;

  // 투자 등급 및 점수
  lines.push(`## 투자 등급: **${backend.investment_grade}**`);
  lines.push(`### 총점: ${score.toFixed(1)}/100점\n`);

  // 강점/약점 분석
  const strengths: string[] = [];
  const weaknesses: string[] = [];

  // 기술적 분석 (25점 만점)
  if (backend.technical_score >= 17.5) {
    strengths.push(`기술적 지표 우수 (${backend.technical_score.toFixed(1)}/25)`);
  } else if (backend.technical_score < 10) {
    weaknesses.push(`기술적 지표 약세 (${backend.technical_score.toFixed(1)}/25)`);
  }

  // 수급 (20점 만점)
  if (backend.supply_score >= 14) {
    strengths.push(`외국인/기관 수급 양호 (${backend.supply_score.toFixed(1)}/20)`);
  } else if (backend.supply_score < 8) {
    weaknesses.push(`수급 부진 (${backend.supply_score.toFixed(1)}/20)`);
  }

  // 펀더멘털 (20점 만점)
  if (backend.fundamental_score >= 14) {
    strengths.push(`펀더멘털 우수 (${backend.fundamental_score.toFixed(1)}/20)`);
  } else if (backend.fundamental_score < 8) {
    weaknesses.push(`펀더멘털 미흡 (${backend.fundamental_score.toFixed(1)}/20)`);
  }

  // 리스크 (10점 만점)
  if (backend.risk_score >= 7) {
    strengths.push(`리스크 낮음 (${backend.risk_score.toFixed(1)}/10)`);
  } else if (backend.risk_score < 4) {
    weaknesses.push(`리스크 높음 (${backend.risk_score.toFixed(1)}/10)`);
  }

  if (strengths.length > 0) {
    lines.push(`**강점**`);
    strengths.forEach(s => lines.push(`- ${s}`));
    lines.push('');
  }

  if (weaknesses.length > 0) {
    lines.push(`**약점**`);
    weaknesses.forEach(w => lines.push(`- ${w}`));
    lines.push('');
  }

  // 권고사항
  if (score >= 70) {
    lines.push(`**권고**: 분할 매수 전략으로 포지션 구축을 고려해 볼 수 있습니다.`);
  } else if (score >= 50) {
    lines.push(`**권고**: 추세 전환 신호를 확인한 후 진입을 검토하시기 바랍니다.`);
  } else {
    lines.push(`**권고**: 신규 진입은 자제하고, 기존 보유자는 비중 축소를 고려해야 합니다.`);
  }

  return lines.join('\n');
};

/**
 * 리스크 요인을 생성합니다.
 */
const generateRisks = (backend: BackendStockAnalysis): string[] => {
  const risks: string[] = [];
  const riskDetails = backend.risk_details;

  if (backend.risk_score < 5) {
    risks.push('리스크 점수가 낮아 변동성 주의 필요');
  }

  if (riskDetails) {
    // 변동성
    if (riskDetails.atr_pct_value && riskDetails.atr_pct_value > 5) {
      risks.push(`높은 변동성 (ATR ${riskDetails.atr_pct_value.toFixed(1)}%)`);
    }

    // 베타
    if (riskDetails.beta_value && riskDetails.beta_value > 1.5) {
      risks.push(`시장 대비 높은 민감도 (베타 ${riskDetails.beta_value.toFixed(2)})`);
    }

    // 최대 낙폭
    if (riskDetails.max_drawdown_value && riskDetails.max_drawdown_value > 20) {
      risks.push(`최근 큰 낙폭 발생 (${riskDetails.max_drawdown_value.toFixed(1)}%)`);
    }
  }

  // 펀더멘털 리스크
  const fundDetails = backend.fundamental_details;
  if (fundDetails) {
    if (fundDetails.per_value && fundDetails.per_value < 0) {
      risks.push('적자 기업');
    }
    if (fundDetails.debt_ratio_value && fundDetails.debt_ratio_value > 200) {
      risks.push(`높은 부채비율 (${fundDetails.debt_ratio_value.toFixed(0)}%)`);
    }
  }

  // 기술적 리스크
  const techDetails = backend.technical_details;
  if (techDetails) {
    if (techDetails.rsi_value && techDetails.rsi_value > 70) {
      risks.push('과매수 구간 - 단기 조정 가능성');
    }
    if (techDetails.position_52w && techDetails.position_52w > 90) {
      risks.push('52주 최고가 근접 - 상승 여력 제한');
    }
  }

  return risks.length > 0 ? risks : ['특별한 리스크 요인 없음'];
};

/**
 * 백엔드 종목 분석 결과를 프론트엔드 타입으로 변환합니다.
 * LLM 분석 결과가 있으면 우선 사용하고, 없으면 템플릿으로 생성합니다.
 */
const transformStock = (backend: BackendStockAnalysis): StockAnalysis => ({
  ticker: backend.symbol,
  name: backend.name,
  currentPrice: backend.technical_details?.current_price
    ? formatPrice(backend.technical_details.current_price)
    : '',
  sector: backend.sector,
  // LLM 요약이 있으면 사용, 없으면 기본 템플릿
  summary: backend.summary || `${backend.investment_grade} 등급 (총점: ${backend.total_score.toFixed(1)}점)`,
  // LLM 투자 포인트가 있으면 사용, 없으면 기본 템플릿
  investmentThesis: backend.investment_thesis && backend.investment_thesis.length > 0
    ? backend.investment_thesis
    : [
        `기술적 분석: ${backend.technical_score.toFixed(1)}/25점`,
        `수급 분석: ${backend.supply_score.toFixed(1)}/20점`,
        `펀더멘털: ${backend.fundamental_score.toFixed(1)}/20점`,
        `시장 환경: ${backend.market_score.toFixed(1)}/15점`,
        `리스크: ${backend.risk_score.toFixed(1)}/10점`,
      ],
  // LLM 리스크가 있으면 사용, 없으면 템플릿으로 생성
  risks: backend.risks && backend.risks.length > 0 ? backend.risks : generateRisks(backend),
  newsSummary: '',
  // LLM 분석이 있으면 사용, 없으면 템플릿으로 생성
  financialAnalysis: backend.financial_analysis || generateFinancialAnalysis(backend),
  technicalAnalysis: backend.technical_analysis || generateTechnicalAnalysis(backend),
  marketSentiment: backend.market_sentiment || generateMarketSentiment(backend),
  comprehensiveAnalysis: backend.comprehensive_analysis || generateComprehensiveAnalysis(backend),
  rubric: transformRubric(backend),
  // 세부 분석 데이터
  technicalDetails: backend.technical_details,
  supplyDetails: backend.supply_details,
  fundamentalDetails: backend.fundamental_details,
  marketDetails: backend.market_details,
  riskDetails: backend.risk_details,
  relativeStrengthDetails: backend.relative_strength_details,
  // 추가 정보
  marketCap: backend.market_cap,
  rankInGroup: backend.rank_in_group,
  high52w: backend.high_52w || backend.technical_details?.high_52w,
  low52w: backend.low_52w || backend.technical_details?.low_52w,
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
 * 현재 실행 중인 분석 태스크가 있는지 조회합니다.
 */
export const getRunningAnalysis = async (): Promise<{ task_id: string | null; status: 'running' | 'idle'; message?: string }> => {
  const response = await fetch(`${API_BASE}/api/analysis/running`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
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
 * 분석 히스토리 목록을 조회합니다.
 */
export const getAnalysisHistory = async (): Promise<AnalysisHistoryItem[]> => {
  const response = await fetch(`${API_BASE}/api/analysis/history`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};

/**
 * 특정 날짜의 분석 결과를 조회합니다.
 */
export const getAnalysisByDate = async (date: string): Promise<AnalysisReport> => {
  const response = await fetch(`${API_BASE}/api/analysis/${date}`);

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
  timeoutMs: number = 7200000, // 2시간 타임아웃 (GPT-5.2 모델 사용 시 더 오래 걸림)
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

// =============================================================================
// 차트 데이터 API
// =============================================================================

/**
 * 종목의 주가 히스토리를 조회합니다.
 */
export const getStockHistory = async (
  symbol: string,
  days: number = 60
): Promise<StockHistoryResponse> => {
  const response = await fetch(`${API_BASE}/api/stocks/${symbol}/history?days=${days}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};

/**
 * 종목의 수급 데이터를 조회합니다.
 */
export const getStockSupply = async (
  symbol: string,
  days: number = 20
): Promise<StockSupplyResponse> => {
  const response = await fetch(`${API_BASE}/api/stocks/${symbol}/supply?days=${days}`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};

// =============================================================================
// SSE 로그 스트리밍
// =============================================================================

export interface TaskLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface TaskStatusEvent {
  type: 'status';
  status: 'completed' | 'failed';
  message: string;
}

/**
 * 분석 태스크 로그를 SSE로 구독합니다.
 *
 * @param taskId 태스크 ID
 * @param onLog 로그 메시지 콜백
 * @param onStatus 상태 변경 콜백 (완료/실패)
 * @param onError 에러 콜백
 * @returns 구독 취소 함수
 */
export const subscribeToTaskLogs = (
  taskId: string,
  onLog: (log: TaskLogEntry) => void,
  onStatus?: (event: TaskStatusEvent) => void,
  onError?: (error: Error) => void,
): (() => void) => {
  const url = `${API_BASE}/api/analysis/task/${taskId}/logs`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as TaskLogEntry;
      onLog(data);
    } catch (e) {
      console.error('Failed to parse log entry:', e);
    }
  };

  eventSource.addEventListener('status', (event) => {
    try {
      const data = JSON.parse((event as MessageEvent).data) as TaskStatusEvent;
      onStatus?.(data);
      // 상태 이벤트 수신 후 연결 종료
      eventSource.close();
    } catch (e) {
      console.error('Failed to parse status event:', e);
    }
  });

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    onError?.(new Error('SSE 연결 오류가 발생했습니다.'));
    eventSource.close();
  };

  // 구독 취소 함수 반환
  return () => {
    eventSource.close();
  };
};

/**
 * 13개 섹터의 자금 흐름(Money Flow) 및 RRG 좌표를 조회합니다.
 */
export const getSectorsFlow = async (): Promise<SectorFlowResult[]> => {
  const response = await fetch(`${API_BASE}/api/sectors/flow`);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json();
};
