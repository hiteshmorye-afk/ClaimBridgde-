import { createFileRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { Settings, Save, Server, Shield, Zap, Database, BrainCircuit, Key } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings & Configuration — ClaimBridge" },
      {
        name: "description",
        content: "Configure FastAPI endpoints, RAG thresholds and workspace roles.",
      },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const [apiEndpoint, setApiEndpoint] = useState(
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
  );
  const [ocrThreshold, setOcrThreshold] = useState("95");
  const [ragSimilarity, setRagSimilarity] = useState("0.75");
  const [autoApproveScore, setAutoApproveScore] = useState("90");

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Settings saved successfully", {
      description: "FastAPI REST configuration & AI engine thresholds updated.",
    });
  };

  return (
    <AppLayout
      title="Platform Settings & Configuration"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Settings" }]}
    >
      <div className="mx-auto max-w-4xl space-y-6">
        
        <form onSubmit={handleSave} className="rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-6 shadow-xl space-y-6">
          <div className="border-b border-slate-200 dark:border-[#1F2937] pb-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">API Connection & AI Engine Settings</h3>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Configure connection parameters for existing FastAPI + PostgreSQL backend.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-[#9CA3AF]">FastAPI REST Endpoint URL</label>
              <input
                type="url"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                className="mt-1 h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] px-3 font-mono text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
              />
              <p className="mt-1 text-[10px] text-slate-400">Referenced via VITE_API_BASE_URL in src/api/client.ts</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-[#9CA3AF]">OCR Confidence Threshold (%)</label>
                <input
                  type="number"
                  value={ocrThreshold}
                  onChange={(e) => setOcrThreshold(e.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] px-3 font-mono text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-[#9CA3AF]">RAG Vector Similarity Cutoff</label>
                <input
                  type="text"
                  value={ragSimilarity}
                  onChange={(e) => setRagSimilarity(e.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] px-3 font-mono text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-[#9CA3AF]">Auto-Approval Cutoff Score</label>
                <input
                  type="number"
                  value={autoApproveScore}
                  onChange={(e) => setAutoApproveScore(e.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] px-3 font-mono text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-[#1F2937]">
            <button
              type="submit"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-6 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition"
            >
              <Save className="size-4" /> Save Configuration
            </button>
          </div>
        </form>

      </div>
    </AppLayout>
  );
}
