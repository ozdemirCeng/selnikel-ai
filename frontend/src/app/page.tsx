'use client';

import React, { useState, useEffect } from 'react';
import {
  Settings,
  Share2,
  LineChart,
  Plus,
  ArrowLeft,
  Sparkles,
  Bot,
  FolderOpen,
  Activity,
  HelpCircle,
  MessageSquarePlus,
  Globe,
  Award,
  Monitor,
  CreditCard,
  X,
  ChevronRight,
  ShieldCheck,
  Sun,
  Moon,
} from 'lucide-react';
import NotebookLMWorkspace from '@/components/NotebookLMWorkspace';
import NotebookLMDashboard from '@/components/NotebookLMDashboard';
import AgentStudio from '@/components/AgentStudio';
import DocumentCatalog from '@/components/DocumentCatalog';
import SystemStatus from '@/components/SystemStatus';

export default function HomePage() {
  // Navigation: 'workspace' | 'dashboard' | 'agent' | 'catalog' | 'status'
  const [currentView, setCurrentView] = useState<'workspace' | 'dashboard' | 'agent' | 'catalog' | 'status'>('workspace');
  const [activeNotebookTitle, setActiveNotebookTitle] = useState('Adsız not defteri');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Theme state: 'dark' | 'light'
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    const savedTheme = (localStorage.getItem('selnikel_theme') as 'dark' | 'light') || 'dark';
    setTheme(savedTheme);
    if (savedTheme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('selnikel_theme', nextTheme);
    if (nextTheme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
  };

  // Modals & Notifications
  const [activeModal, setActiveModal] = useState<'analytics' | 'share' | 'help' | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleOpenNotebook = (titleOrId: string) => {
    // If passed a full title, use it; otherwise fallback to clean default
    setActiveNotebookTitle(titleOrId);
    setCurrentView('workspace');
  };

  const handleCreateNotebook = () => {
    const newTitle = `Yeni Teknik İnceleme ${new Date().toLocaleDateString('tr-TR')}`;
    setActiveNotebookTitle(newTitle);
    setCurrentView('workspace');
    showToast('Yeni not defteri oluşturuldu.');
  };

  const handleShareWorkspace = () => {
    if (typeof window !== 'undefined') {
      navigator.clipboard.writeText(window.location.href);
      showToast('Sohbet & Not Defteri bağlantısı panoya kopyalandı.');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#131314] text-[#e3e3e3]">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-[#1e1f20] border border-blue-500/40 text-white text-xs font-semibold shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Analytics Modal */}
      {activeModal === 'analytics' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[#282a2c] pb-3">
              <div className="flex items-center gap-2">
                <LineChart className="w-5 h-5 text-[#a8c7fa]" />
                <h3 className="font-semibold text-white text-sm">Sistem & RAG Analitikleri</h3>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#8e918f] hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between p-2.5 rounded-xl bg-[#131314]">
                <span className="text-[#8e918f]">Aktif LLM Sağlayıcı:</span>
                <span className="font-mono text-emerald-400 font-semibold">Google Gemini 3.5 Flash</span>
              </div>
              <div className="flex justify-between p-2.5 rounded-xl bg-[#131314]">
                <span className="text-[#8e918f]">Vektör & Hibrit Arama:</span>
                <span className="font-mono text-blue-400 font-semibold">Qdrant + SQLite BGE-M3</span>
              </div>
              <div className="flex justify-between p-2.5 rounded-xl bg-[#131314]">
                <span className="text-[#8e918f]">Kaynak Doğrulama Filtresi:</span>
                <span className="text-white font-medium">Aktif Seçili Dokümanlar</span>
              </div>
              <div className="flex justify-between p-2.5 rounded-xl bg-[#131314]">
                <span className="text-[#8e918f]">Güvenlik & Departman İzni:</span>
                <span className="text-emerald-400 font-semibold">Kurumsal ACL (Yönetici)</span>
              </div>
            </div>
            <button
              onClick={() => setActiveModal(null)}
              className="w-full py-2 rounded-xl bg-[#282a2c] hover:bg-[#333537] text-white text-xs font-semibold transition"
            >
              Kapat
            </button>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {activeModal === 'help' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[#282a2c] pb-3">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-[#a8c7fa]" />
                <h3 className="font-semibold text-white text-sm">Selnikel AI Kullanım Rehberi</h3>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#8e918f] hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs text-[#c4c7c5] leading-relaxed">
              <p>• <strong>Kaynak Seçimi:</strong> Sol paneldeki dokümanların yanındaki kutucukları işaretleyerek veya kaldırarak sorularınızın sadece seçtiğiniz dokümanlar taranarak yanıtlanmasını sağlayabilirsiniz.</p>
              <p>• <strong>Studio Araçları:</strong> Sağdaki 8 araç ile seçili dokümanlardan otomatik Sesli Brifing, Slayt Sunusu, Veri Tablosu veya Teknik Rapor üretebilir ve Word/Excel/PPTX formatında indirebilirsiniz.</p>
              <p>• <strong>Yan Yana Karşılaştırma:</strong> "Yan Yana Karşılaştır" düğmesi ile referans standart ve fabrika test raporunu aynı ekranda açıp tolerans aşımlarını denetleyebilirsiniz.</p>
            </div>
            <button
              onClick={() => setActiveModal(null)}
              className="w-full py-2 rounded-xl bg-[#282a2c] hover:bg-[#333537] text-white text-xs font-semibold transition"
            >
              Anladım
            </button>
          </div>
        </div>
      )}

      {/* 1. TOP APP BAR */}
      <header className="h-14 border-b border-[#282a2c] px-4 flex items-center justify-between bg-[#131314] shrink-0">
        {/* Left: Brand Icon + Title */}
        <div className="flex items-center gap-3">
          <div
            onClick={() => setCurrentView('dashboard')}
            className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-black text-sm shadow-md cursor-pointer hover:opacity-90 transition"
          >
            S
          </div>

          <div className="flex items-center gap-2">
            {currentView !== 'workspace' ? (
              <span className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                Selnikel AI Not Defteri
                <span className="text-[11px] font-normal text-[#8e918f]">Mühendislik İstasyonu</span>
              </span>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className="p-1 rounded-full text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
                  title="Not defterlerine dön"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <input
                  type="text"
                  value={activeNotebookTitle}
                  onChange={(e) => setActiveNotebookTitle(e.target.value)}
                  className="bg-transparent text-sm font-medium text-white hover:bg-[#282a2c] px-2 py-1 rounded-lg focus:outline-none focus:bg-[#282a2c] transition max-w-sm truncate"
                />
              </div>
            )}
          </div>
        </div>

        {/* Center: Workstation Modes Switcher */}
        <div className="hidden md:flex items-center bg-[#1e1f20] border border-[#2d2f31] rounded-full p-1 text-xs">
          <button
            onClick={() => setCurrentView('workspace')}
            className={`px-3.5 py-1 rounded-full font-medium transition ${
              currentView === 'workspace'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'text-[#c4c7c5] hover:text-white'
            }`}
          >
            Not Defteri
          </button>
          <button
            onClick={() => setCurrentView('dashboard')}
            className={`px-3.5 py-1 rounded-full font-medium transition ${
              currentView === 'dashboard'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'text-[#c4c7c5] hover:text-white'
            }`}
          >
            Tüm Not Defterleri
          </button>
          <button
            onClick={() => setCurrentView('agent')}
            className={`px-3.5 py-1 rounded-full font-medium transition flex items-center gap-1.5 ${
              currentView === 'agent'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'text-[#c4c7c5] hover:text-white'
            }`}
          >
            <Sparkles className="w-3 h-3 text-cyan-400" />
            <span>Otonom Ajan</span>
          </button>
          <button
            onClick={() => setCurrentView('catalog')}
            className={`px-3.5 py-1 rounded-full font-medium transition ${
              currentView === 'catalog'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'text-[#c4c7c5] hover:text-white'
            }`}
          >
            Katalog
          </button>
          <button
            onClick={() => setCurrentView('status')}
            className={`px-3.5 py-1 rounded-full font-medium transition ${
              currentView === 'status'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'text-[#c4c7c5] hover:text-white'
            }`}
          >
            Sağlık
          </button>
        </div>

        {/* Right: Actions + Settings + PRO + Avatar */}
        <div className="flex items-center gap-2 relative">
          <button
            onClick={handleCreateNotebook}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-white transition border border-[#37393b]"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Not defteri oluştur</span>
          </button>

          <button
            onClick={() => setActiveModal('analytics')}
            className="p-2 rounded-full text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Sistem Analitikleri"
          >
            <LineChart className="w-4 h-4" />
          </button>

          <button
            onClick={handleShareWorkspace}
            className="p-2 rounded-full text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Paylaş"
          >
            <Share2 className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
            className="p-2 rounded-full text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Ayarlar"
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* Theme Switcher Button */}
          <button
            onClick={toggleTheme}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#282a2c] hover:bg-[#333537] text-xs font-semibold transition border border-[#37393b]"
            title={theme === 'dark' ? 'Beyaz Temaya Geç' : 'Koyu Temaya Geç'}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-white hidden sm:inline">Beyaz Tema</span>
              </>
            ) : (
              <>
                <Moon className="w-3.5 h-3.5 text-indigo-600" />
                <span className="text-slate-800 hidden sm:inline">Koyu Tema</span>
              </>
            )}
          </button>

          <span className="hidden sm:inline px-2 py-0.5 rounded-md bg-[#282a2c] text-[10px] font-semibold text-[#a8c7fa] border border-[#37393b]">
            PRO
          </span>

          {/* User Avatar */}
          <div
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
            className="w-8 h-8 rounded-full p-0.5 bg-gradient-to-tr from-amber-400 via-rose-400 to-teal-400 flex items-center justify-center cursor-pointer ml-1"
          >
            <div className="w-full h-full rounded-full bg-[#282a2c] text-white flex items-center justify-center font-bold text-xs">
              S
            </div>
          </div>

          {/* SETTINGS DROPDOWN */}
          {isSettingsOpen && (
            <div className="absolute top-12 right-0 z-50 w-64 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl shadow-2xl p-2 text-xs text-[#e3e3e3] animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-2 font-semibold text-white border-b border-[#282a2c] flex items-center justify-between">
                <span>Ayarlar</span>
                <span className="text-[10px] font-mono text-cyan-400">Selnikel V1</span>
              </div>

              <div className="py-1 space-y-0.5">
                <button
                  onClick={() => {
                    toggleTheme();
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center justify-between transition"
                >
                  <div className="flex items-center gap-2.5">
                    {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
                    <span>Görünüm Teması</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#131314] text-[#a8c7fa] border border-[#37393b]">
                    {theme === 'dark' ? 'Koyu Tema' : 'Beyaz Tema'}
                  </span>
                </button>

                <button
                  onClick={() => {
                    setActiveModal('help');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <HelpCircle className="w-4 h-4 text-[#8e918f]" />
                  <span>Kullanım Rehberi & Yardım</span>
                </button>

                <button
                  onClick={() => {
                    setActiveModal('analytics');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <Activity className="w-4 h-4 text-[#8e918f]" />
                  <span>Sistem Sağlığı & RAG Durumu</span>
                </button>

                <div className="pt-1 border-t border-[#282a2c]">
                  <div className="px-3 py-1.5 text-[11px] text-[#8e918f] flex items-center justify-between">
                    <span>Lisans:</span>
                    <span className="text-emerald-400 font-semibold">Selnikel Enterprise</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* 2. MAIN VIEWPORT */}
      <main className="flex-1 p-3 overflow-hidden">
        {currentView === 'workspace' && (
          <NotebookLMWorkspace
            notebookTitle={activeNotebookTitle}
            onBackToDashboard={() => setCurrentView('dashboard')}
          />
        )}

        {currentView === 'dashboard' && (
          <NotebookLMDashboard
            onOpenNotebook={handleOpenNotebook}
            onCreateNotebook={handleCreateNotebook}
          />
        )}

        {currentView === 'agent' && (
          <div className="max-w-6xl mx-auto py-4 animate-in fade-in duration-200">
            <AgentStudio />
          </div>
        )}

        {currentView === 'catalog' && (
          <div className="max-w-6xl mx-auto py-4 animate-in fade-in duration-200">
            <DocumentCatalog />
          </div>
        )}

        {currentView === 'status' && (
          <div className="max-w-6xl mx-auto py-4 animate-in fade-in duration-200">
            <SystemStatus />
          </div>
        )}
      </main>
    </div>
  );
}
