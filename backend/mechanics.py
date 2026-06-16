"""
龙骨水车力学仿真模型
基于链传动理论和刮水阻力计算水车驱动力矩和效率

核心模型:
1. 链传动力学模型 (Chain Drive Mechanics)
2. 刮水阻力模型 (Scraping Resistance Model)
3. 综合效率模型 (Overall Efficiency Model)
4. 链板应力分析 (Chain Link Stress Analysis)
"""
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ChainFailureMode(Enum):
    NONE = "none"
    FATIGUE = "fatigue"
    OVERLOAD = "overload"
    WEAR = "wear"
    BUCKLING = "buckling"


@dataclass
class WaterWheelGeometry:
    """水车几何参数"""
    upper_wheel_diameter: float = 1.2
    lower_wheel_diameter: float = 1.2
    center_distance: float = 4.0
    chain_pitch: float = 0.08
    num_blades: int = 24
    blade_width: float = 0.3
    blade_height: float = 0.15
    blade_thickness: float = 0.02
    groove_depth: float = 0.12
    channel_width: float = 0.35

    @property
    def chain_length(self) -> float:
        R1 = self.upper_wheel_diameter / 2
        R2 = self.lower_wheel_diameter / 2
        L = self.center_distance
        arc1 = R1 * (math.pi + 2 * math.asin((R1 - R2) / L))
        arc2 = R2 * (math.pi - 2 * math.asin((R1 - R2) / L))
        tangent = 2 * math.sqrt(L ** 2 - (R1 - R2) ** 2)
        return arc1 + arc2 + tangent

    @property
    def links_per_chain(self) -> int:
        return int(math.ceil(self.chain_length / self.chain_pitch))

    @property
    def blade_submersion_ratio(self) -> float:
        return self.blade_height / self.groove_depth


@dataclass
class MaterialProperties:
    """材料属性 - 汉代木材/竹材/铁材"""
    wood_density: float = 700.0
    bamboo_density: float = 600.0
    iron_density: float = 7800.0
    wood_elastic_modulus: float = 12e9
    iron_elastic_modulus: float = 200e9
    wood_tensile_strength: float = 80e6
    iron_tensile_strength: float = 250e6
    wood_friction_coeff: float = 0.4
    iron_friction_coeff: float = 0.15
    water_density: float = 1000.0
    gravity: float = 9.81


@dataclass
class SimulationInput:
    """仿真输入参数"""
    rotational_speed: float
    water_level_diff: float
    water_lift: float
    chain_wear_factor: float = 0.0
    lubrication_factor: float = 1.0
    temperature: float = 20.0


@dataclass
class SimulationOutput:
    """仿真输出结果"""
    drive_torque: float
    output_torque: float
    input_power: float
    output_power: float
    mechanical_efficiency: float
    hydraulic_efficiency: float
    overall_efficiency: float
    chain_tension_max: float
    chain_tension_min: float
    scrape_resistance: float
    chain_weight_resistance: float
    bending_resistance: float
    friction_resistance: float
    water_acceleration_resistance: float
    chain_failure_risk: ChainFailureMode
    chain_fatigue_life_hours: float
    per_link_stress: np.ndarray
    blade_force: np.ndarray


class ChainDriveMechanics:
    """链传动力学计算"""

    def __init__(self, geometry: WaterWheelGeometry, material: MaterialProperties):
        self.geom = geometry
        self.mat = material

    def calculate_chain_mass(self) -> float:
        num_links = self.geom.links_per_chain
        wood_link_mass = (self.geom.blade_width * self.geom.blade_height *
                          self.geom.blade_thickness * self.mat.wood_density)
        iron_pin_mass = 0.01 * 0.008 * 0.008 * self.mat.iron_density
        return num_links * (wood_link_mass + 2 * iron_pin_mass)

    def calculate_tension_distribution(self, input_torque: float, speed_rpm: float) -> Tuple[np.ndarray, np.ndarray]:
        R_upper = self.geom.upper_wheel_diameter / 2
        R_lower = self.geom.lower_wheel_diameter / 2
        L = self.geom.center_distance

        chain_mass = self.calculate_chain_mass()
        chain_mass_per_length = chain_mass / self.geom.chain_length

        num_links = self.geom.links_per_chain
        tensions = np.zeros(num_links)
        positions = np.zeros(num_links)

        T_tight = input_torque / R_upper
        centrifugal = chain_mass_per_length * (2 * math.pi * speed_rpm / 60) ** 2 * R_upper

        for i in range(num_links):
            s = i * self.geom.chain_pitch
            positions[i] = s

            if s < L:
                ratio = s / L
                tensions[i] = T_tight - ratio * (T_tight * 0.15) + centrifugal
            else:
                s_remaining = s - L
                total_remaining = self.geom.chain_length - L
                ratio = s_remaining / total_remaining
                tensions[i] = T_tight * 0.85 * (1 - ratio) + T_tight * 0.3 * ratio + centrifugal

            if 0.3 * self.geom.chain_length < s < 0.7 * self.geom.chain_length:
                blade_submerged = self.geom.blade_submersion_ratio
                hydrostatic_force = (self.mat.water_density * self.mat.gravity *
                                     self.geom.blade_width * self.geom.blade_height *
                                     blade_submerged * self.geom.groove_depth)
                tensions[i] += hydrostatic_force * 0.5

        return tensions, positions

    def calculate_chain_speed(self, speed_rpm: float) -> float:
        R = self.geom.upper_wheel_diameter / 2
        omega = 2 * math.pi * speed_rpm / 60
        return R * omega


