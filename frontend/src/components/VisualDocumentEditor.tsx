'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Bold,
  Italic,
  Underline,
  Heading1,
  Heading2,
  Heading3,
  Table as TableIcon,
  List,
  ListOrdered,
  AlertTriangle,
  FileCheck,
  Sparkles,
  Loader2,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface VisualDocumentEditorProps {
  initialMarkdown: string;
  notebookTitle?: string;
  onSave?: (updatedMarkdown: string) => void;
}

export default function VisualDocumentEditor({
  initialMarkdown,
  notebookTitle = 'Selnikel Teknik Raporu',
  onSave,
}: VisualDocumentEditorProps) {
  const [contentHtml, setContentHtml] = useState<string>('');
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const editorRef = useRef<HTMLDivElement>(null);

  // Convert incoming Markdown to editable HTML for visual WYSIWYG
  useEffect(() => {
    if (initialMarkdown) {
      setContentHtml(markdownToHtml(initialMarkdown));
    }
  }, [initialMarkdown]);

  // Command executor for visual formatting (Bold, Italic, Lists, etc.)
  const executeCmd = (command: string, value: string | undefined = undefined) => {
    document.execCommand(command, false, value);
    if (editorRef.current) {
      editorRef.current.focus();
      triggerChange();
    }
  };

  const triggerChange = () => {
    if (editorRef.current && onSave) {
      const md = htmlToMarkdown(editorRef.current.innerHTML);
      onSave(md);
    }
  };

  const handleInsertHeading = (tag: 'h1' | 'h2' | 'h3') => {
    executeCmd('formatBlock', `<${tag}>`);
  };

  const handleInsertTable = () => {
    const tableHtml = `
      <table class="w-full my-4 border-collapse border border-[#37393b] rounded-xl overflow-hidden text-xs">
        <thead>
          <tr class="bg-[#282a2c] text-[#c4c7c5]">
            <th class="border border-[#37393b] p-2 text-left font-semibold">Parametre</th>
            <th class="border border-[#37393b] p-2 text-left font-semibold">Değer</th>
            <th class="border border-[#37393b] p-2 text-left font-semibold">Birim</th>
            <th class="border border-[#37393b] p-2 text-left font-semibold">Durum</th>
          </tr>
        </thead>
        <tbody>
          <tr class="hover:bg-[#282a2c]/40">
            <td class="border border-[#37393b] p-2">Buhar Debisi</td>
            <td class="border border-[#37393b] p-2">1250</td>
            <td class="border border-[#37393b] p-2">kg/h</td>
            <td class="border border-[#37393b] p-2 text-emerald-400">Nominal</td>
          </tr>
          <tr class="hover:bg-[#282a2c]/40">
            <td class="border border-[#37393b] p-2">İşletme Basıncı</td>
            <td class="border border-[#37393b] p-2">16.0</td>
            <td class="border border-[#37393b] p-2">bar</td>
            <td class="border border-[#37393b] p-2 text-emerald-400">Güvenli</td>
          </tr>
        </tbody>
      </table>
      <p><br></p>
    `;
    executeCmd('insertHTML', tableHtml);
  };

  const handleInsertAlert = () => {
    const alertHtml = `
      <div class="my-4 p-3 bg-amber-500/10 border-l-4 border-amber-500 rounded-r-xl text-amber-200 text-xs">
        <strong>ÖNEMLİ MÜHENDİSLİK UYARISI:</strong> Emniyet ventili kalibrasyonu periyodik olarak kontrol edilmelidir.
      </div>
      <p><br></p>
    `;
    executeCmd('insertHTML', alertHtml);
  };

  const handleInsertSignature = () => {
    const sigHtml = `
      <div class="my-6 pt-4 border-t border-[#37393b] grid grid-cols-2 gap-4 text-xs text-[#8e918f]">
        <div>
          <p class="font-semibold text-white">Hazırlayan Mühendis:</p>
          <p class="mt-0.5">Selnikel Ar-Ge Departmanı</p>
          <p class="text-[10px] text-[#8e918f]">Tarih: ${new Date().toLocaleDateString('tr-TR')}</p>
        </div>
        <div class="text-right">
          <p class="font-semibold text-white">Onaylayan Başmühendis:</p>
          <p class="mt-0.5 text-emerald-400 font-mono">✓ DİJİTAL İMZALI & ONAYLI</p>
        </div>
      </div>
      <p><br></p>
    `;
    executeCmd('insertHTML', sigHtml);
  };

  const handleAiPolish = () => {
    setIsAiProcessing(true);
    setTimeout(() => {
      executeCmd('formatBlock', '<p>');
      setIsAiProcessing(false);
      triggerChange();
    }, 400);
  };

  return (
    <div
      className={`flex flex-col bg-[#131314] text-[#e3e3e3] overflow-hidden transition-all ${
        isFullscreen ? 'fixed inset-4 z-50 rounded-2xl shadow-2xl border border-[#37393b]' : 'h-full'
      }`}
    >
      {/* 1. SINGLE COMPACT FORMATTING RIBBON */}
      <div className="px-3 py-1.5 border-b border-[#282a2c] bg-[#1e1f20] flex items-center justify-between gap-1 overflow-x-auto select-none">
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => executeCmd('bold')}
            className="p-1.5 rounded-lg text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Kalın (Ctrl+B)"
          >
            <Bold className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => executeCmd('italic')}
            className="p-1.5 rounded-lg text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="İtalik (Ctrl+I)"
          >
            <Italic className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => executeCmd('underline')}
            className="p-1.5 rounded-lg text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Altı Çizili (Ctrl+U)"
          >
            <Underline className="w-3.5 h-3.5" />
          </button>

          <span className="w-px h-4 bg-[#37393b] mx-1" />

          <button
            onClick={() => handleInsertHeading('h1')}
            className="px-2 py-0.5 rounded-lg text-xs font-bold text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Ana Başlık (H1)"
          >
            H1
          </button>
          <button
            onClick={() => handleInsertHeading('h2')}
            className="px-2 py-0.5 rounded-lg text-xs font-semibold text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Alt Başlık (H2)"
          >
            H2
          </button>

          <span className="w-px h-4 bg-[#37393b] mx-1" />

          <button
            onClick={() => executeCmd('insertUnorderedList')}
            className="p-1.5 rounded-lg text-[#c4c7c5] hover:text-white hover:bg-[#282a2c] transition"
            title="Madde İşaretli Liste"
          >
            <List className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleInsertTable}
            className="px-2 py-1 rounded-lg bg-[#282a2c] hover:bg-[#333537] text-[11px] font-medium text-emerald-400 flex items-center gap-1 transition"
            title="Hesaplama Tablosu Ekle"
          >
            <TableIcon className="w-3 h-3" />
            <span>+ Tablo</span>
          </button>

          <button
            onClick={handleInsertAlert}
            className="px-2 py-1 rounded-lg bg-[#282a2c] hover:bg-[#333537] text-[11px] font-medium text-amber-400 flex items-center gap-1 transition"
            title="Emniyet Uyarısı Ekle"
          >
            <AlertTriangle className="w-3 h-3" />
            <span>+ Uyarı</span>
          </button>

          <button
            onClick={handleInsertSignature}
            className="px-2 py-1 rounded-lg bg-[#282a2c] hover:bg-[#333537] text-[11px] font-medium text-blue-400 flex items-center gap-1 transition"
            title="Mühendislik İmzası Ekle"
          >
            <FileCheck className="w-3 h-3" />
            <span>+ İmza</span>
          </button>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleAiPolish}
            disabled={isAiProcessing}
            className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[11px] font-medium text-[#a8c7fa] flex items-center gap-1 transition border border-[#37393b]"
            title="AI ile İmla ve Formatı Düzenle"
          >
            {isAiProcessing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
            <span>AI Düzenle</span>
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg text-[#8e918f] hover:text-white hover:bg-[#282a2c] transition"
            title={isFullscreen ? 'Tam Ekrandan Çık' : 'Tam Ekran Görsel Düzenleyici'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 2. VISUAL A4 DOCUMENT CANVAS */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#0c0d0e] flex justify-center">
        <div className="w-full max-w-2xl min-h-[500px] bg-[#1e1f20] border border-[#2d2f31] rounded-2xl shadow-xl p-6 sm:p-8 text-[#e3e3e3] relative focus-within:border-[#444746] transition">
          {/* Header Banner on Sheet */}
          <div className="pb-3 mb-4 border-b border-[#282a2c] flex items-center justify-between text-xs text-[#8e918f]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span className="font-bold text-white tracking-tight">SELNİKEL ENERJİ A.Ş.</span>
            </div>
            <span className="font-mono text-[10px]">TEKNİK MÜHENDİSLİK ŞARTNAMESİ</span>
          </div>

          {/* Direct Click-to-Edit Visual Area */}
          <div
            ref={editorRef}
            contentEditable
            suppressContentEditableWarning
            onBlur={triggerChange}
            onInput={triggerChange}
            dangerouslySetInnerHTML={{ __html: contentHtml }}
            className="outline-none min-h-[350px] text-xs leading-relaxed space-y-3 focus:outline-none"
            style={{
              fontFamily:
                '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            }}
          />
        </div>
      </div>
    </div>
  );
}

// Lightweight parser: Markdown -> Visual HTML
function markdownToHtml(md: string): string {
  let cleanMd = (md || '').replace(/<!--[\s\S]*?-->/g, '');
  let html = cleanMd
    // Headers
    .replace(/^# (.*$)/gim, '<h1 class="text-lg font-bold text-white my-2.5">$1</h1>')
    .replace(/^## (.*$)/gim, '<h2 class="text-sm font-semibold text-white my-2">$1</h2>')
    .replace(/^### (.*$)/gim, '<h3 class="text-xs font-medium text-[#a8c7fa] my-1.5">$1</h3>')
    // Bold / Italic
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    // Lists
    .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-[#c4c7c5]">$1</li>')
    // Paragraphs
    .replace(/\n\n/gim, '<p><br></p>');

  // Format Markdown Tables to HTML Tables
  const tableRegex = /\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)+)/g;
  html = html.replace(tableRegex, (match, headerLine, bodyLines) => {
    const headers = headerLine.split('|').filter(Boolean).map((h: string) => h.replace(/<!--[\s\S]*?-->/g, '').trim());
    const rows = bodyLines.trim().split('\n').map((row: string) =>
      row.split('|').filter(Boolean).map((cell: string) => cell.replace(/<!--[\s\S]*?-->/g, '').trim())
    );

    let tHtml = `
      <table class="w-full my-3 border-collapse border border-[#37393b] rounded-xl overflow-hidden text-xs">
        <thead>
          <tr class="bg-[#282a2c] text-[#c4c7c5]">
            ${headers.map((h: string) => `<th class="border border-[#37393b] p-2 text-left font-semibold">${h}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (r: string[]) =>
                `<tr class="hover:bg-[#282a2c]/40">${r
                  .map((c: string) => `<td class="border border-[#37393b] p-2">${c}</td>`)
                  .join('')}</tr>`
            )
            .join('')}
        </tbody>
      </table>
    `;
    return tHtml;
  });

  return html;
}

// Lightweight parser: Visual HTML -> Markdown
function htmlToMarkdown(html: string): string {
  let md = html
    .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n\n')
    .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n\n')
    .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n\n')
    .replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
    .replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
    .replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n')
    .replace(/<br\s*[\/]?>/gi, '\n')
    .replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n');

  const tableRegex = /<table[^>]*>[\s\S]*?<thead>[\s\S]*?<tr[^>]*>([\s\S]*?)<\/tr>[\s\S]*?<\/thead>[\s\S]*?<tbody>([\s\S]*?)<\/tbody>[\s\S]*?<\/table>/gi;
  md = md.replace(tableRegex, (match, thContent, tbContent) => {
    const thMatches = thContent.match(/<th[^>]*>([\s\S]*?)<\/th>/gi) || [];
    const headers = thMatches.map((th: string) => th.replace(/<[^>]+>/g, '').trim());

    const trMatches = tbContent.match(/<tr[^>]*>([\s\S]*?)<\/tr>/gi) || [];
    const rows = trMatches.map((tr: string) => {
      const tdMatches = tr.match(/<td[^>]*>([\s\S]*?)<\/td>/gi) || [];
      return tdMatches.map((td: string) => td.replace(/<[^>]+>/g, '').trim());
    });

    let res = `\n| ${headers.join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n`;
    rows.forEach((r: string[]) => {
      res += `| ${r.join(' | ')} |\n`;
    });
    return res + '\n';
  });

  md = md.replace(/<[^>]+>/g, '');
  return md.trim();
}
