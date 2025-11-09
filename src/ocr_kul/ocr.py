import pytesseract
import numpy as np
from ocr_kul.preprocessing import preprocess_for_ocr

# OCR - exporting text from image
def extract_txt(image: np.ndarray) -> str:
    # preprocessing image
    ocr_ready_img = preprocess_for_ocr(image)

    custom_config = r'--oem 3 --psm 6 -l eng'

    text = pytesseract.image_to_string(ocr_ready_img, config=custom_config)

    print(text)

    return text