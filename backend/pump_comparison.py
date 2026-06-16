"""
龙骨水车与现代离心泵跨时代效率对比模块
对比古代龙骨水车与近代离心泵的效率、成本与环境影响
"""
import math
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional

from mechanics import WaterWheelSimulator, SimulationInput, WaterWheelGeometry, MaterialProperties


@dataclass
class PumpPerformance:
    flow_rate_m3h: float
    head_m: float
    pump_efficiency: float
    motor_efficiency: float
    overall_efficiency: float
    power_consumption_kw: float
    shaft_power_kw: float
    npsh_required_m: float
    npsh_available_m: float
    specific_speed: float


@dataclass
class PumpAffinityResult:
    original_flow: float
    new_flow: float
    original_head: float
    new_head: float
    original_power: float
    new_power: float
    speed_ratio: float


@dataclass
class WaterwheelCostResult:
    labor_cost_annual: float
    maintenance_cost_annual: float
    material_replacement_cost: float
    total_annual_cost: float
    cost_per_m3_water: float


@dataclass
class PumpCostResult:
    electricity_cost_annual: float
    maintenance_cost_annual: float
    total_annual_cost: float
    cost_per_m3_water: float
    energy_per_m3_kwh: float


@dataclass
class EfficiencyComparison:
    waterwheel_overall_efficiency: float
    pump_overall_efficiency: float
    waterwheel_output_power_w: float
    pump_output_power_w: float
    waterwheel_input_power_w: float
    pump_input_power_w: float
    efficiency_ratio: float
    flow_rate_m3h: float
    water_level_m: float
    pump_operating_validation: Optional[Dict] = None


@dataclass
class CostComparison:
    waterwheel_cost: WaterwheelCostResult
    pump_cost: PumpCostResult
    cost_difference_annual: float
    cost_ratio: float
    payback_years_if_replace: float


@dataclass
class EnvironmentalComparison:
    waterwheel_carbon_kg_per_year: float
    pump_carbon_kg_per_year: float
    waterwheel_energy_source: str
    pump_energy_source: str
    carbon_savings_kg_per_year: float
    carbon_reduction_percent: float
    waterwheel_material_sustainability_score: float
    pump_material_sustainability_score: float


@dataclass
class EfficiencyCurvePoint:
    speed_ratio: float
    flow_rate_m3h: float
    pump_efficiency: float
    pump_power_kw: float
    waterwheel_speed_rpm: float
    waterwheel_efficiency: float


@dataclass
class FullComparison:
    efficiency: EfficiencyComparison
    cost: CostComparison
    environmental: EnvironmentalComparison
    recommendation: str


@dataclass
class OperatingRange:
    min_flow_m3h: float
    max_flow_m3h: float
    min_head_m: float
    max_head_m: float
    best_efficiency_flow_m3h: float
    best_efficiency_head_m: float


@dataclass
class OperatingPointValidation:
    is_within_range: bool
    flow_deviation_pct: float
    head_deviation_pct: float
    warnings: List[str]
    recommended_flow_m3h: float
    recommended_head_m: float


