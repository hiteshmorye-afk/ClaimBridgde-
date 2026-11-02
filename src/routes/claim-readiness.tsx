import React, { useEffect, useState, useCallback, useMemo } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import {
  ShieldCheck,
  ClipboardCheck,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  ArrowRight,
  ArrowLeft,
  ExternalLink,
  Sparkles,
  FileText,
  User,
  Building2,
  Calendar,
  CreditCard,
  FileSpreadsheet,
  Filter,
  ArrowUpDown,
  Activity,
  Layers,
  Clock,
  Check,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchClaimReadinessDashboard,
  fetchClaimById,
  type ClaimReadinessDashboardResponse,
  type ClaimReadinessDashboardItem,
  type ClaimReadinessDashboardSummary,
  type ClaimApiData,
} from "@/api/claims";
import { getCurrentUser } from "@/api/auth";
import { toast } from "sonner";

export const Route = createFileRoute("/claim-readiness")({
  validateSearch: (search: Record<string, unknown>) => ({
    claimId: typeof search.claimId === "string" ? search.claimId : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Overall Claim Readiness Dashboard — ClaimBridge" },
      {
        name: "description",
        content:
          "Automatic claim readiness dashboard evaluating 7 deterministic categories across all accessible claims.",
      },
    ],
  }),
  component: ClaimReadinessPage,
});

