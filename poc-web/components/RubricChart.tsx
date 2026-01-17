import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { RubricScore } from '../types';

interface Props {
  score: RubricScore;
}

const RubricChart: React.FC<Props> = ({ score }) => {
  const data = [
    { subject: '밸류에이션(20%)', A: score.valuation, fullMark: 10 },
    { subject: '펀더멘털(15%)', A: score.fundamentals, fullMark: 10 },
    { subject: '수급(15%)', A: score.supplyDemand, fullMark: 10 },
    { subject: '모멘텀(15%)', A: score.momentum, fullMark: 10 },
    { subject: '기술적(10%)', A: score.technical, fullMark: 10 },
    { subject: '섹터(10%)', A: score.sector, fullMark: 10 },
    { subject: '리스크(10%)', A: score.risk, fullMark: 10 },
    { subject: '주주환원(5%)', A: score.shareholder, fullMark: 10 },
  ];

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#475569" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <PolarRadiusAxis angle={30} domain={[0, 10]} tick={false} axisLine={false} />
          <Radar
            name="점수"
            dataKey="A"
            stroke="#10b981"
            strokeWidth={2}
            fill="#10b981"
            fillOpacity={0.4}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
            itemStyle={{ color: '#10b981' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RubricChart;