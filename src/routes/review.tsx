import { createFileRoute } from "@tanstack/react-router";
import React, { useState, useEffect } from "react";
import {
  UserCheck,
  Search,
  Filter,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Building2,
  AlertTriangle,
  HelpCircle,
  Inbox,
  RefreshCw,
  Layers,
  Clock,
  Zap,
  ArrowUpDown,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { HumanReviewTriage } from "@/components/pipeline/HumanReviewTriage";
import { Claim, formatINR } from "@/lib/claims";
import {
  fetchClaimById,
  fetchClaims,
  fetchTpaReviewQueue,
  fetchClaimsSummary,
  TpaQueueItem,
  ClaimsSummaryData,
} from "@/api/claims";
import { getCurrentUser } from "@/api/auth";

export const Route = createFileRoute("/review")({
  head: () => ({
    meta: [
      { title: "Human Review & Triage Desk — ClaimBridge" },
      {
        name: "description",
        content: "Role-based human review triage workspace for claims requiring reviewer attention.",
      },
    ],
  }),
  component: HumanReviewPage,
});

type TpaFilterType =
  | "all"
  | "pending_review"
  | "low_confidence"
  | "validation_mismatch"
  | "missing_documents"
  | "info_requested"
  | "escalated"
  | "approved"
  | "rejected";

function HumanReviewPage() {
  const currentUser = getCurrentUser();
  const isHospitalCoordinator =
    !currentUser ||
    currentUser.portal === "Hospital" ||
    currentUser.role === "Coordinator";

  const [tpaFilter, setTpaFilter] = useState<TpaFilterType>("pending_review");
  const [tpaQueue, setTpaQueue] = useState<TpaQueueItem[]>([]);
  const [hospitalClaims, setHospitalClaims] = useState<any[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [activeClaim, setActiveClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingClaim, setLoadingClaim] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"recent" | "amount" | "readiness">("recent");

  const [summary, setSummary] = useState<ClaimsSummaryData>({
    totalClaims: 0,
    approvedClaims: 0,
    rejectedClaims: 0,
    pendingClaims: 0,
    averageReadinessScore: 0,
  });

  // Load Queue & Live Analytics Data
  const loadQueue = async () => {
    setLoading(true);
    try {
      const [sum, claimsList, queueItems] = await Promise.all([
        fetchClaimsSummary().catch(() => null),
        isHospitalCoordinator ? fetchClaims().catch(() => []) : null,
        !isHospitalCoordinator ? fetchTpaReviewQueue(tpaFilter).catch(() => []) : null,
      ]);

      if (sum) {
        setSummary(sum);
      }

      if (isHospitalCoordinator && claimsList) {
        setHospitalClaims(claimsList);
        if (!selectedClaimId && claimsList.length > 0) {
          setSelectedClaimId(claimsList[0].id);
        }
      } else if (queueItems) {
        setTpaQueue(queueItems);
        if (!selectedClaimId && queueItems.length > 0) {
          setSelectedClaimId(queueItems[0].id);
        }
      }
    } catch (err) {
      console.warn("Failed to load review queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [tpaFilter, isHospitalCoordinator]);

  // Load Selected Claim Details
  useEffect(() => {
    if (!selectedClaimId) return;
    setLoadingClaim(true);
    fetchClaimById(selectedClaimId)
      .then((data: any) => {
        if (data) {
          setActiveClaim(data as any);
        }
      })
      .catch((err) => {
        console.warn("Error fetching claim details:", err);
      })
      .finally(() => {
        setLoadingClaim(false);
      });
  }, [selectedClaimId]);

  const rawItems = isHospitalCoordinator ? hospitalClaims : tpaQueue;
  const filteredItems = rawItems
    .filter((item) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        (item.claimNumber || item.id || "").toLowerCase().includes(q) ||
        (item.patientName || "").toLowerCase().includes(q) ||
        (item.hospital || "").toLowerCase().includes(q) ||
        (item.policyNumber || item.insuranceProvider || "").toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      if (sortBy === "amount") {
        return (Number(b.claimedAmount) || 0) - (Number(a.claimedAmount) || 0);
      }
      if (sortBy === "readiness") {
        return (Number(b.readiness) || 0) - (Number(a.readiness) || 0);
      }
      return (b.createdAt || "").localeCompare(a.createdAt || "");
    });

  return (
    <AppLayout
      title={isHospitalCoordinator ? "Hospital Review & Response Desk" : "TPA Adjudication & Triage Desk"}
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Human Review" }]}
    >
      <div className="space-y-6">
        
        {/* HEADER BAR WITH PORTAL IDENTIFIER */}
        <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500">
              <UserCheck className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-foreground">
                  {isHospitalCoordinator
                    ? `Hospital Claims Triage (${summary.totalClaims || hospitalClaims.length} Claims)`
                    : `TPA Review Queue (${summary.totalClaims || tpaQueue.length} Claims Total)`}
                </h2>
                <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 font-mono text-[10px] text-primary">
                  {currentUser?.organization || (isHospitalCoordinator ? "Hospital Scope" : "TPA Scope")}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {isHospitalCoordinator
                  ? "Monitor claims requiring clarification, upload requested evidence, and review validation status."
                  : "Adjudicate incoming claims, inspect multi-document evidence, request info, or approve/reject."}
              </p>
            </div>
          </div>

          <button
            onClick={loadQueue}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary/80 transition"
          >
            <RefreshCw className="size-3.5" /> Refresh Queue
          </button>
        </div>

        {/* OPERATIONAL SUMMARY ANALYTICS CARDS (DERIVED DIRECTLY FROM DATABASE) */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {/* TOTAL CLAIMS */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Total Claims
              </span>
              <p className="mt-1 text-2xl font-extrabold text-foreground font-mono">
                {summary.totalClaims}
              </p>
              <span className="text-[10px] text-muted-foreground">Database records</span>
            </div>
            <div className="flex size-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500">
              <Layers className="size-5" />
            </div>
          </div>

          {/* APPROVED CLAIMS */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Approved
              </span>
              <p className="mt-1 text-2xl font-extrabold text-emerald-500 font-mono">
                {summary.approvedClaims}
              </p>
              <span className="text-[10px] text-emerald-500/80">Adjudicated claims</span>
            </div>
            <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500">
              <CheckCircle2 className="size-5" />
            </div>
          </div>

          {/* REJECTED CLAIMS */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Rejected
              </span>
              <p className="mt-1 text-2xl font-extrabold text-rose-500 font-mono">
                {summary.rejectedClaims}
              </p>
              <span className="text-[10px] text-rose-500/80">With rationale</span>
            </div>
            <div className="flex size-10 items-center justify-center rounded-xl bg-rose-500/10 text-rose-500">
              <XCircle className="size-5" />
            </div>
          </div>

          {/* PENDING / UNDER ANALYSIS */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Pending Review
              </span>
              <p className="mt-1 text-2xl font-extrabold text-amber-500 font-mono">
                {summary.pendingClaims}
              </p>
              <span className="text-[10px] text-amber-500/80">Requires triage</span>
            </div>
            <div className="flex size-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500">
              <Clock className="size-5" />
            </div>
          </div>

          {/* AVERAGE READINESS SCORE */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Avg Readiness
              </span>
              <p className="mt-1 text-2xl font-extrabold text-cyan-500 font-mono">
                {summary.averageReadinessScore}%
              </p>
              <span className="text-[10px] text-cyan-500/80">Composite metric</span>
            </div>
            <div className="flex size-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-500">
              <Zap className="size-5" />
            </div>
          </div>
        </div>

        {/* SEARCH, FILTER & SORT CONTROLS */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm">
          {/* SEARCH BAR */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by claim ID, patient, hospital, insurer..."
              className="h-9 w-full rounded-xl border border-border bg-secondary/50 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition"
            />
          </div>

          <div className="flex items-center gap-2">
            {/* SORT SELECTOR */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ArrowUpDown className="size-3.5" />
              <span>Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="h-8 rounded-lg border border-border bg-secondary px-2 text-xs text-foreground outline-none cursor-pointer"
              >
                <option value="recent">Most Recent</option>
                <option value="amount">Claimed Amount</option>
                <option value="readiness">Readiness Score</option>
              </select>
            </div>
          </div>
        </div>

        {/* TPA FILTER BAR (FOR TPA REVIEWERS) */}
        {!isHospitalCoordinator && (
          <div className="flex flex-wrap gap-1.5 rounded-2xl border border-border bg-card p-2 shadow-sm">
            {[
              { id: "pending_review", label: "Pending Review" },
              { id: "low_confidence", label: "Low Confidence (<85%)" },
              { id: "validation_mismatch", label: "Validation Mismatches" },
              { id: "missing_documents", label: "Missing Documents" },
              { id: "info_requested", label: "Info Requested" },
              { id: "escalated", label: "Escalated" },
              { id: "approved", label: "Approved" },
              { id: "rejected", label: "Rejected" },
              { id: "all", label: "All Scope Claims" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setTpaFilter(f.id as TpaFilterType)}
                className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                  tpaFilter === f.id
                    ? "bg-primary text-white shadow-sm font-semibold"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        {/* QUEUE CARDS STRIP */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Select Claim for Triage Adjudication ({filteredItems.length} of {rawItems.length} showing)
            </span>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-border bg-card p-8 text-center text-xs text-muted-foreground">
              Loading review queue from ClaimBridge backend...
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex min-h-[160px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-8 text-center space-y-2">
              <Inbox className="size-8 text-muted-foreground" />
              <p className="text-sm font-bold text-foreground">No Claims Found</p>
              <p className="text-xs text-muted-foreground max-w-md">
                {searchQuery
                  ? `No claims matched your search "${searchQuery}". Try clearing the search query or changing the filter.`
                  : isHospitalCoordinator
                  ? "All claims submitted by your hospital are currently processed or under review. No outstanding action required."
                  : `No claims match the filter '${tpaFilter}' within your assigned TPA scope.`}
              </p>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {filteredItems.map((item) => {
                const isSelected = selectedClaimId === item.id;
                const confDisplay =
                  item.confidenceCalculated && item.confidenceScore !== null && item.confidenceScore !== undefined
                    ? `${item.confidenceScore}%`
                    : "—";

                return (
                  <button
                    key={item.id}
                    onClick={() => setSelectedClaimId(item.id)}
                    className={`flex flex-col justify-between rounded-xl border p-3.5 text-left transition shadow-sm ${
                      isSelected
                        ? "border-primary bg-primary/10 shadow-md ring-1 ring-primary"
                        : "border-border bg-card hover:border-primary/50"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-primary">
                          {item.claimNumber || item.id}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                            item.status === "Approved"
                              ? "bg-emerald-500/10 text-emerald-500"
                              : item.status === "Rejected"
                              ? "bg-rose-500/10 text-rose-500"
                              : "bg-amber-500/10 text-amber-500"
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-foreground truncate">{item.patientName}</p>
                      <p className="text-[11px] text-muted-foreground truncate">{item.hospital || item.insuranceProvider}</p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-[10px]">
                      <span className="font-mono font-bold text-foreground">
                        {formatINR(item.claimedAmount)}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        Readiness: <strong className="text-foreground">{item.readiness}%</strong>
                      </span>
                    </div>

                    {item.reasons && item.reasons.length > 0 && (
                      <p className="mt-1.5 text-[10px] text-amber-500 truncate">
                        • {item.reasons[0]}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 3-COLUMN TRIAGE WORKSPACE FOR SELECTED CLAIM */}
        {loadingClaim ? (
          <div className="rounded-2xl border border-border bg-card p-12 text-center text-xs text-muted-foreground">
            Loading full claim evidence and document package...
          </div>
        ) : activeClaim ? (
          <HumanReviewTriage claim={activeClaim} onStatusUpdated={loadQueue} />
        ) : null}

      </div>
    </AppLayout>
  );
}
