import os
import sys
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shared.models import IrrigationAnalysisRequest
from shared.redis_client import publish
from shared.config_loader import get_irrigation_config
from shared.database import get_influxdb_manager, IrrigationAnalysisRecord
from irrigation import (
    IrrigationEfficiencyAnalyzer,
    IrrigationAnalysisInput,
    CropType,
    SoilType,
    CropParameters,
    SoilParameters,
    IrrigationSystemConfig,
)


def build_analysis_input(req: IrrigationAnalysisRequest) -> IrrigationAnalysisInput:
    config = get_irrigation_config()

    crop_type = CropType(req.crop_type)
    soil_type = SoilType(req.soil_type)

    crop_config = config.get("crops", {}).get(req.crop_type, {})
    soil_config = config.get("soils", {}).get(req.soil_type, {})
    system_config_data = config.get("system", {})

    crop_params = CropParameters.for_crop(crop_type)
    for k, v in crop_config.items():
        if hasattr(crop_params, k):
            setattr(crop_params, k, v)

    soil_params = SoilParameters.for_soil(soil_type)
    for k, v in soil_config.items():
        if hasattr(soil_params, k):
            setattr(soil_params, k, v)

    sys_cfg = IrrigationSystemConfig()
    if req.system_config:
        for k, v in req.system_config.items():
            if hasattr(sys_cfg, k):
                setattr(sys_cfg, k, v)
    else:
        for k, v in system_config_data.items():
            if hasattr(sys_cfg, k):
                setattr(sys_cfg, k, v)

    return IrrigationAnalysisInput(
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
        system_config=sys_cfg,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Irrigation Analyzer 启动完成 (port 8003)")
    yield


app = FastAPI(title="Irrigation Analyzer - 提水效率和灌溉面积评估", version="2.0.0", lifespan=lifespan)

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
        "service": "irrigation_analyzer",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/irrigation/analyze")
async def run_irrigation_analysis(req: IrrigationAnalysisRequest):
    analysis_input = build_analysis_input(req)
    analyzer = IrrigationEfficiencyAnalyzer()
    result = analyzer.analyze(analysis_input)

    db = get_influxdb_manager()
    db.write_irrigation_analysis(IrrigationAnalysisRecord(
        wheel_id=req.wheel_id,
        optimal_speed=result.optimal_speed,
        irrigation_area=result.area_irrigated_m2,
        water_used=result.total_water_delivered_m3,
        area_efficiency=result.area_efficiency_m2_per_m3,
        analysis_json=json.dumps({
            "irrigation_efficiency": result.irrigation_efficiency,
            "conveyance_efficiency": result.conveyance_efficiency,
            "field_efficiency": result.field_efficiency,
        }),
    ))

    response = {
        "water_balance": {
            "delivered_m3": round(result.total_water_delivered_m3, 2),
            "available_field_m3": round(result.total_water_available_field_m3, 2),
            "crop_requirement_m3": round(result.crop_water_requirement_m3, 2),
            "effective_water_mm": round(result.effective_irrigation_depth_mm, 2),
        },
        "losses": {
            "runoff_m3": round(result.runoff_loss_m3, 2),
            "deep_percolation_m3": round(result.deep_percolation_loss_m3, 2),
            "water_deficit_m3": round(result.water_deficit_m3, 2),
            "water_surplus_m3": round(result.water_surplus_m3, 2),
        },
        "efficiencies": {
            "overall": round(result.irrigation_efficiency, 4),
            "conveyance": round(result.conveyance_efficiency, 4),
            "field_application": round(result.field_efficiency, 4),
            "area_efficiency_m2_per_m3": round(result.area_efficiency_m2_per_m3, 4),
            "water_productivity_kg_per_m3": round(result.water_productivity_kg_per_m3, 4),
        },
        "area_coverage": {
            "irrigated_m2": round(result.area_irrigated_m2, 1),
            "unirrigated_m2": round(result.area_unirrigated_m2, 1),
        },
        "optimal_operation": {
            "optimal_speed_rpm": round(result.optimal_speed, 1),
            "speed_analysis": result.speed_sweep_data,
        },
        "recommendation": result.recommendation,
        "cost_estimate": result.cost_estimate,
    }

    try:
        publish("irrigation_result", json.dumps(response, ensure_ascii=False, default=str))
    except Exception:
        pass

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
