import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useEffect } from "react";
import { FileText } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { getCurrentUser } from "@/api/auth";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports & Audit Trail — ClaimBridge" },
      {
        name: "description",
        content:
          "Generated reports will appear here when a persisted report workflow is available.",
      },
    ],
  }),
  component: ReportsPage,
});

function ReportsPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      navigate({ to: "/auth" });
    } else if (user.role === "claimant") {
      navigate({ to: "/claims" });
    } else if (user.role !== "claims_officer") {
      navigate({ to: "/auth" });
    }
  }, [navigate]);

  return (
    <AppLayout
      title="Audit Reports"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Reports" }]}
    >
      <section className="mx-auto max-w-2xl rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
        <FileText className="mx-auto size-8 text-muted-foreground" />
        <h1 className="mt-4 text-lg font-bold text-foreground">No generated reports</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This workspace does not yet have a persisted report-generation service. No sample or
          synthetic report records are shown.
        </p>
      </section>
    </AppLayout>
  );
}
