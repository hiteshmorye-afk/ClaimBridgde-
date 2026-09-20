import React from "react";
import { Stethoscope, Activity, ShieldAlert, CheckCircle2, FileCheck2, AlertCircle } from "lucide-react";
import { MedicalServiceItem, formatINR } from "@/lib/claims";

interface MedicalIntelligenceProps {
  diagnosis: string;
  medicalRiskScore: number; // e.g. 50
  medicalConfidence: number; // e.g. 70
  services: MedicalServiceItem[];
}

export function MedicalIntelligence({
  diagnosis = "Acute Gastroenteritis & Severe Dehydration (ICD-10: A09)",
  medicalRiskScore = 50,
  medicalConfidence = 70,
  services = [],
}: MedicalIntelligenceProps) {
  const getRiskColor = (score: number) => {
    if (score <= 30) return "text-[#10B981] border-[#10B981]/30 bg-[#10B981]/10";
    if (score <= 60) return "text-[#F59E0B] border-[#F59E0B]/30 bg-[#F59E0B]/10";
    return "text-[#EF4444] border-[#EF4444]/30 bg-[#EF4444]/10";
  };

  return (
    <div className="space-y-6">
      
      {/* MEDICAL INTELLIGENCE METRICS CARDS */}
      <div className="grid gap-4 sm:grid-cols-3">
        
        {/* Diagnosis Header */}
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl sm:col-span-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#06B6D4] uppercase tracking-wider">
            <Stethoscope className="size-4" /> Diagnosed Condition
          </div>
          <h4 className="mt-3 text-base font-bold text-white leading-snug">{diagnosis}</h4>
          <p className="mt-2 text-xs text-[#9CA3AF]">Mapped against ICD-10 & Clinical Care Protocols</p>
        </div>

        {/* Medical Risk Score */}
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl">
          <div className="flex items-center justify-between text-xs text-[#9CA3AF]">
            <span>Medical Risk Score</span>
            <ShieldAlert className="size-4 text-[#F59E0B]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold font-mono text-[#F59E0B]">{medicalRiskScore}</span>
            <span className="text-xs text-[#9CA3AF]">/ 100</span>
          </div>
          <div className={`mt-2 inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${getRiskColor(medicalRiskScore)}`}>
            <AlertCircle className="size-3" /> Moderate Risk Profile
          </div>
        </div>

        {/* Medical Confidence */}
        <div className="rounded-2xl border border-[#1F2937] bg-[#111827] p-5 shadow-xl">
          <div className="flex items-center justify-between text-xs text-[#9CA3AF]">
            <span>Medical AI Confidence</span>
            <Activity className="size-4 text-[#3B82F6]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold font-mono text-[#3B82F6]">{medicalConfidence}%</span>
          </div>
          <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-[#3B82F6]/30 bg-[#3B82F6]/10 px-2.5 py-0.5 text-[10px] font-semibold text-[#3B82F6]">
            <CheckCircle2 className="size-3" /> Clinical Evidence Verified
          </div>
        </div>

      </div>

      {/* ITEMIZED MEDICAL SERVICES TABLE */}
      <div className="overflow-hidden rounded-2xl border border-[#1F2937] bg-[#111827] shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1F2937] px-6 py-4 bg-[#0B0F17]">
          <div>
            <h3 className="text-base font-bold text-white">Itemized Medical Services & Procedures</h3>
            <p className="text-xs text-[#9CA3AF]">Reconciliation of hospital charges against treatment guidelines</p>
          </div>
          <span className="rounded-full bg-[#1F2937] px-3 py-1 font-mono text-xs text-[#06B6D4]">
            {services.length} Line Items
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#0E1420] text-[11px] font-semibold uppercase tracking-wider text-[#9CA3AF]">
              <tr className="border-b border-[#1F2937]">
                <th className="px-6 py-3">Service Name</th>
                <th className="px-6 py-3">CPT / ICD Code</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3 text-right">Qty</th>
                <th className="px-6 py-3 text-right">Unit Cost</th>
                <th className="px-6 py-3 text-right">Total</th>
                <th className="px-6 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937] text-xs">
              {services.map((srv) => (
                <tr key={srv.id} className="transition hover:bg-[#1F2937]/30">
                  <td className="px-6 py-4 font-semibold text-white">{srv.serviceName}</td>
                  <td className="px-6 py-4 font-mono text-[#06B6D4]">{srv.code}</td>
                  <td className="px-6 py-4 text-[#9CA3AF]">{srv.category}</td>
                  <td className="px-6 py-4 text-right font-mono text-white">{srv.quantity}</td>
                  <td className="px-6 py-4 text-right font-mono text-[#9CA3AF]">{formatINR(srv.unitCost)}</td>
                  <td className="px-6 py-4 text-right font-mono font-bold text-white">{formatINR(srv.totalCost)}</td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${
                        srv.coverageStatus === "Covered"
                          ? "border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]"
                          : srv.coverageStatus === "Co-pay Applied"
                          ? "border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B]"
                          : "border-[#EF4444]/30 bg-[#EF4444]/10 text-[#EF4444]"
                      }`}
                    >
                      {srv.coverageStatus}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
