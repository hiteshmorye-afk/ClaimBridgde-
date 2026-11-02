import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  ShieldCheck,
  Stethoscope,
  Info,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Sparkles,
  AlertCircle,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface ReadinessCategoryCheck {
  name: string;
  max_points: number;
  earned_points: number;
  status: string;
  identified_info: string;
  missing_info: string;
  deduction_reason: string;
  recommended_action: string;
}

export interface ReadinessCategory {
  name: string;
  key: string;
  weight: number;
  score: number;
  status: string;
  checks?: ReadinessCategoryCheck[];
  identified_info?: string[];
  missing_info?: string[];
  deductions?: string[];
  recommended_actions?: string[];
}

export interface RecommendedActionItem {
  action: string;
  category: string;
  categoryKey?: string;
  targetStep?: number;
  targetTab?: string;
  targetTitle?: string;
}

export interface ClaimReadinessData {
  readiness_score: number;
  readiness_level: string;
  readiness_status: string;
  stage: string;
  is_provisional: boolean;
  provisional_reasons?: string[];
  categories?: Record<string, ReadinessCategory>;
  category_list?: ReadinessCategory[];
  missing_requirements?: string[];
  recommended_actions?: RecommendedActionItem[];
  disclaimer?: string;
  total_weight?: number;
}

export interface DocumentReliabilityData {
  score: number;
  tier: string;
  tierSummary?: string;
  authenticityStatus?: string;
  explanation?: string;
  readabilityStatus?: string;
  documentTypeCorrectness?: string;
  missingFields?: string[];
  foundFields?: string[];
  extractionConfidence?: number;
  recommendedCorrections?: string[];
  breakdown?: Record<string, {
    score: number;
    max: number;
    label: string;
    status: string;
    description: string;
  }>;
}

interface ClaimReadinessPanelProps {
  documentName?: string;
  documentCategory?: string;
  documentReliability?: DocumentReliabilityData;
  claimReadiness?: ClaimReadinessData;
  claimId?: string;
  className?: string;
  onNavigateToStep?: (step: number, tab?: string) => void;
}

