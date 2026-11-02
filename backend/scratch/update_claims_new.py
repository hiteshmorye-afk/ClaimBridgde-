import re

with open("src/routes/claims.new.tsx", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update UploadedDocRecord status union
old_status = """  status:
    | "pending"
    | "uploading"
    | "ocr_processing"
    | "processing"
    | "correct"
    | "incorrect"
    | "unreadable"
    | "manual_review"
    | "failed";"""

new_status = """  status:
    | "waiting"
    | "uploading"
    | "uploaded"
    | "ocr_processing"
    | "classifying"
    | "extracting"
    | "validating"
    | "completed"
    | "correct"
    | "incorrect"
    | "unreadable"
    | "manual_review"
    | "failed"
    | "pending"
    | "processing";"""

old_status_crlf = old_status.replace("\n", "\r\n")
new_status_crlf = new_status.replace("\n", "\r\n")

if old_status in code:
    code = code.replace(old_status, new_status, 1)
    print("1. Replaced status (LF)")
elif old_status_crlf in code:
    code = code.replace(old_status_crlf, new_status_crlf, 1)
    print("1. Replaced status (CRLF)")
else:
    print("1. Status target not found!")

# 2. Add concurrency and polling refs after activeUploadCatId
old_refs = """  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadCatId, setActiveUploadCatId] = useState<string>("identity_proof");

  // Step 5 created claim ID
  const [createdClaimUuid, setCreatedClaimUuid] = useState<string | null>(null);"""

new_refs = """  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadCatId, setActiveUploadCatId] = useState<string>("identity_proof");

  // Concurrency control & background polling tracking
  const MAX_CONCURRENT_UPLOADS = 2;
  const activeUploadsCountRef = useRef<number>(0);
  const activePollingDocIdsRef = useRef<Set<string>>(new Set());

  // Step 5 created claim ID
  const [createdClaimUuid, setCreatedClaimUuid] = useState<string | null>(null);"""

old_refs_crlf = old_refs.replace("\n", "\r\n")
new_refs_crlf = new_refs.replace("\n", "\r\n")

if old_refs in code:
    code = code.replace(old_refs, new_refs, 1)
    print("2. Added refs (LF)")
elif old_refs_crlf in code:
    code = code.replace(old_refs_crlf, new_refs_crlf, 1)
    print("2. Added refs (CRLF)")
else:
    print("2. Refs target not found!")

# 3. Replace document upload and processing functions (from runProcessingPipeline through handleFileSelected)
old_pipeline_start = "  const runProcessingPipeline = async ("
old_file_selected_end = "  const handleRemoveFile = (catId: string, recordId: string) => {"

start_idx = code.find(old_pipeline_start)
end_idx = code.find(old_file_selected_end)

if start_idx != -1 and end_idx != -1:
    new_pipeline_code = """  // STEP 4: REAL-TIME DOCUMENT PIPELINE & POLLING
  const startDocumentStatusPolling = (
    catId: string,
    fileRecId: string,
    backendDocId: string,
    catDisplayName: string,
    fileName: string
  ) => {
    if (activePollingDocIdsRef.current.has(backendDocId)) return;
    activePollingDocIdsRef.current.add(backendDocId);

    const maxAttempts = 40; // ~60s max polling
    let attempts = 0;

    const pollTimer = setInterval(async () => {
      attempts += 1;
      try {
        const docDetail = await fetchDocumentDetail(backendDocId);
        if (!docDetail) return;

        const pStatus = (docDetail.processingStatus || "").toLowerCase();

        if (pStatus === "ocr processing") {
          setUploadedFiles((prev) => ({
            ...prev,
            [catId]: (prev[catId] || []).map((r) =>
              r.id === fileRecId
                ? { ...r, status: "ocr_processing", progressStage: "OCR Processing..." }
                : r
            ),
          }));
        } else if (pStatus === "classification") {
          setUploadedFiles((prev) => ({
            ...prev,
            [catId]: (prev[catId] || []).map((r) =>
              r.id === fileRecId
                ? { ...r, status: "classifying", progressStage: "Classification..." }
                : r
            ),
          }));
        } else if (pStatus === "information extraction") {
          setUploadedFiles((prev) => ({
            ...prev,
            [catId]: (prev[catId] || []).map((r) =>
              r.id === fileRecId
                ? { ...r, status: "extracting", progressStage: "Information Extraction..." }
                : r
            ),
          }));
        } else if (pStatus === "validation") {
          setUploadedFiles((prev) => ({
            ...prev,
            [catId]: (prev[catId] || []).map((r) =>
              r.id === fileRecId
                ? { ...r, status: "validating", progressStage: "Validation..." }
                : r
            ),
          }));
        } else if (pStatus === "completed" || pStatus === "verified" || pStatus === "failed") {
          clearInterval(pollTimer);
          activePollingDocIdsRef.current.delete(backendDocId);

          if (pStatus === "failed") {
            setUploadedFiles((prev) => ({
              ...prev,
              [catId]: (prev[catId] || []).map((r) =>
                r.id === fileRecId
                  ? {
                      ...r,
                      status: "failed",
                      progressStage: undefined,
                      mismatchWarning: "AI Processing failed on server. Click Retry to re-process.",
                    }
                  : r
              ),
            }));
            toast.error(`${fileName}: Processing failed.`);
            return;
          }

          // Evaluate classification & validation results
          const classification = docDetail.classification || {};
          const detected = classification.document_type || "unknown";
          const confidence = Math.round((classification.confidence || 0.85) * 100);
          const categoryStatus = classification.category_status || "";
          const categoryWarning = classification.mismatch_warning || "";

          let docStatus: UploadedDocRecord["status"] = "correct";
          let mismatchMsg = categoryWarning;

          const isCompatible =
            catId === detected ||
            (catId === "identity_proof" && ["identity_proof", "aadhaar", "pan", "passport", "kyc", "voter_id"].includes(detected)) ||
            (catId === "insurance_card" && ["insurance_card", "insurance_policy", "policy_schedule", "health_card"].includes(detected)) ||
            (catId === "consultation_letter" && ["consultation_letter", "prescription", "opd_slip", "doctor_prescription"].includes(detected)) ||
            (catId === "diagnostic_report" && ["diagnostic_report", "lab_report", "pathology_report", "radiology_report", "investigation_report"].includes(detected)) ||
            (catId === "hospital_bill" && ["hospital_bill", "final_bill", "estimate_bill", "hospital_estimate", "tax_invoice"].includes(detected)) ||
            (catId === "pre_authorization" && ["pre_authorization", "pre_auth_form", "pre_auth_approval"].includes(detected)) ||
            (catId === "other_medical_doc" && ["other_medical_doc", "patient_consent", "consent_form", "declaration_form", "claim_form", "medical_report"].includes(detected));

          if (categoryStatus === "Incorrect Document Type" || (detected !== "unknown" && confidence >= 50 && !isCompatible)) {
            const detectedMeta = PRE_AUTH_CATEGORIES.find((c) => c.id === detected);
            const detectedName = detectedMeta?.name || detected.replace(/_/g, " ").toUpperCase();
            mismatchMsg = categoryWarning || `Incorrect Document Type. This PDF appears to be a ${detectedName}, not ${catDisplayName}. Please upload the correct document.`;
            docStatus = "incorrect";
            toast.error(mismatchMsg);
          } else if (categoryStatus === "Unreadable File") {
            mismatchMsg = categoryWarning || `Unreadable File: No extractable text detected in ${fileName}. Please upload a clear scan.`;
            docStatus = "unreadable";
            toast.error(mismatchMsg);
          } else if (confidence < 45 || categoryStatus === "Document Type Uncertain") {
            mismatchMsg = categoryWarning || "Document Type Uncertain: Please review to ensure the uploaded file matches selected category.";
            docStatus = "manual_review";
            toast.warning(mismatchMsg);
          } else {
            docStatus = "correct";
            toast.success(`${fileName}: Verified as ${catDisplayName}.`);
          }

          setUploadedFiles((prev) => ({
            ...prev,
            [catId]: (prev[catId] || []).map((r) =>
              r.id === fileRecId
                ? {
                    ...r,
                    status: docStatus,
                    progressStage: undefined,
                    detectedCategory: detected,
                    confidence,
                    mismatchWarning: mismatchMsg,
                    extractedFields: docDetail.extractedFields,
                    reliabilityScore: docDetail.reliabilityScore,
                  }
                : r
            ),
          }));
        }

        if (attempts >= maxAttempts) {
          clearInterval(pollTimer);
          activePollingDocIdsRef.current.delete(backendDocId);
        }
      } catch {
        if (attempts >= maxAttempts) {
          clearInterval(pollTimer);
          activePollingDocIdsRef.current.delete(backendDocId);
        }
      }
    }, 1500);
  };

  // Execute single file upload
  const executeFileUpload = async (catId: string, record: UploadedDocRecord) => {
    const catMeta = PRE_AUTH_CATEGORIES.find((c) => c.id === catId);
    const catDisplayName = catMeta?.name || catId;

    // Transition to uploading
    setUploadedFiles((prev) => ({
      ...prev,
      [catId]: (prev[catId] || []).map((r) =>
        r.id === record.id
          ? { ...r, status: "uploading", progressStage: "Uploading to backend..." }
          : r
      ),
    }));

    try {
      const uploadRes = await uploadDocument(record.file!, catDisplayName, createdClaimUuid || undefined);
      const backendDocId = uploadRes?.documentId;
      if (!backendDocId) {
        throw new Error("Backend did not return a valid document ID.");
      }
      if (!createdClaimUuid && uploadRes?.claimId) {
        setCreatedClaimUuid(uploadRes.claimId);
      }

      // Immediately transition to uploaded successfully
      setUploadedFiles((prev) => ({
        ...prev,
        [catId]: (prev[catId] || []).map((r) =>
          r.id === record.id
            ? {
                ...r,
                backendDocId,
                status: "uploaded",
                progressStage: "Uploaded Successfully",
              }
            : r
        ),
      }));

      // Free upload slot immediately for next waiting file
      activeUploadsCountRef.current = Math.max(0, activeUploadsCountRef.current - 1);

      // Start background polling for processing stages
      startDocumentStatusPolling(catId, record.id, backendDocId, catDisplayName, record.name);
    } catch (err: any) {
      activeUploadsCountRef.current = Math.max(0, activeUploadsCountRef.current - 1);
      setUploadedFiles((prev) => ({
        ...prev,
        [catId]: (prev[catId] || []).map((r) =>
          r.id === record.id
            ? {
                ...r,
                status: "failed",
                progressStage: undefined,
                mismatchWarning: `Upload failed: ${err?.message || "Server error"}`,
              }
            : r
        ),
      }));
      toast.error(`Failed to upload ${record.name}: ${err?.message || "Server error"}`);
    }
  };

  // Controlled upload concurrency worker (max 2 active uploads at a time)
  useEffect(() => {
    const waitingItems: { catId: string; record: UploadedDocRecord }[] = [];
    Object.entries(uploadedFiles).forEach(([catId, files]) => {
      files.forEach((r) => {
        if (r.status === "waiting" && r.file) {
          waitingItems.push({ catId, record: r });
        }
      });
    });

    if (waitingItems.length === 0) return;
    if (activeUploadsCountRef.current >= MAX_CONCURRENT_UPLOADS) return;

    const availableSlots = MAX_CONCURRENT_UPLOADS - activeUploadsCountRef.current;
    const itemsToStart = waitingItems.slice(0, availableSlots);

    itemsToStart.forEach(({ catId, record }) => {
      activeUploadsCountRef.current += 1;
      executeFileUpload(catId, record);
    });
  }, [uploadedFiles]);

  const handleRetry = (catId: string, recordId: string) => {
    const rec = (uploadedFiles[catId] || []).find((r) => r.id === recordId);
    if (!rec) return;

    if (rec.backendDocId) {
      const catMeta = PRE_AUTH_CATEGORIES.find((c) => c.id === catId);
      const catDisplayName = catMeta?.name || catId;
      setUploadedFiles((prev) => ({
        ...prev,
        [catId]: (prev[catId] || []).map((r) =>
          r.id === recordId
            ? { ...r, status: "ocr_processing", progressStage: "OCR & Document Intelligence..." }
            : r
        ),
      }));
      processDocument(rec.backendDocId)
        .then(() => {
          startDocumentStatusPolling(catId, recordId, rec.backendDocId!, catDisplayName, rec.name);
        })
        .catch((err) => {
          toast.error(`Retry processing failed: ${err.message || "Server error"}`);
        });
    } else if (rec.file) {
      setUploadedFiles((prev) => ({
        ...prev,
        [catId]: (prev[catId] || []).map((r) =>
          r.id === recordId
            ? { ...r, status: "waiting", progressStage: "Waiting to Upload", mismatchWarning: undefined }
            : r
        ),
      }));
    }
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const catId = activeUploadCatId;

    // Prevent duplicate uploads
    let isDuplicate = false;
    Object.values(uploadedFiles).forEach((files) => {
      if (files.some((f) => f.name === file.name && f.size === `${(file.size / 1024).toFixed(1)} KB`)) {
        isDuplicate = true;
      }
    });

    if (isDuplicate) {
      toast.warning(`"${file.name}" has already been uploaded or queued.`);
      if (e.target) e.target.value = "";
      return;
    }

    const fileRecId = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const newRecord: UploadedDocRecord = {
      id: fileRecId,
      file,
      name: file.name,
      size: `${(file.size / 1024).toFixed(1)} KB`,
      category: catId,
      status: "waiting",
      progressStage: "Waiting to Upload",
    };

    setUploadedFiles((prev) => ({
      ...prev,
      [catId]: [...(prev[catId] || []), newRecord],
    }));

    if (e.target) e.target.value = "";
  };

"""
    code = code[:start_idx] + new_pipeline_code + code[end_idx:]
    print("3. Replaced pipeline and file selected code successfully.")
else:
    print(f"3. Could not find pipeline bounds: start_idx={start_idx}, end_idx={end_idx}")

# 4. Update UI Badges in the file list
old_badges = """                                <div className="flex items-center gap-2">
                                {file.status === "uploading" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "Uploading..."}
                                  </span>
                                )}

                                {(file.status === "processing" || file.status === "ocr_processing") && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "AI Verifying..."}
                                  </span>
                                )}

                                {file.status === "correct" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-500">
                                    <CheckCircle2 className="size-3" /> Correct Document Type
                                  </span>
                                )}

                                {file.status === "incorrect" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                    <XCircle className="size-3" /> Incorrect Document Type
                                  </span>
                                )}

                                {file.status === "unreadable" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                    <AlertTriangle className="size-3" /> Unreadable File
                                  </span>
                                )}

                                {file.status === "manual_review" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-500">
                                    <AlertTriangle className="size-3" /> Manual Review Required
                                  </span>
                                )}

                                {file.status === "failed" && (
                                  <div className="flex items-center gap-1.5">
                                    <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                      <XCircle className="size-3" /> Processing Failed
                                    </span>
                                    {file.backendDocId && (
                                      <button
                                        type="button"
                                        onClick={() => handleRetryProcessing(cat.id, file.id)}
                                        className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-300 hover:text-white"
                                        title="Retry processing"
                                      >
                                        Retry
                                      </button>
                                    )}
                                  </div>
                                )}"""

new_badges = """                                <div className="flex items-center gap-2">
                                {file.status === "waiting" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-slate-400/40 bg-slate-500/10 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:text-slate-400">
                                    <Clock className="size-3" /> Waiting to Upload
                                  </span>
                                )}

                                {file.status === "uploading" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "Uploading..."}
                                  </span>
                                )}

                                {file.status === "uploaded" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold text-cyan-600 dark:text-cyan-400">
                                    <CheckCircle2 className="size-3" /> Uploaded Successfully
                                  </span>
                                )}

                                {file.status === "ocr_processing" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "OCR Processing..."}
                                  </span>
                                )}

                                {file.status === "classifying" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "Classification..."}
                                  </span>
                                )}

                                {file.status === "extracting" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "Information Extraction..."}
                                  </span>
                                )}

                                {file.status === "validating" && (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-500">
                                    <Loader2 className="size-3 animate-spin" /> {file.progressStage || "Validation..."}
                                  </span>
                                )}

                                {(file.status === "correct" || file.status === "completed") && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-500">
                                    <CheckCircle2 className="size-3" /> Correct Document Type
                                  </span>
                                )}

                                {file.status === "incorrect" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                    <XCircle className="size-3" /> Incorrect Document Type
                                  </span>
                                )}

                                {file.status === "unreadable" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                    <AlertTriangle className="size-3" /> Unreadable File
                                  </span>
                                )}

                                {file.status === "manual_review" && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-500">
                                    <AlertTriangle className="size-3" /> Manual Review Required
                                  </span>
                                )}

                                {file.status === "failed" && (
                                  <div className="flex items-center gap-1.5">
                                    <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-500">
                                      <XCircle className="size-3" /> Failed
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => handleRetry(cat.id, file.id)}
                                      className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-300 hover:text-white"
                                      title="Retry"
                                    >
                                      Retry
                                    </button>
                                  </div>
                                )}"""

old_badges_crlf = old_badges.replace("\n", "\r\n")
new_badges_crlf = new_badges.replace("\n", "\r\n")

if old_badges in code:
    code = code.replace(old_badges, new_badges, 1)
    print("4. Replaced UI badges (LF)")
elif old_badges_crlf in code:
    code = code.replace(old_badges_crlf, new_badges_crlf, 1)
    print("4. Replaced UI badges (CRLF)")
else:
    print("4. UI badges target not found!")

with open("src/routes/claims.new.tsx", "w", encoding="utf-8") as f:
    f.write(code)

print("Finished updating src/routes/claims.new.tsx!")
