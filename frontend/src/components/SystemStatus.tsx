'use client';

import React, { useEffect, useState } from 'react';
import { HealthCheckResponse, QueryHistoryItem } from '@/lib/types';
import { fetchHealth, fetchQueryHistory } from '@/lib/api';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Database,
  Cpu,
  Layers,
  Activity,
  Clock,
  Zap,
  Loader2,
} from 'lucide-react';

export default function SystemStatus() {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, historyData] = await Promise.all([
        fetchHealth(),
        fetchQueryHistory().catch(() => []),
      ]);
      setHealth(healthData);
      setHistory(historyData);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err.message || 'Backend bağlantısı sağlanamadı.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    if (status === 'healthy') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Aktif & Sağlıklı
        </span>
      );
    }
    if (status === 'degraded' || status === 'disabled') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
          <AlertTriangle className="w-3.5 h-3.5" />
          Kısmi
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">
        <XCircle className="w-3.5 h-3.5" />
        Hata
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-3xl p-6 text-[#e3e3e3] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-2xl bg-[#282a2c] border border-[#37393b] flex items-center justify-center text-[#a8c7fa]">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-tight">
              Sistem Sağlığı & Canlı Telemetri
            </h1>
            <p className="text-xs text-[#8e918f] mt-0.5">
              PostgreSQL 16, Qdrant Vektör Motoru, FlashRank Yeniden Sıralayıcı ve LLM sağlayıcı sağlık durumu
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-[11px] text-[#8e918f] font-mono">
              Son Güncelleme: {lastUpdated.toLocaleTimeString('tr-TR')}
            </span>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[#c4c7c5] hover:text-white transition border border-[#37393b]"
            title="Yenile"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <XCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 3 Core Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. PostgreSQL */}
        <div className="p-5 rounded-3xl bg-[#1e1f20] border border-[#2d2f31] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white font-medium text-xs">
              <Database className="w-4 h-4 text-blue-400" />
              <span>PostgreSQL 16</span>
            </div>
            {health ? getStatusBadge(health.components.database.status) : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          </div>
          <p className="text-[11px] text-[#8e918f] leading-relaxed">
            Doküman üstverileri, SHA-256 deduplikasyon kayıtları ve sorgu logları.
          </p>
        </div>

        {/* 2. Qdrant */}
        <div className="p-5 rounded-3xl bg-[#1e1f20] border border-[#2d2f31] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white font-medium text-xs">
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Qdrant V1.11.0</span>
            </div>
            {health ? getStatusBadge(health.components.vector_db.status) : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          </div>
          <p className="text-[11px] text-[#8e918f] leading-relaxed">
            BGE-M3 1024-boyutlu yoğun ve BM25 seyrek vektör koleksiyonları.
          </p>
        </div>

        {/* 3. LLM Provider */}
        <div className="p-5 rounded-3xl bg-[#1e1f20] border border-[#2d2f31] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white font-medium text-xs">
              <Cpu className="w-4 h-4 text-teal-400" />
              <span>LLM Katmanı</span>
            </div>
            {health ? getStatusBadge(health.components.llm_provider.status) : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          </div>
          <p className="text-[11px] text-[#8e918f] leading-relaxed">
            Detay: <span className="text-white font-mono">{health?.components.llm_provider.details || 'GPT-4o-mini'}</span>
          </p>
        </div>
      </div>

      {/* Audit Query History */}
      <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#282a2c]">
          <div className="flex items-center gap-2 text-white font-semibold text-xs">
            <Clock className="w-4 h-4 text-[#a8c7fa]" />
            <span>Son Sorgu ve Zeminleme Kayıtları (Audit Log)</span>
          </div>
          <span className="text-[11px] font-mono text-[#8e918f]">
            {history.length} Kayıt
          </span>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-8 text-xs text-[#8e918f]">
            Henüz denetim kaydı bulunmuyor.
          </div>
        ) : (
          <div className="divide-y divide-[#282a2c] max-h-80 overflow-y-auto">
            {history.map((item) => (
              <div key={item.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="space-y-0.5">
                  <div className="text-white font-medium truncate max-w-md">
                    {item.query_text}
                  </div>
                  <div className="text-[10px] text-[#8e918f]">
                    {new Date(item.created_at).toLocaleString('tr-TR')} &bull; Model: {item.llm_model}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-[#282a2c] text-[10px] text-emerald-400 border border-[#37393b]">
                    {item.retrieved_chunk_ids?.length || 0} Kaynak
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-[#282a2c] text-[10px] text-[#a8c7fa] border border-[#37393b]">
                    {item.latency_ms ? `${item.latency_ms.toFixed(0)} ms` : '-'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
