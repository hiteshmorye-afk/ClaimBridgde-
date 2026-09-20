import { createFileRoute, useNavigate, useParams, Link } from "@tanstack/react-router";
import React, { useState } from "react";
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
} from "lucide-react";

import { AppLayout } from "@/components/layout/AppLayout";
import { getClaim, formatDate, formatINR } from "@/lib/claims";
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
      { title: "Claim Verification Trail — ClaimBridge" },
      {
        name: "description",
        content:
          "Full 11-stage AI verification pipeline, OCR bounding viewer, RAG policy evidence and readiness triage.",
      },
    ],
  }),
  component: ClaimDetailPage,
});

type TabType = "ocr" | "medical" | "policy" | "readiness" | "triage";

function ClaimDetailPage() {
  const { claimId } = useParams({ from: "/claims/$claimId" });
  const navigate = useNavigate();

  const claim = getClaim(claimId) || getClaim("CLM-TEST-001");

  const [activeTab, setActiveTab] = useState<TabType>("triage");
  const [activeStageIdx, setActiveStageIdx] = useState(8); // Default Stage 09: Claim Readiness

  if (!claim) {
    return (
      <AppLayout title="Claim Not Found">
        <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center">
          <p className="text-sm text-[#9CA3AF]">Claim {claimId} was not found in active workspace.</p>

          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-xl bg-[#3B82F6] px-4 py-2 text-xs font-semibold text-white"
          >
            <ArrowLeft className="size-4" /> Return to Dashboard
          </Link>
        </div>
      </AppLayout>
    );
  }

  const handleExportPDF = () => {
    generateClaimPDFReport(claim.id);
  };

  return (
    <AppLayout
      title={`Claim ${claim.id}`}
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Claims", href: "/claims" },
        { label: claim.id },
      ]}
    >
      <div className="space-y-8">
        
        {/* ========================================================================= */}
        {/* CLAIM HEADER SUMMARY CARD */}
        {/* ========================================================================= */}
        <div className="flex flex-col justify-between gap-6 rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl lg:flex-row lg:items-center">
          
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-[#3B82F6] uppercase tracking-wider">
                {claim.id}
              </span>
              <span className="rounded-full border border-[#3B82F6]/30 bg-[#3B82F6]/10 px-2.5 py-0.5 font-mono text-[10px] text-[#3B82F6]">
                FastAPI Synced
              </span>
              <span className="rounded-full border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-2.5 py-0.5 font-mono text-[10px] text-[#F59E0B]">
                {claim.routeDecision}
              </span>
            </div>

            <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
              {claim.patientName} <span className="text-base font-normal text-[#9CA3AF]">({claim.patientAge} yrs)</span>
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-[#9CA3AF]">
              <span className="flex items-center gap-1.5 font-semibold text-[#06B6D4]">
                <Building2 className="size-4" /> {claim.hospital}
              </span>
              <span>·</span>
              <span className="flex items-center gap-1.5">
                <Calendar className="size-4 text-[#9CA3AF]" />
                Adm: <strong className="text-white font-mono">{formatDate(claim.admissionDate)}</strong> — Disch: <strong className="text-white font-mono">{formatDate(claim.dischargeDate)}</strong>
              </span>
              <span>·</span>
              <span>Policy #: <strong className="text-white font-mono">{claim.policyNumber}</strong></span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            
            {/* Amount Pill */}
            <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17] px-4 py-3 text-right">
              <span className="text-[10px] font-mono text-[#9CA3AF] uppercase">Total Claimed Charges</span>
              <p className="text-xl font-extrabold font-mono text-[#10B981]">{formatINR(claim.claimedAmount)}</p>
            </div>

            {/* Overall Score Pill */}
            <div className="rounded-xl border border-[#06B6D4]/40 bg-[#06B6D4]/10 px-4 py-3 text-right shadow-[0_0_15px_rgba(6,182,212,0.2)]">
              <span className="text-[10px] font-mono text-[#06B6D4] uppercase">Readiness Score</span>
              <p className="text-xl font-extrabold font-mono text-white">{claim.readiness}%</p>
            </div>

            {/* Export PDF Button */}
            <button
              type="button"
              onClick={handleExportPDF}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#1F2937] bg-[#0B0F17] px-4 text-xs font-semibold text-white transition hover:border-[#3B82F6] hover:bg-[#111827]"
            >
              <Download className="size-4 text-[#3B82F6]" />
              Export Report
            </button>

          </div>

        </div>

        {/* ========================================================================= */}
        {/* VISUAL 11-STAGE AI PIPELINE BAR */}
        {/* ========================================================================= */}
        <PipelineStageBar
          currentStage={claim.stage}
          activeStageIndex={activeStageIdx}
          onSelectStage={(idx) => setActiveStageIdx(idx)}
        />

        {/* ========================================================================= */}
        {/* INTERACTIVE WORKSPACE TABS */}
        {/* ========================================================================= */}
        <div className="flex border-b border-[#1F2937] space-x-2">
          
          <button
            type="button"
            onClick={() => setActiveTab("triage")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition ${
              activeTab === "triage"
                ? "border-[#F59E0B] text-[#F59E0B]"
                : "border-transparent text-[#9CA3AF] hover:text-white"
            }`}
          >
            <UserCheck className="size-4" /> Human Triage Desk
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("ocr")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition ${
              activeTab === "ocr"
                ? "border-[#06B6D4] text-[#06B6D4]"
                : "border-transparent text-[#9CA3AF] hover:text-white"
            }`}
          >
            <FileText className="size-4" /> OCR Bounding Viewer ({claim.ocrConfidence}%)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("medical")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition ${
              activeTab === "medical"
                ? "border-[#3B82F6] text-[#3B82F6]"
                : "border-transparent text-[#9CA3AF] hover:text-white"
            }`}
          >
            <Stethoscope className="size-4" /> Medical Intelligence
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("policy")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition ${
              activeTab === "policy"
                ? "border-[#8B5CF6] text-[#8B5CF6]"
                : "border-transparent text-[#9CA3AF] hover:text-white"
            }`}
          >
            <BookOpen className="size-4" /> RAG Policy Evidence ({claim.policyConfidence}%)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("readiness")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-bold transition ${
              activeTab === "readiness"
                ? "border-[#10B981] text-[#10B981]"
                : "border-transparent text-[#9CA3AF] hover:text-white"
            }`}
          >
            <Zap className="size-4" /> Readiness Gauge ({claim.readiness}%)
          </button>

        </div>

        {/* ========================================================================= */}
        {/* TAB WORKSPACE PANELS */}
        {/* ========================================================================= */}
        <div className="mt-6">
          {activeTab === "triage" && (
            <HumanReviewTriage claim={claim} />
          )}

          {activeTab === "ocr" && (
            <OcrViewer
              confidence={claim.ocrConfidence}
              lines={claim.ocrLines}
              fileName={claim.documents[0]?.fileName}
              documentCategory={claim.documents[0]?.category}
            />
          )}

          {activeTab === "medical" && (
            <MedicalIntelligence
              diagnosis={claim.diagnosis}
              medicalRiskScore={claim.medicalRiskScore}
              medicalConfidence={claim.medicalConfidence}
              services={claim.medicalServices}
            />
          )}

          {activeTab === "policy" && (
            <PolicyRagPanel
              confidence={claim.policyConfidence}
              clauses={claim.policyClauses}
              policyNumber={claim.policyNumber}
              insuranceProvider={claim.insuranceProvider}
            />
          )}

          {activeTab === "readiness" && (
            <ReadinessGauge
              score={claim.readiness}
              validationScore={claim.validationReadiness}
              medicalScore={claim.medicalConfidence}
              policyScore={claim.policyConfidence}
              ocrScore={claim.ocrConfidence}
            />
          )}
        </div>

      </div>
    </AppLayout>
  );
}