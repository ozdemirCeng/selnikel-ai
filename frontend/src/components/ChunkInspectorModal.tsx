'use client';

import React, { useEffect, useState } from 'react';
import { X, FileText, Layers, Hash, Copy, Check, Eye, Code, Loader2, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { DocumentChunkItem } from '@/lib/types';
import { fetchDocumentChunks } from '@/lib/api';

interface ChunkInspectorModalProps {
  documentId: string | null;
  filename: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChunkInspectorModal({
  documentId,
  filename,
  isOpen,
  onClose,
}: ChunkInspectorModalProps) {
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen && documentId) {
      loadChunks(documentId);
    } else {
      setChunks([]);
      setError(null);
    }
  }, [isOpen, documentId]);

  const loadChunks = async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchDocumentChunks(id);
      setChunks(data);
    } catch (err: any) {
      setError(err.message || 'Parçalar yüklenirken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  if (!isOpen) return null;

  const filteredChunks = chunks.filter(
    (c) =>
      c.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.section && c.section.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-[#1e1f20] border border-[#2d2f31] text-[#e3e3e3] rounded-3xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#282a2c] flex items-center justify-between bg-[#1e1f20]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#282a2c] flex items-center justify-center text-[#a8c7fa]">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-medium text-white truncate max-w-lg">
                {filename} &bull; Vektör Parça Müfettişi
              </h2>
              <p className="text-[11px] text-[#8e918f]">
                Toplam {chunks.length} parça &bull; Docling Ayrıştırması
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action and Filter Bar */}
        <div className="p-4 border-b border-[#282a2c] bg-[#131314] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#8e918f] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Parça içeriği veya başlıkta ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#1e1f20] border border-[#2d2f31] rounded-full text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
            />
          </div>

          <div className="flex items-center bg-[#1e1f20] border border-[#2d2f31] rounded-full p-0.5 text-xs">
            <button
              onClick={() => setViewMode('rendered')}
              className={`px-3 py-1 rounded-full font-medium transition ${
                viewMode === 'rendered' ? 'bg-[#a8c7fa] text-[#041e49] font-semibold' : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Görsel (Markdown)
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`px-3 py-1 rounded-full font-medium transition ${
                viewMode === 'raw' ? 'bg-[#a8c7fa] text-[#041e49] font-semibold' : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Ham Metin (Raw)
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[#131314]">
          {isLoading ? (
            <div className="h-48 flex items-center justify-center gap-2 text-xs text-[#8e918f]">
              <Loader2 className="w-5 h-5 animate-spin text-[#a8c7fa]" />
              <span>Parçalar yükleniyor...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              {error}
            </div>
          ) : filteredChunks.length === 0 ? (
            <div className="text-center py-12 text-xs text-[#8e918f]">
              Eşleşen parça bulunamadı.
            </div>
          ) : (
            filteredChunks.map((chunk) => (
              <div
                key={chunk.id}
                className="bg-[#1e1f20] border border-[#282a2c] rounded-2xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between pb-2 border-b border-[#282a2c]">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2.5 py-0.5 rounded-full bg-[#282a2c] text-[#a8c7fa] font-mono text-[10px] font-bold border border-[#37393b]">
                      Parça #{chunk.chunk_index}
                    </span>
                    {chunk.page_number && (
                      <span className="text-[11px] text-[#8e918f]">
                        Sayfa: {chunk.page_number}
                      </span>
                    )}
                    {chunk.section && (
                      <span className="text-[11px] text-[#c4c7c5] font-medium truncate max-w-xs">
                        &bull; {chunk.section}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => handleCopy(chunk.content, chunk.id)}
                    className="p-1 rounded text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
                    title="Parçayı Kopyala"
                  >
                    {copiedId === chunk.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                {viewMode === 'rendered' ? (
                  <div className="prose prose-invert prose-xs max-w-none text-xs leading-relaxed text-[#e3e3e3]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {chunk.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <pre className="p-3 bg-[#131314] rounded-xl text-[11px] font-mono text-[#c4c7c5] whitespace-pre-wrap">
                    {chunk.content}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
