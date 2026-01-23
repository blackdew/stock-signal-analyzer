export interface RubricScore {
  technical: number;         // 기술적 분석 (25%)
  supply: number;            // 수급 분석 (20%)
  fundamental: number;       // 펀더멘털 분석 (20%)
  market: number;            // 시장 환경 (15%)
  risk: number;              // 리스크 평가 (10%)
  relative_strength: number; // 상대 강도 (10%)
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
}

export interface SectorAnalysis {
  name: string;
  reasoning: string;
  topStocks: string[]; // Names of the top 3 stocks in this sector
}

export interface AnalysisReport {
  timestamp: string;
  topSectors: SectorAnalysis[];
  kospiTop10Picks: StockAnalysis[];
  kospiMidPicks: StockAnalysis[]; // 11-20
  kosdaqTop10Picks: StockAnalysis[];
  sectorBestPicks: StockAnalysis[]; // From the top 3 sectors
  finalTop3: StockAnalysis[]; // The absolute best 3 from all 18
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