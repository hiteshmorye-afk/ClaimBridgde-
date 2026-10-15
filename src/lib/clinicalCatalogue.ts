/**
 * ClaimBridge Clinical Diagnosis Catalogue & Validation Engine
 * 
 * Provides verified ICD-10 clinical diagnosis mappings, policy conditions,
 * and strict form validation rules for healthcare insurance intake.
 */

export interface PolicyMappingInfo {
  status: "Potentially Covered" | "Excluded" | "Policy mapping pending";
  clauseReference: string;
  notes: string;
  evidenceSnippet?: string;
}

export interface DiagnosisItem {
  code: string;
  display: string;
  category: string;
  codeSystem: "ICD-10" | "Unresolved";
  policyMapping: PolicyMappingInfo;
}

export const UNLISTED_DIAGNOSIS_CODE = "UNLISTED";

/**
 * Standard Verified Clinical Diagnosis Catalogue (ICD-10 Standard)
 * Includes honest mapping against standard health insurance policy clauses.
 */
export const CLINICAL_DIAGNOSIS_CATALOGUE: DiagnosisItem[] = [
  {
    code: "K81.0",
    display: "Acute Cholecystitis",
    category: "Digestive System / Gallbladder",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 1 & SECTION 2 - HOSPITALIZATION & SURGICAL TREATMENT",
      notes: "Medically necessary inpatient surgical or medical treatment. Subject to itemized document audit.",
      evidenceSnippet: "Hospitalization expenses are covered when the insured person requires medically necessary inpatient treatment. Medically necessary surgical procedures are covered...",
    },
  },
  {
    code: "K35.80",
    display: "Acute Appendicitis, unspecified",
    category: "Digestive System / Appendix",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 2 - SURGICAL TREATMENT",
      notes: "Emergency surgical intervention (appendectomy). Covered under inpatient surgical benefits.",
      evidenceSnippet: "Medically necessary surgical procedures are covered subject to the terms and conditions of the policy.",
    },
  },
  {
    code: "H25.9",
    display: "Senile Cataract, unspecified",
    category: "Eye and Adnexa",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 2 - SURGICAL TREATMENT",
      notes: "Elective or daycare ophthalmic surgical procedure. Subject to standard policy capping and lens sub-limits.",
      evidenceSnippet: "Medically necessary surgical procedures are covered subject to the terms and conditions of the policy.",
    },
  },
  {
    code: "I10",
    display: "Essential (Primary) Hypertension",
    category: "Circulatory System",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 3 - MEDICAL TREATMENT",
      notes: "Medical management. Inpatient coverage applicable if hypertensive urgency or crisis requiring monitoring.",
      evidenceSnippet: "Reasonable and medically necessary medical treatment is covered when supported by appropriate medical documentation.",
    },
  },
  {
    code: "E11.9",
    display: "Type 2 Diabetes Mellitus without complications",
    category: "Endocrine and Metabolic",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 3 & SECTION 5 - MEDICAL TREATMENT & WAITING PERIOD",
      notes: "Subject to pre-existing disease (PED) waiting period verification and active policy tenure.",
      evidenceSnippet: "Certain medical conditions may be subject to an applicable waiting period before coverage becomes effective.",
    },
  },
  {
    code: "A90",
    display: "Dengue Fever [classical dengue]",
    category: "Infectious Diseases",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 1 - HOSPITALIZATION COVERAGE",
      notes: "Inpatient admission reimbursable with documented platelet monitoring and supportive IV therapy.",
      evidenceSnippet: "Hospitalization expenses are covered when the insured person requires medically necessary inpatient treatment.",
    },
  },
  {
    code: "S72.9",
    display: "Fracture of Femur, unspecified",
    category: "Injury and Trauma",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 1 & SECTION 2 - TRAUMA & SURGERY",
      notes: "Trauma and orthopedic surgery with internal fixation. Medically necessary emergency care.",
      evidenceSnippet: "Hospitalization expenses are covered when the insured person requires medically necessary inpatient treatment.",
    },
  },
  {
    code: "I20.9",
    display: "Angina Pectoris, unspecified",
    category: "Circulatory System / Cardiac",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Potentially Covered",
      clauseReference: "SECTION 1 & SECTION 2 - INPATIENT CARDIAC CARE",
      notes: "Inpatient coronary care, angiography, and interventions. Subject to policy room capping.",
      evidenceSnippet: "Reasonable and medically necessary medical treatment is covered when supported by appropriate medical documentation.",
    },
  },
  {
    code: "Z41.1",
    display: "Cosmetic Plastic Surgery (e.g., Elective Rhinoplasty)",
    category: "Elective Aesthetic Procedures",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Excluded",
      clauseReference: "SECTION 4 - EXCLUSIONS",
      notes: "Strict policy exclusion. Aesthetic and elective cosmetic surgeries are non-reimbursable.",
      evidenceSnippet: "Cosmetic surgery is excluded from coverage.",
    },
  },
  {
    code: "Z52.0",
    display: "Experimental / Unproven Stem Cell Therapy",
    category: "Investigational Treatments",
    codeSystem: "ICD-10",
    policyMapping: {
      status: "Excluded",
      clauseReference: "SECTION 4 - EXCLUSIONS",
      notes: "Non-covered therapy. Policy terms exclude unproven, experimental, or investigational protocols.",
      evidenceSnippet: "Experimental treatment is not covered under this policy.",
    },
  },
];

