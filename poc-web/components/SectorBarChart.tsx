import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { SectorAnalysis } from '../types';

interface Props {
  sectors: SectorAnalysis[];
  onSectorClick?: (sectorName: string) => void;
}

const COLORS = [
  '#10b981', // emerald-500
  '#22c55e', // green-500
  '#84cc16', // lime-500
  '#eab308', // yellow-500
  '#f97316', // orange-500
  '#ef4444', // red-500
  '#ec4899', // pink-500
  '#a855f7', // purple-500
  '#6366f1', // indigo-500
  '#3b82f6', // blue-500
  '#0ea5e9', // sky-500
];

const SectorBarChart: React.FC<Props> = ({ sectors, onSectorClick }) => {
  const sortedSectors = [...sectors]
    .sort((a, b) => (b.weightedScore || 0) - (a.weightedScore || 0));

  const data = sortedSectors.map((sector, index) => ({
    name: sector.name,
    score: sector.weightedScore || 0,
    rank: index + 1,
    fill: COLORS[index % COLORS.length],
  }));

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
        >
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#475569' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#e2e8f0', fontSize: 12 }}
            axisLine={{ stroke: '#475569' }}
            width={75}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              borderColor: '#334155',
              borderRadius: '8px',
              color: '#f1f5f9',
            }}
            formatter={(value: number) => [`${value.toFixed(1)}점`, '가중 평균 점수']}
            cursor={{ fill: 'rgba(71, 85, 105, 0.3)' }}
          />
          <Bar
            dataKey="score"
            radius={[0, 4, 4, 0]}
            onClick={(data) => onSectorClick?.(data.name)}
            style={{ cursor: onSectorClick ? 'pointer' : 'default' }}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SectorBarChart;
