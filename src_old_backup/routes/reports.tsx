import { createFileRoute } from "@tanstack/react-router";
import React from "react";
import { FileCheck, Download, Printer, Share2, Sparkles, FileText } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { generateClaimPDFReport } from "@/api/integrations";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports & Audit Trail — ClaimBridge" },
      {
        name: "description",
        content: "Pre-submission audit reports and executive verification summaries.",
      },
    ],
  }),
  component: ReportsPage,
});

const sampleReports = [
  { id: "REP-2026-09", title: "Monthly Claim Readiness & OCR Accuracy Audit", date: "Sep 2026", format: "PDF", size: "4.8 MB" },
  { id: "REP-2026-08", title: "Pre-Authorization Discrepancy & Exclusion Summary", date: "Aug 2026", format: "PDF", size: "3.2 MB" },
  { id: "REP-2026-07", title: "ICD-10/CPT Medical Necessity Reconciliation Report", date: "Jul 2026", format: "PDF", size: "5.1 MB" },
];

function ReportsPage() {
  return (
    <AppLayout
      title="Audit Trail & Reports"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Reports" }]}
    >
      <div className="space-y-6">
        
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">Audit Reports Directory</h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Download compiled pre-submission verification trail reports and PDF summaries.
            </p>
          </div>

          <button
            onClick={() => generateClaimPDFReport("EXEC-SUMMARY")}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-5 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition"
          >
            <Download className="size-4" /> Generate New Audit Report
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {sampleReports.map((rep) => (
            <div
              key={rep.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-5 shadow-lg space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-[#9CA3AF]">
                  <span className="font-mono text-[#06B6D4]">{rep.id}</span>
                  <span>{rep.date}</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">{rep.title}</h4>
              </div>

              <div className="flex items-center justify-between border-t border-slate-200 dark:border-[#1F2937] pt-3 text-xs">
                <span className="font-mono text-slate-500 dark:text-[#9CA3AF]">{rep.size} · {rep.format}</span>
                <button
                  onClick={() => generateClaimPDFReport(rep.id)}
                  className="inline-flex items-center gap-1 font-semibold text-[#3B82F6] hover:underline"
                >
                  <Download className="size-3.5" /> Download
                </button>
              </div>
            </div>
          ))}
        </div>

      </div>
    </AppLayout>
  );
}
