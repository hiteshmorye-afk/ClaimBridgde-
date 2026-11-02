import { createFileRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { Settings, Save, Server, Shield, Zap, Database, BrainCircuit, Key, Users } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { AdminUserManagement } from "@/components/admin/AdminUserManagement";
import { getCurrentUser } from "@/api/auth";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings & Configuration — ClaimBridge" },
      {
        name: "description",
        content: "Configure FastAPI endpoints, RAG thresholds, workspace roles, and user governance.",
      },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const currentUser = getCurrentUser();
  const isAdmin = currentUser?.role === "admin";
  const [activeSection, setActiveSection] = useState<"settings" | "users">(isAdmin ? "users" : "settings");

  const [apiEndpoint, setApiEndpoint] = useState(
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
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
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Navigation Tabs */}
        <div className="flex border-b border-border space-x-2">
          <button
            type="button"
            onClick={() => setActiveSection("settings")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
              activeSection === "settings"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Settings className="w-4 h-4" />
            AI & System Parameters
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("users")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
              activeSection === "users"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Users className="w-4 h-4" />
            User & Organization Governance
            {isAdmin && (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-400">
                Admin
              </span>
            )}
          </button>
        </div>

        {activeSection === "users" ? (
          <AdminUserManagement />
        ) : (
          <form
            onSubmit={handleSave}
            className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-6"
          >
            <div className="border-b border-border pb-4">
              <h3 className="text-base font-bold text-foreground">API Connection & AI Engine Settings</h3>
              <p className="text-xs text-muted-foreground">
                Configure connection parameters for existing FastAPI + PostgreSQL backend.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-foreground">FastAPI REST Endpoint URL</label>
                <input
                  type="url"
                  value={apiEndpoint}
                  onChange={(e) => setApiEndpoint(e.target.value)}
                  className="mt-1 h-10 w-full rounded-xl border border-border bg-secondary px-3 font-mono text-xs text-foreground outline-none focus:border-primary"
                />
                <p className="mt-1 text-[10px] text-muted-foreground">
                  Referenced via VITE_API_BASE_URL in src/api/client.ts
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="text-xs font-semibold text-foreground">OCR Confidence Threshold (%)</label>
                  <input
                    type="number"
                    value={ocrThreshold}
                    onChange={(e) => setOcrThreshold(e.target.value)}
                    className="mt-1 h-10 w-full rounded-xl border border-border bg-secondary px-3 font-mono text-xs text-foreground outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground">RAG Vector Similarity Cutoff</label>
                  <input
                    type="text"
                    value={ragSimilarity}
                    onChange={(e) => setRagSimilarity(e.target.value)}
                    className="mt-1 h-10 w-full rounded-xl border border-border bg-secondary px-3 font-mono text-xs text-foreground outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground">Auto-Approval Cutoff Score</label>
                  <input
                    type="number"
                    value={autoApproveScore}
                    onChange={(e) => setAutoApproveScore(e.target.value)}
                    className="mt-1 h-10 w-full rounded-xl border border-border bg-secondary px-3 font-mono text-xs text-foreground outline-none focus:border-primary"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-border">
              <button
                type="submit"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-xs font-bold text-primary-foreground shadow-sm hover:bg-primary/90 transition"
              >
                <Save className="size-4" /> Save Configuration
              </button>
            </div>
          </form>
        )}
      </div>
    </AppLayout>
  );
}
