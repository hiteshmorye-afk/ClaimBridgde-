import { createFileRoute, Link } from "@tanstack/react-router";
import React, { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Upload,
  Search,
  Eye,
  Download,
  RefreshCw,
  Loader2,
  Inbox,
  AlertCircle,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DOC_CATEGORIES } from "@/lib/claims";
import { DOCUMENT_CATALOGUE, DOCUMENT_SECTIONS } from "@/lib/documentCatalogue";
import { toast } from "sonner";
import { uploadDocument, processDocument, fetchDocuments, VaultDocument } from "@/api/documents";

export const Route = createFileRoute("/documents")({
  head: () => ({
    meta: [
      { title: "Document Vault — ClaimBridge" },
      {
        name: "description",
        content:
          "Multi-document OCR intake vault and verification repository.",
      },
    ],
  }),
  component: DocumentsPage,
});

function DocumentsPage() {
  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const filters: { search?: string; category?: string } = {};
      if (search.trim()) filters.search = search.trim();
      if (categoryFilter !== "All") filters.category = categoryFilter;
      const data = await fetchDocuments(filters);
      setDocuments(data || []);
    } catch (err: any) {
      console.warn("Failed to fetch documents:", err);
      toast.error("Failed to load documents vault from backend.");
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const filtered = documents.filter((doc) => {
    const matches =
      doc.name.toLowerCase().includes(search.toLowerCase()) ||
      doc.claimId.toLowerCase().includes(search.toLowerCase()) ||
      doc.category.toLowerCase().includes(search.toLowerCase());

    if (categoryFilter === "All") {
      return matches;
    }

    return matches && doc.category.toLowerCase().includes(categoryFilter.toLowerCase());
  });

  const handleUpload = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];

    if (!file) {
      return;
    }

    try {
      toast.info(`Uploading ${file.name}...`, {
        description:
          "Sending document to the ClaimBridge intake API.",
      });

      const result = await uploadDocument(
        file,
        "Auto-Detect"
      );

      if (!result) {
        throw new Error(
          "The backend did not return a document ID."
        );
      }

      toast.info(`Processing ${file.name} with ClaimBridge AI...`, {
        description: "Executing PDF OCR, classification, and extraction.",
      });

      const procResult = await processDocument(result.documentId);
      const detectedCat =
        procResult?.pipeline?.classification?.document_type ||
        result.category ||
        "Document";

      toast.success(
        `${file.name} processed: Classified as ${detectedCat.replace(/_/g, " ").toUpperCase()}`,
        {
          description: `Claim Readiness: ${procResult?.pipeline?.claim_readiness?.readiness_score || 0}%`,
        }
      );
      loadDocuments();
    } catch (error: any) {
      console.error(
        "ClaimBridge document upload failed:",
        error
      );

      toast.error(
        `Failed to upload ${file.name}`,
        {
          description:
            error?.message ||
            "Unable to connect to the ClaimBridge backend.",
        }
      );
    } finally {
      e.target.value = "";
    }
  };

  return (
    <AppLayout
      title="Document Repository & OCR Vault"
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Documents" },
      ]}
    >
      <div className="space-y-6">

        {/* HEADER & UPLOAD ACTION */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">
              Document Vault & Intake
            </h1>

            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Multi-document OCR key-value extraction repository
              & document category vault.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadDocuments}
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] px-3.5 text-xs font-semibold text-slate-700 dark:text-white hover:border-[#3B82F6] transition shadow-sm"
            >
              <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>

            <label className="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-5 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition">
              <Upload className="size-4" />

              Upload Document

              <input
                type="file"
                accept=".png,.jpg,.jpeg,.pdf"
                onChange={handleUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>

        {/* SEARCH & CATEGORY FILTERS */}
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">

          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />

            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search document name, claim ID..."
              className="h-10 w-full rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] pl-9 pr-3 text-xs text-slate-900 dark:text-white outline-none focus:border-[#3B82F6]"
            />
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="h-10 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] px-3 text-xs font-semibold text-slate-800 dark:text-white outline-none focus:border-[#3B82F6]"
            >
              <option value="All">All Categories (15 Document Types)</option>
              {DOCUMENT_SECTIONS.map((sec) => (
                <optgroup key={sec.id} label={sec.title}>
                  {DOCUMENT_CATALOGUE.filter((c) => c.section === sec.id).map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>

            <div className="hidden lg:flex items-center gap-1.5">
              {["All", "Final Hospital Bill", "Discharge Summary", "Duly Filled Claim Form", "KYC"].map((label) => {
                const isActive = label === "All" ? categoryFilter === "All" : categoryFilter.toLowerCase().includes(label.toLowerCase());
                return (
                  <button
                    key={label}
                    onClick={() => {
                      if (label === "All") setCategoryFilter("All");
                      else {
                        const found = DOCUMENT_CATALOGUE.find((c) => c.name.toLowerCase().includes(label.toLowerCase()));
                        if (found) setCategoryFilter(found.name);
                      }
                    }}
                    className={`rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition ${
                      isActive
                        ? "bg-[#3B82F6] text-white"
                        : "bg-slate-100 dark:bg-[#0B0F17] text-slate-600 dark:text-[#9CA3AF] hover:text-white"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* DOCUMENTS TABLE */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] shadow-xl">

          <div className="overflow-x-auto">

            <table className="w-full text-left">

              <thead className="bg-slate-50 dark:bg-[#0E1420] text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-[#9CA3AF]">

                <tr className="border-b border-slate-200 dark:border-[#1F2937]">

                  <th className="px-6 py-3.5">
                    Document File
                  </th>

                  <th className="px-6 py-3.5">
                    Category
                  </th>

                  <th className="px-6 py-3.5">
                    Linked Claim
                  </th>

                  <th className="px-6 py-3.5">
                    OCR Accuracy
                  </th>

                  <th className="px-6 py-3.5">
                    File Size
                  </th>

                  <th className="px-6 py-3.5">
                    Status
                  </th>

                  <th className="px-6 py-3.5 text-right">
                    Actions
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y divide-slate-200 dark:divide-[#1F2937] text-xs">

                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Loader2 className="size-6 animate-spin text-[#3B82F6]" />
                        <span className="text-xs font-semibold">Loading documents vault from backend...</span>
                      </div>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Inbox className="size-8 text-slate-400" />
                        <p className="text-sm font-bold text-slate-900 dark:text-white">No documents found in vault</p>
                        <p className="text-xs text-slate-500 dark:text-[#9CA3AF] max-w-sm">
                          {search || categoryFilter !== "All"
                            ? "No documents match the current filter criteria."
                            : "No claim documents have been uploaded to the active workspace yet."}
                        </p>
                        <Link
                          to="/claims/new"
                          className="mt-2 inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-4 py-2 text-xs font-semibold text-white shadow-md shadow-[#3B82F6]/30"
                        >
                          Create Claim & Upload Documents
                        </Link>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filtered.map((doc) => (

                  <tr
                    key={doc.id}
                    className="transition hover:bg-slate-50 dark:hover:bg-[#1F2937]/40"
                  >

                    <td className="px-6 py-4">

                      <div className="flex items-center gap-3">

                        <div className="flex size-9 items-center justify-center rounded-xl bg-[#3B82F6]/15 text-[#3B82F6]">
                          <FileText className="size-5" />
                        </div>

                        <div>

                          <p className="font-semibold text-slate-900 dark:text-white">
                            {doc.name}
                          </p>

                          <p className="text-[10px] text-slate-500 dark:text-[#9CA3AF]">
                            {doc.date}
                          </p>

                        </div>

                      </div>

                    </td>

                    <td className="px-6 py-4 font-semibold text-slate-700 dark:text-[#9CA3AF]">
                      {doc.category}
                    </td>

                    <td className="px-6 py-4 font-mono font-bold text-[#3B82F6]">
                      {doc.claimUuid ? (
                        <Link
                          to="/claims/$claimId"
                          params={{ claimId: doc.claimUuid }}
                          className="hover:underline"
                        >
                          {doc.claimId}
                        </Link>
                      ) : (
                        doc.claimId
                      )}
                    </td>

                    <td className="px-6 py-4">
                      <span className="font-mono font-bold text-[#06B6D4]">
                        {doc.confidence}%
                      </span>
                    </td>

                    <td className="px-6 py-4 font-mono text-slate-500 dark:text-[#9CA3AF]">
                      {doc.size}
                    </td>

                    <td className="px-6 py-4">

                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${
                          doc.status === "Verified"
                            ? "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981]"
                            : "border-[#EF4444]/40 bg-[#EF4444]/10 text-[#EF4444]"
                        }`}
                      >
                        {doc.status}
                      </span>

                    </td>

                    <td className="px-6 py-4 text-right">

                      <div className="flex items-center justify-end gap-2">

                        {doc.claimUuid ? (
                          <Link
                            to="/claims/$claimId"
                            params={{ claimId: doc.claimUuid }}
                            className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#3B82F6] transition"
                            title="Inspect Document in Claim Dossier"
                          >
                            <Eye className="size-4" />
                          </Link>
                        ) : (
                          <button
                            onClick={() =>
                              toast.info(
                                `Viewing ${doc.name} metadata`
                              )
                            }
                            className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#3B82F6]"
                          >
                            <Eye className="size-4" />
                          </button>
                        )}

                        <button
                          onClick={() =>
                            toast.success(
                              `Downloading ${doc.name}`
                            )
                          }
                          className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#10B981]"
                        >
                          <Download className="size-4" />
                        </button>

                      </div>

                    </td>

                  </tr>

                )))}

              </tbody>

            </table>

          </div>

        </div>

      </div>
    </AppLayout>
  );
}