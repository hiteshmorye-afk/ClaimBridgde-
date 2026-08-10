import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  LogOut,
  Receipt,
  Trash2,
  UploadCloud,
} from "lucide-react";

import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { processDocument } from "@/lib/documents.functions";
import { DocumentDetail } from "@/components/DocumentDetail";
import { formatAmount, formatDate, type DocumentRow } from "@/lib/document-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "MedExtract Dashboard — Hospital Bill & Report Data" },
      {
        name: "description",
        content:
          "Upload hospital bills and lab reports, extract patient, provider, charges and results automatically, and review them in one dashboard.",
      },
      { property: "og:title", content: "MedExtract Dashboard" },
      {
        property: "og:description",
        content: "Upload hospital bills and reports and get structured, searchable data.",
      },
    ],
  }),
  component: Dashboard,
});

const ACCEPTED = ["application/pdf", "image/png", "image/jpeg", "image/webp"];
const MAX_BYTES = 20 * 1024 * 1024;

function Dashboard() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const runExtraction = useServerFn(processDocument);
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!loading && !user) navigate({ to: "/auth" });
  }, [loading, user, navigate]);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", user?.id],
    enabled: Boolean(user),
    refetchInterval: (query) =>
      (query.state.data as DocumentRow[] | undefined)?.some(
        (d) => d.status === "pending" || d.status === "processing",
      )
        ? 3000
        : false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("documents")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data as DocumentRow[];
    },
  });

  const selected = documents.find((d) => d.id === selectedId) ?? documents[0] ?? null;

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0 || !user) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        if (!ACCEPTED.includes(file.type)) {
          toast.error(`${file.name}: only PDF, PNG, JPG or WEBP files are supported.`);
          continue;
        }
        if (file.size > MAX_BYTES) {
          toast.error(`${file.name}: file is larger than 20MB.`);
          continue;
        }

        const safeName = file.name.replace(/[^\w.\- ]+/g, "_").slice(0, 120);
        const path = `${user.id}/${crypto.randomUUID()}-${safeName}`;

        const { error: uploadError } = await supabase.storage
          .from("documents")
          .upload(path, file, { contentType: file.type });
        if (uploadError) throw new Error(uploadError.message);

        const { data: inserted, error: insertError } = await supabase
          .from("documents")
          .insert({
            user_id: user.id,
            file_name: safeName,
            storage_path: path,
            mime_type: file.type,
            status: "processing",
          })
          .select("id")
          .single();
        if (insertError) throw new Error(insertError.message);

        await queryClient.invalidateQueries({ queryKey: ["documents", user.id] });
        setSelectedId(inserted.id);

        void runExtraction({ data: { id: inserted.id } })
          .then((result) => {
            if (!result.ok) toast.error(result.error);
            else toast.success(`${safeName} extracted`);
          })
          .catch(() => toast.error(`${safeName}: extraction failed`))
          .finally(() => queryClient.invalidateQueries({ queryKey: ["documents", user.id] }));
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function retry(id: string) {
    const result = await runExtraction({ data: { id } });
    if (!result.ok) toast.error(result.error);
    await queryClient.invalidateQueries({ queryKey: ["documents", user?.id] });
  }

  async function remove(doc: DocumentRow) {
    await supabase.storage.from("documents").remove([doc.storage_path]);
    const { error } = await supabase.from("documents").delete().eq("id", doc.id);
    if (error) {
      toast.error(error.message);
      return;
    }
    if (selectedId === doc.id) setSelectedId(null);
    await queryClient.invalidateQueries({ queryKey: ["documents", user?.id] });
    toast.success("Document deleted");
  }

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const bills = documents.filter((d) => d.doc_type === "bill");
  const billed = bills.reduce((sum, d) => sum + Number(d.total_amount ?? 0), 0);
  const processing = documents.filter(
    (d) => d.status === "pending" || d.status === "processing",
  ).length;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-gradient-hero text-primary-foreground">
              <Activity className="size-5" />
            </span>
            <div>
              <h1 className="font-display text-lg font-semibold leading-tight">MedExtract</h1>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await supabase.auth.signOut();
              navigate({ to: "/auth" });
            }}
          >
            <LogOut className="size-4" /> Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <section className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Documents" value={String(documents.length)} />
          <StatCard
            label="Total billed"
            value={bills.length ? formatAmount(billed, bills[0]?.currency ?? null) : "—"}
          />
          <StatCard label="In progress" value={String(processing)} />
        </section>

        <section
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            void handleFiles(e.dataTransfer.files);
          }}
          className={`mt-6 rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
            dragging ? "border-primary bg-accent/40" : "border-border bg-card"
          }`}
        >
          <UploadCloud className="mx-auto size-8 text-primary" />
          <h2 className="mt-3 font-display text-lg font-semibold">
            Upload a hospital bill or report
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Drag and drop, or browse. PDF, PNG, JPG or WEBP up to 20MB.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            multiple
            className="hidden"
            onChange={(e) => void handleFiles(e.target.files)}
          />
          <Button
            className="mt-5"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? <Loader2 className="size-4 animate-spin" /> : null}
            Choose files
          </Button>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[22rem_1fr]">
          <div className="space-y-3">
            <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Your documents
            </h2>
            {isLoading ? (
              <>
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </>
            ) : documents.length === 0 ? (
              <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                Nothing uploaded yet. Your extracted bills and reports will appear here.
              </p>
            ) : (
              documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedId(doc.id)}
                  className={`w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/60 ${
                    selected?.id === doc.id ? "border-primary shadow-panel" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{doc.file_name}</p>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {doc.provider_name ?? "Provider pending"} · {formatDate(doc.document_date)}
                      </p>
                    </div>
                    <StatusChip status={doc.status} />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <Badge variant="secondary" className="capitalize">
                      {doc.doc_type === "bill" ? (
                        <Receipt className="mr-1 size-3" />
                      ) : (
                        <FileText className="mr-1 size-3" />
                      )}
                      {doc.doc_type}
                    </Badge>
                    <span className="text-sm font-medium tabular-nums">
                      {doc.total_amount != null
                        ? formatAmount(doc.total_amount, doc.currency)
                        : ""}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>

          <div>
            {selected ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {selected.status === "failed" ? (
                    <Button variant="outline" size="sm" onClick={() => void retry(selected.id)}>
                      Retry extraction
                    </Button>
                  ) : null}
                  <Button variant="ghost" size="sm" onClick={() => void remove(selected)}>
                    <Trash2 className="size-4" /> Delete
                  </Button>
                </div>
                {selected.status === "failed" ? (
                  <Card className="border-destructive/40">
                    <CardContent className="flex items-start gap-3 p-5 text-sm">
                      <AlertTriangle className="mt-0.5 size-4 text-destructive" />
                      <span>{selected.error_message ?? "Extraction failed."}</span>
                    </CardContent>
                  </Card>
                ) : null}
                {selected.status === "processing" || selected.status === "pending" ? (
                  <Card>
                    <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" />
                      Reading the document and extracting data…
                    </CardContent>
                  </Card>
                ) : null}
                <DocumentDetail doc={selected} />
              </div>
            ) : (
              <Card className="h-full">
                <CardContent className="flex h-full min-h-64 flex-col items-center justify-center gap-2 text-center">
                  <FileText className="size-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Select a document to see its extracted data.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="shadow-panel">
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-2 font-display text-2xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

function StatusChip({ status }: { status: string }) {
  if (status === "done") {
    return (
      <span className="flex shrink-0 items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">
        <CheckCircle2 className="size-3" /> Done
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex shrink-0 items-center gap-1 rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-medium text-destructive">
        <AlertTriangle className="size-3" /> Failed
      </span>
    );
  }
  return (
    <span className="flex shrink-0 items-center gap-1 rounded-full bg-warning/20 px-2 py-0.5 text-xs font-medium text-warning-foreground">
      <Loader2 className="size-3 animate-spin" /> Working
    </span>
  );
}