class ScrapeResistanceModel:
    """刮水阻力模型"""

    def __init__(self, geometry: WaterWheelGeometry, material: MaterialProperties):
        self.geom = geometry
        self.mat = material

    def calculate_viscous_drag(self, blade_speed: float, water_level_diff: float) -> float:
        A = self.geom.blade_width * self.geom.blade_height * self.geom.blade_submersion_ratio
        dynamic_viscosity = 0.001002 * (1 + 0.0337 * abs(20 - 25))
        Re = self.mat.water_density * blade_speed * self.geom.blade_height / dynamic_viscosity

        if Re < 5000:
            Cd = 1.4 + 8.0 / (Re ** 0.5)
        else:
            Cd = 1.2

        drag_per_blade = 0.5 * self.mat.water_density * Cd * A * blade_speed ** 2
        return drag_per_blade * self.geom.num_blades * self.geom.blade_submersion_ratio * 0.25

    def calculate_scrape_friction(self, water_level_diff: float, wear_factor: float) -> float:
        groove_depth_eff = self.geom.groove_depth * (1 - wear_factor * 0.3)
        contact_width = self.geom.blade_width
        normal_force = (self.mat.water_density * self.mat.gravity * groove_depth_eff *
                        self.geom.blade_height * self.geom.blade_submersion_ratio *
                        self.geom.channel_width * 0.5)
        mu = self.mat.wood_friction_coeff * (1 + wear_factor * 0.5)
        return normal_force * mu * self.geom.num_blades * 0.3

    def calculate_water_acceleration_force(self, blade_speed: float) -> float:
        volume_per_blade = (self.geom.blade_width * self.geom.blade_height *
                            self.geom.blade_submersion_ratio * self.geom.channel_width * 0.6)
        mass_water = self.mat.water_density * volume_per_blade
        freq = self.geom.num_blades / (self.geom.chain_length / max(blade_speed, 0.01))
        acceleration = blade_speed * freq * 0.3
        return mass_water * acceleration * self.geom.num_blades * 0.2


