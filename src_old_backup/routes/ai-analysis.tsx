import { createFileRoute } from "@tanstack/react-router";
import React from "react";
import {
  BrainCircuit,
  Stethoscope,
  BookOpen,
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { MedicalIntelligence } from "@/components/pipeline/MedicalIntelligence";
import { PolicyRagPanel } from "@/components/pipeline/PolicyRagPanel";
import { ReadinessGauge } from "@/components/pipeline/ReadinessGauge";
import { getClaim } from "@/lib/claims";

export const Route = createFileRoute("/ai-analysis")({
  head: () => ({
    meta: [
      { title: "AI Analysis Core — ClaimBridge" },
      {
        name: "description",
        content: "Deep tech AI medical intelligence, ICD-10 coding and RAG policy verification engine.",
      },
    ],
  }),
  component: AiAnalysisPage,
});

function AiAnalysisPage() {
  const sampleClaim = getClaim("CLM-TEST-001") || {
    id: "CLM-TEST-001",
    diagnosis: "Acute Gastroenteritis & Severe Dehydration (ICD-10: A09)",
    medicalRiskScore: 50,
    medicalConfidence: 70,
    policyConfidence: 68.51,
    readiness: 89.47,
    ocrConfidence: 98.93,
    validationReadiness: 100,
    medicalServices: [],
    policyClauses: [],
  };

  return (
    <AppLayout
      title="Autonomous AI Analysis Engine"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Analysis" }]}
    >
      <div className="space-y-8">
        
        {/* HEADER HERO BANNER */}
        <div className="flex flex-col justify-between gap-6 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-6 shadow-xl lg:flex-row lg:items-center">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="flex size-2 rounded-full bg-[#8B5CF6] animate-ping" />
              <span className="font-mono text-xs font-semibold text-[#8B5CF6] uppercase tracking-wider">
                ClaimBridge Core Intelligence
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white sm:text-3xl">
              Medical & Policy Intelligence Hub
            </h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Automated entity extraction, CPT/ICD-10 mapping & RAG policy clause matching.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 px-4 py-3 text-right">
              <span className="text-[10px] font-mono text-purple-600 dark:text-[#8B5CF6] uppercase">RAG Vector Accuracy</span>
              <p className="text-2xl font-extrabold font-mono text-slate-900 dark:text-white">96.8%</p>
            </div>
          </div>
        </div>

        {/* MEDICAL INTELLIGENCE PANEL */}
        <MedicalIntelligence
          diagnosis={sampleClaim.diagnosis}
          medicalRiskScore={sampleClaim.medicalRiskScore}
          medicalConfidence={sampleClaim.medicalConfidence}
          services={sampleClaim.medicalServices}
        />

        {/* RAG POLICY PANEL */}
        <PolicyRagPanel
          confidence={sampleClaim.policyConfidence}
          clauses={sampleClaim.policyClauses}
        />

        {/* READINESS GAUGE */}
        <ReadinessGauge
          score={sampleClaim.readiness}
          validationScore={sampleClaim.validationReadiness}
          medicalScore={sampleClaim.medicalConfidence}
          policyScore={sampleClaim.policyConfidence}
          ocrScore={sampleClaim.ocrConfidence}
        />

      </div>
    </AppLayout>
  );
}
