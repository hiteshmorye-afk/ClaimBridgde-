import { createFileRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { UserCheck, Search, Filter, ShieldAlert, CheckCircle2 } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { HumanReviewTriage } from "@/components/pipeline/HumanReviewTriage";
import { useClaims, getClaim, syncClaimsFromBackend } from "@/lib/claims";
import { fetchClaims } from "@/api/claims";

export const Route = createFileRoute("/review")({
  head: () => ({
    meta: [
      { title: "Human Review Triage Desk — ClaimBridge" },
      {
        name: "description",
        content: "Human review triage workspace for claims requiring reviewer attention.",
      },
    ],
  }),
  component: HumanReviewPage,
});

function HumanReviewPage() {
  const claims = useClaims();

  React.useEffect(() => {
    fetchClaims()
      .then((data) => {
        if (data && Array.isArray(data)) {
          syncClaimsFromBackend(data);
        }
      })
      .catch(() => {});
  }, []);

  const reviewClaims = claims.filter((c) => c.status === "Needs Review" || c.readiness < 90 || c.status === "Under Analysis");
  const [selectedClaimId, setSelectedClaimId] = useState(reviewClaims[0]?.id || claims[0]?.id || "CLM-TEST-001");

  const currentClaim = getClaim(selectedClaimId) || claims[0];

  return (
    <AppLayout
      title="Human Review & Triage Desk"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Human Review" }]}
    >
      <div className="space-y-6">
        
        {/* SELECTOR BAR */}
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <UserCheck className="size-5 text-[#F59E0B]" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                Pending Triage Queue ({reviewClaims.length} Claims)
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-[#9CA3AF]">
                Select a claim from the queue to perform document & policy triage
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {reviewClaims.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedClaimId(c.id)}
                className={`rounded-xl px-3 py-1.5 text-xs font-mono font-semibold transition ${
                  selectedClaimId === c.id
                    ? "bg-[#3B82F6] text-white shadow-md"
                    : "border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] text-slate-700 dark:text-[#9CA3AF]"
                }`}
              >
                {c.id} ({c.readiness}%)
              </button>
            ))}
          </div>
        </div>

        {/* 3-COLUMN TRIAGE DESK */}
        {currentClaim && <HumanReviewTriage claim={currentClaim} />}

      </div>
    </AppLayout>
  );
}
