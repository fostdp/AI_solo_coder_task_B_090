"""
古代龙骨水车力学仿真与灌溉效率分析系统 - FastAPI 后端主程序

功能:
1. 传感器数据接收与存储 (REST API)
2. 力学仿真模型调用 (REST API)
3. 灌溉效率分析 (REST API)
4. 实时数据推送 (WebSocket)
5. 告警检测与推送 (WebSocket)
6. 历史数据查询 (REST API)
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    get_influxdb_manager,
    SensorRecord,
    IrrigationAnalysisRecord
)
from alerts import (
    get_alert_manager,
    Alert,
    AlertThresholds,
    AlertLevel,
    AlertType
)
from mechanics import (
    WaterWheelSimulator,
    SimulationInput,
    WaterWheelGeometry,
    MaterialProperties,
    ChainFailureMode
)
from irrigation import (
    IrrigationEfficiencyAnalyzer,
    IrrigationAnalysisInput,
    CropType,
    SoilType,
    CropParameters,
    SoilParameters,
    IrrigationSystemConfig
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_influxdb_manager()
    alert_mgr = get_alert_manager()
    print("✅ 后端系统启动完成")
    print(f"  - InfluxDB: {'已连接' if db.is_connected() else '未连接'}")
    print(f"  - 告警系统: 已就绪")
    yield
    db.close()
    print("🔌 后端系统已关闭")


app = FastAPI(
    title="古代龙骨水车力学仿真与灌溉效率分析系统",
    description="汉代龙骨水车复原研究数据平台 - 力学仿真、灌溉分析、实时监控",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class SensorDataRequest(BaseModel):
    wheel_id: str = Field(..., description="水车ID")
    location: str = Field("", description="水车位置")
    timestamp: str = Field("", description="ISO时间戳")
    rotational_speed: float = Field(..., description="转速 rpm")
    torque: float = Field(..., description="扭矩 N·m")
    water_lift: float = Field(..., description="提水量 L/min")
    water_level_diff: float = Field(..., description="水位差 m")
    chain_tension: float = Field(0.0, description="链张力 N")
    scrape_resistance: float = Field(0.0, description="刮水阻力 N")
    drive_torque: float = Field(0.0, description="驱动力矩 N·m")
    efficiency: float = Field(0.0, description="效率")
    anomaly: Optional[str] = Field(None, description="异常信息")


class SensorDataBatchRequest(BaseModel):
    records: List[SensorDataRequest]


class MechanicsSimRequest(BaseModel):
    rotational_speed: float = Field(..., description="转速 rpm")
    water_level_diff: float = Field(..., description="水位差 m")
    water_lift: Optional[float] = Field(None, description="提水量 L/min (可选，自动估算)")
    chain_wear_factor: float = Field(0.0, description="链条磨损系数 0~1")
    lubrication_factor: float = Field(1.0, description="润滑系数")
    geometry: Optional[Dict] = Field(None, description="自定义几何参数")
    material: Optional[Dict] = Field(None, description="自定义材料参数")


class MechanicsOptimizeRequest(BaseModel):
    water_level_diff: float = Field(..., description="水位差 m")
    target_area: float = Field(2000.0, description="目标灌溉面积 m²")
    min_speed: float = Field(5.0, description="最小转速 rpm")
    max_speed: float = Field(30.0, description="最大转速 rpm")


class IrrigationAnalysisRequest(BaseModel):
    wheel_id: str = Field(..., description="水车ID")
    water_lift_lpm: float = Field(..., description="提水量 L/min")
    rotational_speed: float = Field(..., description="转速 rpm")
    overall_efficiency: float = Field(..., description="综合效率")
    water_level_diff: float = Field(..., description="水位差 m")
    irrigation_area_m2: float = Field(2000.0, description="灌溉面积 m²")
    hours_operation: float = Field(8.0, description="每日运行小时")
    crop_type: str = Field("general", description="作物类型: rice/wheat/corn/vegetable/general")
    soil_type: str = Field("loam", description="土壤类型: sand/loam/clay/silt")
    weather_et0_mm_day: float = Field(5.0, description="参考蒸散 mm/天")
    initial_soil_moisture_deficit: float = Field(0.3, description="初始土壤含水率亏缺")
    system_config: Optional[Dict] = Field(None, description="灌溉系统配置")


class AlertAcknowledgeRequest(BaseModel):
    alert_id: str = Field(..., description="告警ID")
    wheel_id: Optional[str] = Field(None, description="水车ID")


class ThresholdsUpdateRequest(BaseModel):
    max_chain_tension: Optional[float] = None
    min_efficiency: Optional[float] = None
    min_water_lift: Optional[float] = None
    max_torque: Optional[float] = None
    min_rotational_speed: Optional[float] = None
    max_rotational_speed: Optional[float] = None
    chain_wear_warning: Optional[float] = None
    chain_wear_critical: Optional[float] = None


@app.get("/")
async def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": "古代龙骨水车力学仿真与灌溉效率分析系统",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sensor_api": "/api/sensor/*",
            "mechanics_api": "/api/mechanics/*",
            "irrigation_api": "/api/irrigation/*",
            "alerts_api": "/api/alerts/*",
            "websocket_sensor": "/ws/sensor/{wheel_id}",
            "websocket_alerts": "/ws/alerts"
        }
    }


@app.get("/api/health")
async def health_check():
    db = get_influxdb_manager()
    alert_mgr = get_alert_manager()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "influxdb_connected": db.is_connected(),
        "active_wheels": list(alert_mgr._wheel_states.keys()),
        "total_alerts_triggered": len(alert_mgr._alert_history)
    }


@app.post("/api/sensor/data")
async def receive_sensor_data(data: SensorDataRequest):
    db = get_influxdb_manager()
    alert_mgr = get_alert_manager()

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
        anomaly=data.anomaly
    )

    write_ok = db.write_sensor_record(record)
    data_dict = data.model_dump()
    alerts = await alert_mgr.process_sensor_data(data_dict)

    try:
        await alert_mgr.ws_manager.broadcast_data(data.wheel_id, data_dict)
    except Exception:
        pass

    return {
        "success": write_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alerts_triggered": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@app.post("/api/sensor/batch")
async def receive_sensor_batch(batch: SensorDataBatchRequest):
    db = get_influxdb_manager()
    alert_mgr = get_alert_manager()

    records = []
    all_alerts = []

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
            anomaly=data.anomaly
        )
        records.append(record)

        alerts = await alert_mgr.process_sensor_data(data.model_dump())
        all_alerts.extend(alerts)

        try:
            await alert_mgr.ws_manager.broadcast_data(data.wheel_id, data.model_dump())
        except Exception:
            pass

    write_ok = db.write_sensor_batch(records)

    return {
        "success": write_ok,
        "records_processed": len(records),
        "alerts_triggered": len(all_alerts),
        "alerts": [a.to_dict() for a in all_alerts]
    }


@app.get("/api/sensor/data")
async def query_sensor_data(
    wheel_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(100, ge=1, le=10000),
    aggregate: Optional[str] = Query(None, pattern="^(mean|max|min|sum|count)$"),
    aggregate_window: str = "1m"
):
    db = get_influxdb_manager()
    data = db.query_sensor_data(
        wheel_id=wheel_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        aggregate=aggregate,
        aggregate_window=aggregate_window
    )
    return {"count": len(data), "data": data}


@app.get("/api/sensor/wheels")
async def list_wheels():
    db = get_influxdb_manager()
    wheel_ids = db.list_wheel_ids()
    return {"wheels": wheel_ids}


@app.get("/api/sensor/statistics")
async def get_wheel_statistics(
    wheel_id: str,
    hours: int = Query(24, ge=1, le=720)
):
    db = get_influxdb_manager()
    stats = db.query_statistics(wheel_id, hours)
    return stats


@app.post("/api/mechanics/simulate")
async def run_mechanics_simulation(req: MechanicsSimRequest):
    geom = WaterWheelGeometry()
    if req.geometry:
        for k, v in req.geometry.items():
            if hasattr(geom, k):
                setattr(geom, k, v)

    mat = MaterialProperties()
    if req.material:
        for k, v in req.material.items():
            if hasattr(mat, k):
                setattr(mat, k, v)

    simulator = WaterWheelSimulator(geom, mat)

    if req.water_lift is None:
        water_lift = simulator._estimate_water_lift(req.rotational_speed, req.water_level_diff)
    else:
        water_lift = req.water_lift

    sim_input = SimulationInput(
        rotational_speed=req.rotational_speed,
        water_level_diff=req.water_level_diff,
        water_lift=water_lift,
        chain_wear_factor=max(0.0, min(1.0, req.chain_wear_factor)),
        lubrication_factor=max(0.1, min(2.0, req.lubrication_factor))
    )

    result = simulator.simulate(sim_input)
    water_level_corrections = simulator.scrape_model.get_water_level_corrections(req.water_level_diff)

    return {
        "input": {
            "rotational_speed": req.rotational_speed,
            "water_level_diff": req.water_level_diff,
            "water_lift": water_lift,
            "chain_wear_factor": req.chain_wear_factor
        },
        "drive_torque_Nm": result.drive_torque,
        "output_torque_Nm": result.output_torque,
        "input_power_W": result.input_power,
        "output_power_W": result.output_power,
        "mechanical_efficiency": result.mechanical_efficiency,
        "hydraulic_efficiency": result.hydraulic_efficiency,
        "overall_efficiency": result.overall_efficiency,
        "chain_tension_max_N": result.chain_tension_max,
        "chain_tension_min_N": result.chain_tension_min,
        "polygonal_effect": {
            "speed_velocity_factor_kv": result.speed_velocity_factor,
            "dynamic_load_coefficient": result.chain_impact_coefficient,
            "loss_torque_Nm": result.polygonal_effect_loss,
            "sprocket_teeth_upper": geom.num_sprockets_upper,
            "description": "链传动多边形效应：齿数越少，速度波动和动载荷越大"
        },
        "resistance_breakdown": {
            "scrape_resistance_N": result.scrape_resistance,
            "chain_weight_resistance_N": result.chain_weight_resistance,
            "bending_resistance_N": result.bending_resistance,
            "friction_resistance_N": result.friction_resistance,
            "water_acceleration_resistance_N": result.water_acceleration_resistance,
            "polygonal_effect_equivalent_force_N": result.polygonal_effect_loss / max(geom.upper_wheel_diameter / 2, 0.001)
        },
        "water_level_corrections": water_level_corrections,
        "chain_failure_risk": result.chain_failure_risk.value,
        "chain_fatigue_life_hours": result.chain_fatigue_life_hours,
        "geometry": {
            "chain_length_m": round(geom.chain_length, 3),
            "links_per_chain": geom.links_per_chain,
            "blade_submersion_ratio": round(geom.blade_submersion_ratio, 3)
        }
    }


@app.post("/api/mechanics/optimize")
async def run_mechanics_optimization(req: MechanicsOptimizeRequest):
    simulator = WaterWheelSimulator()
    result = simulator.optimize_speed(
        water_level_diff=req.water_level_diff,
        target_area=req.target_area,
        min_speed=req.min_speed,
        max_speed=req.max_speed
    )

    simplified_data = []
    for d in result["all_data"]:
        simplified_data.append({
            "speed": d["speed"],
            "efficiency": d["efficiency"],
            "water_lift_lpm": d["water_lift"],
            "irrigation_area_m2_hr": d["irrigation_area_per_hour"],
            "power_input_W": d["power_input"]
        })

    return {
        "input": {
            "water_level_diff": req.water_level_diff,
            "target_area_m2": req.target_area,
            "speed_range": [req.min_speed, req.max_speed]
        },
        "optimal_efficiency": {
            "speed_rpm": result["optimal_efficiency_speed"],
            "efficiency": result["optimal_efficiency"]
        },
        "maximum_area": {
            "speed_rpm": result["optimal_area_speed"],
            "area_m2_per_hour": result["max_irrigation_area"]
        },
        "balanced_point": {
            "speed_rpm": result["balanced_speed"],
            "efficiency": result["balanced_efficiency"],
            "area_m2_per_hour": result["balanced_area"]
        },
        "speed_sweep_data": simplified_data
    }


@app.post("/api/irrigation/analyze")
async def run_irrigation_analysis(req: IrrigationAnalysisRequest):
    try:
        crop_type = CropType(req.crop_type)
    except ValueError:
        crop_type = CropType.GENERAL
    try:
        soil_type = SoilType(req.soil_type)
    except ValueError:
        soil_type = SoilType.LOAM

    crop_params = CropParameters.for_crop(crop_type)
    soil_params = SoilParameters.for_soil(soil_type)
    analyzer = IrrigationEfficiencyAnalyzer(crop_params, soil_params)

    sys_config = IrrigationSystemConfig()
    if req.system_config:
        for k, v in req.system_config.items():
            if hasattr(sys_config, k):
                setattr(sys_config, k, v)

    analysis_input = IrrigationAnalysisInput(
        wheel_id=req.wheel_id,
        water_lift_lpm=req.water_lift_lpm,
        rotational_speed=req.rotational_speed,
        overall_efficiency=req.overall_efficiency,
        water_level_diff=req.water_level_diff,
        irrigation_area_m2=req.irrigation_area_m2,
        hours_operation=req.hours_operation,
        crop=crop_type,
        soil=soil_type,
        weather_et0_mm_day=req.weather_et0_mm_day,
        initial_soil_moisture_deficit=req.initial_soil_moisture_deficit,
        system_config=sys_config
    )

    result = analyzer.analyze(analysis_input)

    db = get_influxdb_manager()
    try:
        record = IrrigationAnalysisRecord(
            wheel_id=req.wheel_id,
            optimal_speed=result.optimal_speed,
            irrigation_area=result.area_irrigated_m2,
            water_used=result.total_water_delivered_m3,
            area_efficiency=result.area_efficiency_m2_per_m3,
            analysis_result=json.dumps({
                "crop": crop_type.value,
                "soil": soil_type.value,
                "recommendation": result.recommendation
            }, ensure_ascii=False)
        )
        db.write_irrigation_analysis(record)
    except Exception:
        pass

    sweep_simplified = []
    for d in result.speed_sweep_data:
        sweep_simplified.append({
            "speed_rpm": d["speed"],
            "water_lift_lpm": d["water_lift_lpm"],
            "total_water_m3": d["total_water_m3"],
            "irrigation_efficiency": d["irrigation_efficiency"],
            "area_served_m2": d["area_served_m2"],
            "runoff_loss_m3": d["runoff_loss_m3"],
            "percolation_loss_m3": d["percolation_loss_m3"],
            "power_kw": d["drive_power_kw"]
        })

    return {
        "water_balance": {
            "delivered_m3": result.total_water_delivered_m3,
            "field_available_m3": result.total_water_available_field_m3,
            "crop_requirement_m3": result.crop_water_requirement_m3,
            "effective_water_mm": result.effective_irrigation_depth_mm,
            "infiltrated_mm": result.infiltration_depth_mm,
            "deficit_m3": result.water_deficit_m3,
            "surplus_m3": result.water_surplus_m3
        },
        "losses": {
            "runoff_m3": result.runoff_loss_m3,
            "deep_percolation_m3": result.deep_percolation_loss_m3
        },
        "efficiencies": {
            "overall": result.irrigation_efficiency,
            "conveyance": result.conveyance_efficiency,
            "field_application": result.field_efficiency,
            "area_efficiency_m2_per_m3": result.area_efficiency_m2_per_m3,
            "water_productivity_kg_per_m3": result.water_productivity_kg_m3
        },
        "area_coverage": {
            "irrigated_m2": result.area_irrigated_m2,
            "unirrigated_m2": result.area_unirrigated_m2,
            "target_m2": req.irrigation_area_m2
        },
        "optimal_operation": {
            "optimal_speed_rpm": result.optimal_speed,
            "required_duration_hours": result.irrigation_duration_hours,
            "speed_analysis": sweep_simplified
        },
        "cost_estimate": result.cost_estimate,
        "recommendation": result.recommendation
    }


@app.get("/api/alerts")
async def get_alerts(
    wheel_id: Optional[str] = None,
    active_only: bool = True,
    level: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    alert_mgr = get_alert_manager()

    if active_only:
        alerts = alert_mgr.get_active_alerts(wheel_id)
    else:
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level)
            except ValueError:
                pass
        alerts = alert_mgr.get_alert_history(wheel_id, alert_level, limit)

    return {
        "count": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, req: AlertAcknowledgeRequest):
    alert_mgr = get_alert_manager()
    success = alert_mgr.acknowledge_alert(alert_id, req.wheel_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"success": True, "alert_id": alert_id}


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, req: AlertAcknowledgeRequest):
    alert_mgr = get_alert_manager()
    success = alert_mgr.resolve_alert(alert_id, req.wheel_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"success": True, "alert_id": alert_id}


@app.get("/api/alerts/thresholds")
async def get_thresholds():
    alert_mgr = get_alert_manager()
    t = alert_mgr.thresholds
    return {
        "max_chain_tension_N": t.max_chain_tension,
        "min_efficiency": t.min_efficiency,
        "min_water_lift_Lpm": t.min_water_lift,
        "max_torque_Nm": t.max_torque,
        "min_rotational_speed_rpm": t.min_rotational_speed,
        "max_rotational_speed_rpm": t.max_rotational_speed,
        "chain_wear_warning": t.chain_wear_warning,
        "chain_wear_critical": t.chain_wear_critical,
        "consecutive_anomaly_count": t.consecutive_anomaly_count,
        "efficiency_average_window": t.efficiency_average_window
    }


@app.put("/api/alerts/thresholds")
async def update_thresholds(req: ThresholdsUpdateRequest):
    alert_mgr = get_alert_manager()
    t = alert_mgr.thresholds
    for k, v in req.model_dump(exclude_unset=True).items():
        if hasattr(t, k) and v is not None:
            setattr(t, k, v)
    return {"success": True, "updated": req.model_dump(exclude_unset=True)}


@app.get("/api/wheels/{wheel_id}/state")
async def get_wheel_state(wheel_id: str):
    alert_mgr = get_alert_manager()
    return alert_mgr.get_wheel_state(wheel_id)


@app.websocket("/ws/sensor/{wheel_id}")
async def websocket_sensor(websocket: WebSocket, wheel_id: str):
    alert_mgr = get_alert_manager()
    await alert_mgr.ws_manager.connect(websocket, wheel_id)
    try:
        state = alert_mgr.get_wheel_state(wheel_id)
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "wheel_id": wheel_id,
            "state": state
        }, ensure_ascii=False))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, ensure_ascii=False))
            except Exception:
                pass
    except WebSocketDisconnect:
        alert_mgr.ws_manager.disconnect(websocket, wheel_id)
    except Exception:
        alert_mgr.ws_manager.disconnect(websocket, wheel_id)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    alert_mgr = get_alert_manager()
    await alert_mgr.ws_manager.connect(websocket, None)
    try:
        active = alert_mgr.get_active_alerts()
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "active_alerts": [a.to_dict() for a in active]
        }, ensure_ascii=False))

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_mgr.ws_manager.disconnect(websocket, None)
    except Exception:
        alert_mgr.ws_manager.disconnect(websocket, None)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"启动后端服务: http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
