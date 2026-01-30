import React from 'react';
import { StockAnalysis } from '../types';
import RubricChart from './RubricChart';

interface Props {
  stock: StockAnalysis;
  onClick?: () => void;
}

// 종목 영문명 매핑 (주요 종목)
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
  '두산에너빌리티': 'Doosan Enerbility',
  '한화오션': 'Hanwha Ocean',
  'POSCO홀딩스': 'POSCO Holdings',
  'SK': 'SK',
  'LG': 'LG',
  '넷마블': 'Netmarble',
  '크래프톤': 'Krafton',
  '엔씨소프트': 'NCsoft',
  '카카오': 'Kakao',
  '네이버': 'Naver',
  '아모레퍼시픽': 'Amorepacific',
  '코스맥스': 'Cosmax',
  'LG생활건강': 'LG H&H',
  'CJ제일제당': 'CJ CheilJedang',
  '오리온': 'Orion',
  'KB금융': 'KB Financial',
  '신한지주': 'Shinhan Financial',
  '하나금융지주': 'Hana Financial',
};

// 섹터 영문명 매핑
const SECTOR_ENGLISH_NAMES: Record<string, string> = {
  '반도체': 'AI SEMICONDUCTORS',
  '조선': 'SHIPBUILDING',
  '방산/우주': 'DEFENSE',
  '전력인프라': 'POWER EQUIPMENT',
  '바이오': 'BIO/HEALTHCARE',
  '로봇': 'ROBOTICS',
  '자동차': 'AUTOMOTIVE',
  '신재생에너지': 'RENEWABLE ENERGY',
  '지주': 'HOLDINGS',
  '뷰티': 'BEAUTY',
  '금융': 'FINANCE',
  '푸드': 'FOOD',
  '엔터': 'ENTERTAINMENT',
};

const StockRecommendCard: React.FC<Props> = ({ stock, onClick }) => {
  const englishName = STOCK_ENGLISH_NAMES[stock.name] || stock.name;
  const sectorEnglish = SECTOR_ENGLISH_NAMES[stock.sector] || stock.sector.toUpperCase();

  return (
    <div
      onClick={onClick}
      className="bg-slate-800 border border-slate-700 rounded-xl p-5 cursor-pointer hover:border-emerald-500/50 transition-all hover:shadow-lg hover:shadow-emerald-500/5"
    >
      {/* 헤더: 종목명 + 점수 */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1 pr-4">
          <h3 className="text-lg font-bold text-white leading-tight">
            {stock.name} <span className="text-slate-400 font-normal text-sm">({englishName})</span>
          </h3>
        </div>
        <div className="text-right shrink-0">
          <span className="text-2xl font-bold text-emerald-400">{stock.rubric.total.toFixed(2)}</span>
          <span className="text-slate-400 text-sm">/100</span>
          <div className="text-xs text-slate-500">종합 점수</div>
        </div>
      </div>

      {/* 섹터 태그 */}
      <div className="mb-3">
        <span className="inline-block bg-slate-900 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700">
          {stock.sector} ({sectorEnglish})
        </span>
      </div>

      {/* 한 줄 요약 */}
      <p className="text-slate-300 text-sm mb-4 line-clamp-2">
        {stock.summary}
      </p>

      {/* 8대 핵심 루브릭 레이더 차트 */}
      <div className="h-48">
        <RubricChart score={stock.rubric} version="v3" />
      </div>
    </div>
  );
};

export default StockRecommendCard;
