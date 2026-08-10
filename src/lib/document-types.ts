import type { Database } from "@/integrations/supabase/types";

export type DocumentRow = Database["public"]["Tables"]["documents"]["Row"];

export type LineItem = {
  description: string;
  quantity: number | null;
  amount: number | null;
};

export type LabResult = {
  test: string;
  value: string;
  unit: string | null;
  reference_range: string | null;
  flag: "low" | "normal" | "high" | "unknown";
};

export function formatAmount(amount: number | string, currency: string | null): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(value)) return "—";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency ?? ""} ${value.toLocaleString()}`.trim();
  }
}

export function formatDate(value: string | null): string {
  if (!value) return "No date";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}