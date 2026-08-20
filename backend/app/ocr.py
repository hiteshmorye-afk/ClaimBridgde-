import cv2
import numpy as np


def preprocess_image(image_path: str):
    # 1. Read image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to read image")

    # 2. Resize image
    height, width = image.shape[:2]

    max_width = 1600

    if width > max_width:
        scale = max_width / width
        new_width = int(width * scale)
        new_height = int(height * scale)

        image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

    # 3. Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 4. Remove noise
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)

    # 5. Adaptive thresholding
    threshold = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    # 6. Morphological operation
    kernel = np.ones((2, 2), np.uint8)

    processed = cv2.morphologyEx(
        threshold,
        cv2.MORPH_OPEN,
        kernel
    )

    return processed

if __name__ == "__main__":
    input_path = "test_images/sample_bill.jpg"

    output = preprocess_image(input_path)

    cv2.imwrite("test_images/preprocessed_bill.png", output)

    print("Image preprocessing completed successfully.")
    print("Output saved as preprocessed_bill.png")