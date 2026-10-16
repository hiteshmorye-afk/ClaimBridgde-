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
  Building2,
  Lock,
  ArrowUpRight,
  Check,
} from "lucide-react";
import { Claim, formatINR } from "@/lib/claims";
import { toast } from "sonner";
import { updateClaimStatus, submitClaimantResponse } from "@/api/claims";
import { getCurrentUser } from "@/api/auth";

interface HumanReviewTriageProps {
  claim: Claim;
  onStatusUpdated?: () => void;
}

export function HumanReviewTriage({ claim, onStatusUpdated }: HumanReviewTriageProps) {
  const [rationale, setRationale] = useState("");
  const [policyRef, setPolicyRef] = useState("");
  const [escalationDest, setEscalationDest] = useState("Chief Medical Adjudicator");
  const [requestedDocumentsText, setRequestedDocumentsText] = useState("");
  const [hospitalResponseNotes, setHospitalResponseNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const currentUser = getCurrentUser();
  const isClaimant = currentUser?.role === "claimant";
  const isClaimsOfficer = currentUser?.role === "claims_officer";
  const isFinalDecision = claim.status === "Approved" || claim.status === "Rejected";

  // TPA Decision Actions
  const handleTpaAction = async (action: "Approve" | "Reject" | "RequestInfo" | "Escalate") => {
    if (!isClaimsOfficer || isFinalDecision) return;
    if (!rationale.trim()) {
      toast.error("A reason is required for every review action.");
      return;
    }
    const requestedDocuments = requestedDocumentsText
      .split(/\r?\n|,/)
      .map((document) => document.trim())
      .filter(Boolean);
    if (action === "RequestInfo" && requestedDocuments.length === 0) {
      toast.error("List the additional documents or information required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await updateClaimStatus(
        claim.id,
        action,
        rationale.trim(),
        action === "Escalate" ? escalationDest : undefined,
        policyRef.trim() || undefined,
        action === "RequestInfo" ? requestedDocuments : undefined,
      );

      toast.success(`Claim ${claim.claimNumber || claim.id} updated: ${action}`, {
        description: rationale || `Adjudication decision executed by TPA Reviewer.`,
      });
      setRationale("");
      setRequestedDocumentsText("");
      if (onStatusUpdated) onStatusUpdated();
    } catch (err: any) {
      toast.error(`Action failed: ${err?.message || "Failed to execute decision"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Hospital Response Action
  const handleHospitalResponse = async () => {
    if (!hospitalResponseNotes.trim()) {
      toast.error("Response notes required", {
        description: "Please provide clinical notes or document details for the TPA reviewer.",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await submitClaimantResponse(claim.id, hospitalResponseNotes.trim());
      toast.success("Response submitted to TPA review queue", {
        description: "Status transitioned to Under Analysis with your response attached.",
      });
      setHospitalResponseNotes("");
      if (onStatusUpdated) onStatusUpdated();
    } catch (err: any) {
      toast.error(`Submission failed: ${err?.message || "Failed to submit response"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* HEADER BANNER */}
      <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <UserCheck className="size-5 text-amber-500" />
            <h3 className="text-lg font-bold text-foreground">Human Review Triage Desk</h3>
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[10px] font-mono font-semibold text-primary">
              {isClaimant ? "Claimant Portal View" : isClaimsOfficer ? "Claims Officer Portal" : "Read-only"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            3-Column Triage Workspace: Inspect documents, review AI evidence trail, and execute permitted workflow actions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-500">
            {claim.routeDecision ? `Route: ${claim.routeDecision}` : "Decision route not available"}
          </span>
          <span className="rounded-full border border-border bg-secondary px-3 py-1 font-mono text-xs text-foreground">
            Status: {claim.status}
          </span>
        </div>
      </div>

      {/* 3-COLUMN LAYOUT */}
      <div className="grid gap-6 lg:grid-cols-3">
        
        {/* COLUMN 1: DOCUMENT VAULT */}
        <div className="flex flex-col rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              1. Document Vault
            </span>
            <span className="font-mono text-xs text-primary">{claim.documents.length} Files</span>
          </div>

          <div className="space-y-2.5 overflow-y-auto max-h-[360px] pr-1">
            {claim.documents.map((doc, idx) => (
              <div
                key={doc.id || `${doc.category}-${idx}`}
                className="flex items-center justify-between rounded-xl border border-border bg-secondary/50 p-3"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileText className="size-4 shrink-0 text-primary" />
                  <div className="truncate">
                    <p className="text-xs font-semibold text-foreground truncate">{doc.category}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{doc.fileName}</p>
                  </div>
                </div>
                <div className="shrink-0 flex items-center gap-1.5">
                  {doc.ocrConfidence && (
                    <span className="font-mono text-[9px] text-muted-foreground">
                      {doc.ocrConfidence}%
                    </span>
                  )}
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-mono ${
                      doc.status === "Verified"
                        ? "bg-emerald-500/10 text-emerald-500"
                        : doc.status === "Failed"
                        ? "bg-rose-500/10 text-rose-500"
                        : "bg-amber-500/10 text-amber-500"
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-border bg-secondary/70 p-3 text-xs space-y-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Claimed Amount:</span>
              <span className="font-mono font-bold text-foreground">{formatINR(claim.claimedAmount)}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Hospital:</span>
              <span className="font-semibold text-foreground">{claim.hospital || "—"}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Policy Number:</span>
              <span className="font-mono text-foreground">{claim.policyNumber}</span>
            </div>
          </div>
        </div>

        {/* COLUMN 2: AI EVIDENCE SYNTHESIS */}
        <div className="flex flex-col rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              2. AI Synthesis Evidence
            </span>
            <Bot className="size-4 text-purple-400" />
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[360px] pr-1">
            {claim.routeReasons && claim.routeReasons.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-500 space-y-1">
                <span className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="size-3.5" /> Human Review Drivers:
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-400/90">
                  {claim.routeReasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {claim.findings.map((finding, idx) => (
              <div
                key={`${finding.label}-${idx}`}
                className="rounded-xl border border-border bg-secondary/60 p-3 space-y-1"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-foreground">{finding.label}</span>
                  <span
                    className={`size-2 rounded-full ${
                      finding.severity === "ok"
                        ? "bg-emerald-500"
                        : finding.severity === "warn" || finding.severity === "warning"
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">{finding.detail}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-border bg-secondary/70 p-3 text-xs flex justify-between">
            <span className="text-muted-foreground">Composite Readiness:</span>
            <span className="font-mono font-bold text-primary">{claim.readiness}%</span>
          </div>
        </div>

        {/* COLUMN 3: DECISION DESK (ROLE-BASED SEPARATION) */}
        <div className="flex flex-col justify-between rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
          
          {/* CLAIMANT VIEW: READ-ONLY FINDINGS + RESPONSE FORM */}
          {isClaimant ? (
            <div className="space-y-4 flex-1 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                    3. Claimant Response Desk
                  </span>
                  <Building2 className="size-4 text-primary" />
                </div>

                {/* Authority Boundary Banner */}
                <div className="rounded-xl border border-border bg-secondary/80 p-3 text-xs space-y-1.5">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <Lock className="size-3.5 text-muted-foreground" /> Adjudication Boundary
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Adjudication decisions are restricted to authorized claims officers. Claimants can submit clarifications and request controlled amendments.
                  </p>
                </div>

                {/* Status Indicator */}
                <div className="rounded-xl border border-border bg-secondary/50 p-3 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Current Status:</span>
                    <span className="font-bold text-foreground">{claim.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Processing Stage:</span>
                    <span className="text-primary font-mono text-[11px]">{claim.stage}</span>
                  </div>
                </div>

                {/* Hospital Response Input */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-foreground">
                    Claimant Response / Document Notes
                  </label>
                  <textarea
                    rows={4}
                    value={hospitalResponseNotes}
                    onChange={(e) => setHospitalResponseNotes(e.target.value)}
                    placeholder="Enter clarification, respond to TPA information requests, or reference newly uploaded documents..."
                    className="w-full rounded-xl border border-border bg-background p-3 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary transition"
                  />
                </div>
              </div>

              {/* Submit Hospital Response Button */}
              <button
                type="button"
                disabled={isSubmitting || !hospitalResponseNotes.trim()}
                onClick={handleHospitalResponse}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-xs font-bold text-white hover:bg-primary/90 transition shadow-md disabled:opacity-50"
              >
                <Send className="size-4" /> Submit Response to TPA Desk
              </button>
            </div>
          ) : isClaimsOfficer ? (
            /* TPA REVIEWER VIEW: FULL ADJUDICATION DECISION CONTROLS */
            <div className="space-y-4 flex-1 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-500">
                    3. TPA Adjudication Decision
                  </span>
                  <ShieldCheck className="size-4 text-emerald-500" />
                </div>

                {/* Reviewer Rationale */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-foreground">
                    Mandatory reason for this action <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    placeholder="Explain the action and cite relevant evidence or applicable policy clauses."
                    className="w-full rounded-xl border border-border bg-background p-3 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary transition"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-[11px] font-medium text-muted-foreground">
                    Additional documents / information required (for requests)
                  </label>
                  <textarea
                    rows={2}
                    value={requestedDocumentsText}
                    onChange={(e) => setRequestedDocumentsText(e.target.value)}
                    placeholder="One item per line"
                    className="w-full rounded-xl border border-border bg-background p-3 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary"
                  />
                </div>

                {/* Policy Reference */}
                <div className="space-y-1">
                  <label className="block text-[11px] font-medium text-muted-foreground">
                    Policy Clause Reference (Optional)
                  </label>
                  <input
                    type="text"
                    value={policyRef}
                    onChange={(e) => setPolicyRef(e.target.value)}
                    placeholder="e.g. Section 4.2 Room Rent Sub-Limit"
                    className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary"
                  />
                </div>

                {/* Escalation Destination */}
                <div className="space-y-1">
                  <label className="block text-[11px] font-medium text-muted-foreground">
                    Escalation Destination (for Escalations)
                  </label>
                  <select
                    value={escalationDest}
                    onChange={(e) => setEscalationDest(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground outline-none focus:border-primary"
                  >
                    <option value="Chief Medical Adjudicator">Chief Medical Adjudicator</option>
                    <option value="Fraud & Special Investigation Unit">Fraud & Special Investigation Unit</option>
                    <option value="Senior TPA Underwriting Committee">Senior TPA Underwriting Committee</option>
                  </select>
                </div>
              </div>

              {/* Action Buttons Restricted to TPA */}
              <div className="space-y-2 pt-2 border-t border-border">
                <button
                  type="button"
                  disabled={isSubmitting || isFinalDecision || !isClaimsOfficer}
                  onClick={() => handleTpaAction("Approve")}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 py-2.5 text-xs font-bold text-white hover:bg-emerald-500 transition shadow-md disabled:opacity-50"
                >
                  <CheckCircle2 className="size-4" /> Approve & Finalize Claim
                </button>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    disabled={isSubmitting || isFinalDecision || !isClaimsOfficer}
                    onClick={() => handleTpaAction("RequestInfo")}
                    className="flex items-center justify-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 py-2 text-xs font-semibold text-amber-500 hover:bg-amber-500/20 transition"
                  >
                    <MessageSquare className="size-3.5" /> Request Info
                  </button>

                  <button
                    type="button"
                    disabled={isSubmitting || isFinalDecision || !isClaimsOfficer}
                    onClick={() => handleTpaAction("Escalate")}
                    className="flex items-center justify-center gap-1.5 rounded-xl border border-purple-500/40 bg-purple-500/10 py-2 text-xs font-semibold text-purple-400 hover:bg-purple-500/20 transition"
                  >
                    <Send className="size-3.5" /> Escalate
                  </button>
                </div>

                <button
                  type="button"
                  disabled={isSubmitting || isFinalDecision || !isClaimsOfficer}
                  onClick={() => handleTpaAction("Reject")}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 py-2 text-xs font-semibold text-rose-500 hover:bg-rose-500/20 transition disabled:opacity-50"
                >
                  <XCircle className="size-4" /> Reject Claim (Rationale Required)
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-secondary/50 p-4 text-xs text-muted-foreground">
              This account cannot submit claimant responses or record claims-officer decisions.
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
