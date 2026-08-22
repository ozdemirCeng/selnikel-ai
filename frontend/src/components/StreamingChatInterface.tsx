'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Layers,
  ShieldCheck,
  Search,
  Zap,
  Copy,
  Check,
  RotateCcw,
  FileText,
  Bookmark,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
  CornerDownLeft,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationItem } from '@/lib/types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[];
  sources_used?: string[];
  latency_ms?: number;
  isStreaming?: boolean;
}

interface StreamingChatInterfaceProps {
  onSelectCitation: (citation: CitationItem) => void;
}

const SUGGESTED_PROMPTS = [
  {
    title: 'SB-100 Buhar Debisi ve Basınç Limiti',
    query: 'Selnikel SB-100 endüstriyel kazanının buhar debisi ve maksimum işletme basıncı nedir?',
  },
  {
    title: 'Monoblok Brülör Bakım Periyotları',
    query: 'Endüstriyel brülörlerde nozül kontrol ve temizlik periyotları nelerdir?',
  },
  {
    title: 'Kazan Emniyet Ventili Ayar Prosedürü',
    query: 'Buhar kazanlarında emniyet ventillerinin açma basıncı ve periyodik test kuralları nasıldır?',
  },
  {
    title: 'Radyal Fan Basınç Düşüm Eğrileri',
    query: 'Endüstriyel santrifüj ve radyal fanlarda debi ve basınç düşüm ilişkisi nasıldır?',
  },
];

