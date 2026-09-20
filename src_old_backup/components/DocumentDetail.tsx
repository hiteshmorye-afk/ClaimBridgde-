import { FileText, Receipt } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DocumentRow, LabResult, LineItem } from "@/lib/document-types";
import { formatAmount, formatDate } from "@/lib/document-types";

export function DocumentDetail({ doc }: { doc: DocumentRow }) {
  const lineItems = (doc.line_items ?? []) as LineItem[];
  const labResults = (doc.lab_results ?? []) as LabResult[];

  return (
    <div className="space-y-6">
      <Card className="shadow-panel">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-xl">{doc.file_name}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {doc.provider_name ?? "Unknown provider"} · {formatDate(doc.document_date)}
            </p>
          </div>
          <Badge variant="secondary" className="capitalize">
            {doc.doc_type === "bill" ? (
              <Receipt className="mr-1 size-3.5" />
            ) : (
              <FileText className="mr-1 size-3.5" />
            )}
            {doc.doc_type}
          </Badge>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Field label="Patient" value={doc.patient_name} />
          <Field label="Provider" value={doc.provider_name} />
          <Field
            label="Total"
            value={doc.total_amount != null ? formatAmount(doc.total_amount, doc.currency) : null}
          />
          {doc.summary ? (
            <p className="sm:col-span-3 rounded-lg bg-muted p-4 text-sm leading-relaxed">
              {doc.summary}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {lineItems.length > 0 ? (
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="text-base">Charges ({lineItems.length})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-6 py-3 font-medium">Description</th>
                    <th className="px-6 py-3 font-medium">Qty</th>
                    <th className="px-6 py-3 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((item, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-6 py-3">{item.description}</td>
                      <td className="px-6 py-3 text-muted-foreground">{item.quantity ?? "—"}</td>
                      <td className="px-6 py-3 text-right font-medium tabular-nums">
                        {item.amount != null ? formatAmount(item.amount, doc.currency) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {labResults.length > 0 ? (
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="text-base">Results ({labResults.length})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-6 py-3 font-medium">Test</th>
                    <th className="px-6 py-3 font-medium">Value</th>
                    <th className="px-6 py-3 font-medium">Reference</th>
                    <th className="px-6 py-3 font-medium">Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {labResults.map((row, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-6 py-3">{row.test}</td>
                      <td className="px-6 py-3 font-medium tabular-nums">
                        {row.value} {row.unit ?? ""}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground">
                        {row.reference_range ?? "—"}
                      </td>
                      <td className="px-6 py-3">
                        <FlagBadge flag={row.flag} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {doc.raw_text ? (
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="text-base">Transcribed text</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed text-muted-foreground">
              {doc.raw_text}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value ?? "—"}</p>
    </div>
  );
}

function FlagBadge({ flag }: { flag: LabResult["flag"] }) {
  if (flag === "high" || flag === "low") {
    return (
      <Badge variant="destructive" className="capitalize">
        {flag}
      </Badge>
    );
  }
  if (flag === "normal") {
    return (
      <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">
        Normal
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">—</span>;
}