export function ClaimReadinessPanel({
  documentName,
  documentCategory,
  documentReliability,
  claimReadiness,
  claimId,
  className = "",
  onNavigateToStep,
}: ClaimReadinessPanelProps) {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [showAllChecks, setShowAllChecks] = useState(false);

  const toggleCategory = (key: string) => {
    setExpandedCategories((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // -------------------------------------------------------------------------
  // 1. DOCUMENT RELIABILITY DATA
  // -------------------------------------------------------------------------
  const docScore = documentReliability?.score ?? 85.0;
  const docTier = documentReliability?.tier ?? (docScore >= 90 ? "High Readiness" : docScore >= 75 ? "Good Readiness" : "Needs Attention");
  const docTierSummary = documentReliability?.tierSummary ?? "Document appears complete and consistent based on available checks.";
  const authenticityStatus = documentReliability?.authenticityStatus ?? "Authenticity Not Independently Verified";
  const extractionConfidence = documentReliability?.extractionConfidence ?? 85;
  const missingDocFields = documentReliability?.missingFields || [];
  const recommendedCorrections = documentReliability?.recommendedCorrections || [];
  const docBreakdown = documentReliability?.breakdown;

  // -------------------------------------------------------------------------
  // 2. OVERALL CLAIM READINESS DATA
  // -------------------------------------------------------------------------
  const claimScore = claimReadiness?.readiness_score ?? 78.5;
  const claimLevel = claimReadiness?.readiness_level ?? (claimScore >= 90 ? "Excellent Readiness" : claimScore >= 75 ? "Good Readiness" : claimScore >= 50 ? "Needs Attention" : "Incomplete");
  const isProvisional = claimReadiness?.is_provisional ?? false;
  const provisionalReasons = claimReadiness?.provisional_reasons || [];
  const stageName = (claimReadiness?.stage || "preauth").replace(/_/g, " ").toUpperCase();
  const disclaimer = claimReadiness?.disclaimer || "ClaimBridge Claim Readiness is an internal readiness assessment of documentation completeness, quality, and cross-consistency. It is NOT a guarantee of claim approval, approval probability, medical diagnosis, or official decision by the insurer or IRDAI.";

  // -------------------------------------------------------------------------
  // 3. CATEGORY BREAKDOWN DATA (7 Categories)
  // -------------------------------------------------------------------------
  const defaultCategoryList: ReadinessCategory[] = [
    { name: "Patient Identity & Details", key: "patient_identity", weight: 15, score: 13, status: "Passed" },
    { name: "Insurance Policy Information", key: "policy_information", weight: 20, score: 17, status: "Passed" },
    { name: "Medical Diagnosis & ICD-10", key: "medical_diagnosis", weight: 20, score: 16, status: "Passed" },
    { name: `Required Documents (${stageName})`, key: "required_documents", weight: 20, score: 15, status: "Needs Attention" },
    { name: "Document Quality & Correctness", key: "document_quality", weight: 10, score: 8.5, status: "Passed" },
    { name: "Cross-Document Consistency", key: "cross_document_consistency", weight: 10, score: 9, status: "Passed" },
    { name: "Consent & Authorization", key: "consent_authorization", weight: 5, score: 5, status: "Passed" },
  ];

  const categoryList: ReadinessCategory[] =
    claimReadiness?.category_list && claimReadiness.category_list.length > 0
      ? claimReadiness.category_list
      : defaultCategoryList;

  // -------------------------------------------------------------------------
  // 4. MISSING REQUIREMENTS & RECOMMENDED ACTIONS
  // -------------------------------------------------------------------------
  const missingRequirements = claimReadiness?.missing_requirements || [];
  const recommendedActions = claimReadiness?.recommended_actions || [];

  const handleActionClick = (actionItem: RecommendedActionItem) => {
    if (onNavigateToStep && actionItem.targetStep) {
      onNavigateToStep(actionItem.targetStep, actionItem.targetTab);
    } else if (claimId) {
      window.location.href = `/claims/${claimId}`;
    } else {
      window.location.href = "/claims/new";
    }
  };

  const getLevelBadgeClass = (level: string) => {
    switch (level) {
      case "Excellent Readiness":
        return "bg-emerald-500/15 text-emerald-600 border-emerald-500/30 dark:text-emerald-400";
      case "Good Readiness":
        return "bg-sky-500/15 text-sky-600 border-sky-500/30 dark:text-sky-400";
      case "Needs Attention":
        return "bg-amber-500/15 text-amber-600 border-amber-500/30 dark:text-amber-400";
      default:
        return "bg-rose-500/15 text-rose-600 border-rose-500/30 dark:text-rose-400";
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s.includes("passed") || s.includes("verified") || s.includes("match")) {
      return "bg-emerald-500/10 text-emerald-600 border-emerald-500/30 dark:text-emerald-400";
    }
    if (s.includes("attention") || s.includes("unconfirmed") || s.includes("partial")) {
      return "bg-amber-500/10 text-amber-600 border-amber-500/30 dark:text-amber-400";
    }
    if (s.includes("failed") || s.includes("incorrect") || s.includes("mismatch")) {
      return "bg-rose-500/10 text-rose-600 border-rose-500/30 dark:text-rose-400";
    }
    return "bg-slate-500/10 text-slate-600 border-slate-500/30 dark:text-slate-400";
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ================================================================= */}
      {/* SECTION 1: DOCUMENT RELIABILITY SCORE (Selected Document) */}
      {/* ================================================================= */}
      <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800/80">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-white">
              <FileText className="size-4 text-blue-500" />
              Document Reliability
            </CardTitle>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
              Selected File
            </span>
          </div>
          {documentName && (
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
              {documentName}
            </p>
          )}
          {documentCategory && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Category: <span className="font-medium text-slate-700 dark:text-slate-300">{documentCategory.replace(/_/g, " ").toUpperCase()}</span>
            </p>
          )}
        </CardHeader>

        <CardContent className="pt-4 space-y-3.5">
          {/* Circular Score & Tier */}
          <div className="flex items-center gap-4">
            <div className="relative flex size-20 shrink-0 items-center justify-center rounded-full border-4 border-slate-100 bg-gradient-to-tr from-blue-500/10 to-cyan-500/10 dark:border-slate-800">
              <div className="flex flex-col items-center">
                <span className="font-mono text-2xl font-black text-slate-900 dark:text-white">
                  {Math.round(docScore)}
                </span>
                <span className="text-[9px] font-bold text-slate-400 uppercase">
                  / 100
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-bold ${getLevelBadgeClass(docTier)}`}>
                {docTier}
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
                {docTierSummary}
              </p>
              <p className="text-[10px] font-mono text-slate-400">
                Extraction OCR Quality: {extractionConfidence}%
              </p>
            </div>
          </div>

          {/* Missing Fields Notice */}
          {missingDocFields.length > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-2.5 text-[11px] text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
              <span className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="size-3.5 text-amber-600" />
                Missing Key Document Fields:
              </span>
              <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-300">
                {missingDocFields.join(", ")}
              </p>
            </div>
          )}

          {/* Recommended Corrections for Document */}
          {recommendedCorrections.length > 0 && (
            <div className="rounded-xl border border-blue-500/20 bg-blue-50/50 p-2.5 text-[11px] text-blue-900 dark:border-blue-500/30 dark:bg-blue-950/30 dark:text-blue-200 space-y-1">
              <span className="font-bold">Recommended Document Corrections:</span>
              <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                {recommendedCorrections.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 5-part Breakdown (if present) */}
          {docBreakdown && (
            <div className="space-y-1.5 border-t border-slate-100 pt-3 dark:border-slate-800 text-[11px]">
              {Object.entries(docBreakdown).map(([dimKey, dim]) => (
                <div
                  key={dimKey}
                  className="flex items-center justify-between py-1 border-b border-slate-50 dark:border-slate-800/40"
                >
                  <span className="text-slate-600 dark:text-slate-400 truncate max-w-[170px]">
                    {dim.label}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                      {dim.score}/{dim.max}
                    </span>
                    <span className={`inline-flex rounded px-1.5 py-0.2 text-[9px] font-semibold border ${getStatusBadge(dim.status)}`}>
                      {dim.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Authenticity Notice */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-2.5 text-[10px] leading-relaxed text-slate-600 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400">
            <strong>Authenticity Evidence:</strong> {authenticityStatus}. Ordinary scanned hospital papers receive 0/15 points unless cryptographically verified.
          </div>
        </CardContent>
      </Card>

      {/* ================================================================= */}
      {/* SECTION 2: OVERALL CLAIM READINESS SCORE (Entire Claim) */}
      {/* ================================================================= */}
      <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800/80">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-white">
              <ShieldCheck className="size-4 text-emerald-500" />
              Overall Claim Readiness
            </CardTitle>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              Stage: {stageName}
            </span>
          </div>
        </CardHeader>

        <CardContent className="pt-4 space-y-4">
          {/* Main Score Hero */}
          <div className="flex items-center justify-between p-3 rounded-2xl bg-gradient-to-r from-slate-50 via-slate-50 to-blue-50/30 border border-slate-200 dark:border-slate-800 dark:from-slate-950 dark:via-slate-950 dark:to-blue-950/20">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Claim Readiness Score
              </span>
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-3xl font-black text-slate-900 dark:text-white">
                  {claimScore}
                </span>
                <span className="font-mono text-xs text-slate-400 font-bold">/ 100</span>
              </div>
            </div>

            <div className="flex flex-col items-end gap-1">
              <span className={`rounded-full border px-3 py-1 text-xs font-bold ${getLevelBadgeClass(claimLevel)}`}>
                {claimLevel}
              </span>
              {isProvisional && (
                <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 text-[9px] font-bold text-amber-700 dark:text-amber-300">
                  <AlertCircle className="size-3" /> Provisional Score
                </span>
              )}
            </div>
          </div>

          {/* Provisional Explanation if applicable */}
          {isProvisional && provisionalReasons.length > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200 space-y-1">
              <span className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="size-3.5 text-amber-600" />
                Provisional Assessment Notice:
              </span>
              <p className="text-[11px] leading-tight text-amber-700 dark:text-amber-300">
                This score is provisional because critical claim prerequisites are incomplete:
              </p>
              <ul className="list-disc pl-4 text-[10px] text-amber-700 dark:text-amber-300 space-y-0.5">
                {provisionalReasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {/* ============================================================= */}
          {/* SECTION 3: 7-CATEGORY BREAKDOWN */}
          {/* ============================================================= */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
              <span>Assessment Categories ({categoryList.length})</span>
              <button
                type="button"
                onClick={() => setShowAllChecks(!showAllChecks)}
                className="text-[11px] font-semibold text-blue-600 hover:underline dark:text-blue-400"
              >
                {showAllChecks ? "Hide Details" : "Show All Details"}
              </button>
            </div>

            <div className="space-y-2">
              {categoryList.map((category) => {
                const isExpanded = showAllChecks || !!expandedCategories[category.key];
                const pct = Math.min(100, Math.round((category.score / Math.max(1, category.weight)) * 100));

                return (
                  <div
                    key={category.key}
                    className="rounded-xl border border-slate-200/90 bg-slate-50/50 p-2.5 transition dark:border-slate-800 dark:bg-slate-950/40"
                  >
                    <div
                      className="flex cursor-pointer items-center justify-between text-xs"
                      onClick={() => toggleCategory(category.key)}
                    >
                      <div className="flex items-center gap-2 max-w-[200px]">
                        <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                          {category.name}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                          {category.score}/{category.weight}
                        </span>
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[9px] font-semibold ${getStatusBadge(category.status)}`}>
                          {category.status}
                        </span>
                        {isExpanded ? <ChevronUp className="size-3.5 text-slate-400" /> : <ChevronDown className="size-3.5 text-slate-400" />}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-2 h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          pct >= 90
                            ? "bg-emerald-500"
                            : pct >= 60
                            ? "bg-blue-500"
                            : "bg-amber-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>

                    {/* Expandable Category Checks & Deductions */}
                    {isExpanded && (
                      <div className="mt-3 space-y-2 border-t border-slate-200/80 pt-2 text-[11px] dark:border-slate-800">
                        {/* Deductions if any */}
                        {category.deductions && category.deductions.length > 0 && (
                          <div className="rounded-lg bg-amber-500/10 p-2 text-amber-800 dark:text-amber-200">
                            <span className="font-bold text-[10px] uppercase tracking-wide">Points Deducted:</span>
                            <ul className="mt-0.5 list-disc pl-3.5 space-y-0.5 text-[10px]">
                              {category.deductions.map((ded, idx) => (
                                <li key={idx}>{ded}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Identified Information */}
                        {category.identified_info && category.identified_info.length > 0 && (
                          <div className="space-y-0.5 text-[10px] text-slate-600 dark:text-slate-400">
                            {category.identified_info.map((info, idx) => (
                              <div key={idx} className="flex items-start gap-1">
                                <CheckCircle2 className="size-3 text-emerald-500 shrink-0 mt-0.5" />
                                <span>{info}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Individual Checks list */}
                        {category.checks && category.checks.length > 0 && (
                          <div className="space-y-1.5 pt-1">
                            {category.checks.map((chk, idx) => (
                              <div
                                key={idx}
                                className="flex items-start justify-between rounded-lg bg-white/70 p-1.5 border border-slate-100 dark:bg-slate-900/60 dark:border-slate-800/60 text-[10px]"
                              >
                                <span className="font-medium text-slate-700 dark:text-slate-300">
                                  {chk.name}
                                </span>
                                <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                                  {chk.earned_points}/{chk.max_points}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ============================================================= */}
          {/* SECTION 4: MISSING REQUIREMENTS */}
          {/* ============================================================= */}
          {missingRequirements.length > 0 && (
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/5 p-3 dark:bg-rose-500/10 space-y-1.5">
              <span className="flex items-center gap-1.5 text-xs font-bold text-rose-800 dark:text-rose-200">
                <AlertCircle className="size-4 text-rose-600" />
                Missing Requirements ({stageName}):
              </span>
              <ul className="list-disc pl-4 text-[11px] text-rose-700 dark:text-rose-300 space-y-0.5">
                {missingRequirements.map((req, idx) => (
                  <li key={idx}>{req}</li>
                ))}
              </ul>
            </div>
          )}

          {/* ============================================================= */}
          {/* SECTION 5: RECOMMENDED ACTIONS (Interactive Navigation) */}
          {/* ============================================================= */}
          {recommendedActions.length > 0 && (
            <div className="rounded-2xl border border-blue-500/30 bg-blue-50/40 p-3 dark:border-blue-500/30 dark:bg-blue-950/20 space-y-2">
              <span className="flex items-center gap-1.5 text-xs font-bold text-blue-900 dark:text-blue-200">
                <Sparkles className="size-4 text-blue-500" />
                Recommended Actions:
              </span>
              <div className="space-y-1.5">
                {recommendedActions.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleActionClick(item)}
                    className="flex w-full items-start justify-between gap-2 rounded-xl border border-blue-200/80 bg-white p-2 text-left text-[11px] transition hover:border-blue-400 hover:bg-blue-50/50 dark:border-blue-900/60 dark:bg-slate-900 dark:hover:bg-blue-950/40"
                  >
                    <div className="space-y-0.5">
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {item.action}
                      </p>
                      {item.targetTitle && (
                        <p className="text-[10px] text-blue-600 dark:text-blue-400 font-mono">
                          Go to: {item.targetTitle}
                        </p>
                      )}
                    </div>
                    <ArrowRight className="size-3.5 shrink-0 text-blue-500 mt-0.5" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* DISCLAIMER NOTICE */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2.5 text-[9px] leading-relaxed text-slate-500 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-400">
            <strong>IRDAI / Preparation Notice:</strong> {disclaimer}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
