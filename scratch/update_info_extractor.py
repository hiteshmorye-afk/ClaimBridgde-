with open("backend/app/information_extractor.py", "r", encoding="utf-8") as f:
    text = f.read()

target1 = """    return {
        "doctor_name": doctor,
        "clinic_name": clinic,
        "prescription_date": presc_date,
        "symptoms": symptoms,
        "medications": medications,
    }"""

replacement1 = """    # Diagnosis
    diagnosis = None
    diag_match = re.search(r"(?:Clinical\s+Diagnosis|Provisional\s+Diagnosis|Diagnosis)\s*[:\-]\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)
    if diag_match:
        diagnosis = re.split(r"\s+(?:ICD|Procedure|Treatment|Rx)\s*[:\-]", diag_match.group(1).strip(), flags=re.IGNORECASE)[0].strip()

    return {
        "doctor_name": doctor,
        "clinic_name": clinic,
        "prescription_date": presc_date,
        "symptoms": symptoms,
        "diagnosis": diagnosis,
        "medications": medications,
    }"""

target2 = """    elif canonical_type == "consultation_letter":
        details = extract_consultation_details(normalized_text)
        core_result["document_type"] = "consultation_letter"
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]
        core_result["medications"] = details.get("medications", [])"""

replacement2 = """    elif canonical_type == "consultation_letter":
        details = extract_consultation_details(normalized_text)
        core_result["document_type"] = "consultation_letter"
        if details.get("doctor_name"):
            core_result["doctor_name"] = details["doctor_name"]
        if details.get("diagnosis"):
            core_result["diagnosis"] = details["diagnosis"]
        core_result["medications"] = details.get("medications", [])"""

assert target1 in text, "target1 not found"
assert target2 in text, "target2 not found"

text = text.replace(target1, replacement1, 1)
text = text.replace(target2, replacement2, 1)

with open("backend/app/information_extractor.py", "w", encoding="utf-8") as f:
    f.write(text)

print("information_extractor.py updated successfully!")
