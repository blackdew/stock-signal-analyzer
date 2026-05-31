import React from 'react';
import { SectorFlowResult } from '../types';

interface Props {
  data: SectorFlowResult[];
}

const SectorMoneyFlowBoard: React.FC<Props> = ({ data }) => {
  // 상위 3개 주도 섹터
  const topSectors = data.slice(0, 3);
  // 나머지 섹터
  const restSectors = data.slice(3);

  // 4분면 뱃지 헬퍼
  const renderQuadrantBadge = (quadrant: string) => {
    const configs: Record<string, { label: string; bg: string; text: string }> = {
      Leading: { label: '주도', bg: 'bg-emerald-500/10 border-emerald-500/25', text: 'text-emerald-400' },
      Improving: { label: '개선', bg: 'bg-blue-500/10 border-blue-500/25', text: 'text-blue-400' },
      Weakening: { label: '약화', bg: 'bg-amber-500/10 border-amber-500/25', text: 'text-amber-400' },
      Lagging: { label: '낙오', bg: 'bg-red-500/10 border-red-500/25', text: 'text-red-400' },
    };

    const c = configs[quadrant] || { label: quadrant, bg: 'bg-slate-800 border-slate-700', text: 'text-slate-400' };

    return (
      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* 챔피언 포디움 보드 */}
      <div>
        <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2 mb-4">
          🔥 주도 섹터 자금 흐름 TOP 3
          <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-normal">
            최근 수급 초집중
          </span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {topSectors.map((s, idx) => {
            // 순위별 디자인 테마
            const theme = [
              { border: 'border-amber-500/40', glow: 'shadow-amber-500/5', bg: 'from-amber-950/20 to-slate-900/40', badge: '🥇 1st Sector' },
              { border: 'border-slate-400/30', glow: 'shadow-slate-400/5', bg: 'from-slate-850/20 to-slate-900/40', badge: '🥈 2nd Sector' },
              { border: 'border-amber-700/30', glow: 'shadow-amber-700/5', bg: 'from-amber-900/10 to-slate-900/40', badge: '🥉 3rd Sector' },
            ][idx] || { border: 'border-slate-800', glow: 'shadow-none', bg: 'from-slate-900 to-slate-900', badge: '' };

            return (
              <div 
                key={s.sector_name}
                className={`relative overflow-hidden bg-gradient-to-br ${theme.bg} backdrop-blur-md border ${theme.border} rounded-2xl p-6 shadow-xl ${theme.glow} transition-transform duration-300 hover:-translate-y-1`}
              >
                {/* 우상단 데코레이션 그라데이션 구체 */}
                <div className="absolute -top-10 -right-10 w-24 h-24 bg-gradient-to-br from-slate-100/5 to-transparent rounded-full pointer-events-none" />

                <div className="flex justify-between items-start mb-4">
                  <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
                    {theme.badge}
                  </span>
                  {renderQuadrantBadge(s.quadrant)}
                </div>

                <h4 className="text-2xl font-bold text-slate-100 tracking-tight mb-2">
                  {s.sector_name}
                </h4>

                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300 font-mono">
                    {s.money_flow_score.toFixed(1)}
                  </span>
                  <span className="text-xs text-slate-500">MFS Points</span>
                </div>

                <div className="space-y-2 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span>RRG 좌표 (RS, Mom):</span>
                    <span className="font-mono text-slate-300">
                      ({s.rrg_x.toFixed(1)}, {s.rrg_y.toFixed(1)})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>자금 흐름 진단:</span>
                    <span className="text-emerald-400 font-semibold">
                      {s.money_flow_score >= 80 ? '강력 수급 유입' : s.money_flow_score >= 60 ? '안정적 자금 유입' : '보통 흐름'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 기타 섹터 랭킹 */}
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h4 className="text-sm font-bold text-slate-300 uppercase tracking-widest border-b border-slate-850 pb-3 mb-4">
          전체 섹터 자금 흐름 순위표 (4위 ~ 13위)
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="text-slate-400 font-bold border-b border-slate-800 pb-2">
                <th className="pb-3 w-12 text-center">순위</th>
                <th className="pb-3 pl-2">섹터명</th>
                <th className="pb-3 text-center">RRG 4분면</th>
                <th className="pb-3 text-right">RS Ratio</th>
                <th className="pb-3 text-right">RS Momentum</th>
                <th className="pb-3 text-right pr-4 text-emerald-400 font-bold">Money Flow 점수</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {restSectors.map((s) => (
                <tr key={s.sector_name} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 text-center font-bold text-slate-400 font-mono text-sm">
                    {s.rank}
                  </td>
                  <td className="py-3.5 pl-2 font-bold text-slate-200 text-sm">
                    {s.sector_name}
                  </td>
                  <td className="py-3.5 text-center">
                    {renderQuadrantBadge(s.quadrant)}
                  </td>
                  <td className="py-3.5 text-right font-mono text-slate-300">
                    {s.rrg_x.toFixed(2)}
                  </td>
                  <td className="py-3.5 text-right font-mono text-slate-300">
                    {s.rrg_y.toFixed(2)}
                  </td>
                  <td className="py-3.5 text-right pr-4 font-mono font-bold text-emerald-400 text-sm">
                    {s.money_flow_score.toFixed(1)}점
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SectorMoneyFlowBoard;
