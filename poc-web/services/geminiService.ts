import { GoogleGenAI, Type, Schema } from "@google/genai";
import { StockAnalysis, SectorAnalysis, AnalysisReport } from "../types";

// Helper to validate API Key
const getAIClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API Key is missing. Please select a paid API key using the button.");
  }
  return new GoogleGenAI({ apiKey });
};

// --- Schemas for structured output ---

const rubricSchema: Schema = {
  type: Type.OBJECT,
  properties: {
    technical: { type: Type.NUMBER, description: "Score 1-10: Chart trend, moving averages" },
    supplyDemand: { type: Type.NUMBER, description: "Score 1-10: Institutional/Foreigner net buying" },
    fundamentals: { type: Type.NUMBER, description: "Score 1-10: Revenue growth, OP margin, ROE" },
    valuation: { type: Type.NUMBER, description: "Score 1-10: PER/PBR relative to history/peers. Higher score = More undervalued/Attractive." },
    momentum: { type: Type.NUMBER, description: "Score 1-10: News, catalysts, future contracts" },
    sector: { type: Type.NUMBER, description: "Score 1-10: Industry growth potential" },
    shareholder: { type: Type.NUMBER, description: "Score 1-10: Dividends, buybacks, Value-up policies" },
    risk: { type: Type.NUMBER, description: "Score 1-10: Stability, governance, low debt (Higher score = Lower risk)" },
    total: { type: Type.NUMBER, description: "Weighted Total Score out of 100 based on the 8 criteria weights" },
  },
  required: ["technical", "supplyDemand", "fundamentals", "valuation", "momentum", "sector", "shareholder", "risk", "total"],
};

const stockAnalysisSchema: Schema = {
  type: Type.OBJECT,
  properties: {
    name: { type: Type.STRING },
    ticker: { type: Type.STRING, description: "Stock code if known, else empty" },
    sector: { type: Type.STRING },
    currentPrice: { type: Type.STRING, description: "Latest known price with currency (KRW)" },
    summary: { type: Type.STRING, description: "One sentence summary in Korean" },
    investmentThesis: { type: Type.ARRAY, items: { type: Type.STRING }, description: "3 key reasons to buy in Korean" },
    risks: { type: Type.ARRAY, items: { type: Type.STRING }, description: "Major risk factors in Korean" },
    
    // Detailed Fields
    financialAnalysis: { type: Type.STRING, description: "Detailed analysis of Financial Statements (PER, PBR, Revenue, OP trends) in Markdown format. Be precise with numbers." },
    technicalAnalysis: { type: Type.STRING, description: "Detailed Technical Analysis (Moving Averages, RSI, Support/Resistance lines) in Markdown format." },
    marketSentiment: { type: Type.STRING, description: "Recent News, Rumors, and Market Sentiment Analysis in Markdown format." },
    comprehensiveAnalysis: { type: Type.STRING, description: "Final Synthesis and Strategy verdict in Markdown format." },
    
    newsSummary: { type: Type.STRING, description: "Short news summary" },
    rubric: rubricSchema,
  },
  required: ["name", "sector", "summary", "rubric", "investmentThesis", "financialAnalysis", "technicalAnalysis", "marketSentiment", "comprehensiveAnalysis"],
};

const sectorSchema: Schema = {
  type: Type.OBJECT,
  properties: {
    name: { type: Type.STRING },
    reasoning: { type: Type.STRING, description: "Why this sector is promising now (in Korean)" },
    topStocks: { type: Type.ARRAY, items: { type: Type.STRING }, description: "Names of 3 top stocks in this sector" },
  },
  required: ["name", "reasoning", "topStocks"],
};