class CentrifugalPumpModel:
    def __init__(
        self,
        rated_flow_m3h: float = 50.0,
        rated_head_m: float = 30.0,
        rated_speed_rpm: float = 1450.0,
        pump_efficiency: float = 0.75,
        motor_efficiency: float = 0.92,
        impeller_diameter_m: float = 0.2,
        suction_diameter_m: float = 0.1,
    ):
        self.rated_flow = rated_flow_m3h
        self.rated_head = rated_head_m
        self.rated_speed = rated_speed_rpm
        self.base_pump_efficiency = max(0.60, min(0.85, pump_efficiency))
        self.motor_efficiency = max(0.85, min(0.96, motor_efficiency))
        self.impeller_diameter = impeller_diameter_m
        self.suction_diameter = suction_diameter_m
        self.rho = 1000.0
        self.g = 9.81

    def calculate_performance(
        self,
        flow_rate_m3h: float,
        head_m: float,
        speed_rpm: Optional[float] = None,
        atmospheric_pressure_pa: float = 101325.0,
        vapor_pressure_pa: float = 2338.0,
        suction_head_m: float = 2.0,
    ) -> PumpPerformance:
        n = speed_rpm or self.rated_speed
        Q = flow_rate_m3h / 3600.0
        H = head_m

        pump_eff = self._off_design_efficiency(flow_rate_m3h, head_m, n)

        shaft_power = self.rho * self.g * Q * H / pump_eff if pump_eff > 0 else float('inf')
        motor_input_power = shaft_power / self.motor_efficiency if self.motor_efficiency > 0 else float('inf')

        overall_eff = pump_eff * self.motor_efficiency

        ns = self._specific_speed(flow_rate_m3h, head_m, n)

        npsh_required = self._calculate_npsh_required(flow_rate_m3h, n)
        npsh_available = self._calculate_npsh_available(
            atmospheric_pressure_pa, vapor_pressure_pa, suction_head_m
        )

        return PumpPerformance(
            flow_rate_m3h=flow_rate_m3h,
            head_m=head_m,
            pump_efficiency=round(pump_eff, 4),
            motor_efficiency=round(self.motor_efficiency, 4),
            overall_efficiency=round(overall_eff, 4),
            power_consumption_kw=round(motor_input_power / 1000.0, 4),
            shaft_power_kw=round(shaft_power / 1000.0, 4),
            npsh_required_m=round(npsh_required, 3),
            npsh_available_m=round(npsh_available, 3),
            specific_speed=round(ns, 2),
        )

    def _off_design_efficiency(self, flow_m3h: float, head_m: float, speed_rpm: float) -> float:
        speed_ratio = speed_rpm / self.rated_speed if self.rated_speed > 0 else 1.0
        rated_flow_at_speed = self.rated_flow * speed_ratio
        rated_head_at_speed = self.rated_head * speed_ratio ** 2

        if rated_flow_at_speed <= 0:
            return 0.1

        q_ratio = flow_m3h / rated_flow_at_speed
        h_ratio = head_m / rated_head_at_speed if rated_head_at_speed > 0 else 1.0

        flow_deviation = abs(q_ratio - 1.0)
        head_deviation = abs(h_ratio - 1.0)

        flow_penalty = 0.15 * flow_deviation ** 1.5
        head_penalty = 0.10 * head_deviation ** 1.5

        efficiency = self.base_pump_efficiency - flow_penalty - head_penalty

        if q_ratio < 0.3 or q_ratio > 1.5:
            efficiency *= 0.7
        if q_ratio < 0.1 or q_ratio > 1.8:
            efficiency *= 0.5

        return max(0.05, min(0.85, efficiency))

    def _specific_speed(self, flow_m3h: float, head_m: float, speed_rpm: float) -> float:
        if head_m <= 0:
            return 0.0
        return speed_rpm * math.sqrt(flow_m3h) / head_m ** 0.75

    def _calculate_npsh_required(self, flow_m3h: float, speed_rpm: float) -> float:
        Q = flow_m3h / 3600.0
        A_suction = math.pi * (self.suction_diameter / 2) ** 2
        v_suction = Q / A_suction if A_suction > 0 else 0
        dynamic_head = v_suction ** 2 / (2 * self.g)
        suction_loss = 0.5 * dynamic_head
        npsh_r = dynamic_head + suction_loss + 1.5
        return npsh_r

    def _calculate_npsh_available(
        self,
        atmospheric_pressure_pa: float,
        vapor_pressure_pa: float,
        suction_head_m: float,
    ) -> float:
        hatm = atmospheric_pressure_pa / (self.rho * self.g)
        hv = vapor_pressure_pa / (self.rho * self.g)
        return hatm - hv - suction_head_m

    def affinity_laws(
        self,
        original_flow: float,
        original_head: float,
        original_power: float,
        new_speed_rpm: float,
    ) -> PumpAffinityResult:
        ratio = new_speed_rpm / self.rated_speed if self.rated_speed > 0 else 1.0
        return PumpAffinityResult(
            original_flow=original_flow,
            new_flow=original_flow * ratio,
            original_head=original_head,
            new_head=original_head * ratio ** 2,
            original_power=original_power,
            new_power=original_power * ratio ** 3,
            speed_ratio=round(ratio, 4),
        )

    def power_consumption(self, flow_m3h: float, head_m: float) -> float:
        Q = flow_m3h / 3600.0
        pump_eff = self._off_design_efficiency(flow_m3h, head_m, self.rated_speed)
        if pump_eff <= 0:
            return float('inf')
        shaft_power = self.rho * self.g * Q * head_m / pump_eff
        motor_power = shaft_power / self.motor_efficiency
        return motor_power / 1000.0

    def operating_cost(
        self,
        flow_m3h: float,
        head_m: float,
        hours_per_year: float,
        electricity_rate: float = 0.8,
    ) -> float:
        power_kw = self.power_consumption(flow_m3h, head_m)
        return power_kw * hours_per_year * electricity_rate

    def get_operating_range(self) -> OperatingRange:
        return OperatingRange(
            min_flow_m3h=self.rated_flow * 0.3,
            max_flow_m3h=self.rated_flow * 1.5,
            min_head_m=self.rated_head * 0.5,
            max_head_m=self.rated_head * 1.3,
            best_efficiency_flow_m3h=self.rated_flow * 0.95,
            best_efficiency_head_m=self.rated_head * 1.0,
        )

    def validate_operating_point(self, flow_m3h: float, head_m: float) -> OperatingPointValidation:
        rng = self.get_operating_range()
        warnings = []
        flow_dev = 0.0
        head_dev = 0.0

        if rng.best_efficiency_flow_m3h > 0:
            flow_dev = abs(flow_m3h - rng.best_efficiency_flow_m3h) / rng.best_efficiency_flow_m3h * 100
        if rng.best_efficiency_head_m > 0:
            head_dev = abs(head_m - rng.best_efficiency_head_m) / rng.best_efficiency_head_m * 100

        if flow_m3h < rng.min_flow_m3h:
            warnings.append(f"流量{flow_m3h:.1f}m3/h低于最小允许流量{rng.min_flow_m3h:.1f}m3/h，存在过热风险")
        elif flow_m3h > rng.max_flow_m3h:
            warnings.append(f"流量{flow_m3h:.1f}m3/h超过最大允许流量{rng.max_flow_m3h:.1f}m3/h，电机过载风险")

        if head_m < rng.min_head_m:
            warnings.append(f"扬程{head_m:.1f}m低于最小运行扬程{rng.min_head_m:.1f}m，效率严重偏离")
        elif head_m > rng.max_head_m:
            warnings.append(f"扬程{head_m:.1f}m超过最大运行扬程{rng.max_head_m:.1f}m，可能无法供水")

        if flow_dev > 30:
            warnings.append(f"流量偏离BEP {flow_dev:.1f}%，效率损失显著")
        if head_dev > 30:
            warnings.append(f"扬程偏离BEP {head_dev:.1f}%，运行工况不佳")

        is_within = (rng.min_flow_m3h <= flow_m3h <= rng.max_flow_m3h and
                     rng.min_head_m <= head_m <= rng.max_head_m)

        return OperatingPointValidation(
            is_within_range=is_within,
            flow_deviation_pct=round(flow_dev, 2),
            head_deviation_pct=round(head_dev, 2),
            warnings=warnings,
            recommended_flow_m3h=round(rng.best_efficiency_flow_m3h, 2),
            recommended_head_m=round(rng.best_efficiency_head_m, 2),
        )


