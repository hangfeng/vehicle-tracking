from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import all models to ensure SQLAlchemy registers them before use
from app.models import factory, user, vehicle, location, gate_event, alert, checkpoint, path_template, vehicle_journey  # noqa: F401
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users, checkpoints

app = FastAPI(title="Vehicle Tracking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(gate_events.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(checkpoints.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
