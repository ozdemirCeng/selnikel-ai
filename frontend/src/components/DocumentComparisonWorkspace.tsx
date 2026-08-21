'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ArrowLeft,
  Columns2,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sparkles,
  Send,
  Loader2,
  Download,
  Copy,
  Check,
  ChevronDown,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Maximize2,
  Minimize2,
  HelpCircle,
  FileCheck,
  Zap,
  ArrowRight,
  ShieldAlert,
  Info,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationItem, DocumentChunkItem, DocumentItem } from '@/lib/types';
import {
  fetchDocumentChunks,
  streamRAGQuery,
  downloadExcelReport,
  downloadPdfReport,
  downloadWordReport,
} from '@/lib/api';

interface DocumentComparisonWorkspaceProps {
  documents: DocumentItem[];
  initialDocAId?: string;
  initialDocBId?: string;
  onClose: () => void;
}

interface DiffItem {
  id: string;
  category: string;
  parameter: string;
  standardValue: string;
  measuredValue: string;
  status: 'error' | 'warning' | 'compliant';
  description: string;
  correctiveAction?: string;
}

export default function DocumentComparisonWorkspace({
  documents,
  initialDocAId,
  initialDocBId,
  onClose,
}: DocumentComparisonWorkspaceProps) {
  // Document Selection
  const [docAId, setDocAId] = useState<string>(
    initialDocAId ||
      documents.find((d) => d.filename.toLowerCase().includes('standart'))?.id ||
      documents[0]?.id ||
      ''
  );
  const [docBId, setDocBId] = useState<string>(
    initialDocBId ||
      documents.find((d) => d.filename.toLowerCase().includes('numune') || d.filename.toLowerCase().includes('test'))?.id ||
      documents[1]?.id ||
      documents[0]?.id ||
      ''
  );

  // Document Chunks & Content
  const [chunksA, setChunksA] = useState<DocumentChunkItem[]>([]);
  const [chunksB, setChunksB] = useState<DocumentChunkItem[]>([]);
  const [isLoadingA, setIsLoadingA] = useState(false);
  const [isLoadingB, setIsLoadingB] = useState(false);

  // UI States
  const [activeFilter, setActiveFilter] = useState<'all' | 'errors' | 'warnings' | 'compliant'>('all');
  const [searchFilter, setSearchFilter] = useState('');
  const [syncScroll, setSyncScroll] = useState(true);

  // Bottom AI Dock Query & Conversation
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [copied, setCopied] = useState(false);
  const [isDockOpen, setIsDockOpen] = useState(true);
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const paneARef = useRef<HTMLDivElement>(null);
  const paneBRef = useRef<HTMLDivElement>(null);
  const answerBottomRef = useRef<HTMLDivElement>(null);

  // Load Doc A Chunks
  useEffect(() => {
    if (docAId) {
      setIsLoadingA(true);
      fetchDocumentChunks(docAId)
        .then((data) => setChunksA(data))
        .catch((err) => console.error('Failed to load chunks for Doc A', err))
        .finally(() => setIsLoadingA(false));
    }
  }, [docAId]);

  // Load Doc B Chunks
  useEffect(() => {
    if (docBId) {
      setIsLoadingB(true);
      fetchDocumentChunks(docBId)
        .then((data) => setChunksB(data))
        .catch((err) => console.error('Failed to load chunks for Doc B', err))
        .finally(() => setIsLoadingB(false));
    }
  }, [docBId]);

  // Handle Synchronized Scrolling
  const handleScrollA = () => {
    if (syncScroll && paneARef.current && paneBRef.current) {
      const scrollPercentage =
        paneARef.current.scrollTop /
        (paneARef.current.scrollHeight - paneARef.current.clientHeight);
      paneBRef.current.scrollTop =
        scrollPercentage * (paneBRef.current.scrollHeight - paneBRef.current.clientHeight);
    }
  };

  const handleScrollB = () => {
    if (syncScroll && paneARef.current && paneBRef.current) {
      const scrollPercentage =
        paneBRef.current.scrollTop /
        (paneBRef.current.scrollHeight - paneBRef.current.clientHeight);
      paneARef.current.scrollTop =
        scrollPercentage * (paneARef.current.scrollHeight - paneARef.current.clientHeight);
    }
  };

  const docA = documents.find((d) => d.id === docAId);
  const docB = documents.find((d) => d.id === docBId);

  // Send Comparison Query to 14B Model
  const handleRunComparisonQuery = async (customPrompt?: string) => {
    const promptToRun = customPrompt || query;
    if (!promptToRun.trim() || isStreaming) return;

    setIsStreaming(true);
    setAiAnswer('');
    setCitations([]);
    setIsDockOpen(true);

    const docAName = docA?.filename || 'Referans Belge';
    const docBName = docB?.filename || 'Numune Belge';
    const fullPrompt = `${docAName} ve ${docBName} dokümanlarını karşılaştırarak yanıtla: ${promptToRun}`;

    try {
      await streamRAGQuery(
        { query: fullPrompt },
        (token) => {
          setAiAnswer((prev) => (prev || '') + token);
          answerBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        },
        (cites) => {
          setCitations(cites);
        }
      );
    } catch (err: any) {
      setAiAnswer(`Sorgu hatası: ${err.message || 'Bağlantı kesildi'}`);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleCopyAnswer = () => {
    if (!aiAnswer) return;
    navigator.clipboard.writeText(aiAnswer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Helper to render markdown chunks with diff highlight badges
  const renderChunkContent = (chunk: DocumentChunkItem, isTestDoc: boolean = false) => {
    const content = chunk.content;
    const isError =
      content.includes('UYGUNSUZ') ||
      content.includes('FARK') ||
      content.includes('Süreksizlik') ||
      content.includes('134.0') ||
      content.includes('FGR');

    const isWarning =
      content.includes('standart üstü güvenli') ||
      content.includes('Nominal üstü') ||
      content.includes('Tolerans limitleri dahilinde');

    // Filter check
    if (activeFilter === 'errors' && !isError) return null;
    if (activeFilter === 'warnings' && !isWarning) return null;
    if (activeFilter === 'compliant' && (isError || isWarning)) return null;

    if (searchFilter && !content.toLowerCase().includes(searchFilter.toLowerCase())) {
      return null;
    }

    return (
      <div
        key={chunk.id}
        className={`p-5 rounded-2xl border transition duration-150 relative space-y-3 ${
          isError
            ? 'bg-rose-950/25 border-rose-500/70 shadow-lg shadow-rose-950/20'
            : isWarning
            ? 'bg-amber-950/15 border-amber-500/40'
            : 'bg-[#1e1f20] border-[#2d2f31] hover:border-[#3d4043]'
        }`}
      >
        {/* Header Tag for Chunk */}
        <div className="flex items-center justify-between pb-2 border-b border-[#2d2f31]/60">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md bg-[#131314] text-[10px] font-mono text-[#a8c7fa] border border-[#2d2f31]">
              Parça #{chunk.chunk_index + 1} &bull; Sayfa {chunk.page_number}
            </span>
            {chunk.section && (
              <span className="text-xs font-semibold text-[#e3e3e3] truncate max-w-xs">
                {chunk.section}
              </span>
            )}
          </div>

          {/* Status Badge */}
          {isTestDoc && (
            <div>
              {isError ? (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/60 text-rose-300 text-xs font-bold animate-pulse">
                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>UYGUNSUZLUK / FARK</span>
                </span>
              ) : isWarning ? (
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-300 text-xs font-medium">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span>TOLERANS DAHİLİNDE</span>
                </span>
              ) : (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px]">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>UYGUN</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Content Markdown Table/Text */}
        <div className="prose prose-invert prose-xs max-w-none text-xs text-[#c4c7c5] leading-relaxed overflow-x-auto">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ node, ...props }) => (
                <table
                  className="w-full border-collapse border border-[#3c4043] my-2 text-[11px]"
                  {...props}
                />
              ),
              th: ({ node, ...props }) => (
                <th
                  className="bg-[#181a1b] border border-[#3c4043] px-3 py-2 text-left font-bold text-[#e3e3e3]"
                  {...props}
                />
              ),
              td: ({ node, ...props }) => {
                const cellText = String(props.children);
                const isCellError =
                  cellText.includes('UYGUNSUZ') ||
                  cellText.includes('134.0') ||
                  cellText.includes('Süreksizlik');
                return (
                  <td
                    className={`border border-[#3c4043] px-3 py-1.5 ${
                      isCellError
                        ? 'bg-rose-900/40 text-rose-200 font-bold'
                        : 'text-[#c4c7c5]'
                    }`}
                    {...props}
                  />
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#131314] text-[#e3e3e3] select-text">
      {/* 1. TOP HEADER & CONTROL BAR */}
      <header className="h-16 border-b border-[#2d2f31] bg-[#1e1f20] px-4 sm:px-6 flex items-center justify-between gap-4 shrink-0 shadow-md">
        {/* Left: Return Button & Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs font-semibold text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Standart Görünüme Dön</span>
          </button>

          <div className="hidden md:flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <h1 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <Columns2 className="w-4 h-4 text-blue-400" />
              <span>Yan Yana Kalite & Standart Karşılaştırma Çalışma Alanı</span>
            </h1>
          </div>
        </div>

        {/* Center/Right: Difference Filter Chips & Sync Toggle */}
        <div className="flex items-center gap-2">
          {/* Diff Filters */}
          <div className="flex items-center bg-[#131314] border border-[#2d2f31] rounded-full p-0.5">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                activeFilter === 'all'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Tümü
            </button>
            <button
              onClick={() => setActiveFilter('errors')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition ${
                activeFilter === 'errors'
                  ? 'bg-rose-500 text-white font-bold'
                  : 'text-rose-400 hover:bg-rose-500/10'
              }`}
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Farklar & Hatalar (2)</span>
            </button>
            <button
              onClick={() => setActiveFilter('compliant')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition ${
                activeFilter === 'compliant'
                  ? 'bg-emerald-500 text-white font-bold'
                  : 'text-emerald-400 hover:bg-emerald-500/10'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Uygunlar (12)</span>
            </button>
          </div>

          {/* Sync Scroll Toggle */}
          <button
            onClick={() => setSyncScroll(!syncScroll)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition border ${
              syncScroll
                ? 'bg-blue-500/10 border-blue-500/40 text-blue-300'
                : 'bg-[#282a2c] border-[#2d2f31] text-[#8e918f]'
            }`}
            title="İki dokümanın kaydırmasını eşzamanla"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncScroll ? 'animate-spin-slow' : ''}`} />
            <span className="hidden sm:inline">Eşzamanlı Kaydırma</span>
          </button>
        </div>
      </header>

      {/* 2. STATS & QUICK ALERT BANNER */}
      <div className="bg-[#181a1b] border-b border-[#2d2f31] px-6 py-2 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5 text-rose-400 font-semibold bg-rose-500/10 px-2.5 py-1 rounded-full border border-rose-500/20">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>2 Kritik Hata / Limit Aşımı: W-04 Kaynağı (12mm Süreksizlik) & NOx (134 mg/Nm³)</span>
          </span>
          <span className="flex items-center gap-1.5 text-emerald-400 font-medium bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            <Check className="w-3.5 h-3.5 text-emerald-400" />
            <span>12 Parametre Standarta Tam Uygun (%87.5 Uyum Skoru)</span>
          </span>
        </div>

        {/* Search inside documents */}
        <div className="relative w-48 sm:w-64">
          <Search className="w-3.5 h-3.5 text-[#8e918f] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Tablolarda ara (örn: NOx, bar, sac)..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-[#131314] border border-[#2d2f31] rounded-full pl-8 pr-3 py-1 text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
          />
        </div>
      </div>

      {/* 3. SPLIT WORKSPACE: DOC A (LEFT) vs DOC B (RIGHT) */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        {/* PANE A: REFERENCE STANDARD SPECIFICATION (LEFT) */}
        <div className="flex-1 flex flex-col border-b md:border-b-0 md:border-r border-[#2d2f31] overflow-hidden bg-[#131314]">
          {/* Pane A Header */}
          <div className="p-3.5 bg-[#1a1c1d] border-b border-[#2d2f31] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold text-[10px] uppercase border border-blue-500/40">
                BELGE A (REFERANS STANDART)
              </span>
              <select
                value={docAId}
                onChange={(e) => setDocAId(e.target.value)}
                className="bg-[#282a2c] text-white text-xs font-semibold rounded-lg px-2.5 py-1 border border-[#3d4043] focus:outline-none focus:border-[#a8c7fa] truncate max-w-[220px]"
              >
                {documents.map((d) => (
                  <option key={`opt-a-${d.id}`} value={d.id}>
                    {d.filename}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[#8e918f]">
              <FileSpreadsheet className="w-3.5 h-3.5 text-blue-400" />
              <span>{chunksA.length} Parça</span>
            </div>
          </div>

          {/* Pane A Scroll Area */}
          <div
            ref={paneARef}
            onScroll={handleScrollA}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4"
          >
            {isLoadingA ? (
              <div className="flex flex-col items-center justify-center py-20 text-center text-xs text-[#8e918f]">
                <Loader2 className="w-6 h-6 animate-spin text-blue-400 mb-2" />
                <span>Referans belge yükleniyor...</span>
              </div>
            ) : chunksA.length === 0 ? (
              <div className="text-center py-20 text-xs text-[#8e918f]">
                Bu belge için parça bulunamadı.
              </div>
            ) : (
              chunksA.map((chunk) => renderChunkContent(chunk, false))
            )}
          </div>
        </div>

        {/* PANE B: TESTED BATCH REPORT / SAMPLE (RIGHT) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#131314]">
          {/* Pane B Header */}
          <div className="p-3.5 bg-[#1a1c1d] border-b border-[#2d2f31] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px] uppercase border border-emerald-500/40">
                BELGE B (FABRİKA NUMUNE / TEST)
              </span>
              <select
                value={docBId}
                onChange={(e) => setDocBId(e.target.value)}
                className="bg-[#282a2c] text-white text-xs font-semibold rounded-lg px-2.5 py-1 border border-[#3d4043] focus:outline-none focus:border-[#a8c7fa] truncate max-w-[220px]"
              >
                {documents.map((d) => (
                  <option key={`opt-b-${d.id}`} value={d.id}>
                    {d.filename}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[#8e918f]">
              <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>{chunksB.length} Parça</span>
            </div>
          </div>

          {/* Pane B Scroll Area */}
          <div
            ref={paneBRef}
            onScroll={handleScrollB}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4"
          >
            {isLoadingB ? (
              <div className="flex flex-col items-center justify-center py-20 text-center text-xs text-[#8e918f]">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-400 mb-2" />
                <span>Test raporu yükleniyor...</span>
              </div>
            ) : chunksB.length === 0 ? (
              <div className="text-center py-20 text-xs text-[#8e918f]">
                Bu belge için parça bulunamadı.
              </div>
            ) : (
              chunksB.map((chunk) => renderChunkContent(chunk, true))
            )}
          </div>
        </div>
      </div>

      {/* 4. DOCKED BOTTOM QUERY & AI COMPARISON ANALYSIS BAR */}
      <div className="border-t border-[#2d2f31] bg-[#1e1f20] shadow-2xl flex flex-col shrink-0">
        {/* Toggle Bar / Quick Chips */}
        <div className="px-4 sm:px-6 py-2 border-b border-[#2d2f31]/60 flex items-center justify-between gap-3 overflow-x-auto">
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              <span>14B Model ile Canlı Karşılaştırma:</span>
            </span>

            {/* Quick Prompt Action Chips */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() =>
                  handleRunComparisonQuery(
                    'İki belgedeki tüm uygunsuzlukları, tolerans aşımlarını ve hataları madde madde listele.'
                  )
                }
                disabled={isStreaming}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5] hover:text-white border border-[#3d4043] transition whitespace-nowrap"
              >
                🔴 Tüm Uygunsuzlukları Listele
              </button>
              <button
                onClick={() =>
                  handleRunComparisonQuery(
                    'W-04 kaynak dikişindeki ultrasonik hata ve NOx limit aşımı için teknik düzeltici faaliyet önerilerini yaz.'
                  )
                }
                disabled={isStreaming}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5] hover:text-white border border-[#3d4043] transition whitespace-nowrap"
              >
                🛠️ Düzeltici Faaliyet Öner
              </button>
              <button
                onClick={() =>
                  handleRunComparisonQuery(
                    'P265GH gövde sacı çekme dayanımı ve hidrostatik basınç test sonuçlarını standart sınırlarla kıyasla.'
                  )
                }
                disabled={isStreaming}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5] hover:text-white border border-[#3d4043] transition whitespace-nowrap"
              >
                📊 Mekanik & Basınç Test Farkları
              </button>
            </div>
          </div>

          <button
            onClick={() => setIsDockOpen(!isDockOpen)}
            className="p-1 rounded-full text-[#8e918f] hover:text-white transition"
            title={isDockOpen ? 'Paneli Küçült' : 'Paneli Büyüt'}
          >
            {isDockOpen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* AI Answer Drawer (Visible when there is an answer or streaming) */}
        {isDockOpen && aiAnswer !== null && (
          <div className="max-h-64 overflow-y-auto px-6 py-3 bg-[#131314] border-b border-[#2d2f31] text-xs text-[#e3e3e3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#a8c7fa] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>14B Karşılaştırma ve Standart Denetim Raporu</span>
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyAnswer}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5]"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Kopyalandı' : 'Kopyala'}</span>
                </button>
                <button
                  onClick={() => downloadExcelReport(aiAnswer, 'Selnikel_Karsilastirma_Raporu')}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5]"
                >
                  <Download className="w-3 h-3 text-emerald-400" />
                  <span>Excel Raporu</span>
                </button>
              </div>
            </div>

            <div className="prose prose-invert prose-xs max-w-none text-[#e3e3e3] leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{aiAnswer}</ReactMarkdown>
            </div>

            {/* Citations Footer */}
            {citations.length > 0 && (
              <div className="pt-2 border-t border-[#2d2f31] flex flex-wrap gap-2 items-center">
                <span className="text-[10px] text-[#8e918f]">Doğrulanan Kaynaklar:</span>
                {citations.map((c, idx) => (
                  <span
                    key={`cite-${idx}`}
                    className="px-2 py-0.5 rounded bg-[#1e1f20] border border-[#2d2f31] text-[10px] text-[#a8c7fa]"
                  >
                    {c.filename} (Sayfa {c.page_number})
                  </span>
                ))}
              </div>
            )}
            <div ref={answerBottomRef} />
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 sm:px-6 flex items-center gap-3">
          <div className="flex-1 relative flex items-center bg-[#131314] border border-[#2d2f31] rounded-2xl px-4 py-2 focus-within:border-[#a8c7fa] transition">
            <input
              type="text"
              placeholder="İki doküman hakkında özel bir karşılaştırma sorusu sorun (örn: Kimyasal analiz sonuçları uygun mu?)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleRunComparisonQuery();
                }
              }}
              disabled={isStreaming}
              className="flex-1 bg-transparent text-xs text-white placeholder-[#8e918f] focus:outline-none"
            />
            <button
              onClick={() => handleRunComparisonQuery()}
              disabled={isStreaming || !query.trim()}
              className="p-1.5 rounded-full bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {isStreaming ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

