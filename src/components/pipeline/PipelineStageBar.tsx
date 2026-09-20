import React from "react";
import { Check, Loader2, CircleDashed, ArrowRight } from "lucide-react";
import { PIPELINE_STAGES, PipelineStage } from "@/lib/claims";

interface PipelineStageBarProps {
  currentStage: PipelineStage | string;
  onSelectStage?: (stageIndex: number) => void;
  activeStageIndex?: number;
}

export function PipelineStageBar({
  currentStage,
  onSelectStage,
  activeStageIndex,
}: PipelineStageBarProps) {
  const activeIdx =
    activeStageIndex !== undefined
      ? activeStageIndex
      : Math.max(0, PIPELINE_STAGES.findIndex((s) => s === currentStage));

  return (
    <div className="w-full rounded-2xl border border-[#1F2937] bg-[#111827]/90 p-4 backdrop-blur-md shadow-xl">
      <div className="mb-3 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="flex size-2 rounded-full bg-[#06B6D4] animate-ping" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#06B6D4]">
            Visual AI Claim Processing Pipeline
          </span>
        </div>
        <span className="text-xs text-[#9CA3AF]">
          Stage <strong className="text-white font-mono">{activeIdx + 1}</strong> of {PIPELINE_STAGES.length}
        </span>
      </div>

      {/* Horizontal Pipeline Steps */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isCompleted = idx < activeIdx;
          const isCurrent = idx === activeIdx;

          return (
            <React.Fragment key={stage}>
              {idx > 0 && (
                <div
                  className={`h-0.5 w-4 shrink-0 transition-colors ${
                    idx <= activeIdx ? "bg-[#3B82F6]" : "bg-[#1F2937]"
                  }`}
                />
              )}

              <button
                type="button"
                onClick={() => onSelectStage?.(idx)}
                className={`group flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                  isCurrent
                    ? "border border-[#3B82F6] bg-[#3B82F6]/15 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                    : isCompleted
                    ? "border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981] hover:bg-[#10B981]/20"
                    : "border border-[#1F2937] bg-[#111827] text-[#9CA3AF] hover:border-slate-700 hover:text-white"
                }`}
              >
                <span
                  className={`flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    isCurrent
                      ? "bg-[#3B82F6] text-white"
                      : isCompleted
                      ? "bg-[#10B981] text-white"
                      : "bg-[#1F2937] text-[#9CA3AF]"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="size-3 stroke-[3]" />
                  ) : isCurrent ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    idx + 1
                  )}
                </span>
                <span className="whitespace-nowrap font-mono text-[11px]">{stage.replace(/^\d+\s*/, "")}</span>
              </button>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
