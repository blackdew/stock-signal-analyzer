import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  Label,
  Cell,
} from 'recharts';
import { SectorFlowResult } from '../types';

interface Props {
  data: SectorFlowResult[];
}

const SectorRrgChart: React.FC<Props> = ({ data }) => {
  // RRG 4분면 색상 및 텍스트 맵
  const quadrantConfig = {
    Leading: { color: '#10b981', label: '주도 (Leading)', bg: '#10b98108', desc: '강세 트렌드 유지 및 상승 모멘텀 지속' },
    Weakening: { color: '#f59e0b', label: '약화 (Weakening)', bg: '#f59e0b08', desc: '강세 구간이나 상승 탄력 둔화 및 조정 주의' },
    Lagging: { color: '#ef4444', label: '낙오 (Lagging)', bg: '#ef444408', desc: '하락 트렌드 고착 및 가장 저조한 자금 유입' },
    Improving: { color: '#3b82f6', label: '개선 (Improving)', bg: '#3b82f608', desc: '침체 구간에서 반등 모멘텀 포착 및 선제 진입 구간' },
  };

  // Recharts Scatter 데이터 가공
  // RS Ratio(X)와 RS Momentum(Y)의 최소/최대 영역 산정
  const xValues = data.map((d) => d.rrg_x);
  const yValues = data.map((d) => d.rrg_y);
  
  const minX = Math.min(98.5, ...xValues) - 0.5;
  const maxX = Math.max(101.5, ...xValues) + 0.5;
  const minY = Math.min(98.5, ...yValues) - 0.5;
  const maxY = Math.max(101.5, ...yValues) + 0.5;

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: SectorFlowResult = payload[0].payload;
      const config = quadrantConfig[item.quadrant] || { color: '#ffffff', label: item.quadrant };
      
      return (
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 p-4 rounded-xl shadow-2xl max-w-xs">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-bold text-slate-100 text-base">{item.sector_name}</h4>
            <span 
              className="text-xs font-semibold px-2 py-0.5 rounded-full"
              style={{ backgroundColor: `${config.color}20`, color: config.color }}
            >
              {config.label}
            </span>
          </div>
          <div className="space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between">
              <span>상대강도 (RS Ratio):</span>
              <span className="font-mono text-slate-100 font-semibold">{item.rrg_x.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>상대모멘텀 (RS Mom):</span>
              <span className="font-mono text-slate-100 font-semibold">{item.rrg_y.toFixed(2)}</span>
            </div>
            <div className="h-px bg-slate-800 my-2" />
            <div className="flex justify-between text-emerald-400 font-semibold">
              <span>자금흐름 점수:</span>
              <span>{item.money_flow_score.toFixed(1)}점</span>
            </div>
            <div className="flex justify-between">
              <span>자금흐름 순위:</span>
              <span className="text-slate-100 font-semibold">{item.rank}위</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            📊 섹터 상대순환 RRG 맵
            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-normal">
              13개 섹터 추적
            </span>
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            벤치마크 대비 섹터별 상대적 순환 궤적과 운동 모멘텀을 시각화합니다.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* RRG Scatter Chart */}
        <div className="lg:col-span-3 h-[450px] bg-slate-950/80 rounded-xl relative border border-slate-800/80 p-2">
          {/* 4분면 라벨 백그라운드 오버레이 */}
          <div className="absolute top-4 right-4 pointer-events-none text-[10px] uppercase font-bold tracking-widest text-emerald-500/30">Leading</div>
          <div className="absolute bottom-4 right-4 pointer-events-none text-[10px] uppercase font-bold tracking-widest text-amber-500/30">Weakening</div>
          <div className="absolute bottom-4 left-4 pointer-events-none text-[10px] uppercase font-bold tracking-widest text-red-500/30">Lagging</div>
          <div className="absolute top-4 left-4 pointer-events-none text-[10px] uppercase font-bold tracking-widest text-blue-500/30">Improving</div>

          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 25, right: 25, bottom: 25, left: 25 }}>
              <XAxis 
                type="number" 
                dataKey="rrg_x" 
                name="RS Ratio" 
                domain={[minX, maxX]} 
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={{ stroke: '#334155' }}
                axisLine={{ stroke: '#334155' }}
              >
                <Label value="상대강도비율 (RS Ratio)" offset={-15} position="insideBottom" fill="#94a3b8" fontSize={11} />
              </XAxis>
              <YAxis 
                type="number" 
                dataKey="rrg_y" 
                name="RS Momentum" 
                domain={[minY, maxY]} 
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={{ stroke: '#334155' }}
                axisLine={{ stroke: '#334155' }}
              >
                <Label value="상대모멘텀 (RS Momentum)" angle={-90} offset={-5} position="insideLeft" fill="#94a3b8" fontSize={11} />
              </YAxis>
              <ZAxis type="number" dataKey="money_flow_score" range={[120, 450]} />

              {/* RRG 경계 배경색 칠하기 */}
              {/* 1. Leading (우상 - x >= 100, y >= 100) */}
              <ReferenceArea x1={100} y1={100} fill={quadrantConfig.Leading.bg} />
              {/* 2. Improving (좌상 - x < 100, y >= 100) */}
              <ReferenceArea x2={100} y1={100} fill={quadrantConfig.Improving.bg} />
              {/* 3. Lagging (좌하 - x < 100, y < 100) */}
              <ReferenceArea x2={100} y2={100} fill={quadrantConfig.Lagging.bg} />
              {/* 4. Weakening (우하 - x >= 100, y < 100) */}
              <ReferenceArea x1={100} y2={100} fill={quadrantConfig.Weakening.bg} />

              {/* 경계선 기준선 */}
              <ReferenceLine x={100} stroke="#475569" strokeWidth={1.5} strokeDasharray="3 3" />
              <ReferenceLine y={100} stroke="#475569" strokeWidth={1.5} strokeDasharray="3 3" />

              <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#475569' }} />
              
              <Scatter name="Sectors" data={data}>
                {data.map((entry, index) => {
                  const config = quadrantConfig[entry.quadrant] || { color: '#ffffff' };
                  return (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={config.color} 
                      stroke="#0f172a" 
                      strokeWidth={1.5}
                      className="cursor-pointer hover:scale-125 transition-transform duration-300"
                    />
                  );
                })}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* 4분면 설명 사이드 패널 */}
        <div className="flex flex-col justify-between gap-4">
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-300 uppercase tracking-widest border-b border-slate-800 pb-2">
              RRG 4대 국면 안내
            </h4>
            
            {Object.entries(quadrantConfig).map(([quad, conf]) => {
              const sectorsInQuad = data.filter((d) => d.quadrant === quad);
              return (
                <div key={quad} className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3.5">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: conf.color }} />
                    <span className="font-semibold text-slate-200 text-sm">{conf.label}</span>
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full ml-auto">
                      {sectorsInQuad.length}개 섹터
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                    {conf.desc}
                  </p>
                  {sectorsInQuad.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {sectorsInQuad.map((s) => (
                        <span 
                          key={s.sector_name}
                          className="text-[10px] bg-slate-900 border border-slate-800 text-slate-300 px-2 py-0.5 rounded"
                        >
                          {s.sector_name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[10px] text-slate-600 italic">속한 섹터 없음</span>
                  )}
                </div>
              );
            })}
          </div>
          
          <div className="text-[11px] text-slate-500 bg-slate-950/20 border border-slate-850 p-3 rounded-lg leading-relaxed">
            💡 **상대순환그래프(RRG) 해석**:
            섹터는 시계 방향으로 순환하는 속성이 있습니다: 
            **Improving (개선) → Leading (주도) → Weakening (약화) → Lagging (낙오) → Improving (개선)**. 
            상승 궤도를 타며 개선에서 주도로 넘어가는 입구의 섹터들을 추적하십시오.
          </div>
        </div>
      </div>
    </div>
  );
};

export default SectorRrgChart;
