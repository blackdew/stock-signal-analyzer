export interface RubricScore {
  technical: number;        // 1. Technical Analysis (10%)
  supplyDemand: number;     // 2. Supply/Demand (15%)
  fundamentals: number;     // 3. Fundamentals (Revenue/Profit) (15%)
  valuation: number;        // 4. Valuation (Price Level) (20%)
  momentum: number;         // 5. Momentum/Catalyst (15%)
  sector: number;           // 6. Sector Sentiment (10%)
  shareholder: number;      // 7. Shareholder Return (5%)
  risk: number;             // 8. Risk Management (10%)
  total: number;            // Weighted Score out of 100
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