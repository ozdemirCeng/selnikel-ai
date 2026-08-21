'use client';

import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  Bot,
  Play,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileText,
  Copy,
  Check,
  Download,
  Loader2,
  Layers,
  Cpu,
  Zap,
  ArrowRight,
  FileSpreadsheet,
  Presentation,
  FileCheck,
  Wrench,
  Flame,
  Wind,
  ShieldCheck,
  BarChart3,
  RefreshCw,
  Sliders,
  Maximize2,
  Terminal,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AgentExecutionResponse, ToolDefinition } from '@/lib/types';
import {
  fetchAgentTools,
  runAgentQuery,
  downloadPdfReport,
  downloadExcelReport,
  downloadWordReport,
  downloadPowerPointReport,
} from '@/lib/api';
import VisualDocumentEditor from './VisualDocumentEditor';

const PRESET_AGENT_TASKS = [
  {
    icon: '🔥',
    title: 'SB-100 Termal Verim & Yakıt',
    query:
      'Selnikel SB-100 kazanının 1000 kg/h buhar debisi ve 16 bar işletme basıncında doğal gaz tüketimini ve termal verimini hesapla, teknik rapor oluştur.',
  },
  {
    icon: '💨',
    title: 'Brülör Yanma & Baca Gazı Kaybı',
    query:
      'Doğal gaz yakan bir brülör için saatte 250 Nm3/h yakıt tüketiminde, %3.0 artık O2 ve 160 °C baca gazı sıcaklığında Siegert formülüyle baca kaybını ve yanma verimini hesapla.',
  },
  {
    icon: '♻️',
    title: 'Ekonomizer Atık Isı Geri Kazanımı',
    query:
      '5000 kg/h buhar kapasiteli kazanda baca gazı sıcaklığını 220 °C den 130 °C ye düşüren ekonomizerin geri kazandığı ısıl gücü (kW) ve yıllık doğal gaz tasarrufunu hesapla.',
  },
  {
    icon: '🛡️',
    title: 'Emniyet Ventili Boyutlandırma',
    query:
      '5000 kg/h buhar kapasiteli ve 16 bar_g işletme basınçlı buhar kazanı için EN ISO 4126-1 standardına göre minimum emniyet ventili orifis alanını ve önerilen DN anma çapını hesapla.',
  },
  {
    icon: '🌪️',
    title: '600 mm Fan Debi & Motor Gücü',
    query:
      '600 mm kanal çapı ve 20 m/s hava hızında çalışan 1500 Pa basınçlı endüstriyel fanın debisini (m3/h) ve tavsiye edilen motor gücünü (kW) hesapla.',
  },
  {
    icon: '📊',
    title: 'Çoklu Yakıt Karşılaştırması',
    query:
      'Doğal gaz ve fuel-oil yakıtları için 2000 kg/h buhar kapasitesinde yıllık yakıt maliyeti ve emisyon karşılaştırma tablosu hazırla.',
  },
];