export default function StreamingChatInterface({
  onSelectCitation,
}: StreamingChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [department, setDepartment] = useState<string>('all');
  const [retrievalStatus, setRetrievalStatus] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, retrievalStatus]);

  const handleSend = async (queryText?: string) => {
    const query = (queryText || inputQuery).trim();
    if (!query || isStreaming) return;

    setInputQuery('');
    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    // 1. Add User Message
    const userMsg: Message = {
      id: userMsgId,
      role: 'user',
      content: query,
    };

    // 2. Add placeholder Assistant Message
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    setRetrievalStatus('Qdrant hibrit indeksleri ve BGE-M3 taranıyor...');

    try {
      const { streamRAGQuery } = await import('@/lib/api');
      let accumulatedText = '';
      let streamCitations: CitationItem[] = [];

      await streamRAGQuery(
        {
          query: query,
          top_k: 4,
          department: department === 'all' ? undefined : department,
        },
        (token) => {
          accumulatedText += token;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: accumulatedText } : msg
            )
          );
        },
        (citations) => {
          streamCitations = citations;
        }
      );

      // Finalize Message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: accumulatedText,
                citations: streamCitations,
                isStreaming: false,
              }
            : msg
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: `Hata oluştu: ${err.message || 'Yanıt alınamadı.'}`,
                isStreaming: false,
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
      setRetrievalStatus(null);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const renderCitationPills = (citations?: CitationItem[]) => {
    if (!citations || citations.length === 0) return null;

    return (
      <div className="mt-4 pt-3.5 border-t border-white/[0.08] flex flex-wrap items-center gap-2">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-1.5 mr-1">
          <Bookmark className="w-3 h-3 text-cyan-400" />
          Doğrulanmış Kaynaklar:
        </span>
        {citations.map((cite, idx) => (
          <button
            key={idx}
            onClick={() => onSelectCitation(cite)}
            className="px-2.5 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/25 text-cyan-300 text-[11px] font-medium transition-all flex items-center gap-1.5 shadow-sm group hover:border-cyan-400/40"
          >
            <span className="font-mono text-cyan-400 font-bold">[{idx + 1}]</span>
            <span className="truncate max-w-[150px]">{cite.filename}</span>
            <span className="text-cyan-400/70 text-[10px] font-mono">(S. {cite.page_number})</span>
            <ChevronRight className="w-3 h-3 text-cyan-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition" />
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-13rem)] glass-panel rounded-2xl shadow-2xl overflow-hidden border border-white/[0.08]">
      {/* Scope Header */}
      <div className="px-6 py-3.5 border-b border-white/[0.08] bg-[#0c0f18]/90 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 text-cyan-400 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white tracking-tight">Mühendislik Soru & Cevap Stüdyosu</h3>
            <p className="text-[10px] text-slate-400">Grounded RAG &bull; BGE-M3 Hibrit İndeks &bull; FlashRank ONNX</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="bg-[#131722] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">Tüm Departmanlar</option>
            <option value="engineering">Mühendislik / Tasarım</option>
            <option value="production">İmalat / Üretim</option>
            <option value="service">Servis & Bakım</option>
            <option value="sales">Satış & Teklif</option>
          </select>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto py-10">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600/20 to-cyan-500/10 border border-blue-500/30 text-cyan-400 flex items-center justify-center mb-4 shadow-lg shadow-blue-500/10">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="text-base font-extrabold text-white mb-1.5 tracking-tight">
              Selnikel Mühendislik Bilgi Asistanı
            </h3>
            <p className="text-xs text-slate-400 mb-6 leading-relaxed max-w-md">
              Kazan kapasiteleri, brülör bakım talimatları, fan basınç eğrileri ve teknik şartnameler hakkında sorularınızı anında sorun.
            </p>

            {/* Suggested Prompt Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              {SUGGESTED_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(item.query)}
                  className="p-3.5 text-left rounded-xl glass-card hover:border-blue-500/40 text-xs transition group flex items-start gap-2.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0 opacity-70 group-hover:opacity-100" />
                  <div>
                    <div className="font-semibold text-white group-hover:text-cyan-300 transition text-[11px]">
                      {item.title}
                    </div>
                    <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">
                      {item.query}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-700 to-cyan-600 text-white flex items-center justify-center shrink-0 mt-1 shadow-md shadow-blue-600/20 border border-white/20">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-3xl rounded-2xl p-5 text-xs ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-600/15 border border-blue-400/20'
                    : 'bg-[#0f131f]/90 border border-white/[0.08] text-slate-200 shadow-xl'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center justify-between text-[11px] mb-2.5 pb-2 border-b border-white/[0.06] opacity-70">
                  <span className="font-bold tracking-tight">
                    {msg.role === 'user' ? 'Mühendis' : 'Selnikel AI Copilot'}
                  </span>
                  {msg.role === 'assistant' && (
                    <button
                      onClick={() => handleCopy(msg.content, msg.id)}
                      className="hover:opacity-100 transition p-1 rounded hover:bg-white/[0.06]"
                      title="Kopyala"
                    >
                      {copiedId === msg.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </button>
                  )}
                </div>

                {/* Markdown Body */}
                <div className="prose prose-invert prose-xs max-w-none text-xs leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {/* Loading Indicator */}
                {msg.isStreaming && (
                  <div className="flex items-center gap-2 mt-3.5 text-cyan-400 font-medium">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Teknik yanıt oluşturuluyor...</span>
                  </div>
                )}

                {/* Verified Citations Bar */}
                {renderCitationPills(msg.citations)}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-[#161a29] border border-white/[0.1] text-slate-300 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))
        )}

        {/* Live Retrieval Status Banner */}
        {retrievalStatus && (
          <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-cyan-300 text-xs flex items-center gap-2 animate-pulse">
            <Zap className="w-4 h-4 shrink-0 text-cyan-400" />
            <span className="font-mono text-[11px]">{retrievalStatus}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 border-t border-white/[0.08] bg-[#0c0f18]/90 backdrop-blur-md">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3"
        >
          <input
            ref={inputRef}
            type="text"
            placeholder="Bir teknik soru veya ekipman parametresi sorun (ör. SB-100 debisi)..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isStreaming}
            className="flex-1 px-4 py-3 bg-[#131722] border border-white/[0.08] rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition"
          />

          <button
            type="submit"
            disabled={!inputQuery.trim() || isStreaming}
            className="px-5 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 disabled:opacity-50 flex items-center gap-2 transition"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Sor</span>
                <CornerDownLeft className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
