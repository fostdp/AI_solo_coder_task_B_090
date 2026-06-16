"""
灌溉效率分析模块
基于提水量和灌溉面积，评估不同转速下的最优工况

包含模型:
1. 作物需水量模型 (Crop Water Requirement)
2. 土壤入渗模型 (Soil Infiltration)
3. 灌溉均匀度模型 (Irrigation Uniformity)
4. 综合灌溉效率分析 (Comprehensive Irrigation Efficiency)
5. 工况优化引擎 (Operating Condition Optimization)
"""
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class CropType(Enum):
    RICE = "rice"
    WHEAT = "wheat"
    CORN = "corn"
    VEGETABLE = "vegetable"
    GENERAL = "general"


class SoilType(Enum):
    SAND = "sand"
    LOAM = "loam"
    CLAY = "clay"
    SILT = "silt"


@dataclass
class CropParameters:
    """作物需水量参数 (基于FAO Penman-Monteith简化模型)"""
    crop_type: CropType = CropType.GENERAL
    kc_initial: float = 0.3
    kc_mid: float = 1.15
    kc_end: float = 0.6
    root_depth_m: float = 0.8
    depletion_factor: float = 0.5
    daily_water_requirement_mm: float = 5.0

    @classmethod
    def for_crop(cls, crop: CropType) -> "CropParameters":
        presets = {
            CropType.RICE: cls(CropType.RICE, 1.0, 1.2, 1.0, 0.6, 0.3, 8.0),
            CropType.WHEAT: cls(CropType.WHEAT, 0.4, 1.15, 0.4, 1.0, 0.5, 4.5),
            CropType.CORN: cls(CropType.CORN, 0.3, 1.2, 0.6, 1.2, 0.5, 5.5),
            CropType.VEGETABLE: cls(CropType.VEGETABLE, 0.5, 1.05, 0.8, 0.4, 0.35, 6.0),
            CropType.GENERAL: cls()
        }
        return presets[crop]


@dataclass
class SoilParameters:
    """土壤水文参数"""
    soil_type: SoilType = SoilType.LOAM
    field_capacity: float = 0.35
    wilting_point: float = 0.15
    saturated_hydraulic_conductivity: float = 1.5e-5
    bulk_density: float = 1300.0
    infiltration_k: float = 20.0
    infiltration_n: float = 0.6
    surface_storage_max: float = 0.03

    @classmethod
    def for_soil(cls, soil: SoilType) -> "SoilParameters":
        presets = {
            SoilType.SAND: cls(SoilType.SAND, 0.20, 0.04, 6.0e-5, 1500.0, 60.0, 0.4, 0.01),
            SoilType.LOAM: cls(SoilType.LOAM, 0.35, 0.15, 1.5e-5, 1300.0, 20.0, 0.6, 0.03),
            SoilType.CLAY: cls(SoilType.CLAY, 0.45, 0.25, 1.0e-6, 1200.0, 5.0, 0.8, 0.05),
            SoilType.SILT: cls(SoilType.SILT, 0.40, 0.12, 5.0e-6, 1250.0, 10.0, 0.7, 0.04),
        }
        return presets[soil]


@dataclass
class IrrigationSystemConfig:
    """灌溉系统配置"""
    canal_length_m: float = 500.0
    canal_efficiency: float = 0.75
    distribution_efficiency: float = 0.85
    field_application_efficiency: float = 0.8
    num_fields: int = 3
    field_area_m2: float = 2000.0
    rotation_schedule: List[int] = field(default_factory=lambda: [1, 1, 1])


@dataclass
class IrrigationAnalysisInput:
    """灌溉分析输入"""
    wheel_id: str
    water_lift_lpm: float
    rotational_speed: float
    overall_efficiency: float
    water_level_diff: float
    irrigation_area_m2: float
    hours_operation: float = 8.0
    crop: CropType = CropType.GENERAL
    soil: SoilType = SoilType.LOAM
    weather_et0_mm_day: float = 5.0
    initial_soil_moisture_deficit: float = 0.3
    system_config: IrrigationSystemConfig = field(default_factory=IrrigationSystemConfig)


@dataclass
class IrrigationAnalysisResult:
    """灌溉分析输出"""
    total_water_delivered_m3: float
    total_water_available_field_m3: float
    effective_irrigation_depth_mm: float
    infiltration_depth_mm: float
    runoff_loss_m3: float
    deep_percolation_loss_m3: float
    crop_water_requirement_m3: float
    water_deficit_m3: float
    water_surplus_m3: float
    irrigation_efficiency: float
    conveyance_efficiency: float
    field_efficiency: float
    area_efficiency_m2_per_m3: float
    area_irrigated_m2: float
    area_unirrigated_m2: float
    irrigation_duration_hours: float
    optimal_speed: float
    speed_sweep_data: List[Dict]
    recommendation: str
    cost_estimate: Dict
    water_productivity_kg_m3: float


