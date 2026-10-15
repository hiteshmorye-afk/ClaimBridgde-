import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useState, useRef, useMemo } from "react";
import { toast } from "sonner";
import {
  Upload,
  CheckCircle2,
  Zap,
  Loader2,
  Building2,
  Hash,
  Calendar,
  AlertCircle,
  FileCheck,
  AlertTriangle,
  Trash2,
  Plus,
  Clock,
  ShieldCheck,
  FileText,
  Check,
  Layers,
  Info,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import { AppLayout } from "@/components/layout/AppLayout";
import { addClaim, DOC_CATEGORIES, DocCategory, Claim } from "@/lib/claims";
import { createClaim } from "@/api/claims";
import { uploadDocument, processDocument } from "@/api/documents";
import {
  DOCUMENT_SECTIONS,
  DOCUMENT_CATALOGUE,
  DOCUMENT_CATALOGUE_BY_ID,
  getCategoryRequirement,
  DocumentCategory,
  ClaimContext,
  DocumentCategoryMeta,
} from "@/lib/documentCatalogue";
import {
  ClaimFormState,
  CONFIGURED_INSURERS,
  validateClaimForm,
  validatePatientName,
  validatePatientAge,
  validateHospital,
  validatePolicyNumber,
  validateProvider,
  validateClaimedAmount,
  validateDates,
  validateDiagnosis,
  DiagnosisItem,
  UNLISTED_DIAGNOSIS_CODE,
} from "@/lib/clinicalCatalogue";
import { DiagnosisSelector } from "@/components/claims/DiagnosisSelector";

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

export interface UploadedFileRecord {
  id: string;
  file: File;
  name: string;
  size: string;
  category: DocumentCategory;
  backendDocId?: string;
  status: "pending" | "uploading" | "processing" | "verified" | "error";
  detectedCategory?: string;
  confidence?: number;
  extractedSnippet?: string;
  discrepancyWarning?: string;
  arithmeticDiscrepancy?: string;
}

export function NewClaimPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdClaimId, setCreatedClaimId] = useState<string | null>(null);

  // Claim Context for Dynamic Requirements
  const [claimContext, setClaimContext] = useState<ClaimContext>({
    claimType: "reimbursement",
    isAccident: false,
    hasImplant: false,
    hasAmbulance: false,
  });

  // Multi-document intake state
  const [documentFiles, setDocumentFiles] = useState<Record<DocumentCategory, UploadedFileRecord[]>>({
    claim_form: [],
    insurance_card: [],
    identity_proof: [],
    bank_proof: [],
    discharge_summary: [],
    consultation_letter: [],
    diagnostic_report: [],
    hospital_bill: [],
    payment_receipt: [],
    pharmacy_bill: [],
    fir_mlc: [],
    implant_invoice: [],
    ambulance_receipt: [],
    pre_authorization: [],
    other_medical_doc: [],
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadCategory, setActiveUploadCategory] = useState<DocumentCategory>("hospital_bill");

  // Form State
  const [form, setForm] = useState<ClaimFormState>({
    patientName: "David Miller",
    patientAge: "46",
    hospital: "Apollo Hospitals International",
    policyNumber: "98765432101",
    insuranceProvider: "Pacific Healthcare TPA",
    admissionDate: "2026-08-10",
    dischargeDate: "2026-08-14",
    diagnosisCode: "K81.0",
    diagnosisDisplay: "Acute Cholecystitis",
    customDiagnosis: "",
    clinicalNotes: "Patient presented with acute right upper quadrant pain; ultrasound confirmed acute cholecystitis. Inpatient admission for surgical evaluation.",
    claimedAmount: "145000",
  });

  // Validation State
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // Field Refs for Auto-Focus on Validation Failure
  const nameInputRef = useRef<HTMLInputElement>(null);
  const ageInputRef = useRef<HTMLInputElement>(null);
  const hospitalInputRef = useRef<HTMLInputElement>(null);
  const policyInputRef = useRef<HTMLInputElement>(null);
  const providerInputRef = useRef<HTMLInputElement>(null);
  const amountInputRef = useRef<HTMLInputElement>(null);
  const admissionInputRef = useRef<HTMLInputElement>(null);
  const dischargeInputRef = useRef<HTMLInputElement>(null);

  const handleBlur = (field: keyof ClaimFormState) => {
    setTouched((prev) => ({ ...prev, [field]: true }));

    // Run field-specific validation on blur
    let fieldError: string | null = null;
    if (field === "patientName") fieldError = validatePatientName(form.patientName);
    else if (field === "patientAge") fieldError = validatePatientAge(form.patientAge);
    else if (field === "hospital") fieldError = validateHospital(form.hospital);
    else if (field === "policyNumber") fieldError = validatePolicyNumber(form.policyNumber);
    else if (field === "insuranceProvider") fieldError = validateProvider(form.insuranceProvider);
    else if (field === "claimedAmount") fieldError = validateClaimedAmount(form.claimedAmount);
    else if (field === "admissionDate" || field === "dischargeDate") {
      const { admissionError, dischargeError } = validateDates(
        form.admissionDate,
        form.dischargeDate
      );
      setErrors((prev) => ({
        ...prev,
        admissionDate: admissionError || "",
        dischargeDate: dischargeError || "",
      }));
      return;
    }

    setErrors((prev) => {
      const next = { ...prev };
      if (fieldError) {
        next[field] = fieldError;
      } else {
        delete next[field];
      }
      return next;
    });
  };

  // Open file selector for a specific category
  const handleOpenUpload = (category: DocumentCategory) => {
    setActiveUploadCategory(category);
    fileInputRef.current?.click();
  };

  // Upload and process a document file
  const processDocumentFile = async (
    record: UploadedFileRecord,
    category: DocumentCategory,
    claimId: string
  ) => {
    try {
      // 1. Mark as uploading
      setDocumentFiles((prev) => ({
        ...prev,
        [category]: prev[category].map((item) =>
          item.id === record.id ? { ...item, status: "uploading" } : item
        ),
      }));

      const catMeta = DOCUMENT_CATALOGUE_BY_ID.get(category);
      const catDisplayName = catMeta?.name || category;

      // 2. Upload to server
      const uploadRes = await uploadDocument(record.file, catDisplayName, claimId);
      if (!uploadRes?.documentId) {
        throw new Error("Upload did not return a valid document ID.");
      }

      // 3. Mark as processing
      setDocumentFiles((prev) => ({
        ...prev,
        [category]: prev[category].map((item) =>
          item.id === record.id
            ? { ...item, backendDocId: uploadRes.documentId, status: "processing" }
            : item
        ),
      }));

      // 4. Process through ClaimBridge AI Pipeline
      const procRes = await processDocument(uploadRes.documentId);
      const classification = procRes?.pipeline?.classification || {};
      const validation = procRes?.pipeline?.validation || {};

      const detected = classification.document_type;
      const confidence = Math.round((classification.confidence || 0) * 100);

      let discrepancy: string | undefined = undefined;
      // If detected category doesn't match selected category (or its aliases)
      if (
        detected &&
        detected !== "unknown" &&
        confidence >= 70 &&
        detected !== category &&
        !(category === "insurance_card" && detected === "insurance_policy") &&
        !(category === "consultation_letter" && detected === "prescription") &&
        !(category === "diagnostic_report" && detected === "lab_report") &&
        !(category === "other_medical_doc" && detected === "medical_report")
      ) {
        const detectedMeta = DOCUMENT_CATALOGUE_BY_ID.get(detected as DocumentCategory);
        discrepancy = `AI detected this as "${detectedMeta?.name || detected}" (${confidence}% confidence).`;
      }

      let arithmeticDisc: string | undefined = undefined;
      if (validation.mismatches && Array.isArray(validation.mismatches)) {
        const arithErr = validation.mismatches.find((m: string) =>
          m.toLowerCase().includes("bill total discrepancy")
        );
        if (arithErr) {
          arithmeticDisc = arithErr;
        }
      }

      // 5. Mark as verified
      setDocumentFiles((prev) => ({
        ...prev,
        [category]: prev[category].map((item) =>
          item.id === record.id
            ? {
                ...item,
                status: "verified",
                detectedCategory: detected,
                confidence,
                discrepancyWarning: discrepancy,
                arithmeticDiscrepancy: arithmeticDisc,
              }
            : item
        ),
      }));

      toast.success(`${record.name} verified successfully.`);
    } catch (err: any) {
      setDocumentFiles((prev) => ({
        ...prev,
        [category]: prev[category].map((item) =>
          item.id === record.id ? { ...item, status: "error" } : item
        ),
      }));
      toast.error(`Processing failed for ${record.name}: ${err?.message || "Server error"}`);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const catMeta = DOCUMENT_CATALOGUE_BY_ID.get(activeUploadCategory);
    const isMultiple = catMeta?.multiple ?? false;

    const newRecords: UploadedFileRecord[] = Array.from(files).map((f) => ({
      id: Math.random().toString(36).substring(7),
      file: f,
      name: f.name,
      size: `${(f.size / (1024 * 1024)).toFixed(2)} MB`,
      category: activeUploadCategory,
      status: "pending",
    }));

    setDocumentFiles((prev) => {
      const existing = prev[activeUploadCategory] || [];
      return {
        ...prev,
        [activeUploadCategory]: isMultiple ? [...existing, ...newRecords] : newRecords,
      };
    });

    // Reset input value so same file can be selected again
    e.target.value = "";

    // Trigger background upload and processing if claim is registered
    if (createdClaimId) {
      for (const rec of newRecords) {
        processDocumentFile(rec, activeUploadCategory, createdClaimId);
      }
    }
  };

  const handleRemoveFile = (category: DocumentCategory, recordId: string) => {
    setDocumentFiles((prev) => ({
      ...prev,
      [category]: prev[category].filter((item) => item.id !== recordId),
    }));
    toast.info("Document removed.");
  };

  const handleReclassify = (
    record: UploadedFileRecord,
    fromCategory: DocumentCategory,
    toCategory: DocumentCategory
  ) => {
    setDocumentFiles((prev) => {
      const remainingFrom = prev[fromCategory].filter((item) => item.id !== record.id);
      const updatedRecord: UploadedFileRecord = {
        ...record,
        category: toCategory,
        discrepancyWarning: undefined,
      };
      const toMeta = DOCUMENT_CATALOGUE_BY_ID.get(toCategory);
      const isMultiple = toMeta?.multiple ?? false;
      const targetExisting = prev[toCategory] || [];
      const updatedTo = isMultiple ? [...targetExisting, updatedRecord] : [updatedRecord];

      return {
        ...prev,
        [fromCategory]: remainingFrom,
        [toCategory]: updatedTo,
      };
    });

    const targetMeta = DOCUMENT_CATALOGUE_BY_ID.get(toCategory);
    toast.success(`Moved ${record.name} to "${targetMeta?.name || toCategory}".`);
  };

  // Requirement fulfillment statistics
  const requirementStats = useMemo(() => {
    let mandatoryTotal = 0;
    let mandatoryUploaded = 0;

    DOCUMENT_CATALOGUE.forEach((catMeta) => {
      // Exclude special, other, and bank_proof from the active requirements
      if (catMeta.section === "special" || catMeta.section === "other" || catMeta.id === "bank_proof") {
        return;
      }
      const { requirement } = getCategoryRequirement(catMeta.id, claimContext);
      if (requirement === "mandatory" || requirement === "conditional") {
        mandatoryTotal++;
        if (documentFiles[catMeta.id]?.length > 0) {
          mandatoryUploaded++;
        }
      }
    });

    return {
      mandatoryTotal,
      mandatoryUploaded,
      isComplete: mandatoryUploaded >= mandatoryTotal,
    };
  }, [claimContext, documentFiles]);

  /**
   * STEP 1 -> STEP 2 GUARDED TRANSITION
   * Strictly validates all fields. Only when valid, creates the claim in Neon DB,
   * retrieves the genuine claim UUID, and advances to Step 2.
   */
  const handleProceedToIntake = async () => {
    if (isSubmitting) return;

    // 1. Run complete client-side validation
    const { isValid, errors: validationErrors } = validateClaimForm(form);
    setErrors(validationErrors);
    setTouched({
      patientName: true,
      patientAge: true,
      hospital: true,
      policyNumber: true,
      insuranceProvider: true,
      admissionDate: true,
      dischargeDate: true,
      diagnosis: true,
      claimedAmount: true,
    });

    if (!isValid) {
      // Focus first invalid field
      if (validationErrors.patientName) nameInputRef.current?.focus();
      else if (validationErrors.patientAge) ageInputRef.current?.focus();
      else if (validationErrors.hospital) hospitalInputRef.current?.focus();
      else if (validationErrors.policyNumber) policyInputRef.current?.focus();
      else if (validationErrors.insuranceProvider) providerInputRef.current?.focus();
      else if (validationErrors.claimedAmount) amountInputRef.current?.focus();
      else if (validationErrors.admissionDate) admissionInputRef.current?.focus();
      else if (validationErrors.dischargeDate) dischargeInputRef.current?.focus();

      toast.error("Please resolve the highlighted validation errors before proceeding.");
      return;
    }

    // If claim was already created for this session, navigate to Step 2 directly
    if (createdClaimId) {
      setStep(2);
      return;
    }

    // 2. Submit to backend API to initialize real Neon database record
    setIsSubmitting(true);
    const toastId = toast.loading("Registering claim in database...");

    try {
      const formattedDiagnosis =
        form.diagnosisCode === UNLISTED_DIAGNOSIS_CODE
          ? form.customDiagnosis.trim()
          : `${form.diagnosisDisplay} (ICD-10: ${form.diagnosisCode})`;

      const created = await createClaim({
        patientName: form.patientName.trim(),
        patientAge: Number(form.patientAge),
        hospital: form.hospital.trim(),
        policyNumber: form.policyNumber.trim(),
        insuranceProvider: form.insuranceProvider.trim(),
        admissionDate: form.admissionDate,
        dischargeDate: form.dischargeDate,
        diagnosis: formattedDiagnosis,
        diagnosisCode: form.diagnosisCode,
        diagnosisCodeSystem:
          form.diagnosisCode === UNLISTED_DIAGNOSIS_CODE ? "Unresolved" : "ICD-10",
        clinicalNotes: form.clinicalNotes.trim(),
        claimedAmount: Number(form.claimedAmount),
        status: "Under Analysis",
        stage: "01 Secure Document Intake",
      });

      const realClaimId = created?.id;
      if (!realClaimId) {
        throw new Error("Backend did not return a valid Claim UUID.");
      }

      setCreatedClaimId(realClaimId);

      // Register local mirror for immediate navigation
      const newClaim: Claim = {
        id: realClaimId,
        patientName: form.patientName.trim(),
        patientAge: Number(form.patientAge) || 0,
        hospital: form.hospital.trim(),
        policyNumber: form.policyNumber.trim(),
        insuranceProvider: form.insuranceProvider.trim(),
        admissionDate: form.admissionDate,
        dischargeDate: form.dischargeDate,
        diagnosis: formattedDiagnosis,
        claimedAmount: Number(form.claimedAmount) || 0,
        status: "Under Analysis",
        stage: "01 Secure Document Intake",
        readiness: 0,
        ocrConfidence: 0,
        classification: "Document Intake",
        medicalRiskScore: 0,
        medicalConfidence: 0,
        policyConfidence: 0,
        validationReadiness: 0,
        overallConfidence: 0,
        routeDecision: "Human Review Required",
        documents: [],
        findings: [
          {
            label: "Intake Initialized",
            detail: `Claim registered in Neon database (UUID: ${realClaimId}).`,
            severity: "ok",
          },
        ],
        medicalServices: [],
        policyClauses: [],
        ocrLines: [],
      };
      addClaim(newClaim);

      toast.success("Claim registered successfully!", {
        id: toastId,
        description: `Backend UUID: ${realClaimId}`,
      });

      // Proceed to Step 2 (Document Intake)
      setStep(2);
    } catch (err: any) {
      toast.error(`Claim initialization failed: ${err?.message || "Server error"}`, {
        id: toastId,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * STEP 2 -> TRIGGER AI PIPELINE & NAVIGATE TO CLAIM
   */
  const handleTriggerPipeline = async () => {
    if (!createdClaimId) {
      toast.error("No active claim record found. Please return to Step 1.");
      return;
    }

    setIsSubmitting(true);
    const toastId = toast.loading("Finalizing document intake and verifying claim...");

    try {
      // Process any pending files
      const allFiles: UploadedFileRecord[] = Object.values(documentFiles).flat();
      const pendingFiles = allFiles.filter((f) => f.status === "pending" || f.status === "error");

      for (const rec of pendingFiles) {
        toast.loading(`Processing ${rec.name}...`, { id: toastId });
        await processDocumentFile(rec, rec.category, createdClaimId);
      }

      toast.success("Document verification completed!", {
        id: toastId,
        description: "Navigating to Claim Verification Dossier.",
      });

      navigate({ to: "/claims/$claimId", params: { claimId: createdClaimId } });
    } catch (err: any) {
      toast.error(`Verification pipeline encountered an issue: ${err?.message || "Server error"}`, {
        id: toastId,
      });
    } finally {
      setIsSubmitting(false);
    }
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
        <div className="flex items-center justify-between rounded-2xl border border-[#1F2937] bg-[#111827] p-4 shadow-lg">
          <div
            className={`flex items-center gap-3 ${
              step === 1 ? "text-[#3B82F6]" : "text-[#10B981]"
            }`}
          >
            <span
              className={`flex size-7 items-center justify-center rounded-full font-mono text-xs font-bold ${
                step === 1 ? "bg-[#3B82F6]/20 text-[#3B82F6]" : "bg-[#10B981]/20 text-[#10B981]"
              }`}
            >
              1
            </span>
            <span className="text-xs font-bold">1. Patient & Policy Details</span>
          </div>

          <div className="h-0.5 w-12 bg-[#1F2937]" />

          <div
            className={`flex items-center gap-3 ${
              step === 2 ? "text-[#3B82F6]" : "text-[#9CA3AF]"
            }`}
          >
            <span
              className={`flex size-7 items-center justify-center rounded-full font-mono text-xs font-bold ${
                step === 2 ? "bg-[#3B82F6]/20 text-[#3B82F6]" : "bg-[#1F2937] text-[#9CA3AF]"
              }`}
            >
              2
            </span>
            <span className="text-xs font-bold">2. Document Intake & Upload</span>
          </div>
        </div>

        {/* STEP 1: PATIENT & POLICY FORM */}
        {step === 1 && (
          <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl space-y-6">
            <div className="border-b border-[#1F2937] pb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">
                  Patient & Insurance Policy Information
                </h3>
                <p className="text-xs text-[#9CA3AF] mt-0.5">
                  Input hospital record, verified ICD-10 diagnosis, and numeric policy identifier
                </p>
              </div>
              <span className="text-[11px] text-[#9CA3AF]">
                Fields marked with <span className="text-[#EF4444] font-bold">*</span> are mandatory
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {/* PATIENT FULL NAME */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Patient Full Name <span className="text-[#EF4444]">*</span>
                </label>
                <input
                  ref={nameInputRef}
                  type="text"
                  value={form.patientName}
                  onChange={(e) => {
                    const val = e.target.value;
                    setForm((prev) => ({ ...prev, patientName: val }));
                    if (errors.patientName) {
                      const err = validatePatientName(val);
                      if (!err) setErrors((prev) => ({ ...prev, patientName: "" }));
                    }
                  }}
                  onBlur={() => handleBlur("patientName")}
                  placeholder="e.g. David Miller or Mary-Jane O'Neil"
                  className={`mt-1 h-10 w-full rounded-xl border bg-[#0B0F17] px-3 text-xs text-white outline-none transition-colors ${
                    errors.patientName
                      ? "border-[#EF4444] focus:border-[#EF4444]"
                      : "border-[#1F2937] focus:border-[#3B82F6]"
                  }`}
                />
                {errors.patientName && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.patientName}
                  </p>
                )}
              </div>

              {/* PATIENT AGE */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Patient Age (0–120 Years) <span className="text-[#EF4444]">*</span>
                </label>
                <input
                  ref={ageInputRef}
                  type="number"
                  min="0"
                  max="120"
                  step="1"
                  value={form.patientAge}
                  onChange={(e) => {
                    const val = e.target.value;
                    setForm((prev) => ({ ...prev, patientAge: val }));
                    if (errors.patientAge) {
                      const err = validatePatientAge(val);
                      if (!err) setErrors((prev) => ({ ...prev, patientAge: "" }));
                    }
                  }}
                  onBlur={() => handleBlur("patientAge")}
                  placeholder="e.g. 46"
                  className={`mt-1 h-10 w-full rounded-xl border bg-[#0B0F17] px-3 text-xs text-white outline-none transition-colors ${
                    errors.patientAge
                      ? "border-[#EF4444] focus:border-[#EF4444]"
                      : "border-[#1F2937] focus:border-[#3B82F6]"
                  }`}
                />
                {errors.patientAge && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.patientAge}
                  </p>
                )}
              </div>

              {/* HOSPITAL / PROVIDER NAME */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Hospital / Provider Name <span className="text-[#EF4444]">*</span>
                </label>
                <div className="relative mt-1">
                  <input
                    ref={hospitalInputRef}
                    type="text"
                    value={form.hospital}
                    onChange={(e) => {
                      const val = e.target.value;
                      setForm((prev) => ({ ...prev, hospital: val }));
                      if (errors.hospital) {
                        const err = validateHospital(val);
                        if (!err) setErrors((prev) => ({ ...prev, hospital: "" }));
                      }
                    }}
                    onBlur={() => handleBlur("hospital")}
                    placeholder="e.g. Apollo Hospitals International"
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] pl-8 pr-3 text-xs text-white outline-none transition-colors ${
                      errors.hospital
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                  <Building2 className="absolute left-2.5 top-3 size-3.5 text-[#9CA3AF]" />
                </div>
                {errors.hospital && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.hospital}
                  </p>
                )}
              </div>

              {/* POLICY NUMBER */}
              <div>
                <label className="flex items-center justify-between text-xs font-semibold text-[#9CA3AF]">
                  <span>
                    Policy Number (8–13 digits) <span className="text-[#EF4444]">*</span>
                  </span>
                  <span className="font-mono text-[10px] text-[#6B7280]">
                    Digits only ({form.policyNumber.length}/13)
                  </span>
                </label>
                <div className="relative mt-1">
                  <input
                    ref={policyInputRef}
                    type="text"
                    inputMode="numeric"
                    maxLength={13}
                    value={form.policyNumber}
                    onChange={(e) => {
                      // Preserve string with leading zeros; accept digits only
                      const val = e.target.value.replace(/\D/g, "");
                      setForm((prev) => ({ ...prev, policyNumber: val }));
                      if (errors.policyNumber) {
                        const err = validatePolicyNumber(val);
                        if (!err) setErrors((prev) => ({ ...prev, policyNumber: "" }));
                      }
                    }}
                    onBlur={() => handleBlur("policyNumber")}
                    placeholder="e.g. 98765432101 (8-13 digits)"
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] pl-8 pr-3 text-xs text-white outline-none transition-colors ${
                      errors.policyNumber
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                  <Hash className="absolute left-2.5 top-3 size-3.5 text-[#9CA3AF]" />
                </div>
                {errors.policyNumber && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.policyNumber}
                  </p>
                )}
              </div>

              {/* INSURANCE PROVIDER / TPA */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Insurance Provider / TPA <span className="text-[#EF4444]">*</span>
                </label>
                <div className="relative mt-1">
                  <input
                    ref={providerInputRef}
                    type="text"
                    list="insurers-list"
                    value={form.insuranceProvider}
                    onChange={(e) => {
                      const val = e.target.value;
                      setForm((prev) => ({ ...prev, insuranceProvider: val }));
                      if (errors.insuranceProvider) {
                        const err = validateProvider(val);
                        if (!err) setErrors((prev) => ({ ...prev, insuranceProvider: "" }));
                      }
                    }}
                    onBlur={() => handleBlur("insuranceProvider")}
                    placeholder="Select or enter insurer (e.g. Pacific Healthcare TPA)"
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] px-3 text-xs text-white outline-none transition-colors ${
                      errors.insuranceProvider
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                  <datalist id="insurers-list">
                    {CONFIGURED_INSURERS.map((ins) => (
                      <option key={ins} value={ins} />
                    ))}
                  </datalist>
                </div>
                {errors.insuranceProvider && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.insuranceProvider}
                  </p>
                )}
              </div>

              {/* CLAIMED AMOUNT */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Claimed Amount (INR / ₹) <span className="text-[#EF4444]">*</span>
                </label>
                <div className="relative mt-1">
                  <span className="absolute left-3 top-2.5 font-mono text-xs font-bold text-[#9CA3AF]">
                    ₹
                  </span>
                  <input
                    ref={amountInputRef}
                    type="number"
                    step="0.01"
                    min="1"
                    value={form.claimedAmount}
                    onChange={(e) => {
                      const val = e.target.value;
                      setForm((prev) => ({ ...prev, claimedAmount: val }));
                      if (errors.claimedAmount) {
                        const err = validateClaimedAmount(val);
                        if (!err) setErrors((prev) => ({ ...prev, claimedAmount: "" }));
                      }
                    }}
                    onBlur={() => handleBlur("claimedAmount")}
                    placeholder="e.g. 145000"
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] pl-8 pr-3 text-xs text-white outline-none transition-colors ${
                      errors.claimedAmount
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                </div>
                {errors.claimedAmount && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.claimedAmount}
                  </p>
                )}
              </div>

              {/* ADMISSION DATE */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Admission Date <span className="text-[#EF4444]">*</span>
                </label>
                <div className="relative mt-1">
                  <input
                    ref={admissionInputRef}
                    type="date"
                    value={form.admissionDate}
                    onChange={(e) => {
                      const val = e.target.value;
                      setForm((prev) => ({ ...prev, admissionDate: val }));
                      const { admissionError } = validateDates(val, form.dischargeDate);
                      setErrors((prev) => ({
                        ...prev,
                        admissionDate: admissionError || "",
                      }));
                    }}
                    onBlur={() => handleBlur("admissionDate")}
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] px-3 text-xs text-white outline-none transition-colors ${
                      errors.admissionDate
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                </div>
                {errors.admissionDate && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.admissionDate}
                  </p>
                )}
              </div>

              {/* DISCHARGE DATE */}
              <div>
                <label className="text-xs font-semibold text-[#9CA3AF]">
                  Discharge Date <span className="text-[#EF4444]">*</span>
                </label>
                <div className="relative mt-1">
                  <input
                    ref={dischargeInputRef}
                    type="date"
                    value={form.dischargeDate}
                    onChange={(e) => {
                      const val = e.target.value;
                      setForm((prev) => ({ ...prev, dischargeDate: val }));
                      const { dischargeError } = validateDates(form.admissionDate, val);
                      setErrors((prev) => ({
                        ...prev,
                        dischargeDate: dischargeError || "",
                      }));
                    }}
                    onBlur={() => handleBlur("dischargeDate")}
                    className={`h-10 w-full rounded-xl border bg-[#0B0F17] px-3 text-xs text-white outline-none transition-colors ${
                      errors.dischargeDate
                        ? "border-[#EF4444] focus:border-[#EF4444]"
                        : "border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                  />
                </div>
                {errors.dischargeDate && (
                  <p className="mt-1 text-[11px] font-medium text-[#EF4444]">
                    {errors.dischargeDate}
                  </p>
                )}
              </div>
            </div>

            {/* STRUCTURED CLINICAL DIAGNOSIS & ICD-10 SELECTOR */}
            <div className="border-t border-[#1F2937] pt-4">
              <DiagnosisSelector
                selectedCode={form.diagnosisCode}
                customDiagnosis={form.customDiagnosis}
                clinicalNotes={form.clinicalNotes}
                onSelectDiagnosis={(item: DiagnosisItem | null) => {
                  if (item) {
                    setForm((prev) => ({
                      ...prev,
                      diagnosisCode: item.code,
                      diagnosisDisplay: item.display,
                    }));
                  } else {
                    setForm((prev) => ({
                      ...prev,
                      diagnosisCode: "",
                      diagnosisDisplay: "",
                    }));
                  }
                  if (errors.diagnosis) {
                    const err = validateDiagnosis(item ? item.code : "", form.customDiagnosis);
                    setErrors((prev) => ({ ...prev, diagnosis: err || "" }));
                  }
                }}
                onCustomDiagnosisChange={(val) => {
                  setForm((prev) => ({ ...prev, customDiagnosis: val }));
                  if (errors.diagnosis) {
                    const err = validateDiagnosis(form.diagnosisCode, val);
                    setErrors((prev) => ({ ...prev, diagnosis: err || "" }));
                  }
                }}
                onClinicalNotesChange={(val) =>
                  setForm((prev) => ({ ...prev, clinicalNotes: val }))
                }
                error={errors.diagnosis}
              />
            </div>

            {/* PROCEED TO DOCUMENT INTAKE BUTTON */}
            <div className="flex items-center justify-between border-t border-[#1F2937] pt-4">
              <div className="flex items-center gap-2 text-xs text-[#9CA3AF]">
                <FileCheck className="size-4 text-[#3B82F6]" />
                <span>Verification requires document evidence in Step 2</span>
              </div>

              <button
                type="button"
                onClick={handleProceedToIntake}
                disabled={isSubmitting}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#3B82F6] px-6 text-xs font-semibold text-white shadow-lg shadow-[#3B82F6]/30 hover:bg-[#2563EB] disabled:opacity-50 transition-all"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Registering Claim...
                  </>
                ) : (
                  "Proceed to Document Intake"
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: UPLOAD DOCUMENTS (CORE, MEDICAL, FINANCIAL) */}
        {step === 2 && (
          <div className="space-y-6">
            {/* HIDDEN FILE INPUT (DYNAMIC MULTIPLE FLAG) */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg"
              multiple={DOCUMENT_CATALOGUE_BY_ID.get(activeUploadCategory)?.multiple ?? false}
            />

            {/* CATEGORIZED SECTIONS */}
            {DOCUMENT_SECTIONS.filter((s) => s.id !== "special" && s.id !== "other").map((section) => {
              const categories = DOCUMENT_CATALOGUE.filter(
                (cat) => cat.section === section.id && cat.id !== "bank_proof"
              );

              return (
                <div
                  key={section.id}
                  className="rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl space-y-4"
                >
                  {/* SECTION HEADER */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 border-b border-[#1F2937] pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>{section.title}</span>
                      </h4>
                      <p className="text-[11px] text-[#9CA3AF] mt-0.5">{section.subtitle}</p>
                    </div>
                    <span className="self-start sm:self-auto rounded-full bg-[#1F2937] px-2.5 py-0.5 text-[10px] font-semibold text-[#9CA3AF]">
                      {section.badge}
                    </span>
                  </div>

                  {/* CATEGORY CARDS GRID */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    {categories.map((catMeta) => {
                      const reqInfo = getCategoryRequirement(catMeta.id, claimContext);
                      const uploadsList = documentFiles[catMeta.id] || [];

                      return (
                        <div
                          key={catMeta.id}
                          className="flex flex-col justify-between rounded-xl border border-[#1F2937] bg-[#0B0F17] p-4 transition-all hover:border-[#374151]"
                        >
                          <div>
                            {/* TITLE & REQUIREMENT BADGE */}
                            <div className="flex items-start justify-between gap-2 mb-1.5">
                              <h5 className="text-xs font-bold text-white leading-tight">
                                {catMeta.name}
                              </h5>

                              {reqInfo.requirement === "mandatory" && (
                                <span className="shrink-0 rounded-md bg-[#EF4444]/15 border border-[#EF4444]/30 px-2 py-0.5 text-[10px] font-bold text-[#EF4444]">
                                  Mandatory
                                </span>
                              )}
                              {reqInfo.requirement === "conditional" && (
                                <span
                                  title={reqInfo.reason}
                                  className="shrink-0 rounded-md bg-[#F59E0B]/15 border border-[#F59E0B]/30 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B]"
                                >
                                  Conditional
                                </span>
                              )}
                              {reqInfo.requirement === "optional" && (
                                <span className="shrink-0 rounded-md bg-[#374151]/50 border border-[#4B5563]/40 px-2 py-0.5 text-[10px] font-medium text-[#9CA3AF]">
                                  Optional
                                </span>
                              )}
                            </div>

                            <p className="text-[11px] text-[#9CA3AF] mb-3 leading-relaxed">
                              {catMeta.description}
                            </p>

                            {/* UPLOADED FILES LIST */}
                            {uploadsList.length > 0 && (
                              <div className="space-y-2 mb-3">
                                {uploadsList.map((item) => (
                                  <div
                                    key={item.id}
                                    className="rounded-lg border border-[#1F2937] bg-[#111827] p-2 text-xs space-y-1.5"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <div className="flex items-center gap-2 truncate">
                                        <FileText className="size-3.5 text-[#3B82F6] shrink-0" />
                                        <span className="font-medium text-white truncate">
                                          {item.name}
                                        </span>
                                        <span className="text-[10px] text-[#6B7280]">
                                          ({item.size})
                                        </span>
                                      </div>

                                      <div className="flex items-center gap-1.5 shrink-0">
                                        {item.status === "uploading" && (
                                          <span className="flex items-center gap-1 text-[10px] text-[#3B82F6]">
                                            <Loader2 className="size-3 animate-spin" /> Uploading...
                                          </span>
                                        )}
                                        {item.status === "processing" && (
                                          <span className="flex items-center gap-1 text-[10px] text-[#06B6D4]">
                                            <Loader2 className="size-3 animate-spin" /> OCR AI...
                                          </span>
                                        )}
                                        {item.status === "verified" && (
                                          <span className="flex items-center gap-1 text-[10px] text-[#10B981] font-semibold">
                                            <CheckCircle2 className="size-3" />
                                            Verified
                                            {item.confidence ? ` (${item.confidence}%)` : ""}
                                          </span>
                                        )}
                                        {item.status === "error" && (
                                          <span className="flex items-center gap-1 text-[10px] text-[#EF4444]">
                                            <AlertCircle className="size-3" /> Failed
                                          </span>
                                        )}

                                        <button
                                          type="button"
                                          onClick={() => handleRemoveFile(catMeta.id, item.id)}
                                          title="Remove File"
                                          className="text-[#9CA3AF] hover:text-[#EF4444] p-1 transition-colors"
                                        >
                                          <Trash2 className="size-3" />
                                        </button>
                                      </div>
                                    </div>

                                    {/* AI RECATEGORIZATION ALERT BANNER */}
                                    {item.discrepancyWarning && item.detectedCategory && (
                                      <div className="rounded-md bg-[#F59E0B]/10 border border-[#F59E0B]/30 p-2 flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-1.5 text-[10px] text-[#F59E0B]">
                                          <AlertTriangle className="size-3 shrink-0" />
                                          <span>{item.discrepancyWarning}</span>
                                        </div>
                                        <button
                                          type="button"
                                          onClick={() =>
                                            handleReclassify(
                                              item,
                                              catMeta.id,
                                              item.detectedCategory as DocumentCategory
                                            )
                                          }
                                          className="shrink-0 rounded bg-[#F59E0B]/20 hover:bg-[#F59E0B]/30 px-2 py-0.5 text-[10px] font-bold text-[#F59E0B] transition-colors"
                                        >
                                          Reclassify
                                        </button>
                                      </div>
                                    )}

                                    {/* ARITHMETIC BILLING MISMATCH ALERT */}
                                    {item.arithmeticDiscrepancy && (
                                      <div className="rounded-md bg-[#EF4444]/10 border border-[#EF4444]/30 p-2 text-[10px] text-[#EF4444] flex items-center gap-1.5">
                                        <AlertCircle className="size-3 shrink-0" />
                                        <span>{item.arithmeticDiscrepancy}</span>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* UPLOAD / ADD ACTION BUTTON */}
                          <div className="pt-2 border-t border-[#1F2937]/60 flex items-center justify-between">
                            <span className="text-[10px] text-[#6B7280]">
                              {catMeta.multiple ? "Supports multiple files" : "Single document"}
                            </span>

                            <button
                              type="button"
                              onClick={() => handleOpenUpload(catMeta.id)}
                              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                                uploadsList.length > 0
                                  ? catMeta.multiple
                                    ? "bg-[#1F2937] text-white hover:bg-[#374151]"
                                    : "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/40"
                                  : "bg-[#3B82F6]/20 text-[#3B82F6] hover:bg-[#3B82F6]/30 border border-[#3B82F6]/40"
                              }`}
                            >
                              {uploadsList.length === 0 ? (
                                <>
                                  <Upload className="size-3" /> Upload
                                </>
                              ) : catMeta.multiple ? (
                                <>
                                  <Plus className="size-3" /> Add More
                                </>
                              ) : (
                                <>
                                  <RefreshCw className="size-3" /> Replace
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* STEPPER NAVIGATION & PIPELINE TRIGGER FOOTER */}
            <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-[#9CA3AF] hover:text-white transition-colors"
              >
                ← Back to Patient & Policy Details
              </button>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="text-right">
                  <div className="text-xs font-semibold text-white">
                    {requirementStats.mandatoryUploaded} of {requirementStats.mandatoryTotal}{" "}
                    Required Documents Uploaded
                  </div>
                  <div className="text-[10px] text-[#9CA3AF]">
                    {requirementStats.isComplete
                      ? "All required documents satisfied."
                      : "Recommended: upload all required files before pipeline evaluation."}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleTriggerPipeline}
                  disabled={isSubmitting}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-6 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl disabled:opacity-50 transition-all"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Executing AI Pipeline...
                    </>
                  ) : (
                    <>
                      <Zap className="size-4" /> Trigger AI Verification Pipeline
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}