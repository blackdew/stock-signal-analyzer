import React, { useState, useEffect, useRef } from 'react';
import {
  Briefcase,
  TrendingUp,
  BarChart2,
  Zap,
  LayoutDashboard,
  PlayCircle,
  CheckCircle2,
  Loader2,
  Key,
  MessageSquare,
  Save,
  Download,
  History,
  Trash2,
  FileText,
  List,
  Award,
  Menu,
  X
} from 'lucide-react';
import { 
  AgentStatus, 
  AnalysisReport, 
  StockAnalysis,
  SavedReport
} from './types';
import * as ApiService from './services/apiService';
import { AnalysisHistoryItem } from './services/apiService';
import StockCard from './components/StockCard';
import StockModal from './components/StockModal';
import ChatSidebar from './components/ChatSidebar';
import SectorBarChart from './components/SectorBarChart';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import ReactMarkdown from 'react-markdown';

const App = () => {
  const [apiKeySet, setApiKeySet] = useState(false);
  const [status, setStatus] = useState<AgentStatus>(AgentStatus.IDLE);
  const [logs, setLogs] = useState<string[]>([]);
  const [report, setReport] = useState<Partial<AnalysisReport>>({});
  const [selectedStock, setSelectedStock] = useState<StockAnalysis | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'sectors' | 'kospi10' | 'kospiMid' | 'kosdaq' | 'all18' | 'final'>('overview');
  
  // New State Features
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [savedReports, setSavedReports] = useState<SavedReport[]>([]);

  // Server Analysis History
  const [serverHistory, setServerHistory] = useState<AnalysisHistoryItem[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  // References
  const logEndRef = useRef<HTMLDivElement>(null);
  const fullReportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Load Saved Reports
  useEffect(() => {
    const saved = localStorage.getItem('alphaInvest_reports');
    if (saved) {
      try {
        setSavedReports(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }
  }, []);

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const checkBackendHealth = async () => {
    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      if (response.ok) {
        setApiKeySet(true);
        return;
      }
    } catch {
      // 백엔드 연결 실패 시 Gemini API 키 확인 (폴백)
    }

    // 폴백: 기존 AI Studio API 키 체크
    if (window.aistudio && window.aistudio.hasSelectedApiKey) {
      const hasKey = await window.aistudio.hasSelectedApiKey();
      setApiKeySet(hasKey);
    } else if (process.env.API_KEY) {
      setApiKeySet(true);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  // 페이지 로드 시 서버 히스토리 및 최신 분석 결과 자동 로드
  useEffect(() => {
    const loadInitialData = async () => {
      if (!apiKeySet) return;

      setIsLoadingHistory(true);
      try {
        // 서버 히스토리 로드
        const history = await ApiService.getAnalysisHistory();
        setServerHistory(history);

        // 최신 분석 결과 로드 (히스토리가 있는 경우)
        if (history.length > 0) {
          addLog("기존 분석 결과를 불러오는 중...");
          const latestReport = await ApiService.getLatestAnalysis();
          setReport(latestReport);
          setSelectedDate(history[0].date);
          setStatus(AgentStatus.COMPLETE);
          setActiveTab('final');
          addLog("최신 분석 결과를 불러왔습니다.");
        }
      } catch (error: any) {
        console.error("초기 데이터 로드 실패:", error);
        // 분석 결과가 없으면 조용히 실패 (새로운 분석 시작 가능)
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadInitialData();
  }, [apiKeySet]);

  const handleSelectKey = async () => {
    // 먼저 백엔드 헬스 체크 재시도
    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      if (response.ok) {
        setApiKeySet(true);
        return;
      }
    } catch {
      // 백엔드 연결 실패
    }

    // AI Studio API 키 선택 (폴백)
    if (window.aistudio && window.aistudio.openSelectKey) {
      await window.aistudio.openSelectKey();
      setApiKeySet(true);
    }
  };

  const saveCurrentReport = (currentReport: AnalysisReport) => {
      const newSavedReport: SavedReport = {
          id: Date.now().toString(),
          date: new Date().toLocaleString('ko-KR'),
          report: currentReport
      };
      const updated = [newSavedReport, ...savedReports].slice(0, 10); // Keep last 10
      setSavedReports(updated);
      localStorage.setItem('alphaInvest_reports', JSON.stringify(updated));
      addLog("리포트가 자동으로 저장되었습니다.");
  };

  const loadReport = (saved: SavedReport) => {
      setReport(saved.report);
      setStatus(AgentStatus.COMPLETE);
      setActiveTab('final');
      addLog(`저장된 리포트(${saved.date})를 불러왔습니다.`);
  };

  // 서버에서 특정 날짜의 분석 결과 로드
  const loadServerReport = async (date: string) => {
    setIsLoadingHistory(true);
    try {
      addLog(`${date} 날짜의 분석 결과를 불러오는 중...`);
      const analysisReport = await ApiService.getAnalysisByDate(date);
      setReport(analysisReport);
      setSelectedDate(date);
      setStatus(AgentStatus.COMPLETE);
      setActiveTab('final');
      addLog(`${date} 날짜의 분석 결과를 불러왔습니다.`);
    } catch (error: any) {
      console.error("분석 결과 로드 실패:", error);
      addLog(`오류: ${error.message}`);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const deleteReport = (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      const updated = savedReports.filter(r => r.id !== id);
      setSavedReports(updated);
      localStorage.setItem('alphaInvest_reports', JSON.stringify(updated));
  };

  const downloadFullPDF = async () => {
      if (!fullReportRef.current) return;
      
      const btn = document.getElementById('pdf-btn');
      if(btn) btn.innerText = "생성 중...";

      try {
          // Temporarily make it visible but transparent to avoid flash? 
          // Actually html2canvas needs it to be in DOM. 
          // We positioned it absolute -9999px which works.
          
          const canvas = await html2canvas(fullReportRef.current, {
              scale: 2,
              backgroundColor: '#0f172a',
          });
          
          const imgData = canvas.toDataURL('image/png');
          const pdf = new jsPDF('p', 'mm', 'a4');

          const pdfWidth = 210;
          const pdfHeight = 297;
          const imgWidth = pdfWidth;
          const imgHeight = (canvas.height * pdfWidth) / canvas.width;
          
          let heightLeft = imgHeight;
          let position = 0;

          // Multi-page logic
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
          heightLeft -= pdfHeight;

          while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pdfHeight;
          }

          pdf.save(`AlphaInvest_FullReport_${new Date().toISOString().slice(0,10)}.pdf`);
      } catch (err) {
          console.error(err);
          alert("전체 PDF 생성 중 오류가 발생했습니다.");
      } finally {
          if(btn) btn.innerText = "전체 PDF 다운로드";
      }
  };

  const runAnalysis = async () => {
    setLogs([]);
    setReport({});

    try {
      // Step 1: 기존 분석 결과 확인 시도
      setStatus(AgentStatus.ANALYZING_SECTORS);
      addLog("백엔드 API: 기존 분석 결과 확인 중...");

      let analysisReport: AnalysisReport | null = null;

      try {
        // 먼저 기존 분석 결과가 있는지 확인
        analysisReport = await ApiService.getLatestAnalysis();
        addLog("기존 분석 결과를 발견했습니다. 데이터 로드 중...");
      } catch {
        // 기존 결과가 없으면 새로 분석 실행
        addLog("기존 분석 결과가 없습니다. 새로운 분석을 시작합니다...");

        // Step 2: 분석 실행
        setStatus(AgentStatus.ANALYZING_KOSPI_10);
        addLog("백엔드 API: 분석 태스크 시작...");
        const taskResponse = await ApiService.runAnalysis({ mode: 'daily', use_cache: true });
        addLog(`태스크 ID: ${taskResponse.task_id}`);

        // Step 3: 폴링으로 완료 대기
        setStatus(AgentStatus.ANALYZING_KOSPI_MID);
        addLog("백엔드 API: 분석 진행 중 (폴링)...");

        analysisReport = await ApiService.pollAnalysisTask(
          taskResponse.task_id,
          (status, message) => {
            if (status === 'running') {
              addLog(`진행 중: ${message || '분석 실행 중...'}`);
            }
          },
          3000, // 3초 간격
          600000 // 10분 타임아웃
        );
      }

      // Step 4: 결과 로드 및 표시
      setStatus(AgentStatus.ANALYZING_KOSDAQ);
      addLog(`유망 섹터 ${analysisReport.topSectors?.length || 0}개 식별`);
      setReport(prev => ({ ...prev, topSectors: analysisReport!.topSectors }));

      setStatus(AgentStatus.ANALYZING_SECTOR_STOCKS);
      addLog(`KOSPI Top 10: ${analysisReport.kospiTop10Picks?.length || 0}개 종목 분석 완료`);
      addLog(`KOSPI 11-20: ${analysisReport.kospiMidPicks?.length || 0}개 종목 분석 완료`);
      addLog(`KOSDAQ Top 10: ${analysisReport.kosdaqTop10Picks?.length || 0}개 종목 분석 완료`);
      setReport(prev => ({
        ...prev,
        kospiTop10Picks: analysisReport!.kospiTop10Picks,
        kospiMidPicks: analysisReport!.kospiMidPicks,
        kosdaqTop10Picks: analysisReport!.kosdaqTop10Picks,
        sectorBestPicks: analysisReport!.sectorBestPicks,
      }));

      // Step 5: 최종 결과
      setStatus(AgentStatus.SYNTHESIZING_FINAL);
      addLog("최종 Top 3 종목 선별 완료.");

      const finalReport = {
        ...analysisReport,
        timestamp: analysisReport.timestamp || new Date().toISOString()
      };

      setReport(finalReport);
      addLog("리포트 생성 완료!");

      setStatus(AgentStatus.COMPLETE);
      setActiveTab('final');
      saveCurrentReport(finalReport as AnalysisReport);

      // 서버 히스토리 갱신
      try {
        const history = await ApiService.getAnalysisHistory();
        setServerHistory(history);
        if (history.length > 0) {
          setSelectedDate(history[0].date);
        }
      } catch {
        // 히스토리 갱신 실패는 무시
      }

    } catch (error: any) {
      console.error(error);
      addLog(`오류 발생: ${error.message}`);
      setStatus(AgentStatus.ERROR);
    }
  };

  const navItems = [
    { id: 'overview', label: '대시보드', icon: LayoutDashboard },
    { id: 'sectors', label: '유망 섹터', icon: Briefcase },
    { id: 'kospi10', label: '코스피 상위 10', icon: TrendingUp },
    { id: 'kospiMid', label: '코스피 11-20위', icon: BarChart2 },
    { id: 'kosdaq', label: '코스닥 상위 10', icon: Zap },
    { id: 'all18', label: '전체 18종목', icon: List },
    { id: 'final', label: '최종 TOP 5', icon: CheckCircle2 },
  ];

  if (!apiKeySet) {
      return (
          <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
              <div className="text-center space-y-6 max-w-md">
                  <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Key className="w-10 h-10 text-emerald-500" />
                  </div>
                  <h1 className="text-3xl font-bold text-white">AlphaInvest AI</h1>
                  <p className="text-slate-400">
                      백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하거나 API 키를 선택해주세요.
                  </p>
                  <p className="text-slate-500 text-sm">
                      백엔드 실행: <code className="bg-slate-800 px-2 py-1 rounded">uv run python main.py --web</code>
                  </p>
                  <button
                    onClick={handleSelectKey}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-6 rounded-lg transition-all w-full"
                  >
                      다시 연결 시도
                  </button>
              </div>
          </div>
      )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col md:flex-row overflow-hidden relative">
      
      {/* Hidden Container for Full PDF Generation */}
      {status === AgentStatus.COMPLETE && (
        <div ref={fullReportRef} className="fixed left-[-9999px] top-0 w-[1200px] bg-slate-900 p-8 text-white space-y-8">
            <h1 className="text-4xl font-bold text-emerald-500 mb-8 border-b border-slate-700 pb-4">AlphaInvest AI 시장 분석 리포트</h1>
            <div className="text-sm text-slate-400 mb-8">생성일: {new Date().toLocaleString('ko-KR')}</div>
            
            <section>
                <h2 className="text-2xl font-bold mb-4 text-emerald-400">1. 유망 섹터 (Top Sectors)</h2>
                {report.topSectors?.map((s, i) => (
                    <div key={i} className="mb-4 bg-slate-800 p-4 rounded border border-slate-700">
                        <h3 className="text-xl font-bold">{s.name}</h3>
                        <p className="text-slate-300">{s.reasoning}</p>
                        <p className="text-sm mt-2 text-emerald-400">대장주: {s.topStocks.join(', ')}</p>
                    </div>
                ))}
            </section>

            <section>
                <h2 className="text-2xl font-bold mb-4 text-emerald-400">2. 최종 추천 TOP 5</h2>
                {report.finalTop5?.map((stock, i) => (
                     <div key={i} className="mb-6 bg-slate-800 p-6 rounded border border-slate-700">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="text-2xl font-bold">{stock.name}</h3>
                            <span className="text-emerald-400 font-bold text-xl">Score: {stock.rubric.total}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mb-4 text-sm bg-slate-900 p-2 rounded">
                            <div>기술적: {stock.rubric.technical.toFixed(1)}</div>
                            <div>수급: {stock.rubric.supply.toFixed(1)}</div>
                            <div>펀더멘털: {stock.rubric.fundamental.toFixed(1)}</div>
                            <div>시장환경: {stock.rubric.market.toFixed(1)}</div>
                        </div>
                        <div className="prose prose-invert prose-sm max-w-none">
                            <h4 className="font-bold text-emerald-300">종합 분석</h4>
                            <ReactMarkdown>{stock.comprehensiveAnalysis}</ReactMarkdown>
                        </div>
                     </div>
                ))}
            </section>

            <section>
                <h2 className="text-2xl font-bold mb-4 text-emerald-400">3. 전체 분석 종목 요약 (KOSPI/KOSDAQ)</h2>
                <div className="grid grid-cols-2 gap-4">
                    {[...(report.kospiTop10Picks || []), ...(report.kosdaqTop10Picks || [])].map((stock, i) => (
                        <div key={i} className="bg-slate-800 p-3 rounded border border-slate-700">
                            <div className="font-bold">{stock.name} ({stock.sector})</div>
                            <div className="text-xs text-slate-400 truncate">{stock.summary}</div>
                            <div className="text-xs text-emerald-400 text-right mt-1">Score: {stock.rubric.total}</div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
      )}

      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        className="fixed top-4 left-4 z-50 md:hidden bg-slate-800 p-2 rounded-lg border border-slate-700 text-white"
      >
        {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`
        fixed md:relative
        top-0 left-0
        w-64 h-screen
        bg-slate-950 border-r border-slate-800
        p-6 flex flex-col shrink-0 overflow-y-auto
        z-40
        transform transition-transform duration-300 ease-in-out
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <h1 className="text-2xl font-bold text-emerald-500 mb-8 flex items-center gap-2 mt-8 md:mt-0">
          <TrendingUp /> AlphaInvest
        </h1>

        <nav className="space-y-2 mb-8">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id as any);
                setIsMobileMenuOpen(false);
              }}
              disabled={status !== AgentStatus.COMPLETE && item.id !== 'overview'}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-sm font-medium ${
                activeTab === item.id
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/50'
                  : status !== AgentStatus.COMPLETE && item.id !== 'overview'
                    ? 'opacity-50 cursor-not-allowed text-slate-500'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
        </nav>

        {/* Server History Section */}
        <div className="mt-auto pt-6 border-t border-slate-800">
           <h3 className="text-xs font-semibold text-slate-500 uppercase mb-4 flex items-center gap-2">
               <FileText size={12}/> 분석 히스토리
           </h3>
           <div className="space-y-2 max-h-48 overflow-y-auto">
               {isLoadingHistory && (
                   <div className="flex items-center gap-2 text-xs text-slate-500">
                       <Loader2 className="animate-spin" size={12}/> 로딩 중...
                   </div>
               )}
               {!isLoadingHistory && serverHistory.length === 0 && (
                   <p className="text-xs text-slate-600 italic">분석 결과 없음</p>
               )}
               {serverHistory.map((item) => (
                   <div key={item.date}
                        onClick={() => {
                          loadServerReport(item.date);
                          setIsMobileMenuOpen(false);
                        }}
                        className={`group flex flex-col text-xs p-2 rounded cursor-pointer transition-colors ${
                          selectedDate === item.date
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'text-slate-400 hover:text-emerald-400 hover:bg-slate-900'
                        }`}>
                       <span className="font-medium">{item.date}</span>
                       <span className="text-slate-500 truncate text-[10px]">{item.preview}</span>
                   </div>
               ))}
           </div>
        </div>

        {/* Local Saved Reports Section */}
        {savedReports.length > 0 && (
        <div className="pt-4 border-t border-slate-800/50">
           <h3 className="text-xs font-semibold text-slate-500 uppercase mb-4 flex items-center gap-2">
               <History size={12}/> 로컬 저장
           </h3>
           <div className="space-y-2">
               {savedReports.map(saved => (
                   <div key={saved.id}
                        onClick={() => {
                          loadReport(saved);
                          setIsMobileMenuOpen(false);
                        }}
                        className="group flex items-center justify-between text-xs text-slate-400 hover:text-emerald-400 hover:bg-slate-900 p-2 rounded cursor-pointer transition-colors">
                       <span>{saved.date}</span>
                       <button onClick={(e) => deleteReport(saved.id, e)} className="opacity-0 group-hover:opacity-100 hover:text-red-400">
                           <Trash2 size={12}/>
                       </button>
                   </div>
               ))}
           </div>
        </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-grow p-4 pt-16 md:pt-4 md:p-12 overflow-y-auto relative md:ml-0">
        
        {/* Top Right Controls */}
        <div className="absolute top-6 right-6 flex items-center gap-3 z-30" id="no-print">
            {status === AgentStatus.COMPLETE && (
                <button 
                  id="pdf-btn"
                  onClick={downloadFullPDF}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm transition-all border border-slate-700"
                >
                    <Download size={16} /> 전체 PDF 다운로드
                </button>
            )}
            <button 
                onClick={() => setIsChatOpen(!isChatOpen)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all shadow-lg ${
                    isChatOpen ? 'bg-emerald-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/30'
                }`}
            >
                <MessageSquare size={18} /> AI 챗봇
            </button>
        </div>

        {activeTab === 'overview' && (
          <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pt-10">
            <header className="text-center mb-12">
              <h2 className="text-4xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
                AI 기반 주식 시장 분석
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                6개의 특화된 AI 에이전트가 시장 섹터를 정밀 분석하고, 18개의 유망 종목을 선별하여
                자체 루브릭 모델을 통해 최상위 5개 투자 종목을 추천합니다.
              </p>
            </header>

            {/* Action Area */}
            {status === AgentStatus.IDLE ? (
              <div className="flex justify-center">
                <button 
                  onClick={runAnalysis}
                  className="group relative flex items-center gap-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 px-12 rounded-full shadow-lg shadow-emerald-600/30 transition-all transform hover:scale-105"
                >
                  <PlayCircle size={24} />
                  전체 시장 분석 시작
                  <div className="absolute inset-0 rounded-full ring-4 ring-white/10 group-hover:ring-white/20 transition-all"></div>
                </button>
              </div>
            ) : (
              <div className="bg-slate-950 rounded-xl border border-slate-800 p-6 shadow-inner h-64 flex flex-col">
                 <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
                    <span className="text-emerald-400 font-mono text-sm flex items-center gap-2">
                        <Loader2 className="animate-spin" size={14}/> 실시간 에이전트 로그
                    </span>
                 </div>
                 <div className="flex-grow overflow-y-auto font-mono text-xs text-slate-300 space-y-1">
                    {logs.map((log, i) => (
                        <div key={i}>{log}</div>
                    ))}
                    <div ref={logEndRef} />
                 </div>
              </div>
            )}
            
            {/* Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700">
                    <div className="w-10 h-10 bg-blue-500/20 text-blue-400 rounded-lg flex items-center justify-center mb-4"><Briefcase /></div>
                    <h3 className="font-bold mb-2">섹터 로테이션 분석</h3>
                    <p className="text-sm text-slate-400">반도체, 바이오, 방산 등 주요 섹터의 자금 이동을 추적합니다.</p>
                </div>
                <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700">
                    <div className="w-10 h-10 bg-purple-500/20 text-purple-400 rounded-lg flex items-center justify-center mb-4"><BarChart2 /></div>
                    <h3 className="font-bold mb-2">밸류에이션 점검</h3>
                    <p className="text-sm text-slate-400">단순 모멘텀이 아닌 현재 주가 수준(저평가/고평가)을 철저히 검증합니다.</p>
                </div>
                <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700">
                    <div className="w-10 h-10 bg-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center mb-4"><CheckCircle2 /></div>
                    <h3 className="font-bold mb-2">최종 Top 5 선정</h3>
                    <p className="text-sm text-slate-400">18개의 후보군 중 최고의 투자 기회를 가진 5개 종목을 엄선합니다.</p>
                </div>
            </div>
          </div>
        )}

        {/* Dynamic Views based on Tabs */}
        {(activeTab === 'sectors' && report.topSectors) && (
            <div className="space-y-8 pt-10">
               <h2 className="text-2xl font-bold flex items-center gap-2"><Briefcase className="text-emerald-400"/> 섹터 분석</h2>

               {/* Sector Bar Chart */}
               {report.allSectors && report.allSectors.length > 0 && (
                   <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
                       <h3 className="text-lg font-semibold text-white mb-4">섹터별 점수 순위</h3>
                       <SectorBarChart sectors={report.allSectors} />
                   </div>
               )}

               {/* Top 3 Sectors Detail */}
               <div>
                   <h3 className="text-lg font-semibold text-white mb-4">상위 3개 섹터 상세</h3>
                   <div className="grid grid-cols-1 gap-6">
                       {report.topSectors.map((sector, idx) => (
                           <div key={idx} className="bg-slate-800 border border-slate-700 rounded-xl p-6 break-inside-avoid">
                               <div className="flex justify-between items-start mb-4">
                                   <h3 className="text-xl font-bold text-white">{sector.name}</h3>
                                   <div className="flex items-center gap-2">
                                       {sector.weightedScore && (
                                           <span className="text-emerald-400 font-bold">{sector.weightedScore.toFixed(1)}점</span>
                                       )}
                                       <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-1 rounded font-bold">#{idx + 1}</span>
                                   </div>
                               </div>
                               <p className="text-slate-300 mb-6">{sector.reasoning}</p>
                               <div>
                                   <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">대장주 (Leading Stocks)</h4>
                                   <div className="flex flex-wrap gap-2">
                                       {sector.topStocks.map((stock, sIdx) => (
                                           <span key={sIdx} className="bg-slate-900 text-slate-200 px-3 py-1 rounded border border-slate-700 text-sm">
                                               {stock}
                                           </span>
                                       ))}
                                   </div>
                               </div>
                           </div>
                       ))}
                   </div>
               </div>

               {report.sectorBestPicks && (
                   <div className="mt-12 break-before-page">
                       <h3 className="text-xl font-bold mb-4 text-slate-300">상세 분석: 섹터별 추천주</h3>
                       <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                           {report.sectorBestPicks.map((stock, i) => (
                               <StockCard key={i} stock={stock} onClick={() => setSelectedStock(stock)} />
                           ))}
                       </div>
                   </div>
               )}
            </div>
        )}

        {(activeTab === 'kospi10' && report.kospiTop10Picks) && (
            <div className="space-y-6 pt-10">
                <h2 className="text-2xl font-bold flex items-center gap-2"><TrendingUp className="text-emerald-400"/> 코스피 상위 10선</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {report.kospiTop10Picks.map((stock, i) => (
                        <StockCard key={i} stock={stock} rank={i+1} onClick={() => setSelectedStock(stock)} />
                    ))}
                </div>
            </div>
        )}

        {(activeTab === 'kospiMid' && report.kospiMidPicks) && (
            <div className="space-y-6 pt-10">
                <h2 className="text-2xl font-bold flex items-center gap-2"><BarChart2 className="text-emerald-400"/> 코스피 11-20위 추천</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {report.kospiMidPicks.map((stock, i) => (
                        <StockCard key={i} stock={stock} rank={i+1} onClick={() => setSelectedStock(stock)} />
                    ))}
                </div>
            </div>
        )}

        {(activeTab === 'kosdaq' && report.kosdaqTop10Picks) && (
            <div className="space-y-6 pt-10">
                <h2 className="text-2xl font-bold flex items-center gap-2"><Zap className="text-emerald-400"/> 코스닥 상위 10선</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {report.kosdaqTop10Picks.map((stock, i) => (
                        <StockCard key={i} stock={stock} rank={i+1} onClick={() => setSelectedStock(stock)} />
                    ))}
                </div>
            </div>
        )}

        {(activeTab === 'all18' && report.final18) && (
            <div className="space-y-6 pt-10">
                <h2 className="text-2xl font-bold flex items-center gap-2"><List className="text-emerald-400"/> 전체 18개 선정 종목</h2>
                <p className="text-slate-400 text-sm">KOSPI Top 10, KOSPI 11-20, KOSDAQ Top 10, 섹터별 상위 종목에서 선별된 최종 18개 종목입니다.</p>

                <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-slate-900/50">
                                <tr className="text-left">
                                    <th className="px-4 py-3 font-semibold text-slate-300 w-12">#</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300">종목명</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300">섹터</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-right">총점</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-center">등급</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-right">기술적</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-right">수급</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-right">펀더멘털</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 text-right">시장</th>
                                    <th className="px-4 py-3 font-semibold text-slate-300 w-20"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700/50">
                                {report.final18.map((stock, i) => {
                                    const gradeColor = stock.rubric.grade === 'Strong Buy' ? 'text-emerald-400 bg-emerald-500/20'
                                        : stock.rubric.grade === 'Buy' ? 'text-green-400 bg-green-500/20'
                                        : stock.rubric.grade === 'Hold' ? 'text-yellow-400 bg-yellow-500/20'
                                        : 'text-orange-400 bg-orange-500/20';
                                    return (
                                        <tr key={i} className="hover:bg-slate-700/30 transition-colors cursor-pointer" onClick={() => setSelectedStock(stock)}>
                                            <td className="px-4 py-3 text-slate-400 font-mono">{i + 1}</td>
                                            <td className="px-4 py-3">
                                                <div className="font-semibold text-white">{stock.name}</div>
                                                <div className="text-xs text-slate-500">{stock.ticker}</div>
                                            </td>
                                            <td className="px-4 py-3 text-slate-400">{stock.sector}</td>
                                            <td className="px-4 py-3 text-right font-bold text-emerald-400">{stock.rubric.total.toFixed(1)}</td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={`px-2 py-1 rounded text-xs font-semibold ${gradeColor}`}>
                                                    {stock.rubric.grade}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-right text-slate-300">{stock.rubric.technical.toFixed(1)}</td>
                                            <td className="px-4 py-3 text-right text-slate-300">{stock.rubric.supply.toFixed(1)}</td>
                                            <td className="px-4 py-3 text-right text-slate-300">{stock.rubric.fundamental.toFixed(1)}</td>
                                            <td className="px-4 py-3 text-right text-slate-300">{stock.rubric.market.toFixed(1)}</td>
                                            <td className="px-4 py-3 text-center">
                                                <button className="text-emerald-400 hover:text-emerald-300 text-xs font-medium">
                                                    상세 →
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        )}

        {(activeTab === 'final' && report.finalTop5) && (
            <div className="space-y-8 pt-10">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold text-white mb-2">최종 투자 추천 (Final Recommendations)</h2>
                    <p className="text-slate-400">18개의 유망 후보군 중 다각도 분석을 통해 선정된 TOP 5 종목입니다.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                    {report.finalTop5.map((stock, i) => (
                        <div key={i} className="relative break-inside-avoid">
                            <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white px-4 py-1 rounded-full text-sm font-bold shadow-lg z-10">
                                #{i + 1} PICK
                            </div>
                            <div className="h-full border-2 border-emerald-500/30 rounded-xl overflow-hidden shadow-[0_0_30px_rgba(16,185,129,0.1)]">
                                <StockCard stock={stock} onClick={() => setSelectedStock(stock)} />
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-12 bg-slate-800/30 rounded-xl p-8 border border-slate-700 break-inside-avoid">
                    <h3 className="text-xl font-bold mb-4 text-slate-300">투자 전략 노트 & 밸류에이션 코멘트</h3>
                    <p className="text-slate-400 leading-relaxed">
                        선정된 5개 종목은 현재 시장 상황에서 기술적 모멘텀, 펀더멘털 가치, 그리고 기관 수급이 가장 강력하게 결합된 기회를 나타냅니다.
                        AI 에이전트들은 특히 <span className="text-emerald-400 font-semibold">현재 주가 수준(Price Level)</span>이 고평가되지 않았는지 집중적으로 점검하였습니다.
                        재무 건전성과 실적 대비 저평가 매력이 있거나, 강력한 상승 재료가 밸류에이션 부담을 상쇄하는 종목을 우선했습니다.
                        <br/><br/>
                        투자는 개인의 책임하에 신중하게 결정하시기 바랍니다.
                    </p>
                </div>
            </div>
        )}
      </main>

      <ChatSidebar 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
        report={report}
      />
      
      <StockModal stock={selectedStock} onClose={() => setSelectedStock(null)} />
    </div>
  );
};

export default App;