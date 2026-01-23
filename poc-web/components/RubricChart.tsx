import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { RubricScore } from '../types';

interface Props {
  score: RubricScore;
}

const RubricChart: React.FC<Props> = ({ score }) => {
  // 백엔드와 동일한 6개 카테고리 (100점 만점 기준, 각 카테고리별 가중치 비율로 표시)
  const data = [
    { subject: '기술적(25%)', A: score.technical, fullMark: 25 },
    { subject: '수급(20%)', A: score.supply, fullMark: 20 },
    { subject: '펀더멘털(20%)', A: score.fundamental, fullMark: 20 },
    { subject: '시장환경(15%)', A: score.market, fullMark: 15 },
    { subject: '리스크(10%)', A: score.risk, fullMark: 10 },
    { subject: '상대강도(10%)', A: score.relative_strength, fullMark: 10 },
  ];

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#475569" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <PolarRadiusAxis angle={30} domain={[0, 25]} tick={false} axisLine={false} />
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