export default function AgentStudio() {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [inputQuery, setInputQuery] = useState(
    'Selnikel SB-100 kazanının 1000 kg/h buhar debisi ve 16 bar işletme basıncında doğal gaz tüketimini ve termal verimini hesapla, teknik rapor oluştur.'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentResponse, setAgentResponse] = useState<AgentExecutionResponse | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<'visual' | 'preview' | 'metrics'>('visual');

  useEffect(() => {
    fetchAgentTools()
      .then(setTools)
      .catch((e) => console.error('Failed to load tools', e));
  }, []);

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepNumber]: !prev[stepNumber],
    }));
  };

  const handleRunAgent = async (queryText?: string) => {
    const query = (queryText || inputQuery).trim();
    if (!query || isLoading) return;

    setInputQuery(query);
    setIsLoading(true);
    setError(null);
    setExpandedSteps({});

    try {
      const response = await runAgentQuery(query);
      setAgentResponse(response);
      const openMap: Record<number, boolean> = {};
      response.steps.forEach((s) => {
        openMap[s.step_number] = true;
      });
      setExpandedSteps(openMap);
    } catch (err: any) {
      setError(err.message || 'Ajan görevi yürütülürken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'excel' | 'word' | 'pptx') => {
    const content = agentResponse?.final_answer;
    if (!content) return;
    setIsExporting(format);
    try {
      if (format === 'pdf') {
        await downloadPdfReport(content, 'Selnikel Otonom Ajan Raporu');
      } else if (format === 'excel') {
        await downloadExcelReport(content, 'Selnikel Otonom Ajan Verileri');
      } else if (format === 'word') {
        await downloadWordReport(content, 'Selnikel Otonom Ajan Raporu');
      } else if (format === 'pptx') {
        await downloadPowerPointReport(content, 'Selnikel Otonom Ajan Sunumu');
      }
    } catch (err: any) {
      alert(`Dışa aktarma başarısız: ${err.message}`);
    } finally {
      setIsExporting(null);
    }
  };

  return (
    <div className="h-[calc(100vh-5.5rem)] flex flex-col gap-3 pb-2">
      {/* 1. TOP STATUS & ENGINE TOOLBAR */}
      <div className="px-4 py-2.5 bg-[#1e1f20] border border-[#2d2f31] rounded-2xl flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-[#282a2c] border border-[#37393b] flex items-center justify-center text-[#a8c7fa]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold text-white tracking-tight">
                Otonom Mühendislik Ajanı (ReAct Studio)
              </h2>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-mono font-semibold border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {tools.length || 8} Endüstriyel Araç Aktif
              </span>
            </div>
            <p className="text-[11px] text-[#8e918f]">
              Çok adımlı termodinamik/akışkan hesap motorları ve doğrulanmış RAG aramaları ile otomatik teknik raporlama
            </p>
          </div>
        </div>

        {/* Action Preset Pills */}
        <div className="hidden xl:flex items-center gap-1.5">
          {PRESET_AGENT_TASKS.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => handleRunAgent(preset.query)}
              disabled={isLoading}
              className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-[#333537] text-[11px] text-[#c4c7c5] hover:text-white transition flex items-center gap-1 border border-[#37393b]"
            >
              <span>{preset.icon}</span>
              <span className="truncate max-w-[130px]">{preset.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 2. MAIN 2-PANE WORKSPACE */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 overflow-hidden">
        {/* ─── LEFT COLUMN: COMMAND & REASONING CONSOLE (5 COLS) ─── */}
        <div className="lg:col-span-5 h-full bg-[#1e1f20] rounded-2xl border border-[#2d2f31] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-3.5 border-b border-[#282a2c] flex items-center justify-between bg-[#1e1f20]">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#a8c7fa]" />
              <span className="text-xs font-semibold text-white">Görev & Akıl Yürütme Konsolu</span>
            </div>

            {agentResponse && (
              <span className="text-[10px] font-mono text-[#8e918f]">
                {agentResponse.steps.length} Adım &bull; {agentResponse.tools_used.length} Araç
              </span>
            )}
          </div>

          {/* Preset Quick Chips (Mobile/Tablet) */}
          <div className="xl:hidden p-2.5 border-b border-[#282a2c] bg-[#18191b] flex items-center gap-1.5 overflow-x-auto">
            {PRESET_AGENT_TASKS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => handleRunAgent(preset.query)}
                disabled={isLoading}
                className="px-2 py-0.5 rounded-full bg-[#282a2c] text-[10px] text-[#c4c7c5] shrink-0 border border-[#37393b]"
              >
                {preset.icon} {preset.title}
              </button>
            ))}
          </div>

          {/* Mission Input Form */}
          <div className="p-3.5 border-b border-[#282a2c] bg-[#131314] space-y-2.5">
            <textarea
              rows={3}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ajan için bir mühendislik görevi tanımlayın (ör. SB-100 termal verimini ve yakıt tüketimini hesaplayıp raporla)..."
              disabled={isLoading}
              className="w-full p-3 bg-[#1e1f20] border border-[#2d2f31] rounded-xl text-xs text-white placeholder-[#8e918f] focus:outline-none focus:border-[#a8c7fa] resize-none leading-relaxed"
            />

            <button
              onClick={() => handleRunAgent()}
              disabled={!inputQuery.trim() || isLoading}
              className="w-full py-2.5 px-4 bg-[#a8c7fa] hover:bg-[#d3e3fd] disabled:opacity-40 text-[#041e49] font-semibold text-xs rounded-full flex items-center justify-center gap-2 transition shadow-md"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Ajan Akıl Yürütüyor (Adımlar İşleniyor)...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Görevi Yürüt (ReAct Plan & Execute)</span>
                </>
              )}
            </button>
          </div>

          {/* Stepper Timeline Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#131314]">
            {isLoading ? (
              <div className="h-64 flex flex-col items-center justify-center gap-3 text-[#8e918f]">
                <div className="w-12 h-12 rounded-full bg-[#1e1f20] border border-[#282a2c] flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-[#a8c7fa]" />
                </div>
                <div className="text-center space-y-1">
                  <p className="text-xs font-medium text-white">Mühendislik Ajanı Çalışıyor...</p>
                  <p className="text-[11px] text-[#8e918f] max-w-xs">
                    Termodinamik formüller çözülüyor, RAG dokümanları taranıyor ve teknik rapor sentezleniyor.
                  </p>
                </div>
              </div>
            ) : error ? (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            ) : !agentResponse ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#8e918f] space-y-3">
                <Bot className="w-8 h-8 text-[#8e918f]/40" />
                <p className="text-xs font-medium text-[#c4c7c5]">Ajan Beklemede</p>
                <p className="text-[11px] text-[#8e918f] max-w-xs">
                  Yukarıdaki görev kutusuna bir talep girin veya hazır mühendislik şablonlarından birine tıklayarak otonom akıl yürütmeyi başlatın.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-[11px] text-[#8e918f] px-1">
                  <span className="font-semibold text-[#c4c7c5]">Yürütülen ReAct Adımları</span>
                  <span>{agentResponse.steps.length} Eylem Tamamlandı</span>
                </div>

                {agentResponse.steps.map((step) => {
                  const isExpanded = !!expandedSteps[step.step_number];
                  const toolName = step.tool_call?.tool_name;
                  const toolArgs = step.tool_call?.arguments;
                  const observation = step.tool_result?.data || step.tool_result?.error;

                  return (
                    <div
                      key={step.step_number}
                      className="bg-[#1e1f20] border border-[#282a2c] rounded-xl overflow-hidden transition"
                    >
                      {/* Step Header Accordion */}
                      <button
                        onClick={() => toggleStep(step.step_number)}
                        className="w-full p-2.5 text-left flex items-center justify-between hover:bg-[#282a2c]/50 transition text-xs"
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className="w-5 h-5 rounded-full bg-[#282a2c] text-[#a8c7fa] font-mono text-[10px] font-bold flex items-center justify-center shrink-0 border border-[#37393b]">
                            {step.step_number}
                          </span>
                          <span className="font-mono text-[#a8c7fa] font-semibold text-[11px] truncate">
                            {toolName || 'Akıl Yürütme'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[#8e918f] shrink-0">
                          <span className="text-[10px]">Detay</span>
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </div>
                      </button>

                      {/* Step Details */}
                      {isExpanded && (
                        <div className="p-3 border-t border-[#282a2c] space-y-2 text-xs bg-[#18191b]">
                          {/* Thought */}
                          {step.thought && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-semibold text-[#8e918f] flex items-center gap-1">
                                <span>💭</span> Düşünce:
                              </span>
                              <p className="text-[11px] text-[#e3e3e3] bg-[#1e1f20] p-2 rounded-lg border border-[#282a2c] leading-relaxed">
                                {step.thought}
                              </p>
                            </div>
                          )}

                          {/* Tool & Args */}
                          {toolName && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-semibold text-blue-400 flex items-center gap-1">
                                <span>🛠️</span> Çağrılan Araç:
                              </span>
                              <div className="bg-[#131314] p-2 rounded-lg font-mono text-[10px] text-blue-300 overflow-x-auto border border-[#282a2c]">
                                {toolName}({JSON.stringify(toolArgs || {})})
                              </div>
                            </div>
                          )}

                          {/* Observation */}
                          {observation && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-semibold text-emerald-400 flex items-center gap-1">
                                <span>📊</span> Gözlem Çıktısı:
                              </span>
                              <div className="bg-[#131314] p-2 rounded-lg font-mono text-[10px] text-emerald-300 overflow-x-auto max-h-36 overflow-y-auto border border-[#282a2c]">
                                {typeof observation === 'object'
                                  ? JSON.stringify(observation, null, 2)
                                  : observation}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ─── RIGHT COLUMN: LIVE ARTIFACT & WORD/A4 CANVAS (7 COLS) ─── */}
        <div className="lg:col-span-7 h-full bg-[#1e1f20] rounded-2xl border border-[#2d2f31] flex flex-col overflow-hidden">
          {/* Header with Mode Switcher & Exporters */}
          <div className="p-3 border-b border-[#282a2c] bg-[#1e1f20] flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white">Mühendislik Rapor Tuvali</span>

              {/* View Switchers */}
              <div className="flex items-center bg-[#131314] border border-[#282a2c] rounded-full p-0.5 text-xs">
                <button
                  onClick={() => setRightTab('visual')}
                  className={`px-3 py-1 rounded-full font-medium transition ${
                    rightTab === 'visual'
                      ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                      : 'text-[#8e918f] hover:text-white'
                  }`}
                  title="Word/A4 Tarzı Görsel Düzenleyici"
                >
                  Görsel Sayfa
                </button>
                <button
                  onClick={() => setRightTab('preview')}
                  className={`px-3 py-1 rounded-full font-medium transition ${
                    rightTab === 'preview'
                      ? 'bg-[#a8c7fa] text-[#041e49] font-bold'
                      : 'text-[#8e918f] hover:text-white'
                  }`}
                  title="Okuma Önizlemesi"
                >
                  Önizleme
                </button>
              </div>
            </div>

            {/* Exporters Bar */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={() => handleExport('excel')}
                disabled={!agentResponse?.final_answer || !!isExporting}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-emerald-600/20 text-emerald-400 text-xs font-semibold flex items-center gap-1 transition border border-[#37393b] disabled:opacity-40"
                title="Excel (.xlsx) Tablosu Olarak İndir"
              >
                {isExporting === 'excel' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileSpreadsheet className="w-3 h-3" />}
                <span>.XLSX</span>
              </button>

              <button
                onClick={() => handleExport('word')}
                disabled={!agentResponse?.final_answer || !!isExporting}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-blue-600/20 text-blue-400 text-xs font-semibold flex items-center gap-1 transition border border-[#37393b] disabled:opacity-40"
                title="Word (.docx) Şartnamesi Olarak İndir"
              >
                {isExporting === 'word' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                <span>.DOCX</span>
              </button>

              <button
                onClick={() => handleExport('pptx')}
                disabled={!agentResponse?.final_answer || !!isExporting}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-amber-600/20 text-amber-400 text-xs font-semibold flex items-center gap-1 transition border border-[#37393b] disabled:opacity-40"
                title="PowerPoint (.pptx) Sunumu Olarak İndir"
              >
                {isExporting === 'pptx' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Presentation className="w-3.5 h-3.5" />}
                <span>.PPTX</span>
              </button>

              <button
                onClick={() => handleExport('pdf')}
                disabled={!agentResponse?.final_answer || !!isExporting}
                className="px-2.5 py-1 rounded-full bg-[#282a2c] hover:bg-rose-600/20 text-rose-400 text-xs font-semibold flex items-center gap-1 transition border border-[#37393b] disabled:opacity-40"
                title="PDF (.pdf) Raporu Olarak İndir"
              >
                {isExporting === 'pdf' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileCheck className="w-3.5 h-3.5" />}
                <span>.PDF</span>
              </button>
            </div>
          </div>

          {/* Main Artifact Body */}
          <div className="flex-1 overflow-hidden relative bg-[#131314]">
            {agentResponse?.final_answer ? (
              rightTab === 'visual' ? (
                <VisualDocumentEditor
                  initialMarkdown={agentResponse.final_answer}
                  notebookTitle="Selnikel Otonom Ajan Raporu"
                />
              ) : (
                <div className="p-6 overflow-y-auto h-full prose prose-invert prose-xs max-w-none text-xs leading-relaxed text-[#e3e3e3]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {agentResponse.final_answer}
                  </ReactMarkdown>
                </div>
              )
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-[#8e918f] space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-[#1e1f20] border border-[#282a2c] flex items-center justify-center text-[#a8c7fa]">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="space-y-1 max-w-md">
                  <h3 className="text-sm font-semibold text-white">Canlı Mühendislik Rapor Alanı</h3>
                  <p className="text-xs text-[#8e918f] leading-relaxed">
                    Ajan sol taraftan görevi tamamladığında nihai hesaplama tabloları ve şartnameler doğrudan burada **Word / A4 Görsel Sayfa Düzenleyicide** açılır. İstediğiniz sayıyı veya maddeyi tıklayıp değiştirebilir, anında Excel/Word/PDF olarak indirebilirsiniz.
                  </p>
                </div>

                {/* KPI Teaser Cards */}
                <div className="grid grid-cols-3 gap-3 w-full max-w-md pt-2">
                  <div className="p-3 rounded-xl bg-[#1e1f20] border border-[#282a2c] text-left">
                    <span className="text-[10px] text-[#8e918f] block">Termal Verim</span>
                    <span className="text-xs font-mono font-bold text-emerald-400">%91.5 ASME</span>
                  </div>
                  <div className="p-3 rounded-xl bg-[#1e1f20] border border-[#282a2c] text-left">
                    <span className="text-[10px] text-[#8e918f] block">Yakıt Analizi</span>
                    <span className="text-xs font-mono font-bold text-blue-400">Nm3/h Doğal Gaz</span>
                  </div>
                  <div className="p-3 rounded-xl bg-[#1e1f20] border border-[#282a2c] text-left">
                    <span className="text-[10px] text-[#8e918f] block">İhracat</span>
                    <span className="text-xs font-mono font-bold text-amber-400">.XLSX & .DOCX</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
