import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';
import { SupplyItem } from '../types';
import { getStockSupply } from '../services/apiService';
import { ChartSkeleton } from './Skeleton';

interface Props {
  symbol: string;
  days?: number;
}

interface ChartData {
  date: string;
  foreign: number;
  institution: number;
}

const SupplyChart: React.FC<Props> = ({ symbol, days = 20 }) => {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'daily' | 'cumulative'>('daily');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await getStockSupply(symbol, days);
        const chartData = response.supply.map((item: SupplyItem) => ({
          date: item.date.slice(5), // MM-DD 형식
          foreign: item.foreign_net,
          institution: item.institution_net,
        }));
        // 날짜순 정렬 (오래된 순)
        chartData.reverse();
        setData(chartData);
      } catch (err) {
        setError(err instanceof Error ? err.message : '데이터 로드 실패');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, days]);

  if (loading) {
    return <ChartSkeleton />;
  }

  if (error) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <p className="text-slate-400 text-sm">수급 데이터가 없습니다.</p>
      </div>
    );
  }

  // 누적 데이터 계산
  const cumulativeData = data.reduce<ChartData[]>((acc, curr, idx) => {
    const prev = acc[idx - 1];
    acc.push({
      date: curr.date,
      foreign: (prev?.foreign || 0) + curr.foreign,
      institution: (prev?.institution || 0) + curr.institution,
    });
    return acc;
  }, []);

  const displayData = viewMode === 'daily' ? data : cumulativeData;

  // 합계 계산
  const totalForeign = data.reduce((sum, d) => sum + d.foreign, 0);
  const totalInstitution = data.reduce((sum, d) => sum + d.institution, 0);

  const formatValue = (value: number) => {
    if (Math.abs(value) >= 1000) {
      return `${(value / 1000).toFixed(1)}천`;
    }
    return value.toFixed(1);
  };

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-400">{days}일 수급 동향 (억원)</span>
        <div className="flex gap-1">
          <button
            onClick={() => setViewMode('daily')}
            className={`px-2 py-1 text-xs rounded ${
              viewMode === 'daily'
                ? 'bg-slate-700 text-white'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            일별
          </button>
          <button
            onClick={() => setViewMode('cumulative')}
            className={`px-2 py-1 text-xs rounded ${
              viewMode === 'cumulative'
                ? 'bg-slate-700 text-white'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            누적
          </button>
        </div>
      </div>

      {/* 차트 */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={displayData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
              tickFormatter={(v) => formatValue(v)}
              width={45}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                borderColor: '#334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(value: number, name: string) => {
                const labels: Record<string, string> = {
                  foreign: '외국인',
                  institution: '기관',
                };
                const color = value >= 0 ? '#10b981' : '#ef4444';
                return [
                  <span style={{ color }}>{value.toFixed(2)} 억원</span>,
                  labels[name] || name,
                ];
              }}
            />
            <ReferenceLine y={0} stroke="#475569" />
            <Bar dataKey="foreign" name="외국인" maxBarSize={12}>
              {displayData.map((entry, index) => (
                <Cell
                  key={`foreign-${index}`}
                  fill={entry.foreign >= 0 ? '#3b82f6' : '#6366f1'}
                  fillOpacity={entry.foreign >= 0 ? 0.8 : 0.5}
                />
              ))}
            </Bar>
            <Bar dataKey="institution" name="기관" maxBarSize={12}>
              {displayData.map((entry, index) => (
                <Cell
                  key={`inst-${index}`}
                  fill={entry.institution >= 0 ? '#f59e0b' : '#d97706'}
                  fillOpacity={entry.institution >= 0 ? 0.8 : 0.5}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 범례 */}
      <div className="flex justify-center gap-6 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-blue-500" />
          <span className="text-slate-400">외국인</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-amber-500" />
          <span className="text-slate-400">기관</span>
        </div>
      </div>

      {/* 합계 정보 */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-slate-800/50 rounded p-3">
          <div className="flex justify-between items-center">
            <span className="text-blue-400">외국인 {days}일 합계</span>
            <span className={`font-mono font-semibold ${totalForeign >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalForeign >= 0 ? '+' : ''}{totalForeign.toFixed(1)} 억
            </span>
          </div>
        </div>
        <div className="bg-slate-800/50 rounded p-3">
          <div className="flex justify-between items-center">
            <span className="text-amber-400">기관 {days}일 합계</span>
            <span className={`font-mono font-semibold ${totalInstitution >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalInstitution >= 0 ? '+' : ''}{totalInstitution.toFixed(1)} 억
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupplyChart;
