import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2, LogOut, Plus, Search } from "lucide-react";

import { signOutDemoUser } from "@/hooks/useAuth";
import { useAuth } from "@/hooks/useAuth";
import { BrandLockup, ReadinessScore, StatusBadge } from "@/components/claim-ui";
import { formatDate, formatINR, useClaims, type ClaimStatus } from "@/lib/claims";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/index/backup")({
  head: () => ({
    meta: [
      { title: "ClaimBridge — Insurance Claim Verification Dashboard" },
      {
        name: "description",
        content:
          "Verify, validate and prepare insurance claims before submission. Track claim status, documents and readiness scores in one dashboard.",
      },
      { property: "og:title", content: "ClaimBridge — Intelligent Insurance Claim Verification" },
      {
        property: "og:description",
        content: "Verify, validate and prepare insurance claims before submission.",
      },
    ],
  }),
  component: Dashboard,
});

const FILTERS: ("All" | ClaimStatus)[] = [
  "All",
  "Under Analysis",
  "Ready for Submission",
  "Needs Review",
];

function Dashboard() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const claims = useClaims();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!loading && !user) navigate({ to: "/auth" });
  }, [loading, user, navigate]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const counts = {
    total: claims.length,
    analysis: claims.filter((c) => c.status === "Under Analysis").length,
    ready: claims.filter((c) => c.status === "Ready for Submission").length,
    review: claims.filter((c) => c.status === "Needs Review").length,
  };

  const q = query.trim().toLowerCase();
  const visible = claims.filter(
    (c) =>
      (filter === "All" || c.status === filter) &&
      (!q ||
        c.id.toLowerCase().includes(q) ||
        c.patientName.toLowerCase().includes(q) ||
        c.policyNumber.toLowerCase().includes(q) ||
        c.insuranceProvider.toLowerCase().includes(q)),
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <BrandLockup />
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight">Hospital Insurance Coordinator</p>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                signOutDemoUser();
                navigate({ to: "/auth" });
              }}
            >
              <LogOut className="size-4" /> Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold">Claims dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Verify, validate and prepare insurance claims before submission.
            </p>
          </div>
          <Button onClick={() => navigate({ to: "/claims/new" })}>
            <Plus className="size-4" /> Create New Claim
          </Button>
        </div>

        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Claims" value={counts.total} />
          <StatCard label="Claims Under Analysis" value={counts.analysis} />
          <StatCard label="Ready for Submission" value={counts.ready} tone="success" />
          <StatCard label="Needs Review" value={counts.review} tone="warning" />
        </section>

        <section className="mt-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    filter === f
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-card text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search claim ID, patient or policy"
                className="pl-9"
              />
            </div>
          </div>

          <div className="mt-4 overflow-x-auto rounded-lg border bg-card">
            <table className="w-full min-w-[60rem] text-sm">
              <thead className="border-b bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Claim ID</th>
                  <th className="px-4 py-3 font-medium">Patient</th>
                  <th className="px-4 py-3 font-medium">Policy Number</th>
                  <th className="px-4 py-3 font-medium">Insurance Provider</th>
                  <th className="px-4 py-3 font-medium">Claim Status</th>
                  <th className="px-4 py-3 font-medium">Readiness Score</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate({ to: "/claims/$claimId", params: { claimId: c.id } })}
                    className="cursor-pointer border-b last:border-0 transition-colors hover:bg-accent/40"
                  >
                    <td className="px-4 py-3 font-mono text-xs">{c.id}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{c.patientName}</p>
                      <p className="text-xs text-muted-foreground">
                        Admitted {formatDate(c.admissionDate)} · {formatINR(c.claimedAmount)}
                      </p>
                    </td>
                    <td className="px-4 py-3">{c.policyNumber}</td>
                    <td className="px-4 py-3">{c.insuranceProvider}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3">
                      <ReadinessScore value={c.readiness} />
                    </td>
                  </tr>
                ))}
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-muted-foreground">
                      No claims match this filter.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success" | "warning";
}) {
  const color =
    tone === "success" ? "text-success" : tone === "warning" ? "text-warning-foreground" : "";
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className={`mt-2 font-display text-3xl font-semibold tabular-nums ${color}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
