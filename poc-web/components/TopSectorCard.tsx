import React from 'react';
import { SectorAnalysis } from '../types';

interface Props {
  sector: SectorAnalysis;
  rank: number;
}

// 섹터 영문명 매핑
const SECTOR_ENGLISH_NAMES: Record<string, string> = {
  '반도체': 'AI Semiconductors',
  '조선': 'Shipbuilding',
  '방산/우주': 'Defense',
  '전력인프라': 'Power Equipment',
  '바이오': 'Bio/Healthcare',
  '로봇': 'Robotics',
  '자동차': 'Automotive',
  '신재생에너지': 'Renewable Energy',
  '지주': 'Holdings',
  '뷰티': 'Beauty/Cosmetics',
  '금융': 'Finance',
  '푸드': 'Food & Beverage',
  '엔터': 'Entertainment',
};

// 대장주 영문명 매핑 (주요 종목)
const STOCK_ENGLISH_NAMES: Record<string, string> = {
  'SK하이닉스': 'SK Hynix',
  '삼성전자': 'Samsung Electronics',
  '한미반도체': 'Hanmi Semiconductor',
  'HD현대일렉트릭': 'HD Hyundai Electric',
  'LS ELECTRIC': 'LS ELECTRIC',
  '효성중공업': 'Hyosung Heavy Industries',
  '한화에어로스페이스': 'Hanwha Aerospace',
  '현대로템': 'Hyundai Rotem',
  'LIG넥스원': 'LIG Nex1',
  'HD한국조선해양': 'HD Korea Shipbuilding',
  '삼성바이오로직스': 'Samsung Biologics',
  '셀트리온': 'Celltrion',
  '현대차': 'Hyundai Motor',
  '기아': 'Kia',
  'LG에너지솔루션': 'LG Energy Solution',
  '삼성SDI': 'Samsung SDI',
  'HD현대중공업': 'HD Hyundai Heavy Industries',
};

const TopSectorCard: React.FC<Props> = ({ sector, rank }) => {
  const englishName = SECTOR_ENGLISH_NAMES[sector.name] || sector.name;

  // LLM 분석 결과가 있으면 사용, 없으면 기본 reasoning 사용
  const description = sector.outlook || sector.reasoning;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 relative">
      {/* 순위 배지 */}
      <div className="absolute top-4 right-4">
        <span className="bg-emerald-500 text-white text-xs font-bold px-3 py-1 rounded">
          순위 {rank}
        </span>
      </div>

      {/* 섹터명 */}
      <h3 className="text-xl font-bold text-white mb-4 pr-20">
        {sector.name} <span className="text-slate-400 font-normal">({englishName})</span>
      </h3>

      {/* 섹터 분석 설명 */}
      <p className="text-slate-300 text-sm leading-relaxed mb-6">
        {description}
      </p>

      {/* 대장주 태그 */}
      <div>
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          대장주 (LEADING STOCKS)
        </h4>
        <div className="flex flex-wrap gap-2">
          {sector.topStocks.map((stock, idx) => {
            const stockEnglish = STOCK_ENGLISH_NAMES[stock] || stock;
            return (
              <span
                key={idx}
                className="bg-slate-900 text-slate-200 px-3 py-1.5 rounded border border-slate-700 text-sm"
              >
                {stock} <span className="text-slate-500">({stockEnglish})</span>
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TopSectorCard;
