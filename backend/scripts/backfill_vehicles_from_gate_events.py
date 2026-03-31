"""
根据历史 gate_events 补齐 vehicles 表中缺失的车辆。
用法：docker compose exec backend python scripts/backfill_vehicles_from_gate_events.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models import factory, user, vehicle, location, gate_event, alert, checkpoint, path_template, vehicle_journey  # noqa: F401
from app.services.vehicle_backfill import backfill_vehicles_from_gate_events


async def main():
    async with AsyncSessionLocal() as db:
        created = await backfill_vehicles_from_gate_events(db)
        print(f"✓ 回填完成，新增车辆 {created} 条")


if __name__ == "__main__":
    asyncio.run(main())
