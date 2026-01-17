import React, { useRef } from 'react';
import { StockAnalysis } from '../types';
import RubricChart from './RubricChart';
import { X, TrendingUp, AlertTriangle, Newspaper, BarChart3, FileText, Download, Activity, PieChart } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

interface Props {
  stock: StockAnalysis | null;
  onClose: () => void;
}

const StockModal: React.FC<Props> = ({ stock, onClose }) => {
  const reportRef = useRef<HTMLDivElement>(null);

  if (!stock) return null;

  const handleDownloadPDF = async () => {
    if (!reportRef.current) return;
    const btn = document.getElementById('stock-pdf-btn');
    if (btn) btn.innerText = "생성 중...";

    try {
      const canvas = await html2canvas(reportRef.current, {
        scale: 2,
        backgroundColor: '#0f172a',
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = 210;
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`${stock.name}_분석리포트.pdf`);
    } catch (e) {
      console.error(e);
      alert("PDF 생성 실패");
    } finally {
      if (btn) btn.innerText = "PDF 다운로드";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-5xl max-h-[95vh] overflow-y-auto shadow-2xl animate-in fade-in zoom-in duration-200 flex flex-col">
        
        {/* Sticky Header */}
        <div className="sticky top-0 bg-slate-900/95 backdrop-blur border-b border-slate-800 p-6 flex justify-between items-center z-20">
          <div>
            <h2 className="text-3xl font-bold text-white mb-1 flex items-center gap-2">
                {stock.name} 
                <span className="text-sm font-normal text-slate-500 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">{stock.ticker || 'KRX'}</span>
            </h2>
            <div className="flex gap-3 text-sm text-slate-400">
              <span className="text-emerald-400 font-mono font-bold">{stock.sector}</span>
              {stock.currentPrice && <span>Current: <span className="text-white">{stock.currentPrice}</span></span>}
            </div>
          </div>
          <div className="flex gap-2">
            <button 
                id="stock-pdf-btn"
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm transition-colors font-medium"
            >
                <Download size={16} /> PDF 다운로드
            </button>
            <button 
                onClick={onClose}
                className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors"
            >
                <X size={24} />
            </button>
          </div>
        </div>

        {/* Content for PDF Capture */}
        <div ref={reportRef} className="p-8 bg-slate-900 text-slate-200">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left Column: Metrics & Chart */}
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <BarChart3 size={16} /> 8대 핵심 루브릭 (Score: {stock.rubric.total})
                </h3>
                <RubricChart score={stock.rubric} />
                <div className="mt-4 space-y-2 text-xs">
                     {/* Mini Score Table */}
                     <div className="grid grid-cols-2 gap-2">
                        <div className="flex justify-between p-2 bg-slate-800 rounded"><span>밸류에이션</span><span className="text-emerald-400 font-bold">{stock.rubric.valuation}</span></div>
                        <div className="flex justify-between p-2 bg-slate-800 rounded"><span>펀더멘털</span><span className="text-white font-bold">{stock.rubric.fundamentals}</span></div>
                        <div className="flex justify-between p-2 bg-slate-800 rounded"><span>수급</span><span className="text-white font-bold">{stock.rubric.supplyDemand}</span></div>
                        <div className="flex justify-between p-2 bg-slate-800 rounded"><span>기술적</span><span className="text-white font-bold">{stock.rubric.technical}</span></div>
                     </div>
                </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700">
                    <h3 className="text-lg font-semibold text-amber-400 mb-3 flex items-center gap-2">
                        <AlertTriangle size={18} /> 주요 리스크 (Risks)
                    </h3>
                    <ul className="space-y-2">
                        {stock.risks.map((point, i) => (
                        <li key={i} className="flex gap-2 text-sm text-slate-300">
                            <span className="text-amber-500 font-bold mt-0.5">•</span>
                            {point}
                        </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Right Column: Detailed Markdown Analysis */}
            <div className="lg:col-span-2 space-y-8">
                <section>
                    <h3 className="text-xl font-bold text-white mb-3 border-b border-slate-800 pb-2">핵심 요약</h3>
                    <p className="text-slate-300 text-lg leading-relaxed">{stock.summary}</p>
                </section>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-slate-800/30 p-5 rounded-xl border border-slate-700/50">
                        <h4 className="text-lg font-semibold text-blue-400 mb-3 flex items-center gap-2">
                            <PieChart size={18} /> 재무 & 밸류에이션 분석
                        </h4>
                        <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                            <ReactMarkdown>{stock.financialAnalysis || "분석 데이터 없음"}</ReactMarkdown>
                        </div>
                    </div>
                    <div className="bg-slate-800/30 p-5 rounded-xl border border-slate-700/50">
                        <h4 className="text-lg font-semibold text-purple-400 mb-3 flex items-center gap-2">
                            <Activity size={18} /> 기술적 & 차트 분석
                        </h4>
                        <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                            <ReactMarkdown>{stock.technicalAnalysis || "분석 데이터 없음"}</ReactMarkdown>
                        </div>
                    </div>
                </div>

                <section className="bg-slate-800/30 p-5 rounded-xl border border-slate-700/50">
                    <h4 className="text-lg font-semibold text-orange-400 mb-3 flex items-center gap-2">
                        <Newspaper size={18} /> 뉴스 & 시장 센티멘트
                    </h4>
                    <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                        <ReactMarkdown>{stock.marketSentiment || "분석 데이터 없음"}</ReactMarkdown>
                    </div>
                </section>

                 <section className="bg-emerald-900/10 p-6 rounded-xl border border-emerald-500/30">
                    <h4 className="text-xl font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                        <FileText size={20} /> 종합 투자 의견 (Comprehensive Verdict)
                    </h4>
                    <div className="prose prose-invert prose-base max-w-none text-slate-200">
                        <ReactMarkdown>{stock.comprehensiveAnalysis || "종합 분석 데이터 없음"}</ReactMarkdown>
                    </div>
                </section>
            </div>
            </div>
        </div>

      </div>
    </div>
  );
};

export default StockModal;