import { createFileRoute, Link } from "@tanstack/react-router";
import React, { useState } from "react";
import {
  FileSpreadsheet,
  Search,
  Plus,
  ArrowRight,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Download,
  Building2,
  FileCheck,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useClaims, formatINR, syncClaimsFromBackend } from "@/lib/claims";
import { fetchClaims } from "@/api/claims";
import { generateClaimPDFReport } from "@/api/integrations";

export const Route = createFileRoute("/claims/")({
  head: () => ({
    meta: [
      { title: "All Claims — ClaimBridge Operations" },
      {
        name: "description",
        content: "View, filter and manage all active insurance claims in the ClaimBridge pipeline.",
      },
    ],
  }),
  component: ClaimsIndexPage,
});

function ClaimsIndexPage() {
  const claims = useClaims();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  React.useEffect(() => {
    fetchClaims()
      .then((data) => {
        if (data && Array.isArray(data)) {
          syncClaimsFromBackend(data);
        }
      })
      .catch(() => {});
  }, []);

  const filtered = claims.filter((c) => {
    const matches =
      c.patientName.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase()) ||
      c.policyNumber.toLowerCase().includes(search.toLowerCase()) ||
      c.hospital.toLowerCase().includes(search.toLowerCase());
    if (statusFilter === "All") return matches;
    return matches && c.status === statusFilter;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Ready for Submission":
      case "Approved":
        return "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981]";
      case "Needs Review":
        return "border-[#F59E0B]/40 bg-[#F59E0B]/10 text-[#F59E0B]";
      case "Under Analysis":
        return "border-[#3B82F6]/40 bg-[#3B82F6]/10 text-[#3B82F6]";
      default:
        return "border-slate-700 bg-slate-800 text-slate-300";
    }
  };

  return (
    <AppLayout
      title="Claims Portfolio"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Claims" }]}
    >
      <div className="space-y-6">
        
        {/* HEADING & ACTIONS */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">Active Claims Directory</h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Comprehensive portfolio management for all intake, verified & pending review claims.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => generateClaimPDFReport("ALL-CLAIMS")}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] px-4 text-xs font-semibold text-slate-700 dark:text-white hover:border-[#3B82F6]"
            >
              <Download className="size-4 text-[#3B82F6]" />
              Export Portfolio
            </button>

            <Link
              to="/claims/new"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-4 text-xs font-semibold text-white shadow-md shadow-[#3B82F6]/30"
            >
              <Plus className="size-4" />
              New Claim
            </Link>
          </div>
        </div>

        {/* SEARCH & FILTERS */}
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search claim ID, patient, hospital..."
              className="h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] pl-9 pr-3 text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
            />
          </div>

          <div className="flex flex-wrap gap-1.5 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-100 dark:bg-[#0B0F17] p-1">
            {["All", "Ready for Submission", "Needs Review", "Under Analysis"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  statusFilter === st
                    ? "bg-[#3B82F6] text-white shadow-sm"
                    : "text-slate-600 dark:text-[#9CA3AF] hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* CLAIMS TABLE */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 dark:bg-[#0E1420] text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-[#9CA3AF]">
                <tr className="border-b border-slate-200 dark:border-[#1F2937]">
                  <th className="px-6 py-3.5">Claim ID & Stage</th>
                  <th className="px-6 py-3.5">Patient & Provider</th>
                  <th className="px-6 py-3.5">Policy Number</th>
                  <th className="px-6 py-3.5">Claimed Amount</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Readiness Score</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#1F2937] text-xs">
                {filtered.map((claim) => (
                  <tr key={claim.id} className="transition hover:bg-slate-50 dark:hover:bg-[#1F2937]/40">
                    <td className="px-6 py-4">
                      <Link
                        to="/claims/$claimId"
                        params={{ claimId: claim.id }}
                        className="font-mono font-bold text-[#3B82F6] hover:underline"
                      >
                        {claim.id}
                      </Link>
                      <p className="text-[10px] text-slate-500 dark:text-[#9CA3AF]">{claim.stage}</p>
                    </td>

                    <td className="px-6 py-4">
                      <p className="font-semibold text-slate-900 dark:text-white">{claim.patientName}</p>
                      <p className="text-[11px] text-[#06B6D4]">{claim.hospital}</p>
                    </td>

                    <td className="px-6 py-4 font-mono text-slate-600 dark:text-[#9CA3AF]">
                      {claim.policyNumber}
                    </td>

                    <td className="px-6 py-4 font-mono font-bold text-slate-900 dark:text-white">
                      {formatINR(claim.claimedAmount)}
                    </td>

                    <td className="px-6 py-4">
                      <span className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-semibold ${getStatusBadge(claim.status)}`}>
                        {claim.status}
                      </span>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-100 dark:bg-[#1F2937]">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-[#3B82F6] to-[#06B6D4]"
                            style={{ width: `${claim.readiness}%` }}
                          />
                        </div>
                        <span className="font-mono font-bold text-slate-900 dark:text-white">
                          {claim.readiness}%
                        </span>
                      </div>
                    </td>

                    <td className="px-6 py-4 text-right">
                      <Link
                        to="/claims/$claimId"
                        params={{ claimId: claim.id }}
                        className="inline-flex size-8 items-center justify-center rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#111827] text-slate-600 dark:text-[#9CA3AF] hover:text-[#3B82F6]"
                      >
                        <ArrowRight className="size-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </AppLayout>
  );
}
