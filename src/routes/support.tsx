import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useEffect } from "react";
import { LifeBuoy, FileText, AlertTriangle, CheckCircle2, MessageSquareText } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { getCurrentUser } from "@/api/auth";

export const Route = createFileRoute("/support")({
  head: () => ({
    meta: [
      { title: "Help & Support — ClaimBridge" },
      { name: "description", content: "Support guidance and issue triage for ClaimBridge users." },
    ],
  }),
  component: SupportPage,
});

function SupportPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      navigate({ to: "/auth" });
    }
  }, [navigate]);

  const user = getCurrentUser();

  if (!user) {
    return null;
  }

  const sections = [
    {
      icon: FileText,
      title: "Check existing claim details",
      description: "Review claim status, supporting documents, and policy readiness in the current workflow.",
    },
    {
      icon: AlertTriangle,
      title: "Resolve missing-document alerts",
      description: "Upload the required files before continuing. Missing evidence is surfaced in the claim intake and review flow.",
    },
    {
      icon: CheckCircle2,
      title: "Confirm approval or decision updates",
      description: "Use your claim records and review queue to verify any approval, query, or rejection updates.",
    },
  ];

  return (
    <AppLayout title="Help & Support" breadcrumbs={[{ label: "Dashboard", href: "/claims" }, { label: "Support" }]}>
      <div className="mx-auto max-w-4xl space-y-6">
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <LifeBuoy className="size-6" />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Support center</p>
              <h1 className="text-2xl font-extrabold text-foreground">How can we help?</h1>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {sections.map(({ icon: Icon, title, description }) => (
            <div key={title} className="rounded-2xl border border-border bg-card p-5 shadow-sm">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon className="size-5" />
              </div>
              <h2 className="mt-4 text-sm font-bold text-foreground">{title}</h2>
              <p className="mt-2 text-xs text-muted-foreground">{description}</p>
            </div>
          ))}
        </section>

        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <MessageSquareText className="size-5 text-primary" />
            <h2 className="text-base font-bold text-foreground">Need help with a specific claim?</h2>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Start from your active claim record or the review queue for the exact workflow you are following. This application does not provide external support contacts or mock service channels.
          </p>
        </section>
      </div>
    </AppLayout>
  );
}
