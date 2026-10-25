# --- 2. OCR (Szöveg kinyerése) ---

import pytesseract
from .. import config


def extract_text_from_image(image):
    """
    Tesseract OCR segítségével kinyeri a képen található összes szöveget
    (alapból angol és magyar nyelv támogatásával, lásd config.OCR_NYELVEK).
    """
    return pytesseract.image_to_string(image, lang=config.OCR_NYELVEK)