class SoilInfiltrationModel:
    """土壤入渗模型 (Horton方程 + Green-Ampt修正)"""

    def __init__(self, soil_params: SoilParameters):
        self.soil = soil_params

    def horton_infiltration_rate(self, t_minutes: float) -> float:
        f0 = self.soil.infiltration_k * 3
        fc = self.soil.infiltration_k
        k_decay = 0.1
        return fc + (f0 - fc) * math.exp(-k_decay * t_minutes)

    def cumulative_infiltration(self, t_minutes: float, application_rate_mm_hr: float) -> Tuple[float, float]:
        dt = 0.5
        times = np.arange(0, t_minutes + dt, dt)
        cumulative = 0.0
        runoff = 0.0
        app_rate_mm_min = application_rate_mm_hr / 60.0

        for t in times:
            f_rate = self.horton_infiltration_rate(t)
            actual_infilt = min(f_rate * dt, app_rate_mm_min * dt + cumulative * 0)
            cumulative += actual_infilt
            surface_supply = app_rate_mm_min * dt
            if surface_supply > actual_infilt:
                runoff += (surface_supply - actual_infilt)

        return cumulative, runoff

    def deep_percolation(self, infiltration_mm: float, moisture_deficit: float) -> float:
        taw = (self.soil.field_capacity - self.soil.wilting_point) * 1000
        refill_needed = moisture_deficit * taw
        return max(0, infiltration_mm - refill_needed)


class CropWaterRequirementModel:
    """作物需水量模型 (简化FAO方法)"""

    def __init__(self, crop_params: CropParameters):
        self.crop = crop_params

    def calculate_daily_etc_mm(self, et0_mm: float, growth_stage: float = 0.5) -> float:
        if growth_stage < 0.25:
            kc = self.crop.kc_initial + (self.crop.kc_mid - self.crop.kc_initial) * (growth_stage / 0.25)
        elif growth_stage < 0.75:
            kc = self.crop.kc_mid
        else:
            progress = (growth_stage - 0.75) / 0.25
            kc = self.crop.kc_mid + (self.crop.kc_end - self.crop.kc_mid) * progress
        return et0_mm * kc

    def total_water_required(self, area_m2: float, et0_mm: float, days: int = 1,
                             growth_stage: float = 0.5) -> float:
        etc_mm_day = self.calculate_daily_etc_mm(et0_mm, growth_stage)
        return (etc_mm_day / 1000.0) * area_m2 * days / 0.85


