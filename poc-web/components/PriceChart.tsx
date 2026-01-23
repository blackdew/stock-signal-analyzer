import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { PriceHistoryItem } from '../types';
import { getStockHistory } from '../services/apiService';
import { ChartSkeleton } from './Skeleton';

interface Props {
  symbol: string;
  days?: number;
}

interface ChartData {
  date: string;
  close: number;
  open: number;
  high: number;
  low: number;
  volume: number;
}

const PriceChart: React.FC<Props> = ({ symbol, days = 60 }) => {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await getStockHistory(symbol, days);
        const chartData = response.history.map((item: PriceHistoryItem) => ({
          date: item.date.slice(5), // MM-DD 형식
          close: item.close,
          open: item.open,
          high: item.high,
          low: item.low,
          volume: item.volume,
        }));
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
        <p className="text-slate-400 text-sm">주가 데이터가 없습니다.</p>
      </div>
    );
  }

  // 평균가 계산
  const avgPrice = data.reduce((sum, d) => sum + d.close, 0) / data.length;

  // 가격 변동 계산
  const firstPrice = data[0].close;
  const lastPrice = data[data.length - 1].close;
  const priceChange = lastPrice - firstPrice;
  const priceChangePercent = (priceChange / firstPrice) * 100;
  const isPositive = priceChange >= 0;

  // Y축 도메인 계산
  const prices = data.flatMap(d => [d.high, d.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.1;

  const formatPrice = (value: number) => value.toLocaleString('ko-KR');

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-400">{days}일 가격 추이</span>
        <span className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{priceChangePercent.toFixed(2)}%
        </span>
      </div>

      {/* 차트 */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={isPositive ? '#10b981' : '#ef4444'}
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor={isPositive ? '#10b981' : '#ef4444'}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[minPrice - padding, maxPrice + padding]}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
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
                  close: '종가',
                  high: '고가',
                  low: '저가',
                  open: '시가',
                };
                return [formatPrice(value), labels[name] || name];
              }}
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload as ChartData;
                return (
                  <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs">
                    <p className="text-slate-400 mb-2">{label}</p>
                    <div className="grid grid-cols-2 gap-2">
                      <span className="text-slate-500">시가</span>
                      <span className="text-white text-right">{formatPrice(d.open)}</span>
                      <span className="text-slate-500">고가</span>
                      <span className="text-emerald-400 text-right">{formatPrice(d.high)}</span>
                      <span className="text-slate-500">저가</span>
                      <span className="text-red-400 text-right">{formatPrice(d.low)}</span>
                      <span className="text-slate-500">종가</span>
                      <span className="text-white font-semibold text-right">{formatPrice(d.close)}</span>
                    </div>
                  </div>
                );
              }}
            />
            <ReferenceLine
              y={avgPrice}
              stroke="#64748b"
              strokeDasharray="3 3"
              label={{
                value: '평균',
                position: 'right',
                fill: '#64748b',
                fontSize: 10,
              }}
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke={isPositive ? '#10b981' : '#ef4444'}
              strokeWidth={2}
              fill="url(#colorPrice)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 요약 정보 */}
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="bg-slate-800/50 rounded p-2 text-center">
          <span className="text-slate-500 block">시작</span>
          <span className="text-white font-mono">{formatPrice(firstPrice)}</span>
        </div>
        <div className="bg-slate-800/50 rounded p-2 text-center">
          <span className="text-slate-500 block">현재</span>
          <span className="text-white font-mono">{formatPrice(lastPrice)}</span>
        </div>
        <div className="bg-slate-800/50 rounded p-2 text-center">
          <span className="text-slate-500 block">최고</span>
          <span className="text-emerald-400 font-mono">{formatPrice(maxPrice)}</span>
        </div>
        <div className="bg-slate-800/50 rounded p-2 text-center">
          <span className="text-slate-500 block">최저</span>
          <span className="text-red-400 font-mono">{formatPrice(minPrice)}</span>
        </div>
      </div>
    </div>
  );
};

export default PriceChart;
