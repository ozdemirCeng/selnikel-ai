'use client';

import React, { useEffect, useState } from 'react';
import {
  FileText,
  UploadCloud,
  Trash2,
  Layers,
  Search,
  Filter,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FolderOpen,
  Calendar,
  HardDrive,
  ExternalLink,
  Plus,
  Loader2,
  Eye,
} from 'lucide-react';
import { DocumentItem } from '@/lib/types';
import { deleteDocument, fetchDocuments } from '@/lib/api';
import NotebookLMAddSourceModal from './NotebookLMAddSourceModal';
import ChunkInspectorModal from './ChunkInspectorModal';

export default function DocumentCatalog() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Inspector modal state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocName, setSelectedDocName] = useState<string>('');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState<string>('all');
  const [docTypeFilter, setDocTypeFilter] = useState<string>('all');

  // Delete State
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [departmentFilter, docTypeFilter]);

  const loadDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const dept = departmentFilter === 'all' ? undefined : departmentFilter;
      const dtype = docTypeFilter === 'all' ? undefined : docTypeFilter;
      const data = await fetchDocuments(dept, dtype);
      setDocuments(data);
    } catch (err: any) {
      setError(err.message || 'Dokümanlar yüklenemedi.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`"${name}" dokümanını ve tüm vektör parçalarını silmek istediğinize emin misiniz?`)) {
      return;
    }

    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      alert(`Silme başarısız: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-2xl overflow-hidden flex flex-col">
      {/* Integrated Unified Header & Omnibar */}
      <div className="p-4 border-b border-[#282a2c] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-[#282a2c] border border-[#37393b] flex items-center justify-center text-[#a8c7fa]">
            <FolderOpen className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold text-white tracking-tight">
                Teknik Doküman Kataloğu & Vektör Deposu
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#282a2c] text-[#a8c7fa] border border-[#37393b]">
                {filteredDocs.length} Doküman
              </span>
            </div>
            <p className="text-[11px] text-[#8e918f]">
              IBM Docling ile ayrıştırılmış teknik şartnameler ve Qdrant hibrid vektör indeksleri
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Omnibar */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-[#8e918f] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Doküman adı ile ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#131314] border border-[#2d2f31] rounded-full text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa] transition"
            />
          </div>

          {/* Department Filter Pills */}
          <div className="flex items-center gap-1 bg-[#131314] border border-[#282a2c] rounded-full p-0.5 text-xs">
            <button
              onClick={() => setDepartmentFilter('all')}
              className={`px-3 py-1 rounded-full font-medium transition ${
                departmentFilter === 'all'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Tümü
            </button>
            <button
              onClick={() => setDepartmentFilter('engineering')}
              className={`px-3 py-1 rounded-full font-medium transition ${
                departmentFilter === 'engineering'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'text-[#8e918f] hover:text-white'
              }`}
            >
              Ar-Ge
            </button>
            <button
              onClick={() => setDepartmentFilter('manufacturing')}
              className={`px-3 py-1 rounded-full font-medium transition ${
                departmentFilter === 'manufacturing'
                  ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                  : 'text-[#8e918f] hover:text-white'
              }`}
            >
              İmalat
            </button>
          </div>

          <button
            onClick={loadDocuments}
            disabled={isLoading}
            className="p-1.5 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[#c4c7c5] hover:text-white transition border border-[#37393b]"
            title="Yenile"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-3.5 py-1.5 bg-white text-black font-semibold text-xs rounded-full hover:bg-slate-200 transition flex items-center gap-1.5 shadow-md shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Doküman Ekle</span>
          </button>
        </div>
      </div>

      {/* Documents Table View */}
      <div className="bg-[#1e1f20] border border-[#2d2f31] rounded-3xl overflow-hidden">
        {isLoading ? (
          <div className="h-48 flex items-center justify-center gap-2 text-xs text-[#8e918f]">
            <Loader2 className="w-5 h-5 animate-spin text-[#a8c7fa]" />
            <span>Doküman kataloğu yükleniyor...</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="h-48 flex flex-col items-center justify-center text-center p-6 text-[#8e918f] space-y-2">
            <FileText className="w-8 h-8 text-[#8e918f]/50" />
            <span className="text-xs text-[#c4c7c5]">Doküman bulunamadı.</span>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="text-xs text-[#a8c7fa] hover:underline"
            >
              İlk dokümanınızı ekleyin
            </button>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#282a2c] text-[#8e918f] font-medium text-[11px]">
                <th className="py-3.5 px-5">Doküman Adı</th>
                <th className="py-3.5 px-4">Departman</th>
                <th className="py-3.5 px-4">Sayfa / Parça</th>
                <th className="py-3.5 px-4">Boyut</th>
                <th className="py-3.5 px-4">Tarih</th>
                <th className="py-3.5 px-5 text-right">Aksiyonlar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#282a2c]">
              {filteredDocs.map((doc) => (
                <tr key={doc.id} className="hover:bg-[#282a2c]/60 transition group">
                  <td className="py-4 px-5 font-medium text-white flex items-center gap-3">
                    <FileText className="w-4 h-4 text-[#a8c7fa] shrink-0" />
                    <span className="truncate max-w-xs">{doc.filename}</span>
                  </td>
                  <td className="py-4 px-4 text-[#c4c7c5]">
                    <span className="px-2.5 py-0.5 rounded-full bg-[#282a2c] text-[10px] border border-[#37393b]">
                      {doc.department}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-[#8e918f]">
                    {doc.total_pages || 1} sayfa &bull; {doc.chunk_count || 0} parça
                  </td>
                  <td className="py-4 px-4 text-[#8e918f]">
                    {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(1)} KB` : '-'}
                  </td>
                  <td className="py-4 px-4 text-[#8e918f]">
                    {new Date(doc.created_at).toLocaleDateString('tr-TR')}
                  </td>
                  <td className="py-4 px-5 text-right space-x-1">
                    <button
                      onClick={() => {
                        setSelectedDocId(doc.id);
                        setSelectedDocName(doc.filename);
                      }}
                      className="p-1.5 rounded-lg text-[#8e918f] hover:text-white hover:bg-[#333537] transition"
                      title="Parçaları İncele"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id, doc.filename)}
                      disabled={deletingId === doc.id}
                      className="p-1.5 rounded-lg text-[#8e918f] hover:text-rose-400 hover:bg-[#333537] transition"
                      title="Dokümanı Sil"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      <NotebookLMAddSourceModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={loadDocuments}
      />

      <ChunkInspectorModal
        documentId={selectedDocId}
        filename={selectedDocName}
        isOpen={!!selectedDocId}
        onClose={() => {
          setSelectedDocId(null);
          setSelectedDocName('');
        }}
      />
    </div>
  );
}
