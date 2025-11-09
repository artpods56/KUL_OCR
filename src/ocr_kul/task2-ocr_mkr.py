from PIL import Image
import numpy as np
import streamlit as st
import cv2
import pytesseract
import json
# path to execute pytesseract operations on my local computer
# pytesseract.pytesseract.tesseract_cmd = r'E:\programy\poboczne\tesseract\tesseract.exe'



# preprocessing picture for better results -------
def preprocess_for_ocr(image_cv):
    if image_cv.shape[2] == 4:
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 3)
    tresh = cv2.adaptiveThreshold(blurred, 255,
                                  cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 11, 2)
    return tresh



# OCR - exporting text from image
def extract_txt(image):
    # preprocessing image
    ocr_ready_img = preprocess_for_ocr(image)

    custom_config = r'--oem 3 --psm 6 -l eng'

    text = pytesseract.image_to_string(ocr_ready_img, config=custom_config)

    print(text)

    return text



# Steamlit main page - for easy usage
st.set_page_config(page_title="OCR - TASK 2", layout="centered")
st.title("OCR - TASK 2 - MKR")

uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])

# uploading file
if uploaded_file:
    image = Image.open(uploaded_file)
    image_np = np.array(image)

    st.image(image, caption="Uploaded image", use_container_width=True)

    if st.button("Image to text"):
        text = extract_txt(image_np)
        st.write("OCR result: ")
        st.write(text)

        with open("resultTXT.txt", "w", encoding="utf-8") as resultOCRtxt:
            resultOCRtxt.write(text)
    
        # download txt
        st.download_button(label="Download TXT", data=text, file_name="resultTXT.txt", mime="text/plain")



        # line split
        lines = text.split("\n")
        json_data = {
            "raw_text": text,
            "lines": [line for line in lines if line.strip() != ""]
        }

        with open("resultJSON.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        # download json
        st.download_button( label="Download JSON", data=json.dumps(json_data, ensure_ascii=False, indent=4), file_name="resultJSON.json", mime="application/json")