const rubricInstruction = `
    [8대 평가 루브릭 및 가중치 적용]
    각 항목은 1~10점 척도로 평가하고, 아래 가중치를 반영하여 총점(Total Score, 100점 만점)을 계산하십시오.
    
    1. 밸류에이션 (Valuation): 20% (가장 중요. 현재 주가가 저평가 상태인가? 부담스러운 수준이면 점수 차감)
    2. 수급 (Supply/Demand): 15% (기관/외인 매수세)
    3. 펀더멘털 (Fundamentals): 15% (매출/이익 성장성, 수익성)
    4. 모멘텀 (Momentum): 15% (강력한 호재, 계약, 미래 기대감)
    5. 기술적 분석 (Technical): 10% (차트 추세, 정배열 여부)
    6. 섹터 매력도 (Sector): 10% (산업 업황, 주도 테마 여부)
    7. 리스크 관리 (Risk): 10% (재무 안정성, 오버행, 오너 리스크. 리스크가 낮을수록 높은 점수)
    8. 주주 환원 (Shareholder): 5% (배당, 자사주 소각 등 밸류업 노력)
    
    Total Score = (Valuation*2 + Supply*1.5 + Fundamentals*1.5 + Momentum*1.5 + Technical*1 + Sector*1 + Risk*1 + Shareholder*0.5)
`;

// Shared instruction for stability
const strictConsistencyInstruction = `
    [분석 일관성 원칙]
    같은 기업에 대한 분석은 언제나 일관되어야 합니다.
    실제 최신 시장 데이터를 기반으로 분석하되, 기업의 본질적 가치(Fundamental)와 시장의 위치(Position)는 
    섹터 관점이든 시총 관점이든 동일하게 해석되어야 합니다.
    할루시네이션(거짓 정보)을 피하고, 구체적인 수치(PER, PBR, 영업이익률 등)를 제시하십시오.
    작성된 내용은 Markdown 포맷을 사용하여 가독성을 높여야 합니다 (볼드체, 리스트 등 활용).
`;

// --- Sub-Agent Functions ---

// 1. Sector Analyst Agent
export const analyzeSectors = async (): Promise<SectorAnalysis[]> => {
  const ai = getAIClient();
  const prompt = `
    현재 한국 주식 시장(KOSPI, KOSDAQ)의 트렌드를 분석하십시오. 
    반도체, 조선, 방산, 원전, 전력기기, 바이오, 로봇, 자동차, 신재생에너지, 지주사, 뷰티, 금융 등 주요 섹터를 비교 분석하십시오.
    시장 모멘텀, 정부 정책(밸류업 등), 글로벌 트렌드를 바탕으로 지금 당장 투자 기회가 가장 높은 상위 3개 섹터를 선정하십시오.
    각 섹터별로 대장주(leading stocks) 3개를 선정하여 리스트업하십시오.
    모든 응답은 반드시 '한국어'로 작성되어야 합니다.
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: prompt,
    config: {
      tools: [{ googleSearch: {} }],
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: sectorSchema,
      },
    },
  });

  return JSON.parse(response.text || "[]");
};

// 2. Market Cap Group Analyst
export const analyzeMarketGroup = async (groupDescription: string): Promise<StockAnalysis[]> => {
  const ai = getAIClient();
  const prompt = `
    전문 펀드 매니저로서 행동하십시오.
    먼저 ${groupDescription}에 해당하는 기업 순위를 최신 데이터로 파악하십시오 (한국 시장 기준).
    그 후, 해당 기업들을 정밀 분석하여 투자 전망이 밝은 상위 3개 종목을 선정하십시오.
    
    ${strictConsistencyInstruction}
    ${rubricInstruction}
    
    [상세 리포트 작성 요구사항]
    - financialAnalysis: 재무재표(매출, 영업이익, PER, PBR) 추이와 적정 주가 분석 (Markdown)
    - technicalAnalysis: 주요 이동평균선, 지지/저항 라인, 거래량 분석 (Markdown)
    - marketSentiment: 뉴스 헤드라인, 공시, 시장 소문 및 수급 동향 (Markdown)
    - comprehensiveAnalysis: 위 내용을 종합한 최종 매수/매도 전략 및 목표가 제시 (Markdown)

    선정된 3개 종목에 대해 위 요구사항을 포함한 상세 리포트를 작성하십시오.
    모든 내용은 반드시 '한국어'로 작성되어야 합니다.
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: prompt,
    config: {
      tools: [{ googleSearch: {} }],
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: stockAnalysisSchema,
      },
    },
  });

  return JSON.parse(response.text || "[]");
};

