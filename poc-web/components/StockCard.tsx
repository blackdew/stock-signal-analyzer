import React from 'react';
import { StockAnalysis } from '../types';
import RubricChart from './RubricChart';

interface Props {
  stock: StockAnalysis;
  rank?: number;
  onClick: () => void;
}

const StockCard: React.FC<Props> = ({ stock, rank, onClick }) => {
  return (
    <div 
      onClick={onClick}
      className="bg-slate-800 border border-slate-700 rounded-xl p-4 hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/10 transition-all cursor-pointer group flex flex-col h-full"
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2">
            {rank && (
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                {rank}
              </span>
            )}
            <h3 className="text-lg font-bold text-white group-hover:text-emerald-400 transition-colors">
              {stock.name}
            </h3>
          </div>
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider bg-slate-700/50 px-2 py-0.5 rounded mt-1 inline-block">
            {stock.sector}
          </span>
        </div>
        <div className="text-right">
            <div className="text-2xl font-bold text-emerald-400">{stock.rubric.total}<span className="text-sm text-slate-500">/100</span></div>
            <div className="text-xs text-slate-500">종합 점수</div>
        </div>
      </div>

      <div className="mb-4 flex-grow">
        <p className="text-sm text-slate-300 line-clamp-2">{stock.summary}</p>
      </div>

      <div className="mt-auto">
        <RubricChart score={stock.rubric} />
      </div>
    </div>
  );
};

export default StockCard;