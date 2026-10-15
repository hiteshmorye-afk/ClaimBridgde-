import { createFileRoute } from "@tanstack/react-router";
import React from "react";
import { Link2, Activity, ShieldCheck, CheckCircle2, Send, Database, Server } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { exportToTPA } from "@/api/integrations";

import { useClaims } from "@/lib/claims";

export const Route = createFileRoute("/tpa-integration")({
  head: () => ({
    meta: [
      { title: "TPA Integration Center — ClaimBridge" },
      {
        name: "description",
        content: "HL7 FHIR / ISO20022 Claim payload pre-authorization & settlement gateway.",
      },
    ],
  }),
  component: TpaIntegrationPage,
});

function TpaIntegrationPage() {
  const claims = useClaims();
  const activeClaimId = claims[0]?.claimNumber || claims[0]?.id || "CLM-EXPORT-GATEWAY";

  const tpaGateways = [
    { name: "Pacific Healthcare TPA", status: "Connected", protocol: "HL7 FHIR v4", latency: "142 ms" },
    { name: "Star Health Gateway", status: "Connected", protocol: "REST / ISO20022", latency: "185 ms" },
    { name: "HDFC ERGO Enterprise", status: "Connected", protocol: "SOAP / FHIR", latency: "210 ms" },
    { name: "Niva Bupa Direct", status: "Connected", protocol: "REST API", latency: "165 ms" },
  ];

  return (
    <AppLayout
      title="TPA & Pre-Authorization Gateway"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "TPA Integration" }]}
    >
      <div className="space-y-6">
        
        {/* HEADER HERO */}
        <div className="flex flex-col justify-between gap-6 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-6 shadow-xl lg:flex-row lg:items-center">
          <div>
            <div className="flex items-center gap-2">
              <Link2 className="size-5 text-[#06B6D4]" />
              <span className="font-mono text-xs font-semibold text-[#06B6D4] uppercase tracking-wider">
                Enterprise Integration Gateway
              </span>
            </div>
            <h1 className="mt-1 text-2xl font-extrabold text-slate-900 dark:text-white sm:text-3xl">
              TPA Pre-Authorization & Settlement Protocols
            </h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              HL7 FHIR & ISO20022 payload dispatch connectors with real-time status Webhooks.
            </p>
          </div>

          <button
            onClick={() => exportToTPA(activeClaimId, "Pacific Healthcare TPA")}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] px-5 text-xs font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition"
          >
            <Send className="size-4" /> Trigger Test TPA Export Payload
          </button>
        </div>

        {/* GATEWAY CONNECTORS GRID */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {tpaGateways.map((gw) => (
            <div
              key={gw.name}
              className="rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-5 shadow-lg space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-[#10B981]">
                  <span className="size-2 rounded-full bg-[#10B981] animate-ping" /> {gw.status}
                </span>
                <span className="font-mono text-[10px] text-slate-500 dark:text-[#9CA3AF]">{gw.latency}</span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">{gw.name}</h4>
              <p className="font-mono text-xs text-[#06B6D4]">{gw.protocol}</p>
            </div>
          ))}
        </div>

      </div>
    </AppLayout>
  );
}
