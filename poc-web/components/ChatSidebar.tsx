import React, { useState, useEffect, useRef } from 'react';
import { X, Send, Bot, User, Sparkles } from 'lucide-react';
import { ChatMessage, AnalysisReport } from '../types';
import * as GeminiService from '../services/geminiService';
import ReactMarkdown from 'react-markdown';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  report: Partial<AnalysisReport>;
}

const ChatSidebar: React.FC<Props> = ({ isOpen, onClose, report }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'model', text: '안녕하세요! 생성된 투자 리포트에 대해 궁금한 점이 있으신가요? 종목의 **밸류에이션**이나 **리스크**에 대해 질문해주세요.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: ChatMessage = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      if (!report.finalTop3) {
         setMessages(prev => [...prev, { role: 'model', text: '먼저 시장 분석을 실행하여 리포트를 생성해주세요.' }]);
         setLoading(false);
         return;
      }

      const response = await GeminiService.chatWithAnalyst(report as AnalysisReport, userMsg.text, messages);
      setMessages(prev => [...prev, { role: 'model', text: response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'model', text: '오류가 발생했습니다. 잠시 후 다시 시도해주세요.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div 
      className={`fixed top-0 right-0 h-full w-96 bg-slate-900 border-l border-slate-800 shadow-2xl transform transition-transform duration-300 z-50 flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <h3 className="text-white font-bold flex items-center gap-2">
          <Sparkles className="text-emerald-500" size={18} />
          AI 투자 상담
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-grow overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'model' ? 'bg-emerald-600' : 'bg-blue-600'}`}>
              {msg.role === 'model' ? <Bot size={16} /> : <User size={16} />}
            </div>
            <div className={`max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed ${
              msg.role === 'model' 
                ? 'bg-slate-800 text-slate-200 rounded-tl-none' 
                : 'bg-blue-600 text-white rounded-tr-none'
            }`}>
              {msg.role === 'model' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
              ) : (
                  msg.text
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
             <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0">
               <Bot size={16} />
             </div>
             <div className="bg-slate-800 rounded-2xl p-3 rounded-tl-none flex items-center gap-1">
               <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></div>
               <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-75"></div>
               <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-150"></div>
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-slate-950 border-t border-slate-800">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="궁금한 내용을 물어보세요..."
            className="w-full bg-slate-800 text-white rounded-xl py-3 pl-4 pr-12 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none h-12"
          />
          <button 
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="absolute right-2 top-2 p-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatSidebar;