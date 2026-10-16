import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useEffect, useState } from "react";
import { BarChart3, Clock3, FileText, ShieldCheck } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppLayout } from "@/components/layout/AppLayout";
import { getCurrentUser } from "@/api/auth";
import { ClaimsAnalyticsData, fetchClaimsAnalytics } from "@/api/claims";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Portfolio Analytics — ClaimBridge" },
      {
        name: "description",
        content:
          "Organization-scoped claim volumes, decisions, discrepancies and readiness trends.",
      },
    ],
  }),
  component: AnalyticsPage,
});

function AnalyticsPage() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState<ClaimsAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      navigate({ to: "/auth" });
      return;
    }
    if (user.role === "claimant") {
      navigate({ to: "/claims" });
      return;
    }
    if (user.role !== "claims_officer") {
      navigate({ to: "/auth" });
      return;
    }

    let active = true;
    fetchClaimsAnalytics()
      .then((result) => {
        if (active) setAnalytics(result);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load authorized analytics.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [navigate]);

  const decisionData = Object.entries(analytics?.decisionDistribution || {}).map(
    ([status, count]) => ({ status, count }),
  );
  const discrepancyData = analytics?.commonDiscrepancies || [];

  return (
    <AppLayout
      title="Organization-Scoped Analytics"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Analytics" }]}
    >
      <div className="space-y-8">
        <header>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">
            Claims Analytics
          </h1>
          <p className="mt-1 text-xs text-slate-500 dark:text-[#9CA3AF]">
            Values are calculated from persisted claims and review events in your authorized TPA
            scope.
          </p>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300"
          >
            {error}
          </div>
        )}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: "Authorized Claims",
              value: analytics?.totalClaims,
              icon: FileText,
            },
            {
              label: "Pending Review",
              value: analytics?.pendingReview,
              icon: ShieldCheck,
            },
            {
              label: "Average Processing Time",
              value:
                analytics?.averageProcessingTimeDays == null
                  ? "Not available"
                  : `${analytics.averageProcessingTimeDays} days`,
              icon: Clock3,
            },
            {
              label: "Decision Outcomes",
              value: analytics ? analytics.approved + analytics.rejected : undefined,
              icon: BarChart3,
            },
          ].map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-[#1F2937] dark:bg-[#111827]"
            >
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-[#9CA3AF]">
                  {label}
                </p>
                <p className="mt-2 font-mono text-2xl font-bold text-slate-900 dark:text-white">
                  {loading ? "…" : (value ?? "—")}
                </p>
              </div>
              <Icon className="size-5 text-primary" />
            </div>
          ))}
        </section>

        {loading ? (
          <div className="rounded-2xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
            Loading authorized analytics…
          </div>
        ) : analytics ? (
          <section className="grid gap-6 lg:grid-cols-2">
            <ChartPanel
              title="Readiness Trend"
              description="Recorded average readiness; it is not an approval probability."
            >
              {analytics.readinessTrends.length === 0 ? (
                <EmptyChart message="No persisted readiness trend data is available." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={analytics.readinessTrends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis dataKey="month" stroke="#9CA3AF" />
                    <YAxis yAxisId="readiness" domain={[0, 100]} stroke="#9CA3AF" />
                    <YAxis
                      yAxisId="processed"
                      orientation="right"
                      allowDecimals={false}
                      stroke="#9CA3AF"
                    />
                    <Tooltip />
                    <Area
                      type="monotone"
                      yAxisId="readiness"
                      dataKey="averageReadiness"
                      stroke="#06B6D4"
                      fill="#06B6D4"
                      fillOpacity={0.2}
                      name="Average readiness"
                    />
                    <Area
                      type="monotone"
                      yAxisId="processed"
                      dataKey="processedClaims"
                      stroke="#8B5CF6"
                      fill="#8B5CF6"
                      fillOpacity={0.15}
                      name="Processed claims"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </ChartPanel>

            <ChartPanel
              title="Recorded Decision Distribution"
              description="Current authorized-scope outcomes from claim records."
            >
              {decisionData.length === 0 ? (
                <EmptyChart message="No decision distribution data is available." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={decisionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis dataKey="status" stroke="#9CA3AF" />
                    <YAxis allowDecimals={false} stroke="#9CA3AF" />
                    <Tooltip />
                    <Bar dataKey="count" fill="#10B981" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartPanel>

            <ChartPanel
              title="Common Discrepancies"
              description="Counts from persisted validation findings in the authorized scope."
            >
              {discrepancyData.length === 0 ? (
                <EmptyChart message="No persisted discrepancy data is available." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={discrepancyData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis type="number" allowDecimals={false} stroke="#9CA3AF" />
                    <YAxis type="category" dataKey="category" width={150} stroke="#9CA3AF" />
                    <Tooltip />
                    <Bar dataKey="count" fill="#F59E0B" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartPanel>
          </section>
        ) : null}
      </div>
    </AppLayout>
  );
}

function ChartPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-[#1F2937] dark:bg-[#111827]">
      <h2 className="text-base font-bold text-slate-900 dark:text-white">{title}</h2>
      <p className="mb-4 text-xs text-slate-500 dark:text-[#9CA3AF]">{description}</p>
      <div className="h-72 w-full">{children}</div>
    </article>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
      {message}
    </div>
  );
}
