import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Check, Upload } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { addClaim, DOC_CATEGORIES, type DocCategory } from "@/lib/claims";
import { BrandLockup } from "@/components/claim-ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/claims/new")({
  head: () => ({
    meta: [
      { title: "Create New Claim — ClaimBridge" },
      {
        name: "description",
        content:
          "Enter patient and policy details and upload claim documents to start insurance claim verification.",
      },
      { property: "og:title", content: "Create New Claim — ClaimBridge" },
      {
        property: "og:description",
        content: "Start a new insurance claim verification with patient, policy and document details.",
      },
    ],
  }),
  component: NewClaim,
});

type Uploaded = Partial<Record<DocCategory, string>>;

function NewClaim() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [uploads, setUploads] = useState<Uploaded>({});
  const pending = useRef<DocCategory | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    patientName: "",
    patientAge: "",
    policyNumber: "",
    insuranceProvider: "",
    admissionDate: "",
    dischargeDate: "",
    diagnosis: "",
    claimedAmount: "",
  });

  useEffect(() => {
    if (!loading && !user) navigate({ to: "/auth" });
  }, [loading, user, navigate]);

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function continueToDocuments() {
    if (!form.patientName.trim() || !form.policyNumber.trim() || !form.insuranceProvider.trim()) {
      toast.error("Patient name, policy number and insurance provider are required.");
      return;
    }
    setStep(2);
  }

  function submit() {
    const uploaded = Object.entries(uploads).map(([category, fileName]) => ({
      category: category as DocCategory,
      fileName: fileName as string,
    }));
    if (uploaded.length === 0) {
      toast.error("Upload at least one claim document.");
      return;
    }
    const created = addClaim({
      patientName: form.patientName.trim(),
      patientAge: Number(form.patientAge) || 0,
      policyNumber: form.policyNumber.trim(),
      insuranceProvider: form.insuranceProvider.trim(),
      admissionDate: form.admissionDate,
      dischargeDate: form.dischargeDate,
      diagnosis: form.diagnosis.trim(),
      claimedAmount: Number(form.claimedAmount) || 0,
      documents: uploaded,
    });
    toast.success(`${created.id} created and queued for verification`);
    navigate({ to: "/claims/$claimId", params: { claimId: created.id } });
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <BrandLockup to="/" />
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/" })}>
            <ArrowLeft className="size-4" /> Back to dashboard
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="font-display text-2xl font-semibold">Create new claim</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Verify, validate and prepare insurance claims before submission.
        </p>

        <ol className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {["Patient & Policy Details", "Upload Claim Documents"].map((label, i) => {
            const active = step === i + 1;
            const done = step > i + 1;
            return (
              <li key={label} className="flex items-center gap-2">
                <span
                  className={`flex size-6 items-center justify-center rounded-full border text-xs font-medium ${
                    active || done
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  {done ? <Check className="size-3" /> : i + 1}
                </span>
                <span className={active ? "font-medium" : "text-muted-foreground"}>{label}</span>
              </li>
            );
          })}
        </ol>

        {step === 1 ? (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-base">Patient & policy details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field label="Patient name">
                <Input value={form.patientName} onChange={(e) => set("patientName", e.target.value)} placeholder="e.g. Ananya Sharma" />
              </Field>
              <Field label="Age">
                <Input type="number" value={form.patientAge} onChange={(e) => set("patientAge", e.target.value)} placeholder="41" />
              </Field>
              <Field label="Policy number">
                <Input value={form.policyNumber} onChange={(e) => set("policyNumber", e.target.value)} placeholder="POL-88213-A" />
              </Field>
              <Field label="Insurance provider">
                <Input value={form.insuranceProvider} onChange={(e) => set("insuranceProvider", e.target.value)} placeholder="Star Health" />
              </Field>
              <Field label="Admission date">
                <Input type="date" value={form.admissionDate} onChange={(e) => set("admissionDate", e.target.value)} />
              </Field>
              <Field label="Discharge date">
                <Input type="date" value={form.dischargeDate} onChange={(e) => set("dischargeDate", e.target.value)} />
              </Field>
              <Field label="Claimed amount (₹)">
                <Input type="number" value={form.claimedAmount} onChange={(e) => set("claimedAmount", e.target.value)} placeholder="184500" />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Diagnosis / procedure">
                  <Textarea
                    rows={2}
                    value={form.diagnosis}
                    onChange={(e) => set("diagnosis", e.target.value)}
                    placeholder="Acute appendicitis — laparoscopic appendectomy"
                  />
                </Field>
              </div>
              <div className="sm:col-span-2 flex justify-end">
                <Button onClick={continueToDocuments}>Continue to documents</Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-base">Upload claim documents</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  const category = pending.current;
                  if (file && category) setUploads((u) => ({ ...u, [category]: file.name }));
                  if (fileRef.current) fileRef.current.value = "";
                }}
              />
              {DOC_CATEGORIES.map((category) => (
                <div
                  key={category}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{category}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {uploads[category] ?? "No file selected"}
                    </p>
                  </div>
                  <Button
                    variant={uploads[category] ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => {
                      pending.current = category;
                      fileRef.current?.click();
                    }}
                  >
                    {uploads[category] ? <Check className="size-4" /> : <Upload className="size-4" />}
                    {uploads[category] ? "Replace" : "Upload"}
                  </Button>
                </div>
              ))}
              <div className="flex justify-between pt-2">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button onClick={submit}>Start verification</Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}