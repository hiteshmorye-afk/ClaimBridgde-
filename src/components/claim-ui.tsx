import { Link } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";

import type { ClaimStatus } from "@/lib/claims";

export function ClaimBridgeMark({ size = "md" }: { size?: "sm" | "md" }) {
  return (
    <span
      className={`flex items-center justify-center rounded-lg bg-primary text-primary-foreground ${
        size === "sm" ? "size-9" : "size-11"
      }`}
    >
      <ShieldCheck className={size === "sm" ? "size-4" : "size-5"} />
    </span>
  );
}

export function BrandLockup({ to }: { to?: string }) {
  const content = (
    <span className="flex items-center gap-3">
      <ClaimBridgeMark size="sm" />
      <span>
        <span className="block font-display text-lg font-semibold leading-tight">ClaimBridge</span>
        <span className="block text-xs text-muted-foreground">
          Intelligent Insurance Claim Verification
        </span>
      </span>
    </span>
  );
  return to ? <Link to={to}>{content}</Link> : content;
}

const statusStyles: Record<ClaimStatus, string> = {
  "Ready for Submission": "bg-success/12 text-success border-success/30",
  "Under Analysis": "bg-primary/10 text-primary border-primary/25",
  "Needs Review": "bg-warning/20 text-warning-foreground border-warning/40",
  Approved: "bg-success/12 text-success border-success/30",
  Rejected: "bg-destructive/10 text-destructive border-destructive/30",
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyles[status]}`}
    >
      {status}
    </span>
  );
}

export function ReadinessScore({ value, className = "" }: { value: number; className?: string }) {
  const tone = value >= 80 ? "bg-success" : value >= 60 ? "bg-primary" : "bg-warning";
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-sm font-medium tabular-nums">{value}%</span>
    </div>
  );
}