class WaterWheelSimulator:
    """综合水车力学仿真器"""

    def __init__(
        self,
        geometry: Optional[WaterWheelGeometry] = None,
        material: Optional[MaterialProperties] = None
    ):
        self.geom = geometry or WaterWheelGeometry()
        self.mat = material or MaterialProperties()
        self.chain_mechanics = ChainDriveMechanics(self.geom, self.mat)
        self.scrape_model = ScrapeResistanceModel(self.geom, self.mat)

    def _weight_resistance(self, chain_tensions: np.ndarray) -> float:
        chain_mass = self.chain_mechanics.calculate_chain_mass()
        water_mass_lifted = 0
        for i, T in enumerate(chain_tensions):
            if 0.2 * self.geom.chain_length < i * self.geom.chain_pitch < 0.6 * self.geom.chain_length:
                water_mass_lifted += (self.mat.water_density * self.geom.blade_width *
                                      self.geom.blade_height * self.geom.blade_submersion_ratio *
                                      self.geom.channel_width * 0.5)
        return (chain_mass * self.mat.gravity * 0.05 +
                water_mass_lifted * self.mat.gravity * 0.3)

    def _bending_resistance(self, speed_rpm: float, wear_factor: float) -> float:
        R_upper = self.geom.upper_wheel_diameter / 2
        R_lower = self.geom.lower_wheel_diameter / 2
        links_upper = math.ceil(math.pi * R_upper / self.geom.chain_pitch)
        links_lower = math.ceil(math.pi * R_lower / self.geom.chain_pitch)
        E = self.mat.wood_elastic_modulus
        I = (self.geom.blade_width * self.geom.blade_thickness ** 3) / 12
        bending_force_per_link = (E * I / R_upper ** 2) * (1 + wear_factor * 0.4)
        return bending_force_per_link * (links_upper + links_lower) * (0.1 + speed_rpm / 100)

    def _friction_losses(
        self,
        tensions: np.ndarray,
        speed_rpm: float,
        lubrication_factor: float
    ) -> float:
        max_t = np.max(tensions)
        axle_friction = max_t * self.mat.iron_friction_coeff * (1 / lubrication_factor)
        chain_joint_friction = (np.mean(tensions) * self.mat.wood_friction_coeff *
                                (1 + speed_rpm / 200) * self.geom.links_per_chain * 0.01)
        return axle_friction + chain_joint_friction

    def _output_torque_from_water(self, water_lift_lpm: float, level_diff: float) -> float:
        mass_flow = water_lift_lpm / 60.0 * self.mat.water_density / 1000
        potential_power = mass_flow * self.mat.gravity * level_diff
        speed_rad_s = 2 * math.pi * max(1, water_lift_lpm / (
            self.geom.blade_width * self.geom.blade_height * self.geom.blade_submersion_ratio *
            self.geom.channel_width * self.geom.num_blades * 1000 / 60 * 0.4
        ))
        return potential_power / speed_rad_s if speed_rad_s > 0 else 0

    def simulate(self, params: SimulationInput) -> SimulationOutput:
        blade_speed = self.chain_mechanics.calculate_chain_speed(params.rotational_speed)

        viscous_drag = self.scrape_model.calculate_viscous_drag(blade_speed, params.water_level_diff)
        scrape_friction = self.scrape_model.calculate_scrape_friction(params.water_level_diff, params.chain_wear_factor)
        water_accel = self.scrape_model.calculate_water_acceleration_force(blade_speed)
        total_scrape_resistance = viscous_drag + scrape_friction + water_accel

        output_torque = self._output_torque_from_water(params.water_lift, params.water_level_diff)
        R_upper = self.geom.upper_wheel_diameter / 2
        estimated_torque = output_torque + total_scrape_resistance * R_upper

        tensions, positions = self.chain_mechanics.calculate_tension_distribution(
            estimated_torque, params.rotational_speed
        )

        weight_res = self._weight_resistance(tensions)
        bending_res = self._bending_resistance(params.rotational_speed, params.chain_wear_factor)
        friction_res = self._friction_losses(tensions, params.rotational_speed, params.lubrication_factor)

        drive_torque = output_torque + (
            total_scrape_resistance * R_upper +
            weight_res * R_upper +
            bending_res * R_upper +
            friction_res * R_upper
        ) * (1 + params.chain_wear_factor * 0.3)

        omega = 2 * math.pi * params.rotational_speed / 60
        input_power = drive_torque * omega
        output_power = output_torque * omega

        hydraulic_eff = min(1.0, output_power / max(input_power, 0.001))
        mechanical_eff = max(0.0, 1.0 - (
            (total_scrape_resistance + weight_res + bending_res + friction_res) * R_upper / max(drive_torque, 0.001)
        ))
        overall_eff = hydraulic_eff * mechanical_eff * (1 - params.chain_wear_factor * 0.2)

        T_max = np.max(tensions)
        T_min = np.min(tensions)
        fatigue_mode, fatigue_life = self._assess_chain_failure(T_max, T_min, params.chain_wear_factor)

        blade_forces = self._calculate_blade_forces(tensions, positions, blade_speed)

        return SimulationOutput(
            drive_torque=round(drive_torque, 4),
            output_torque=round(output_torque, 4),
            input_power=round(input_power, 4),
            output_power=round(output_power, 4),
            mechanical_efficiency=round(mechanical_eff, 4),
            hydraulic_efficiency=round(hydraulic_eff, 4),
            overall_efficiency=round(overall_eff, 4),
            chain_tension_max=round(T_max, 2),
            chain_tension_min=round(T_min, 2),
            scrape_resistance=round(total_scrape_resistance, 4),
            chain_weight_resistance=round(weight_res, 4),
            bending_resistance=round(bending_res, 4),
            friction_resistance=round(friction_res, 4),
            water_acceleration_resistance=round(water_accel, 4),
            chain_failure_risk=fatigue_mode,
            chain_fatigue_life_hours=round(fatigue_life, 1),
            per_link_stress=tensions,
            blade_force=blade_forces
        )

    def _calculate_blade_forces(self, tensions, positions, blade_speed) -> np.ndarray:
        num_blades = self.geom.num_blades
        blade_spacing = self.geom.chain_length / num_blades
        forces = np.zeros(num_blades)
        for b in range(num_blades):
            b_pos = b * blade_spacing
            idx = int(b_pos / self.geom.chain_pitch)
            idx = min(idx, len(tensions) - 1)
            if 0.2 * self.geom.chain_length < b_pos < 0.6 * self.geom.chain_length:
                hydro = (self.mat.water_density * self.mat.gravity *
                         self.geom.blade_width * self.geom.blade_height *
                         self.geom.blade_submersion_ratio * 0.5)
                drag = 0.5 * self.mat.water_density * 1.2 * (
                    self.geom.blade_width * self.geom.blade_height
                ) * blade_speed ** 2 * self.geom.blade_submersion_ratio
                forces[b] = tensions[idx] + hydro + drag
            else:
                forces[b] = tensions[idx]
        return forces

    def _assess_chain_failure(
        self, T_max: float, T_min: float, wear_factor: float
    ) -> Tuple[ChainFailureMode, float]:
        link_area = self.geom.blade_width * self.geom.blade_thickness * 0.4
        sigma_max = T_max / link_area
        sigma_min = T_min / link_area
        sigma_amplitude = (sigma_max - sigma_min) / 2
        sigma_mean = (sigma_max + sigma_min) / 2

        tensile_limit = self.mat.wood_tensile_strength * (1 - wear_factor * 0.5)

        if sigma_max > tensile_limit * 0.95:
            return ChainFailureMode.OVERLOAD, 0.0

        if wear_factor > 0.85:
            return ChainFailureMode.WEAR, 100.0

        if sigma_mean > tensile_limit * 0.7 and sigma_amplitude / tensile_limit > 0.1:
            return ChainFailureMode.BUCKLING, 500.0

        Goodman_ratio = sigma_mean / tensile_limit + sigma_amplitude / (tensile_limit * 0.3)
        if Goodman_ratio > 1.0:
            fatigue_cycles = 1e5 * (1.0 / max(Goodman_ratio, 0.5)) ** 3
            failure_mode = ChainFailureMode.FATIGUE
        else:
            fatigue_cycles = 1e8
            failure_mode = ChainFailureMode.NONE

        cycles_per_hour = (self.geom.links_per_chain * self.geom.chain_length /
                          max(self.chain_mechanics.calculate_chain_speed(15), 0.01)) * 3600
        fatigue_hours = fatigue_cycles / max(cycles_per_hour, 1)

        return failure_mode, fatigue_hours

    def optimize_speed(
        self,
        water_level_diff: float,
        target_area: float,
        min_speed: float = 5.0,
        max_speed: float = 30.0,
        num_points: int = 50
    ) -> Dict:
        speeds = np.linspace(min_speed, max_speed, num_points)
        results = []

        for speed in speeds:
            water_lift = self._estimate_water_lift(speed, water_level_diff)
            sim_in = SimulationInput(
                rotational_speed=speed,
                water_level_diff=water_level_diff,
                water_lift=water_lift,
                chain_wear_factor=0.1
            )
            out = self.simulate(sim_in)
            area_per_hour = (water_lift * 60 / 1000) / 0.05
            results.append({
                "speed": speed,
                "efficiency": out.overall_efficiency,
                "water_lift": water_lift,
                "irrigation_area_per_hour": area_per_hour,
                "power_input": out.input_power,
                "chain_failure_risk": out.chain_failure_risk.value
            })

        best_eff_idx = max(range(len(results)), key=lambda i: results[i]["efficiency"])
        best_area_idx = max(range(len(results)), key=lambda i: results[i]["irrigation_area_per_hour"])

        area_target = target_area
        for i, r in enumerate(results):
            if r["irrigation_area_per_hour"] >= area_target:
                balance_idx = i
                break
        else:
            balance_idx = best_area_idx

        return {
            "all_data": results,
            "optimal_efficiency_speed": results[best_eff_idx]["speed"],
            "optimal_efficiency": results[best_eff_idx]["efficiency"],
            "optimal_area_speed": results[best_area_idx]["speed"],
            "max_irrigation_area": results[best_area_idx]["irrigation_area_per_hour"],
            "balanced_speed": results[balance_idx]["speed"],
            "balanced_efficiency": results[balance_idx]["efficiency"],
            "balanced_area": results[balance_idx]["irrigation_area_per_hour"]
        }

    def _estimate_water_lift(self, speed_rpm: float, level_diff: float) -> float:
        blade_speed = self.chain_mechanics.calculate_chain_speed(speed_rpm)
        vol_per_blade = (self.geom.blade_width * self.geom.blade_height *
                         self.geom.blade_submersion_ratio * self.geom.channel_width * 0.55)
        chain_len = self.geom.chain_length
        blades_passing_per_second = blade_speed / (chain_len / self.geom.num_blades)
        liters_per_sec = vol_per_blade * blades_passing_per_second * 1000
        level_factor = 1.0 - 0.05 * max(0, level_diff - 1.5)
        return liters_per_sec * 60 * level_factor