class WaterwheelOperatingCost:
    def __init__(
        self,
        num_workers: int = 3,
        wage_per_worker_per_day: float = 150.0,
        working_days_per_year: int = 300,
        wood_replacement_cost_annual: float = 800.0,
        chain_repair_cost_annual: float = 500.0,
        general_maintenance_rate: float = 0.05,
        wheel_construction_cost: float = 5000.0,
    ):
        self.num_workers = max(2, min(4, num_workers))
        self.wage_per_worker_per_day = wage_per_worker_per_day
        self.working_days_per_year = working_days_per_year
        self.wood_replacement_cost = wood_replacement_cost_annual
        self.chain_repair_cost = chain_repair_cost_annual
        self.general_maintenance_rate = general_maintenance_rate
        self.wheel_construction_cost = wheel_construction_cost

    def calculate(self, annual_water_volume_m3: float) -> WaterwheelCostResult:
        labor_cost = self.num_workers * self.wage_per_worker_per_day * self.working_days_per_year
        material_replacement = self.wood_replacement_cost + self.chain_repair_cost
        general_maintenance = self.wheel_construction_cost * self.general_maintenance_rate
        maintenance_cost = material_replacement + general_maintenance
        total = labor_cost + maintenance_cost

        cost_per_m3 = total / annual_water_volume_m3 if annual_water_volume_m3 > 0 else float('inf')

        return WaterwheelCostResult(
            labor_cost_annual=round(labor_cost, 2),
            maintenance_cost_annual=round(maintenance_cost, 2),
            material_replacement_cost=round(material_replacement, 2),
            total_annual_cost=round(total, 2),
            cost_per_m3_water=round(cost_per_m3, 4),
        )


