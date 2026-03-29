import os
from fastapi import FastAPI, UploadFile, File, Form
import httpx
from recognizer import recognize_plate

app = FastAPI(title="AI Recognition Service")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    factory_id: str = Form(...),
    gate_id: str = Form(None),
    direction: str = Form(...),
):
    image_bytes = await file.read()
    plate, confidence = recognize_plate(image_bytes)

    if not plate:
        return {"plate_number": None, "confidence": 0.0, "event_id": None}

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/gate-events", json={
            "factory_id": factory_id,
            "gate_id": gate_id,
            "plate_number": plate,
            "direction": direction,
            "image_url": None,
            "confidence_score": confidence,
        })
        event_id = resp.json().get("id") if resp.status_code == 200 else None

    return {"plate_number": plate, "confidence": confidence, "event_id": event_id}
