/**
 * ClaimBridge Form Validation & Clinical Catalogue Unit Test Suite
 * Tests all requirements from Section 12 of Change 1.
 */

import {
  validatePatientName,
  validatePatientAge,
  validateHospital,
  validatePolicyNumber,
  validateProvider,
  validateClaimedAmount,
  validateDates,
  validateDiagnosis,
  validateClaimForm,
  CLINICAL_DIAGNOSIS_CATALOGUE,
  UNLISTED_DIAGNOSIS_CODE,
} from "./src/lib/clinicalCatalogue.ts";

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  [PASS] ${message}`);
  } else {
    failed++;
    console.error(`  [FAIL] ${message}`);
  }
}

console.log("======================================================================");
console.log("CLAIMBRIDGE CLINICAL FORM & DIAGNOSIS VALIDATION SUITE");
console.log("======================================================================\n");

// 1. PATIENT FULL NAME
console.log("1. Patient Full Name Validation:");
assert(validatePatientName("David Miller") === null, "Accepts standard full name 'David Miller'");
assert(validatePatientName("Mary-Jane O'Neil") === null, "Accepts hyphens and apostrophes 'Mary-Jane O\'Neil'");
assert(validatePatientName("José García") === null, "Accepts international diacritics 'José García'");
assert(validatePatientName("David123") !== null, "Rejects name containing numbers 'David123'");
assert(validatePatientName("12345") !== null, "Rejects numeric-only name '12345'");
assert(validatePatientName("") !== null, "Rejects empty name");
assert(validatePatientName("   ") !== null, "Rejects whitespace-only name");
assert(validatePatientName("John @Doe") !== null, "Rejects arbitrary symbols 'John @Doe'");

// 2. PATIENT AGE
console.log("\n2. Patient Age Validation:");
assert(validatePatientAge(45) === null, "Accepts standard age 45");
assert(validatePatientAge(0) === null, "Accepts minimum boundary age 0");
assert(validatePatientAge(120) === null, "Accepts maximum boundary age 120");
assert(validatePatientAge(-1) !== null, "Rejects negative age -1");
assert(validatePatientAge(121) !== null, "Rejects age exceeding maximum 121");
assert(validatePatientAge("45.5") !== null, "Rejects decimal age 45.5");
assert(validatePatientAge("abc") !== null, "Rejects alphabetic age");
assert(validatePatientAge("") !== null, "Rejects empty age");

// 3. HOSPITAL / PROVIDER NAME
console.log("\n3. Hospital Name Validation:");
assert(validateHospital("Apollo Hospitals International") === null, "Accepts legitimate hospital name");
assert(validateHospital("St. Jude Clinic 24") === null, "Accepts hospital name with numbers/punctuation");
assert(validateHospital("") !== null, "Rejects empty hospital name");
assert(validateHospital("   ") !== null, "Rejects whitespace-only hospital name");

// 4. POLICY NUMBER (8-13 DIGITS)
console.log("\n4. Policy Number Validation (8-13 digits):");
assert(validatePolicyNumber("12345678") === null, "Accepts minimum 8 digits '12345678'");
assert(validatePolicyNumber("1234567890123") === null, "Accepts maximum 13 digits '1234567890123'");
assert(validatePolicyNumber("01234567") === null, "Preserves and accepts leading zero '01234567'");
assert(validatePolicyNumber("98765432101") === null, "Accepts 11 digits '98765432101'");
assert(validatePolicyNumber("1234567") !== null, "Rejects 7 digits (too short)");
assert(validatePolicyNumber("12345678901234") !== null, "Rejects 14 digits (too long)");
assert(validatePolicyNumber("POL-12345678") !== null, "Rejects alphabetic prefix 'POL-12345678'");
assert(validatePolicyNumber("1234 5678") !== null, "Rejects spaces in policy number");
assert(validatePolicyNumber("1234-5678") !== null, "Rejects hyphens in policy number");

// 5. INSURANCE PROVIDER / TPA
console.log("\n5. Insurance Provider Validation:");
assert(validateProvider("Pacific Healthcare TPA") === null, "Accepts valid provider");
assert(validateProvider("") !== null, "Rejects empty provider");
assert(validateProvider("   ") !== null, "Rejects whitespace-only provider");

// 6. CLAIMED AMOUNT
console.log("\n6. Claimed Amount Validation:");
assert(validateClaimedAmount("145000") === null, "Accepts integer amount '145000'");
assert(validateClaimedAmount("145000.50") === null, "Accepts 2 decimal amount '145000.50'");
assert(validateClaimedAmount("0") !== null, "Rejects zero amount");
assert(validateClaimedAmount("-500") !== null, "Rejects negative amount");
assert(validateClaimedAmount("abc") !== null, "Rejects non-numeric amount");
assert(validateClaimedAmount("145000.555") !== null, "Rejects more than 2 decimal places");

// 7. DATES & ORDERING
console.log("\n7. Admission and Discharge Date Ordering:");
const validDates = validateDates("2026-08-10", "2026-08-14");
assert(validDates.admissionError === null && validDates.dischargeError === null, "Accepts valid date order (10th to 14th)");

const sameDayDates = validateDates("2026-08-10", "2026-08-10");
assert(sameDayDates.admissionError === null && sameDayDates.dischargeError === null, "Accepts same-day admission and discharge");

const invertedDates = validateDates("2026-08-15", "2026-08-10");
assert(invertedDates.admissionError !== null, "Rejects admission date after discharge date");

const missingDates = validateDates("", "2026-08-10");
assert(missingDates.admissionError !== null, "Rejects missing admission date");

// 8. DIAGNOSIS & CLINICAL NOTES
console.log("\n8. Diagnosis Selection & Catalogue Validation:");
assert(validateDiagnosis("K81.0", "") === null, "Accepts valid catalogue diagnosis K81.0");
assert(validateDiagnosis("", "") !== null, "Rejects empty diagnosis selection");
assert(validateDiagnosis(UNLISTED_DIAGNOSIS_CODE, "") !== null, "Rejects unlisted diagnosis without clinical description");
assert(validateDiagnosis(UNLISTED_DIAGNOSIS_CODE, "Acute Pancreatitis") === null, "Accepts unlisted diagnosis with clinical description");

// Verify catalogue integrity
const k81 = CLINICAL_DIAGNOSIS_CATALOGUE.find((d) => d.code === "K81.0");
assert(k81 !== undefined, "Catalogue contains Acute Cholecystitis K81.0");
assert(k81.policyMapping.status === "Potentially Covered", "K81.0 policy status is Potentially Covered");

const z41 = CLINICAL_DIAGNOSIS_CATALOGUE.find((d) => d.code === "Z41.1");
assert(z41 !== undefined, "Catalogue contains Cosmetic Surgery Z41.1");
assert(z41.policyMapping.status === "Excluded", "Z41.1 policy status is Excluded");

// 9. COMPLETE FORM VALIDATION
console.log("\n9. Complete Form-Level Validation:");
const validForm = {
  patientName: "David Miller",
  patientAge: "46",
  hospital: "Apollo Hospitals International",
  policyNumber: "98765432101",
  insuranceProvider: "Pacific Healthcare TPA",
  admissionDate: "2026-08-10",
  dischargeDate: "2026-08-14",
  diagnosisCode: "K81.0",
  diagnosisDisplay: "Acute Cholecystitis",
  customDiagnosis: "",
  clinicalNotes: "Patient admitted with abdominal pain.",
  claimedAmount: "145000",
};
const validResult = validateClaimForm(validForm);
assert(validResult.isValid === true, "Valid complete form passes validation");

const invalidForm = { ...validForm, patientName: "David123", policyNumber: "12345" };
const invalidResult = validateClaimForm(invalidForm);
assert(invalidResult.isValid === false, "Invalid form is rejected");
assert(invalidResult.errors.patientName !== undefined, "Invalid name error present");
assert(invalidResult.errors.policyNumber !== undefined, "Invalid policy number error present");

console.log("\n======================================================================");
console.log(`TOTAL TESTS: ${passed + failed} | PASSED: ${passed} | FAILED: ${failed}`);
console.log("======================================================================");

if (failed > 0) {
  process.exit(1);
} else {
  console.log("ALL FORM VALIDATION UNIT TESTS PASSED CLEANLY!");
}
