import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useEffect } from "react";
import { CircleUserRound, Mail, ShieldCheck, Building2, Phone, ArrowRight } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { getCurrentUser } from "@/api/auth";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "My Profile — ClaimBridge" },
      { name: "description", content: "Patient and team profile information for the authenticated ClaimBridge user." },
    ],
  }),
  component: ProfilePage,
});

function ProfilePage() {
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

  return (
    <AppLayout title="My Profile" breadcrumbs={[{ label: "Dashboard", href: "/claims" }, { label: "Profile" }]}>
      <div className="mx-auto max-w-3xl space-y-6">
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <CircleUserRound className="size-7" />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Authenticated account</p>
              <h1 className="text-2xl font-extrabold text-foreground">{user.name}</h1>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Mail className="size-4 text-primary" />
              Email
            </div>
            <p className="text-sm font-medium text-foreground">{user.email}</p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Phone className="size-4 text-primary" />
              Phone
            </div>
            <p className="text-sm font-medium text-foreground">{user.phone || "Not provided"}</p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <ShieldCheck className="size-4 text-primary" />
              Role
            </div>
            <p className="text-sm font-medium text-foreground">{user.canonical_role || user.role}</p>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Building2 className="size-4 text-primary" />
              Organization
            </div>
            <p className="text-sm font-medium text-foreground">{user.organization || "Not assigned"}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm text-muted-foreground">
            Profile updates and account management remain handled through the existing secure settings workflow.
          </p>
          <button
            type="button"
            onClick={() => navigate({ to: "/settings" })}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground"
          >
            Open Account Settings <ArrowRight className="size-4" />
          </button>
        </section>
      </div>
    </AppLayout>
  );
}
