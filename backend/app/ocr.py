import io
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union

import cv2
import numpy as np
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

os.environ["FLAGS_enable_pir_api"] = "0"

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception:
    PADDLE_AVAILABLE = False


def preprocess_image(image_input: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
    """Preprocess image for optimal OCR extraction."""
    if isinstance(image_input, str):
        image = cv2.imread(image_input)
        if image is None:
            raise ValueError(f"Unable to read image at: {image_input}")
    elif isinstance(image_input, Image.Image):
        image = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        image = image_input
    else:
        raise ValueError("Unsupported image input type for preprocessing")

    height, width = image.shape[:2]
    max_width = 1600

    if width > max_width:
        scale = max_width / width
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    threshold = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )

    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)


def _ocr_single_image(image_input: Union[str, np.ndarray, Image.Image]) -> Dict[str, Any]:
    """Run PaddleOCR or PyTesseract on an image array or file path."""
    lines: List[Dict[str, Any]] = []
    all_scores: List[float] = []

    # 1. Try PaddleOCR if available
    if PADDLE_AVAILABLE:
        try:
            ocr = PaddleOCR(lang="en", enable_mkldnn=False)
            if isinstance(image_input, Image.Image):
                np_img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
                results = ocr.predict(np_img)
            else:
                results = ocr.predict(image_input)

            for result in results:
                texts = result.get("rec_texts", [])
                scores = result.get("rec_scores", [])
                for text, score in zip(texts, scores):
                    t = text.strip()
                    if not t:
                        continue
                    sc = float(score)
                    lines.append({
                        "text": t,
                        "confidence": round(sc, 4),
                    })
                    all_scores.append(sc)

            if lines:
                avg_score = sum(all_scores) / len(all_scores)
                return {
                    "text": "\n".join(l["text"] for l in lines),
                    "confidence": round(avg_score, 4),
                    "lines": lines,
                    "line_count": len(lines),
                }
        except Exception as exc:
            print(f"[OCR Notice] PaddleOCR processing failed: {exc}. Trying fallback.")

    # 2. Try PyTesseract fallback
    try:
        import pytesseract
        import shutil

        # Auto-detect Tesseract binary path on Windows if not in PATH
        current_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
        if current_cmd == "tesseract" and not shutil.which("tesseract"):
            for cand in [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            ]:
                if os.path.isfile(cand):
                    pytesseract.pytesseract.tesseract_cmd = cand
                    break

        if isinstance(image_input, str):
            pil_img = Image.open(image_input)
        elif isinstance(image_input, np.ndarray):
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) if len(image_input.shape) == 3 else image_input
            pil_img = Image.fromarray(rgb)
        else:
            pil_img = image_input

        extracted_text_raw = pytesseract.image_to_string(pil_img)
        raw_lines = [l.strip() for l in extracted_text_raw.splitlines() if l.strip()]

        if raw_lines:
            try:
                data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
                tess_scores = [
                    float(c) / 100.0
                    for c in data.get("conf", [])
                    if isinstance(c, (int, float, str)) and str(c).replace("-", "").isdigit() and float(c) > 0
                ]
                avg_conf = (sum(tess_scores) / len(tess_scores)) if tess_scores else 0.85
            except Exception:
                avg_conf = 0.85

            tess_lines = [{"text": l, "confidence": round(avg_conf, 4)} for l in raw_lines]
            return {
                "text": "\n".join(raw_lines),
                "confidence": round(avg_conf, 4),
                "lines": tess_lines,
                "line_count": len(tess_lines),
            }
    except Exception:
        pass

    return {
        "text": "",
        "confidence": 0.0,
        "lines": [],
        "line_count": 0,
    }


def _process_pdf_document(file_path: str) -> Dict[str, Any]:
    """Process a PDF file with native text extraction and image OCR fallback."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) is required for PDF processing but is not installed.")

    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Validate size & signature
    with open(file_path, "rb") as f:
        header = f.read(1024)

    if not header:
        raise ValueError(f"PDF file is empty (0 bytes): {path_obj.name}")

    if b"%PDF-" not in header:
        raise ValueError(f"Invalid PDF signature: {path_obj.name} is corrupted or not a valid PDF.")

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise ValueError(f"Corrupted or unreadable PDF file: {exc}")

    try:
        if doc.is_encrypted:
            raise ValueError(f"Encrypted or password-protected PDF files are not supported: {path_obj.name}")

        if doc.page_count == 0:
            raise ValueError(f"PDF file contains no pages: {path_obj.name}")

        all_page_texts: List[str] = []
        all_lines: List[Dict[str, Any]] = []

        for page_idx in range(doc.page_count):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Attempt embedded text extraction
            embedded_text = page.get_text("text").strip()
            has_embedded_text = bool(re.search(r"[A-Za-z0-9]", embedded_text))

            if has_embedded_text:
                page_lines_raw = [l.strip() for l in embedded_text.splitlines() if l.strip()]
                page_lines_objs = [
                    {
                        "text": l,
                        "confidence": 1.0,
                        "page": page_num,
                        "extraction_method": "embedded_text",
                    }
                    for l in page_lines_raw
                ]
                all_lines.extend(page_lines_objs)
                all_page_texts.append("\n".join(page_lines_raw))
            else:
                # 2. Render page to image and run OCR
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_bytes))

                ocr_res = _ocr_single_image(pil_img)
                if ocr_res["lines"]:
                    for l in ocr_res["lines"]:
                        all_lines.append({
                            "text": l["text"],
                            "confidence": l["confidence"],
                            "page": page_num,
                            "extraction_method": "ocr",
                        })
                    all_page_texts.append(ocr_res["text"])

        combined_text = "\n\n".join(all_page_texts).strip()

        if not all_lines:
            raise ValueError(f"OCR extraction failed: No text could be detected in PDF document {path_obj.name}.")

        conf_sum = sum(l["confidence"] for l in all_lines)
        avg_confidence = conf_sum / len(all_lines) if all_lines else 0.0

        return {
            "text": combined_text,
            "confidence": round(avg_confidence, 4),
            "lines": all_lines,
            "line_count": len(all_lines),
            "page_count": doc.page_count,
        }
    finally:
        doc.close()


def run_ocr(image_path: str) -> Dict[str, Any]:
    """
    Main OCR and document reading entrypoint.
    Supports both standard images (PNG, JPG, JPEG) and PDF documents.
    """
    path_obj = Path(image_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Document file does not exist: {image_path}")

    # Check if PDF
    if path_obj.suffix.lower() == ".pdf":
        return _process_pdf_document(image_path)

    # Process standard image file
    ocr_result = _ocr_single_image(image_path)

    if not ocr_result.get("lines"):
        # TASK 2: Do NOT return misleading mock fallback text
        raise ValueError(f"OCR extraction failed: No text could be extracted from image {path_obj.name}.")

    return ocr_result


def main():
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    input_path = os.path.join(
        backend_dir,
        "test_images",
        "sample_bill.jpg"
    )

    print("\nStarting OCR processing...")
    try:
        result = run_ocr(input_path)
        print("\nOCR completed successfully.")
        print("\nExtracted Text:")
        print("--------------------------------")
        print(result["text"])
        print("--------------------------------")
        print(f"Confidence: {result['confidence'] * 100:.2f}%")
        print(f"Detected Lines: {result['line_count']}")
    except Exception as e:
        print(f"OCR failed: {e}")


if __name__ == "__main__":
    main()