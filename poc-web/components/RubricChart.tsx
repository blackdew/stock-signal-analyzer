import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { RubricScore } from '../types';

interface Props {
  score: RubricScore;
  version?: 'v2' | 'v3';  // 차트 버전 선택
}

const RubricChart: React.FC<Props> = ({ score, version = 'v3' }) => {
  // V3: 8대 핵심 루브릭 (validation-imgs 기준)
  const dataV3 = [
    { subject: '밸류에이션(20%)', A: score.valuation ?? 0, fullMark: 20 },
    { subject: '펀더멘털(15%)', A: score.fundamental ?? 0, fullMark: 15 },
    { subject: '수급(15%)', A: score.supply ?? 0, fullMark: 15 },
    { subject: '모멘텀(15%)', A: score.momentum ?? 0, fullMark: 15 },
    { subject: '기술적(10%)', A: score.technical ?? 0, fullMark: 10 },
    { subject: '섹터(10%)', A: score.sector ?? 0, fullMark: 10 },
    { subject: '리스크(10%)', A: score.risk ?? 0, fullMark: 10 },
    { subject: '주주환원(5%)', A: score.shareholder ?? 0, fullMark: 5 },
  ];

  // V2: 6대 카테고리 (기존 버전)
  const dataV2 = [
    { subject: '기술적(25%)', A: score.technical, fullMark: 25 },
    { subject: '수급(20%)', A: score.supply, fullMark: 20 },
    { subject: '펀더멘털(20%)', A: score.fundamental, fullMark: 20 },
    { subject: '시장환경(15%)', A: score.market, fullMark: 15 },
    { subject: '리스크(10%)', A: score.risk, fullMark: 10 },
    { subject: '상대강도(10%)', A: score.relative_strength, fullMark: 10 },
  ];

  // V3 데이터가 있는지 확인 (valuation이 null/undefined가 아니면 V3)
  // V3 점수가 0일 수도 있으므로 > 0이 아닌 != null로 체크
  const hasV3Data = score.valuation != null;
  const useV3 = version === 'v3' && hasV3Data;
  const data = useV3 ? dataV3 : dataV2;
  const maxDomain = useV3 ? 20 : 25;

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#475569" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <PolarRadiusAxis angle={30} domain={[0, maxDomain]} tick={false} axisLine={false} />
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
            formatter={(value: number) => [`${value.toFixed(1)}점`, '점수']}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RubricChart;
