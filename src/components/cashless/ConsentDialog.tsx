import React, { useState } from "react";
import { recordPatientConsent, PatientConsentRecord } from "@/api/cashless";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ShieldCheck, FileText, CheckCircle2, AlertCircle } from "lucide-react";

interface ConsentDialogProps {
  claimId: string;
  patientName: string;
  insuranceProvider: string;
  existingConsent?: PatientConsentRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConsentRecorded: () => void;
}

export const ConsentDialog: React.FC<ConsentDialogProps> = ({
  claimId,
  patientName,
  insuranceProvider,
  existingConsent,
  open,
  onOpenChange,
  onConsentRecorded,
}) => {
  const [consenterName, setConsenterName] = useState(existingConsent?.consenterName || patientName);
  const [consenterRelationship, setConsenterRelationship] = useState(
    existingConsent?.consenterRelationship || "Self"
  );
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultConsentText = `I, ${consenterName || "[Patient/Guardian]"}, hereby give my free and informed statutory consent to Apollo Specialty Hospital, ClaimBridge AI platform, and ${
    insuranceProvider || "the Third-Party Administrator"
  } to securely collect, transmit, and process the patient's medical records, diagnostic reports, and itemized billing for the explicit purpose of cashless hospitalization pre-authorization, concurrent review, and final settlement. I acknowledge that all transmissions comply with Indian digital healthcare guidelines.`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!acknowledged) {
      setError("Please confirm acknowledgment of the statutory data sharing terms.");
      return;
    }
    if (!consenterName.trim()) {
      setError("Consenter full name is required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await recordPatientConsent(claimId, {
        consenter_name: consenterName.trim(),
        consenter_relationship: consenterRelationship,
        purpose: "Cashless Hospitalization Medical Data Processing",
        consent_text: defaultConsentText,
      });

      if (res.error) {
        setError(res.error);
      } else {
        onConsentRecorded();
        onOpenChange(false);
      }
    } catch {
      setError("Failed to record patient consent. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Patient Medical Data Sharing Consent
              </DialogTitle>
              <DialogDescription className="text-xs">
                Statutory authorization for cashless pre-authorization and insurance review
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {existingConsent ? (
          <div className="space-y-4 py-2">
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                  Consent Verified & Recorded
                </div>
                <div className="text-xs text-muted-foreground">
                  Recorded by <strong>{existingConsent.consenterName}</strong> ({existingConsent.consenterRelationship}) on{" "}
                  {existingConsent.timestamp ? new Date(existingConsent.timestamp).toLocaleString() : "Recently"}
                </div>
                {existingConsent.ipAddress && (
                  <div className="text-[11px] text-muted-foreground">Audit IP: {existingConsent.ipAddress}</div>
                )}
              </div>
            </div>

            <div className="p-3 bg-muted/40 rounded-md border text-xs text-muted-foreground whitespace-pre-wrap font-mono">
              {existingConsent.consentText}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-xs text-destructive flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="consenterName" className="text-xs">
                  Consenter Full Name *
                </Label>
                <Input
                  id="consenterName"
                  value={consenterName}
                  onChange={(e) => setConsenterName(e.target.value)}
                  placeholder="Patient or Guardian name"
                  className="h-8 text-xs"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="consenterRelationship" className="text-xs">
                  Relationship to Patient *
                </Label>
                <select
                  id="consenterRelationship"
                  value={consenterRelationship}
                  onChange={(e) => setConsenterRelationship(e.target.value)}
                  className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                >
                  <option value="Self">Self (Patient)</option>
                  <option value="Spouse">Spouse</option>
                  <option value="Parent">Parent</option>
                  <option value="Child">Child</option>
                  <option value="Legal Guardian">Legal Guardian</option>
                  <option value="Other">Other Representative</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs flex items-center gap-1.5 text-muted-foreground">
                <FileText className="w-3.5 h-3.5" />
                Statutory Declaration Statement
              </Label>
              <div className="p-3 rounded-md border bg-muted/30 text-xs leading-relaxed text-muted-foreground">
                {defaultConsentText}
              </div>
            </div>

            <div className="flex items-start gap-2 pt-1">
              <Checkbox
                id="acknowledged"
                checked={acknowledged}
                onCheckedChange={(c) => setAcknowledged(Boolean(c))}
                className="mt-0.5"
              />
              <label htmlFor="acknowledged" className="text-xs text-foreground leading-snug cursor-pointer">
                I hereby declare that I am authorized to grant this statutory consent, and all medical records may be transmitted securely to the insurer/TPA for cashless pre-authorization.
              </label>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !acknowledged}>
                {submitting ? "Recording..." : "Record & Verify Consent"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
