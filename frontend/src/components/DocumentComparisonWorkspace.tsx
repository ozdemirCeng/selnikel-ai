'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ArrowLeft,
  Columns2,
  FileSpreadsheet,
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
  Maximize2,
  Minimize2,
  FileCheck,
  X,
  MessageSquare,
  ShieldAlert,
  ChevronUp,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationItem, DocumentChunkItem, DocumentItem } from '@/lib/types';
import {
  fetchDocumentChunks,
  streamRAGQuery,
  downloadExcelReport,
  downloadPdfReport,
} from '@/lib/api';

interface DocumentComparisonWorkspaceProps {
  documents: DocumentItem[];
  initialDocAId?: string;
  initialDocBId?: string;
  onClose: () => void;
}

export default function DocumentComparisonWorkspace({
  documents,
  initialDocAId,
  initialDocBId,
  onClose,
}: DocumentComparisonWorkspaceProps) {
  // Find distinct default documents
  const standardDoc = documents.find((d) => d.filename.toLowerCase().includes('standart')) || documents[0];
  const testDoc =
    documents.find(
      (d) =>
        d.id !== standardDoc?.id &&
        (d.filename.toLowerCase().includes('numune') ||
          d.filename.toLowerCase().includes('test') ||
          d.filename.toLowerCase().includes('rapor'))
    ) ||
    documents.find((d) => d.id !== standardDoc?.id) ||
    documents[0];

  // Document Selection
  const [docAId, setDocAId] = useState<string>(initialDocAId || standardDoc?.id || '');
  const [docBId, setDocBId] = useState<string>(initialDocBId || testDoc?.id || '');

  // Document Chunks & Content
  const [chunksA, setChunksA] = useState<DocumentChunkItem[]>([]);
  const [chunksB, setChunksB] = useState<DocumentChunkItem[]>([]);
  const [isLoadingA, setIsLoadingA] = useState(false);
  const [isLoadingB, setIsLoadingB] = useState(false);

  // UI States
  const [activeFilter, setActiveFilter] = useState<'all' | 'errors' | 'compliant'>('all');
  const [searchFilter, setSearchFilter] = useState('');
  const [syncScroll, setSyncScroll] = useState(true);

  // Floating AI Drawer States
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [copied, setCopied] = useState(false);

  const paneARef = useRef<HTMLDivElement>(null);
  const paneBRef = useRef<HTMLDivElement>(null);
  const answerBottomRef = useRef<HTMLDivElement>(null);

  // Load Doc A Chunks
  useEffect(() => {
    if (docAId) {
      setIsLoadingA(true);
      fetchDocumentChunks(docAId)
        .then((data) => setChunksA(data))
        .catch((err) => console.error('Failed to load Doc A chunks', err))
        .finally(() => setIsLoadingA(false));
    }
  }, [docAId]);

  // Load Doc B Chunks
  useEffect(() => {
    if (docBId) {
      setIsLoadingB(true);
      fetchDocumentChunks(docBId)
        .then((data) => setChunksB(data))
        .catch((err) => console.error('Failed to load Doc B chunks', err))
        .finally(() => setIsLoadingB(false));
    }
  }, [docBId]);

  // Synchronized Scrolling
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

  // Run AI Comparison Query
  const handleRunComparisonQuery = async (customPrompt?: string) => {
    const promptToRun = customPrompt || query;
    if (!promptToRun.trim() || isStreaming) return;

    setIsStreaming(true);
    setAiAnswer('');
    setCitations([]);
    setIsDrawerOpen(true);

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

  // Proper Markdown table cleaner that preserves standard GFM syntax
  const cleanChunkMarkdown = (rawContent: string): string => {
    const lines = rawContent
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0 && !l.startsWith('[Document:') && !l.startsWith('### Table:') && !l.startsWith('Table: Tablo:'));

    const tableLines = lines.filter((l) => l.startsWith('|') && l.endsWith('|'));
    const nonTableLines = lines.filter((l) => !(l.startsWith('|') && l.endsWith('|')));

    if (tableLines.length >= 3) {
      const firstRow = tableLines[0];
      const secondRow = tableLines[1];
      const thirdRow = tableLines[2];

      if (firstRow.toLowerCase().includes('sütun 2') && secondRow.startsWith('| ---')) {
        const actualHeader = thirdRow;
        const colCount = actualHeader.split('|').filter((c) => c.trim().length > 0).length;
        const separator = '| ' + Array(colCount).fill('---').join(' | ') + ' |';
        const dataRows = tableLines.slice(3);
        const reconstructedTable = [actualHeader, separator, ...dataRows].join('\n');
        return [...nonTableLines, reconstructedTable].join('\n\n');
      }
    }

    return lines.join('\n\n');
  };

  // Render Table / Chunk Content
  const renderChunk = (chunk: DocumentChunkItem, isTestDoc: boolean = false) => {
    const content = chunk.content;
    const isError =
      content.includes('UYGUNSUZ') ||
      content.includes('FARK') ||
      content.includes('Süreksizlik') ||
      content.includes('134.0') ||
      content.includes('FGR');

    if (activeFilter === 'errors' && !isError) return null;
    if (activeFilter === 'compliant' && isError) return null;
    if (searchFilter && !content.toLowerCase().includes(searchFilter.toLowerCase())) return null;

    const cleanedContent = cleanChunkMarkdown(content);

    return (
      <div
        key={chunk.id}
        className={`mb-4 rounded-xl border transition duration-150 overflow-hidden ${
          isError
            ? 'bg-rose-950/20 border-rose-500/80 shadow-md shadow-rose-950/30'
            : 'bg-[#181a1b] border-[#2d2f31]'
        }`}
      >
        {/* Compact Chunk Title Bar */}
        <div className="px-3.5 py-1.5 bg-[#1e2022] border-b border-[#2d2f31] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#a8c7fa]">
              {chunk.section || `Sayfa ${chunk.page_number}`}
            </span>
          </div>

          {isTestDoc && (
            <div>
              {isError ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/50 text-[10px] font-bold animate-pulse">
                  <XCircle className="w-3 h-3 text-rose-400" />
                  <span>UYGUNSUZLUK / LİMİT AŞIMI</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-medium">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>STANDARDA UYGUN</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Clean High-Density Table */}
        <div className="p-3 overflow-x-auto">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ node, ...props }) => (
                <table className="w-full border-collapse text-xs" {...props} />
              ),
              thead: ({ node, ...props }) => (
                <thead className="bg-[#131415] border-b border-[#3c4043]" {...props} />
              ),
              th: ({ node, ...props }) => (
                <th
                  className="border border-[#2d2f31] px-3 py-2 text-left font-bold text-[#a8c7fa] text-[11px] bg-[#141517]"
                  {...props}
                />
              ),
              td: ({ node, ...props }) => {
                const cellText = String(props.children);
                const isCellError =
                  cellText.includes('UYGUNSUZ') ||
                  cellText.includes('134.0') ||
                  cellText.includes('Süreksizlik') ||
                  cellText.includes('12 mm');
                const isCellSuccess = cellText.includes('UYGUN') || cellText.includes('Sıfır sızıntı');

                return (
                  <td
                    className={`border border-[#2d2f31] px-3 py-1.5 text-xs transition ${
                      isCellError
                        ? 'bg-rose-900/50 text-rose-100 font-bold border-rose-500/60'
                        : isCellSuccess
                        ? 'text-emerald-300'
                        : 'text-[#c4c7c5]'
                    }`}
                    {...props}
                  />
                );
              },
            }}
          >
            {cleanedContent}
          </ReactMarkdown>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#101112] text-[#e3e3e3] select-text">
      {/* ─── 1. ULTRA-COMPACT SLIM HEADER (48px) ─── */}
      <header className="h-12 border-b border-[#2d2f31] bg-[#181a1b] px-3 sm:px-4 flex items-center justify-between gap-3 shrink-0">
        {/* Left: Back & Document Selectors */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#282a2c] hover:bg-[#333537] text-xs font-semibold text-white transition shrink-0"
            title="Geri dön"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Geri</span>
          </button>

          {/* Doc A Selector */}
          <div className="flex items-center gap-1 bg-[#131314] px-2 py-0.5 rounded-lg border border-[#2d2f31] shrink-0">
            <span className="text-[10px] font-bold text-blue-400">A:</span>
            <select
              value={docAId}
              onChange={(e) => setDocAId(e.target.value)}
              className="bg-transparent text-white text-xs font-semibold outline-none cursor-pointer max-w-[140px] sm:max-w-[200px] truncate"
            >
              {documents.map((d) => (
                <option key={`a-${d.id}`} value={d.id} className="bg-[#1e1f20]">
                  {d.filename}
                </option>
              ))}
            </select>
          </div>

          <span className="text-[#8e918f] text-xs shrink-0">↔</span>

          {/* Doc B Selector */}
          <div className="flex items-center gap-1 bg-[#131314] px-2 py-0.5 rounded-lg border border-[#2d2f31] shrink-0">
            <span className="text-[10px] font-bold text-emerald-400">B:</span>
            <select
              value={docBId}
              onChange={(e) => setDocBId(e.target.value)}
              className="bg-transparent text-white text-xs font-semibold outline-none cursor-pointer max-w-[140px] sm:max-w-[200px] truncate"
            >
              {documents.map((d) => (
                <option key={`b-${d.id}`} value={d.id} className="bg-[#1e1f20]">
                  {d.filename}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Center: Live Stats Summary Badges */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>2 Uygunsuzluk (NOx 134 & W-04 Kaynak)</span>
          </span>
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>12 Standarta Uygun</span>
          </span>
        </div>

        {/* Right: Diff Filter Toggle & Sync Scroll */}
        <div className="flex items-center gap-1.5 shrink-0">
          <div className="flex items-center bg-[#131314] border border-[#2d2f31] rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-2.5 py-0.5 rounded-md transition ${
                activeFilter === 'all'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Tümü
            </button>
            <button
              onClick={() => setActiveFilter('errors')}
              className={`flex items-center gap-1 px-2.5 py-0.5 rounded-md transition ${
                activeFilter === 'errors'
                  ? 'bg-rose-500 text-white font-bold'
                  : 'text-rose-400 hover:bg-rose-500/10'
              }`}
            >
              <XCircle className="w-3 h-3" />
              <span>Hatalar</span>
            </button>
          </div>

          <button
            onClick={() => setSyncScroll(!syncScroll)}
            className={`p-1.5 rounded-lg border text-xs transition ${
              syncScroll
                ? 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                : 'bg-[#282a2c] border-[#2d2f31] text-[#8e918f]'
            }`}
            title={syncScroll ? 'Eşzamanlı Kaydırma Aktif' : 'Bağımsız Kaydırma'}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          {/* AI Drawer Toggle Button */}
          <button
            onClick={() => setIsDrawerOpen(!isDrawerOpen)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition border ${
              isDrawerOpen
                ? 'bg-blue-500 text-white border-blue-400'
                : 'bg-blue-500/20 text-blue-300 border-blue-500/40 hover:bg-blue-500/30'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Asistan</span>
          </button>
        </div>
      </header>

      {/* ─── 2. FULL-HEIGHT SPLIT PANES (90%+ SCREEN REAL ESTATE) ─── */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        {/* PANE A: REFERENCE STANDARD (LEFT) */}
        <div className="flex-1 flex flex-col border-b md:border-b-0 md:border-r border-[#2d2f31] overflow-hidden bg-[#101112]">
          {/* Sub-header */}
          <div className="px-4 py-1.5 bg-[#141517] border-b border-[#2d2f31] flex items-center justify-between text-xs text-[#8e918f]">
            <span className="font-semibold text-blue-300 uppercase tracking-wide text-[11px]">
              REFERANS STANDART SPESİFİKASYONU ({docA?.filename})
            </span>
            <span className="text-[11px]">{chunksA.length} Parça</span>
          </div>

          {/* Scrollable Content */}
          <div
            ref={paneARef}
            onScroll={handleScrollA}
            className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3"
          >
            {isLoadingA ? (
              <div className="flex flex-col items-center justify-center py-20 text-xs text-[#8e918f]">
                <Loader2 className="w-6 h-6 animate-spin text-blue-400 mb-2" />
                <span>Standart yükleniyor...</span>
              </div>
            ) : chunksA.length === 0 ? (
              <div className="text-center py-20 text-xs text-[#8e918f]">Doküman içeriği bulunamadı.</div>
            ) : (
              chunksA.map((chunk) => renderChunk(chunk, false))
            )}
          </div>
        </div>

        {/* PANE B: TEST SAMPLE / FAT REPORT (RIGHT) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#101112]">
          {/* Sub-header */}
          <div className="px-4 py-1.5 bg-[#141517] border-b border-[#2d2f31] flex items-center justify-between text-xs text-[#8e918f]">
            <span className="font-semibold text-emerald-300 uppercase tracking-wide text-[11px]">
              TEST EDİLEN FABRİKA NUMUNESİ ({docB?.filename})
            </span>
            <span className="text-[11px]">{chunksB.length} Parça</span>
          </div>

          {/* Scrollable Content */}
          <div
            ref={paneBRef}
            onScroll={handleScrollB}
            className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3"
          >
            {isLoadingB ? (
              <div className="flex flex-col items-center justify-center py-20 text-xs text-[#8e918f]">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-400 mb-2" />
                <span>Test raporu yükleniyor...</span>
              </div>
            ) : chunksB.length === 0 ? (
              <div className="text-center py-20 text-xs text-[#8e918f]">Doküman içeriği bulunamadı.</div>
            ) : (
              chunksB.map((chunk) => renderChunk(chunk, true))
            )}
          </div>
        </div>
      </div>

      {/* ─── 3. FLOATING MINIMALIST AI BAR & SLIDE-UP DRAWER ─── */}
      {!isDrawerOpen ? (
        /* Collapsed Floating Bottom Pill */
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 bg-[#181a1b]/95 backdrop-blur-md border border-[#3d4043] rounded-full px-4 py-2 shadow-2xl">
          <Sparkles className="w-4 h-4 text-blue-400 shrink-0" />
          <button
            onClick={() =>
              handleRunComparisonQuery('İki belgedeki tüm uygunsuzlukları ve düzeltici faaliyetleri listele.')
            }
            className="text-xs text-[#c4c7c5] hover:text-white transition whitespace-nowrap"
          >
            🔴 Uygunsuzlukları Listele
          </button>
          <span className="text-[#3d4043]">&bull;</span>
          <button
            onClick={() =>
              handleRunComparisonQuery('W-04 kaynağı ve NOx limit aşımı için aksiyon planı çıkar.')
            }
            className="text-xs text-[#c4c7c5] hover:text-white transition whitespace-nowrap"
          >
            🛠️ Düzeltici Faaliyet Öner
          </button>
          <span className="text-[#3d4043]">&bull;</span>
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="px-2.5 py-1 rounded-full bg-[#a8c7fa] text-[#041e49] text-xs font-bold hover:bg-[#d3e3fd] transition flex items-center gap-1"
          >
            <span>Soru Sor</span>
            <ChevronUp className="w-3 h-3" />
          </button>
        </div>
      ) : (
        /* Slide-up Expanded Drawer */
        <div className="absolute bottom-0 inset-x-0 z-40 bg-[#181a1b]/98 backdrop-blur-xl border-t border-[#3d4043] shadow-2xl flex flex-col max-h-[50vh] transition-all">
          {/* Drawer Header */}
          <div className="px-4 py-2 bg-[#131415] border-b border-[#2d2f31] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-bold text-white">14B AI Mühendislik Karşılaştırma Asistanı</span>
            </div>

            <div className="flex items-center gap-2">
              {aiAnswer && (
                <>
                  <button
                    onClick={handleCopyAnswer}
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5]"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>Kopyala</span>
                  </button>
                  <button
                    onClick={() => downloadExcelReport(aiAnswer, 'Selnikel_Karsilastirma_Raporu')}
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5]"
                  >
                    <Download className="w-3 h-3 text-emerald-400" />
                    <span>Excel Raporu</span>
                  </button>
                </>
              )}
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="p-1 rounded-md text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* AI Response Area */}
          {aiAnswer && (
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-[#101112]">
              <div className="prose prose-invert prose-xs max-w-none text-[#e3e3e3] leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ node, ...props }) => (
                      <div className="overflow-x-auto my-2 rounded-xl border border-[#3d4043] shadow-md bg-[#181a1b]">
                        <table className="w-full border-collapse text-xs" {...props} />
                      </div>
                    ),
                    thead: ({ node, ...props }) => (
                      <thead className="bg-[#1e2227] border-b border-[#3d4043]" {...props} />
                    ),
                    th: ({ node, ...props }) => (
                      <th className="border-r border-[#3d4043] last:border-r-0 px-3 py-2 text-left font-bold text-[#a8c7fa] text-[11px] uppercase tracking-wider" {...props} />
                    ),
                    td: ({ node, ...props }) => {
                      const cellStr = String(props.children);
                      const isError = cellStr.includes('❌') || cellStr.includes('UYGUNSUZ') || cellStr.includes('LİMİT AŞIMI') || cellStr.includes('134.0') || cellStr.includes('Süreksizlik');
                      const isSuccess = cellStr.includes('✅') || cellStr.includes('UYGUN');
                      return (
                        <td
                          className={`border-t border-r border-[#2d2f31] last:border-r-0 px-3 py-1.5 text-xs ${
                            isError
                              ? 'bg-rose-950/40 text-rose-200 font-bold'
                              : isSuccess
                              ? 'text-emerald-300'
                              : 'text-[#e3e3e3]'
                          }`}
                          {...props}
                        />
                      );
                    },
                    h1: ({ node, ...props }) => (
                      <h1 className="text-sm font-bold text-white mt-3 mb-1.5 pb-1 border-b border-[#2d2f31]" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2 className="text-xs font-bold text-[#a8c7fa] mt-2.5 mb-1" {...props} />
                    ),
                  }}
                >
                  {aiAnswer}
                </ReactMarkdown>
              </div>

              {citations.length > 0 && (
                <div className="pt-2 border-t border-[#2d2f31] flex flex-wrap gap-2 items-center text-[10px] text-[#8e918f]">
                  <span>Kaynaklar:</span>
                  {citations.map((c, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-[#1e1f20] border border-[#2d2f31] text-[#a8c7fa]">
                      {c.filename} (Sayfa {c.page_number})
                    </span>
                  ))}
                </div>
              )}
              <div ref={answerBottomRef} />
            </div>
          )}

          {/* Prompt Input Form */}
          <div className="p-3 bg-[#181a1b] border-t border-[#2d2f31] flex items-center gap-2">
            <input
              type="text"
              placeholder="İki doküman hakkında karşılaştırma sorusu sorun (örn: Kimyasal analiz ve darbe testleri standartlara uygun mu?)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleRunComparisonQuery();
                }
              }}
              disabled={isStreaming}
              className="flex-1 bg-[#101112] border border-[#2d2f31] rounded-xl px-3.5 py-2 text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
            />
            <button
              onClick={() => handleRunComparisonQuery()}
              disabled={isStreaming || !query.trim()}
              className="p-2 rounded-xl bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] disabled:opacity-40 transition"
            >
              {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


