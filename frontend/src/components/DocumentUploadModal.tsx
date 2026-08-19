'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, X, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles } from 'lucide-react';
import { uploadDocument } from '@/lib/api';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function DocumentUploadModal({
  isOpen,
  onClose,
  onSuccess,
}: DocumentUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [department, setDepartment] = useState('engineering');
  const [documentType, setDocumentType] = useState('technical_specification');
  const [language, setLanguage] = useState('tr');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
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

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Lütfen bir dosya seçiniz.');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      await uploadDocument(file, department, documentType, language);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setFile(null);
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Yükleme sırasında hata oluştu.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-[#0e111a] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-white/[0.08]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#131722]/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 text-cyan-400 flex items-center justify-center">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-white tracking-tight">Teknik Doküman Yükle</h3>
              <p className="text-[11px] text-slate-400">Docling ayrıştırıcı & BGE-M3 hibrit indeksleme</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white rounded-lg p-1.5 transition hover:bg-white/[0.06]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleUpload} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center gap-2 text-xs text-rose-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-xs text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Doküman başarıyla işlendi ve indekslendi!</span>
            </div>
          )}

          {/* File Dropzone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-7 text-center cursor-pointer transition flex flex-col items-center justify-center ${
              file
                ? 'border-cyan-500/50 bg-blue-500/5'
                : 'border-white/[0.12] hover:border-cyan-500/40 hover:bg-white/[0.02]'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx,.txt"
              onChange={handleFileChange}
              className="hidden"
            />
            {file ? (
              <div className="flex items-center gap-3 text-slate-200">
                <FileText className="w-8 h-8 text-cyan-400" />
                <div className="text-left">
                  <p className="text-sm font-bold truncate max-w-xs text-white">{file.name}</p>
                  <p className="text-xs text-slate-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
            ) : (
              <>
                <UploadCloud className="w-10 h-10 text-slate-500 mb-2" />
                <p className="text-xs font-semibold text-slate-200">
                  Dosyayı sürükleyin veya <span className="text-cyan-400 underline">gözatın</span>
                </p>
                <p className="text-[11px] text-slate-500 mt-1">PDF, DOCX, XLSX (Maks. 50MB)</p>
              </>
            )}
          </div>

          {/* Metadata Controls */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Departman
              </label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full text-xs bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="engineering">Mühendislik / Tasarım</option>
                <option value="production">Üretim / İmalat</option>
                <option value="service">Servis / Bakım</option>
                <option value="sales">Satış / Teklif</option>
                <option value="quality">Kalite / Test</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Doküman Türü
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="w-full text-xs bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="technical_specification">Teknik Şartname</option>
                <option value="datasheet">Ürün Kataloğu / Datasheet</option>
                <option value="user_manual">Kullanım & Bakım Kılavuzu</option>
                <option value="service_record">Servis / Test Kaydı</option>
                <option value="calculation_sheet">Hesap Raporu</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">
              Dil
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full text-xs bg-[#131722] border border-white/[0.08] rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="tr">Türkçe (TR)</option>
              <option value="en">İngilizce (EN)</option>
              <option value="de">Almanca (DE)</option>
            </select>
          </div>

          {/* Footer Buttons */}
          <div className="pt-4 flex items-center justify-end gap-3 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl transition hover:bg-white/[0.04]"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={!file || isUploading || success}
              className="px-5 py-2.5 text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-xl shadow-lg shadow-blue-500/25 disabled:opacity-50 flex items-center gap-2 transition"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  İşleniyor (Docling)...
                </>
              ) : (
                'İndeksle & Kaydet'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
