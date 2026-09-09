from .validation_engine import validate_extracted_information
from .ocr import run_ocr
from .document_classifier import classify_document
from .information_extractor import extract_information


def process_document(image_path: str):
    """
    Complete document-level processing pipeline.

    Image
      ↓
    OCR
      ↓
    Document Classification
      ↓
    Information Extraction
    """

    print("\n" + "=" * 60)
    print("CLAIMBRIDGE DOCUMENT PROCESSING PIPELINE")
    print("=" * 60)

    # -----------------------------------
    # STEP 1: OCR
    # -----------------------------------
    print("\n[1/3] Running OCR...")

    ocr_result = run_ocr(image_path)

    extracted_text = ocr_result.get("text", "")
    ocr_confidence = ocr_result.get("confidence", 0.0)

    print(f"OCR Confidence: {ocr_confidence * 100:.2f}%")
    print(f"Detected Lines: {ocr_result.get('line_count', 0)}")

    # -----------------------------------
    # STEP 2: DOCUMENT CLASSIFICATION
    # -----------------------------------
    print("\n[2/3] Classifying document...")

    classification_result = classify_document(extracted_text)

    print(
        f"Document Type: "
        f"{classification_result['document_type']}"
    )

    print(
        f"Classification Confidence: "
        f"{classification_result['confidence'] * 100:.2f}%"
    )

    # -----------------------------------
    # STEP 3: INFORMATION EXTRACTION
    # -----------------------------------
    print("\n[3/3] Extracting information...")

    extraction_result = extract_information(extracted_text)
    # -----------------------------------
    # STEP 4: VALIDATION & CONSISTENCY
    # -----------------------------------
    print("\n[4/4] Validating extracted information...")

    validation_result = validate_extracted_information(
        extraction_result
    )

    print(
        f"Verification Status: "
        f"{validation_result['verification_status']}"
    )

    print(
        f"Readiness Score: "
        f"{validation_result['readiness_score']:.2f}%"
    )

    print(
        f"Missing Fields: "
        f"{validation_result['missing_fields']}"
    )

    print(
        f"Mismatches: "
        f"{validation_result['mismatches']}"
    )
    # -----------------------------------
    # FINAL RESULT
    # -----------------------------------
    result = {
        "file": image_path,
        "ocr": {
            "text": extracted_text,
            "confidence": ocr_confidence,
            "line_count": ocr_result.get("line_count", 0),
        },
        "classification": classification_result,
        "extracted_information": extraction_result,
        "validation": validation_result,
    }

    print("\n" + "=" * 60)
    print("DOCUMENT PROCESSING COMPLETED")
    print("=" * 60)

    print("\nDocument Type:")
    print(classification_result["document_type"])

    print("\nExtracted Information:")

    for key, value in extraction_result.items():
        print(f"{key}: {value}")

    return result


if __name__ == "__main__":

    import os

    backend_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    input_path = os.path.join(
        backend_dir,
        "test_images",
        "sample_bill.jpg"
    )

    process_document(input_path)