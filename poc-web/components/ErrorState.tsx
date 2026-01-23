import React from 'react';
import { AlertTriangle, RefreshCw, ServerOff, WifiOff } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  type?: 'error' | 'network' | 'server' | 'empty';
  onRetry?: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title = '오류 발생',
  message,
  type = 'error',
  onRetry,
}) => {
  const icons = {
    error: AlertTriangle,
    network: WifiOff,
    server: ServerOff,
    empty: AlertTriangle,
  };

  const colors = {
    error: 'text-red-400 bg-red-500/10',
    network: 'text-orange-400 bg-orange-500/10',
    server: 'text-yellow-400 bg-yellow-500/10',
    empty: 'text-slate-400 bg-slate-500/10',
  };

  const Icon = icons[type];

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-6 ${colors[type]}`}>
        <Icon size={32} />
      </div>

      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-slate-400 max-w-md mb-6">{message}</p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded-lg transition-colors font-medium"
        >
          <RefreshCw size={18} />
          다시 시도
        </button>
      )}
    </div>
  );
};

export const NetworkError: React.FC<{ onRetry?: () => void }> = ({ onRetry }) => (
  <ErrorState
    title="네트워크 오류"
    message="서버에 연결할 수 없습니다. 인터넷 연결을 확인하고 다시 시도해주세요."
    type="network"
    onRetry={onRetry}
  />
);

export const ServerError: React.FC<{ onRetry?: () => void }> = ({ onRetry }) => (
  <ErrorState
    title="서버 오류"
    message="서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    type="server"
    onRetry={onRetry}
  />
);

export const EmptyState: React.FC<{ message?: string }> = ({
  message = '데이터가 없습니다. 분석을 실행해주세요.',
}) => (
  <ErrorState
    title="데이터 없음"
    message={message}
    type="empty"
  />
);

export default ErrorState;
