import PyPDF2
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def extract_pdf_text(path):
    # لو path جاي من DB نسبي (uploads/file.pdf)
    full_path = path
    if not os.path.isabs(path):
        full_path = os.path.join(BASE_DIR, path)

    print("TRYING TO READ:", full_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(full_path)

    text = ""
    with open(full_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""

    return text
