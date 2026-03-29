import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr: PaddleOCR | None = None

def get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr

def recognize_plate(image_bytes: bytes) -> tuple[str, float]:
    """Returns (plate_number, confidence_score). Returns ('', 0.0) if nothing detected."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "", 0.0

    ocr = get_ocr()
    result = ocr.ocr(img, cls=True)
    if not result or not result[0]:
        return "", 0.0

    best_text = ""
    best_score = 0.0
    for line in result[0]:
        text, score = line[1]
        if score > best_score:
            best_text = text
            best_score = score

    return best_text.replace(" ", ""), best_score
