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
import { useClaims, formatINR } from "@/lib/claims";
import { getCurrentUser } from "@/api/auth";

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

const volumeTrendData = [
  { month: "Jan", volume: 3200, incurred: 4.2 },
  { month: "Feb", volume: 3800, incurred: 5.1 },
  { month: "Mar", volume: 4100, incurred: 5.8 },
  { month: "Apr", volume: 4900, incurred: 6.9 },
  { month: "May", volume: 5400, incurred: 7.4 },
  { month: "Jun", volume: 6100, incurred: 8.8 },
  { month: "Jul", volume: 6800, incurred: 9.6 },
  { month: "Aug", volume: 7400, incurred: 11.2 },
  { month: "Sep", volume: 8200, incurred: 14.2 },
];

const riskDistributionData = [
  { name: "Low Risk (Auto Qualified)", value: 68, color: "#10B981" },
  { name: "Medium Risk (Human Review)", value: 24, color: "#F59E0B" },
  { name: "High Risk / Flagged", value: 8, color: "#EF4444" },
];

function DashboardPage() {
  const claims = useClaims();
  const navigate = useNavigate();

  React.useEffect(() => {
    const user = getCurrentUser();
    if (user?.portal === "Hospital") {
      navigate({ to: "/claims" });
    }
  }, [navigate]);

  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("All");

  const filteredClaims = claims.filter((claim) => {
    const matchesSearch =
      claim.patientName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.policyNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.hospital.toLowerCase().includes(searchQuery.toLowerCase());

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
              Insurance Claim Intelligence Portal
            </h1>
            <p className="mt-1 text-xs text-[#9CA3AF]">
              Real-time multi-document OCR extraction, RAG policy verification & readiness triage.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/claims/CLM-TEST-001"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#06B6D4]/50 bg-[#06B6D4]/10 px-4 text-xs font-semibold text-[#06B6D4] transition hover:bg-[#06B6D4]/20 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
            >
              <Zap className="size-4" />
              Inspect CLM-TEST-001 Demo
            </Link>

            <Link
              to="/claims/new"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-5 text-xs font-semibold text-white shadow-lg shadow-[#3B82F6]/30 transition hover:shadow-xl hover:shadow-[#3B82F6]/50"
            >
              <Plus className="size-4" />
              Create New Claim
            </Link>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* KPI METRICS GRID */}
        {/* ========================================================================= */}
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          
          {/* Total Claims */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-blue">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Total Claims Processed
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-white">28,218</p>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-[#10B981]">
                  <TrendingUp className="size-3.5" /> +14.2% from last month
                </div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#3B82F6]/15 text-[#3B82F6]">
                <FileText className="size-5" />
              </div>
            </div>
          </div>

          {/* Total Incurred */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-cyan">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Total Incurred Loss
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#06B6D4]">₹18.4M</p>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-[#06B6D4]">
                  <DollarSign className="size-3.5" /> Avg ₹184,000 / Claim
                </div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#06B6D4]/15 text-[#06B6D4]">
                <BarChart3 className="size-5" />
              </div>
            </div>
          </div>

          {/* Avg Claim Readiness Score */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-purple">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Avg. Readiness Score
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#8B5CF6]">88 / 100</p>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-[#10B981]">
                  <CheckCircle2 className="size-3.5" /> High submission readiness
                </div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#8B5CF6]/15 text-[#8B5CF6]">
                <Zap className="size-5" />
              </div>
            </div>
          </div>

          {/* Pending Human Review Count */}
          <div className="glass-panel p-5 rounded-2xl border border-[#1F2937] glow-hover-cyan">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Pending Human Review
                </p>
                <p className="mt-2 text-3xl font-extrabold font-mono text-[#F59E0B]">342</p>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-[#F59E0B]">
                  <Clock className="size-3.5" /> Requires Triage Action
                </div>
              </div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#F59E0B]/15 text-[#F59E0B]">
                <UserCheck className="size-5" />
              </div>
            </div>
          </div>

        </section>

        {/* ========================================================================= */}
        {/* DASHBOARD ANALYTICS CHARTS */}
        {/* ========================================================================= */}
        <section className="grid gap-6 lg:grid-cols-3">
          
          {/* Volume & Incurred Trend (Neon Area Chart) */}
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl lg:col-span-2">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Claim Processing Volume & Incurred Loss Trend</h3>
                <p className="text-xs text-[#9CA3AF]">Monthly intake volume vs incurred claim loss ($M)</p>
              </div>
              <span className="rounded-full bg-[#3B82F6]/10 px-3 py-1 font-mono text-xs text-[#3B82F6]">
                2026 YTD Analytics
              </span>
            </div>

            <div className="mt-6 h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={volumeTrendData}>
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
                  <YAxis stroke="#9CA3AF" tickLine={false} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B0F17",
                      borderColor: "#1F2937",
                      borderRadius: "0.75rem",
                      color: "#F9FAFB",
                    }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="#06B6D4" strokeWidth={3} fillOpacity={1} fill="url(#neonCyanArea)" name="Claim Volume" />
                  <Area type="monotone" dataKey="incurred" stroke="#3B82F6" strokeWidth={3} fillOpacity={1} fill="url(#neonBlueArea)" name="Incurred Loss ($M)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Risk Distribution Donut Chart */}
          <div className="flex flex-col justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl">
            <div className="border-b border-[#1F2937] pb-4">
              <h3 className="text-base font-bold text-white">Risk Distribution</h3>
              <p className="text-xs text-[#9CA3AF]">Claim Readiness AI risk breakdown</p>
            </div>

            <div className="relative my-4 flex h-60 items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <RePieChart>
                  <Pie
                    data={riskDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {riskDistributionData.map((entry, index) => (
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
                <span className="text-2xl font-extrabold font-mono text-white">100%</span>
                <span className="text-[10px] text-[#9CA3AF]">Distribution</span>
              </div>
            </div>

            <div className="space-y-2 border-t border-[#1F2937] pt-4">
              {riskDistributionData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-[#9CA3AF]">{item.name}</span>
                  </div>
                  <span className="font-mono font-bold text-white">{item.value}%</span>
                </div>
              ))}
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
                  Real-time status tracking, OCR confidence & readiness scores
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
                  {["All", "Ready for Submission", "Needs Review", "Under Analysis"].map((st) => (
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
                {filteredClaims.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#9CA3AF]">
                      No claims found matching your search filter.
                    </td>
                  </tr>
                ) : (
                  filteredClaims.map((claim) => (
                    <tr
                      key={claim.id}
                      className="group transition hover:bg-[#1F2937]/40"
                    >
                      {/* Claim ID */}
                      <td className="px-6 py-4">
                        <Link
                          to="/claims/$claimId"
                          params={{ claimId: claim.id }}
                          className="font-mono font-bold text-[#3B82F6] hover:underline"
                        >
                          {claim.id}
                        </Link>
                        <p className="text-[10px] text-[#9CA3AF]">{claim.stage}</p>
                      </td>

                      {/* Patient / Hospital */}
                      <td className="px-6 py-4">
                        <p className="font-semibold text-white">{claim.patientName}</p>
                        <p className="text-[11px] text-[#06B6D4]">{claim.hospital}</p>
                      </td>

                      {/* Policy Number */}
                      <td className="px-6 py-4 font-mono text-[#9CA3AF]">
                        {claim.policyNumber}
                      </td>

                      {/* Claimed Amount */}
                      <td className="px-6 py-4 font-mono font-bold text-white">
                        {formatINR(claim.claimedAmount)}
                      </td>

                      {/* Status Badge */}
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold ${getStatusBadge(
                            claim.status
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
                          <span className="font-mono font-bold text-white">
                            {claim.readiness}%
                          </span>
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