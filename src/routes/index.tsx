import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import React, { useState } from "react";
import {
  FileText,
  Activity,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Plus,
  Search,
  ArrowRight,
  ShieldCheck,
  Zap,
  Filter,
  BarChart3,
  PieChart,
  UserCheck,
  DollarSign,
  Clock,
  Sparkles,
} from "lucide-react";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RePieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import { AppLayout } from "@/components/layout/AppLayout";
import { formatINR } from "@/lib/claims";
import { getCurrentUser } from "@/api/auth";
import {
  ClaimsAnalyticsData,
  ClaimsSummaryData,
  ClaimApiData,
  fetchClaims,
  fetchClaimsAnalytics,
  fetchClaimsSummary,
} from "@/api/claims";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — ClaimBridge Intelligence" },
      {
        name: "description",
        content:
          "Autonomous Insurance Claim Verification, OCR Extraction & Readiness Assessment Platform.",
      },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState<ClaimApiData[]>([]);
  const [summary, setSummary] = useState<ClaimsSummaryData | null>(null);
  const [analytics, setAnalytics] = useState<ClaimsAnalyticsData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      navigate({ to: "/auth" });
      return;
    }
    if (user.role === "claimant") {
      navigate({ to: "/claims" });
      return;
    }

    let active = true;
    Promise.all([fetchClaims(), fetchClaimsSummary(), fetchClaimsAnalytics()])
      .then(([claimData, summaryData, analyticsData]) => {
        if (!active) return;
        setClaims(Array.isArray(claimData) ? claimData : []);
        setSummary(summaryData);
        setAnalytics(analyticsData);
      })
      .catch((err: unknown) => {
        if (active) {
          setLoadError(
            err instanceof Error ? err.message : "Unable to load the authorized dashboard.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [navigate]);

  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("All");

  const filteredClaims = claims.filter((claim) => {
    const matchesSearch =
      (claim.patientName || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (claim.claimNumber || claim.id).toLowerCase().includes(searchQuery.toLowerCase()) ||
      (claim.policyNumber || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (claim.hospital || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (filterStatus === "All") return matchesSearch;
    return matchesSearch && claim.status === filterStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Ready for Submission":
      case "Approved":
        return "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981] shadow-[0_0_10px_rgba(16,185,129,0.2)]";
      case "Needs Review":
        return "border-[#F59E0B]/40 bg-[#F59E0B]/10 text-[#F59E0B] shadow-[0_0_10px_rgba(245,158,11,0.2)]";
      case "Under Analysis":
        return "border-[#3B82F6]/40 bg-[#3B82F6]/10 text-[#3B82F6] shadow-[0_0_10px_rgba(59,130,246,0.2)]";
      default:
        return "border-slate-700 bg-slate-800 text-slate-300";
    }
  };

  const readinessTrendData = analytics?.readinessTrends || [];
  const discrepancyData = (analytics?.commonDiscrepancies || []).slice(0, 5).map((item, index) => ({
    name: item.category,
    value: item.count,
    color: ["#EF4444", "#F59E0B", "#06B6D4", "#8B5CF6", "#10B981"][index] || "#64748B",
  }));

  return (
    <AppLayout title="Claims Operations Dashboard">
      <div className="space-y-8">
        {/* ========================================================================= */}
        {/* TOP WELCOME HEADING */}
        {/* ========================================================================= */}
        <section className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg bg-[#3B82F6]/20 text-[#3B82F6]">
                <ShieldCheck className="size-4" />
              </div>
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#06B6D4]">
                Enterprise Operations Workspace
              </span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
              TPA Claims Officer Dashboard
            </h1>
            <p className="mt-1 text-xs text-[#9CA3AF]">
              Authorized claims, evidence review, decisions, and organization-scoped analytics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/review"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#06B6D4]/50 bg-[#06B6D4]/10 px-4 text-xs font-semibold text-[#06B6D4] transition hover:bg-[#06B6D4]/20 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
            >
              <Zap className="size-4" />
              Open Review Queue
            </Link>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* KPI METRICS GRID */}
        {/* ========================================================================= */}
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Total Claims */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-blue">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Total Claims
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-white">
                  {summary?.totalClaims ?? "—"}
                </p>
                <div className="mt-2 text-xs text-[#9CA3AF]">In authorized TPA scope</div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#3B82F6]/15 text-[#3B82F6]">
                <FileText className="size-5" />
              </div>
            </div>
          </div>

          {/* Pending Review */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-cyan">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Pending Review
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#06B6D4]">
                  {summary?.pendingReviewClaims ?? "—"}
                </p>
                <div className="mt-2 text-xs text-[#9CA3AF]">Awaiting officer review</div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#06B6D4]/15 text-[#06B6D4]">
                <BarChart3 className="size-5" />
              </div>
            </div>
          </div>

          {/* Approved */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-purple">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Approved
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#8B5CF6]">
                  {summary?.approvedClaims ?? "—"}
                </p>
                <div className="mt-2 text-xs text-[#9CA3AF]">Recorded TPA decisions</div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#8B5CF6]/15 text-[#8B5CF6]">
                <Zap className="size-5" />
              </div>
            </div>
          </div>

          {/* Rejected */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-cyan">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Rejected
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#F59E0B]">
                  {summary?.rejectedClaims ?? "—"}
                </p>
                <div className="mt-2 text-xs text-[#9CA3AF]">Recorded TPA decisions</div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#F59E0B]/15 text-[#F59E0B]">
                <UserCheck className="size-5" />
              </div>
            </div>
          </div>

          {[
            {
              label: "Awaiting Information",
              value: analytics?.awaitingInformation,
              note: "Additional evidence requested",
            },
            { label: "Escalated", value: analytics?.escalated, note: "Requires senior review" },
            {
              label: "Average Readiness",
              value: summary?.averageReadinessScore,
              note: "Readiness is not an approval decision",
            },
            {
              label: "Avg. Processing Time",
              value: analytics?.averageProcessingTimeDays,
              note: "Days across recorded decisions",
            },
          ].map((metric) => (
            <div key={metric.label} className="glass-panel p-5 rounded-2xl border border-[#1F2937]">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                {metric.label}
              </p>
              <p className="mt-2 font-mono text-3xl font-extrabold text-white">
                {metric.value == null
                  ? "—"
                  : metric.label === "Average Readiness"
                    ? `${metric.value}%`
                    : metric.value}
              </p>
              <p className="mt-2 text-xs text-[#9CA3AF]">{metric.note}</p>
            </div>
          ))}
        </section>

        {/* ========================================================================= */}
        {/* DASHBOARD ANALYTICS CHARTS */}
        {/* ========================================================================= */}
        <section className="grid gap-6 lg:grid-cols-3">
          {/* Recorded readiness processing trend */}
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl lg:col-span-2">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">
                  Processed Claims & Readiness Trend
                </h3>
                <p className="text-xs text-[#9CA3AF]">
                  From recorded processing events in your authorized scope
                </p>
              </div>
              <span className="rounded-full bg-[#3B82F6]/10 px-3 py-1 font-mono text-xs text-[#3B82F6]">
                {readinessTrendData.length} monthly buckets
              </span>
            </div>

            <div className="mt-6 h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={readinessTrendData}>
                  <defs>
                    <linearGradient id="neonCyanArea" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06B6D4" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="neonBlueArea" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                  <XAxis dataKey="month" stroke="#9CA3AF" tickLine={false} fontSize={12} />
                  <YAxis yAxisId="claims" stroke="#9CA3AF" tickLine={false} fontSize={12} />
                  <YAxis
                    yAxisId="readiness"
                    orientation="right"
                    domain={[0, 100]}
                    stroke="#9CA3AF"
                    tickLine={false}
                    fontSize={12}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B0F17",
                      borderColor: "#1F2937",
                      borderRadius: "0.75rem",
                      color: "#F9FAFB",
                    }}
                  />
                  <Area
                    type="monotone"
                    yAxisId="claims"
                    dataKey="processedClaims"
                    stroke="#06B6D4"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#neonCyanArea)"
                    name="Processed claims"
                  />
                  <Area
                    type="monotone"
                    yAxisId="readiness"
                    dataKey="averageReadiness"
                    stroke="#3B82F6"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#neonBlueArea)"
                    name="Average readiness (not approval)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recorded discrepancy distribution */}
          <div className="flex flex-col justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl">
            <div className="border-b border-[#1F2937] pb-4">
              <h3 className="text-base font-bold text-white">Recorded Discrepancies</h3>
              <p className="text-xs text-[#9CA3AF]">Counts from persisted validation findings</p>
            </div>

            <div className="relative my-4 flex h-60 items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <RePieChart>
                  <Pie
                    data={discrepancyData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {discrepancyData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B0F17",
                      borderColor: "#1F2937",
                      borderRadius: "0.5rem",
                      color: "#F9FAFB",
                    }}
                  />
                </RePieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                <span className="text-2xl font-extrabold font-mono text-white">
                  {discrepancyData.reduce((sum, item) => sum + item.value, 0)}
                </span>
                <span className="text-[10px] text-[#9CA3AF]">Recorded findings</span>
              </div>
            </div>

            <div className="space-y-2 border-t border-[#1F2937] pt-4">
              {discrepancyData.length === 0 ? (
                <p className="text-center text-xs text-[#9CA3AF]">
                  No persisted discrepancy data in this scope.
                </p>
              ) : (
                discrepancyData.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className="size-2.5 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-[#9CA3AF]">{item.name}</span>
                    </div>
                    <span className="font-mono font-bold text-white">{item.value}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* LIVE RECENT CLAIMS TABLE */}
        {/* ========================================================================= */}
        <section className="overflow-hidden rounded-2xl border border-[#1F2937] bg-[#111827] shadow-xl">
          {/* Table Search & Filters */}
          <div className="border-b border-[#1F2937] bg-[#0B0F17] p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-base font-bold text-white">Live Claims Pipeline Table</h2>
                <p className="text-xs text-[#9CA3AF]">
                  Authorized organization claims and recorded readiness assessments
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#9CA3AF]" />
                  <input
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search claim, patient or hospital..."
                    className="h-9 w-full rounded-xl border border-[#1F2937] bg-[#111827] pl-9 pr-3 text-xs text-white placeholder-[#6B7280] outline-none focus:border-[#3B82F6]"
                  />
                </div>

                <div className="flex gap-1.5 rounded-xl border border-[#1F2937] bg-[#111827] p-1">
                  {["All", "Needs Review", "Under Analysis", "Approved", "Rejected"].map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setFilterStatus(st)}
                      className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                        filterStatus === st
                          ? "bg-[#3B82F6] text-white shadow-sm"
                          : "text-[#9CA3AF] hover:text-white"
                      }`}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Table Contents */}
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-[#0E1420] text-[10px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                <tr className="border-b border-[#1F2937]">
                  <th className="px-6 py-3.5">Claim ID</th>
                  <th className="px-6 py-3.5">Patient / Hospital</th>
                  <th className="px-6 py-3.5">Policy Number</th>
                  <th className="px-6 py-3.5">Claimed Amount</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Readiness Score</th>
                  <th className="px-6 py-3.5 text-right">Pipeline Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937] text-xs">
                {loadError ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-red-300">
                      {loadError}
                    </td>
                  </tr>
                ) : loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#9CA3AF]">
                      Loading authorized claims…
                    </td>
                  </tr>
                ) : filteredClaims.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#9CA3AF]">
                      No claims found matching your search filter.
                    </td>
                  </tr>
                ) : (
                  filteredClaims.map((claim) => (
                    <tr key={claim.id} className="group transition hover:bg-[#1F2937]/40">
                      {/* Claim ID */}
                      <td className="px-6 py-4">
                        <Link
                          to="/claims/$claimId"
                          params={{ claimId: claim.id }}
                          className="font-mono font-bold text-[#3B82F6] hover:underline"
                        >
                          {claim.claimNumber || claim.id}
                        </Link>
                        <p className="text-[10px] text-[#9CA3AF]">{claim.stage}</p>
                      </td>

                      {/* Patient / Hospital */}
                      <td className="px-6 py-4">
                        <p className="font-semibold text-white">{claim.patientName}</p>
                        <p className="text-[11px] text-[#06B6D4]">{claim.hospital}</p>
                      </td>

                      {/* Policy Number */}
                      <td className="px-6 py-4 font-mono text-[#9CA3AF]">{claim.policyNumber}</td>

                      {/* Claimed Amount */}
                      <td className="px-6 py-4 font-mono font-bold text-white">
                        {formatINR(claim.claimedAmount)}
                      </td>

                      {/* Status Badge */}
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold ${getStatusBadge(
                            claim.status,
                          )}`}
                        >
                          <span className="size-1.5 rounded-full bg-current" />
                          {claim.status}
                        </span>
                      </td>

                      {/* Readiness Score Progress */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-[#1F2937]">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#3B82F6] to-[#06B6D4]"
                              style={{ width: `${claim.readiness}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-white">{claim.readiness}%</span>
                        </div>
                      </td>

                      {/* Action */}
                      <td className="px-6 py-4 text-right">
                        <Link
                          to="/claims/$claimId"
                          params={{ claimId: claim.id }}
                          className="inline-flex size-8 items-center justify-center rounded-xl border border-[#1F2937] bg-[#111827] text-[#9CA3AF] transition hover:border-[#3B82F6] hover:text-white"
                        >
                          <ArrowRight className="size-4" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
