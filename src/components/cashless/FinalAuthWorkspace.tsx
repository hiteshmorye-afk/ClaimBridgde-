import React, { useEffect, useState } from "react";
import {
  fetchFinalAuthDetails,
  saveFinalAuthDraft,
  submitFinalAuth,
  adjudicateFinalAuth,
  FinalAuthDetailsResponse,
} from "@/api/cashless";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  FileCheck2,
  DollarSign,
  Send,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Scale,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

interface FinalAuthWorkspaceProps {
  claimId: string;
  userRole?: string;
  onRefresh?: () => void;
}

export const FinalAuthWorkspace: React.FC<FinalAuthWorkspaceProps> = ({
  claimId,
  userRole = "claimant",
  onRefresh,
}) => {
  const [data, setData] = useState<FinalAuthDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states (Coordinator)
  const [finalBilledAmount, setFinalBilledAmount] = useState<number>(0);
  const [submissionReference, setSubmissionReference] = useState("");

  // Deductions state
  const [deductions, setDeductions] = useState<Array<{ name: string; amount: number }>>([
    { name: "Non-Medical Consumables", amount: 3500 },
    { name: "Room Rent Excess Differential", amount: 4500 },
  ]);

  // TPA Settlement States
  const [tpaDecision, setTpaDecision] = useState<"Approved" | "Partially Approved" | "Rejected">("Approved");
  const [tpaApprovedAmount, setTpaApprovedAmount] = useState<number>(0);
  const [tpaRef, setTpaRef] = useState("");
  const [tpaRemarks, setTpaRemarks] = useState("");

  const isCoordinator = userRole === "claimant" || userRole === "Coordinator";
  const isTpa = userRole === "claims_officer" || userRole === "Reviewer";

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchFinalAuthDetails(claimId);
      if (res.data) {
        setData(res.data);
        if (res.data.finalAuth) {
          const fa = res.data.finalAuth;
          setFinalBilledAmount(fa.finalBilledAmount);
          if (fa.submissionReference) setSubmissionReference(fa.submissionReference);
          if (fa.finalApprovedAmount) setTpaApprovedAmount(fa.finalApprovedAmount);
          if (fa.deductionBreakdown && Object.keys(fa.deductionBreakdown).length > 0) {
            setDeductions(
              Object.entries(fa.deductionBreakdown).map(([name, amount]) => ({
                name,
                amount: Number(amount),
              }))
            );
          }
        } else if (res.data.financialComparison) {
          setFinalBilledAmount(res.data.financialComparison.finalBilledAmount);
          setTpaApprovedAmount(res.data.financialComparison.initialApprovedAmount);
        }
      } else if (res.error) {
        setError(res.error);
      }
    } catch {
      setError("Failed to load final authorization workspace.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [claimId]);

  const totalDeductions = deductions.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);
  const patientResponsibility = Math.max(0, finalBilledAmount - tpaApprovedAmount);

  const handleSaveDraft = async () => {
    setError(null);
    setSuccessMsg(null);
    const map: Record<string, number> = {};
    deductions.forEach((d) => {
      if (d.name.trim()) map[d.name.trim()] = Number(d.amount);
    });

    try {
      const res = await saveFinalAuthDraft(claimId, {
        final_billed_amount: finalBilledAmount,
        deduction_breakdown: map,
        patient_responsibility_amount: totalDeductions,
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Final bill details saved as draft.");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Failed to save final authorization draft.");
    }
  };

  const handleSubmitFinalAuth = async () => {
    if (!submissionReference.trim()) {
      setError("Please provide a submission reference number.");
      return;
    }
    setError(null);
    try {
      const res = await submitFinalAuth(claimId, {
        submission_reference: submissionReference.trim(),
      });
      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Final authorization package submitted for TPA settlement.");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Failed to submit final settlement package.");
    }
  };

  const handleTpaAdjudicate = async () => {
    if (!tpaRef.trim()) {
      setError("Settlement authorization reference number is required.");
      return;
    }

    setError(null);
    try {
      const map: Record<string, number> = {};
      deductions.forEach((d) => {
        if (d.name.trim()) map[d.name.trim()] = Number(d.amount);
      });

      const res = await adjudicateFinalAuth(claimId, {
        decision: tpaDecision,
        final_approved_amount: tpaApprovedAmount,
        non_payable_deductions: totalDeductions,
        deduction_breakdown: map,
        patient_responsibility_amount: patientResponsibility,
        final_approval_reference: tpaRef.trim(),
        tpa_remarks: tpaRemarks.trim() || undefined,
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Final cashless settlement letter executed successfully.");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Failed to execute final settlement adjudication.");
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">Loading Final Authorization Workspace...</div>;
  }

  const comparison = data?.financialComparison;
  const finalAuth = data?.finalAuth;
  const isSettled = finalAuth?.status === "Settled" || finalAuth?.status === "Approved";

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

      {/* 3-Way Financial Comparison Header Card */}
      <Card className="border-primary/20 bg-gradient-to-br from-card to-muted/20">
        <CardHeader className="py-3 px-4 border-b">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-xs font-semibold flex items-center gap-2 text-foreground">
                <Scale className="w-4 h-4 text-primary" />
                3-Way Financial Reconciliation Card
              </CardTitle>
              <CardDescription className="text-xs">
                Cross-comparison of initial pre-authorization estimate, approved cashless cap, and final hospital invoice
              </CardDescription>
            </div>
            {finalAuth?.status && (
              <Badge variant={isSettled ? "default" : "outline"} className={isSettled ? "bg-emerald-600" : ""}>
                {finalAuth.status}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg border bg-background/50 space-y-1">
              <span className="text-[11px] text-muted-foreground uppercase font-semibold">1. Estimated Pre-Auth Cost</span>
              <div className="text-lg font-bold text-foreground">
                INR {comparison?.estimatedCost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <span className="text-[10px] text-muted-foreground">Original intake estimate</span>
            </div>

            <div className="p-3 rounded-lg border bg-background/50 space-y-1">
              <span className="text-[11px] text-muted-foreground uppercase font-semibold">2. Initial Approved Amount</span>
              <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                INR {comparison?.initialApprovedAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <span className="text-[10px] text-muted-foreground">Authorized pre-admission cap</span>
            </div>

            <div className={`p-3 rounded-lg border space-y-1 ${
              comparison?.exceedsInitialAuth
                ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-300"
                : "bg-background/50"
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground uppercase font-semibold">3. Final Billed Amount</span>
                {comparison?.exceedsInitialAuth && (
                  <Badge variant="outline" className="text-[10px] bg-amber-500/20 text-amber-700 border-amber-400">
                    +₹{comparison.varianceFromInitial.toLocaleString()} Excess
                  </Badge>
                )}
              </div>
              <div className="text-lg font-bold">
                INR {finalBilledAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <span className="text-[10px] text-muted-foreground">
                {comparison?.exceedsInitialAuth ? "Exceeds authorized cap by differential" : "Within authorized cap"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settlement Breakdown Notice if Settled */}
      {isSettled && (
        <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-300 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Final Cashless Settlement Authorization Letter
            </span>
            <span className="text-xs font-mono text-emerald-800 dark:text-emerald-400">
              Ref: {finalAuth?.finalApprovalReference}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <div className="p-2.5 rounded-md bg-background/80 border">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">TPA Approved Settlement</span>
              <div className="text-sm font-bold text-emerald-600">
                INR {Number(finalAuth?.finalApprovedAmount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-2.5 rounded-md bg-background/80 border">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">Non-Payable Deductions</span>
              <div className="text-sm font-bold text-muted-foreground">
                INR {Number(finalAuth?.nonPayableDeductions || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-2.5 rounded-md bg-background/80 border">
              <span className="text-[10px] text-muted-foreground uppercase font-semibold">Patient Out-of-Pocket Due</span>
              <div className="text-sm font-bold text-amber-600">
                INR {Number(finalAuth?.patientResponsibilityAmount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {finalAuth?.tpaRemarks && (
            <p className="text-xs text-muted-foreground italic pt-1">
              TPA Adjudication Remarks: {finalAuth.tpaRemarks}
            </p>
          )}
        </div>
      )}

      {/* Main Form: Billing Reconciliation & TPA Settlement */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Final Invoice Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="py-3 px-4 border-b">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <Receipt className="w-4 h-4 text-primary" />
                Final Itemized Hospital Bill Total
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Final Billed Amount (₹) *</Label>
                <Input
                  type="number"
                  value={finalBilledAmount}
                  disabled={!isCoordinator || isSettled}
                  onChange={(e) => setFinalBilledAmount(Math.max(0, Number(e.target.value) || 0))}
                  className="h-9 text-sm font-semibold"
                />
              </div>

              {/* Deductions Breakdown Table */}
              <div className="space-y-2 pt-2">
                <Label className="text-xs font-semibold">Identified Non-Payable Heads & Consumables</Label>
                <div className="space-y-2">
                  {deductions.map((d, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Input
                        value={d.name}
                        disabled={!isCoordinator || isSettled}
                        onChange={(e) => {
                          const updated = [...deductions];
                          updated[idx].name = e.target.value;
                          setDeductions(updated);
                        }}
                        className="h-8 text-xs flex-1"
                      />
                      <div className="relative w-32">
                        <span className="absolute left-2.5 top-1.5 text-xs text-muted-foreground">₹</span>
                        <Input
                          type="number"
                          value={d.amount}
                          disabled={!isCoordinator || isSettled}
                          onChange={(e) => {
                            const updated = [...deductions];
                            updated[idx].amount = Math.max(0, Number(e.target.value) || 0);
                            setDeductions(updated);
                          }}
                          className="h-8 text-xs pl-6 text-right"
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Total Disallowed / Non-Payable Deductions:</span>
                  <span className="font-bold text-foreground">
                    INR {totalDeductions.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {isCoordinator && !isSettled && (
                <div className="pt-2 flex justify-end">
                  <Button size="sm" onClick={handleSaveDraft} className="text-xs">
                    Save Final Bill Draft
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Submission / TPA Settlement Adjudication */}
        <div className="space-y-6">
          {/* Submission Panel (Coordinator) */}
          {isCoordinator && !isSettled && (
            <Card>
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Send className="w-4 h-4 text-primary" />
                  Submit for TPA Settlement
                </CardTitle>
                <CardDescription className="text-xs">
                  Transmit final invoice and discharge summary to insurer
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Final Settlement Reference Ref # *</Label>
                  <Input
                    value={submissionReference}
                    onChange={(e) => setSubmissionReference(e.target.value)}
                    placeholder="e.g. STAR-FINAL-2026-001"
                    className="h-8 text-xs"
                  />
                </div>

                <Button
                  size="sm"
                  onClick={handleSubmitFinalAuth}
                  disabled={!submissionReference.trim()}
                  className="w-full text-xs gap-1.5 mt-2"
                >
                  <Send className="w-3.5 h-3.5" />
                  Submit Final Authorization
                </Button>
              </CardContent>
            </Card>
          )}

          {/* TPA Settlement Panel (Reviewer) */}
          {isTpa && !isSettled && (
            <Card className="border-primary/40 bg-primary/5">
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-xs font-semibold text-primary">TPA Settlement Adjudication</CardTitle>
                <CardDescription className="text-xs">
                  Issue cashless discharge clearance and itemize patient responsibility
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Decision</Label>
                  <select
                    value={tpaDecision}
                    onChange={(e: any) => setTpaDecision(e.target.value)}
                    className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background font-medium"
                  >
                    <option value="Approved">Approve Settlement</option>
                    <option value="Partially Approved">Partially Approve (With Deductions)</option>
                    <option value="Rejected">Reject Settlement</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Final TPA Approved Amount (₹) *</Label>
                  <Input
                    type="number"
                    value={tpaApprovedAmount}
                    onChange={(e) => setTpaApprovedAmount(Math.max(0, Number(e.target.value) || 0))}
                    className="h-8 text-xs font-bold text-emerald-600"
                  />
                </div>

                <div className="p-2.5 rounded-md bg-muted/60 border text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Patient Out-of-Pocket Due:</span>
                    <strong className="text-amber-600">
                      ₹{Math.max(0, finalBilledAmount - tpaApprovedAmount).toLocaleString()}
                    </strong>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Final Settlement Approval Ref # *</Label>
                  <Input
                    value={tpaRef}
                    onChange={(e) => setTpaRef(e.target.value)}
                    placeholder="e.g. STAR-SETTLE-88990"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Adjudication Remarks / Clause Reference</Label>
                  <Textarea
                    value={tpaRemarks}
                    onChange={(e) => setTpaRemarks(e.target.value)}
                    placeholder="e.g. Approved per network schedule..."
                    rows={2}
                    className="text-xs"
                  />
                </div>

                <Button size="sm" onClick={handleTpaAdjudicate} className="w-full text-xs mt-2">
                  Authorize Cashless Settlement
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
