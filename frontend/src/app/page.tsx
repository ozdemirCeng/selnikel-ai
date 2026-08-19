'use client';

import React, { useState } from 'react';
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

  const handleOpenNotebook = (id: string) => {
    setActiveNotebookTitle(
      id === 'nb-1'
        ? 'Selnikel SB-100 Endüstriyel Buhar Kazanı'
        : id === 'nb-2'
        ? 'Brülör Bakım & Ayar Talimatları'
        : 'Endüstriyel Fan Basınç Eğrileri'
    );
    setCurrentView('workspace');
  };

  const handleCreateNotebook = () => {
    setActiveNotebookTitle('Yeni Not Defteri');
    setCurrentView('workspace');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#131314] text-[#e3e3e3]">
      {/* 1. EXACT GOOGLE NOTEBOOKLM TOP APP BAR */}
      <header className="h-14 border-b border-[#282a2c] px-4 flex items-center justify-between bg-[#131314] shrink-0">
        {/* Left: Gemini Icon + Title */}
        <div className="flex items-center gap-3">
          {/* Gemini Colored Curved Icon */}
          <div
            onClick={() => setCurrentView('dashboard')}
            className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 via-indigo-400 to-teal-300 flex items-center justify-center text-[#041e49] font-black text-sm shadow-md cursor-pointer hover:opacity-90 transition"
          >
            ✦
          </div>

          <div className="flex items-center gap-2">
            {currentView !== 'dashboard' ? (
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
            ) : (
              <span className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                Gemini Notebook
                <span className="text-[11px] font-normal text-[#8e918f]">Selnikel Enerji</span>
              </span>
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
            onClick={() => alert('Grounded RAG Doğruluk Skoru: %100')}
            className="p-2 rounded-full text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Analiz"
          >
            <LineChart className="w-4 h-4" />
          </button>

          <button
            onClick={() => alert('Paylaşım bağlantısı panoya kopyalandı.')}
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

          <span className="hidden sm:inline px-2 py-0.5 rounded-md bg-[#282a2c] text-[10px] font-semibold text-[#a8c7fa] border border-[#37393b]">
            PRO
          </span>

          {/* User Avatar */}
          <div
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
            className="w-8 h-8 rounded-full p-0.5 bg-gradient-to-tr from-amber-400 via-rose-400 to-teal-400 flex items-center justify-center cursor-pointer ml-1"
          >
            <div className="w-full h-full rounded-full bg-[#282a2c] text-white flex items-center justify-center font-bold text-xs">
              Ö
            </div>
          </div>

          {/* EXACT SETTINGS DROPDOWN (From Screenshot 1) */}
          {isSettingsOpen && (
            <div className="absolute top-12 right-0 z-50 w-64 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl shadow-2xl p-2 text-xs text-[#e3e3e3] animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-2 font-semibold text-white border-b border-[#282a2c] flex items-center justify-between">
                <span>Ayarlar</span>
                <span className="text-[10px] font-mono text-cyan-400">Selnikel V1</span>
              </div>

              <div className="py-1 space-y-0.5">
                <button
                  onClick={() => {
                    alert('Selnikel AI yardım kılavuzu.');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <HelpCircle className="w-4 h-4 text-[#8e918f]" />
                  <span>Gemini Notebook yardımı</span>
                </button>

                <button
                  onClick={() => {
                    alert('Geri bildirim modülü açıldı.');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <MessageSquarePlus className="w-4 h-4 text-[#8e918f]" />
                  <span>Geri bildirim gönder</span>
                </button>

                <button
                  onClick={() => {
                    window.open('https://discord.com', '_blank');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <Globe className="w-4 h-4 text-[#8e918f]" />
                  <span>Discord</span>
                </button>

                <button
                  onClick={() => {
                    alert('Hedef dil: Türkçe (TR)');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <Globe className="w-4 h-4 text-[#8e918f]" />
                  <span>Hedef dil</span>
                </button>

                <button
                  onClick={() => {
                    alert('Filigranlar kaldırıldı.');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <Award className="w-4 h-4 text-[#8e918f]" />
                  <span>Filigranları kaldır</span>
                </button>

                <button
                  onClick={() => {
                    alert('Lisans: Selnikel Enerji Enterprise');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 transition"
                >
                  <Award className="w-4 h-4 text-[#8e918f]" />
                  <span>Lisanslar</span>
                </button>

                <button
                  onClick={() => {
                    alert('Cihaz: Windows Workstation (Local Central Server)');
                    setIsSettingsOpen(false);
                  }}
                  className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center justify-between transition"
                >
                  <div className="flex items-center gap-2.5">
                    <Monitor className="w-4 h-4 text-[#8e918f]" />
                    <span>Cihaz</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-[#8e918f]" />
                </button>

                <div className="pt-1 border-t border-[#282a2c]">
                  <button
                    onClick={() => {
                      alert('Kurumsal Abonelik: Aktif');
                      setIsSettingsOpen(false);
                    }}
                    className="w-full px-3 py-2 rounded-xl text-left hover:bg-[#282a2c] flex items-center gap-2.5 text-amber-300 transition"
                  >
                    <CreditCard className="w-4 h-4 text-amber-400" />
                    <span>Aboneliği yönetin</span>
                  </button>
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