export function ClaimReadinessPage() {
  const { claimId: searchClaimId } = Route.useSearch();
  const navigate = useNavigate();

  // Authentication state
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Dashboard state (Overview mode)
  const [dashboardData, setDashboardData] = useState<ClaimReadinessDashboardResponse | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState<boolean>(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedLevelFilter, setSelectedLevelFilter] = useState<string>("all");
  const [selectedStageFilter, setSelectedStageFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"score_asc" | "score_desc" | "date_desc" | "patient_asc">("score_asc");

  // Single Claim Detail state (Detailed Inspection mode)
  const [selectedClaimId, setSelectedClaimId] = useState<string>(searchClaimId || "");
  const [claimData, setClaimData] = useState<ClaimApiData | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

  // Sync state with URL search params
  useEffect(() => {
    setSelectedClaimId(searchClaimId || "");
  }, [searchClaimId]);

  // Auth verification
  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      navigate({ to: "/auth" });
      return;
    }
    setCurrentUser(user);
  }, [navigate]);

  // Load Dashboard Data automatically on page load
  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    setDashboardError(null);
    try {
      const data = await fetchClaimReadinessDashboard({
        search: searchTerm,
        status: "all",
        stage: selectedStageFilter,
        level: selectedLevelFilter,
        sortBy: sortBy,
      });
      setDashboardData(data);
    } catch (err: any) {
      console.error("Failed to load claim readiness dashboard:", err);
      setDashboardError(err?.message || "Unable to fetch overall claim readiness assessments.");
      toast.error("Unable to load claim readiness dashboard.");
    } finally {
      setLoadingDashboard(false);
    }
  }, [searchTerm, selectedStageFilter, selectedLevelFilter, sortBy]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Load detailed single claim assessment when selectedClaimId is set
  const loadSingleClaimDetail = useCallback(async (id: string) => {
    if (!id) {
      setClaimData(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const data = await fetchClaimById(id);
      setClaimData(data);
    } catch (err: any) {
      console.error(`Failed to load detailed assessment for claim ${id}:`, err);
      toast.error(err?.message || "Unable to load claim details.");
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (selectedClaimId) {
      loadSingleClaimDetail(selectedClaimId);
    } else {
      setClaimData(null);
    }
  }, [selectedClaimId, loadSingleClaimDetail]);

  // Navigation handlers
  const handleViewClaimDetails = (id: string) => {
    setSelectedClaimId(id);
    navigate({
      search: (prev: any) => ({ ...prev, claimId: id }),
    });
  };

  const handleBackToDashboard = () => {
    setSelectedClaimId("");
    setClaimData(null);
    navigate({
      search: (prev: any) => ({ ...prev, claimId: undefined }),
    });
  };

  const toggleCategory = (key: string) => {
    setExpandedCategories((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Helper styles for readiness levels
  const getLevelBadge = (level: string) => {
    switch (level) {
      case "Excellent Readiness":
      case "Excellent":
        return {
          bg: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30 dark:text-emerald-400",
          barBg: "bg-emerald-500",
          label: "Excellent Readiness",
        };
      case "Good Readiness":
      case "Good":
        return {
          bg: "bg-sky-500/10 text-sky-600 border-sky-500/30 dark:text-sky-400",
          barBg: "bg-sky-500",
          label: "Good Readiness",
        };
      case "Needs Attention":
        return {
          bg: "bg-amber-500/10 text-amber-600 border-amber-500/30 dark:text-amber-400",
          barBg: "bg-amber-500",
          label: "Needs Attention",
        };
      default:
        return {
          bg: "bg-rose-500/10 text-rose-600 border-rose-500/30 dark:text-rose-400",
          barBg: "bg-rose-500",
          label: "Incomplete",
        };
    }
  };

  const formatStageLabel = (stage: string) => {
    const s = (stage || "").toLowerCase();
    if (s.includes("preauth") || s.includes("pre-auth") || s.includes("cashless")) {
      return "Pre-Authorization";
    }
    if (s.includes("final") || s.includes("discharge")) {
      return "Final Authorization";
    }
    if (s.includes("reimburse")) {
      return "Reimbursement";
    }
    return stage || "Pre-Authorization";
  };

  // Detailed Claim Assessment computed data
  const readinessDetail = useMemo(() => {
    if (!claimData) return null;
    const rawReadiness = (claimData as any)?.claimReadiness || (claimData as any)?.readinessBreakdown || {};
    const score = Number(rawReadiness.readiness_score ?? rawReadiness.readinessScore ?? claimData?.readiness ?? 0);
    const level = rawReadiness.readiness_level ?? rawReadiness.readinessLevel ?? (
      score >= 90 ? "Excellent Readiness" : score >= 75 ? "Good Readiness" : score >= 50 ? "Needs Attention" : "Incomplete"
    );
    const isProvisional = Boolean(rawReadiness.is_provisional ?? rawReadiness.isProvisional ?? false);
    const provisionalReasons: string[] = rawReadiness.provisional_reasons || rawReadiness.provisionalReasons || [];
    const stage = (rawReadiness.stage || claimData?.claimType || claimData?.stage || "preauth").replace(/_/g, " ").toUpperCase();
    const missingRequirements: string[] = rawReadiness.missing_requirements || rawReadiness.missingRequirements || rawReadiness.blockers || [];
    const recommendedActions: string[] = rawReadiness.recommended_actions || rawReadiness.recommendedActions || [];
    const disclaimer = rawReadiness.disclaimer || "ClaimBridge Claim Readiness is an internal readiness assessment of documentation completeness, quality, and cross-consistency. It is NOT a guarantee of claim approval, approval probability, medical diagnosis, or official decision by the insurer or IRDAI.";

    // 7 categories
    let categoryList: any[] = rawReadiness.category_list || rawReadiness.categoryList || [];
    if (!categoryList || categoryList.length === 0) {
      if (rawReadiness.categories) {
        categoryList = Object.values(rawReadiness.categories);
      } else if (rawReadiness.components) {
        categoryList = Object.entries(rawReadiness.components).map(([k, comp]: [string, any]) => ({
          key: k,
          name: comp.name || comp.label || k.replace(/_/g, " ").toUpperCase(),
          weight: comp.weight || 20,
          score: comp.score || 0,
          status: comp.status || (comp.score >= comp.weight ? "Passed" : "Needs Attention"),
          checks: comp.checks || [],
          deductions: comp.deductions || [],
          identified_info: comp.identified_info || [],
          recommended_actions: comp.recommendedActions || comp.recommended_actions || [],
        }));
      }
    }

    return {
      score,
      level,
      isProvisional,
      provisionalReasons,
      stage,
      missingRequirements,
      recommendedActions,
      disclaimer,
      categoryList,
    };
  }, [claimData]);

  // Client-side quick filter on claims list if user searches or filters
  const displayedClaims = useMemo(() => {
    if (!dashboardData) return [];
    let items = [...dashboardData.claims];

    // Client-side search fallback
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      items = items.filter((c) =>
        c.claimNumber.toLowerCase().includes(q) ||
        c.patientName.toLowerCase().includes(q) ||
        c.hospital.toLowerCase().includes(q) ||
        c.policyNumber.toLowerCase().includes(q)
      );
    }

    // Client-side level fallback
    if (selectedLevelFilter !== "all") {
      items = items.filter((c) => {
        const lvl = c.readinessLevel.toLowerCase();
        if (selectedLevelFilter === "excellent") return lvl.includes("excellent");
        if (selectedLevelFilter === "good") return lvl.includes("good");
        if (selectedLevelFilter === "needs_attention") return lvl.includes("attention");
        if (selectedLevelFilter === "incomplete") return lvl.includes("incomplete");
        return true;
      });
    }

    // Client-side stage fallback
    if (selectedStageFilter !== "all") {
      items = items.filter((c) => {
        const stg = c.claimStage.toLowerCase();
        if (selectedStageFilter === "preauth") return stg.includes("pre") || stg.includes("cashless");
        if (selectedStageFilter === "final_auth") return stg.includes("final") || stg.includes("discharge");
        if (selectedStageFilter === "reimbursement") return stg.includes("reimburse");
        return true;
      });
    }

    return items;
  }, [dashboardData, searchTerm, selectedLevelFilter, selectedStageFilter]);

  // Summary Metrics
  const summary: ClaimReadinessDashboardSummary = useMemo(() => {
    if (dashboardData?.summary) return dashboardData.summary;
    const total = displayedClaims.length;
    const exc = displayedClaims.filter((c) => c.readinessScore >= 90).length;
    const good = displayedClaims.filter((c) => c.readinessScore >= 75 && c.readinessScore < 90).length;
    const att = displayedClaims.filter((c) => c.readinessScore >= 50 && c.readinessScore < 75).length;
    const inc = displayedClaims.filter((c) => c.readinessScore < 50).length;
    const avg = total > 0 ? displayedClaims.reduce((acc, c) => acc + c.readinessScore, 0) / total : 0;
    return {
      totalAssessed: total,
      excellentClaims: exc,
      goodClaims: good,
      needsAttentionClaims: att,
      incompleteClaims: inc,
      averageScore: Math.round(avg * 10) / 10,
    };
  }, [dashboardData, displayedClaims]);

  return (
    <AppLayout
      title={selectedClaimId ? "Claim Readiness Assessment Details" : "Overall Claim Readiness Dashboard"}
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Claim Readiness", href: "/claim-readiness" },
        ...(selectedClaimId && claimData
          ? [{ label: claimData.claimNumber || selectedClaimId, href: `/claim-readiness?claimId=${selectedClaimId}` }]
          : []),
      ]}
    >
      <div className="space-y-6">
        {/* ========================================================================= */}
        {/* VIEW MODE 1: INDIVIDUAL CLAIM DETAILED INSPECTION */}
        {/* ========================================================================= */}
        {selectedClaimId ? (
          <div className="space-y-6">
            {/* Detailed View Navigation Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleBackToDashboard}
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-secondary/60 px-3 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary"
                >
                  <ArrowLeft className="size-4 text-muted-foreground" />
                  <span>Back to Claims Dashboard</span>
                </button>
                <div className="hidden h-5 w-px bg-border sm:block" />
                <div className="hidden sm:block">
                  <h2 className="text-sm font-bold text-foreground">
                    Detailed 7-Category Evaluation
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    Showing deterministic readiness checks and recommendations for claim #{claimData?.claimNumber || selectedClaimId}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => loadSingleClaimDetail(selectedClaimId)}
                  disabled={loadingDetail}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary disabled:opacity-50"
                >
                  <RefreshCw className={`size-3.5 text-primary ${loadingDetail ? "animate-spin" : ""}`} />
                  <span>Re-Evaluate</span>
                </button>

                <Link
                  to={`/claims/${selectedClaimId}` as any}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-white transition hover:bg-primary/90"
                >
                  <span>Open Full Claim Dossier</span>
                  <ExternalLink className="size-3.5" />
                </Link>
              </div>
            </div>

            {loadingDetail ? (
              <Card className="border-border bg-card p-12 text-center shadow-sm">
                <RefreshCw className="mx-auto size-8 animate-spin text-primary" />
                <p className="mt-3 text-sm font-semibold text-foreground">
                  Evaluating claim documentation evidence...
                </p>
                <p className="text-xs text-muted-foreground">
                  Running deterministic checks across all 7 assessment categories.
                </p>
              </Card>
            ) : !claimData || !readinessDetail ? (
              <Card className="border-border bg-card p-12 text-center shadow-sm">
                <AlertCircle className="mx-auto size-10 text-rose-500" />
                <h3 className="mt-4 text-base font-bold text-foreground">Claim Assessment Not Found</h3>
                <p className="mt-1 text-xs text-muted-foreground max-w-md mx-auto">
                  Unable to load the readiness assessment for claim reference {selectedClaimId}. It may have been archived or outside your authorized organization.
                </p>
                <button
                  type="button"
                  onClick={handleBackToDashboard}
                  className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white"
                >
                  Return to Dashboard
                </button>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Active Claim Metadata Banner */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-2xl border border-border bg-card p-4 shadow-sm text-xs">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Patient Name
                    </span>
                    <p className="font-semibold text-foreground flex items-center gap-1.5 truncate">
                      <User className="size-3.5 text-primary shrink-0" />
                      {claimData.patientName}
                    </p>
                  </div>

                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Claim Reference
                    </span>
                    <p className="font-mono font-semibold text-foreground truncate">
                      {claimData.claimNumber}
                    </p>
                  </div>

                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Treating Hospital
                    </span>
                    <p className="font-semibold text-foreground flex items-center gap-1.5 truncate">
                      <Building2 className="size-3.5 text-primary shrink-0" />
                      {claimData.hospital}
                    </p>
                  </div>

                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Evaluation Stage
                    </span>
                    <p className="font-semibold text-foreground">
                      <span className="inline-flex rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-mono text-primary">
                        {readinessDetail.stage}
                      </span>
                    </p>
                  </div>
                </div>

                {/* Overall Score Hero Card */}
                <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm">
                  <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-5">
                      {/* Score Gauge */}
                      <div className="relative flex size-28 shrink-0 items-center justify-center rounded-2xl border border-border bg-secondary/40 shadow-inner">
                        <div className="text-center">
                          <span className="font-mono text-3xl font-black text-foreground">
                            {Math.round(readinessDetail.score)}
                          </span>
                          <span className="text-xs font-semibold text-muted-foreground">/100</span>
                          <div className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-primary">
                            Points
                          </div>
                        </div>
                      </div>

                      {/* Score Information */}
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${
                              getLevelBadge(readinessDetail.level).bg
                            }`}
                          >
                            <ShieldCheck className="size-3.5" />
                            {readinessDetail.level}
                          </span>

                          {readinessDetail.isProvisional && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-bold text-amber-500">
                              <AlertTriangle className="size-3" />
                              Provisional Score
                            </span>
                          )}

                          <span className="rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                            Stage: {readinessDetail.stage}
                          </span>
                        </div>

                        <h2 className="text-base font-bold text-foreground">
                          {readinessDetail.score >= 90
                            ? "Complete & Document-Ready for Submission"
                            : readinessDetail.score >= 75
                            ? "Substantially Complete with Minor Non-Blocking Items"
                            : readinessDetail.score >= 50
                            ? "Attention Required Before Submission"
                            : "Incomplete Documentation Package"}
                        </h2>

                        <p className="text-xs text-muted-foreground max-w-2xl">
                          Calculated deterministically from 7 categories: Patient Identity (15), Policy Info (20), Diagnosis & ICD-10 (20), Required Documents (20), Document Quality (10), Cross-Consistency (10), and Consent (5).
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-col gap-2 rounded-xl border border-border bg-secondary/20 p-4 text-xs md:w-64">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Points Earned:</span>
                        <span className="font-mono font-bold text-foreground">
                          {readinessDetail.score.toFixed(1)} / 100
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Stage Requirements:</span>
                        <span className="font-semibold text-foreground">
                          {readinessDetail.missingRequirements.length === 0 ? "Satisfied" : `${readinessDetail.missingRequirements.length} Missing`}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Assessment Type:</span>
                        <span className="font-semibold text-foreground">
                          {readinessDetail.isProvisional ? "Provisional" : "Authoritative"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Provisional Assessment Notice */}
                  {readinessDetail.isProvisional && (
                    <div className="mt-5 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs">
                      <div className="flex items-start gap-2.5">
                        <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="font-bold text-amber-600 dark:text-amber-400">
                            Provisional Assessment Notice
                          </h4>
                          <p className="mt-1 text-muted-foreground">
                            This readiness assessment is provisional because critical mandatory claim components are pending or unconfirmed:
                          </p>
                          <ul className="mt-2 list-disc pl-4 space-y-1 text-foreground/90 font-medium">
                            {readinessDetail.provisionalReasons.map((reason, idx) => (
                              <li key={idx}>{reason}</li>
                            ))}
                          </ul>
                          <p className="mt-2 text-[11px] text-muted-foreground">
                            The score will automatically recalculate to authoritative status once required documents and ICD-10 diagnostic proofs are uploaded.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Stage Missing Requirements */}
                {readinessDetail.missingRequirements.length > 0 && (
                  <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5 shadow-sm">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="size-5 text-rose-500 shrink-0 mt-0.5" />
                      <div className="space-y-2">
                        <h3 className="text-sm font-bold text-rose-600 dark:text-rose-400">
                          Stage Missing Requirements ({readinessDetail.stage})
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          The following documents or prerequisites are mandatory for this claim's workflow stage and must be uploaded to avoid query or rejection:
                        </p>
                        <div className="flex flex-wrap gap-2 pt-1">
                          {readinessDetail.missingRequirements.map((req, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-bold text-rose-600 dark:text-rose-400"
                            >
                              <AlertCircle className="size-3 shrink-0" />
                              {req.replace(/_/g, " ").toUpperCase()}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 7 Assessment Categories Breakdown */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-foreground">
                        All 7 Explainable Assessment Categories
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Detailed points earned, checks performed, identified evidence, and point deductions.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {readinessDetail.categoryList.map((cat, idx) => {
                      const isExpanded = expandedCategories[cat.key] ?? false;
                      const percentage = cat.weight > 0 ? Math.round((cat.score / cat.weight) * 100) : 0;
                      const status = (cat.status || "").toLowerCase();
                      const isPassed = status.includes("passed") || status.includes("verified") || percentage >= 90;

                      return (
                        <div
                          key={cat.key || idx}
                          className="rounded-2xl border border-border bg-card shadow-sm transition hover:border-primary/30"
                        >
                          <div
                            onClick={() => toggleCategory(cat.key)}
                            className="flex cursor-pointer items-center justify-between p-4"
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={`flex size-8 shrink-0 items-center justify-center rounded-xl border text-xs font-bold ${
                                  isPassed
                                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                    : percentage >= 50
                                    ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                    : "border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                }`}
                              >
                                {idx + 1}
                              </div>

                              <div>
                                <div className="flex items-center gap-2">
                                  <h4 className="text-xs font-bold text-foreground">
                                    {cat.name}
                                  </h4>
                                  <span className="rounded-md bg-secondary px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                                    Weight: {cat.weight} pts
                                  </span>
                                </div>
                                <div className="mt-1 flex items-center gap-2">
                                  <div className="h-1.5 w-32 overflow-hidden rounded-full bg-secondary">
                                    <div
                                      className={`h-full rounded-full ${
                                        percentage >= 80 ? "bg-emerald-500" : percentage >= 50 ? "bg-amber-500" : "bg-rose-500"
                                      }`}
                                      style={{ width: `${Math.min(100, percentage)}%` }}
                                    />
                                  </div>
                                  <span className="font-mono text-[11px] font-semibold text-muted-foreground">
                                    {cat.score} / {cat.weight} pts ({percentage}%)
                                  </span>
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span
                                className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                                  isPassed
                                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                    : percentage >= 50
                                    ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                    : "border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                }`}
                              >
                                {cat.status || (isPassed ? "Passed" : "Needs Attention")}
                              </span>

                              {isExpanded ? (
                                <ChevronUp className="size-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="size-4 text-muted-foreground" />
                              )}
                            </div>
                          </div>

                          {/* Expandable Category Details */}
                          {isExpanded && (
                            <div className="border-t border-border bg-secondary/15 p-4 text-xs space-y-4">
                              {/* Checks performed */}
                              {cat.checks && cat.checks.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                    Checks Performed
                                  </span>
                                  <div className="mt-1.5 space-y-1">
                                    {cat.checks.map((chk: any, cIdx: number) => {
                                      const label = typeof chk === "string" ? chk : chk.check || chk.name;
                                      const earned = chk.earned !== undefined ? `${chk.earned}/${chk.max || chk.available}` : null;
                                      const passed = chk.passed ?? (chk.earned === chk.max);

                                      return (
                                        <div
                                          key={cIdx}
                                          className="flex items-center justify-between rounded-lg bg-card/60 p-2 border border-border/50"
                                        >
                                          <div className="flex items-center gap-2">
                                            {passed ? (
                                              <CheckCircle2 className="size-3.5 text-emerald-500 shrink-0" />
                                            ) : (
                                              <AlertTriangle className="size-3.5 text-amber-500 shrink-0" />
                                            )}
                                            <span className="text-foreground font-medium">{label}</span>
                                          </div>
                                          {earned && (
                                            <span className="font-mono text-[11px] text-muted-foreground">
                                              {earned}
                                            </span>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Identified Information */}
                              {cat.identified_info && cat.identified_info.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                                    Successfully Identified Evidence
                                  </span>
                                  <div className="mt-1 flex flex-wrap gap-1.5">
                                    {cat.identified_info.map((info: string, iIdx: number) => (
                                      <span
                                        key={iIdx}
                                        className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300"
                                      >
                                        ✓ {info}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Deductions & Missing Info */}
                              {cat.deductions && cat.deductions.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                                    Points Deducted & Missing Information
                                  </span>
                                  <div className="mt-1.5 space-y-1">
                                    {cat.deductions.map((ded: string, dIdx: number) => (
                                      <div
                                        key={dIdx}
                                        className="flex items-start gap-2 rounded-lg border border-rose-500/20 bg-rose-500/5 p-2 text-rose-700 dark:text-rose-300 font-medium"
                                      >
                                        <AlertCircle className="size-3.5 shrink-0 mt-0.5 text-rose-500" />
                                        <span>{ded}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Recommended Next Actions */}
                              {cat.recommended_actions && cat.recommended_actions.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
                                    Recommended Corrective Action
                                  </span>
                                  <div className="mt-1 space-y-1">
                                    {cat.recommended_actions.map((act: string, aIdx: number) => (
                                      <div
                                        key={aIdx}
                                        className="flex items-center gap-2 rounded-lg border border-sky-500/20 bg-sky-500/5 p-2 text-sky-700 dark:text-sky-300"
                                      >
                                        <Sparkles className="size-3.5 shrink-0 text-sky-500" />
                                        <span>{act}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Recommended Corrective Actions Overall */}
                {readinessDetail.recommendedActions.length > 0 && (
                  <div className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-5 shadow-sm">
                    <div className="flex items-start gap-3">
                      <Sparkles className="size-5 text-sky-500 shrink-0 mt-0.5" />
                      <div className="space-y-2">
                        <h3 className="text-sm font-bold text-sky-600 dark:text-sky-400">
                          Recommended Corrective Actions to Reach 90+ Score
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          Prioritized steps to resolve remaining gaps before insurer adjudication:
                        </p>
                        <div className="space-y-1.5 pt-1">
                          {readinessDetail.recommendedActions.map((action, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2.5 rounded-xl border border-sky-500/20 bg-card p-2.5 text-xs text-foreground font-medium"
                            >
                              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-sky-500/20 text-[10px] font-bold text-sky-600 dark:text-sky-400">
                                {idx + 1}
                              </span>
                              <span>{action}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Regulatory Disclaimer */}
                <div className="rounded-xl border border-border bg-secondary/30 p-4 text-[11px] text-muted-foreground">
                  <p className="font-semibold text-foreground/80">ClaimBridge Assessment Notice</p>
                  <p className="mt-1">{readinessDetail.disclaimer}</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ========================================================================= */
          /* VIEW MODE 2: AUTOMATIC OVERALL CLAIM READINESS DASHBOARD (ALL CLAIMS) */
          /* ========================================================================= */
          <div className="space-y-6">
            {/* Header Strip */}
            <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <ClipboardCheck className="size-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-lg font-bold text-foreground">
                        Overall Claim Readiness Dashboard
                      </h1>
                      <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        Live Auto-Assessed
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Automatic 7-category readiness evaluation across all claims accessible to your account.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={loadDashboard}
                    disabled={loadingDashboard}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary disabled:opacity-50"
                  >
                    <RefreshCw className={`size-3.5 text-primary ${loadingDashboard ? "animate-spin" : ""}`} />
                    <span>Refresh Assessments</span>
                  </button>

                  <Link
                    to="/claims/new"
                    className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-primary/90"
                  >
                    <span>New Pre-Auth / Claim</span>
                  </Link>
                </div>
              </div>
            </div>

            {/* Error banner if dashboard load failed */}
            {dashboardError && (
              <div className="flex items-center justify-between rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-600 dark:text-rose-400">
                <div className="flex items-center gap-2">
                  <AlertCircle className="size-4 shrink-0" />
                  <span>{dashboardError}</span>
                </div>
                <button
                  type="button"
                  onClick={loadDashboard}
                  className="rounded-lg bg-rose-600 px-3 py-1 font-semibold text-white hover:bg-rose-700"
                >
                  Retry
                </button>
              </div>
            )}

            {/* ========================================================================= */}
            {/* 2.A SUMMARY METRIC CARDS */}
            {/* ========================================================================= */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {/* Card 1: Total Assessed */}
              <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                    Total Claims
                  </span>
                  <div className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <FileText className="size-3.5" />
                  </div>
                </div>
                <p className="mt-2 text-2xl font-black text-foreground">
                  {loadingDashboard ? "—" : summary.totalAssessed}
                </p>
                <div className="mt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Assessed Claims</span>
                  {summary.totalAssessed > 0 && (
                    <span className="font-mono text-primary font-bold">
                      Avg: {summary.averageScore}%
                    </span>
                  )}
                </div>
              </div>

              {/* Card 2: Excellent */}
              <div
                onClick={() => setSelectedLevelFilter(selectedLevelFilter === "excellent" ? "all" : "excellent")}
                className={`cursor-pointer rounded-2xl border p-4 shadow-sm transition hover:border-emerald-500/50 ${
                  selectedLevelFilter === "excellent"
                    ? "border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500"
                    : "border-border bg-card"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    Excellent
                  </span>
                  <div className="flex size-7 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                    <Sparkles className="size-3.5" />
                  </div>
                </div>
                <p className="mt-2 text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  {loadingDashboard ? "—" : summary.excellentClaims}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Score 90–100 pts
                </p>
              </div>

              {/* Card 3: Good */}
              <div
                onClick={() => setSelectedLevelFilter(selectedLevelFilter === "good" ? "all" : "good")}
                className={`cursor-pointer rounded-2xl border p-4 shadow-sm transition hover:border-sky-500/50 ${
                  selectedLevelFilter === "good"
                    ? "border-sky-500 bg-sky-500/10 ring-1 ring-sky-500"
                    : "border-border bg-card"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
                    Good
                  </span>
                  <div className="flex size-7 items-center justify-center rounded-lg bg-sky-500/15 text-sky-600 dark:text-sky-400">
                    <CheckCircle2 className="size-3.5" />
                  </div>
                </div>
                <p className="mt-2 text-2xl font-black text-sky-600 dark:text-sky-400">
                  {loadingDashboard ? "—" : summary.goodClaims}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Score 75–89 pts
                </p>
              </div>

              {/* Card 4: Needs Attention */}
              <div
                onClick={() => setSelectedLevelFilter(selectedLevelFilter === "needs_attention" ? "all" : "needs_attention")}
                className={`cursor-pointer rounded-2xl border p-4 shadow-sm transition hover:border-amber-500/50 ${
                  selectedLevelFilter === "needs_attention"
                    ? "border-amber-500 bg-amber-500/10 ring-1 ring-amber-500"
                    : "border-border bg-card"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                    Needs Attention
                  </span>
                  <div className="flex size-7 items-center justify-center rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="size-3.5" />
                  </div>
                </div>
                <p className="mt-2 text-2xl font-black text-amber-600 dark:text-amber-400">
                  {loadingDashboard ? "—" : summary.needsAttentionClaims}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Score 50–74 pts
                </p>
              </div>

              {/* Card 5: Incomplete */}
              <div
                onClick={() => setSelectedLevelFilter(selectedLevelFilter === "incomplete" ? "all" : "incomplete")}
                className={`cursor-pointer rounded-2xl border p-4 shadow-sm transition hover:border-rose-500/50 ${
                  selectedLevelFilter === "incomplete"
                    ? "border-rose-500 bg-rose-500/10 ring-1 ring-rose-500"
                    : "border-border bg-card"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                    Incomplete
                  </span>
                  <div className="flex size-7 items-center justify-center rounded-lg bg-rose-500/15 text-rose-600 dark:text-rose-400">
                    <AlertCircle className="size-3.5" />
                  </div>
                </div>
                <p className="mt-2 text-2xl font-black text-rose-600 dark:text-rose-400">
                  {loadingDashboard ? "—" : summary.incompleteClaims}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Score &lt; 50 pts
                </p>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* SEARCH & FILTER CONTROLS BAR */}
            {/* ========================================================================= */}
            <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
              {/* Search Box */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Filter by Claim ID, Patient, Hospital, Policy #..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full rounded-xl border border-border bg-secondary/40 pl-9 pr-4 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                />
              </div>

              {/* Filter Controls */}
              <div className="flex flex-wrap items-center gap-2">
                {/* Level Filter */}
                <select
                  value={selectedLevelFilter}
                  onChange={(e) => setSelectedLevelFilter(e.target.value)}
                  className="rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none"
                >
                  <option value="all">All Readiness Levels</option>
                  <option value="excellent">Excellent (90–100)</option>
                  <option value="good">Good (75–89)</option>
                  <option value="needs_attention">Needs Attention (50–74)</option>
                  <option value="incomplete">Incomplete (&lt; 50)</option>
                </select>

                {/* Stage Filter */}
                <select
                  value={selectedStageFilter}
                  onChange={(e) => setSelectedStageFilter(e.target.value)}
                  className="rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none"
                >
                  <option value="all">All Stages</option>
                  <option value="preauth">Pre-Authorization</option>
                  <option value="final_auth">Final Authorization</option>
                  <option value="reimbursement">Reimbursement</option>
                </select>

                {/* Sort Order */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground focus:border-primary focus:outline-none"
                >
                  <option value="score_asc">Sort: Lowest Score First (Default)</option>
                  <option value="score_desc">Sort: Highest Score First</option>
                  <option value="date_desc">Sort: Newest Claims First</option>
                  <option value="patient_asc">Sort: Patient Name (A–Z)</option>
                </select>
              </div>
            </div>

            {/* ========================================================================= */}
            {/* 2.B OVERALL CLAIM READINESS TABLE */}
            {/* ========================================================================= */}
            <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
              {loadingDashboard ? (
                <div className="p-12 text-center">
                  <RefreshCw className="mx-auto size-8 animate-spin text-primary" />
                  <p className="mt-3 text-sm font-semibold text-foreground">
                    Loading overall claim readiness assessments...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Evaluating live documentation completeness and 7-category evidence across all accessible claims.
                  </p>
                </div>
              ) : displayedClaims.length === 0 ? (
                <div className="p-12 text-center">
                  <ClipboardCheck className="mx-auto size-10 text-muted-foreground/60" />
                  <h3 className="mt-3 text-sm font-bold text-foreground">
                    {summary.totalAssessed === 0 ? "No Claims Found" : "No Matching Claims"}
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
                    {summary.totalAssessed === 0
                      ? "There are currently no insurance claims recorded or assigned to your organization."
                      : "Try clearing your search query or adjusting your readiness level/stage filters."}
                  </p>
                  {summary.totalAssessed > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearchTerm("");
                        setSelectedLevelFilter("all");
                        setSelectedStageFilter("all");
                      }}
                      className="mt-3 inline-flex items-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary/80"
                    >
                      Reset All Filters
                    </button>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-border bg-secondary/30 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3.5">Claim ID</th>
                        <th className="px-4 py-3.5">Patient Name</th>
                        <th className="px-4 py-3.5">Hospital</th>
                        <th className="px-4 py-3.5">Claim Stage</th>
                        <th className="px-4 py-3.5 w-48">Readiness Score</th>
                        <th className="px-4 py-3.5">Status</th>
                        <th className="px-4 py-3.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {displayedClaims.map((claim) => {
                        const levelConfig = getLevelBadge(claim.readinessLevel);
                        const stageLabel = formatStageLabel(claim.claimStage);

                        return (
                          <tr
                            key={claim.claimId}
                            className="transition hover:bg-secondary/20 group"
                          >
                            {/* 1. Claim ID */}
                            <td className="px-4 py-3.5 font-mono font-bold text-foreground">
                              <span className="rounded-lg bg-secondary px-2 py-1 text-[11px] group-hover:bg-primary/10 group-hover:text-primary transition">
                                {claim.claimNumber}
                              </span>
                            </td>

                            {/* 2. Patient Name */}
                            <td className="px-4 py-3.5">
                              <div className="font-semibold text-foreground">
                                {claim.patientName}
                              </div>
                              <div className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                                {claim.patientAge !== null && claim.patientAge !== undefined && (
                                  <span>{claim.patientAge} yrs •</span>
                                )}
                                <span>{claim.insuranceProvider || "Insurance"}</span>
                              </div>
                            </td>

                            {/* 3. Hospital */}
                            <td className="px-4 py-3.5 text-foreground">
                              <div className="flex items-center gap-1.5">
                                <Building2 className="size-3 text-muted-foreground shrink-0" />
                                <span className="truncate max-w-[150px]">{claim.hospital}</span>
                              </div>
                            </td>

                            {/* 4. Claim Stage */}
                            <td className="px-4 py-3.5">
                              <span className="inline-flex items-center rounded-full border border-border bg-secondary/50 px-2.5 py-0.5 text-[10px] font-semibold text-foreground">
                                {stageLabel}
                              </span>
                            </td>

                            {/* 5. Readiness Score */}
                            <td className="px-4 py-3.5">
                              <div className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-mono font-black text-sm text-foreground">
                                      {claim.readinessScore.toFixed(1)}
                                    </span>
                                    <span className="text-[10px] font-medium text-muted-foreground">/100</span>
                                  </div>

                                  {claim.isProvisional && (
                                    <span
                                      title={claim.provisionalReasons?.join("; ") || "Missing documentation"}
                                      className="inline-flex items-center gap-0.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.2 text-[9px] font-bold text-amber-500"
                                    >
                                      <AlertTriangle className="size-2.5" />
                                      PROV
                                    </span>
                                  )}
                                </div>

                                {/* Mini Progress Bar */}
                                <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                                  <div
                                    className={`h-full rounded-full transition-all duration-300 ${levelConfig.barBg}`}
                                    style={{ width: `${Math.min(100, Math.max(2, claim.readinessScore))}%` }}
                                  />
                                </div>
                              </div>
                            </td>

                            {/* 6. Status */}
                            <td className="px-4 py-3.5">
                              <span
                                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${levelConfig.bg}`}
                              >
                                <span className={`size-1.5 rounded-full ${levelConfig.barBg}`} />
                                {claim.readinessLevel}
                              </span>
                            </td>

                            {/* 7. Action */}
                            <td className="px-4 py-3.5 text-right">
                              <button
                                type="button"
                                onClick={() => handleViewClaimDetails(claim.claimId)}
                                className="inline-flex items-center gap-1 rounded-xl bg-primary/10 border border-primary/20 px-3 py-1.5 text-xs font-bold text-primary transition hover:bg-primary hover:text-white"
                              >
                                <span>View Details</span>
                                <ArrowRight className="size-3" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Table Footer */}
              {!loadingDashboard && displayedClaims.length > 0 && (
                <div className="flex items-center justify-between border-t border-border bg-secondary/10 px-4 py-3 text-[11px] text-muted-foreground">
                  <span>
                    Showing <strong className="text-foreground">{displayedClaims.length}</strong> of{" "}
                    <strong className="text-foreground">{dashboardData?.summary?.totalAssessed || displayedClaims.length}</strong> evaluated claims
                  </span>
                  <span className="font-medium text-foreground">
                    Sorted by readiness score (lowest first)
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
export default ClaimReadinessPage;
