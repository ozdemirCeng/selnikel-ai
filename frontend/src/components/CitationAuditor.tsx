'use client';

import React from 'react';
import { X, FileText, CheckCircle2, ShieldCheck, ExternalLink, Bookmark, Hash, ArrowUpRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationItem } from '@/lib/types';

interface CitationAuditorProps {
  citation: CitationItem | null;
  onClose: () => void;
  onInspectDocument?: (docId: string, filename: string) => void;
}

export default function CitationAuditor({
  citation,
  onClose,
  onInspectDocument,
}: CitationAuditorProps) {
  if (!citation) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center bg-[#0e111a]/40 text-slate-500">
        <div className="w-12 h-12 rounded-2xl bg-[#131722] border border-white/[0.08] flex items-center justify-center mb-3 text-slate-400 shadow-inner">
          <Bookmark className="w-5 h-5 text-cyan-400/80" />
        </div>
        <h4 className="text-xs font-bold text-slate-200 mb-1 tracking-tight">Kaynak & Tablo Denetleyicisi</h4>
        <p className="text-[11px] text-slate-400 max-w-[220px] leading-relaxed">
          Cevaptaki bir alıntı etiketine <span className="text-cyan-400 font-mono font-bold">[1]</span> tıklayarak orijinal teknik sayfa ve tablo detaylarını burada yan yana denetleyebilirsiniz.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#0e111a]/95 backdrop-blur-xl animate-in slide-in-from-right-4 duration-200">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#131722]/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-cyan-400 flex items-center justify-center">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-white truncate max-w-[170px] tracking-tight">
                {citation.filename}
              </h4>
              <span className="px-2 py-0.2 rounded bg-cyan-500/15 text-cyan-300 font-mono text-[10px] font-bold border border-cyan-500/25">
                S. {citation.page_number}
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Doğrulanmış Teknik Kaynak</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
        {/* Verification Status Card */}
        <div className="p-3.5 rounded-xl bg-[#131722] border border-white/[0.08] flex items-center justify-between shadow-md">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-200 font-semibold text-xs">Zemin Doğrulaması</span>
          </div>
          {citation.score && (
            <span className="text-[11px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-md border border-emerald-500/25">
              Alaka: %{(citation.score * 100).toFixed(0)}
            </span>
          )}
        </div>

        {/* Section Info */}
        {citation.section && (
          <div>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Bölüm / Başlık
            </span>
            <div className="p-2.5 rounded-lg bg-[#131722]/80 border border-white/[0.06] text-slate-200 font-medium">
              {citation.section}
            </div>
          </div>
        )}

        {/* Snippet & Preserved Table */}
        <div>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
            Alıntılanan Orijinal Metin & Tablo
          </span>
          <div className="p-4 rounded-xl bg-[#131722] border border-white/[0.08] prose prose-invert prose-xs max-w-none text-slate-200 text-xs leading-relaxed overflow-x-auto shadow-inner">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {citation.snippet}
            </ReactMarkdown>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-white/[0.08] bg-[#131722]/90 flex items-center justify-between">
        <span className="text-[10px] text-slate-500 font-mono truncate max-w-[120px]">
          ID: {citation.document_id.slice(0, 8)}...
        </span>
        {onInspectDocument && citation.document_id !== 'unverified' && (
          <button
            onClick={() => onInspectDocument(citation.document_id, citation.filename)}
            className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-md shadow-blue-500/20"
          >
            Tüm Parçaları Aç
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
