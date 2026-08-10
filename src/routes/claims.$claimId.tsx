import { createFileRoute, useNavigate, useParams } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft, Check, CircleDashed, FileText, Loader2 } from "lucide-react";

import { BrandLockup, ReadinessScore, StatusBadge } from "@/components/claim-ui";
import { formatDate, formatINR, getClaim, PIPELINE_STAGES, useClaims } from "@/lib/claims";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/claims/$claimId")({
  head: () => ({
    meta: [
      { title: "Claim Verification — ClaimBridge" },
      {
        name: "description",
        content:
          "Review document checks, policy verification, cross-document validation and the claim readiness score.",
      },
      { property: "og:title", content: "Claim Verification — ClaimBridge" },
      {
        property: "og:description",
        content: "Full verification trail and readiness score for an insurance claim.",
      },
    ],
  }),
  component: ClaimDetail,
});

const docStatusStyles: Record<string, string> = {
  Verified: "text-success",
  Processing: "text-primary",
  Missing: "text-muted-foreground",
  Mismatch: "text-destructive",
};

function ClaimDetail() {
  const { claimId } = useParams({ from: "/claims/$claimId" });
  const navigate = useNavigate();
  useClaims();
  const claim = getClaim(claimId);

  if (!claim) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3">
        <p className="text-sm text-muted-foreground">Claim {claimId} was not found.</p>
        <Button onClick={() => navigate({ to: "/" })}>Back to dashboard</Button>
      </div>
    );
  }

  const currentStage = PIPELINE_STAGES.indexOf(claim.stage);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <BrandLockup to="/" />
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/" })}>
            <ArrowLeft className="size-4" /> Back to dashboard
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
              {claim.id}
            </p>
            <h1 className="mt-1 font-display text-2xl font-semibold">{claim.patientName}</h1>
            <p className="text-sm text-muted-foreground">{claim.diagnosis}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <StatusBadge status={claim.status} />
            <ReadinessScore value={claim.readiness} />
          </div>
        </div>

        <Card className="mt-6">
          <CardContent className="grid gap-5 p-5 sm:grid-cols-2 lg:grid-cols-4">
            <Detail label="Policy number" value={claim.policyNumber} />
            <Detail label="Insurance provider" value={claim.insuranceProvider} />
            <Detail label="Admission" value={formatDate(claim.admissionDate)} />
            <Detail label="Discharge" value={formatDate(claim.dischargeDate)} />
            <Detail label="Patient age" value={claim.patientAge ? `${claim.patientAge} yrs` : "—"} />
            <Detail label="Claimed amount" value={formatINR(claim.claimedAmount)} />
            <Detail label="Current stage" value={claim.stage} />
            <Detail label="Readiness score" value={`${claim.readiness}%`} />
          </CardContent>
        </Card>

        <div className="mt-6 grid gap-6 lg:grid-cols-[20rem_1fr]">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Verification workflow</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {PIPELINE_STAGES.map((stage, i) => {
                const done = i < currentStage;
                const active = i === currentStage;
                return (
                  <div key={stage} className="flex items-center gap-3 text-sm">
                    <span
                      className={`flex size-5 shrink-0 items-center justify-center rounded-full border ${
                        done
                          ? "border-success bg-success text-success-foreground"
                          : active
                            ? "border-primary text-primary"
                            : "border-border text-muted-foreground"
                      }`}
                    >
                      {done ? (
                        <Check className="size-3" />
                      ) : active ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : (
                        <CircleDashed className="size-3" />
                      )}
                    </span>
                    <span className={active ? "font-medium" : done ? "" : "text-muted-foreground"}>
                      {stage}
                    </span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Claim documents</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {claim.documents.map((doc) => (
                  <div
                    key={doc.category}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <FileText className="size-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{doc.category}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {doc.fileName}
                          {doc.note ? ` · ${doc.note}` : ""}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs font-medium ${docStatusStyles[doc.status] ?? "text-muted-foreground"}`}
                    >
                      {doc.status}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Verification findings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {claim.findings.map((f) => (
                  <div key={f.label} className="flex items-start gap-3 text-sm">
                    {f.severity === "ok" ? (
                      <Check className="mt-0.5 size-4 shrink-0 text-success" />
                    ) : (
                      <AlertTriangle
                        className={`mt-0.5 size-4 shrink-0 ${
                          f.severity === "error" ? "text-destructive" : "text-warning"
                        }`}
                      />
                    )}
                    <div>
                      <p className="font-medium">{f.label}</p>
                      <p className="text-muted-foreground">{f.detail}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Final report</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  {claim.status === "Ready for Submission"
                    ? "All required documents are verified and consistent with the policy. This claim can be submitted to the insurer."
                    : claim.status === "Needs Review"
                      ? "Discrepancies were found during validation. Resolve the findings above before submitting this claim."
                      : "Verification is still in progress. The report will be available once all checks complete."}
                </p>
                <Button disabled={claim.status !== "Ready for Submission"}>
                  Download final report
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}