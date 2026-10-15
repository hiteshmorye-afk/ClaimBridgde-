import { createFileRoute, useNavigate, useParams, Link } from "@tanstack/react-router";
import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  FileText,
  Stethoscope,
  BookOpen,
  Zap,
  UserCheck,
  Building2,
  Calendar,
  DollarSign,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Download,
  Share2,
  Clock,
  History,
  FileCheck2,
  Eye,
  Check,
  XCircle,
  HelpCircle,
  Layers,
  Sparkles,
} from "lucide-react";

import { AppLayout } from "@/components/layout/AppLayout";
import { formatDate, formatINR, convertApiClaimToClaim, Claim } from "@/lib/claims";
import { fetchClaimById, ClaimApiData } from "@/api/claims";
import { PipelineStageBar } from "@/components/pipeline/PipelineStageBar";
import { OcrViewer } from "@/components/pipeline/OcrViewer";
import { MedicalIntelligence } from "@/components/pipeline/MedicalIntelligence";
import { PolicyRagPanel } from "@/components/pipeline/PolicyRagPanel";
import { ReadinessGauge } from "@/components/pipeline/ReadinessGauge";
import { HumanReviewTriage } from "@/components/pipeline/HumanReviewTriage";
import { generateClaimPDFReport } from "@/api/integrations";

export const Route = createFileRoute("/claims/$claimId")({
  head: () => ({
    meta: [
      { title: "Claim Readiness & Verification Trail — ClaimBridge" },
      {
        name: "description",
        content:
          "Authoritative Claim Readiness Dashboard: real multi-document OCR, field-level validation, RAG policy evidence, readiness scoring, and auditable history.",
      },
    ],
  }),
  component: ClaimDetailPage,
});

type TabType =
  | "readiness"
  | "validation"
  | "documents"
  | "medical_policy"
  | "history"
  | "triage";

