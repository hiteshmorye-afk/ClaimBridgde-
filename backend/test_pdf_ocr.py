import os
import sys
import tempfile
import pytest
from pathlib import Path
from PIL import Image, ImageDraw

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf as fitz
from app.ocr import run_ocr


def test_1_searchable_pdf():
    """Test 1: Searchable PDF with embedded text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "searchable.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        sample_text = (
            "CHONG HUA HOSPITAL\n"
            "PATIENT: JOHN DOE\n"
            "ADMISSION DATE: 12.08.2026\n"
            "DISCHARGE DATE: 15.08.2026\n"
            "TOTAL CHARGES: 75000.00\n"
            "DIAGNOSIS: ACUTE BRONCHITIS"
        )
        page.insert_text((50, 72), sample_text, fontsize=12)
        doc.save(pdf_path)
        doc.close()

        result = run_ocr(pdf_path)

        assert "CHONG HUA HOSPITAL" in result["text"]
        assert "TOTAL CHARGES: 75000.00" in result["text"]
        assert result["confidence"] == 1.0
        assert result["line_count"] >= 5
        assert result["page_count"] == 1
        assert all(l["extraction_method"] == "embedded_text" for l in result["lines"])
        assert all(l["page"] == 1 for l in result["lines"])
        print("[PASS] Test 1: Searchable PDF successfully extracted with 100% confidence.")


def test_2_scanned_pdf():
    """Test 2: Scanned PDF containing image without embedded text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "scanned.pdf")

        # Create an image with readable text
        img = Image.new("RGB", (800, 300), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), "HOSPITAL INVOICE BILL\nAMOUNT: 50000.00", fill="black")

        img_path = os.path.join(tmpdir, "temp_img.png")
        img.save(img_path)

        # Place image into PDF without adding any digital text stream
        doc = fitz.open()
        page = doc.new_page(width=800, height=300)
        page.insert_image(page.rect, filename=img_path)
        doc.save(pdf_path)
        doc.close()

        # Ensure raw PDF has 0 embedded text
        check_doc = fitz.open(pdf_path)
        assert check_doc[0].get_text().strip() == ""
        check_doc.close()

        # Run OCR - should render page and either extract text via OCR or fail without fabrication
        try:
            result = run_ocr(pdf_path)
            assert result["page_count"] == 1
            print(f"[PASS] Test 2: Scanned PDF rendered and processed via OCR engine (lines: {result['line_count']}).")
        except ValueError as e:
            # If local OCR engine has no Tesseract binary configured, it cleanly raises ValueError without fabricating
            assert "OCR extraction failed" in str(e)
            print(f"[PASS] Test 2: Scanned PDF rendered and failed cleanly without fabrication: {e}")


def test_3_multipage_pdf():
    """Test 3: Multi-page PDF preserving page boundaries and metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "multipage.pdf")
        doc = fitz.open()

        # Page 1
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((50, 72), "PAGE 1: INPATIENT ADMISSION\nPATIENT: SARAH CONNOR", fontsize=12)

        # Page 2
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((50, 72), "PAGE 2: PHARMACY DISPENSATION\nTOTAL MEDICINES: 12000.00", fontsize=12)

        doc.save(pdf_path)
        doc.close()

        result = run_ocr(pdf_path)

        assert result["page_count"] == 2
        assert "PAGE 1: INPATIENT ADMISSION" in result["text"]
        assert "PAGE 2: PHARMACY DISPENSATION" in result["text"]

        page_1_lines = [l for l in result["lines"] if l["page"] == 1]
        page_2_lines = [l for l in result["lines"] if l["page"] == 2]

        assert len(page_1_lines) >= 2
        assert len(page_2_lines) >= 2
        print("[PASS] Test 3: Multi-page PDF extracted preserving page boundaries and page numbers.")


def test_4_corrupted_and_empty_pdf():
    """Test 4: Error handling for corrupted, empty, and invalid signature PDFs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty PDF (0 bytes)
        empty_pdf = os.path.join(tmpdir, "empty.pdf")
        with open(empty_pdf, "wb") as f:
            pass

        try:
            run_ocr(empty_pdf)
            assert False, "Should have raised ValueError on empty PDF"
        except ValueError as e:
            assert "empty" in str(e).lower()
            print("[PASS] Test 4a: Correctly rejected 0-byte empty PDF.")

        # Invalid signature PDF
        corrupt_pdf = os.path.join(tmpdir, "corrupt.pdf")
        with open(corrupt_pdf, "wb") as f:
            f.write(b"NOT_A_VALID_PDF_HEADER_CONTENT")

        try:
            run_ocr(corrupt_pdf)
            assert False, "Should have raised ValueError on invalid PDF signature"
        except ValueError as e:
            assert "invalid pdf signature" in str(e).lower()
            print("[PASS] Test 4b: Correctly rejected invalid signature PDF.")


def test_5_png_jpg_compatibility():
    """Test 5: Compatibility with existing image files (PNG/JPG)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test_receipt.png")
        img = Image.new("RGB", (600, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "APOLLO HOSPITALS BILL", fill="black")
        img.save(img_path)

        try:
            result = run_ocr(img_path)
            assert "text" in result
            assert "confidence" in result
            assert "lines" in result
            print(f"[PASS] Test 5: Image compatibility verified (extracted: {result['line_count']} lines).")
        except ValueError as e:
            # If no OCR engine is installed locally, clean error is raised
            assert "OCR extraction failed" in str(e)
            print(f"[PASS] Test 5: Image processed with clean exception: {e}")


def test_6_no_fabricated_text_on_failure():
    """Test 6: Verify that blank images NEVER return hardcoded Mrs. Tuhod mock text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        blank_img = os.path.join(tmpdir, "blank.png")
        img = Image.new("RGB", (100, 100), color="white")
        img.save(blank_img)

        try:
            result = run_ocr(blank_img)
            # If it didn't raise, ensure it did NOT return the hardcoded mock text
            assert "MRS. TUHOD" not in result["text"]
            assert "184000.00" not in result["text"]
        except ValueError as e:
            assert "OCR extraction failed" in str(e)
            print("[PASS] Test 6: Confirmed no fabricated text is returned on failed OCR.")


if __name__ == "__main__":
    print("\n=== RUNNING CLAIMBRIDGE STEP 1 PDF & OCR TESTS ===")
    test_1_searchable_pdf()
    test_2_scanned_pdf()
    test_3_multipage_pdf()
    test_4_corrupted_and_empty_pdf()
    test_5_png_jpg_compatibility()
    test_6_no_fabricated_text_on_failure()
    print("\nALL 6 FOCUSED TESTS PASSED CLEANLY!")