class PumpOperatingCost:
    def __init__(
        self,
        electricity_rate: float = 0.8,
        maintenance_rate: float = 0.03,
        pump_purchase_cost: float = 15000.0,
        motor_purchase_cost: float = 8000.0,
    ):
        self.electricity_rate = electricity_rate
        self.maintenance_rate = maintenance_rate
        self.pump_purchase_cost = pump_purchase_cost
        self.motor_purchase_cost = motor_purchase_cost

    def calculate(
        self,
        pump_model: CentrifugalPumpModel,
        flow_m3h: float,
        head_m: float,
        hours_per_year: float,
    ) -> PumpCostResult:
        power_kw = pump_model.power_consumption(flow_m3h, head_m)
        annual_electricity = power_kw * hours_per_year * self.electricity_rate

        total_equipment = self.pump_purchase_cost + self.motor_purchase_cost
        maintenance_cost = total_equipment * self.maintenance_rate

        total = annual_electricity + maintenance_cost

        annual_volume = flow_m3h * hours_per_year
        cost_per_m3 = total / annual_volume if annual_volume > 0 else float('inf')
        energy_per_m3 = power_kw / flow_m3h if flow_m3h > 0 else float('inf')

        return PumpCostResult(
            electricity_cost_annual=round(annual_electricity, 2),
            maintenance_cost_annual=round(maintenance_cost, 2),
            total_annual_cost=round(total, 2),
            cost_per_m3_water=round(cost_per_m3, 4),
            energy_per_m3_kwh=round(energy_per_m3, 4),
        )


