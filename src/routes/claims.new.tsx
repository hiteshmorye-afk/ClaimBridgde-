import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useState, useRef } from "react";
import { toast } from "sonner";
import { ArrowLeft, Upload, CheckCircle2, ShieldCheck, Sparkles, FileText, Zap } from "lucide-react";

import { AppLayout } from "@/components/layout/AppLayout";
import { addClaim, DOC_CATEGORIES, DocCategory, Claim } from "@/lib/claims";
import { createClaim } from "@/api/claims";

export const Route = createFileRoute("/claims/new")({
  head: () => ({
    meta: [
      { title: "Create New Claim — ClaimBridge Intake" },
      {
        name: "description",
        content: "Secure document intake & claim creation wizard for hospital coordinators.",
      },
    ],
  }),
  component: NewClaimPage,
});

export function NewClaimPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [uploads, setUploads] = useState<Partial<Record<DocCategory, string>>>({
    "Hospital Bill": "hospital_bill_scan_2026.pdf",
    "Discharge Summary": "discharge_summary_signed.pdf",
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentCategory, setCurrentCategory] = useState<DocCategory>("Hospital Bill");

  const [form, setForm] = useState({
    patientName: "David Miller",
    patientAge: "46",
    hospital: "Chong Hua Hospital",
    policyNumber: "POL-[#88921-X]",
    insuranceProvider: "Pacific Healthcare TPA",
    admissionDate: "2026-08-10",
    dischargeDate: "2026-08-14",
    diagnosis: "Acute Cholecystitis — Laparoscopic Cholecystectomy (ICD-10: K80.0)",
    claimedAmount: "145000",
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      setUploads((prev) => ({
        ...prev,
        [currentCategory]: file.name,
      }));
      toast.success(`Uploaded ${file.name} for ${currentCategory}`);
    }
  };

  const handleCreate = async () => {
    const claimId = `CLM-2026-${Math.floor(1000 + Math.random() * 9000)}`;

    const newClaim: Claim = {
      id: claimId,
      patientName: form.patientName,
      patientAge: Number(form.patientAge) || 45,
      hospital: form.hospital,
      policyNumber: form.policyNumber,
      insuranceProvider: form.insuranceProvider,
      admissionDate: form.admissionDate,
      dischargeDate: form.dischargeDate,
      diagnosis: form.diagnosis,
      claimedAmount: Number(form.claimedAmount) || 145000,
      status: "Under Analysis",
      stage: "03 OCR Extraction",
      readiness: 91.2,
      ocrConfidence: 98.5,
      classification: "Hospital Bill & Discharge Summary",
      medicalRiskScore: 25,
      medicalConfidence: 88,
      policyConfidence: 92.4,
      validationReadiness: 100,
      overallConfidence: 91.2,
      routeDecision: "Auto Approval Eligible",
      documents: Object.entries(uploads).map(([cat, fname]) => ({
        category: cat as DocCategory,
        fileName: fname as string,
        status: "Verified",
        fileSize: "1.8 MB",
      })),
      findings: [
        { label: "Document Intake Verified", detail: "2 files scanned and encrypted into intake pipeline.", severity: "ok" },
        { label: "OCR Processing Started", detail: "Line items extracted into key-value schema.", severity: "ok" },
      ],
      medicalServices: [
        { id: "S1", serviceName: "Laparoscopic Cholecystectomy", code: "CPT-47562", category: "Surgery", quantity: 1, unitCost: 95000, totalCost: 95000, coverageStatus: "Covered" },
        { id: "S2", serviceName: "Inpatient Care (4 Days)", code: "CPT-99232", category: "Room & Board", quantity: 4, unitCost: 12500, totalCost: 50000, coverageStatus: "Covered" },
      ],
      policyClauses: [
        { id: "P1", section: "Section 3.1", clauseTitle: "Surgical Coverage", textSnippet: "Surgical procedures 100% reimbursable.", status: "Verified", confidence: 95.0 },
      ],
      ocrLines: [
        { id: "O1", label: "TOTAL CHARGES", value: "145,000.00", confidence: 98.5, box: { x: 60, y: 80, w: 30, h: 5 } },
      ],
    };

    addClaim(newClaim);
    try {
      await createClaim(newClaim);
    } catch {
      // offline fallback
    }

    toast.success(`Claim ${claimId} successfully initialized`, {
      description: "AI extraction & verification pipeline triggered.",
    });

    navigate({ to: "/claims/$claimId", params: { claimId } });
  };

  return (
    <AppLayout
      title="Create New Insurance Claim"
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Claims", href: "/claims" },
        { label: "New Claim Intake" },
      ]}
    >
      <div className="mx-auto max-w-4xl space-y-6">
        
        {/* WIZARD STEPPER */}
        <div className="flex items-center justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-4">
          <div className={`flex items-center gap-3 ${step === 1 ? "text-[#3B82F6]" : "text-[#10B981]"}`}>
            <span className="flex size-7 items-center justify-center rounded-full bg-[#3B82F6]/20 font-mono text-xs font-bold">1</span>
            <span className="text-xs font-bold">1. Patient & Policy Details</span>
          </div>

          <div className="h-0.5 w-12 bg-[#1F2937]" />

          <div className={`flex items-center gap-3 ${step === 2 ? "text-[#3B82F6]" : "text-[#9CA3AF]"}`}>
            <span className="flex size-7 items-center justify-center rounded-full bg-[#1F2937] font-mono text-xs font-bold">2</span>
            <span className="text-xs font-bold">2. Document Intake & Upload</span>
          </div>
        </div>

        {/* STEP 1: PATIENT & POLICY FORM */}
        {step === 1 && (
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl space-y-6">
            <div className="border-b border-[#1F2937] pb-4">
              <h3 className="text-base font-bold text-white">Patient & Insurance Policy Information</h3>
              <p className="text-xs text-[#9CA3AF]">Input hospital record and policy identifier for AI verification</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Patient Full Name</label>
                <input
                  type="text"
                  value={form.patientName}
                  onChange={(e) => setForm({ ...form, patientName: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Patient Age (Years)</label>
                <input
                  type="number"
                  value={form.patientAge}
                  onChange={(e) => setForm({ ...form, patientAge: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Hospital / Provider Name</label>
                <input
                  type="text"
                  value={form.hospital}
                  onChange={(e) => setForm({ ...form, hospital: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Policy Number</label>
                <input
                  type="text"
                  value={form.policyNumber}
                  onChange={(e) => setForm({ ...form, policyNumber: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Insurance Provider / TPA</label>
                <input
                  type="text"
                  value={form.insuranceProvider}
                  onChange={(e) => setForm({ ...form, insuranceProvider: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Claimed Amount (INR / Local Currency)</label>
                <input
                  type="number"
                  value={form.claimedAmount}
                  onChange={(e) => setForm({ ...form, claimedAmount: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Admission Date</label>
                <input
                  type="date"
                  value={form.admissionDate}
                  onChange={(e) => setForm({ ...form, admissionDate: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">Discharge Date</label>
                <input
                  type="date"
                  value={form.dischargeDate}
                  onChange={(e) => setForm({ ...form, dischargeDate: e.target.value })}
                  className="mt-1 h-10 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white outline-none focus:border-[#3B82F6]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-[#9CA3AF]">Diagnosis & Clinical Notes</label>
              <textarea
                rows={3}
                value={form.diagnosis}
                onChange={(e) => setForm({ ...form, diagnosis: e.target.value })}
                className="mt-1 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] p-3 text-xs text-white outline-none focus:border-[#3B82F6]"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#3B82F6] px-6 text-xs font-semibold text-white shadow-lg shadow-[#3B82F6]/30 hover:bg-[#2563EB]"
              >
                Proceed to Document Intake
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: UPLOAD DOCUMENTS */}
        {step === 2 && (
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl space-y-6">
            <div className="border-b border-[#1F2937] pb-4">
              <h3 className="text-base font-bold text-white">Upload Claim Verification Documents</h3>
              <p className="text-xs text-[#9CA3AF]">Multi-document intake for AI OCR & RAG extraction</p>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg"
            />

            <div className="grid gap-4 sm:grid-cols-2">
              {DOC_CATEGORIES.map((cat) => {
                const uploadedFile = uploads[cat];
                return (
                  <div
                    key={cat}
                    className="flex items-center justify-between rounded-xl border border-[#1F2937] bg-[#0B0F17] p-4"
                  >
                    <div>
                      <p className="text-xs font-semibold text-white">{cat}</p>
                      <p className="text-[10px] text-[#9CA3AF]">
                        {uploadedFile ? uploadedFile : "No document uploaded"}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setCurrentCategory(cat);
                        fileInputRef.current?.click();
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${
                        uploadedFile
                          ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/40"
                          : "bg-[#1F2937] text-white hover:bg-[#374151]"
                      }`}
                    >
                      {uploadedFile ? <CheckCircle2 className="size-3.5" /> : <Upload className="size-3.5" />}
                      {uploadedFile ? "Uploaded" : "Upload"}
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between border-t border-[#1F2937] pt-4">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-[#9CA3AF] hover:text-white"
              >
                Back to Patient Details
              </button>

              <button
                type="button"
                onClick={handleCreate}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-6 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl"
              >
                <Zap className="size-4" /> Trigger AI Verification Pipeline
              </button>
            </div>
          </div>
        )}

      </div>
    </AppLayout>
  );
}