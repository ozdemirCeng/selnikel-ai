'use client';

import React, { useEffect, useState } from 'react';
import {
  FileText,
  Search,
  X,
  ArrowLeft,
  Copy,
  Check,
  Download,
  Loader2,
  ExternalLink,
  BookOpen,
  Sparkles,
  Layers,
  FileSpreadsheet,
  CornerDownLeft,
  ChevronRight,
  Hash,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { DocumentChunkItem } from '@/lib/types';
import { fetchDocumentChunks, downloadExcelReport } from '@/lib/api';

interface NotebookLMSourceReaderProps {
  documentId: string;
  filename: string;
  department?: string;
  totalPages?: number;
  highlightSnippet?: string;
  onClose: () => void;
  onAskAboutDoc?: (query: string) => void;
}

export default function NotebookLMSourceReader({
  documentId,
  filename,
  department = 'Mühendislik',
  totalPages = 1,
  highlightSnippet,
  onClose,
  onAskAboutDoc,
}: NotebookLMSourceReaderProps) {
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activePage, setActivePage] = useState<number | 'all'>('all');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadContent();
  }, [documentId]);

  const loadContent = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchDocumentChunks(documentId);
      setChunks(data);
    } catch (err: any) {
      setError(err.message || 'Doküman içeriği yüklenemedi.');
    } finally {
      setIsLoading(false);
    }
  };

  const pages = Array.from(
    new Set(chunks.map((c) => c.page_number).filter(Boolean))
  ).sort((a, b) => (a as number) - (b as number)) as number[];

  const filteredChunks = chunks.filter((c) => {
    const matchesPage = activePage === 'all' || c.page_number === activePage;
    const matchesSearch =
      !searchQuery ||
      c.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.section && c.section.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesPage && matchesSearch;
  });

  const fullDocumentMarkdown = chunks.map((c) => c.content).join('\n\n---\n\n');

  const handleCopy = () => {
    navigator.clipboard.writeText(fullDocumentMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportExcel = async () => {
    try {
      await downloadExcelReport(fullDocumentMarkdown, `${filename} Veri Tablosu`);
    } catch (e: any) {
      alert(`Excel export failed: ${e.message}`);
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1e1f20] text-[#e3e3e3] rounded-2xl overflow-hidden border border-[#2d2f31]">
      {/* 1. Header Toolbar */}
      <div className="p-3.5 border-b border-[#282a2c] bg-[#1e1f20] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-[#282a2c] text-[#8e918f] hover:text-white transition shrink-0"
            title="Kaynak Listesine Dön"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="overflow-hidden">
            <h3 className="text-xs font-semibold text-white truncate flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#a8c7fa] shrink-0" />
              <span className="truncate">{filename}</span>
            </h3>
            <div className="flex items-center gap-2 text-[10px] text-[#8e918f] mt-0.5">
              <span>{department}</span>
              <span>&bull;</span>
              <span>{chunks.length} Parça</span>
              {totalPages > 0 && (
                <>
                  <span>&bull;</span>
                  <span>{totalPages} Sayfa</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
            title="Tüm Doküman Metnini Kopyala"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleExportExcel}
            className="p-1.5 rounded-lg text-[#8e918f] hover:text-emerald-400 hover:bg-[#282a2c] transition"
            title="Tabloları Excel Olarak İndir"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-[#282a2c] text-[#8e918f] hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. In-Document Search & Page Navigation Bar */}
      <div className="p-2.5 border-b border-[#282a2c] bg-[#131314] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-[#8e918f] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Doküman içinde ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#1e1f20] border border-[#2d2f31] rounded-full text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
          />
        </div>

        {/* Page Jump Pills */}
        {pages.length > 1 && (
          <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
            <button
              onClick={() => setActivePage('all')}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition ${
                activePage === 'all'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'bg-[#1e1f20] text-[#8e918f] hover:text-white'
              }`}
            >
              Tümü
            </button>
            {pages.map((p, pIdx) => (
              <button
                key={`page-${p}-${pIdx}`}
                onClick={() => setActivePage(p)}
                className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition ${
                  activePage === p
                    ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                    : 'bg-[#1e1f20] text-[#8e918f] hover:text-white'
                }`}
              >
                S.{p}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 3. Quick Action Chips (Ask AI about this specific doc) */}
      {onAskAboutDoc && (
        <div className="px-3 py-2 border-b border-[#282a2c] bg-[#18191b] flex items-center gap-1.5 overflow-x-auto">
          <span className="text-[10px] text-[#8e918f] font-medium shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-[#a8c7fa]" />
            Hızlı İstek:
          </span>
          <button
            onClick={() => onAskAboutDoc(`"${filename}" dokümanının teknik yönetici özetini çıkar ve önemli parametreleri listele.`)}
            className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[10px] text-[#c4c7c5] hover:text-white transition shrink-0"
          >
            Yönetici Özeti Çıkar
          </button>
          <button
            onClick={() => onAskAboutDoc(`"${filename}" dokümanındaki tüm sayısal ve teknik tabloları analiz et.`)}
            className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[10px] text-[#c4c7c5] hover:text-white transition shrink-0"
          >
            Teknik Tabloları İncele
          </button>
          <button
            onClick={() => onAskAboutDoc(`"${filename}" dokümanına göre bakım, emniyet ve işletme talimatlarını özetle.`)}
            className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[10px] text-[#c4c7c5] hover:text-white transition shrink-0"
          >
            Bakım & Emniyet Kuralları
          </button>
        </div>
      )}

      {/* 4. Document Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#131314]">
        {isLoading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-2 text-xs text-[#8e918f]">
            <Loader2 className="w-6 h-6 animate-spin text-[#a8c7fa]" />
            <span>Doküman sayfaları ve tabloları yükleniyor...</span>
          </div>
        ) : error ? (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            {error}
          </div>
        ) : filteredChunks.length === 0 ? (
          <div className="text-center py-12 text-xs text-[#8e918f]">
            Arama kriterine uygun içerik bulunamadı.
          </div>
        ) : (
          filteredChunks.map((chunk, idx) => {
            const isHighlighted =
              highlightSnippet &&
              chunk.content.toLowerCase().includes(highlightSnippet.toLowerCase().slice(0, 30));

            return (
              <div
                key={chunk.id || `chunk-${chunk.chunk_index}-${idx}`}
                className={`p-4 rounded-2xl border transition ${
                  isHighlighted
                    ? 'bg-[#282a2c] border-[#a8c7fa] ring-1 ring-[#a8c7fa]'
                    : 'bg-[#1e1f20] border-[#282a2c]'
                }`}
              >
                {/* Chunk Meta Header */}
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#282a2c]/60 text-[10px]">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[#a8c7fa] font-bold">
                      Parça #{chunk.chunk_index}
                    </span>
                    {chunk.page_number && (
                      <span className="text-[#8e918f]">
                        &bull; Sayfa {chunk.page_number}
                      </span>
                    )}
                    {chunk.section && (
                      <span className="text-[#c4c7c5] font-medium truncate max-w-xs">
                        &bull; {chunk.section}
                      </span>
                    )}
                  </div>

                  <span className="text-[#8e918f] font-mono">
                    {chunk.token_count || 0} token
                  </span>
                </div>

                {/* Rendered Markdown Body */}
                <div className="prose prose-invert prose-xs max-w-none text-xs leading-relaxed text-[#e3e3e3]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {chunk.content}
                  </ReactMarkdown>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
