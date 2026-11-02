import React, { useState, useEffect } from "react";
import {
  X,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  FileText,
  DollarSign,
  AlertCircle,
  HelpCircle,
  Download,
  Info,
  RefreshCw,
} from "lucide-react";
import {
  fetchDischargeReadiness,
  DischargeReadinessResponse,
} from "@/api/cashless";
import { toast } from "sonner";

interface DischargeReadinessModalProps {
  claimId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DischargeReadinessModal({
  claimId,
  isOpen,
  onClose,
}: DischargeReadinessModalProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DischargeReadinessResponse | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchDischargeReadiness(claimId);
      setData(res);
    } catch (err: any) {
      toast.error(err?.message || "Failed to load discharge readiness status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [claimId, isOpen]);

  if (!isOpen) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CLEARED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="w-4 h-4" /> Ready for Discharge Clearance
          </span>
        );
      case "PENDING_SETTLEMENT":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-300 dark:border-amber-800">
            <Clock className="w-4 h-4" /> Awaiting Final Insurer Approval
          </span>
        );
      case "QUERY_PENDING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-400 border border-red-300 dark:border-red-800">
            <AlertTriangle className="w-4 h-4" /> Outstanding Queries Raised
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <AlertCircle className="w-4 h-4" /> Not Ready for Discharge
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 dark:border-slate-800 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Discharge Readiness Assessment
              </h3>
              {data && getStatusBadge(data.readiness_status)}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Advisory clinical and administrative readiness verification for hospital billing desk.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {loading ? (
            <div className="py-12 text-center text-slate-500">
              <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-3 text-primary-500" />
              <p>Analyzing cashless claim settlement criteria...</p>
            </div>
          ) : !data ? (
            <div className="py-8 text-center text-red-500">
              Failed to load readiness details.
            </div>
          ) : (
            <>
              {/* Caution Banner */}
              <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                <div className="text-xs text-blue-800 dark:text-blue-300">
                  <strong className="font-semibold">Statutory Governance:</strong> This system does not automatically discharge the patient. Hospital billing and clinical authorities must physically verify settlement letters and patient collection before signing discharge slips.
                </div>
              </div>

              {/* Patient & Financial Snapshot */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">Estimated Cost</div>
                  <div className="text-base font-bold text-slate-800 dark:text-slate-100">
                    ₹{data.estimated_cost?.toLocaleString("en-IN") || 0}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">Initial Auth</div>
                  <div className="text-base font-bold text-blue-600 dark:text-blue-400">
                    ₹{data.initial_approved_amount?.toLocaleString("en-IN") || 0}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">Final Approved</div>
                  <div className="text-base font-bold text-emerald-600 dark:text-emerald-400">
                    ₹{data.final_approved_amount?.toLocaleString("en-IN") || 0}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900">
                  <div className="text-[11px] text-rose-600 dark:text-rose-400">Patient Due</div>
                  <div className="text-base font-bold text-rose-700 dark:text-rose-300">
                    ₹{data.patient_responsibility?.toLocaleString("en-IN") || 0}
                  </div>
                </div>
              </div>

              {/* Checklist */}
              <div>
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary-500" />
                  Readiness Criteria Assessment
                </h4>
                <div className="space-y-2">
                  {data.discharge_checklist.map((c, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl border flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/30 border-slate-200 dark:border-slate-800"
                    >
                      <div className="space-y-0.5">
                        <div className="font-medium text-slate-800 dark:text-slate-200">
                          {c.item}
                        </div>
                        <div className="text-xs text-slate-500">{c.details}</div>
                      </div>
                      <div>
                        {c.status === "PASS" ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Pass
                          </span>
                        ) : c.status === "WARN" ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
                            <AlertCircle className="w-3.5 h-3.5" /> Review
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-800">
                            <AlertTriangle className="w-3.5 h-3.5" /> Blocked
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Outstanding Queries if any */}
              {data.outstanding_queries && data.outstanding_queries.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800">
                  <h5 className="font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5 mb-2">
                    <AlertTriangle className="w-4 h-4" /> Active Queries Requiring Resolution
                  </h5>
                  <ul className="list-disc list-inside space-y-1 text-xs text-amber-700 dark:text-amber-400">
                    {data.outstanding_queries.map((q, idx) => (
                      <li key={idx}>{q}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
