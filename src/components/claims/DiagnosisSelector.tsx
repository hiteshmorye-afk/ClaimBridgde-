import React, { useState, useRef, useEffect } from "react";
import {
  Search,
  ChevronDown,
  Check,
  ShieldCheck,
  AlertTriangle,
  FileQuestion,
  Info,
  Stethoscope,
  X,
} from "lucide-react";
import {
  CLINICAL_DIAGNOSIS_CATALOGUE,
  DiagnosisItem,
  UNLISTED_DIAGNOSIS_CODE,
} from "@/lib/clinicalCatalogue";

interface DiagnosisSelectorProps {
  selectedCode: string;
  customDiagnosis: string;
  clinicalNotes: string;
  onSelectDiagnosis: (item: DiagnosisItem | null) => void;
  onCustomDiagnosisChange: (val: string) => void;
  onClinicalNotesChange: (val: string) => void;
  error?: string;
}

export function DiagnosisSelector({
  selectedCode,
  customDiagnosis,
  clinicalNotes,
  onSelectDiagnosis,
  onCustomDiagnosisChange,
  onClinicalNotesChange,
  error,
}: DiagnosisSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const selectedItem =
    CLINICAL_DIAGNOSIS_CATALOGUE.find((d) => d.code === selectedCode) || null;
  const isUnlisted = selectedCode === UNLISTED_DIAGNOSIS_CODE;

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredDiagnoses = CLINICAL_DIAGNOSIS_CATALOGUE.filter((item) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      item.display.toLowerCase().includes(q) ||
      item.code.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  });

  const handleSelect = (item: DiagnosisItem) => {
    onSelectDiagnosis(item);
    setIsOpen(false);
    setSearchQuery("");
  };

  const handleSelectUnlisted = () => {
    onSelectDiagnosis({
      code: UNLISTED_DIAGNOSIS_CODE,
      display: "Other / Unlisted Clinical Diagnosis",
      category: "Unlisted Condition",
      codeSystem: "Unresolved",
      policyMapping: {
        status: "Policy mapping pending",
        clauseReference: "UNRESOLVED - MANUAL REVIEW REQUIRED",
        notes: "Unlisted diagnosis. Will be routed to a medical auditor for manual policy reconciliation.",
      },
    });
    setIsOpen(false);
    setSearchQuery("");
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectDiagnosis(null);
    onCustomDiagnosisChange("");
  };

  return (
    <div className="space-y-4" ref={dropdownRef}>
      {/* 1. DIAGNOSIS DROPDOWN TRIGGER */}
      <div className="relative">
        <label className="flex items-center justify-between text-xs font-semibold text-[#9CA3AF]">
          <span>
            Clinical Diagnosis & ICD-10 Code <span className="text-[#EF4444]">*</span>
          </span>
          <span className="text-[10px] text-[#6B7280]">
            ICD-10 Catalogue (Standard Clinical Coding)
          </span>
        </label>

        <div
          role="button"
          tabIndex={0}
          onClick={() => setIsOpen(!isOpen)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setIsOpen(!isOpen);
            }
          }}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          className={`mt-1.5 flex min-h-[46px] w-full cursor-pointer items-center justify-between rounded-xl border bg-[#0B0F17] px-3.5 py-2.5 text-left text-xs transition-colors ${
            error
              ? "border-[#EF4444] focus:ring-1 focus:ring-[#EF4444]"
              : isOpen
              ? "border-[#3B82F6] ring-1 ring-[#3B82F6]"
              : "border-[#1F2937] hover:border-[#374151]"
          }`}
        >
          <div className="flex flex-1 items-center gap-2 overflow-hidden">
            <Stethoscope className="size-4 shrink-0 text-[#3B82F6]" />
            {selectedItem ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-white">
                  {selectedItem.display}
                </span>
                <span className="inline-flex items-center rounded-md bg-[#3B82F6]/20 px-2 py-0.5 font-mono text-[10px] font-bold text-[#3B82F6]">
                  ICD-10: {selectedItem.code}
                </span>
              </div>
            ) : isUnlisted ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-white">
                  Other / Unlisted Diagnosis
                </span>
                <span className="inline-flex items-center rounded-md bg-[#F59E0B]/20 px-2 py-0.5 font-mono text-[10px] font-bold text-[#F59E0B]">
                  Unresolved Code
                </span>
              </div>
            ) : (
              <span className="text-[#6B7280]">
                Search or select diagnosis by name or ICD-10 code (e.g. K81, Appendicitis)...
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 pl-2">
            {(selectedItem || isUnlisted) && (
              <button
                type="button"
                onClick={handleClear}
                title="Clear selection"
                className="rounded-md p-1 text-[#6B7280] hover:bg-[#1F2937] hover:text-white"
              >
                <X className="size-3.5" />
              </button>
            )}
            <ChevronDown
              className={`size-4 text-[#9CA3AF] transition-transform duration-200 ${
                isOpen ? "rotate-180 text-[#3B82F6]" : ""
              }`}
            />
          </div>
        </div>

        {error && (
          <p className="mt-1 text-[11px] font-medium text-[#EF4444]">{error}</p>
        )}

        {/* 2. SEARCHABLE DROPDOWN POPOVER */}
        {isOpen && (
          <div className="absolute z-50 mt-1.5 w-full rounded-2xl border border-[#1F2937] bg-[#111827] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
            {/* SEARCH INPUT */}
            <div className="border-b border-[#1F2937] p-2.5">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 size-3.5 text-[#9CA3AF]" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter by disease name, ICD-10 code, or organ system..."
                  className="h-9 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] pl-8 pr-3 text-xs text-white placeholder-[#6B7280] outline-none focus:border-[#3B82F6]"
                />
              </div>
            </div>

            {/* LIST OF OPTIONS */}
            <div className="max-h-64 overflow-y-auto p-1.5 divide-y divide-[#1F2937]/50">
              {filteredDiagnoses.length > 0 ? (
                filteredDiagnoses.map((item) => {
                  const isSelected = selectedCode === item.code;
                  return (
                    <button
                      key={item.code}
                      type="button"
                      onClick={() => handleSelect(item)}
                      className={`flex w-full items-start justify-between rounded-xl p-2.5 text-left transition-colors ${
                        isSelected
                          ? "bg-[#3B82F6]/15 text-white"
                          : "text-[#D1D5DB] hover:bg-[#1F2937]/70 hover:text-white"
                      }`}
                    >
                      <div className="space-y-1 pr-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold">{item.display}</span>
                          <span className="font-mono text-[10px] font-bold text-[#3B82F6] bg-[#3B82F6]/15 px-1.5 py-0.5 rounded">
                            {item.code}
                          </span>
                        </div>
                        <p className="text-[10px] text-[#9CA3AF]">{item.category}</p>
                      </div>

                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                            item.policyMapping.status === "Potentially Covered"
                              ? "bg-[#10B981]/20 text-[#10B981]"
                              : item.policyMapping.status === "Excluded"
                              ? "bg-[#EF4444]/20 text-[#EF4444]"
                              : "bg-[#F59E0B]/20 text-[#F59E0B]"
                          }`}
                        >
                          {item.policyMapping.status}
                        </span>
                        {isSelected && <Check className="size-3.5 text-[#3B82F6]" />}
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-[#9CA3AF]">
                  No matching diagnosis found in the configured ICD-10 catalogue.
                </div>
              )}

              {/* UNLISTED DIAGNOSIS PATHWAY */}
              <button
                type="button"
                onClick={handleSelectUnlisted}
                className={`flex w-full items-center justify-between rounded-xl p-2.5 text-left transition-colors ${
                  isUnlisted
                    ? "bg-[#F59E0B]/15 text-white"
                    : "text-[#F59E0B] hover:bg-[#1F2937]/70"
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileQuestion className="size-4 shrink-0 text-[#F59E0B]" />
                  <div>
                    <span className="text-xs font-semibold">Other / Unlisted Diagnosis</span>
                    <p className="text-[10px] text-[#9CA3AF]">
                      Manually enter clinical description (marked as unresolved for review)
                    </p>
                  </div>
                </div>
                <span className="rounded bg-[#F59E0B]/20 px-1.5 py-0.5 font-mono text-[9px] font-bold text-[#F59E0B]">
                  Unresolved
                </span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 3. UNLISTED DIAGNOSIS INPUT PATHWAY */}
      {isUnlisted && (
        <div className="rounded-xl border border-[#F59E0B]/40 bg-[#F59E0B]/10 p-3.5 space-y-2.5">
          <div className="flex items-start gap-2 text-xs text-[#F59E0B]">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unlisted Clinical Condition</p>
              <p className="text-[11px] text-[#D1D5DB] mt-0.5">
                The diagnosis is not in the configured standard ICD-10 catalogue. Please specify the documented clinical description. It will be recorded as <strong>Unresolved</strong> and routed to an insurance medical officer for policy determination.
              </p>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[#D1D5DB]">
              Documented Diagnosis Description <span className="text-[#EF4444]">*</span>
            </label>
            <input
              type="text"
              value={customDiagnosis}
              onChange={(e) => onCustomDiagnosisChange(e.target.value)}
              placeholder="e.g., Acute Pancreatitis secondary to hypertriglyceridemia..."
              className="mt-1 h-9 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] px-3 text-xs text-white placeholder-[#6B7280] outline-none focus:border-[#F59E0B]"
            />
          </div>
        </div>
      )}

      {/* 4. SELECTED DIAGNOSIS & POLICY MAPPING CARD */}
      {selectedItem && (
        <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17] p-3.5 space-y-3">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-2.5">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-[#3B82F6] bg-[#3B82F6]/20 px-2 py-0.5 rounded-md">
                {selectedItem.code}
              </span>
              <span className="text-xs font-bold text-white">
                {selectedItem.display}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span
                className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold ${
                  selectedItem.policyMapping.status === "Potentially Covered"
                    ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30"
                    : selectedItem.policyMapping.status === "Excluded"
                    ? "bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/30"
                    : "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/30"
                }`}
              >
                {selectedItem.policyMapping.status === "Potentially Covered" ? (
                  <ShieldCheck className="size-3" />
                ) : selectedItem.policyMapping.status === "Excluded" ? (
                  <AlertTriangle className="size-3" />
                ) : (
                  <Info className="size-3" />
                )}
                {selectedItem.policyMapping.status}
              </span>
            </div>
          </div>

          <div className="space-y-1.5 text-xs text-[#9CA3AF]">
            <div className="flex items-start gap-1.5">
              <span className="font-mono text-[10px] text-[#6B7280] uppercase tracking-wider shrink-0 mt-0.5">
                Clause Ref:
              </span>
              <span className="font-mono text-[11px] text-[#06B6D4]">
                {selectedItem.policyMapping.clauseReference}
              </span>
            </div>

            <p className="text-[11px] text-[#D1D5DB] leading-relaxed">
              {selectedItem.policyMapping.notes}
            </p>

            {selectedItem.policyMapping.evidenceSnippet && (
              <div className="mt-1 rounded-lg bg-[#111827] border border-[#1F2937] p-2 text-[10px] italic text-[#9CA3AF]">
                "{selectedItem.policyMapping.evidenceSnippet}"
              </div>
            )}
          </div>

          <div className="flex items-center gap-1 text-[10px] text-[#6B7280] border-t border-[#1F2937]/70 pt-2">
            <Info className="size-3 shrink-0 text-[#9CA3AF]" />
            <span>
              Clause reference from standard policy rules. Final claim settlement requires itemized invoice and medical record verification in the AI pipeline.
            </span>
          </div>
        </div>
      )}

      {/* 5. SUPPLEMENTARY CLINICAL NOTES */}
      <div>
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-[#9CA3AF]">
            Supplementary Clinical Notes & Attending Physician Remarks
          </label>
          <span className="text-[10px] text-[#6B7280]">Optional</span>
        </div>
        <textarea
          rows={2}
          value={clinicalNotes}
          onChange={(e) => onClinicalNotesChange(e.target.value)}
          placeholder="e.g., Patient presented with 3-day history of right upper quadrant pain, ultrasound confirmed cholelithiasis. No surgical complications..."
          className="mt-1 w-full rounded-xl border border-[#1F2937] bg-[#0B0F17] p-3 text-xs text-white placeholder-[#6B7280] outline-none focus:border-[#3B82F6]"
        />
      </div>
    </div>
  );
}
