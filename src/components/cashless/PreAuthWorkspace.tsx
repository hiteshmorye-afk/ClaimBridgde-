import React, { useEffect, useState } from "react";
import {
  fetchPreAuthDetails,
  savePreAuthDraft,
  submitPreAuthPackage,
  fetchPreAuthPackage,
  adjudicatePreAuth,
  respondPreAuthQuery,
  PreAuthDetailsResponse,
} from "@/api/cashless";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText,
  Send,
  CheckCircle2,
  AlertTriangle,
  Clock,
  XCircle,
  HelpCircle,
  Sparkles,
  Download,
  ShieldAlert,
} from "lucide-react";

interface PreAuthWorkspaceProps {
  claimId: string;
  userRole?: string;
  onRefresh?: () => void;
}

export const PreAuthWorkspace: React.FC<PreAuthWorkspaceProps> = ({
  claimId,
  userRole = "claimant",
  onRefresh,
}) => {
  const [data, setData] = useState<PreAuthDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states
  const [roomType, setRoomType] = useState("Single Private AC");
  const [proposedTreatment, setProposedTreatment] = useState("");
  const [treatingDoctor, setTreatingDoctor] = useState("");
  const [doctorRegNo, setDoctorRegNo] = useState("");

  // Cost Breakdown Items
  const [costItems, setCostItems] = useState<Array<{ name: string; amount: number }>>([
    { name: "Room Rent & Nursing Charges", amount: 15000 },
    { name: "Surgical & Professional Charges", amount: 35000 },
    { name: "Operation Theatre (OT) Charges", amount: 15000 },
    { name: "Diagnostic Investigations", amount: 8000 },
    { name: "Pharmacy & Consumables", amount: 12000 },
  ]);

  // Submission state
  const [submissionMode, setSubmissionMode] = useState("Online Portal");
  const [submissionReference, setSubmissionReference] = useState("");

  // Query response state
  const [queryResponse, setQueryResponse] = useState("");

  // TPA Adjudication states
  const [tpaDecision, setTpaDecision] = useState<"Approved" | "Partially Approved" | "Query Raised" | "Rejected">("Approved");
  const [tpaAmount, setTpaAmount] = useState<number>(0);
  const [tpaConditions, setTpaConditions] = useState("");
  const [tpaRemarks, setTpaRemarks] = useState("");

  // Package export preview
  const [exportFingerprint, setExportFingerprint] = useState<string | null>(null);

  const isCoordinator = userRole === "claimant" || userRole === "Coordinator";
  const isTpa = userRole === "claims_officer" || userRole === "Reviewer";

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPreAuthDetails(claimId);
      if (res.data) {
        setData(res.data);
        if (res.data.preauth) {
          const p = res.data.preauth;
          if (p.roomType) setRoomType(p.roomType);
          if (p.proposedTreatment) setProposedTreatment(p.proposedTreatment);
          if (p.treatingDoctor) setTreatingDoctor(p.treatingDoctor);
          if (p.doctorRegistrationNo) setDoctorRegNo(p.doctorRegistrationNo);
          if (p.costBreakdown && Object.keys(p.costBreakdown).length > 0) {
            setCostItems(
              Object.entries(p.costBreakdown).map(([name, amount]) => ({
                name,
                amount: Number(amount),
              }))
            );
          }
          if (p.submissionReference) setSubmissionReference(p.submissionReference);
          if (p.submissionMode) setSubmissionMode(p.submissionMode);
          if (p.initialApprovalAmount) setTpaAmount(p.initialApprovalAmount);
        }
      } else if (res.error) {
        setError(res.error);
      }
    } catch {
      setError("Failed to load pre-authorization details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [claimId]);

  const totalEstimatedCost = costItems.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);

  const handleUpdateCost = (index: number, field: "name" | "amount", value: any) => {
    const updated = [...costItems];
    if (field === "amount") {
      updated[index].amount = Math.max(0, Number(value) || 0);
    } else {
      updated[index].name = value;
    }
    setCostItems(updated);
  };

  const handleAddCostItem = () => {
    setCostItems([...costItems, { name: "Other Inpatient Charges", amount: 5000 }]);
  };

  const handleRemoveCostItem = (index: number) => {
    if (costItems.length <= 1) return;
    setCostItems(costItems.filter((_, i) => i !== index));
  };

  const handleSaveDraft = async () => {
    setError(null);
    setSuccessMsg(null);
    const breakdownMap: Record<string, number> = {};
    costItems.forEach((item) => {
      if (item.name.trim()) breakdownMap[item.name.trim()] = Number(item.amount);
    });

    try {
      const res = await savePreAuthDraft(claimId, {
        room_type: roomType,
        proposed_treatment: proposedTreatment,
        treating_doctor: treatingDoctor,
        doctor_registration_no: doctorRegNo,
        estimated_cost: totalEstimatedCost,
        cost_breakdown: breakdownMap,
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Pre-authorization draft saved successfully.");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Failed to save pre-authorization draft.");
    }
  };

  const handleSubmitPackage = async () => {
    if (!submissionReference.trim()) {
      setError("Please provide an external portal/TPA submission reference number.");
      return;
    }

    setError(null);
    setSuccessMsg(null);
    try {
      const res = await submitPreAuthPackage(claimId, {
        submission_mode: submissionMode,
        submission_reference: submissionReference.trim(),
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Pre-authorization package submitted to insurer/TPA.");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Submission failed. Ensure at least one supporting document is uploaded.");
    }
  };

  const handleExportPackage = async () => {
    try {
      const res = await fetchPreAuthPackage(claimId);
      if (res.data) {
        setExportFingerprint(res.data.packageFingerprint);
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res.data, null, 2));
        const downloadAnchor = document.createElement("a");
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `preauth_${data?.claimNumber || claimId}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      }
    } catch {
      setError("Failed to export pre-authorization package.");
    }
  };

  const handleRespondQuery = async () => {
    if (!queryResponse.trim()) {
      setError("Please provide a response to the TPA query.");
      return;
    }
    setError(null);
    try {
      const res = await respondPreAuthQuery(claimId, {
        hospital_query_response: queryResponse.trim(),
      });
      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg("Query response sent to TPA reviewer.");
        setQueryResponse("");
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("Failed to submit query response.");
    }
  };

  const handleTpaAdjudicate = async () => {
    setError(null);
    try {
      const res = await adjudicatePreAuth(claimId, {
        decision: tpaDecision,
        initial_approval_amount: tpaDecision.includes("Approved") ? tpaAmount : undefined,
        approval_conditions: tpaConditions,
        query_remarks: tpaRemarks,
      });

      if (res.error) {
        setError(res.error);
      } else {
        setSuccessMsg(`Pre-authorization adjudication complete: ${tpaDecision}.`);
        loadData();
        onRefresh?.();
      }
    } catch {
      setError("TPA adjudication failed. Ensure organization scope matches insurer.");
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">Loading Pre-Authorization Workspace...</div>;
  }

  const preauth = data?.preauth;
  const statusStr = preauth?.status || "Draft";

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "Approved":
        return <Badge className="bg-emerald-600 text-white gap-1"><CheckCircle2 className="w-3 h-3" /> Approved</Badge>;
      case "Partially Approved":
        return <Badge className="bg-amber-600 text-white gap-1"><AlertTriangle className="w-3 h-3" /> Partially Approved</Badge>;
      case "Submitted":
      case "Under Review":
        return <Badge className="bg-blue-600 text-white gap-1"><Clock className="w-3 h-3" /> {st}</Badge>;
      case "Query Raised":
        return <Badge className="bg-purple-600 text-white gap-1"><HelpCircle className="w-3 h-3" /> Query Raised</Badge>;
      case "Rejected":
        return <Badge className="bg-destructive text-white gap-1"><XCircle className="w-3 h-3" /> Rejected</Badge>;
      default:
        return <Badge variant="outline" className="gap-1"><FileText className="w-3 h-3" /> Draft</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-xs text-destructive flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-xs text-emerald-800 dark:text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {successMsg}
        </div>
      )}

      {/* Header Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border bg-card/60 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold text-foreground">Cashless Pre-Authorization Workspace</h2>
            {getStatusBadge(statusStr)}
          </div>
          <p className="text-xs text-muted-foreground">
            Insurer: <strong className="text-foreground">{data?.insuranceProvider}</strong> &bull; Policy:{" "}
            <strong className="text-foreground">{data?.policyNumber}</strong> &bull; Patient:{" "}
            <strong className="text-foreground">{data?.patientName}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportPackage} className="gap-1.5 text-xs h-8">
            <Download className="w-3.5 h-3.5" />
            Export Package
          </Button>
          {exportFingerprint && (
            <span className="text-[10px] font-mono text-muted-foreground hidden sm:inline">
              SHA: {exportFingerprint.slice(0, 8)}...
            </span>
          )}
        </div>
      </div>

      {/* Query Banner if Query Raised */}
      {statusStr === "Query Raised" && (
        <Card className="border-purple-300 bg-purple-500/5">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs font-semibold text-purple-900 dark:text-purple-300 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-purple-600" />
              TPA Adjudicator Query Raised
            </CardTitle>
            <CardDescription className="text-xs text-purple-800 dark:text-purple-400">
              The insurer requires additional clarification before pre-authorization can be granted.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div className="p-3 rounded-md bg-purple-100/50 dark:bg-purple-950/40 text-xs text-purple-950 dark:text-purple-200">
              {preauth?.tpaQueryRemarks}
            </div>

            {isCoordinator && (
              <div className="space-y-2 pt-1">
                <Label className="text-xs">Hospital Clinical / Administrative Response</Label>
                <Textarea
                  value={queryResponse}
                  onChange={(e) => setQueryResponse(e.target.value)}
                  placeholder="Provide supporting clinical clarification, diagnostic findings, or physician remarks..."
                  rows={3}
                  className="text-xs"
                />
                <Button size="sm" onClick={handleRespondQuery} className="gap-1.5 text-xs">
                  <Send className="w-3.5 h-3.5" />
                  Submit Query Response
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Initial Approval Details if Granted */}
      {preauth?.initialApprovalAmount && preauth.initialApprovalAmount > 0 && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Initial Cashless Authorization Approved
            </span>
            <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400">
              INR {preauth.initialApprovalAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="text-xs text-emerald-800 dark:text-emerald-400 flex flex-wrap gap-x-4 gap-y-1">
            <span>Reference: <strong>{preauth.approvalReference}</strong></span>
            {preauth.approvedAt && <span>Approved At: {new Date(preauth.approvedAt).toLocaleString()}</span>}
          </div>
          {preauth.approvalConditions && (
            <p className="text-xs text-muted-foreground pt-1 italic">
              Conditions: {preauth.approvalConditions}
            </p>
          )}
        </div>
      )}

      {/* Main Grid: Details & Cost Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Clinical & Cost Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="py-3 px-4 border-b">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                Hospitalization & Clinical Scope
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Room / Bed Category</Label>
                  <select
                    value={roomType}
                    disabled={!isCoordinator || statusStr === "Approved"}
                    onChange={(e) => setRoomType(e.target.value)}
                    className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                  >
                    <option value="General Ward">General Ward</option>
                    <option value="Twin Sharing">Twin Sharing</option>
                    <option value="Single Private AC">Single Private AC</option>
                    <option value="Deluxe Suite">Deluxe Suite</option>
                    <option value="ICU / ICCU">ICU / Intensive Care</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Treating Doctor / Consultant</Label>
                  <Input
                    value={treatingDoctor}
                    disabled={!isCoordinator || statusStr === "Approved"}
                    onChange={(e) => setTreatingDoctor(e.target.value)}
                    placeholder="e.g. Dr. Ramesh Verma, MS"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Doctor Medical Council Reg No.</Label>
                  <Input
                    value={doctorRegNo}
                    disabled={!isCoordinator || statusStr === "Approved"}
                    onChange={(e) => setDoctorRegNo(e.target.value)}
                    placeholder="e.g. MCI-2012-44321"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Proposed Treatment & Line of Management</Label>
                  <Input
                    value={proposedTreatment}
                    disabled={!isCoordinator || statusStr === "Approved"}
                    onChange={(e) => setProposedTreatment(e.target.value)}
                    placeholder="e.g. Laparoscopic Appendectomy under GA"
                    className="h-8 text-xs"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Itemized Cost Breakdown Ledger */}
          <Card>
            <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  Estimated Inpatient Cost Breakdown
                </CardTitle>
                <CardDescription className="text-xs">
                  Enter estimated heads for room, surgery, investigations, and medicines
                </CardDescription>
              </div>
              {isCoordinator && statusStr !== "Approved" && (
                <Button variant="outline" size="sm" onClick={handleAddCostItem} className="h-7 text-xs">
                  + Add Head
                </Button>
              )}
            </CardHeader>
            <CardContent className="p-4 space-y-3">
              <div className="space-y-2">
                {costItems.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Input
                      value={item.name}
                      disabled={!isCoordinator || statusStr === "Approved"}
                      onChange={(e) => handleUpdateCost(idx, "name", e.target.value)}
                      className="h-8 text-xs flex-1"
                      placeholder="Charge head"
                    />
                    <div className="relative w-36">
                      <span className="absolute left-2.5 top-1.5 text-xs text-muted-foreground">₹</span>
                      <Input
                        type="number"
                        value={item.amount}
                        disabled={!isCoordinator || statusStr === "Approved"}
                        onChange={(e) => handleUpdateCost(idx, "amount", e.target.value)}
                        className="h-8 text-xs pl-6 text-right"
                      />
                    </div>
                    {isCoordinator && statusStr !== "Approved" && costItems.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveCostItem(idx)}
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                      >
                        ✕
                      </Button>
                    )}
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">Total Estimated Pre-Auth Claim:</span>
                <span className="text-base font-bold text-primary">
                  INR {totalEstimatedCost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>

              {isCoordinator && statusStr !== "Approved" && (
                <div className="pt-2 flex justify-end gap-2">
                  <Button size="sm" onClick={handleSaveDraft} className="text-xs">
                    Save Pre-Auth Draft
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Checklist & Submission / Adjudication Desk */}
        <div className="space-y-6">
          {/* Document Checklist */}
          <Card>
            <CardHeader className="py-3 px-4 border-b">
              <CardTitle className="text-xs font-semibold">Mandatory Pre-Auth Documents</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2.5">
              {data?.checklist.map((item) => (
                <div
                  key={item.type}
                  className={`p-2.5 rounded-md border text-xs flex items-center justify-between ${
                    item.uploaded
                      ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-800 dark:text-emerald-400"
                      : "bg-amber-500/5 border-amber-500/20 text-amber-800 dark:text-amber-400"
                  }`}
                >
                  <span className="font-medium">{item.label}</span>
                  {item.uploaded ? (
                    <span className="text-[11px] flex items-center gap-1 font-semibold text-emerald-600">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Uploaded
                    </span>
                  ) : (
                    <span className="text-[11px] flex items-center gap-1 font-semibold text-amber-600">
                      <Clock className="w-3.5 h-3.5" /> Required
                    </span>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Submission Panel (Coordinator) */}
          {isCoordinator && statusStr !== "Approved" && (
            <Card>
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Send className="w-4 h-4 text-primary" />
                  Insurer / TPA Dispatch Tracking
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Dispatch Mode</Label>
                  <select
                    value={submissionMode}
                    onChange={(e) => setSubmissionMode(e.target.value)}
                    className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background"
                  >
                    <option value="Online Portal">Insurer / TPA Online Portal</option>
                    <option value="Official Email">Official TPA Cashless Desk Email</option>
                    <option value="Direct API Bridge">Direct Hospital-TPA EDI Bridge</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">TPA Portal Submission Ref # *</Label>
                  <Input
                    value={submissionReference}
                    onChange={(e) => setSubmissionReference(e.target.value)}
                    placeholder="e.g. STAR-PRE-2026-9901"
                    className="h-8 text-xs"
                  />
                </div>

                <Button
                  size="sm"
                  onClick={handleSubmitPackage}
                  disabled={!submissionReference.trim()}
                  className="w-full text-xs gap-1.5 mt-2"
                >
                  <Send className="w-3.5 h-3.5" />
                  Submit Pre-Authorization
                </Button>
              </CardContent>
            </Card>
          )}

          {/* TPA Adjudication Panel (TPA Reviewer only) */}
          {isTpa && (
            <Card className="border-primary/40 bg-primary/5">
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-xs font-semibold text-primary">TPA Initial Adjudication Desk</CardTitle>
                <CardDescription className="text-xs">
                  Review clinical notes and authorize initial cashless hospitalization cap
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Adjudication Decision</Label>
                  <select
                    value={tpaDecision}
                    onChange={(e: any) => setTpaDecision(e.target.value)}
                    className="w-full h-8 px-2 text-xs rounded-md border border-input bg-background font-medium"
                  >
                    <option value="Approved">Approve Pre-Authorization</option>
                    <option value="Partially Approved">Partially Approve (Cap Amount)</option>
                    <option value="Query Raised">Raise Query for Hospital</option>
                    <option value="Rejected">Reject Pre-Authorization</option>
                  </select>
                </div>

                {tpaDecision.includes("Approved") && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Approved Initial Amount (₹) *</Label>
                    <Input
                      type="number"
                      value={tpaAmount || totalEstimatedCost}
                      onChange={(e) => setTpaAmount(Number(e.target.value))}
                      className="h-8 text-xs"
                    />
                  </div>
                )}

                {tpaDecision.includes("Approved") && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Approval Schedule / Conditions</Label>
                    <Input
                      value={tpaConditions}
                      onChange={(e) => setTpaConditions(e.target.value)}
                      placeholder="e.g. Excludes non-medical consumables per IRDAI list"
                      className="h-8 text-xs"
                    />
                  </div>
                )}

                {(tpaDecision === "Query Raised" || tpaDecision === "Rejected") && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Remarks / Query Details *</Label>
                    <Textarea
                      value={tpaRemarks}
                      onChange={(e) => setTpaRemarks(e.target.value)}
                      placeholder="Explain reason for query or denial..."
                      rows={3}
                      className="text-xs"
                    />
                  </div>
                )}

                <Button size="sm" onClick={handleTpaAdjudicate} className="w-full text-xs mt-2">
                  Execute Decision ({tpaDecision})
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
