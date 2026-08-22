'use client';

import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  FileText,
  FileSpreadsheet,
  Presentation,
  CheckCircle2,
  Sparkles,
  Layers,
  UploadCloud,
  Download,
  Copy,
  Check,
  Loader2,
  SlidersHorizontal,
  FolderOpen,
  ShieldCheck,
  FileCheck,
  Send,
  CornerDownLeft,
  Bot,
  User,
  Plus,
  RefreshCw,
  Eye,
  Hash,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationItem, DocumentItem } from '@/lib/types';
import {
  downloadExcelReport,
  downloadPdfReport,
  downloadPowerPointReport,
  downloadWordReport,
  fetchDocuments,
} from '@/lib/api';
import DocumentUploadModal from './DocumentUploadModal';
import ChunkInspectorModal from './ChunkInspectorModal';

interface StudioMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[];
}

export default function NotebookLMStudio() {
  // Sources State
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<Record<string, boolean>>({});
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Inspector Modal
  const [inspectDocId, setInspectDocId] = useState<string | null>(null);
  const [inspectDocName, setInspectDocName] = useState('');

  // Conversation State
  const [messages, setMessages] = useState<StudioMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // Active Studio Artifact Content
  const [studioArtifact, setStudioArtifact] = useState<string>(
    `# Selnikel Teknik Çalışma Kılavuzu & Mühendislik Brifingi\n\nBu stüdyo paneli, sol tarafta seçtiğiniz teknik kaynaklardan otomatik olarak **Excel Tabloları**, **Word Şartnameleri**, **PowerPoint Sunumları** ve **Resmi PDF Raporları** üretmenizi sağlar.\n\n### Öne Çıkan Özellikler\n- **Çoklu Kaynak Filtreleme**: Sadece işaretli dokümanlar üzerinden zeminleme.\n- **Tek Tıkla Dışa Aktarma**: Sağ üstteki format butonları ile resmi şirket şablonlarında indirme.\n- **Görsel & Tablo Koruma**: Docling ayrıştırması ile teknik değerler korunur.`
  );
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    setIsLoadingDocs(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      // Select all by default
      const initialMap: Record<string, boolean> = {};
      docs.forEach((d) => {
        initialMap[d.id] = true;
      });
      setSelectedDocIds(initialMap);
    } catch (e) {
      console.error('Failed to load documents for studio', e);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const selectAllDocs = (selected: boolean) => {
    const newMap: Record<string, boolean> = {};
    documents.forEach((d) => {
      newMap[d.id] = selected;
    });
    setSelectedDocIds(newMap);
  };

  const selectedCount = Object.values(selectedDocIds).filter(Boolean).length;

  const handleSend = async (customQuery?: string) => {
    const query = (customQuery || inputQuery).trim();
    if (!query || isStreaming) return;

    setInputQuery('');
    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', content: query },
      { id: assistantMsgId, role: 'assistant', content: '' },
    ]);
    setIsStreaming(true);

    try {
      const { streamRAGQuery } = await import('@/lib/api');
      let accumulated = '';
      let streamCitations: CitationItem[] = [];

      const activeDocIds = Object.keys(selectedDocIds).filter((id) => selectedDocIds[id]);

      await streamRAGQuery(
        {
          query: query,
          document_ids: activeDocIds.length > 0 ? activeDocIds : undefined,
          top_k: 5,
        },
        (token) => {
          accumulated += token;
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMsgId ? { ...m, content: accumulated } : m))
          );
        },
        (citations) => {
          streamCitations = citations;
        }
      );

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId ? { ...m, content: accumulated, citations: streamCitations } : m
        )
      );
      // Update active studio artifact with the latest answer
      if (accumulated) {
        setStudioArtifact(accumulated);
      }
    } catch (e: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId ? { ...m, content: `Hata: ${e.message || 'Yanıt alınamadı.'}` } : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleExport = async (format: 'excel' | 'word' | 'pptx' | 'pdf') => {
    setIsExporting(format);
    try {
      if (format === 'excel') {
        await downloadExcelReport(studioArtifact, 'Selnikel Mühendislik Tabloları');
      } else if (format === 'word') {
        await downloadWordReport(studioArtifact, 'Selnikel Teknik Şartname Raporu');
      } else if (format === 'pptx') {
        await downloadPowerPointReport(studioArtifact, 'Selnikel Mühendislik Sunumu');
      } else if (format === 'pdf') {
        await downloadPdfReport(studioArtifact, 'Selnikel Resmi Teknik Raporu');
      }
    } catch (err: any) {
      alert(`Dışa aktarma hatası: ${err.message}`);
    } finally {
      setIsExporting(null);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(studioArtifact);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start h-[calc(100vh-13rem)]">
      {/* 1. LEFT PANE: Sources Rail (NotebookLM Style) */}
      <div className="lg:col-span-3 h-full glass-panel rounded-2xl flex flex-col overflow-hidden border border-white/[0.08] shadow-2xl">
        <div className="px-4 py-3.5 border-b border-white/[0.08] bg-[#0c0f18] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white tracking-tight">Kaynaklar</h3>
          </div>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/15 text-cyan-300 border border-cyan-500/25">
            {selectedCount} / {documents.length}
          </span>
        </div>

        {/* Source Action Bar */}
        <div className="p-3 border-b border-white/[0.06] bg-[#101422] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={() => selectAllDocs(true)}
              className="text-[10px] text-cyan-400 hover:underline font-medium"
            >
              Tümünü Seç
            </button>
            <span className="text-slate-600">&bull;</span>
            <button
              onClick={() => selectAllDocs(false)}
              className="text-[10px] text-slate-400 hover:underline"
            >
              Temizle
            </button>
          </div>

          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-cyan-300 border border-blue-500/30 text-[10px] font-bold flex items-center gap-1 transition"
          >
            <Plus className="w-3 h-3" />
            Kaynak Ekle
          </button>
        </div>

        {/* Source Checkbox List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoadingDocs ? (
            <div className="h-32 flex items-center justify-center gap-2 text-slate-500 text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              <span>Yükleniyor...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center p-6 text-slate-500 text-xs">
              Henüz kaynak yüklenmedi.
            </div>
          ) : (
            documents.map((doc) => {
              const isChecked = !!selectedDocIds[doc.id];
              return (
                <div
                  key={doc.id}
                  className={`p-2.5 rounded-xl border transition flex items-start gap-2.5 ${
                    isChecked
                      ? 'bg-[#131722] border-cyan-500/30 shadow-sm'
                      : 'bg-transparent border-white/[0.04] opacity-60 hover:opacity-100'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleDocSelection(doc.id)}
                    className="mt-1 rounded border-slate-700 text-blue-600 focus:ring-0 focus:ring-offset-0 bg-[#0c0f18]"
                  />
                  <div className="flex-1 overflow-hidden">
                    <div className="text-xs font-semibold text-white truncate">
                      {doc.filename}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                      <span>{doc.department}</span>
                      <span>&bull;</span>
                      <span>{doc.total_pages || 1} s.</span>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setInspectDocId(doc.id);
                      setInspectDocName(doc.filename);
                    }}
                    className="p-1 rounded text-slate-500 hover:text-cyan-400 transition"
                    title="Parçaları İncele"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 2. CENTER PANE: Grounded Conversation */}
      <div className="lg:col-span-5 h-full glass-panel rounded-2xl flex flex-col overflow-hidden border border-white/[0.08] shadow-2xl">
        <div className="px-4 py-3.5 border-b border-white/[0.08] bg-[#0c0f18] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white tracking-tight">Grounded Sohbet & Soru-Cevap</h3>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">
            {selectedCount} Aktif Kaynak
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <Sparkles className="w-8 h-8 text-cyan-400/60 mb-2" />
              <h4 className="font-bold text-slate-200 text-xs mb-1">NotebookLM Tarzı Çalışma Alanı</h4>
              <p className="text-[11px] text-slate-400 max-w-xs leading-relaxed">
                Sol panelden seçtiğiniz dokümanlar hakkında soru sorun. Yanıtlar anında sağdaki Stüdyo kartına aktarılır.
              </p>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`p-3.5 rounded-xl ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white ml-6 font-medium'
                    : 'bg-[#131722] border border-white/[0.06] text-slate-200 mr-4'
                }`}
              >
                <div className="font-bold text-[10px] mb-1 opacity-75">
                  {m.role === 'user' ? 'Mühendis' : 'Selnikel AI'}
                </div>
                <div className="prose prose-invert prose-xs max-w-none text-xs leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input */}
        <div className="p-3 border-t border-white/[0.08] bg-[#0c0f18]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Seçili kaynaklar hakkında soru sorun..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isStreaming}
              className="flex-1 px-3 py-2 bg-[#131722] border border-white/[0.08] rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isStreaming}
              className="p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl transition"
            >
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CornerDownLeft className="w-4 h-4" />
              )}
            </button>
          </form>
        </div>
      </div>

      {/* 3. RIGHT PANE: NotebookLM Studio Artifacts & Exporters */}
      <div className="lg:col-span-4 h-full glass-panel rounded-2xl flex flex-col overflow-hidden border border-white/[0.08] shadow-2xl">
        {/* Header with Multi-Format Export Buttons */}
        <div className="px-4 py-3 border-b border-white/[0.08] bg-[#0c0f18]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold text-white tracking-tight">Stüdyo Çıktıları</h3>
            </div>
            <button
              onClick={handleCopy}
              className="p-1 rounded text-slate-400 hover:text-white transition"
              title="Kopyala"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Export Action Bar (Excel, Word, PPTX, PDF) */}
          <div className="grid grid-cols-4 gap-1.5 pt-1">
            <button
              onClick={() => handleExport('excel')}
              disabled={!!isExporting}
              className="px-2 py-1.5 rounded-lg bg-[#131722] hover:bg-emerald-600/20 border border-white/[0.08] hover:border-emerald-500/40 text-emerald-300 text-[10px] font-bold flex flex-col items-center gap-1 transition"
              title="Excel (.xlsx) Tablosu Olarak İndir"
            >
              {isExporting === 'excel' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
              <span>.XLSX</span>
            </button>

            <button
              onClick={() => handleExport('word')}
              disabled={!!isExporting}
              className="px-2 py-1.5 rounded-lg bg-[#131722] hover:bg-blue-600/20 border border-white/[0.08] hover:border-blue-500/40 text-cyan-300 text-[10px] font-bold flex flex-col items-center gap-1 transition"
              title="Word (.docx) Raporu Olarak İndir"
            >
              {isExporting === 'word' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
              <span>.DOCX</span>
            </button>

            <button
              onClick={() => handleExport('pptx')}
              disabled={!!isExporting}
              className="px-2 py-1.5 rounded-lg bg-[#131722] hover:bg-amber-600/20 border border-white/[0.08] hover:border-amber-500/40 text-amber-300 text-[10px] font-bold flex flex-col items-center gap-1 transition"
              title="PowerPoint (.pptx) Sunumu Olarak İndir"
            >
              {isExporting === 'pptx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Presentation className="w-3.5 h-3.5" />}
              <span>.PPTX</span>
            </button>

            <button
              onClick={() => handleExport('pdf')}
              disabled={!!isExporting}
              className="px-2 py-1.5 rounded-lg bg-[#131722] hover:bg-rose-600/20 border border-white/[0.08] hover:border-rose-500/40 text-rose-300 text-[10px] font-bold flex flex-col items-center gap-1 transition"
              title="PDF (.pdf) Raporu Olarak İndir"
            >
              {isExporting === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileCheck className="w-3.5 h-3.5" />}
              <span>.PDF</span>
            </button>
          </div>
        </div>

        {/* Live Rendered Artifact */}
        <div className="flex-1 overflow-y-auto p-4 prose prose-invert prose-xs max-w-none text-xs leading-relaxed bg-[#0c0f18]/60">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {studioArtifact}
          </ReactMarkdown>
        </div>
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={loadSources}
      />

      {/* Chunk Inspector Modal */}
      <ChunkInspectorModal
        documentId={inspectDocId}
        filename={inspectDocName}
        isOpen={!!inspectDocId}
        onClose={() => {
          setInspectDocId(null);
          setInspectDocName('');
        }}
      />
    </div>
  );
}
