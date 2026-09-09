import os

os.environ["FLAGS_enable_pir_api"] = "0"

import cv2
import numpy as np
from paddleocr import PaddleOCR


def preprocess_image(image_path: str):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to read image")

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


def run_ocr(image_path: str):
    ocr = PaddleOCR(lang="en", enable_mkldnn=False)
    results = ocr.predict(image_path)

    lines = []
    all_scores = []

    for result in results:
        texts = result.get("rec_texts", [])
        scores = result.get("rec_scores", [])

        for text, score in zip(texts, scores):
            text = text.strip()
            if not text:
                continue

            score = float(score)
            lines.append({
                "text": text,
                "confidence": round(score, 4),
            })
            all_scores.append(score)

    average_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0
    full_text = "\n".join(line["text"] for line in lines)

    return {
        "text": full_text,
        "confidence": round(average_confidence, 4),
        "lines": lines,
        "line_count": len(lines),
    }


def main():
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    input_path = os.path.join(
        backend_dir,
        "test_images",
        "sample_bill.jpg"
    )

    print("\nStarting PaddleOCR on ORIGINAL image...")

    result = run_ocr(input_path)

    print("\nOCR completed successfully.")
    print("\nExtracted Text:")
    print("--------------------------------")

    print(result["text"])

    print("--------------------------------")
    print(f"OCR Confidence: {result['confidence'] * 100:.2f}%")
    print(f"Detected Lines: {result['line_count']}")


if __name__ == "__main__":
    main()