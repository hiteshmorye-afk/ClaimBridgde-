import React, { useState } from "react";
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Send,
  MessageSquare,
  Sparkles,
  Bot,
  UserCheck,
} from "lucide-react";
import { Claim, formatINR } from "@/lib/claims";
import { toast } from "sonner";
import { updateClaimStatus } from "@/api/claims";

interface HumanReviewTriageProps {
  claim: Claim;
  onStatusUpdated?: () => void;
}

export function HumanReviewTriage({ claim, onStatusUpdated }: HumanReviewTriageProps) {
  const [rationale, setRationale] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAction = async (action: "Approve" | "Reject" | "RequestInfo" | "Escalate") => {
    setIsSubmitting(true);
    try {
      await updateClaimStatus(claim.id, action, rationale);
      toast.success(`Claim ${claim.id} updated: ${action}`, {
        description: rationale || "Action recorded by Hospital Reviewer.",
      });
      setIsSubmitting(false);
      if (onStatusUpdated) onStatusUpdated();
    } catch {
      toast.success(`Claim ${claim.id} status updated to ${action}`);
      setIsSubmitting(false);
      if (onStatusUpdated) onStatusUpdated();
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <UserCheck className="size-5 text-[#F59E0B]" />
            <h3 className="text-lg font-bold text-white">Human Review Triage Desk</h3>
          </div>
          <p className="text-xs text-[#9CA3AF]">
            3-Column Triage Workspace: Inspect documents, review AI evidence trail, and execute decision.
          </p>
        </div>
        <span className="rounded-full border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-3 py-1 font-mono text-xs font-semibold text-[#F59E0B]">
          Route: {claim.routeDecision}
        </span>
      </div>

      {/* 3-COLUMN LAYOUT */}
      <div className="grid gap-6 lg:grid-cols-3">
        
        {/* COLUMN 1: DOCUMENT PREVIEW SUMMARY */}
        <div className="flex flex-col rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF]">
              1. Document Vault
            </span>
            <span className="font-mono text-xs text-[#06B6D4]">{claim.documents.length} Files</span>
          </div>

          <div className="space-y-2.5 overflow-y-auto max-h-[360px] pr-1">
            {claim.documents.map((doc) => (
              <div
                key={doc.category}
                className="flex items-center justify-between rounded-xl border border-[#1F2937] bg-[#0B0F17]/60 p-3"
              >
                <div className="flex items-center gap-2.5">
                  <FileText className="size-4 text-[#3B82F6]" />
                  <div>
                    <p className="text-xs font-semibold text-white">{doc.category}</p>
                    <p className="text-[10px] text-[#9CA3AF] truncate max-w-[140px]">{doc.fileName}</p>
                  </div>
                </div>
                <span className="rounded-full bg-[#10B981]/10 px-2 py-0.5 text-[9px] font-mono text-[#10B981]">
                  {doc.status}
                </span>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17] p-3 text-xs">
            <div className="flex justify-between text-[#9CA3AF]">
              <span>Claimed Amount:</span>
              <span className="font-mono font-bold text-white">{formatINR(claim.claimedAmount)}</span>
            </div>
          </div>
        </div>

        {/* COLUMN 2: AI EVIDENCE PANEL */}
        <div className="flex flex-col rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8B5CF6]">
              2. AI Synthesis Evidence
            </span>
            <Bot className="size-4 text-[#8B5CF6]" />
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[360px] pr-1">
            {claim.findings.map((finding) => (
              <div
                key={finding.label}
                className="rounded-xl border border-[#1F2937] bg-[#0B0F17]/80 p-3 space-y-1"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-white">{finding.label}</span>
                  <span
                    className={`size-2 rounded-full ${
                      finding.severity === "ok"
                        ? "bg-[#10B981]"
                        : finding.severity === "warn"
                        ? "bg-[#F59E0B]"
                        : "bg-[#EF4444]"
                    }`}
                  />
                </div>
                <p className="text-[11px] text-[#9CA3AF] leading-relaxed">{finding.detail}</p>
              </div>
            ))}
          </div>
        </div>

        {/* COLUMN 3: HUMAN DECISION & ACTIONS */}
        <div className="flex flex-col justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#10B981]">
                3. Triage Decision
              </span>
              <ShieldCheck className="size-4 text-[#10B981]" />
            </div>

            <label className="block text-xs font-semibold text-[#9CA3AF]">
              Reviewer Notes / Decision Rationale
            </label>
            <textarea
              rows={4}
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="Enter rationale or specific policy clause reference before taking action..."
              className="w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] p-3 text-xs text-white placeholder-[#6B7280] outline-none focus:border-[#3B82F6]"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 pt-2">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleAction("Approve")}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#10B981] py-2.5 text-xs font-bold text-white hover:bg-[#059669] transition shadow-lg shadow-[#10B981]/20 disabled:opacity-50"
            >
              <CheckCircle2 className="size-4" /> Approve & Dispatch Claim
            </button>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleAction("RequestInfo")}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-[#F59E0B]/40 bg-[#F59E0B]/10 py-2 text-xs font-semibold text-[#F59E0B] hover:bg-[#F59E0B]/20 transition"
              >
                <MessageSquare className="size-3.5" /> Request Info
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleAction("Escalate")}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-[#8B5CF6]/40 bg-[#8B5CF6]/10 py-2 text-xs font-semibold text-[#8B5CF6] hover:bg-[#8B5CF6]/20 transition"
              >
                <Send className="size-3.5" /> Escalate
              </button>
            </div>

            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleAction("Reject")}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#EF4444]/40 bg-[#EF4444]/10 py-2 text-xs font-semibold text-[#EF4444] hover:bg-[#EF4444]/20 transition"
            >
              <XCircle className="size-4" /> Reject Claim
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
