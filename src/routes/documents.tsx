import { createFileRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import {
  FileText,
  Upload,
  Search,
  Eye,
  Download,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DOC_CATEGORIES } from "@/lib/claims";
import { toast } from "sonner";
import { uploadDocument, processDocument } from "@/api/documents";

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

const sampleDocuments = [
  {
    id: "DOC-001",
    name: "chong_hua_bill_184k.pdf",
    category: "Hospital Bill",
    claimId: "CLM-TEST-001",
    confidence: 98.93,
    status: "Verified",
    size: "2.4 MB",
    date: "19.05.2019",
  },
  {
    id: "DOC-002",
    name: "discharge_summary_tuhod.pdf",
    category: "Discharge Summary",
    claimId: "CLM-TEST-001",
    confidence: 99.1,
    status: "Verified",
    size: "1.8 MB",
    date: "19.05.2019",
  },
  {
    id: "DOC-003",
    name: "pacific_health_card.png",
    category: "Insurance Card",
    claimId: "CLM-TEST-001",
    confidence: 97.5,
    status: "Verified",
    size: "850 KB",
    date: "16.05.2019",
  },
  {
    id: "DOC-004",
    name: "rx_medications_may2019.pdf",
    category: "Prescription",
    claimId: "CLM-TEST-001",
    confidence: 98.2,
    status: "Verified",
    size: "620 KB",
    date: "16.05.2019",
  },
  {
    id: "DOC-005",
    name: "stent_bill.pdf",
    category: "Hospital Bill",
    claimId: "CLM-2026-0891",
    confidence: 96.4,
    status: "Mismatch",
    size: "3.1 MB",
    date: "26.07.2026",
  },
  {
    id: "DOC-006",
    name: "star_health_card.pdf",
    category: "Insurance Card",
    claimId: "CLM-2026-0892",
    confidence: 99.4,
    status: "Verified",
    size: "1.2 MB",
    date: "18.07.2026",
  },
];

function DocumentsPage() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");

  const filtered = sampleDocuments.filter((doc) => {
    const matches =
      doc.name.toLowerCase().includes(search.toLowerCase()) ||
      doc.claimId.toLowerCase().includes(search.toLowerCase()) ||
      doc.category.toLowerCase().includes(search.toLowerCase());

    if (categoryFilter === "All") {
      return matches;
    }

    return matches && doc.category === categoryFilter;
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

          <div className="flex flex-wrap gap-1.5 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-100 dark:bg-[#0B0F17] p-1">

            <button
              onClick={() => setCategoryFilter("All")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                categoryFilter === "All"
                  ? "bg-[#3B82F6] text-white shadow-sm"
                  : "text-slate-600 dark:text-[#9CA3AF] hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              All Categories
            </button>

            {DOC_CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  categoryFilter === cat
                    ? "bg-[#3B82F6] text-white shadow-sm"
                    : "text-slate-600 dark:text-[#9CA3AF] hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                {cat}
              </button>
            ))}

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

                {filtered.map((doc) => (

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
                      {doc.claimId}
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

                        <button
                          onClick={() =>
                            toast.info(
                              `Viewing ${doc.name} preview`
                            )
                          }
                          className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#3B82F6]"
                        >
                          <Eye className="size-4" />
                        </button>

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

                ))}

              </tbody>

            </table>

          </div>

        </div>

      </div>
    </AppLayout>
  );
}