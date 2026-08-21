'use client';

import React, { useState, useRef } from 'react';
import {
  X,
  UploadCloud,
  Globe,
  HardDrive,
  Clipboard,
  FileText,
  Search,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Plus,
  ExternalLink,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import {
  uploadDocument,
  searchWeb,
  ingestWebUrl,
  ingestRawText,
  WebSearchResultItem,
} from '@/lib/api';

interface NotebookLMAddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type SourceMode = 'upload' | 'search' | 'url' | 'text';

export default function NotebookLMAddSourceModal({
  isOpen,
  onClose,
  onSuccess,
}: NotebookLMAddSourceModalProps) {
  const [mode, setMode] = useState<SourceMode>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [department, setDepartment] = useState('engineering');
  const [documentType, setDocumentType] = useState('technical_specification');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Web Search State
  const [webQuery, setWebQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<WebSearchResultItem[]>([]);

  // Direct URL State
  const [inputUrl, setInputUrl] = useState('');
  const [customTitle, setCustomTitle] = useState('');

  // Pasted Text State
  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleUploadFile = async () => {
    if (!file) {
      setError('Lütfen bir dosya seçin veya sürükleyin.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      await uploadDocument(file, department, documentType, 'tr');
      showSuccessFeedback('Doküman başarıyla işlendi ve deftere eklendi!');
    } catch (err: any) {
      setError(err.message || 'Yükleme başarısız oldu.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSearchWeb = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!webQuery.trim()) return;

    setIsSearching(true);
    setError(null);
    setMode('search');

    try {
      const results = await searchWeb(webQuery, 6);
      setSearchResults(results);
      if (results.length === 0) {
        setError(`"${webQuery}" için internette sonuç bulunamadı.`);
      }
    } catch (err: any) {
      setError(err.message || 'Web araması sırasında hata oluştu.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleIngestUrl = async (targetUrl: string, title?: string) => {
    if (!targetUrl.trim()) {
      setError('Lütfen geçerli bir URL girin.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      await ingestWebUrl(targetUrl, department, title || customTitle || undefined);
      showSuccessFeedback('Web kaynağı başarıyla indirildi, ayrıştırıldı ve deftere eklendi!');
    } catch (err: any) {
      setError(err.message || 'Web URL aktarımı başarısız oldu.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleIngestText = async () => {
    if (!textContent.trim()) {
      setError('Lütfen metin içeriği girin.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      await ingestRawText(textTitle || 'Not Defteri Alıntısı', textContent, department);
      showSuccessFeedback('Kopyalanan metin başarıyla deftere eklendi!');
    } catch (err: any) {
      setError(err.message || 'Metin ekleme başarısız oldu.');
    } finally {
      setIsProcessing(false);
    }
  };

  const showSuccessFeedback = (msg: string) => {
    setSuccess(true);
    setSuccessMessage(msg);
    setTimeout(() => {
      setSuccess(false);
      setFile(null);
      setInputUrl('');
      setTextContent('');
      onSuccess();
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-[#1e1f20] border border-[#2d2f31] text-[#e3e3e3] rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden relative max-h-[90vh] flex flex-col">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition z-10"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6 sm:p-8 space-y-5 overflow-y-auto flex-1">
          {/* Header Title with Gradient */}
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Belgelerinizden & Web'den
            </h2>
            <div className="text-xl font-bold bg-gradient-to-r from-blue-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
              Notlarınıza Kaynak Ekleyin
            </div>
          </div>

          {/* Live Web Search Bar */}
          <form onSubmit={handleSearchWeb} className="relative">
            <div className="flex items-center gap-2 bg-[#131314] border border-[#2d2f31] rounded-2xl px-4 py-2.5 focus-within:border-[#a8c7fa] transition">
              <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#282a2c] text-xs font-medium text-[#a8c7fa]">
                <Globe className="w-3.5 h-3.5" />
                <span>Web Arama</span>
              </span>
              <input
                type="text"
                placeholder="Örn: TS EN 12953 kazan standardı, brülör emisyon limitleri..."
                value={webQuery}
                onChange={(e) => setWebQuery(e.target.value)}
                className="flex-1 bg-transparent text-xs text-[#e3e3e3] placeholder-[#8e918f] focus:outline-none ml-2"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="p-1.5 rounded-full hover:bg-[#282a2c] text-[#8e918f] hover:text-white transition"
              >
                {isSearching ? (
                  <Loader2 className="w-4 h-4 animate-spin text-[#a8c7fa]" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </button>
            </div>
          </form>

          {/* Mode Switcher Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-2xl text-xs font-medium transition ${
                mode === 'upload'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold shadow'
                  : 'bg-[#282a2c] hover:bg-[#333537] text-[#e3e3e3]'
              }`}
            >
              <UploadCloud className="w-4 h-4 text-blue-400" />
              <span>Dosya yükle</span>
            </button>

            <button
              type="button"
              onClick={() => setMode('url')}
              className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-2xl text-xs font-medium transition ${
                mode === 'url'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold shadow'
                  : 'bg-[#282a2c] hover:bg-[#333537] text-[#e3e3e3]'
              }`}
            >
              <Globe className="w-4 h-4 text-red-400" />
              <span>Web URL</span>
            </button>

            <button
              type="button"
              onClick={() => setMode('text')}
              className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-2xl text-xs font-medium transition ${
                mode === 'text'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold shadow'
                  : 'bg-[#282a2c] hover:bg-[#333537] text-[#e3e3e3]'
              }`}
            >
              <Clipboard className="w-4 h-4 text-emerald-400" />
              <span>Metin Yapıştır</span>
            </button>

            <button
              type="button"
              onClick={() => {
                if (searchResults.length > 0) setMode('search');
                else handleSearchWeb();
              }}
              className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-2xl text-xs font-medium transition ${
                mode === 'search'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold shadow'
                  : 'bg-[#282a2c] hover:bg-[#333537] text-[#e3e3e3]'
              }`}
            >
              <Sparkles className="w-4 h-4 text-yellow-400" />
              <span>Sonuçlar ({searchResults.length})</span>
            </button>
          </div>

          {/* Status Banners */}
          {error && (
            <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* MODE 1: FILE UPLOAD */}
          {mode === 'upload' && (
            <div className="space-y-4">
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="border border-dashed border-[#444746] rounded-3xl bg-[#131314] p-8 text-center cursor-pointer hover:border-[#a8c7fa] transition flex flex-col items-center justify-center min-h-[160px]"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.xlsx,.xls,.txt,.md"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {file ? (
                  <div className="flex items-center gap-3 text-left">
                    <FileText className="w-8 h-8 text-blue-400 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-white truncate max-w-xs">{file.name}</p>
                      <p className="text-xs text-[#8e918f]">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Yüklemeye Hazır
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    <UploadCloud className="w-8 h-8 text-[#8e918f] mx-auto mb-2" />
                    <p className="text-sm font-semibold text-white">
                      Dosyalarınızı buraya bırakın veya seçin
                    </p>
                    <p className="text-xs text-[#8e918f]">
                      PDF, Excel (.xlsx, .xls), Word (.docx), Markdown (.md), Metin (.txt)
                    </p>
                  </div>
                )}
              </div>

              {file && (
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleUploadFile}
                    disabled={isProcessing || success}
                    className="px-6 py-2.5 bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] font-bold text-xs rounded-full shadow transition flex items-center gap-2"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Ayrıştırılıyor & İndeksleniyor...</span>
                      </>
                    ) : (
                      <span>Kaynağı Deftere Ekle</span>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* MODE 2: DIRECT WEB URL INGEST */}
          {mode === 'url' && (
            <div className="space-y-4 bg-[#131314] p-5 rounded-3xl border border-[#2d2f31]">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-red-400" />
                  <span>Web Sayfası veya Makale URL Adresi:</span>
                </label>
                <input
                  type="url"
                  placeholder="https://example.com/teknik-sartname veya https://tr.wikipedia.org/..."
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[11px] text-[#8e918f]">
                  İsteğe Bağlı Başlık (Boş bırakılırsa sayfadan otomatik alınır):
                </label>
                <input
                  type="text"
                  placeholder="Örn: Kazan_Standardi_Web"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full px-4 py-2 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => handleIngestUrl(inputUrl)}
                  disabled={isProcessing || !inputUrl.trim() || success}
                  className="px-6 py-2.5 bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] font-bold text-xs rounded-full shadow transition flex items-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Web Sayfası Kazınıyor & Tablolar Çıkarılıyor...</span>
                    </>
                  ) : (
                    <>
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>URL'yi Deftere Kaynak Olarak Ekle</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* MODE 3: PASTED RAW TEXT INGEST */}
          {mode === 'text' && (
            <div className="space-y-4 bg-[#131314] p-5 rounded-3xl border border-[#2d2f31]">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Clipboard className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Not / Belge Başlığı:</span>
                </label>
                <input
                  type="text"
                  placeholder="Örn: Teknik Notlar ve Ölçüm Verileri"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  className="w-full px-4 py-2 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-white">
                  Kopyalanan Metin veya Tablo İçeriği:
                </label>
                <textarea
                  rows={5}
                  placeholder="Metni buraya yapıştırın..."
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  className="w-full p-4 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa] leading-relaxed"
                />
              </div>

              <div className="flex justify-end pt-1">
                <button
                  onClick={handleIngestText}
                  disabled={isProcessing || !textContent.trim() || success}
                  className="px-6 py-2.5 bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] font-bold text-xs rounded-full shadow transition flex items-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Kaydediliyor...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Metni Kaynak Olarak Ekle</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* MODE 4: LIVE WEB SEARCH RESULTS LIST */}
          {mode === 'search' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-1">
                <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-blue-400" />
                  <span>İnternet Arama Sonuçları ({searchResults.length})</span>
                </span>
                <span className="text-[11px] text-[#8e918f]">
                  Tek tıkla defterinize ekleyin
                </span>
              </div>

              {searchResults.length === 0 ? (
                <div className="text-center py-10 text-xs text-[#8e918f] bg-[#131314] rounded-2xl border border-[#2d2f31]">
                  Arama yapmak için yukarıdaki arama kutusuna bir teknik terim veya standart yazıp Enter'a basın.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1">
                  {searchResults.map((item, idx) => (
                    <div
                      key={`search-res-${idx}`}
                      className="p-3.5 rounded-2xl bg-[#131314] border border-[#282a2c] hover:border-[#a8c7fa]/50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="overflow-hidden flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <a
                            href={item.href}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs font-bold text-[#a8c7fa] hover:underline truncate flex items-center gap-1"
                          >
                            <span>{item.title}</span>
                            <ExternalLink className="w-3 h-3 shrink-0 text-[#8e918f]" />
                          </a>
                        </div>
                        <p className="text-[11px] text-[#8e918f] line-clamp-2 leading-relaxed">
                          {item.body}
                        </p>
                      </div>

                      <button
                        onClick={() => handleIngestUrl(item.href, item.title)}
                        disabled={isProcessing}
                        className="px-3.5 py-1.5 rounded-full bg-[#282a2c] hover:bg-[#a8c7fa] hover:text-[#041e49] text-xs font-medium text-white transition flex items-center gap-1.5 shrink-0 self-start sm:self-center"
                        title="Bu web sayfasını deftere kaynak olarak aktar"
                      >
                        {isProcessing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Plus className="w-3.5 h-3.5" />
                        )}
                        <span>Deftere Ekle</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

