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
import { formatINR } from "@/lib/claims";
import { fetchClaims } from "@/api/claims";
import { generateClaimPDFReport } from "@/api/integrations";
import { getCurrentUser } from "@/api/auth";
import type { ClaimApiData } from "@/api/claims";
import { useNavigate } from "@tanstack/react-router";

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
  const navigate = useNavigate();
  const currentUser = getCurrentUser();
  const isClaimant = currentUser?.role === "claimant";
  const [claims, setClaims] = useState<ClaimApiData[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  React.useEffect(() => {
    if (!currentUser) {
      navigate({ to: "/auth" });
      return;
    }
    let active = true;
    setLoading(true);
    fetchClaims()
      .then((data) => {
        if (active) setClaims(Array.isArray(data) ? data : []);
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(error instanceof Error ? error.message : "Unable to load claims.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [currentUser?.id, navigate]);

  const filtered = claims.filter((c) => {
    const matches =
      (c.patientName || "").toLowerCase().includes(search.toLowerCase()) ||
      (c.claimNumber || c.id).toLowerCase().includes(search.toLowerCase()) ||
      (c.policyNumber || "").toLowerCase().includes(search.toLowerCase()) ||
      (c.hospital || "").toLowerCase().includes(search.toLowerCase());
    if (statusFilter === "All") return matches;
    return matches && c.status === statusFilter;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Ready for Submission":
      case "Approved":
        return "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981]";
      case "Rejected":
        return "border-[#EF4444]/40 bg-[#EF4444]/10 text-[#EF4444]";
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
      title={isClaimant ? "My Claims" : "Organization Claims"}
      breadcrumbs={[{ label: "Dashboard", href: isClaimant ? "/claims" : "/" }, { label: "Claims" }]}
    >
      <div className="space-y-6">
        
        {/* HEADING & ACTIONS */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {isClaimant ? "My Claims" : "Authorized Claims"}
            </h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              {isClaimant
                ? "Track your submitted claims, outstanding actions, and recorded decisions."
                : "Claims returned by the backend for your authorized TPA organization only."}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {!isClaimant && (
              <button
                onClick={() => generateClaimPDFReport("AUTHORIZED-TPA-CLAIMS")}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] px-4 text-xs font-semibold text-slate-700 dark:text-white hover:border-[#3B82F6]"
              >
                <Download className="size-4 text-[#3B82F6]" />
                Export Authorized Claims
              </button>
            )}
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
                {loadError ? (
                  <tr><td colSpan={7} className="py-10 text-center text-sm text-rose-500">{loadError}</td></tr>
                ) : loading ? (
                  <tr><td colSpan={7} className="py-10 text-center text-sm text-slate-500">Loading authorized claims…</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={7} className="py-10 text-center text-sm text-slate-500">
                    {isClaimant ? "No claims have been submitted for your account yet." : "No claims are available in your authorized scope."}
                  </td></tr>
                ) : filtered.map((claim) => (
                  <tr key={claim.id} className="transition hover:bg-slate-50 dark:hover:bg-[#1F2937]/40">
                    <td className="px-6 py-4">
                      <Link
                        to="/claims/$claimId"
                        params={{ claimId: claim.id }}
                        className="font-mono font-bold text-[#3B82F6] hover:underline"
                      >
                        {claim.claimNumber || claim.id}
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
                          {claim.readiness == null ? "Not assessed" : `${claim.readiness}%`}
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
