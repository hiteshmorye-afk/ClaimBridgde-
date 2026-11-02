with open("src/api/documents.ts", "r", encoding="utf-8") as f:
    text = f.read()

target = """  pipeline?: {
    stages: DocumentProcessingStage[];
  };
}"""

replacement = """  pipeline?: {
    stages: DocumentProcessingStage[];
  };
  reliabilityScore?: number;
  reliabilityTier?: string;
  reliabilityTierSummary?: string;
  authenticityStatus?: string;
  plainEnglishExplanation?: string;
  reliabilityBreakdown?: Record<string, {
    score: number;
    max: number;
    label: string;
    status: string;
    description: string;
  }>;
  fieldChecks?: Array<{
    information: string;
    foundInPdf: string;
    comparedWith: string;
    result: string;
    explanation?: string;
  }>;
  medicalDiagnoses?: Array<{
    originalDiagnosis: string;
    normalizedDiagnosis: string;
    icd10Code: string;
    description: string;
    confidence: number;
    status: string;
    evidence?: string;
  }>;
  fileUrl?: string;
}"""

assert target in text, "target not found in documents.ts"
text = text.replace(target, replacement, 1)

with open("src/api/documents.ts", "w", encoding="utf-8") as f:
    f.write(text)

print("src/api/documents.ts updated successfully!")