function ClaimDetailPage() {
  const { claimId } = useParams({ from: "/claims/$claimId" });
  const navigate = useNavigate();

  const [claimData, setClaimData] = useState<ClaimApiData | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [activeTab, setActiveTab] = useState<TabType>("readiness");
  const [selectedDocIndex, setSelectedDocIndex] = useState(0);

  const loadClaim = () => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage("");

    fetchClaimById(claimId)
      .then((data) => {
        if (data) {
          setClaimData(data);
          setClaim(convertApiClaimToClaim(data));
        }
      })
      .catch((err: any) => {
        const msg = err?.message || "Failed to load claim.";
        setErrorMessage(msg);
        if (msg.includes("403") || msg.toLowerCase().includes("forbidden") || msg.toLowerCase().includes("access denied")) {
          setErrorStatus(403);
        } else if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
          setErrorStatus(404);
        } else {
          setErrorStatus(500);
        }
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadClaim();
  }, [claimId]);

  if (loading) {
    return (
      <AppLayout title="Loading Claim Readiness...">
        <div className="flex min-h-[460px] flex-col items-center justify-center gap-4 text-center">
          <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm font-semibold text-foreground">Loading claim details from ClaimBridge backend...</p>
          <p className="text-xs text-muted-foreground font-mono">{claimId}</p>
        </div>
      </AppLayout>
    );
  }

  if (errorStatus === 403) {
    return (
      <AppLayout title="Access Restricted">
        <div className="mx-auto max-w-lg rounded-2xl border border-rose-500/30 bg-card p-8 text-center space-y-4 shadow-xl my-12">
          <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500">
            <ShieldCheck className="size-6" />
          </div>
          <h2 className="text-lg font-bold text-foreground">Organization Access Boundary</h2>
          <p className="text-xs text-muted-foreground">
            {errorMessage || "You are not authorized to view claims outside your assigned hospital or insurance organization scope."}
          </p>
          <div className="pt-2">
            <Link
              to="/claims"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-primary/90 transition"
            >
              <ArrowLeft className="size-4" /> Return to Claims Portfolio
            </Link>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!claim || errorStatus === 404) {
    return (
      <AppLayout title="Claim Not Found">
        <div className="mx-auto max-w-lg rounded-2xl border border-border bg-card p-8 text-center space-y-4 shadow-xl my-12">
          <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500">
            <AlertTriangle className="size-6" />
          </div>
          <h2 className="text-lg font-bold text-foreground">Claim Not Found</h2>
          <p className="text-xs text-muted-foreground">
            Claim <strong className="font-mono text-foreground">{claimId}</strong> was not found in the active ClaimBridge workspace.
          </p>
          <div className="pt-2">
            <Link
              to="/claims"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-primary/90 transition"
            >
              <ArrowLeft className="size-4" /> View All Claims
            </Link>
          </div>
        </div>
      </AppLayout>
    );
  }

  const handleExportPDF = () => {
    generateClaimPDFReport(claim.claimNumber || claim.id);
  };

  const readinessBreakdown = claimData?.readinessBreakdown || (claim as any).readinessBreakdown;
  const fieldValidationTable = claimData?.fieldValidationTable || (claim as any).fieldValidationTable || [];
  const pipelineStages = claimData?.pipelineStages || (claim as any).pipelineStages || [];
  const historyRecords = claimData?.history || (claim as any).history || [];
  const documents = claim.documents || [];
  const selectedDoc = documents[selectedDocIndex] || documents[0];

  return (
    <AppLayout
      title={`Claim ${claim.claimNumber || claim.id}`}
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Claims", href: "/claims" },
        { label: claim.claimNumber || claim.id },
      ]}
    >
      <div className="space-y-6">
        
        {/* ========================================================================= */}
        {/* SECTION 4: CLAIM OVERVIEW HEADER CARD */}
        {/* ========================================================================= */}
        <div className="flex flex-col justify-between gap-6 rounded-2xl border border-border bg-card p-6 shadow-sm lg:flex-row lg:items-center">
          
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm font-bold text-primary uppercase tracking-wider">
                {claim.claimNumber || claim.id}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-mono font-semibold ${
                  claim.status === "Approved"
                    ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
                    : claim.status === "Rejected"
                    ? "border border-rose-500/30 bg-rose-500/10 text-rose-500"
                    : "border border-amber-500/30 bg-amber-500/10 text-amber-500"
                }`}
              >
                {claim.status}
              </span>
              <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 font-mono text-[10px] text-primary">
                Route: {claim.routeDecision}
              </span>
              <span className="rounded-full border border-border bg-secondary px-2.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                Neon DB Synced
              </span>
            </div>

            <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
              {claim.patientName}{" "}
              <span className="text-base font-normal text-muted-foreground">
                ({claim.patientAge ? `${claim.patientAge} yrs` : "Age Unspecified"})
              </span>
            </h1>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-semibold text-primary">
                <Building2 className="size-4" /> {claim.hospital || "Hospital Unspecified"}
              </span>
              <span>·</span>
              <span className="flex items-center gap-1.5">
                <Calendar className="size-4 text-muted-foreground" />
                Adm: <strong className="text-foreground font-mono">{formatDate(claim.admissionDate)}</strong> — Disch:{" "}
                <strong className="text-foreground font-mono">{formatDate(claim.dischargeDate)}</strong>
              </span>
              <span>·</span>
              <span>
                Policy: <strong className="text-foreground font-mono">{claim.policyNumber}</strong> ({claim.insuranceProvider})
              </span>
              {claim.createdAt && (
                <>
                  <span>·</span>
                  <span>Intake: <strong className="text-foreground font-mono">{formatDate(claim.createdAt)}</strong></span>
                </>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Amount Pill */}
            <div className="rounded-xl border border-border bg-secondary px-4 py-3 text-right">
              <span className="text-[10px] font-mono text-muted-foreground uppercase">Claimed Amount</span>
              <p className="text-xl font-extrabold font-mono text-emerald-500">{formatINR(claim.claimedAmount)}</p>
            </div>

            {/* Overall Readiness Pill */}
            <div className="rounded-xl border border-primary/40 bg-primary/10 px-4 py-3 text-right shadow-sm">
              <span className="text-[10px] font-mono text-primary uppercase">Readiness Score</span>
              <p className="text-xl font-extrabold font-mono text-foreground">
                {claim.readiness !== null && claim.readiness !== undefined ? `${claim.readiness}%` : "—"}
              </p>
            </div>

            {/* Export Report */}
            <button
              type="button"
              onClick={handleExportPDF}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 text-xs font-semibold text-foreground transition hover:border-primary hover:bg-secondary"
            >
              <Download className="size-4 text-primary" />
              Export Dossier
            </button>
          </div>

        </div>

        {/* ========================================================================= */}
        {/* SECTION 5: 13-STAGE PIPELINE VISUALIZATION */}
        {/* ========================================================================= */}
        <PipelineStageBar currentStage={claim.stage} />

        {/* ========================================================================= */}
        {/* WORKSPACE NAVIGATION TABS */}
        {/* ========================================================================= */}
        <div className="flex border-b border-border space-x-1 overflow-x-auto scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveTab("readiness")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "readiness"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Zap className="size-4" /> Readiness Score & Breakdown
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("validation")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "validation"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileCheck2 className="size-4" /> Field Validation & Cross-Recon ({fieldValidationTable.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("documents")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "documents"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileText className="size-4" /> Document Inventory & OCR ({documents.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("medical_policy")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "medical_policy"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Stethoscope className="size-4" /> Clinical & Policy Intelligence
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "history"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <History className="size-4" /> Audit Trail & History ({historyRecords.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("triage")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition whitespace-nowrap ${
              activeTab === "triage"
                ? "border-amber-500 text-amber-500"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <UserCheck className="size-4" /> Triage & Adjudication
          </button>
        </div>

        {/* ========================================================================= */}
        {/* TAB CONTENT PANELS */}
        {/* ========================================================================= */}
        <div className="space-y-6">
          
          {/* TAB 1: READINESS BREAKDOWN */}
          {activeTab === "readiness" && (
            <div className="space-y-6">
              {/* Readiness Gauge & Summary */}
              <ReadinessGauge
                score={claim.readiness || 0}
                validationScore={claim.validationReadiness || claim.readiness || 0}
                medicalScore={claim.medicalConfidence || 0}
                policyScore={claim.policyConfidence || 0}
                ocrScore={claim.ocrConfidence || 0}
              />

              {/* Exact Component Weight Contribution Breakdown (35/25/25/15) */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-foreground">Scoring Component Weight Contributions</h3>
                    <p className="text-xs text-muted-foreground">
                      Authoritative ClaimBridge Readiness Aggregation Formula: Validation (35%), Medical (25%), Policy (25%), OCR (15%).
                    </p>
                  </div>
                  <span className="font-mono text-xs font-bold text-primary">
                    Total: {claim.readiness || 0}%
                  </span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    {
                      label: "Validation Engine",
                      weight: "35%",
                      score: claim.validationReadiness || claim.readiness || 0,
                      contrib: ((claim.validationReadiness || claim.readiness || 0) * 0.35).toFixed(2),
                      color: "text-blue-500 bg-blue-500/10 border-blue-500/30",
                    },
                    {
                      label: "Medical Intelligence",
                      weight: "25%",
                      score: claim.medicalConfidence || 0,
                      contrib: ((claim.medicalConfidence || 0) * 0.25).toFixed(2),
                      color: "text-purple-500 bg-purple-500/10 border-purple-500/30",
                    },
                    {
                      label: "Policy Intelligence (RAG)",
                      weight: "25%",
                      score: claim.policyConfidence || 0,
                      contrib: ((claim.policyConfidence || 0) * 0.25).toFixed(2),
                      color: "text-amber-500 bg-amber-500/10 border-amber-500/30",
                    },
                    {
                      label: "OCR & Document AI",
                      weight: "15%",
                      score: claim.ocrConfidence || 0,
                      contrib: ((claim.ocrConfidence || 0) * 0.15).toFixed(2),
                      color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30",
                    },
                  ].map((comp) => (
                    <div key={comp.label} className="rounded-xl border border-border bg-secondary/50 p-4 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-foreground">{comp.label}</span>
                        <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] border ${comp.color}`}>
                          Weight {comp.weight}
                        </span>
                      </div>
                      <div className="flex items-baseline justify-between font-mono">
                        <span className="text-xl font-extrabold text-foreground">{comp.score}%</span>
                        <span className="text-xs text-muted-foreground">+{comp.contrib}% pts</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary"
                          style={{ width: `${Math.min(comp.score, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {readinessBreakdown?.explanation && (
                  <p className="text-xs text-muted-foreground bg-secondary/40 p-3 rounded-xl border border-border">
                    {readinessBreakdown.explanation}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: FIELD-LEVEL VALIDATION TABLE */}
          {activeTab === "validation" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h3 className="text-sm font-bold text-foreground">Field-Level Validation & Cross-Reconciliation</h3>
                  <p className="text-xs text-muted-foreground">
                    Granular extraction audits across uploaded bills, discharge cards, identity proofs, and policy schedules.
                  </p>
                </div>
                <span className="font-mono text-xs text-primary">{fieldValidationTable.length} Rules Evaluated</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/50 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Field Name</th>
                      <th className="px-4 py-3">Extracted Value</th>
                      <th className="px-4 py-3">Source Document</th>
                      <th className="px-4 py-3">Validation Rule</th>
                      <th className="px-4 py-3">Result</th>
                      <th className="px-4 py-3">Audit Explanation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {fieldValidationTable.map((row: any, i: number) => {
                      const isAccepted = row.result === "Accepted";
                      const isMismatch = row.result === "Mismatch" || row.result === "Rejected";
                      return (
                        <tr key={i} className="hover:bg-secondary/30 transition">
                          <td className="px-4 py-3.5 font-semibold text-foreground">{row.field}</td>
                          <td className="px-4 py-3.5 font-mono text-foreground">{String(row.extractedValue)}</td>
                          <td className="px-4 py-3.5 text-muted-foreground">{row.sourceDocument} (p.{row.page || 1})</td>
                          <td className="px-4 py-3.5 text-muted-foreground">{row.validationRule}</td>
                          <td className="px-4 py-3.5">
                            <span
                              className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold ${
                                isAccepted
                                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
                                  : isMismatch
                                  ? "bg-rose-500/10 text-rose-500 border border-rose-500/30"
                                  : "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                              }`}
                            >
                              {row.result}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-muted-foreground max-w-xs">{row.explanation}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: DOCUMENT INVENTORY & OCR VIEWER */}
          {activeTab === "documents" && (
            <div className="space-y-6">
              {/* Documents List Strip */}
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {documents.map((doc, idx) => (
                  <button
                    key={doc.id || idx}
                    type="button"
                    onClick={() => setSelectedDocIndex(idx)}
                    className={`rounded-xl border p-4 text-left transition shadow-sm ${
                      selectedDocIndex === idx
                        ? "border-primary bg-primary/10 ring-1 ring-primary"
                        : "border-border bg-card hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <FileText className="size-4 text-primary" />
                      <span className="font-mono text-[10px] text-emerald-500">{doc.status}</span>
                    </div>
                    <p className="mt-2 text-xs font-bold text-foreground truncate">{doc.category}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{doc.fileName}</p>
                    {doc.ocrConfidence && (
                      <p className="mt-2 font-mono text-[10px] text-primary">OCR: {doc.ocrConfidence}%</p>
                    )}
                  </button>
                ))}
              </div>

              {/* Selected Document OCR Detail */}
              {selectedDoc && (
                <OcrViewer
                  confidence={selectedDoc.ocrConfidence || claim.ocrConfidence}
                  lines={claim.ocrLines}
                  fileName={selectedDoc.fileName}
                  documentCategory={selectedDoc.category}
                />
              )}
            </div>
          )}

          {/* TAB 4: CLINICAL & POLICY EVIDENCE */}
          {activeTab === "medical_policy" && (
            <div className="space-y-6">
              <MedicalIntelligence
                diagnosis={claim.diagnosis}
                medicalRiskScore={claim.medicalRiskScore}
                medicalConfidence={claim.medicalConfidence}
                services={claim.medicalServices}
              />

              <PolicyRagPanel
                confidence={claim.policyConfidence}
                clauses={claim.policyClauses}
                policyNumber={claim.policyNumber}
                insuranceProvider={claim.insuranceProvider}
              />
            </div>
          )}

          {/* TAB 5: AUDIT TRAIL & CLAIM HISTORY */}
          {activeTab === "history" && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h3 className="text-sm font-bold text-foreground">Immutable Claim Audit Trail</h3>
                  <p className="text-xs text-muted-foreground">
                    Persisted historical transitions and adjudicator actions committed to Neon PostgreSQL.
                  </p>
                </div>
                <span className="font-mono text-xs text-primary">{historyRecords.length} Events</span>
              </div>

              {historyRecords.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-8">No historical transitions recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-secondary/50 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border">
                      <tr>
                        <th className="px-4 py-3">Timestamp</th>
                        <th className="px-4 py-3">Action Performed</th>
                        <th className="px-4 py-3">Actor / Adjudicator</th>
                        <th className="px-4 py-3">Status Transition</th>
                        <th className="px-4 py-3">Remarks / Rationale</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {historyRecords.map((h: any, i: number) => (
                        <tr key={h.id || i} className="hover:bg-secondary/30 transition">
                          <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">
                            {formatDate(h.timestamp)}
                          </td>
                          <td className="px-4 py-3 font-semibold text-foreground">{h.action}</td>
                          <td className="px-4 py-3 text-primary">{h.performedBy || "System Engine"}</td>
                          <td className="px-4 py-3 font-mono text-[11px]">
                            <span className="text-muted-foreground">{h.previousStatus || "Start"}</span> →{" "}
                            <strong className="text-foreground">{h.newStatus}</strong>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground max-w-sm">{h.remarks || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: TRIAGE DESK */}
          {activeTab === "triage" && (
            <HumanReviewTriage claim={claim} onStatusUpdated={loadClaim} />
          )}

        </div>

      </div>
    </AppLayout>
  );
}