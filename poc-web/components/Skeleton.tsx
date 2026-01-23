import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => (
  <div className={`animate-pulse bg-slate-700/50 rounded ${className}`} />
);

export const StockCardSkeleton: React.FC = () => (
  <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 h-full">
    <div className="flex justify-between items-start mb-3">
      <div className="space-y-2">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="text-right space-y-2">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-4 w-12" />
      </div>
    </div>
    <Skeleton className="h-12 w-full mb-4" />
    <Skeleton className="h-48 w-full" />
  </div>
);

export const TableRowSkeleton: React.FC = () => (
  <tr className="border-b border-slate-700/50">
    <td className="px-4 py-3"><Skeleton className="h-4 w-6" /></td>
    <td className="px-4 py-3">
      <Skeleton className="h-5 w-24 mb-1" />
      <Skeleton className="h-3 w-16" />
    </td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
    <td className="px-4 py-3"><Skeleton className="h-6 w-16 rounded-full" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
    <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
  </tr>
);

export const SectorCardSkeleton: React.FC = () => (
  <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
    <div className="flex justify-between items-start mb-4">
      <Skeleton className="h-7 w-24" />
      <Skeleton className="h-6 w-16" />
    </div>
    <Skeleton className="h-16 w-full mb-6" />
    <div>
      <Skeleton className="h-4 w-32 mb-3" />
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-16" />
      </div>
    </div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
    <Skeleton className="h-6 w-40 mb-4" />
    <Skeleton className="h-80 w-full" />
  </div>
);

export const LoadingOverlay: React.FC<{ message?: string }> = ({ message = '분석 중...' }) => (
  <div className="flex flex-col items-center justify-center py-20 space-y-4">
    <div className="relative">
      <div className="w-16 h-16 border-4 border-slate-700 border-t-emerald-500 rounded-full animate-spin" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-8 h-8 bg-slate-900 rounded-full" />
      </div>
    </div>
    <p className="text-slate-400 text-sm animate-pulse">{message}</p>
  </div>
);

export default Skeleton;
