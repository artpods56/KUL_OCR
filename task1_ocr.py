import os
from glob import glob
import json
import pytesseract
from PIL import Image
import cv2
from tkinter import Tk, filedialog, messagebox

# path to Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )
    return thresh

def perform_ocr(image_path):
    processed = preprocess_image(image_path)
    text = pytesseract.image_to_string(processed, lang='eng')
    return text

def load_images_from_folder(folder_path):
    image_extensions = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff")
    files = []
    for ext in image_extensions:
        files.extend(glob(os.path.join(folder_path, ext)))
    return files

def ocr_and_save(images, save_folder):
    results = {}
    for img_path in images:
        text = perform_ocr(img_path)
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        results[base_name] = text

        # Save plain text
        txt_file = os.path.join(save_folder, f"{base_name}_ocr_result.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(text)

    # save JSON
    json_file = os.path.join(save_folder, "ocr_results.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    return results


# GUI

def select_file_or_folder():
    root = Tk()
    root.withdraw()

    choice = messagebox.askyesno("Select Mode", "Do you want to select a folder of images?\nYes = Folder, No = Single File")
    
    if choice:
        path = filedialog.askdirectory(title="Select folder with images")
        if not path:
            return []
        images = load_images_from_folder(path)
        if not images:
            messagebox.showerror("No Images", "No supported images found in folder.")
        return images
    else:
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if not path:
            return []
        return [path]

def select_save_folder():
    root = Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Select folder to save OCR results")
    return folder


if __name__ == "__main__":
    images = select_file_or_folder()
    if not images:
        exit()

    save_folder = select_save_folder()
    if not save_folder:
        messagebox.showerror("No Folder", "No save folder selected. Exiting.")
        exit()

    results = ocr_and_save(images, save_folder)
    messagebox.showinfo("OCR Completed", f"OCR finished for {len(images)} image(s).\nResults saved in {save_folder}.")
