export interface RubricScore {
  // V2 기존 카테고리 (하위 호환)
  technical: number;         // 기술적 분석 (25%)
  supply: number;            // 수급 분석 (20%)
  fundamental: number;       // 펀더멘털 분석 (20%)
  market: number;            // 시장 환경 (15%)
  risk: number;              // 리스크 평가 (10%)
  relative_strength: number; // 상대 강도 (10%)

  // V3 8대 핵심 루브릭 (선택적)
  valuation?: number;        // 밸류에이션 (20%)
  momentum?: number;         // 모멘텀 (15%)
  sector?: number;           // 섹터 (10%)
  shareholder?: number;      // 주주환원 (5%)

  total: number;             // 100점 만점 종합 점수
  grade: InvestmentGrade;    // 투자 등급
}

// 투자 등급 타입
export type InvestmentGrade = 'Strong Buy' | 'Buy' | 'Hold' | 'Sell' | 'Strong Sell';

// 투자 등급별 설정 (색상 등)
export const INVESTMENT_GRADES: Record<InvestmentGrade, { min: number; color: string; bgColor: string }> = {
  'Strong Buy': { min: 80, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  'Buy': { min: 60, color: 'text-green-400', bgColor: 'bg-green-500/20' },
  'Hold': { min: 40, color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
  'Sell': { min: 20, color: 'text-orange-400', bgColor: 'bg-orange-500/20' },
  'Strong Sell': { min: 0, color: 'text-red-400', bgColor: 'bg-red-500/20' },
};

// 점수로부터 등급 계산 헬퍼 함수
export function getGradeFromScore(score: number): InvestmentGrade {
  if (score >= 80) return 'Strong Buy';
  if (score >= 60) return 'Buy';
  if (score >= 40) return 'Hold';
  if (score >= 20) return 'Sell';
  return 'Strong Sell';
}

// =============================================================================
// 세부 분석 데이터 타입
// =============================================================================

export interface TechnicalDetails {
  trend?: number;
  rsi?: number;
  support_resistance?: number;
  macd?: number;
  adx?: number;
  // 원본 값
  ma20_value?: number;
  ma60_value?: number;
  rsi_value?: number;
  macd_value?: number;
  macd_signal_value?: number;
  adx_value?: number;
  current_price?: number;
  low_52w?: number;
  high_52w?: number;
  position_52w?: number;
}

export interface SupplyDetails {
  foreign?: number;
  institution?: number;
  trading_value?: number;
  // 원본 값
  foreign_consecutive_days?: number;
  institution_consecutive_days?: number;
  trading_value_amount?: number;
}

export interface FundamentalDetails {
  per?: number;
  pbr?: number;
  roe?: number;
  growth?: number;
  debt?: number;
  // 원본 값
  per_value?: number;
  pbr_value?: number;
  roe_value?: number;
  sector_avg_per?: number;
  sector_avg_pbr?: number;
  op_growth_value?: number;
  debt_ratio_value?: number;
}

export interface MarketDetails {
  news?: number;
  sector_momentum?: number;
  analyst?: number;
}

export interface RiskDetails {
  volatility?: number;
  beta?: number;
  downside_risk?: number;
  // 원본 값
  atr_pct_value?: number;
  beta_value?: number;
  max_drawdown_value?: number;
}

export interface RelativeStrengthDetails {
  sector_rank?: number;
  alpha?: number;
  // 원본 값
  sector_rank_value?: number;
  sector_total_value?: number;
  stock_return_value?: number;
  market_return_value?: number;
  alpha_value?: number;
}

export interface StockAnalysis {
  ticker: string; // e.g., "005930" (if available) or name
  name: string;
  currentPrice?: string;
  sector: string;
  rubric: RubricScore;
  summary: string;
  investmentThesis: string[];
  risks: string[];
  newsSummary: string; // Keep for backward compat, but use detailed below

  // Detailed Report Fields (Markdown)
  financialAnalysis: string; // Detailed Financial Statements & Valuation
  technicalAnalysis: string; // Chart & Price Trend Analysis
  marketSentiment: string;   // News & Market Atmosphere
  comprehensiveAnalysis: string; // Final Verdict

  // 세부 분석 데이터 (백엔드에서 제공)
  technicalDetails?: TechnicalDetails;
  supplyDetails?: SupplyDetails;
  fundamentalDetails?: FundamentalDetails;
  marketDetails?: MarketDetails;
  riskDetails?: RiskDetails;
  relativeStrengthDetails?: RelativeStrengthDetails;

  // 추가 정보
  marketCap?: number;
  rankInGroup?: number;
  high52w?: number;
  low52w?: number;
}

export interface SectorAnalysis {
  name: string;
  reasoning: string;
  topStocks: string[]; // Names of the top 3 stocks in this sector
  weightedScore?: number; // 시가총액 가중 평균 점수
  rank?: number; // 섹터 순위

  // LLM 분석 결과
  outlook?: string;           // 향후 전망
  keyDrivers?: string[];      // 핵심 모멘텀 리스트
  investmentStrategy?: string; // 투자 전략
}

export interface AnalysisReport {
  timestamp: string;
  topSectors: SectorAnalysis[];
  allSectors?: SectorAnalysis[]; // All sectors for chart visualization
  kospiTop10Picks: StockAnalysis[];
  kospiMidPicks: StockAnalysis[]; // 11-20
  kosdaqTop10Picks: StockAnalysis[];
  sectorBestPicks: StockAnalysis[]; // From the top 3 sectors
  finalTop5: StockAnalysis[]; // The absolute best 5 from all 18
  final18: StockAnalysis[]; // All 18 selected stocks
}

export enum AgentStatus {
  IDLE = 'IDLE',
  ANALYZING_SECTORS = 'ANALYZING_SECTORS',
  ANALYZING_KOSPI_10 = 'ANALYZING_KOSPI_10',
  ANALYZING_KOSPI_MID = 'ANALYZING_KOSPI_MID',
  ANALYZING_KOSDAQ = 'ANALYZING_KOSDAQ',
  ANALYZING_SECTOR_STOCKS = 'ANALYZING_SECTOR_STOCKS',
  SYNTHESIZING_FINAL = 'SYNTHESIZING_FINAL',
  COMPLETE = 'COMPLETE',
  ERROR = 'ERROR',
}

export interface AgentProgress {
  status: AgentStatus;
  logs: string[];
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}

export interface SavedReport {
  id: string;
  date: string;
  report: AnalysisReport;
}

// =============================================================================
// 차트 데이터 타입
// =============================================================================

export interface PriceHistoryItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SupplyItem {
  date: string;
  foreign_net: number;      // 외국인 순매수 (억원)
  institution_net: number;  // 기관 순매수 (억원)
}

export interface StockHistoryResponse {
  symbol: string;
  name: string;
  history: PriceHistoryItem[];
}

export interface StockSupplyResponse {
  symbol: string;
  name: string;
  supply: SupplyItem[];
}