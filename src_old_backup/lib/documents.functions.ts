import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { z } from "zod";

const IdInput = z.object({ id: z.string().uuid() });

export const processDocument = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: unknown) => IdInput.parse(input))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;

    const { data: doc, error } = await supabase
      .from("documents")
      .select("id, storage_path, file_name, mime_type")
      .eq("id", data.id)
      .eq("user_id", userId)
      .single();

    if (error || !doc) throw new Error("Document not found.");

    await supabase
      .from("documents")
      .update({ status: "processing", error_message: null })
      .eq("id", doc.id);

    try {
      const { data: file, error: dlError } = await supabase.storage
        .from("documents")
        .download(doc.storage_path);
      if (dlError || !file) throw new Error("Could not read the uploaded file.");

      const bytes = Buffer.from(await file.arrayBuffer());
      if (bytes.byteLength === 0) throw new Error("The uploaded file is empty.");

      const { extractFromDocument } = await import("./extract.server");
      const extracted = await extractFromDocument({
        base64: bytes.toString("base64"),
        mimeType: doc.mime_type || "application/pdf",
        fileName: doc.file_name,
      });

      const { error: updateError } = await supabase
        .from("documents")
        .update({
          status: "done",
          doc_type: extracted.doc_type,
          patient_name: extracted.patient_name,
          provider_name: extracted.provider_name,
          document_date: extracted.document_date,
          total_amount: extracted.total_amount,
          currency: extracted.currency,
          line_items: extracted.line_items,
          lab_results: extracted.lab_results,
          summary: extracted.summary,
          raw_text: extracted.raw_text,
          error_message: null,
        })
        .eq("id", doc.id);

      if (updateError) throw new Error(updateError.message);

      return { ok: true as const };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Extraction failed.";
      await supabase
        .from("documents")
        .update({ status: "failed", error_message: message })
        .eq("id", doc.id);
      return { ok: false as const, error: message };
    }
  });