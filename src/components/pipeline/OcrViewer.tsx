import React, { useState } from "react";
import { FileText, Eye, CheckCircle2, Search, ZoomIn, ZoomOut, Sparkles, Layers } from "lucide-react";
import { OcrLine } from "@/lib/claims";

interface OcrViewerProps {
  confidence: number;
  lines: OcrLine[];
  fileName?: string;
  documentCategory?: string;
}

export function OcrViewer({
  confidence = 98.93,
  lines = [],
  fileName = "chong_hua_bill_184k.pdf",
  documentCategory = "Hospital Bill",
}: OcrViewerProps) {
  const [selectedLineId, setSelectedLineId] = useState<string | null>(lines[0]?.id || null);
  const [zoomLevel, setZoomLevel] = useState(100);

  const selectedLine = lines.find((l) => l.id === selectedLineId) || lines[0];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      
      {/* LEFT SIDE: DOCUMENT PREVIEW WITH BOUNDING LINES OVERLAY */}
      <div className="flex flex-col rounded-2xl border border-[#1F2937] bg-[#111827] overflow-hidden shadow-xl">
        
        {/* Document Header Controls */}
        <div className="flex items-center justify-between border-b border-[#1F2937] bg-[#0B0F17] px-5 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-[#06B6D4]/20 text-[#06B6D4]">
              <FileText className="size-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">{fileName}</p>
              <p className="text-[10px] text-[#9CA3AF]">{documentCategory} · Simulated High-Res Canvas</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setZoomLevel((z) => Math.max(75, z - 15))}
              className="rounded-lg border border-[#1F2937] bg-[#111827] p-1.5 text-[#9CA3AF] hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut className="size-3.5" />
            </button>
            <span className="font-mono text-[10px] text-[#9CA3AF]">{zoomLevel}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(150, z + 15))}
              className="rounded-lg border border-[#1F2937] bg-[#111827] p-1.5 text-[#9CA3AF] hover:text-white"
              title="Zoom In"
            >
              <ZoomIn className="size-3.5" />
            </button>
          </div>
        </div>

        {/* High-Tech Document Bounding Box Canvas Overlay */}
        <div className="relative flex min-h-[420px] flex-1 items-center justify-center bg-[#070A0F] p-6 overflow-hidden bg-scanline-effect">
          <div
            className="relative aspect-[3/4] w-full max-w-sm rounded-lg border border-[#1F2937] bg-[#0E1420] p-6 shadow-2xl transition-transform duration-200"
            style={{ transform: `scale(${zoomLevel / 100})` }}
          >
            {/* Header Mockup */}
            <div className="border-b border-dashed border-[#1F2937] pb-4 text-center">
              <div className="inline-block rounded bg-[#3B82F6]/10 px-2 py-0.5 text-[9px] font-mono text-[#3B82F6]">
                CHONG HUA HOSPITAL INC.
              </div>
              <p className="mt-1 text-[11px] font-bold text-white">STATEMENT OF ACCOUNT & ITEMIZED BILL</p>
              <p className="text-[9px] text-[#9CA3AF]">Fuente Osmeña, Cebu City · BIR TIN: 000-349-112</p>
            </div>

            {/* Document Bounding Boxes */}
            <div className="mt-4 space-y-3">
              {lines.map((line) => {
                const isSelected = line.id === selectedLineId;
                return (
                  <div
                    key={line.id}
                    onClick={() => setSelectedLineId(line.id)}
                    className={`relative cursor-pointer rounded border p-2 transition-all ${
                      isSelected
                        ? "border-[#06B6D4] bg-[#06B6D4]/15 shadow-[0_0_15px_rgba(6,182,212,0.4)]"
                        : "border-[#1F2937] bg-[#111827]/40 hover:border-[#3B82F6]/60 hover:bg-[#3B82F6]/10"
                    }`}
                  >
                    {/* Bounding Line Indicator Pill */}
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-mono text-[#9CA3AF]">{line.label}</span>
                      <span
                        className={`font-mono text-[9px] ${
                          line.confidence >= 98 ? "text-[#10B981]" : "text-[#F59E0B]"
                        }`}
                      >
                        {line.confidence}%
                      </span>
                    </div>
                    <p className="mt-0.5 font-mono text-xs font-bold text-white">{line.value}</p>

                    {isSelected && (
                      <span className="absolute -top-2 -right-2 flex size-4 items-center justify-center rounded-full bg-[#06B6D4] text-[9px] font-bold text-black">
                        ✓
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Stamp Footer */}
            <div className="mt-6 flex justify-end">
              <div className="rounded border border-[#10B981]/50 bg-[#10B981]/10 px-3 py-1 font-mono text-[9px] font-bold text-[#10B981] rotate-[-6deg]">
                VERIFIED BILL
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* RIGHT SIDE: CONFIDENCE SCORE & EXTRACTED KEY-VALUE TABLE */}
      <div className="flex flex-col rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl">
        
        <div className="flex items-start justify-between border-b border-[#1F2937] pb-5">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-[#06B6D4]" />
              <h3 className="text-base font-bold text-white">OCR Intelligence Engine</h3>
            </div>
            <p className="mt-1 text-xs text-[#9CA3AF]">
              Multi-page deep extraction confidence & bounding box coordinates
            </p>
          </div>

          <div className="flex flex-col items-end">
            <span className="text-[10px] font-mono text-[#9CA3AF] uppercase tracking-wider">
              Extraction Accuracy
            </span>
            <span className="text-3xl font-extrabold font-mono text-[#06B6D4]">
              {confidence}%
            </span>
            <span className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-[#10B981]/20 px-2 py-0.5 text-[10px] font-semibold text-[#10B981]">
              <CheckCircle2 className="size-3" /> High Confidence
            </span>
          </div>
        </div>

        {/* Selected Field Inspector Box */}
        {selectedLine && (
          <div className="my-4 rounded-xl border border-[#06B6D4]/40 bg-[#06B6D4]/10 p-4">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[#06B6D4] uppercase tracking-wider">
                Selected Bounding Box: {selectedLine.id}
              </span>
              <span className="font-mono text-white">Confidence: {selectedLine.confidence}%</span>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-[#9CA3AF]">Field Label:</span>
                <p className="font-semibold text-white">{selectedLine.label}</p>
              </div>
              <div>
                <span className="text-[#9CA3AF]">Parsed Value:</span>
                <p className="font-mono font-bold text-[#10B981]">{selectedLine.value}</p>
              </div>
            </div>
          </div>
        )}

        {/* Extracted Key-Value Lines */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-2">
            Detected Key-Value Lines ({lines.length})
          </p>

          {lines.map((line) => {
            const isSelected = line.id === selectedLineId;
            return (
              <div
                key={line.id}
                onClick={() => setSelectedLineId(line.id)}
                className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition ${
                  isSelected
                    ? "border-[#06B6D4] bg-[#06B6D4]/10"
                    : "border-[#1F2937] bg-[#0B0F17]/50 hover:bg-[#1F2937]/50"
                }`}
              >
                <div>
                  <p className="text-xs text-[#9CA3AF]">{line.label}</p>
                  <p className="text-sm font-semibold font-mono text-white">{line.value}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold ${
                      line.confidence >= 98
                        ? "bg-[#10B981]/20 text-[#10B981]"
                        : "bg-[#F59E0B]/20 text-[#F59E0B]"
                    }`}
                  >
                    {line.confidence}%
                  </span>
                  <Eye className="size-4 text-[#9CA3AF]" />
                </div>
              </div>
            );
          })}
        </div>

      </div>

    </div>
  );
}
