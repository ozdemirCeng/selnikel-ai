'use client';

import React, { useState } from 'react';
import {
  Search,
  LayoutGrid,
  List,
  Plus,
  MoreVertical,
  Settings,
  HelpCircle,
  MessageSquarePlus,
  Globe,
  Award,
  Monitor,
  CreditCard,
  ChevronDown,
  Sparkles,
  Layers,
  FolderPlus,
  Check,
} from 'lucide-react';

interface NotebookItem {
  id: string;
  title: string;
  icon: string;
  sourceCount: number;
  createdAt: string;
  role: string;
}

const SAMPLE_NOTEBOOKS: NotebookItem[] = [
  {
    id: 'nb-1',
    title: 'Selnikel SB-100 Endüstriyel Buhar Kazanı Teknik İnceleme',
    icon: '⚡',
    sourceCount: 12,
    createdAt: '19 Ağu 2026',
    role: 'Owner',
  },
  {
    id: 'nb-2',
    title: 'Monoblok ve Dual-Blok Brülör Bakım & Ayar Talimatları',
    icon: '🔥',
    sourceCount: 8,
    createdAt: '18 Ağu 2026',
    role: 'Owner',
  },
  {
    id: 'nb-3',
    title: 'Endüstriyel Santrifüj & Radyal Fan Basınç Düşüm Eğrileri',
    icon: '🌪️',
    sourceCount: 5,
    createdAt: '16 Ağu 2026',
    role: 'Owner',
  },
  {
    id: 'nb-4',
    title: 'Kazan Emniyet Ventili & Basınçlı Kap Standartları (ASME PTC 4.1)',
    icon: '⚖️',
    sourceCount: 14,
    createdAt: '15 Ağu 2026',
    role: 'Owner',
  },
  {
    id: 'nb-5',
    title: 'Selnikel Isı ve Enerji Ar-Ge Şartname Kataloğu 2026',
    icon: '📘',
    sourceCount: 22,
    createdAt: '10 Ağu 2026',
    role: 'Owner',
  },
];

interface NotebookLMDashboardProps {
  onOpenNotebook: (notebookId: string) => void;
  onCreateNotebook: () => void;
}

export default function NotebookLMDashboard({
  onOpenNotebook,
  onCreateNotebook,
}: NotebookLMDashboardProps) {
  const [filterTab, setFilterTab] = useState<'all' | 'mine' | 'featured' | 'collections'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const filteredNotebooks = SAMPLE_NOTEBOOKS.filter((nb) =>
    nb.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 space-y-8 animate-in fade-in duration-200">
      {/* Controls Bar: Filter Pills + Search + Sort + New Notebook */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setFilterTab('all')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
              filterTab === 'all'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'bg-[#282a2c] text-[#e3e3e3] hover:bg-[#333537]'
            }`}
          >
            Tümü
          </button>
          <button
            onClick={() => setFilterTab('mine')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
              filterTab === 'mine'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'bg-[#282a2c] text-[#e3e3e3] hover:bg-[#333537]'
            }`}
          >
            Not defterlerim
          </button>
          <button
            onClick={() => setFilterTab('featured')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
              filterTab === 'featured'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'bg-[#282a2c] text-[#e3e3e3] hover:bg-[#333537]'
            }`}
          >
            Öne çıkan not defterleri
          </button>
          <button
            onClick={() => setFilterTab('collections')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
              filterTab === 'collections'
                ? 'bg-[#a8c7fa] text-[#041e49] font-semibold'
                : 'bg-[#282a2c] text-[#e3e3e3] hover:bg-[#333537]'
            }`}
          >
            Koleksiyonlar
          </button>
        </div>

        {/* Search, Toggle & Create */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-[#8e918f] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Not defterlerinde ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-1.5 bg-[#1e1f20] border border-[#2d2f31] rounded-full text-xs text-[#e3e3e3] placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa] w-48"
            />
          </div>

          <div className="flex items-center bg-[#1e1f20] border border-[#2d2f31] rounded-full p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-full transition ${
                viewMode === 'grid' ? 'bg-[#333537] text-white' : 'text-[#8e918f] hover:text-white'
              }`}
              title="Izgara Görünümü"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-full transition ${
                viewMode === 'list' ? 'bg-[#333537] text-white' : 'text-[#8e918f] hover:text-white'
              }`}
              title="Liste Görünümü"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={onCreateNotebook}
            className="px-4 py-2 bg-white text-black font-semibold text-xs rounded-full hover:bg-slate-200 transition flex items-center gap-1.5 shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>Yeni not defteri</span>
          </button>
        </div>
      </div>

      {/* Title */}
      <div>
        <h2 className="text-xl font-medium text-[#e3e3e3] tracking-tight">
          Son kullanılan not defterleri
        </h2>
      </div>

      {/* Notebooks Table (List View) */}
      {viewMode === 'list' ? (
        <div className="rounded-2xl overflow-hidden border border-transparent">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#282a2c] text-[#8e918f] font-medium text-[11px]">
                <th className="py-3 px-4">Başlık</th>
                <th className="py-3 px-4">Kaynaklar</th>
                <th className="py-3 px-4">Oluşturulma zamanı</th>
                <th className="py-3 px-4">Rol</th>
                <th className="py-3 px-4 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1f20]">
              {filteredNotebooks.map((nb) => (
                <tr
                  key={nb.id}
                  onClick={() => onOpenNotebook(nb.id)}
                  className="hover:bg-[#1e1f20] transition cursor-pointer group"
                >
                  <td className="py-4 px-4 font-medium text-[#e3e3e3] flex items-center gap-3">
                    <span className="text-base">{nb.icon}</span>
                    <span className="group-hover:text-[#a8c7fa] transition">{nb.title}</span>
                  </td>
                  <td className="py-4 px-4 text-[#c4c7c5]">
                    {nb.sourceCount} kaynak
                  </td>
                  <td className="py-4 px-4 text-[#8e918f]">
                    {nb.createdAt}
                  </td>
                  <td className="py-4 px-4 text-[#8e918f]">
                    {nb.role}
                  </td>
                  <td className="py-4 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <button className="p-1 rounded text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNotebooks.map((nb) => (
            <div
              key={nb.id}
              onClick={() => onOpenNotebook(nb.id)}
              className="p-5 rounded-2xl bg-[#1e1f20] border border-[#2d2f31] hover:border-[#444746] transition cursor-pointer space-y-3 group"
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl">{nb.icon}</span>
                <span className="text-[11px] font-mono text-[#8e918f]">{nb.sourceCount} kaynak</span>
              </div>
              <h3 className="text-sm font-medium text-[#e3e3e3] group-hover:text-[#a8c7fa] transition line-clamp-2">
                {nb.title}
              </h3>
              <div className="text-[11px] text-[#8e918f] pt-2 border-t border-[#282a2c] flex justify-between">
                <span>{nb.createdAt}</span>
                <span>{nb.role}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
