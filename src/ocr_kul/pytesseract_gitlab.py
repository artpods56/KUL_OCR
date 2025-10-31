import pytesseract
from PIL import Image
import json
import os
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe" #path to a tesseract

def foldel_work(folder_path :str)->dict:
    results={}
    for filename in os.listdir(folder_path):
        results=OCR(filename,folder_path,results)
    return results
    

def OCR(filename:str,folder_path:str,results:dict)->dict:
    if filename.lower().endswith((".png",".jpg",".jpeg")): #here you can write more extensions of a graphic file
            image_path=os.path.join(folder_path,filename)

            text=pytesseract.image_to_string(Image.open(image_path))
            txt_filename=os.path.splitext(filename)[0]+".txt"
            txt_path=os.path.join(folder_path,txt_filename)
            with open(txt_path,"w",encoding="utf-8") as text_file:
                text_file.write(text)

            results[filename]={
                "file_path":image_path,
                "extracted_text":text
            }
    return results

def to_json(results:dict,json_filename : str,folder_path:str):
    with open(os.path.join(folder_path,json_filename),"w",encoding="utf-8") as json_file:
        json.dump(results,json_file,ensure_ascii=False, indent=4)

def main():
    folder_path=r"C:\\Users\\Jan\Desktop\\Wisual\\praktyki" #path to a folder with every image you want to work with
    json_filename="ocr_results.json"
    results=foldel_work(folder_path,)
    to_json(results,json_filename,folder_path)
    

if __name__=="__main__":
    main()