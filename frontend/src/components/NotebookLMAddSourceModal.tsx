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
} from 'lucide-react';
import { uploadDocument } from '@/lib/api';

interface NotebookLMAddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function NotebookLMAddSourceModal({
  isOpen,
  onClose,
  onSuccess,
}: NotebookLMAddSourceModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [department, setDepartment] = useState('engineering');
  const [documentType, setDocumentType] = useState('technical_specification');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [webQuery, setWebQuery] = useState('');
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

  const handleUpload = async () => {
    if (!file) {
      setError('Lütfen bir dosya seçin veya sürükleyin.');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      await uploadDocument(file, department, documentType, 'tr');
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setFile(null);
        onSuccess();
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || 'Yükleme başarısız oldu.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-[#1e1f20] border border-[#2d2f31] text-[#e3e3e3] rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-8 space-y-6">
          {/* Header Title with Gradient */}
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Belgelerinizden
            </h2>
            <div className="text-xl font-bold bg-gradient-to-r from-blue-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
              Notlarınıza
            </div>
          </div>

          {/* Web Search Bar in Modal */}
          <div className="relative">
            <div className="flex items-center gap-2 bg-[#131314] border border-[#2d2f31] rounded-2xl px-4 py-3">
              <button className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#282a2c] text-xs font-medium text-[#e3e3e3] hover:bg-[#333537] transition">
                <Globe className="w-3.5 h-3.5 text-blue-400" />
                <span>Web</span>
                <ChevronDown className="w-3 h-3 text-[#8e918f]" />
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#282a2c] text-xs font-medium text-[#e3e3e3] hover:bg-[#333537] transition">
                <span>Hızlı Araştırma</span>
                <ChevronDown className="w-3 h-3 text-[#8e918f]" />
              </button>
              <input
                type="text"
                placeholder="Web'de yeni kaynaklar arayın..."
                value={webQuery}
                onChange={(e) => setWebQuery(e.target.value)}
                className="flex-1 bg-transparent text-xs text-[#e3e3e3] placeholder-[#8e918f] focus:outline-none ml-2"
              />
              <Search className="w-4 h-4 text-[#8e918f]" />
            </div>
          </div>

          {/* Status Banners */}
          {error && (
            <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Doküman başarıyla işlendi ve not defterine eklendi!</span>
            </div>
          )}

          {/* Dropzone Container */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="border border-[#2d2f31] rounded-3xl bg-[#131314] p-8 text-center cursor-pointer hover:border-[#444746] transition flex flex-col items-center justify-center min-h-[170px]"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="hidden"
            />

            {file ? (
              <div className="flex items-center gap-3 text-left">
                <FileText className="w-8 h-8 text-blue-400" />
                <div>
                  <p className="text-sm font-semibold text-white truncate max-w-xs">{file.name}</p>
                  <p className="text-xs text-[#8e918f]">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Hazır
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <p className="text-base font-semibold text-white">
                  veya dosyalarınızı bırakın
                </p>
                <p className="text-xs text-[#8e918f]">
                  pdf, resim, belge, ses, ve daha fazlası
                </p>
              </div>
            )}
          </div>

          {/* Action Buttons Row (Exact NotebookLM Style) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center justify-center gap-2 py-3 px-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-[#e3e3e3] transition"
            >
              <UploadCloud className="w-4 h-4 text-blue-400" />
              <span>Dosya yükle</span>
            </button>

            <button
              type="button"
              onClick={() => alert('Web URL bağlantısı ekleme hazır.')}
              className="flex items-center justify-center gap-2 py-3 px-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-[#e3e3e3] transition"
            >
              <Globe className="w-4 h-4 text-red-400" />
              <span>Web siteleri</span>
            </button>

            <button
              type="button"
              onClick={() => alert('Google Drive entegrasyonu.')}
              className="flex items-center justify-center gap-2 py-3 px-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-[#e3e3e3] transition"
            >
              <HardDrive className="w-4 h-4 text-yellow-400" />
              <span>Drive</span>
            </button>

            <button
              type="button"
              onClick={() => {
                navigator.clipboard.readText().then((clip) => {
                  if (clip) alert(`Panodan kopyalanan metin algılandı (${clip.slice(0, 30)}...)`);
                });
              }}
              className="flex items-center justify-center gap-2 py-3 px-3 rounded-2xl bg-[#282a2c] hover:bg-[#333537] text-xs font-medium text-[#e3e3e3] transition"
            >
              <Clipboard className="w-4 h-4 text-emerald-400" />
              <span>Kopyalanan metin</span>
            </button>
          </div>

          {/* Submit Action */}
          {file && (
            <div className="pt-2 flex justify-end">
              <button
                onClick={handleUpload}
                disabled={isUploading || success}
                className="px-6 py-2.5 bg-[#a8c7fa] hover:bg-[#d3e3fd] text-[#041e49] font-semibold text-xs rounded-full shadow transition flex items-center gap-2"
              >
                {isUploading ? (
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
      </div>
    </div>
  );
}
