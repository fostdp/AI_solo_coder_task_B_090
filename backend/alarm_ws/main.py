import os
import sys
import json
import asyncio
import threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shared.models import AlertAcknowledgeRequest, ThresholdsUpdateRequest
from shared.database import get_influxdb_manager
from alerts import (
    get_alert_manager,
    AlertThresholds,
    AlertLevel,
    AlertType,
)


def start_redis_subscriber():
    try:
        from shared.redis_client import get_pubsub, REDIS_CHANNELS
        pubsub = get_pubsub()
        channel = REDIS_CHANNELS["sensor_data"]
        pubsub.subscribe(channel)

        alert_mgr = get_alert_manager()

        def listen():
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        asyncio.run(alert_mgr.process_sensor_data(data))
                    except Exception:
                        pass

        t = threading.Thread(target=listen, daemon=True)
        t.start()
    except Exception as e:
        print(f"Redis 订阅启动失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_redis_subscriber()
    print("✅ Alarm & WebSocket 启动完成 (port 8004)")
    yield


app = FastAPI(title="Alarm & WebSocket - 告警评估和推送", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "service": "alarm_ws",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/alerts")
async def get_alerts(
    wheel_id: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    alert_mgr = get_alert_manager()
    db = get_influxdb_manager()

    db_alerts = db.query_alerts(
        wheel_id=wheel_id,
        alert_level=level,
        limit=limit,
    )

    active = alert_mgr.get_active_alerts(wheel_id)

    return {
        "active_alerts": [a.to_dict() for a in active],
        "history_from_db": db_alerts,
        "total_active": len(active),
    }


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, req: AlertAcknowledgeRequest):
    alert_mgr = get_alert_manager()
    success = alert_mgr.acknowledge_alert(alert_id, req.wheel_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"success": True, "alert_id": alert_id}


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, req: AlertAcknowledgeRequest):
    alert_mgr = get_alert_manager()
    success = alert_mgr.resolve_alert(alert_id, req.wheel_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"success": True, "alert_id": alert_id}


@app.get("/api/alerts/thresholds")
async def get_thresholds():
    alert_mgr = get_alert_manager()
    return alert_mgr.thresholds.__dict__


@app.put("/api/alerts/thresholds")
async def update_thresholds(req: ThresholdsUpdateRequest):
    alert_mgr = get_alert_manager()
    current = alert_mgr.thresholds
    for k, v in req.model_dump(exclude_none=True).items():
        if hasattr(current, k) and v is not None:
            setattr(current, k, v)
    return {"success": True, "thresholds": current.__dict__}


@app.get("/api/wheels/{wheel_id}/state")
async def get_wheel_state(wheel_id: str):
    alert_mgr = get_alert_manager()
    return alert_mgr.get_wheel_state(wheel_id)


@app.websocket("/ws/sensor/{wheel_id}")
async def websocket_sensor(websocket: WebSocket, wheel_id: str):
    alert_mgr = get_alert_manager()
    ws_mgr = alert_mgr.ws_manager

    await ws_mgr.connect(websocket, wheel_id)
    try:
        await websocket.send_json({
            "type": "connection_established",
            "wheel_id": wheel_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_mgr.disconnect(websocket, wheel_id)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    alert_mgr = get_alert_manager()
    ws_mgr = alert_mgr.ws_manager

    await ws_mgr.connect(websocket)
    try:
        active = alert_mgr.get_active_alerts()
        await websocket.send_json({
            "type": "connection_established",
            "active_alerts": [a.to_dict() for a in active],
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_mgr.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