class IrrigationEfficiencyAnalyzer:
    """灌溉效率综合分析器"""

    def __init__(
        self,
        crop: Optional[CropParameters] = None,
        soil: Optional[SoilParameters] = None
    ):
        self.crop_params = crop or CropParameters.for_crop(CropType.GENERAL)
        self.soil_params = soil or SoilParameters.for_soil(SoilType.LOAM)
        self.infiltration_model = SoilInfiltrationModel(self.soil_params)
        self.crop_model = CropWaterRequirementModel(self.crop_params)

    def analyze(self, params: IrrigationAnalysisInput) -> IrrigationAnalysisResult:
        water_delivered_m3 = (params.water_lift_lpm / 1000.0) * 60.0 * params.hours_operation

        canal_loss = water_delivered_m3 * (1 - params.system_config.canal_efficiency)
        after_canal = water_delivered_m3 - canal_loss

        dist_loss = after_canal * (1 - params.system_config.distribution_efficiency)
        field_water = after_canal - dist_loss

        field_water_depth_mm = (field_water / params.irrigation_area_m2) * 1000.0

        hours = params.hours_operation
        application_rate = field_water_depth_mm / max(hours, 0.1)

        infiltration_mm, runoff_mm = self.infiltration_model.cumulative_infiltration(
            hours * 60, application_rate
        )
        runoff_m3 = (runoff_mm / 1000.0) * params.irrigation_area_m2
        infiltration_m3 = (infiltration_mm / 1000.0) * params.irrigation_area_m2

        percolation_mm = self.infiltration_model.deep_percolation(
            infiltration_mm, params.initial_soil_moisture_deficit
        )
        percolation_m3 = (percolation_mm / 1000.0) * params.irrigation_area_m2

        effective_water_m3 = infiltration_m3 - percolation_m3
        effective_depth_mm = (effective_water_m3 / params.irrigation_area_m2) * 1000.0

        crop_req_m3 = self.crop_model.total_water_required(
            params.irrigation_area_m2,
            params.weather_et0_mm_day,
            days=max(1, int(params.hours_operation / 8))
        )

        water_deficit = max(0, crop_req_m3 - effective_water_m3)
        water_surplus = max(0, effective_water_m3 - crop_req_m3)

        conveyance_eff = params.system_config.canal_efficiency * params.system_config.distribution_efficiency
        field_eff = effective_water_m3 / max(field_water, 0.001)
        overall_irrig_eff = effective_water_m3 / max(water_delivered_m3, 0.001)
        area_eff_per_m3 = params.irrigation_area_m2 / max(water_delivered_m3, 0.001)

        etc_mm = self.crop_model.calculate_daily_etc_mm(params.weather_et0_mm_day)
        required_depth = etc_mm * max(1, params.hours_operation / 8)
        needed_water_m3 = (required_depth / 1000.0) * params.irrigation_area_m2 / max(conveyance_eff * field_eff, 0.3)
        required_hours = (needed_water_m3 * 1000.0) / max(params.water_lift_lpm, 0.1) / 60.0

        actual_irrigable = min(
            params.irrigation_area_m2,
            effective_water_m3 / max((required_depth / 1000.0), 0.0001)
        )
        unirrigated = max(0, params.irrigation_area_m2 - actual_irrigable)

        sweep_data = self._sweep_speed_analysis(params)
        optimal_speed = self._find_optimal_speed(sweep_data)

        recommendation = self._generate_recommendation(
            params, water_deficit, water_surplus, overall_irrig_eff, required_hours, optimal_speed
        )

        cost = self._estimate_cost(params, water_delivered_m3, effective_water_m3)

        water_productivity = 1.5 / max(water_delivered_m3 / max(actual_irrigable, 1), 0.001)

        return IrrigationAnalysisResult(
            total_water_delivered_m3=round(water_delivered_m3, 3),
            total_water_available_field_m3=round(field_water, 3),
            effective_irrigation_depth_mm=round(effective_depth_mm, 2),
            infiltration_depth_mm=round(infiltration_mm, 2),
            runoff_loss_m3=round(runoff_m3, 3),
            deep_percolation_loss_m3=round(percolation_m3, 3),
            crop_water_requirement_m3=round(crop_req_m3, 3),
            water_deficit_m3=round(water_deficit, 3),
            water_surplus_m3=round(water_surplus, 3),
            irrigation_efficiency=round(overall_irrig_eff, 4),
            conveyance_efficiency=round(conveyance_eff, 4),
            field_efficiency=round(field_eff, 4),
            area_efficiency_m2_per_m3=round(area_eff_per_m3, 3),
            area_irrigated_m2=round(actual_irrigable, 1),
            area_unirrigated_m2=round(unirrigated, 1),
            irrigation_duration_hours=round(required_hours, 2),
            optimal_speed=round(optimal_speed, 2),
            speed_sweep_data=sweep_data,
            recommendation=recommendation,
            cost_estimate=cost,
            water_productivity_kg_m3=round(water_productivity, 3)
        )

    def _sweep_speed_analysis(self, params: IrrigationAnalysisInput,
                              min_speed: float = 5.0, max_speed: float = 30.0,
                              points: int = 20) -> List[Dict]:
        speeds = np.linspace(min_speed, max_speed, points)
        results = []

        base_lift = params.water_lift_lpm / max(params.rotational_speed, 1)

        for speed in speeds:
            lift = base_lift * speed
            efficiency_speed_factor = 1.0 - 0.3 * abs(speed - params.rotational_speed) / max(params.rotational_speed, 1)
            efficiency_speed_factor = max(0.3, min(1.2, efficiency_speed_factor))

            water_del = (lift / 1000.0) * 60.0 * params.hours_operation
            field_water = water_del * params.system_config.canal_efficiency * params.system_config.distribution_efficiency
            field_depth = (field_water / params.irrigation_area_m2) * 1000.0
            app_rate = field_depth / max(params.hours_operation, 0.1)

            infilt_mm, runoff_mm = self.infiltration_model.cumulative_infiltration(
                params.hours_operation * 60, app_rate
            )
            perc_mm = self.infiltration_model.deep_percolation(
                infilt_mm, params.initial_soil_moisture_deficit
            )

            infilt_m3 = (infilt_mm / 1000.0) * params.irrigation_area_m2
            perc_m3 = (perc_mm / 1000.0) * params.irrigation_area_m2
            effective = infilt_m3 - perc_m3

            irrig_eff = effective / max(water_del, 0.001) * efficiency_speed_factor
            irrig_eff = max(0, min(1, irrig_eff))

            etc_mm = self.crop_model.calculate_daily_etc_mm(params.weather_et0_mm_day)
            req_depth = etc_mm * max(1, params.hours_operation / 8)
            area_served = min(
                params.irrigation_area_m2,
                effective / max((req_depth / 1000.0), 0.0001)
            )

            results.append({
                "speed": round(float(speed), 2),
                "water_lift_lpm": round(float(lift), 2),
                "total_water_m3": round(float(water_del), 2),
                "effective_water_m3": round(float(effective), 2),
                "irrigation_efficiency": round(float(irrig_eff), 4),
                "area_served_m2": round(float(area_served), 1),
                "runoff_loss_m3": round(float((runoff_mm / 1000.0) * params.irrigation_area_m2), 2),
                "percolation_loss_m3": round(float(perc_m3), 2),
                "drive_power_kw": round(float(lift * params.water_level_diff * 9.81 /
                                               (60 * 1000 * max(0.1, params.overall_efficiency))), 3)
            })

        return results

    def _find_optimal_speed(self, sweep_data: List[Dict]) -> float:
        best_idx = 0
        best_score = -1
        for i, d in enumerate(sweep_data):
            score = (d["irrigation_efficiency"] * 0.6 +
                     (d["area_served_m2"] / max(1, d["total_water_m3"])) * 0.3 +
                     1.0 / max(0.1, d["drive_power_kw"]) * 0.1)
            if score > best_score:
                best_score = score
                best_idx = i
        return sweep_data[best_idx]["speed"]

    def _generate_recommendation(
        self, params, deficit, surplus, irrig_eff, req_hours, opt_speed
    ) -> str:
        recs = []

        if deficit > 0.1:
            recs.append(f"⚠ 水量不足，缺水 {deficit:.1f} m³，建议延长灌溉时间至 {req_hours:.1f} 小时")
            if opt_speed > params.rotational_speed:
                recs.append(f"  或提高转速至 {opt_speed:.1f} rpm 以增加提水量")
        elif surplus > 0.1:
            recs.append(f"💧 水量过剩 {surplus:.1f} m³，存在浪费，建议缩短灌溉时间")
            if opt_speed < params.rotational_speed:
                recs.append(f"  或降低转速至 {opt_speed:.1f} rpm 以提高效率")

        if irrig_eff < 0.5:
            recs.append(f"🔧 灌溉效率偏低 ({irrig_eff:.1%})，建议检查渠道防渗、改进配水方式")
        elif irrig_eff < 0.65:
            recs.append(f"📊 灌溉效率中等 ({irrig_eff:.1%})，有优化空间")
        else:
            recs.append(f"✅ 灌溉效率良好 ({irrig_eff:.1%})")

        if abs(params.rotational_speed - opt_speed) / max(opt_speed, 1) > 0.2:
            direction = "提高" if opt_speed > params.rotational_speed else "降低"
            recs.append(f"⚙ 推荐{direction}转速至最优工况 {opt_speed:.1f} rpm")

        return " | ".join(recs) if recs else "✅ 当前工况良好"

    def _estimate_cost(self, params, water_delivered, effective) -> Dict:
        labor_rate = 25
        power_rate = 0.6
        maintenance_factor = 0.15

        power_kw = (params.water_lift_lpm * params.water_level_diff * 9.81 /
                    (60 * 1000 * max(0.1, params.overall_efficiency)))

        labor_cost = labor_rate * params.hours_operation
        power_cost = power_rate * power_kw * params.hours_operation
        maintenance_cost = (labor_cost + power_cost) * maintenance_factor
        total_cost = labor_cost + power_cost + maintenance_cost

        return {
            "labor_cost_rmb": round(labor_cost, 2),
            "power_cost_rmb": round(power_cost, 2),
            "maintenance_cost_rmb": round(maintenance_cost, 2),
            "total_cost_rmb": round(total_cost, 2),
            "cost_per_m3_water_rmb": round(total_cost / max(water_delivered, 0.1), 4),
            "cost_per_m2_area_rmb": round(total_cost / max(params.irrigation_area_m2, 0.1), 4),
            "cost_per_m3_effective_rmb": round(total_cost / max(effective, 0.1), 4)
        }
