import streamlit as st
from PIL import Image
import numpy as np
from ocr_kul.ocr import extract_txt

def main():
    st.set_page_config(page_title="OCR - TASK 5", layout="centered")
    st.title("OCR - TASK 5 - MKR")

    uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        image_np = np.array(image)
        st.image(image, caption="Uploaded image", use_container_width=True)

        if st.button("Image to text"):
            text = extract_txt(image_np)
            st.write("OCR result: ")
            st.write(text)

            # Save text
            with open("resultTXT.txt", "w", encoding="utf-8") as f:
                f.write(text)

            # Prepare JSON
            lines = [line for line in text.split("\n") if line.strip()]
            json_data = {"raw_text": text, "lines": lines}
            with open("resultJSON.json", "w", encoding="utf-8") as f:
                import json
                json.dump(json_data, f, ensure_ascii=False, indent=4)

            # Download buttons
            st.download_button("Download TXT", data=text, file_name="resultTXT.txt", mime="text/plain")
            st.download_button(
                "Download JSON",
                data=json.dumps(json_data, ensure_ascii=False, indent=4),
                file_name="resultJSON.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
