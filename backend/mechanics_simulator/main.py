import os
import sys
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from shared.models import MechanicsSimRequest, MechanicsOptimizeRequest
from shared.redis_client import publish
from shared.config_loader import get_mechanics_config
from mechanics import WaterWheelSimulator, SimulationInput, WaterWheelGeometry, MaterialProperties, ChainFailureMode

def build_geometry_from_config(overrides: Dict = None) -> WaterWheelGeometry:
    config = get_mechanics_config().get("geometry", {})
    if overrides:
        config.update(overrides)
    return WaterWheelGeometry(**{k: v for k, v in config.items() if hasattr(WaterWheelGeometry, k)})

def build_material_from_config(overrides: Dict = None) -> MaterialProperties:
    config = get_mechanics_config().get("material", {})
    if overrides:
        config.update(overrides)
    return MaterialProperties(**{k: v for k, v in config.items() if hasattr(MaterialProperties, k)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Mechanics Simulator 启动完成 (port 8002)")
    yield


app = FastAPI(title="Mechanics Simulator - 链传动和力矩计算", version="2.0.0", lifespan=lifespan)

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
        "service": "mechanics_simulator",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/mechanics/simulate")
async def run_mechanics_simulation(req: MechanicsSimRequest):
    geom = build_geometry_from_config(req.geometry)
    mat = build_material_from_config(req.material)

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
        lubrication_factor=max(0.1, min(2.0, req.lubrication_factor)),
    )

    result = simulator.simulate(sim_input)
    water_level_corrections = simulator.scrape_model.get_water_level_corrections(req.water_level_diff)

    response = {
        "input": {
            "rotational_speed": req.rotational_speed,
            "water_level_diff": req.water_level_diff,
            "water_lift": water_lift,
            "chain_wear_factor": req.chain_wear_factor,
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
        },
        "resistance_breakdown": {
            "scrape_resistance_N": result.scrape_resistance,
            "chain_weight_resistance_N": result.chain_weight_resistance,
            "bending_resistance_N": result.bending_resistance,
            "friction_resistance_N": result.friction_resistance,
            "water_acceleration_resistance_N": result.water_acceleration_resistance,
            "polygonal_effect_equivalent_force_N": result.polygonal_effect_loss / max(geom.upper_wheel_diameter / 2, 0.001),
        },
        "water_level_corrections": water_level_corrections,
        "chain_failure_risk": result.chain_failure_risk.value,
        "chain_fatigue_life_hours": result.chain_fatigue_life_hours,
        "geometry": {
            "chain_length_m": round(geom.chain_length, 3),
            "links_per_chain": geom.links_per_chain,
            "blade_submersion_ratio": round(geom.blade_submersion_ratio, 3),
        },
    }

    try:
        publish("mechanics_result", json.dumps(response, ensure_ascii=False, default=str))
    except Exception:
        pass

    return response


@app.post("/api/mechanics/optimize")
async def run_mechanics_optimization(req: MechanicsOptimizeRequest):
    geom = build_geometry_from_config()
    mat = build_material_from_config()
    simulator = WaterWheelSimulator(geom, mat)

    speeds = [req.min_speed + i * (req.max_speed - req.min_speed) / 14 for i in range(15)]
    results = []

    for speed in speeds:
        water_lift = simulator._estimate_water_lift(speed, req.water_level_diff)
        sim_input = SimulationInput(
            rotational_speed=speed,
            water_level_diff=req.water_level_diff,
            water_lift=water_lift,
        )
        result = simulator.simulate(sim_input)
        results.append({
            "speed_rpm": round(speed, 2),
            "drive_torque_Nm": result.drive_torque,
            "overall_efficiency": result.overall_efficiency,
            "water_lift_lpm": round(water_lift, 1),
            "input_power_W": result.input_power,
        })

    best = max(results, key=lambda x: x["overall_efficiency"])
    return {"optimal": best, "sweep": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
