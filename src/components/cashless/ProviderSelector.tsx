import React, { useEffect, useState } from "react";
import { fetchInsuranceProviders, InsuranceProvider } from "@/api/cashless";
import { Building2, Phone, Mail, Globe, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ProviderSelectorProps {
  selectedProvider: string;
  onSelectProvider: (providerName: string, providerCode: string) => void;
  disabled?: boolean;
}

const FALLBACK_PROVIDERS: InsuranceProvider[] = [
  {
    id: "star",
    name: "Star Health and Allied Insurance",
    code: "STAR_HEALTH",
    providerType: "Insurer",
    officialWebsite: "https://www.starhealth.in",
    officialPortalUrl: "https://www.starhealth.in/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "diagnostic_report"],
    providerNotes: "Official insurer portal is used for claim submission when the policy is active.",
    contactPhone: "1800-425-2255",
    contactEmail: "claims@starhealth.in",
    portalUrl: "https://www.starhealth.in/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "hdfc",
    name: "HDFC ERGO General Insurance",
    code: "HDFC_ERGO",
    providerType: "Insurer",
    officialWebsite: "https://www.hdfcergo.com",
    officialPortalUrl: "https://www.hdfcergo.com/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "hospital_bill"],
    providerNotes: "Use the verified official portal for cashless authorization and final settlement submissions.",
    contactPhone: "022-6234-6234",
    contactEmail: "healthclaims@hdfcergo.com",
    portalUrl: "https://www.hdfcergo.com/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "care",
    name: "Care Health Insurance",
    code: "CARE_HEALTH",
    providerType: "Insurer",
    officialWebsite: "https://www.careinsurance.com",
    officialPortalUrl: "https://www.careinsurance.com/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "pre_authorization"],
    providerNotes: "Portal submission is the standard route for hospital coordination and pre-auth work.",
    contactPhone: "1800-102-4488",
    contactEmail: "customerfirst@careinsurance.com",
    portalUrl: "https://www.careinsurance.com/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "niva",
    name: "Niva Bupa Health Insurance",
    code: "NIVA_BUPA",
    providerType: "Insurer",
    officialWebsite: "https://www.nivabupa.com",
    officialPortalUrl: "https://www.nivabupa.com/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "diagnostic_report"],
    providerNotes: "Cashless packages should be marked as portal_redirect unless an insurer API is formally configured.",
    contactPhone: "1860-500-8888",
    contactEmail: "customercare@nivabupa.com",
    portalUrl: "https://www.nivabupa.com/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "icici",
    name: "ICICI Lombard General Insurance",
    code: "ICICI_LOMBARD",
    providerType: "Insurer",
    officialWebsite: "https://www.icicilombard.com",
    officialPortalUrl: "https://www.icicilombard.com/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "hospital_bill"],
    providerNotes: "Portal-based documentation is preferred unless a verified API credential is configured.",
    contactPhone: "1800-2666",
    contactEmail: "healthclaims@icicilombard.com",
    portalUrl: "https://www.icicilombard.com/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "bajaj",
    name: "Bajaj Allianz General Insurance",
    code: "BAJAJ_ALLIANZ",
    providerType: "Insurer",
    officialWebsite: "https://www.bajajallianz.com",
    officialPortalUrl: "https://www.bajajallianz.com/claims",
    submissionMode: "portal_redirect",
    requiredDocumentCategories: ["claim_form", "insurance_card", "identity_proof", "diagnostic_report"],
    providerNotes: "Manual confirmation should be used until a verified insurer integration is configured.",
    contactPhone: "1800-209-5858",
    contactEmail: "bagichelp@bajajallianz.co.in",
    portalUrl: "https://www.bajajallianz.com/claims",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
  {
    id: "pacific",
    name: "Pacific Healthcare TPA",
    code: "PACIFIC_TPA",
    providerType: "TPA",
    officialWebsite: "https://portal.pacifichealth.in",
    officialPortalUrl: "https://portal.pacifichealth.in",
    submissionMode: "manual",
    requiredDocumentCategories: ["pre_authorization", "insurance_card", "identity_proof", "hospital_bill"],
    providerNotes: "TPA portal credentials should be configured before enabling API-based submission.",
    contactPhone: "1800-111-9999",
    contactEmail: "tpa@pacifichealth.in",
    portalUrl: "https://portal.pacifichealth.in",
    supportedClaimTypes: ["cashless", "reimbursement"],
    isActive: true,
  },
];

export const ProviderSelector: React.FC<ProviderSelectorProps> = ({
  selectedProvider,
  onSelectProvider,
  disabled = false,
}) => {
  const [providers, setProviders] = useState<InsuranceProvider[]>(FALLBACK_PROVIDERS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const res = await fetchInsuranceProviders(true);
        if (mounted && res.data && res.data.length > 0) {
          setProviders(res.data);
        }
      } catch {
        // Fall back gracefully
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const selected = providers.find((p) => p.name === selectedProvider) || null;
  const selectedPortalUrl = selected?.officialPortalUrl || selected?.portalUrl;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Building2 className="w-3.5 h-3.5 text-primary" />
          Insurance Provider / TPA Directory
        </label>
        {loading && <span className="text-xs text-muted-foreground animate-pulse">Syncing directory...</span>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {providers.map((p) => {
          const isSelected = p.name === selectedProvider;
          return (
            <button
              key={p.code}
              type="button"
              disabled={disabled}
              onClick={() => onSelectProvider(p.name, p.code)}
              className={`p-3 rounded-lg border text-left transition-all relative ${
                isSelected
                  ? "border-primary bg-primary/5 ring-1 ring-primary shadow-sm"
                  : "border-border hover:border-border/80 hover:bg-muted/40"
              } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-medium text-xs text-foreground line-clamp-1">{p.name}</div>
                {isSelected && <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />}
              </div>

              <div className="mt-2 flex flex-wrap gap-1">
                {p.providerType && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex items-center gap-1 text-muted-foreground font-normal">
                    {p.providerType}
                  </Badge>
                )}
                {p.contactPhone && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex items-center gap-1 text-muted-foreground font-normal">
                    <Phone className="w-2.5 h-2.5" />
                    {p.contactPhone}
                  </Badge>
                )}
                {p.contactEmail && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex items-center gap-1 text-muted-foreground font-normal">
                    <Mail className="w-2.5 h-2.5" />
                    Support
                  </Badge>
                )}
                {(p.officialPortalUrl || p.portalUrl) && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex items-center gap-1 text-muted-foreground font-normal">
                    <Globe className="w-2.5 h-2.5" />
                    {(p.submissionMode || "portal").replace("_", " ")}
                  </Badge>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {selected && (
        <div className="p-2.5 bg-muted/30 border border-border/60 rounded-md text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
          <span>
            Selected: <strong className="text-foreground">{selected.name}</strong> ({selected.code})
          </span>
          <div className="flex gap-2 text-[11px]">
            {selected.providerType && <span>{selected.providerType}</span>}
            {selected.contactPhone && <span>Toll-Free: {selected.contactPhone}</span>}
            {selectedPortalUrl && (
              <a
                href={selectedPortalUrl}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline inline-flex items-center gap-1"
              >
                {selected.submissionMode === "manual" ? "Manual Portal" : "Official Portal"} &rarr;
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
