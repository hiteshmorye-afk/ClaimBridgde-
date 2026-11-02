import React, { useEffect, useState } from "react";
import { fetchTreatmentRecords, addTreatmentRecord, TreatmentRecordItem } from "@/api/cashless";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Stethoscope, Calendar, Activity, AlertCircle, PlusCircle, CheckCircle2 } from "lucide-react";

interface TreatmentTrackerProps {
  claimId: string;
  isCoordinator?: boolean;
}

export const TreatmentTracker: React.FC<TreatmentTrackerProps> = ({
  claimId,
  isCoordinator = true,
}) => {
  const [records, setRecords] = useState<TreatmentRecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Record Form State
  const [recordDate, setRecordDate] = useState(new Date().toISOString().split("T")[0]);
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [updatedDiagnosis, setUpdatedDiagnosis] = useState("");
  const [cumulativeExpenses, setCumulativeExpenses] = useState<number | "">("");
  const [procedureName, setProcedureName] = useState("");
  const [doctorName, setDoctorName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadRecords = async () => {
    setLoading(true);
    try {
      const res = await fetchTreatmentRecords(claimId);
      if (res.data) {
        setRecords(res.data);
      }
    } catch {
      setError("Failed to load treatment timeline.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [claimId]);

  const handleAddRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clinicalNotes.trim()) {
      setError("Clinical notes are required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMsg(null);

    const procs = procedureName.trim()
      ? [{ name: procedureName.trim(), surgeon: doctorName.trim() || undefined }]
      : [];

    try {
      const res = await addTreatmentRecord(claimId, {
        record_date: recordDate,
        clinical_notes: clinicalNotes.trim(),
        procedures_performed: procs,
        updated_diagnosis: updatedDiagnosis.trim() || undefined,
        cumulative_expenses: cumulativeExpenses !== "" ? Number(cumulativeExpenses) : undefined,
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Inpatient treatment entry recorded successfully.");
        setClinicalNotes("");
        setProcedureName("");
        setDoctorName("");
        loadRecords();
      }
    } catch {
      setError("Failed to record treatment entry.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Alert Notices */}
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-xs text-destructive flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-xs text-emerald-800 dark:text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {successMsg}
        </div>
      )}

      {/* Hospital Staff Entry Form */}
      {isCoordinator && (
        <Card>
          <CardHeader className="py-3 px-4 border-b">
            <CardTitle className="text-xs font-semibold flex items-center gap-2">
              <PlusCircle className="w-4 h-4 text-primary" />
              Record Inpatient Clinical Update & Interim Expense
            </CardTitle>
            <CardDescription className="text-xs">
              Document daily rounds, surgical notes, diagnostic findings, and running cumulative expenses
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            <form onSubmit={handleAddRecord} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Record Date *</Label>
                  <Input
                    type="date"
                    value={recordDate}
                    onChange={(e) => setRecordDate(e.target.value)}
                    className="h-8 text-xs"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Updated Diagnosis (if any)</Label>
                  <Input
                    value={updatedDiagnosis}
                    onChange={(e) => setUpdatedDiagnosis(e.target.value)}
                    placeholder="e.g. Perforated Appendix with Peritonitis"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Cumulative Running Expenses (₹)</Label>
                  <Input
                    type="number"
                    value={cumulativeExpenses}
                    onChange={(e) => setCumulativeExpenses(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="e.g. 65000"
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs">Daily Clinical Notes / Case Course *</Label>
                <Textarea
                  value={clinicalNotes}
                  onChange={(e) => setClinicalNotes(e.target.value)}
                  placeholder="Record patient vitals, clinical response, post-op progress, antibiotic regimen..."
                  rows={3}
                  className="text-xs"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Procedure Conducted</Label>
                  <Input
                    value={procedureName}
                    onChange={(e) => setProcedureName(e.target.value)}
                    placeholder="e.g. Emergency Diagnostic Laparoscopy"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Operating Surgeon / Attending Physician</Label>
                  <Input
                    value={doctorName}
                    onChange={(e) => setDoctorName(e.target.value)}
                    placeholder="e.g. Dr. Ramesh Verma"
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button type="submit" size="sm" disabled={submitting} className="text-xs gap-1.5">
                  <Activity className="w-3.5 h-3.5" />
                  {submitting ? "Saving..." : "Add Inpatient Update"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Chronological Treatment Timeline */}
      <Card>
        <CardHeader className="py-3 px-4 border-b">
          <CardTitle className="text-xs font-semibold flex items-center gap-2">
            <Stethoscope className="w-4 h-4 text-primary" />
            Inpatient Clinical Course & Ledger Timeline
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          {loading ? (
            <div className="py-6 text-center text-xs text-muted-foreground animate-pulse">
              Loading clinical course...
            </div>
          ) : records.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              No treatment records entered yet. Use the form above to document inpatient progress.
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
              {records.map((r) => (
                <div key={r.id} className="relative">
                  <div className="absolute -left-[19px] top-1 w-2.5 h-2.5 rounded-full bg-primary ring-4 ring-background" />

                  <div className="p-3.5 rounded-lg border bg-card/60 shadow-xs space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-primary" />
                        <span className="text-xs font-semibold text-foreground">{r.recordDate}</span>
                        {r.updatedDiagnosis && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                            {r.updatedDiagnosis}
                          </span>
                        )}
                      </div>

                      {r.cumulativeExpenses !== null && r.cumulativeExpenses !== undefined && (
                        <span className="text-xs font-bold text-primary">
                          Running Total: INR {Number(r.cumulativeExpenses).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
                      {r.clinicalNotes}
                    </p>

                    {r.proceduresPerformed && r.proceduresPerformed.length > 0 && (
                      <div className="pt-1 flex flex-wrap gap-1.5">
                        {r.proceduresPerformed.map((p, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary font-medium flex items-center gap-1"
                          >
                            <Activity className="w-3 h-3" />
                            {p.name} {p.surgeon && `(by ${p.surgeon})`}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