class CrossEraComparison:
    def __init__(
        self,
        pump_model: Optional[CentrifugalPumpModel] = None,
        waterwheel_sim: Optional[WaterWheelSimulator] = None,
        waterwheel_cost: Optional[WaterwheelOperatingCost] = None,
        pump_cost: Optional[PumpOperatingCost] = None,
        grid_carbon_intensity: float = 0.6,
    ):
        self.pump_model = pump_model or CentrifugalPumpModel()
        self.waterwheel_sim = waterwheel_sim or WaterWheelSimulator()
        self.waterwheel_cost = waterwheel_cost or WaterwheelOperatingCost()
        self.pump_cost = pump_cost or PumpOperatingCost()
        self.grid_carbon_intensity = grid_carbon_intensity

    def _waterwheel_theoretical_efficiency(
        self, water_level: float, rotational_speed: float = 15.0
    ) -> float:
        geom = self.waterwheel_sim.geom
        mat = self.waterwheel_sim.mat
        blade_speed = self.waterwheel_sim.chain_mechanics.calculate_chain_speed(rotational_speed)

        bucket_eff = min(0.95, 0.55 + 0.4 * geom.blade_submersion_ratio)
        if geom.blade_submersion_ratio < 0.5:
            bucket_eff *= 0.8 + 0.4 * geom.blade_submersion_ratio

        R = geom.upper_wheel_diameter / 2
        omega = 2 * math.pi * rotational_speed / 60
        friction_eff = 1.0 - mat.wood_friction_coeff * 0.15
        friction_eff = max(0.7, min(0.95, friction_eff))

        chain_speed = blade_speed
        ideal_speed = math.sqrt(2 * mat.gravity * water_level) if water_level > 0 else 1.0
        speed_ratio = chain_speed / max(ideal_speed, 0.01)
        hydraulic_eff = 4 * speed_ratio * (1 - speed_ratio)
        hydraulic_eff = max(0.3, min(0.75, hydraulic_eff))

        leakage_rate = 0.05 + 0.02 * (rotational_speed / 30)
        volumetric_eff = 1.0 - leakage_rate
        volumetric_eff = max(0.7, min(0.95, volumetric_eff))

        overall = bucket_eff * friction_eff * hydraulic_eff * volumetric_eff
        return max(0.30, min(0.55, overall))

    def _estimate_waterwheel_flow(self, water_level: float, rotational_speed: float = 15.0) -> float:
        blade_speed = self.waterwheel_sim.chain_mechanics.calculate_chain_speed(rotational_speed)
        vol_per_blade = (
            self.waterwheel_sim.geom.blade_width
            * self.waterwheel_sim.geom.blade_height
            * self.waterwheel_sim.geom.blade_submersion_ratio
            * self.waterwheel_sim.geom.channel_width
            * 0.55
        )
        chain_len = self.waterwheel_sim.geom.chain_length
        blades_per_sec = blade_speed / (chain_len / self.waterwheel_sim.geom.num_blades)
        liters_per_sec = vol_per_blade * blades_per_sec * 1000
        level_factor = 1.0 - 0.05 * max(0, water_level - 1.5)
        m3_per_h = liters_per_sec * 3.6 * level_factor
        return max(0.1, m3_per_h)

    def _simulate_waterwheel(self, water_level: float, rotational_speed: float = 15.0):
        water_lift = self._estimate_waterwheel_flow(water_level, rotational_speed)
        sim_input = SimulationInput(
            rotational_speed=rotational_speed,
            water_level_diff=water_level,
            water_lift=water_lift,
            chain_wear_factor=0.1,
            lubrication_factor=1.0,
            temperature=20.0,
        )
        result = self.waterwheel_sim.simulate(sim_input)
        return result, water_lift

    def compare_efficiency(
        self,
        water_level: float,
        flow_rate: float,
        pump_head: Optional[float] = None,
    ) -> EfficiencyComparison:
        head = pump_head if pump_head is not None else water_level * 2.5

        ww_result, ww_flow = self._simulate_waterwheel(water_level)
        ww_eff = self._waterwheel_theoretical_efficiency(water_level)

        ww_flow_m3h = self._estimate_waterwheel_flow(water_level)
        ww_output_power = self.waterwheel_sim.mat.water_density * self.waterwheel_sim.mat.gravity * (ww_flow_m3h / 3600.0) * water_level
        ww_input_power = ww_output_power / ww_eff if ww_eff > 0 else 0

        pump_perf = self.pump_model.calculate_performance(flow_rate, head)
        pump_eff = pump_perf.overall_efficiency

        pump_output_power = self.pump_model.rho * self.pump_model.g * (flow_rate / 3600.0) * head
        pump_input_power = pump_output_power / pump_eff if pump_eff > 0 else 0

        efficiency_ratio = pump_eff / ww_eff if ww_eff > 0 else float('inf')

        validation = self.pump_model.validate_operating_point(flow_rate, head)
        pump_validation_dict = {
            "is_within_range": validation.is_within_range,
            "flow_deviation_pct": validation.flow_deviation_pct,
            "head_deviation_pct": validation.head_deviation_pct,
            "warnings": validation.warnings,
            "recommended_flow_m3h": validation.recommended_flow_m3h,
            "recommended_head_m": validation.recommended_head_m,
        }

        return EfficiencyComparison(
            waterwheel_overall_efficiency=round(ww_eff, 4),
            pump_overall_efficiency=round(pump_eff, 4),
            waterwheel_output_power_w=round(ww_output_power, 2),
            pump_output_power_w=round(pump_output_power, 2),
            waterwheel_input_power_w=round(ww_input_power, 2),
            pump_input_power_w=round(pump_input_power, 2),
            efficiency_ratio=round(efficiency_ratio, 2),
            flow_rate_m3h=round(flow_rate, 2),
            water_level_m=round(water_level, 2),
            pump_operating_validation=pump_validation_dict,
        )

    def compare_costs(self, annual_operating_hours: float, flow_rate: float = 10.0, water_level: float = 2.0) -> CostComparison:
        head = water_level * 2.5

        annual_volume = flow_rate * annual_operating_hours
        ww_cost_result = self.waterwheel_cost.calculate(annual_volume)

        pump_cost_result = self.pump_cost.calculate(
            self.pump_model, flow_rate, head, annual_operating_hours
        )

        cost_diff = pump_cost_result.total_annual_cost - ww_cost_result.total_annual_cost
        cost_ratio = pump_cost_result.total_annual_cost / ww_cost_result.total_annual_cost if ww_cost_result.total_annual_cost > 0 else float('inf')

        pump_total_investment = self.pump_cost.pump_purchase_cost + self.pump_cost.motor_purchase_cost
        if cost_diff < 0:
            payback = pump_total_investment / abs(cost_diff) if abs(cost_diff) > 0 else float('inf')
        else:
            annual_pump_saving_from_efficiency = (
                (1.0 / 0.35 - 1.0 / 0.70) * flow_rate * annual_operating_hours * 0.8 * 0.5
            )
            payback = pump_total_investment / annual_pump_saving_from_efficiency if annual_pump_saving_from_efficiency > 0 else float('inf')

        return CostComparison(
            waterwheel_cost=ww_cost_result,
            pump_cost=pump_cost_result,
            cost_difference_annual=round(cost_diff, 2),
            cost_ratio=round(cost_ratio, 2),
            payback_years_if_replace=round(payback, 1),
        )

    def compare_environmental_impact(
        self,
        annual_operating_hours: float = 2000.0,
        flow_rate: float = 10.0,
        water_level: float = 2.0,
    ) -> EnvironmentalComparison:
        head = water_level * 2.5

        pump_power_kw = self.pump_model.power_consumption(flow_rate, head)
        pump_annual_electricity_kwh = pump_power_kw * annual_operating_hours
        pump_carbon = pump_annual_electricity_kwh * self.grid_carbon_intensity

        num_workers = self.waterwheel_cost.num_workers
        human_metabolic_power_kw = 0.1 * num_workers
        food_carbon_factor = 2.5
        ww_carbon = human_metabolic_power_kw * annual_operating_hours * food_carbon_factor

        wood_replacement = self.waterwheel_cost.wood_replacement_cost
        wood_carbon_factor = 0.3
        ww_carbon += wood_replacement * wood_carbon_factor

        carbon_savings = ww_carbon - pump_carbon
        carbon_reduction = (carbon_savings / ww_carbon * 100) if ww_carbon > 0 else 0

        ww_sustainability = 8.0
        pump_sustainability = 4.0

        if carbon_reduction > 50:
            pump_sustainability += 2.0
        elif carbon_reduction > 0:
            pump_sustainability += 1.0

        return EnvironmentalComparison(
            waterwheel_carbon_kg_per_year=round(ww_carbon, 2),
            pump_carbon_kg_per_year=round(pump_carbon, 2),
            waterwheel_energy_source="人力/畜力/水力",
            pump_energy_source="电网电力",
            carbon_savings_kg_per_year=round(carbon_savings, 2),
            carbon_reduction_percent=round(carbon_reduction, 2),
            waterwheel_material_sustainability_score=round(ww_sustainability, 1),
            pump_material_sustainability_score=round(pump_sustainability, 1),
        )

    def get_comparison_summary(self) -> Dict:
        summary = {
            "waterwheel": {
                "typical_efficiency_range": "30%-55%",
                "typical_flow_range_m3h": "1-20",
                "typical_head_range_m": "1-5",
                "energy_source": "人力/畜力/水力",
                "advantages": [
                    "无需外部能源",
                    "可就地取材制造",
                    "低技术门槛",
                    "环境友好",
                ],
                "disadvantages": [
                    "效率低",
                    "扬程有限",
                    "依赖人力",
                    "维护频繁",
                ],
            },
            "centrifugal_pump": {
                "typical_efficiency_range": "60%-85%",
                "typical_flow_range_m3h": "5-500",
                "typical_head_range_m": "5-100",
                "energy_source": "电力",
                "advantages": [
                    "效率高",
                    "流量扬程范围广",
                    "自动化运行",
                    "维护简单",
                ],
                "disadvantages": [
                    "依赖电力",
                    "碳排放",
                    "制造成本高",
                    "需要专业安装",
                ],
            },
            "key_metrics": {
                "efficiency_improvement_factor": "1.5x-2.5x",
                "flow_capacity_improvement": "25x-50x",
                "head_capacity_improvement": "20x-40x",
                "technology_gap_years": "约1800年",
            },
        }
        return summary

    def get_efficiency_curves(
        self, speed_range: Optional[Tuple[float, float]] = None, num_points: int = 50
    ) -> List[EfficiencyCurvePoint]:
        if speed_range is None:
            speed_range = (0.2, 1.5)

        ratios = np.linspace(speed_range[0], speed_range[1], num_points)
        curves = []

        for ratio in ratios:
            pump_speed = self.pump_model.rated_speed * ratio
            flow_at_speed = self.pump_model.rated_flow * ratio
            head_at_speed = self.pump_model.rated_head * ratio ** 2

            pump_eff = self.pump_model._off_design_efficiency(
                flow_at_speed, head_at_speed, pump_speed
            )
            pump_power = self.pump_model.power_consumption(flow_at_speed, head_at_speed)

            ww_speed = max(3, min(30, 15 * ratio))
            ww_eff = self._waterwheel_theoretical_efficiency(2.0, ww_speed)

            curves.append(EfficiencyCurvePoint(
                speed_ratio=round(ratio, 4),
                flow_rate_m3h=round(flow_at_speed, 2),
                pump_efficiency=round(pump_eff, 4),
                pump_power_kw=round(pump_power, 4),
                waterwheel_speed_rpm=round(ww_speed, 2),
                waterwheel_efficiency=round(ww_eff, 4),
            ))

        return curves

    def compare_at_same_conditions(
        self,
        water_level: float,
        flow_rate: float,
        hours_per_year: float,
    ) -> FullComparison:
        head = water_level * 2.5

        eff_comp = self.compare_efficiency(water_level, flow_rate, head)
        cost_comp = self.compare_costs(hours_per_year, flow_rate, water_level)
        env_comp = self.compare_environmental_impact(hours_per_year, flow_rate, water_level)

        pump_score = 0
        ww_score = 0

        if eff_comp.pump_overall_efficiency > eff_comp.waterwheel_overall_efficiency:
            pump_score += 3
        else:
            ww_score += 3

        if cost_comp.pump_cost.total_annual_cost < cost_comp.waterwheel_cost.total_annual_cost:
            pump_score += 2
        else:
            ww_score += 2

        if env_comp.pump_carbon_kg_per_year < env_comp.waterwheel_carbon_kg_per_year:
            pump_score += 2
        else:
            ww_score += 2

        if flow_rate > 20:
            pump_score += 2
        elif flow_rate < 5:
            ww_score += 2

        if pump_score > ww_score:
            recommendation = (
                f"现代离心泵综合更优(得分{pump_score}:{ww_score})。"
                f"效率提升{eff_comp.efficiency_ratio:.1f}倍，"
                f"年成本差异{cost_comp.cost_difference_annual:.0f}元，"
                f"碳减排{env_comp.carbon_reduction_percent:.1f}%。"
            )
        elif ww_score > pump_score:
            recommendation = (
                f"龙骨水车在此工况下综合更优(得分{ww_score}:{pump_score})。"
                f"无需电力，低流量场景更适合，材料可持续性更高。"
            )
        else:
            recommendation = (
                f"两者综合持平(得分{pump_score}:{ww_score})。"
                f"需根据具体场景和优先级进一步选择。"
            )

        return FullComparison(
            efficiency=eff_comp,
            cost=cost_comp,
            environmental=env_comp,
            recommendation=recommendation,
        )
