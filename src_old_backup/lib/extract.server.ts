import { z } from "zod";

export const ExtractedSchema = z.object({
  doc_type: z.enum(["bill", "report", "unknown"]).default("unknown"),
  patient_name: z.string().nullable().default(null),
  provider_name: z.string().nullable().default(null),
  document_date: z.string().nullable().default(null),
  total_amount: z.number().nullable().default(null),
  currency: z.string().nullable().default(null),
  line_items: z
    .array(
      z.object({
        description: z.string(),
        quantity: z.number().nullable().default(null),
        amount: z.number().nullable().default(null),
      }),
    )
    .default([]),
  lab_results: z
    .array(
      z.object({
        test: z.string(),
        value: z.string(),
        unit: z.string().nullable().default(null),
        reference_range: z.string().nullable().default(null),
        flag: z.enum(["low", "normal", "high", "unknown"]).default("unknown"),
      }),
    )
    .default([]),
  summary: z.string().nullable().default(null),
  raw_text: z.string().nullable().default(null),
});

export type Extracted = z.infer<typeof ExtractedSchema>;

const SYSTEM_PROMPT = `You are a medical document data-extraction engine.
You receive a scanned hospital bill, invoice, discharge summary, or lab/diagnostic report.
Read every visible character, including handwriting and stamps.

Return ONLY a JSON object with this exact shape:
{
  "doc_type": "bill" | "report" | "unknown",
  "patient_name": string|null,
  "provider_name": string|null,          // hospital / lab / clinic name
  "document_date": "YYYY-MM-DD"|null,
  "total_amount": number|null,           // grand total payable, digits only
  "currency": string|null,               // ISO code, e.g. INR, USD
  "line_items": [ { "description": string, "quantity": number|null, "amount": number|null } ],
  "lab_results": [ { "test": string, "value": string, "unit": string|null, "reference_range": string|null, "flag": "low"|"normal"|"high"|"unknown" } ],
  "summary": string|null,                // 1-2 sentence plain-language summary
  "raw_text": string                     // full transcribed text of the document
}

Rules: never invent values; use null when unreadable. line_items only for bills, lab_results only for reports. No markdown fences.`;

function stripFences(text: string): string {
  const trimmed = text.trim();
  if (!trimmed.startsWith("```")) return trimmed;
  return trimmed
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/```$/, "")
    .trim();
}

export async function extractFromDocument(params: {
  base64: string;
  mimeType: string;
  fileName: string;
}): Promise<Extracted> {
  const apiKey = process.env["LOVABLE_API_KEY"];
  if (!apiKey) throw new Error("AI is not configured for this project.");

  const isPdf = params.mimeType === "application/pdf";
  const content = isPdf
    ? [
        { type: "text", text: "Extract the structured data from this document." },
        {
          type: "file",
          file: {
            filename: params.fileName,
            file_data: `data:${params.mimeType};base64,${params.base64}`,
          },
        },
      ]
    : [
        { type: "text", text: "Extract the structured data from this document." },
        {
          type: "image_url",
          image_url: { url: `data:${params.mimeType};base64,${params.base64}` },
        },
      ];

  const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Lovable-API-Key": apiKey,
    },
    body: JSON.stringify({
      model: "google/gemini-3.6-flash",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content },
      ],
      response_format: { type: "json_object" },
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    console.error(`AI gateway error [${response.status}]: ${body}`);
    if (response.status === 429) throw new Error("Too many requests right now. Please retry in a moment.");
    if (response.status === 402) throw new Error("AI credits exhausted. Add credits to continue extracting.");
    throw new Error(`Extraction failed (${response.status}).`);
  }

  const payload = (await response.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const text = payload.choices?.[0]?.message?.content ?? "";
  if (!text) throw new Error("The model returned an empty response.");

  let parsed: unknown;
  try {
    parsed = JSON.parse(stripFences(text));
  } catch {
    throw new Error("The model returned an unreadable response.");
  }

  return ExtractedSchema.parse(parsed);
}