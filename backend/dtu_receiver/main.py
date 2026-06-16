import os
import sys
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shared.database import get_influxdb_manager, SensorRecord
from shared.redis_client import publish
from shared.models import SensorDataRequest, SensorDataBatchRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_influxdb_manager()
    print("✅ DTU Receiver 启动完成 (port 8001)")
    yield
    db.close()


app = FastAPI(title="DTU Receiver - 传感器数据采集", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    db = get_influxdb_manager()
    return {
        "service": "dtu_receiver",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "influxdb_connected": db.is_connected(),
    }


@app.post("/api/sensor/data")
async def receive_sensor_data(data: SensorDataRequest):
    db = get_influxdb_manager()

    if not data.timestamp:
        data.timestamp = datetime.now(timezone.utc).isoformat()

    record = SensorRecord(
        wheel_id=data.wheel_id,
        location=data.location,
        timestamp=data.timestamp,
        rotational_speed=data.rotational_speed,
        torque=data.torque,
        water_lift=data.water_lift,
        water_level_diff=data.water_level_diff,
        chain_tension=data.chain_tension,
        scrape_resistance=data.scrape_resistance,
        drive_torque=data.drive_torque,
        efficiency=data.efficiency,
        anomaly=data.anomaly,
    )

    write_ok = db.write_sensor_record(record)

    data_dict = data.model_dump()
    try:
        publish("sensor_data", json.dumps(data_dict, ensure_ascii=False, default=str))
    except Exception:
        pass

    return {
        "success": write_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "published": True,
    }


@app.post("/api/sensor/batch")
async def receive_sensor_batch(batch: SensorDataBatchRequest):
    db = get_influxdb_manager()
    records = []
    all_dicts = []

    for data in batch.records:
        if not data.timestamp:
            data.timestamp = datetime.now(timezone.utc).isoformat()

        record = SensorRecord(
            wheel_id=data.wheel_id,
            location=data.location,
            timestamp=data.timestamp,
            rotational_speed=data.rotational_speed,
            torque=data.torque,
            water_lift=data.water_lift,
            water_level_diff=data.water_level_diff,
            chain_tension=data.chain_tension,
            scrape_resistance=data.scrape_resistance,
            drive_torque=data.drive_torque,
            efficiency=data.efficiency,
            anomaly=data.anomaly,
        )
        records.append(record)
        all_dicts.append(data.model_dump())

    write_ok = db.write_sensor_batch(records)

    for d in all_dicts:
        try:
            publish("sensor_data", json.dumps(d, ensure_ascii=False, default=str))
        except Exception:
            pass

    return {
        "success": write_ok,
        "count": len(records),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/sensor/data")
async def query_sensor_data(
    wheel_id: str = Query("han_dynasty_wheel_001"),
    start_time: str = Query("-24h"),
    limit: int = Query(100, ge=1, le=1000),
    aggregate: str = Query(""),
    aggregate_window: str = Query("10m"),
):
    db = get_influxdb_manager()
    data = db.query_sensor_data(
        wheel_id=wheel_id,
        start_time=start_time,
        limit=limit,
        aggregate=aggregate or None,
        aggregate_window=aggregate_window,
    )
    return {"count": len(data), "data": data}


@app.get("/api/sensor/wheels")
async def list_wheels():
    db = get_influxdb_manager()
    return {"wheels": db.list_wheel_ids()}


@app.get("/api/sensor/statistics")
async def get_wheel_statistics(
    wheel_id: str,
    hours: int = Query(24, ge=1, le=720),
):
    db = get_influxdb_manager()
    return db.query_statistics(wheel_id, hours)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
