import cv2
import numpy as np

# preprocessing picture for better results -------
def preprocess_for_ocr(image_cv: np.ndarray) -> np.ndarray:
    if image_cv.shape[2] == 4:
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

    blurred = cv2.medianBlur(gray, 3)
    tresh = cv2.adaptiveThreshold(blurred, 255,
                                  cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 11, 2)
    return tresh