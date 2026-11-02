with open("src/routes/claims.new.tsx", "r", encoding="utf-8") as f:
    text = f.read()

target = """                              <div className="flex items-center gap-2">
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

replacement = """                              <div className="flex items-center gap-2">
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

target_crlf = target.replace("\n", "\r\n")
replacement_crlf = replacement.replace("\n", "\r\n")

if target in text:
    text = text.replace(target, replacement, 1)
    print("Replaced badges (LF)")
elif target_crlf in text:
    text = text.replace(target_crlf, replacement_crlf, 1)
    print("Replaced badges (CRLF)")
else:
    print("Badges target not found!")

# Also update draft saving to include uploadedFilesSummary
old_save_state = """      createdClaimUuid,
    };
    window.localStorage.setItem("claimbridge_preauth_workflow_draft", JSON.stringify(payload));"""

new_save_state = """      createdClaimUuid,
      uploadedFilesSummary: Object.fromEntries(
        Object.entries(uploadedFiles).map(([catKey, files]) => [
          catKey,
          files.map((f) => ({
            id: f.id,
            name: f.name,
            size: f.size,
            category: f.category,
            backendDocId: f.backendDocId,
            status: f.status,
            progressStage: f.progressStage,
            detectedCategory: f.detectedCategory,
            confidence: f.confidence,
            mismatchWarning: f.mismatchWarning,
            extractedFields: f.extractedFields,
            reliabilityScore: f.reliabilityScore,
          })),
        ])
      ),
    };
    window.localStorage.setItem("claimbridge_preauth_workflow_draft", JSON.stringify(payload));"""

old_save_state_crlf = old_save_state.replace("\n", "\r\n")
new_save_state_crlf = new_save_state.replace("\n", "\r\n")

if old_save_state in text:
    text = text.replace(old_save_state, new_save_state, 1)
    print("Replaced saveStateToLocalStorage (LF)")
elif old_save_state_crlf in text:
    text = text.replace(old_save_state_crlf, new_save_state_crlf, 1)
    print("Replaced saveStateToLocalStorage (CRLF)")
else:
    print("saveStateToLocalStorage target not found!")

# Also update saveStateToLocalStorage dependency array to include uploadedFiles
old_deps = """    aadhaarVerificationStatus,
    diagnosisList,
  ]);"""

new_deps = """    aadhaarVerificationStatus,
    diagnosisList,
    uploadedFiles,
  ]);"""

old_deps_crlf = old_deps.replace("\n", "\r\n")
new_deps_crlf = new_deps.replace("\n", "\r\n")

if old_deps in text:
    text = text.replace(old_deps, new_deps, 1)
    print("Replaced saveStateToLocalStorage deps (LF)")
elif old_deps_crlf in text:
    text = text.replace(old_deps_crlf, new_deps_crlf, 1)
    print("Replaced saveStateToLocalStorage deps (CRLF)")
else:
    print("deps target not found!")

# Also restore uploadedFiles in RESTORE DRAFT FROM LOCAL STORAGE ON MOUNT
old_restore = """        if (d.createdClaimUuid) setCreatedClaimUuid(d.createdClaimUuid);
      }
    } catch {"""

new_restore = """        if (d.createdClaimUuid) setCreatedClaimUuid(d.createdClaimUuid);
        if (d.uploadedFilesSummary && typeof d.uploadedFilesSummary === "object") {
          setUploadedFiles((prev) => ({ ...prev, ...d.uploadedFilesSummary }));
          // Resume polling for any documents that had a backendDocId and were in-flight
          Object.entries(d.uploadedFilesSummary).forEach(([catId, files]: [string, any]) => {
            (files || []).forEach((f: any) => {
              if (
                f.backendDocId &&
                ["waiting", "uploading", "uploaded", "ocr_processing", "classifying", "extracting", "validating"].includes(f.status)
              ) {
                const catMeta = PRE_AUTH_CATEGORIES.find((c) => c.id === catId);
                const catDisplayName = catMeta?.name || catId;
                startDocumentStatusPolling(catId, f.id, f.backendDocId, catDisplayName, f.name);
              }
            });
          });
        }
      }
    } catch {"""

old_restore_crlf = old_restore.replace("\n", "\r\n")
new_restore_crlf = new_restore.replace("\n", "\r\n")

if old_restore in text:
    text = text.replace(old_restore, new_restore, 1)
    print("Replaced restore draft (LF)")
elif old_restore_crlf in text:
    text = text.replace(old_restore_crlf, new_restore_crlf, 1)
    print("Replaced restore draft (CRLF)")
else:
    print("restore draft target not found!")

with open("src/routes/claims.new.tsx", "w", encoding="utf-8") as f:
    f.write(text)

print("Finished updating badges and draft persistence!")
