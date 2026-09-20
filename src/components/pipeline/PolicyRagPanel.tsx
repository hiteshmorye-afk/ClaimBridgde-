import React from "react";
import { BookOpen, ShieldCheck, AlertTriangle, ExternalLink, CheckCircle2, Sparkles } from "lucide-react";
import { PolicyClauseEvidence } from "@/lib/claims";

interface PolicyRagPanelProps {
  confidence: number; // e.g. 68.51
  clauses: PolicyClauseEvidence[];
  policyNumber?: string;
  insuranceProvider?: string;
}

export function PolicyRagPanel({
  confidence = 68.51,
  clauses = [],
  policyNumber = "POL-CH-99482-B",
  insuranceProvider = "Pacific Healthcare TPA",
}: PolicyRagPanelProps) {
  return (
    <div className="space-y-6">
      
      {/* RAG VERIFICATION HEADER CARD */}
      <div className="flex flex-col gap-4 rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#8B5CF6] to-[#3B82F6] text-white shadow-lg shadow-[#8B5CF6]/30">
            <BookOpen className="size-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-[#8B5CF6] uppercase tracking-wider">
                RAG Policy Verification Engine
              </span>
              <span className="rounded-full bg-[#8B5CF6]/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-[#8B5CF6]">
                Neural Vector Search
              </span>
            </div>
            <h3 className="mt-1 text-lg font-bold text-white">
              Policy Status: Potentially Covered ({confidence}% Confidence)
            </h3>
            <p className="text-xs text-[#9CA3AF]">
              {insuranceProvider} · Policy #{policyNumber}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 border-t border-[#1F2937] pt-4 lg:border-t-0 lg:pt-0">
          <div className="text-right">
            <span className="text-[10px] font-mono text-[#9CA3AF] uppercase">Retrieval Match Score</span>
            <div className="text-2xl font-extrabold font-mono text-[#8B5CF6]">{confidence}%</div>
          </div>
          <div className="flex size-10 items-center justify-center rounded-xl bg-[#8B5CF6]/20 text-[#8B5CF6]">
            <Sparkles className="size-5" />
          </div>
        </div>
      </div>

      {/* EVIDENCE CARDS GRID */}
      <div className="space-y-4">
        <h4 className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider">
          Retrieved Policy Clauses & Exclusion Evidence Cards ({clauses.length})
        </h4>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {clauses.map((clause) => (
            <div
              key={clause.id}
              className="flex flex-col justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl transition-all duration-300 hover:border-[#8B5CF6]/50 hover:shadow-[0_0_20px_rgba(139,92,246,0.2)]"
            >
              <div>
                <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
                  <span className="font-mono text-xs font-semibold text-[#06B6D4]">{clause.section}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      clause.status === "Verified"
                        ? "bg-[#10B981]/20 text-[#10B981]"
                        : clause.status === "Conditional"
                        ? "bg-[#F59E0B]/20 text-[#F59E0B]"
                        : "bg-[#EF4444]/20 text-[#EF4444]"
                    }`}
                  >
                    {clause.status}
                  </span>
                </div>

                <h5 className="mt-3 text-sm font-bold text-white leading-snug">{clause.clauseTitle}</h5>

                <p className="mt-2 text-xs text-[#9CA3AF] italic bg-[#0B0F17] p-3 rounded-xl border border-[#1F2937] leading-relaxed">
                  "{clause.textSnippet}"
                </p>
              </div>

              <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#1F2937]">
                <div className="flex items-center gap-1.5 text-xs text-[#9CA3AF]">
                  <CheckCircle2 className="size-3.5 text-[#10B981]" />
                  <span>Score: {clause.confidence}%</span>
                </div>

                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#3B82F6] hover:underline"
                >
                  View Citation <ExternalLink className="size-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