/**
 * Recognized Insurance Providers / TPAs
 */
export const CONFIGURED_INSURERS: string[] = [
  "Pacific Healthcare TPA",
  "Star Health and Allied Insurance",
  "HDFC ERGO General Insurance",
  "Niva Bupa Health Insurance",
  "ICICI Lombard General Insurance",
  "Care Health Insurance",
  "National Insurance Company",
  "Bajaj Allianz General Insurance",
  "United India Insurance",
  "New India Assurance",
];

export interface ClaimFormState {
  patientName: string;
  patientAge: string;
  hospital: string;
  policyNumber: string;
  insuranceProvider: string;
  admissionDate: string;
  dischargeDate: string;
  diagnosisCode: string;
  diagnosisDisplay: string;
  customDiagnosis: string;
  clinicalNotes: string;
  claimedAmount: string;
}

/**
 * Validation Functions
 */

export function validatePatientName(name: string): string | null {
  const trimmed = (name || "").trim();
  if (!trimmed) {
    return "Patient full name is required.";
  }
  if (/\d/.test(trimmed)) {
    return "Patient full name must not contain numbers.";
  }
  // Allow Unicode letters (accents, diacritics), spaces, hyphens, apostrophes, and periods
  // Reject arbitrary symbols like @, #, $, %, etc.
  const nameRegex = /^[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\s'\-.]+$/;
  if (!nameRegex.test(trimmed)) {
    return "Patient full name contains invalid characters (use only letters, spaces, hyphens, and apostrophes).";
  }
  if (trimmed.length < 2) {
    return "Patient full name must be at least 2 characters.";
  }
  if (trimmed.length > 100) {
    return "Patient full name cannot exceed 100 characters.";
  }
  return null;
}

export function validatePatientAge(age: string | number): string | null {
  if (age === "" || age === null || age === undefined) {
    return "Patient age is required.";
  }
  const strAge = String(age).trim();
  if (!strAge) {
    return "Patient age is required.";
  }
  // Must be non-negative integer
  if (!/^\d+$/.test(strAge)) {
    return "Patient age must be a whole number (no decimals or symbols).";
  }
  const numAge = Number(strAge);
  if (isNaN(numAge)) {
    return "Patient age must be a valid number.";
  }
  if (numAge < 0 || numAge > 120) {
    return "Patient age must be between 0 and 120 years.";
  }
  return null;
}

export function validateHospital(hospital: string): string | null {
  const trimmed = (hospital || "").trim();
  if (!trimmed) {
    return "Hospital / provider name is required.";
  }
  if (trimmed.length < 2) {
    return "Hospital / provider name must be at least 2 characters.";
  }
  if (trimmed.length > 150) {
    return "Hospital / provider name cannot exceed 150 characters.";
  }
  return null;
}

export function validatePolicyNumber(policyNum: string): string | null {
  const trimmed = (policyNum || "").trim();
  if (!trimmed) {
    return "Policy number is required.";
  }
  if (!/^\d+$/.test(trimmed)) {
    return "Policy number must contain only numeric digits (no letters, spaces, or symbols).";
  }
  if (trimmed.length < 8 || trimmed.length > 13) {
    return `Policy number must be between 8 and 13 digits (currently ${trimmed.length} digits).`;
  }
  return null;
}

export function validateProvider(provider: string): string | null {
  const trimmed = (provider || "").trim();
  if (!trimmed) {
    return "Insurance provider / TPA is required.";
  }
  if (trimmed.length > 150) {
    return "Provider name cannot exceed 150 characters.";
  }
  return null;
}

export function validateClaimedAmount(amount: string | number): string | null {
  if (amount === "" || amount === null || amount === undefined) {
    return "Claimed amount is required.";
  }
  const str = String(amount).trim();
  if (!str) {
    return "Claimed amount is required.";
  }
  const num = Number(str);
  if (isNaN(num) || !isFinite(num)) {
    return "Claimed amount must be a valid numeric value.";
  }
  if (num <= 0) {
    return "Claimed amount must be a positive amount greater than zero.";
  }
  // Check decimal places
  if (str.includes(".")) {
    const decimals = str.split(".")[1];
    if (decimals && decimals.length > 2) {
      return "Claimed amount cannot have more than 2 decimal places.";
    }
  }
  if (num > 100_000_000) {
    return "Claimed amount exceeds the maximum permissible limit (₹100,000,000).";
  }
  return null;
}

export function validateDates(
  admissionDate: string,
  dischargeDate: string
): { admissionError: string | null; dischargeError: string | null } {
  let admissionError: string | null = null;
  let dischargeError: string | null = null;

  if (!admissionDate) {
    admissionError = "Admission date is required.";
  }
  if (!dischargeDate) {
    dischargeError = "Discharge date is required.";
  }

  if (admissionDate && dischargeDate) {
    const adm = new Date(admissionDate);
    const dis = new Date(dischargeDate);
    if (isNaN(adm.getTime())) {
      admissionError = "Admission date is invalid.";
    }
    if (isNaN(dis.getTime())) {
      dischargeError = "Discharge date is invalid.";
    }
    if (!isNaN(adm.getTime()) && !isNaN(dis.getTime())) {
      if (adm > dis) {
        admissionError = "Admission date cannot be after discharge date.";
        dischargeError = "Discharge date cannot be before admission date.";
      }
    }
  }

  return { admissionError, dischargeError };
}

export function validateDiagnosis(
  diagnosisCode: string,
  customDiagnosis: string
): string | null {
  if (!diagnosisCode) {
    return "Diagnosis selection is mandatory. Please select from the catalogue or choose 'Other / Unlisted'.";
  }
  if (diagnosisCode === UNLISTED_DIAGNOSIS_CODE) {
    if (!customDiagnosis || !customDiagnosis.trim()) {
      return "Please enter a clinical description for the unlisted diagnosis.";
    }
    if (customDiagnosis.trim().length < 3) {
      return "Unlisted diagnosis description must be at least 3 characters.";
    }
  }
  return null;
}

export function validateClaimForm(form: ClaimFormState): {
  isValid: boolean;
  errors: Record<string, string>;
} {
  const errors: Record<string, string> = {};

  const nameErr = validatePatientName(form.patientName);
  if (nameErr) errors.patientName = nameErr;

  const ageErr = validatePatientAge(form.patientAge);
  if (ageErr) errors.patientAge = ageErr;

  const hospErr = validateHospital(form.hospital);
  if (hospErr) errors.hospital = hospErr;

  const polErr = validatePolicyNumber(form.policyNumber);
  if (polErr) errors.policyNumber = polErr;

  const provErr = validateProvider(form.insuranceProvider);
  if (provErr) errors.insuranceProvider = provErr;

  const amtErr = validateClaimedAmount(form.claimedAmount);
  if (amtErr) errors.claimedAmount = amtErr;

  const { admissionError, dischargeError } = validateDates(
    form.admissionDate,
    form.dischargeDate
  );
  if (admissionError) errors.admissionDate = admissionError;
  if (dischargeError && !errors.admissionDate) errors.dischargeDate = dischargeError;

  const diagErr = validateDiagnosis(form.diagnosisCode, form.customDiagnosis);
  if (diagErr) errors.diagnosis = diagErr;

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