// 3. Sector Deep Dive Analyst
export const analyzeSectorSpecificStocks = async (sectors: SectorAnalysis[]): Promise<StockAnalysis[]> => {
  const ai = getAIClient();
  const sectorNames = sectors.map(s => s.name).join(", ");
  const stockContext = sectors.map(s => `${s.name}: ${s.topStocks.join(', ')}`).join("; ");
  
  const prompt = `
    다음 유망 섹터들에 집중하십시오: ${sectorNames}.
    특히 다음 종목들을 심층 분석하십시오: ${stockContext}.
    각 섹터별로 최고의 종목들을 선정하여 분석하십시오 (섹터당 3개, 총 9개 종목).
    
    ${strictConsistencyInstruction}
    ${rubricInstruction}
    
    [상세 리포트 작성 요구사항]
    - financialAnalysis: 재무재표, 밸류에이션, 성장성 지표 정밀 분석 (Markdown)
    - technicalAnalysis: 차트 패턴, 추세선, 골든크로스 등 기술적 지표 (Markdown)
    - marketSentiment: 섹터 내 경쟁 현황, 관련 뉴스, 수급 주체 분석 (Markdown)
    - comprehensiveAnalysis: 섹터 모멘텀과 결합된 최종 투자 의견 (Markdown)
    
    모든 내용은 반드시 '한국어'로 작성되어야 합니다.
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: prompt,
    config: {
      tools: [{ googleSearch: {} }],
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: stockAnalysisSchema,
      },
    },
  });

  return JSON.parse(response.text || "[]");
};

// 4. Final Evaluator Agent
export const selectFinalTop3 = async (allStocks: StockAnalysis[]): Promise<StockAnalysis[]> => {
  const ai = getAIClient();
  // Pass minimal info to save context window, but include rubric breakdown
  const candidates = JSON.stringify(allStocks.map(s => ({ 
      name: s.name, 
      rubric: s.rubric, 
      sector: s.sector 
  })));
  
  const prompt = `
    당신은 최고 투자 책임자(CIO)입니다.
    다음은 하위 에이전트들이 선별한 18개의 후보 종목 리스트입니다:
    ${candidates}
    
    잠재 수익률과 안정성이 가장 높은 절대적인 TOP 3 종목을 최종 선정하십시오.
    
    [판단 기준]
    - 총점(Total Score)가 높은 순으로 고려하되, 포트폴리오의 섹터 분산을 고려하십시오.
    - 밸류에이션 부담이 적고 실적 성장이 확실한 종목을 우선하십시오.
    
    선정된 3개 종목에 대해 기존 분석 데이터(재무, 차트, 뉴스 등)를 더욱 보강하여 
    최종 투자 리포트를 완성하십시오. 내용은 Markdown 형식으로 매우 구체적이어야 합니다.
    모든 내용은 반드시 '한국어'로 작성되어야 합니다.
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: stockAnalysisSchema,
      },
    },
  });

  return JSON.parse(response.text || "[]");
};

// 5. Chat with Analyst
export const chatWithAnalyst = async (report: AnalysisReport, userMessage: string, chatHistory: any[]): Promise<string> => {
  const ai = getAIClient();
  
  const systemContext = `
    당신은 AlphaInvest의 수석 투자 분석가 AI입니다.
    사용자가 생성한 최신 시장 분석 리포트를 바탕으로 답변해야 합니다.
    답변 형식은 가독성이 좋은 **Markdown**을 사용하십시오.
    
    [리포트 요약]
    - 유망 섹터: ${report.topSectors?.map(s => s.name).join(', ')}
    - 최종 Top 3 추천주: ${report.finalTop3?.map(s => s.name).join(', ')}
    
    사용자의 질문에 대해 리포트의 상세 데이터(재무, 차트, 수급, 8대 루브릭 점수 등)를 인용하여 논리적으로 설명하십시오.
    답변은 친절하고 전문적인 '한국어'로 하십시오.
  `;

  const fullPrompt = `
    ${systemContext}

    [이전 대화]
    ${chatHistory.map(m => `${m.role === 'user' ? '사용자' : '분석가'}: ${m.text}`).join('\n')}

    사용자 질문: ${userMessage}
    분석가 답변:
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: fullPrompt
  });

  return response.text || "죄송합니다. 답변을 생성할 수 없습니다.";
};