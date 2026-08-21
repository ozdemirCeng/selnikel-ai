'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
  FileText,
  Search,
  Plus,
  ChevronDown,
  Globe,
  Sparkles,
  ArrowRight,
  Send,
  MoreVertical,
  SlidersHorizontal,
  FolderOpen,
  Eye,
  PanelLeftClose,
  PanelRightClose,
  Download,
  Copy,
  Check,
  Loader2,
  Mic,
  Presentation,
  Video,
  Network,
  FileSpreadsheet,
  FileCheck,
  CreditCard,
  PieChart,
  Edit3,
  X,
  Zap,
  BookOpen,
  Save,
  CheckCircle2,
  Table,
  Heading,
  Bold,
  ArrowLeft,
  ChevronRight,
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
  streamRAGQuery,
} from '@/lib/api';
import NotebookLMAddSourceModal from './NotebookLMAddSourceModal';
import NotebookLMSourceReader from './NotebookLMSourceReader';
import ChunkInspectorModal from './ChunkInspectorModal';
import VisualDocumentEditor from './VisualDocumentEditor';

interface WorkspaceMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[];
}

interface NotebookLMWorkspaceProps {
  notebookTitle?: string;
  onBackToDashboard?: () => void;
}

export default function NotebookLMWorkspace({
  notebookTitle = 'Adsız not defteri',
  onBackToDashboard,
}: NotebookLMWorkspaceProps) {
  // Sources
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<Record<string, boolean>>({});
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isAddSourceOpen, setIsAddSourceOpen] = useState(false);

  // Active Source Reader State
  const [activeReaderDoc, setActiveReaderDoc] = useState<{
    id: string;
    filename: string;
    department?: string;
    totalPages?: number;
    highlightSnippet?: string;
  } | null>(null);

  // Inspector Modal
  const [inspectDocId, setInspectDocId] = useState<string | null>(null);
  const [inspectDocName, setInspectDocName] = useState('');

  // Conversation
  const [messages, setMessages] = useState<WorkspaceMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSmartBanner, setShowSmartBanner] = useState(true);

  // Studio View State: 'cards' (Production Tools) vs 'artifact' (Document Editor)
  const [studioView, setStudioView] = useState<'cards' | 'artifact'>('cards');
  const [studioArtifact, setStudioArtifact] = useState<string>(
    `# Selnikel Teknik Mühendislik Raporu\n\n## 1. Yönetici Özeti\nBu çalışma kılavuzu ve teknik şartname çıktısı, seçili kaynaklardan otomatik derlenmiştir. Dilerseniz yukarıdaki **"Görsel Sayfa"** sekmesine geçerek doğrudan Word gibi yazıya tıklayıp değiştirebilir veya **"Düzenle"** sekmesinden değerleri doğrudan güncelleyebilirsiniz.\n\n## 2. Teknik Parametreler & Hesaplama Tablosu\n| Parametre Adı | Nominal Değer | Birim | Durum |\n|---|---|---|---|\n| Buhar Üretim Debisi | 1000 | kg/h | Nominal |\n| İşletme Basıncı | 16 | bar | Güvenli |\n| Termal Verim (ASME) | 91.5 | % | Yüksek |\n| Doğal Gaz Tüketimi | 75.4 | Nm3/h | Optimum |\n\n## 3. Mühendislik Notları & Tavsiyeler\n- Emniyet ventili yıllık periyodik bakım kontrolü yapılmalıdır.\n- Brülör hava/yakıt oranı O2 trim sistemiyle izlenmelidir.`
  );
  const [studioMode, setStudioMode] = useState<'preview' | 'visual' | 'edit'>('visual');
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const editorTextareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadSources();
    // Load persisted studio content if available
    const saved = localStorage.getItem(`selnikel_studio_${notebookTitle}`);
    if (saved) {
      setStudioArtifact(saved);
    }
  }, [notebookTitle]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSources = async () => {
    setIsLoadingDocs(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      const initialMap: Record<string, boolean> = {};
      docs.forEach((d) => {
        initialMap[d.id] = true;
      });
      setSelectedDocIds(initialMap);
    } catch (e) {
      console.error('Failed to load sources', e);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const selectedCount = Object.values(selectedDocIds).filter(Boolean).length;

  const handleOpenSource = (doc: DocumentItem, highlight?: string) => {
    setActiveReaderDoc({
      id: doc.id,
      filename: doc.filename,
      department: doc.department,
      totalPages: doc.total_pages || 1,
      highlightSnippet: highlight,
    });
  };

  const handleCitationClick = (citation: CitationItem) => {
    const matchedDoc = documents.find((d) => d.id === citation.document_id || d.filename === citation.filename);
    if (matchedDoc) {
      handleOpenSource(matchedDoc, citation.snippet);
    } else {
      setActiveReaderDoc({
        id: citation.document_id,
        filename: citation.filename,
        highlightSnippet: citation.snippet,
      });
    }
  };

  const handleSaveArtifact = () => {
    localStorage.setItem(`selnikel_studio_${notebookTitle}`, studioArtifact);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const insertTemplate = (templateText: string) => {
    setStudioArtifact((prev) => `${prev}\n\n${templateText}`);
    setStudioMode('edit');
    setTimeout(() => {
      if (editorTextareaRef.current) {
        editorTextareaRef.current.scrollTop = editorTextareaRef.current.scrollHeight;
      }
    }, 100);
  };

  const handleSend = async (queryText?: string) => {
    const query = (queryText || inputQuery).trim();
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
      let accumulated = '';
      let streamCitations: CitationItem[] = [];

      await streamRAGQuery(
        { query: query, top_k: 5 },
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

      if (accumulated) {
        setStudioArtifact(accumulated);
        localStorage.setItem(`selnikel_studio_${notebookTitle}`, accumulated);
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

  const handleExport = async (format: 'pdf' | 'excel' | 'word' | 'pptx') => {
    setIsExporting(format);
    try {
      const content = studioArtifact || '# Selnikel Mühendislik Çıktısı';
      if (format === 'excel') {
        await downloadExcelReport(content, `${notebookTitle} Tablosu`);
      } else if (format === 'word') {
        await downloadWordReport(content, `${notebookTitle} Raporu`);
      } else if (format === 'pptx') {
        await downloadPowerPointReport(content, `${notebookTitle} Sunumu`);
      } else if (format === 'pdf') {
        await downloadPdfReport(content, `${notebookTitle} Raporu`);
      }
    } catch (e: any) {
      alert(`Dışa aktarma hatası: ${e.message}`);
    } finally {
      setIsExporting(null);
    }
  };

  const handleStudioCardClick = async (cardType: string) => {
    setStudioView('artifact');
    if (cardType === 'slide') {
      handleExport('pptx');
    } else if (cardType === 'table') {
      handleExport('excel');
    } else if (cardType === 'report') {
      handleExport('word');
    } else if (cardType === 'audio') {
      handleSend('Bu not defterindeki kaynakların kapsamlı bir sesli brifing / özet metnini oluştur.');
    } else if (cardType === 'flashcard') {
      handleSend('Bu dokümanlardan mühendisler için 5 adet soru-cevap bilgi kartı (flashcard) oluştur.');
    } else if (cardType === 'test') {
      handleSend('Dokümanlardaki şartnamelere göre 5 soruluk teknik uygunluk test ve doğrulama maddeleri hazırla.');
    } else if (cardType === 'mindmap') {
      handleSend('Bu konunun hiyerarşik zihin haritasını (mindmap) markdown liste formatında çıkar.');
    } else if (cardType === 'infographic') {
      handleSend('Bu sistemin çalışma prensiplerini ve sayısal verilerini infografik metin şeması olarak hazırla.');
    }
  };

  return (
    <div className="h-[calc(100vh-5.5rem)] grid grid-cols-1 lg:grid-cols-12 gap-3 pb-3">
      {/* 1. LEFT COLUMN: Kaynaklar OR Kaynak Okuyucu */}
      <div className="lg:col-span-4 xl:col-span-3 h-full overflow-hidden">
        {activeReaderDoc ? (
          <NotebookLMSourceReader
            documentId={activeReaderDoc.id}
            filename={activeReaderDoc.filename}
            department={activeReaderDoc.department}
            totalPages={activeReaderDoc.totalPages}
            highlightSnippet={activeReaderDoc.highlightSnippet}
            onClose={() => setActiveReaderDoc(null)}
            onAskAboutDoc={(query) => handleSend(query)}
          />
        ) : (
          <div className="h-full bg-[#1e1f20] rounded-2xl flex flex-col overflow-hidden border border-[#2d2f31]">
            {/* Header */}
            <div className="p-4 flex items-center justify-between border-b border-[#282a2c]">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[#e3e3e3]">Kaynaklar</span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[#282a2c] text-[#a8c7fa] border border-[#37393b]">
                  {selectedCount}/{documents.length}
                </span>
              </div>
              <button className="text-[#8e918f] hover:text-white transition">
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Add Source Button */}
            <div className="p-4 space-y-3">
              <button
                onClick={() => setIsAddSourceOpen(true)}
                className="w-full py-2.5 px-4 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-white flex items-center justify-center gap-1.5 transition border border-[#37393b]"
              >
                <Plus className="w-4 h-4" />
                <span>Kaynak ekle</span>
              </button>

              {/* Web Search Box */}
              <div className="bg-[#131314] rounded-2xl p-2.5 border border-[#282a2c] space-y-2">
                <span className="text-[11px] text-[#8e918f] block px-1">
                  Web&apos;de yeni kaynaklar arayın
                </span>
                <div className="flex items-center gap-1.5">
                  <button className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#282a2c] text-[10px] font-medium text-[#e3e3e3]">
                    <Globe className="w-3 h-3 text-blue-400" />
                    <span>Web</span>
                    <ChevronDown className="w-2.5 h-2.5 text-[#8e918f]" />
                  </button>
                  <button className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#282a2c] text-[10px] font-medium text-[#e3e3e3]">
                    <span>Hızlı Araştırma</span>
                    <ChevronDown className="w-2.5 h-2.5 text-[#8e918f]" />
                  </button>
                  <button
                    onClick={() => alert('Web araştırması yapılıyor...')}
                    className="ml-auto p-1.5 rounded-full hover:bg-[#282a2c] text-[#8e918f] hover:text-white transition"
                  >
                    <Search className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Source Items List */}
            <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
              {isLoadingDocs ? (
                <div className="h-40 flex items-center justify-center gap-2 text-xs text-[#8e918f]">
                  <Loader2 className="w-4 h-4 animate-spin text-[#a8c7fa]" />
                  <span>Yükleniyor...</span>
                </div>
              ) : documents.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#8e918f] space-y-3">
                  <FileText className="w-8 h-8 text-[#8e918f]/50" />
                  <p className="text-xs leading-relaxed text-[#c4c7c5]">
                    Kayıtlı kaynaklar burada gösterilir
                  </p>
                  <p className="text-[11px] text-[#8e918f] max-w-[200px]">
                    Dosya, web sitesi veya başka kaynaklar ekleyin. Ardından bu kaynaklara dayalı olarak soru sorun veya içerik oluşturun.
                  </p>
                  <button
                    onClick={() => setIsAddSourceOpen(true)}
                    className="text-xs text-[#a8c7fa] hover:underline font-medium"
                  >
                    Dosyaları buraya bırakın veya kaynak ekleyin
                  </button>
                </div>
              ) : (
                documents.map((doc) => {
                  const isChecked = !!selectedDocIds[doc.id];
                  return (
                    <div
                      key={doc.id}
                      className={`p-3 rounded-2xl border transition flex items-start gap-2.5 cursor-pointer group ${
                        isChecked
                          ? 'bg-[#282a2c] border-[#37393b]'
                          : 'bg-transparent border-[#282a2c]/50 opacity-60 hover:opacity-100'
                      }`}
                      onClick={() => handleOpenSource(doc)}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleDocSelection(doc.id);
                        }}
                        className="mt-1 rounded border-[#444746] text-[#a8c7fa] focus:ring-0 bg-[#131314]"
                      />
                      <div className="flex-1 overflow-hidden">
                        <div className="text-xs font-medium text-white truncate group-hover:text-[#a8c7fa] transition">
                          {doc.filename}
                        </div>
                        <div className="text-[10px] text-[#8e918f] mt-0.5 flex items-center gap-1.5">
                          <span>{doc.department}</span>
                          <span>&bull;</span>
                          <span>{doc.total_pages || 1} sayfa</span>
                          <span>&bull;</span>
                          <span className="text-[#a8c7fa] underline opacity-0 group-hover:opacity-100 transition">
                            İçeriği Aç &gt;
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2. CENTER COLUMN: Sohbet */}
      <div className="lg:col-span-4 xl:col-span-4 h-full bg-[#1e1f20] rounded-2xl flex flex-col overflow-hidden border border-[#2d2f31]">
        {/* Header */}
        <div className="p-4 flex items-center justify-between border-b border-[#282a2c]">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[#e3e3e3]">Sohbet</span>
            {activeReaderDoc && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#282a2c] text-[#c4c7c5] truncate max-w-[180px]">
                📖 {activeReaderDoc.filename}
              </span>
            )}
          </div>
          <button className="text-[#8e918f] hover:text-white transition">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>

        {/* Conversation Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col justify-center space-y-6 max-w-md mx-auto">
              <div className="text-3xl">👋</div>
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold text-white tracking-tight">
                  Not defterinizi başlatalım...
                </h2>
                <p className="text-xs text-[#8e918f] leading-relaxed">
                  Bu boş tuvali kullanarak yeni bir şey öğrenebilir, oluşturabilir veya yeni bir konuda ilerleme kaydedebilirsiniz. Sol panelden dokümanları açabilir, sağ panelde ise **raporları canlı düzenleyip anında Excel/Word/PPTX/PDF çıktısı** alabilirsiniz.
                </p>
              </div>

              <div className="space-y-2.5 pt-2">
                <span className="text-xs font-medium text-[#c4c7c5] block">
                  Bu not defterinin size hangi konuda yardımcı olmasını istersiniz?
                </span>

                <div className="space-y-2">
                  <button
                    onClick={() => handleSend('Selnikel endüstriyel kazanları ve kapasiteleri hakkında genel bilgi ver.')}
                    className="w-full text-left py-2.5 px-4 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs text-[#e3e3e3] transition border border-transparent hover:border-[#37393b]"
                  >
                    Yeni bir konu hakkında bilgi edinin
                  </button>

                  <button
                    onClick={() => handleSend('SB-100 kazanı ve monoblok brülörler için teknik şartname ve özet içerik oluştur.')}
                    className="w-full text-left py-2.5 px-4 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs text-[#e3e3e3] transition border border-transparent hover:border-[#37393b]"
                  >
                    Yeni içerikler oluşturun
                  </button>

                  <button
                    onClick={() => handleSend('Radyal fan debi ve basınç düşüm hesaplamalarını projelendir.')}
                    className="w-full text-left py-2.5 px-4 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs text-[#e3e3e3] transition border border-transparent hover:border-[#37393b]"
                  >
                    Bir projede ilerleme kaydedin
                  </button>
                </div>
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className="space-y-2">
                <div className="text-[11px] font-medium text-[#8e918f]">
                  {m.role === 'user' ? 'Siz' : 'Selnikel AI'}
                </div>
                <div
                  className={`p-4 rounded-2xl text-xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-[#282a2c] text-white'
                      : 'bg-[#131314] text-[#e3e3e3] border border-[#282a2c]'
                  }`}
                >
                  <div className="prose prose-invert prose-xs max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content}
                    </ReactMarkdown>
                  </div>

                  {/* Inline Grounded Citations */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-[#282a2c] flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] text-[#8e918f] font-medium">Doğrulanan Kaynaklar:</span>
                      {m.citations.map((cite, cIdx) => (
                        <button
                          key={cIdx}
                          onClick={() => handleCitationClick(cite)}
                          className="px-2.5 py-0.5 rounded-full bg-[#282a2c] hover:bg-[#37393b] text-[#a8c7fa] hover:text-white text-[10px] font-medium transition border border-[#37393b] flex items-center gap-1"
                          title="Dokümanı ve Parçayı Aç"
                        >
                          <BookOpen className="w-3 h-3" />
                          <span>{cite.filename}</span>
                          {cite.page_number && <span>(S.{cite.page_number})</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Bottom Omnibar */}
        <div className="p-4 border-t border-[#282a2c] bg-[#1e1f20] space-y-2">
          {showSmartBanner && (
            <div className="flex items-center justify-between py-1.5 px-3 rounded-xl bg-[#282a2c]/60 text-[11px] text-[#c4c7c5]">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>Selnikel Notebook artık daha akıllı. Web&apos;de yeni kaynaklar bulmasını isteyin.</span>
              </span>
              <button
                onClick={() => setShowSmartBanner(false)}
                className="text-[#8e918f] hover:text-white p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center bg-[#131314] border border-[#2d2f31] rounded-full px-4 py-2.5 focus-within:border-[#a8c7fa] transition"
          >
            <input
              type="text"
              placeholder="Soru sorun veya içerik oluşturun"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isStreaming}
              className="flex-1 bg-transparent text-xs text-white placeholder-[#8e918f] focus:outline-none"
            />

            <div className="flex items-center gap-3 ml-2">
              <span className="text-[11px] text-[#8e918f]">
                {selectedCount} kaynak
              </span>

              <button
                type="submit"
                disabled={!inputQuery.trim() || isStreaming}
                className="w-7 h-7 rounded-full bg-[#282a2c] hover:bg-[#333537] disabled:opacity-40 text-white flex items-center justify-center transition shrink-0"
              >
                {isStreaming ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#a8c7fa]" />
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* 3. RIGHT COLUMN: Studio Hub (8 Production Cards OR Active Document Editor) */}
      <div className="lg:col-span-4 xl:col-span-5 h-full bg-[#1e1f20] rounded-2xl flex flex-col overflow-hidden border border-[#2d2f31]">
        {studioView === 'cards' ? (
          /* ─── A. STUDIO PRODUCTION TOOLS GRID (8 CARDS) ─── */
          <div className="h-full flex flex-col">
            {/* Header */}
            <div className="p-4 flex items-center justify-between border-b border-[#282a2c]">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[#e3e3e3]">Studio</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#282a2c] text-[#a8c7fa] border border-[#37393b]">
                  8 Üretim Aracı
                </span>
              </div>

              <div className="flex items-center gap-2">
                {studioArtifact && (
                  <button
                    onClick={() => setStudioView('artifact')}
                    className="px-3 py-1 bg-[#282a2c] hover:bg-[#333537] text-xs text-[#a8c7fa] font-medium rounded-full flex items-center gap-1.5 transition border border-[#37393b]"
                  >
                    <span>Açık Raporu Gör</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* 8 Authentic NotebookLM Cards Grid */}
            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              <div>
                <span className="text-xs font-semibold text-[#c4c7c5] block mb-2 px-1">
                  Yeni Çıktı Üretin
                </span>
                <div className="grid grid-cols-2 gap-2.5">
                  {/* Card 1: Sesli Özet */}
                  <button
                    onClick={() => handleStudioCardClick('audio')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                        <Mic className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Sesli Özet</span>
                        <span className="text-[10px] text-[#8e918f]">Sesli brifing metni</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 2: Slayt Sunusu */}
                  <button
                    onClick={() => handleStudioCardClick('slide')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
                        <Presentation className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Slayt Sunusu</span>
                        <span className="text-[10px] text-amber-400/80 font-mono">.PPTX İndir</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 3: Videolu Özet */}
                  <button
                    onClick={() => handleStudioCardClick('audio')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                        <Video className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Videolu Özet</span>
                        <span className="text-[10px] text-[#8e918f]">Video sunum planı</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 4: Zihin Haritası */}
                  <button
                    onClick={() => handleStudioCardClick('mindmap')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-pink-500/10 text-pink-400 flex items-center justify-center">
                        <Network className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Zihin Haritası</span>
                        <span className="text-[10px] text-[#8e918f]">Kavramsal şema</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 5: Raporlar */}
                  <button
                    onClick={() => handleStudioCardClick('report')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Raporlar</span>
                        <span className="text-[10px] text-blue-400/80 font-mono">.DOCX İndir</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 6: Bilgi Kartları */}
                  <button
                    onClick={() => handleStudioCardClick('flashcard')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                        <CreditCard className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Bilgi kartları</span>
                        <span className="text-[10px] text-[#8e918f]">5 Adet Soru-Cevap</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 7: Test */}
                  <button
                    onClick={() => handleStudioCardClick('test')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center">
                        <FileCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Test</span>
                        <span className="text-[10px] text-[#8e918f]">Doğrulama maddeleri</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>

                  {/* Card 8: Veri Tablosu */}
                  <button
                    onClick={() => handleStudioCardClick('table')}
                    className="p-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-left transition flex items-center justify-between group border border-[#37393b]/40 hover:border-[#a8c7fa]/30"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                        <FileSpreadsheet className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-[#e3e3e3] block">Veri Tablosu</span>
                        <span className="text-[10px] text-emerald-400/80 font-mono">.XLSX İndir</span>
                      </div>
                    </div>
                    <span className="text-[#8e918f] group-hover:text-white text-xs">&gt;</span>
                  </button>
                </div>
              </div>

              {/* Saved Notes & Artifacts Section */}
              {studioArtifact && (
                <div className="pt-2">
                  <span className="text-xs font-semibold text-[#c4c7c5] block mb-2 px-1">
                    Kayıtlı Raporlar & Notlar
                  </span>
                  <div
                    onClick={() => setStudioView('artifact')}
                    className="p-3.5 rounded-2xl bg-[#282a2c] hover:bg-[#333537] border border-[#37393b] cursor-pointer group transition flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="overflow-hidden">
                        <span className="text-xs font-semibold text-white block truncate group-hover:text-[#a8c7fa] transition">
                          Selnikel Teknik Mühendislik Raporu
                        </span>
                        <span className="text-[10px] text-[#8e918f] block truncate mt-0.5">
                          Tıklayarak Görsel Sayfa Düzenleyicide açın ve düzenleyin
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[#8e918f] group-hover:text-white shrink-0 ml-2" />
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Bar: Not Ekle */}
            <div className="p-4 border-t border-[#282a2c] flex justify-end">
              <button
                onClick={() => {
                  const note = prompt('Yeni not başlığı veya içerik girin:');
                  if (note) {
                    insertTemplate(`### Not: ${note}`);
                    setStudioView('artifact');
                  }
                }}
                className="px-4 py-2 bg-white text-black font-semibold text-xs rounded-full hover:bg-slate-200 transition flex items-center gap-1.5 shadow-md"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Not ekle</span>
              </button>
            </div>
          </div>
        ) : (
          /* ─── B. ACTIVE DOCUMENT & VISUAL WYSIWYG EDITOR ─── */
          <div className="h-full flex flex-col overflow-hidden">
            {/* Header with Back Button + Mode Switcher + Exporters */}
            <div className="p-3 border-b border-[#282a2c] bg-[#1e1f20] flex items-center justify-between gap-2 overflow-x-auto select-none">
              <div className="flex items-center gap-2">
                {/* Back to 8 Production Tools Button */}
                <button
                  onClick={() => setStudioView('cards')}
                  className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs font-semibold text-[#c4c7c5] hover:text-white flex items-center gap-1 transition border border-[#37393b]"
                  title="Üretim Araçlarına Dön"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Üretim</span>
                </button>

                {/* Mode Switcher */}
                <div className="flex items-center bg-[#131314] border border-[#282a2c] rounded-full p-0.5 text-xs">
                  <button
                    onClick={() => setStudioMode('visual')}
                    className={`px-2.5 py-1 rounded-full font-medium transition ${
                      studioMode === 'visual'
                        ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                        : 'text-[#8e918f] hover:text-white'
                    }`}
                    title="Görsel Word / A4 Sayfa Düzenleyici"
                  >
                    Görsel Sayfa
                  </button>
                  <button
                    onClick={() => setStudioMode('preview')}
                    className={`px-2.5 py-1 rounded-full font-medium transition ${
                      studioMode === 'preview'
                        ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                        : 'text-[#8e918f] hover:text-white'
                    }`}
                    title="Önizleme Modu"
                  >
                    Önizleme
                  </button>
                  <button
                    onClick={() => setStudioMode('edit')}
                    className={`px-2.5 py-1 rounded-full font-medium transition ${
                      studioMode === 'edit'
                        ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                        : 'text-[#8e918f] hover:text-white'
                    }`}
                    title="Markdown Kod Modu"
                  >
                    Kod
                  </button>
                </div>
              </div>

              {/* Exporters & Actions */}
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => handleExport('excel')}
                  disabled={!!isExporting}
                  className="px-2 py-0.5 rounded-full bg-[#282a2c] hover:bg-emerald-600/20 text-emerald-400 text-[11px] font-semibold flex items-center gap-1 transition border border-[#37393b]"
                  title="Excel (.xlsx) İndir"
                >
                  {isExporting === 'excel' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileSpreadsheet className="w-3 h-3" />}
                  <span>.XLSX</span>
                </button>

                <button
                  onClick={() => handleExport('word')}
                  disabled={!!isExporting}
                  className="px-2 py-0.5 rounded-full bg-[#282a2c] hover:bg-blue-600/20 text-blue-400 text-[11px] font-semibold flex items-center gap-1 transition border border-[#37393b]"
                  title="Word (.docx) İndir"
                >
                  {isExporting === 'word' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                  <span>.DOCX</span>
                </button>

                <button
                  onClick={() => handleExport('pptx')}
                  disabled={!!isExporting}
                  className="px-2 py-0.5 rounded-full bg-[#282a2c] hover:bg-amber-600/20 text-amber-400 text-[11px] font-semibold flex items-center gap-1 transition border border-[#37393b]"
                  title="Sunum (.pptx) İndir"
                >
                  {isExporting === 'pptx' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Presentation className="w-3 h-3" />}
                  <span>.PPTX</span>
                </button>

                <button
                  onClick={() => handleExport('pdf')}
                  disabled={!!isExporting}
                  className="px-2 py-0.5 rounded-full bg-[#282a2c] hover:bg-rose-600/20 text-rose-400 text-[11px] font-semibold flex items-center gap-1 transition border border-[#37393b]"
                  title="PDF (.pdf) İndir"
                >
                  {isExporting === 'pdf' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileCheck className="w-3 h-3" />}
                  <span>.PDF</span>
                </button>

                <span className="w-px h-4 bg-[#37393b] mx-0.5" />

                <button
                  onClick={handleSaveArtifact}
                  className="px-2.5 py-1 rounded-full bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[11px] text-[#041e49] font-bold flex items-center gap-1 transition shadow"
                  title="Kaydet"
                >
                  {isSaved ? <CheckCircle2 className="w-3 h-3" /> : <Save className="w-3 h-3" />}
                  <span>{isSaved ? 'Kayıt' : 'Kaydet'}</span>
                </button>

                <button
                  onClick={() => {
                    navigator.clipboard.writeText(studioArtifact);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="p-1 rounded-lg text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
                  title="Metni Kopyala"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-hidden relative bg-[#131314]">
              {studioMode === 'visual' ? (
                <VisualDocumentEditor
                  initialMarkdown={studioArtifact}
                  notebookTitle={notebookTitle}
                  onSave={(updated) => {
                    setStudioArtifact(updated);
                    localStorage.setItem(`selnikel_studio_${notebookTitle}`, updated);
                  }}
                />
              ) : studioMode === 'edit' ? (
                <div className="h-full flex flex-col p-4 space-y-3">
                  <div className="flex items-center gap-1.5 pb-2 border-b border-[#282a2c] overflow-x-auto">
                    <button
                      onClick={() => insertTemplate('| Parametre | Değer | Birim |\n|---|---|---|\n| Kapasite | 1500 | kg/h |')}
                      className="px-2.5 py-1 rounded-lg bg-[#1e1f20] hover:bg-[#282a2c] text-[10px] font-mono text-emerald-400 transition flex items-center gap-1 border border-[#282a2c]"
                    >
                      <Table className="w-3 h-3" />
                      <span>+ Tablo Şablonu</span>
                    </button>

                    <button
                      onClick={() => insertTemplate('### Yeni Teknik Bölüm\n- Açıklama ve hesap detayları buraya girilir.')}
                      className="px-2.5 py-1 rounded-lg bg-[#1e1f20] hover:bg-[#282a2c] text-[10px] font-mono text-[#a8c7fa] transition flex items-center gap-1 border border-[#282a2c]"
                    >
                      <Heading className="w-3 h-3" />
                      <span>+ Başlık Ekle</span>
                    </button>

                    <button
                      onClick={() => insertTemplate('> [!IMPORTANT]\n> Emniyet ventili kontrolü zorunludur.')}
                      className="px-2.5 py-1 rounded-lg bg-[#1e1f20] hover:bg-[#282a2c] text-[10px] font-mono text-amber-400 transition flex items-center gap-1 border border-[#282a2c]"
                    >
                      <span>+ Uyarı Bloğu</span>
                    </button>
                  </div>

                  <textarea
                    ref={editorTextareaRef}
                    value={studioArtifact}
                    onChange={(e) => setStudioArtifact(e.target.value)}
                    placeholder="Rapor veya mühendislik metnini doğrudan düzenleyin..."
                    className="w-full flex-1 p-3 bg-[#1e1f20] border border-[#282a2c] rounded-2xl font-mono text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa] resize-none leading-relaxed"
                  />
                </div>
              ) : (
                <div className="p-5 overflow-y-auto h-full prose prose-invert prose-xs max-w-none text-xs leading-relaxed text-[#e3e3e3]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {studioArtifact}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Add Source Modal */}
      <NotebookLMAddSourceModal
        isOpen={isAddSourceOpen}
        onClose={() => setIsAddSourceOpen(false)}
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
