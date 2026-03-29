import pytest
import numpy as np
import cv2
from recognizer import recognize_plate

def make_blank_image() -> bytes:
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def test_blank_image_returns_empty():
    plate, score = recognize_plate(make_blank_image())
    assert plate == ""
    assert score == 0.0

def test_invalid_bytes_returns_empty():
    plate, score = recognize_plate(b"not an image")
    assert plate == ""
    assert score == 0.0
