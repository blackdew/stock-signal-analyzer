import React from 'react';

interface Props {
  currentPrice: number;
  low52w: number;
  high52w: number;
}

const PriceRangeIndicator: React.FC<Props> = ({ currentPrice, low52w, high52w }) => {
  // 범위 유효성 검사
  if (high52w <= low52w || currentPrice < low52w || currentPrice > high52w) {
    return (
      <div className="text-sm text-slate-500">
        52주 고저 데이터 없음
      </div>
    );
  }

  // 현재가 위치 계산 (0~100%)
  const range = high52w - low52w;
  const position = ((currentPrice - low52w) / range) * 100;

  // 위치에 따른 색상 (저점 근처: 빨강, 고점 근처: 초록)
  const getPositionColor = (pos: number): string => {
    if (pos < 30) return 'text-red-400';
    if (pos < 50) return 'text-orange-400';
    if (pos < 70) return 'text-yellow-400';
    return 'text-emerald-400';
  };

  // 바 색상 그라데이션
  const getBarGradient = (): string => {
    return 'bg-gradient-to-r from-red-500 via-yellow-500 to-emerald-500';
  };

  const formatPrice = (price: number): string => {
    return price.toLocaleString('ko-KR');
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-slate-400">
        <span>52주 저가</span>
        <span>52주 고가</span>
      </div>

      {/* 프로그레스 바 */}
      <div className="relative h-3 rounded-full bg-slate-700 overflow-hidden">
        {/* 그라데이션 배경 */}
        <div className={`absolute inset-0 ${getBarGradient()} opacity-30`} />

        {/* 현재가 위치 마커 */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-white shadow-lg shadow-white/50 rounded-full"
          style={{ left: `${Math.min(Math.max(position, 0), 100)}%`, transform: 'translateX(-50%)' }}
        />
      </div>

      {/* 가격 표시 */}
      <div className="flex justify-between text-xs">
        <span className="text-red-400 font-mono">{formatPrice(low52w)}</span>
        <span className={`font-mono font-semibold ${getPositionColor(position)}`}>
          {formatPrice(currentPrice)} ({position.toFixed(1)}%)
        </span>
        <span className="text-emerald-400 font-mono">{formatPrice(high52w)}</span>
      </div>

      {/* 위치 해석 */}
      <div className="text-center text-xs text-slate-500">
        {position < 30 && '52주 저점 근처 (매수 고려)'}
        {position >= 30 && position < 50 && '52주 범위 하단'}
        {position >= 50 && position < 70 && '52주 범위 중간'}
        {position >= 70 && '52주 고점 근처 (신중 접근)'}
      </div>
    </div>
  );
};

export default PriceRangeIndicator;
