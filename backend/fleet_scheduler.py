"""
模块重构说明:
- 原模块名: scheduling.py
- 新模块名: fleet_scheduler.py
- 主类名: MultiWheelScheduler (保持不变)
- 重构日期: 2026-06-16
- 说明: 多水车联合灌溉调度优化模块整体迁移，所有 dataclass、枚举和类保持不变

多水车联合灌溉调度优化模块
基于贪心分配与负载均衡策略，协调多台龙骨水车的灌溉调度

核心模型:
1. 水车单元管理 (WaterWheelUnit)
2. 灌溉区域管理 (IrrigationZone)
3. 多水车调度器 (MultiWheelScheduler)
4. 贪心分配算法 (Greedy Allocation)
5. 负载均衡优化 (Load Balancing)
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from mechanics import WaterWheelSimulator, SimulationInput, WaterWheelGeometry, MaterialProperties
from irrigation import (
    IrrigationEfficiencyAnalyzer, IrrigationAnalysisInput,
    CropType, SoilType, CropParameters, SoilParameters, IrrigationSystemConfig
)

__all__ = [
    "MaintenanceStatus",
    "CommunicationDelayConfig",
    "CommunicationDelayResult",
    "CommunicationDelaySimulator",
    "WaterWheelUnit",
    "IrrigationZone",
    "WheelAllocation",
    "TimeSlot",
    "MultiWheelScheduler",
]


class MaintenanceStatus(Enum):
    OPERATIONAL = "operational"
    UNDER_REPAIR = "under_repair"


@dataclass
class CommunicationDelayConfig:
    base_delay_s: float = 2.0
    per_km_delay_s: float = 0.5
    message_loss_rate: float = 0.02
    retry_delay_s: float = 3.0
    max_retries: int = 2
    coordination_overhead_s: float = 1.0


@dataclass
class CommunicationDelayResult:
    from_wheel_id: str
    to_wheel_id: str
    distance_km: float
    one_way_delay_s: float
    round_trip_delay_s: float
    effective_delay_s: float
    message_lost: bool
    retries: int


class CommunicationDelaySimulator:
    def __init__(self, config: Optional[CommunicationDelayConfig] = None):
        self.config = config or CommunicationDelayConfig()

    def estimate_distance_km(self, loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
        dx = (loc1[0] - loc2[0]) * 111.0
        dy = (loc1[1] - loc2[1]) * 85.0
        return math.sqrt(dx * dx + dy * dy)

    def simulate_delay(
        self,
        from_id: str,
        to_id: str,
        from_loc: Tuple[float, float],
        to_loc: Tuple[float, float],
    ) -> CommunicationDelayResult:
        distance = self.estimate_distance_km(from_loc, to_loc)
        one_way = self.config.base_delay_s + distance * self.config.per_km_delay_s
        round_trip = one_way * 2
        retries = 0
        message_lost = False

        effective = round_trip + self.config.coordination_overhead_s
        for attempt in range(self.config.max_retries + 1):
            if random.random() < self.config.message_loss_rate:
                retries += 1
                effective += self.config.retry_delay_s
                if attempt == self.config.max_retries:
                    message_lost = True
            else:
                break

        return CommunicationDelayResult(
            from_wheel_id=from_id,
            to_wheel_id=to_id,
            distance_km=round(distance, 3),
            one_way_delay_s=round(one_way, 3),
            round_trip_delay_s=round(round_trip, 3),
            effective_delay_s=round(effective, 3),
            message_lost=message_lost,
            retries=retries,
        )

    def simulate_all_pairs(self, wheels: List) -> Dict[str, List[CommunicationDelayResult]]:
        results: Dict[str, List[CommunicationDelayResult]] = {}
        for i, w1 in enumerate(wheels):
            if not w1.is_available():
                continue
            results[w1.wheel_id] = []
            for j, w2 in enumerate(wheels):
                if i == j or not w2.is_available():
                    continue
                delay = self.simulate_delay(
                    w1.wheel_id, w2.wheel_id,
                    w1.location, w2.location,
                )
                results[w1.wheel_id].append(delay)
        return results

    def compute_coordination_overhead_s(self, wheels: List) -> float:
        available = [w for w in wheels if w.is_available()]
        if len(available) <= 1:
            return 0.0
        all_delays = self.simulate_all_pairs(available)
        max_delay = 0.0
        for wid, delays in all_delays.items():
            for d in delays:
                if not d.message_lost and d.effective_delay_s > max_delay:
                    max_delay = d.effective_delay_s
        return max_delay


@dataclass
class WaterWheelUnit:
    wheel_id: str
    location: Tuple[float, float]
    geometry_params: WaterWheelGeometry
    material_params: MaterialProperties
    max_speed: float = 25.0
    current_speed: float = 0.0
    efficiency_curve: Dict[float, float] = field(default_factory=dict)
    maintenance_status: MaintenanceStatus = MaintenanceStatus.OPERATIONAL
    available_hours_per_day: float = 10.0

    def __post_init__(self):
        if not self.efficiency_curve:
            self.efficiency_curve = self._generate_efficiency_curve()

    def _generate_efficiency_curve(self) -> Dict[float, float]:
        sim = WaterWheelSimulator(self.geometry_params, self.material_params)
        curve = {}
        for speed in [5, 8, 10, 12, 15, 18, 20, 22, 25]:
            if speed <= self.max_speed:
                water_lift = sim._estimate_water_lift(speed, 2.0)
                sim_in = SimulationInput(
                    rotational_speed=speed,
                    water_level_diff=2.0,
                    water_lift=water_lift,
                    chain_wear_factor=0.1
                )
                out = sim.simulate(sim_in)
                curve[speed] = out.overall_efficiency
        return curve

    def get_optimal_speed(self) -> float:
        if not self.efficiency_curve:
            return self.max_speed * 0.6
        best_speed = max(self.efficiency_curve, key=self.efficiency_curve.get)
        return min(best_speed, self.max_speed)

    def get_efficiency_at_speed(self, speed: float) -> float:
        if speed in self.efficiency_curve:
            return self.efficiency_curve[speed]
        speeds = sorted(self.efficiency_curve.keys())
        if not speeds:
            return 0.5
        if speed <= speeds[0]:
            return self.efficiency_curve[speeds[0]]
        if speed >= speeds[-1]:
            return self.efficiency_curve[speeds[-1]]
        for i in range(len(speeds) - 1):
            if speeds[i] <= speed <= speeds[i + 1]:
                t = (speed - speeds[i]) / (speeds[i + 1] - speeds[i])
                return (self.efficiency_curve[speeds[i]] * (1 - t) +
                        self.efficiency_curve[speeds[i + 1]] * t)
        return 0.5

    def estimate_water_output_m3_per_hour(self, speed: Optional[float] = None) -> float:
        if self.maintenance_status != MaintenanceStatus.OPERATIONAL:
            return 0.0
        run_speed = speed if speed is not None else self.get_optimal_speed()
        sim = WaterWheelSimulator(self.geometry_params, self.material_params)
        water_lift_lpm = sim._estimate_water_lift(run_speed, 2.0)
        return (water_lift_lpm / 1000.0) * 60.0

    def daily_capacity_m3(self) -> float:
        return self.estimate_water_output_m3_per_hour() * self.available_hours_per_day

    def is_available(self) -> bool:
        return self.maintenance_status == MaintenanceStatus.OPERATIONAL


@dataclass
class IrrigationZone:
    zone_id: str
    area_m2: float
    crop_type: CropType
    soil_type: SoilType
    water_requirement_m3: float
    elevation_m: float = 0.0
    distance_to_source_m: float = 0.0
    priority: int = 3

    def __post_init__(self):
        if self.priority < 1:
            self.priority = 1
        elif self.priority > 5:
            self.priority = 5

    def elevation_penalty(self) -> float:
        return 1.0 + self.elevation_m * 0.02

    def distance_penalty(self) -> float:
        return 1.0 + self.distance_to_source_m * 0.0005

    def adjusted_water_requirement(self) -> float:
        return self.water_requirement_m3 * self.elevation_penalty() * self.distance_penalty()

    def crop_params(self) -> CropParameters:
        return CropParameters.for_crop(self.crop_type)

    def soil_params(self) -> SoilParameters:
        return SoilParameters.for_soil(self.soil_type)


@dataclass
class WheelAllocation:
    wheel_id: str
    zone_id: str
    assigned_hours: float
    speed: float
    estimated_water_m3: float
    efficiency: float


@dataclass
class TimeSlot:
    start_hour: float
    end_hour: float
    wheel_id: str
    zone_id: str
    speed: float
    estimated_water_m3: float


class MultiWheelScheduler:
    def __init__(self, comm_config: Optional[CommunicationDelayConfig] = None):
        self.wheels: List[WaterWheelUnit] = []
        self.zones: List[IrrigationZone] = []
        self.allocations: List[WheelAllocation] = []
        self._wheel_remaining_hours: Dict[str, float] = {}
        self._wheel_remaining_capacity: Dict[str, float] = {}
        self._comm_simulator = CommunicationDelaySimulator(comm_config)

    def add_wheel(self, wheel_unit: WaterWheelUnit) -> None:
        self.wheels.append(wheel_unit)

    def add_zone(self, irrigation_zone: IrrigationZone) -> None:
        self.zones.append(irrigation_zone)

    def calculate_total_capacity(self) -> float:
        return sum(w.daily_capacity_m3() for w in self.wheels if w.is_available())

    def get_wheel_status(self) -> List[Dict]:
        status_list = []
        for w in self.wheels:
            status_list.append({
                "wheel_id": w.wheel_id,
                "location": w.location,
                "maintenance_status": w.maintenance_status.value,
                "current_speed": w.current_speed,
                "max_speed": w.max_speed,
                "optimal_speed": w.get_optimal_speed(),
                "available_hours_per_day": w.available_hours_per_day,
                "daily_capacity_m3": w.daily_capacity_m3(),
                "efficiency_at_optimal": w.get_efficiency_at_speed(w.get_optimal_speed()),
            })
        return status_list

    def _reset_tracking(self) -> None:
        self._wheel_remaining_hours = {
            w.wheel_id: w.available_hours_per_day for w in self.wheels if w.is_available()
        }
        self._wheel_remaining_capacity = {
            w.wheel_id: w.daily_capacity_m3() for w in self.wheels if w.is_available()
        }
        self.allocations = []

    def greedy_allocate(self) -> List[WheelAllocation]:
        self._reset_tracking()
        sorted_zones = sorted(
            self.zones,
            key=lambda z: (-z.priority, -z.adjusted_water_requirement())
        )
        available_wheels = [w for w in self.wheels if w.is_available()]

        for zone in sorted_zones:
            remaining_need = zone.adjusted_water_requirement()
            wheel_scores = []
            for w in available_wheels:
                if self._wheel_remaining_hours.get(w.wheel_id, 0) <= 0:
                    continue
                distance = math.sqrt(
                    (w.location[0] - 0) ** 2 + (w.location[1] - 0) ** 2
                )
                optimal_speed = w.get_optimal_speed()
                efficiency = w.get_efficiency_at_speed(optimal_speed)
                output_m3_h = w.estimate_water_output_m3_per_hour(optimal_speed)
                elevation_factor = 1.0 / max(zone.elevation_penalty(), 0.1)
                distance_factor = 1.0 / max(zone.distance_penalty(), 0.1)
                score = efficiency * output_m3_h * elevation_factor * distance_factor
                wheel_scores.append((w, score, optimal_speed, output_m3_h))

            wheel_scores.sort(key=lambda x: -x[1])

            for w, score, optimal_speed, output_m3_h in wheel_scores:
                if remaining_need <= 0:
                    break
                if self._wheel_remaining_hours.get(w.wheel_id, 0) <= 0:
                    continue

                hours_needed = remaining_need / max(output_m3_h, 0.001)
                hours_available = self._wheel_remaining_hours[w.wheel_id]
                assigned_hours = min(hours_needed, hours_available)
                estimated_water = output_m3_h * assigned_hours

                self.allocations.append(WheelAllocation(
                    wheel_id=w.wheel_id,
                    zone_id=zone.zone_id,
                    assigned_hours=assigned_hours,
                    speed=optimal_speed,
                    estimated_water_m3=round(estimated_water, 3),
                    efficiency=w.get_efficiency_at_speed(optimal_speed)
                ))

                self._wheel_remaining_hours[w.wheel_id] -= assigned_hours
                self._wheel_remaining_capacity[w.wheel_id] -= estimated_water
                remaining_need -= estimated_water

        return self.allocations

    def balance_load(self) -> List[WheelAllocation]:
        if not self.allocations:
            self.greedy_allocate()

        operational_wheels = [w for w in self.wheels if w.is_available()]
        if len(operational_wheels) <= 1:
            return self.allocations

        avg_load = sum(
            w.available_hours_per_day - self._wheel_remaining_hours.get(w.wheel_id, 0)
            for w in operational_wheels
        ) / len(operational_wheels)

        max_iterations = 10
        for _ in range(max_iterations):
            loads = {}
            for w in operational_wheels:
                loads[w.wheel_id] = w.available_hours_per_day - self._wheel_remaining_hours.get(w.wheel_id, 0)

            max_load_wheel_id = max(loads, key=loads.get)
            min_load_wheel_id = min(loads, key=loads.get)

            if loads[max_load_wheel_id] - loads[min_load_wheel_id] < 0.5:
                break

            overloaded_allocs = [
                a for a in self.allocations if a.wheel_id == max_load_wheel_id
            ]
            if not overloaded_allocs:
                break

            transfer_cand = min(overloaded_allocs, key=lambda a: a.efficiency)
            underloaded_wheel = next(
                w for w in operational_wheels if w.wheel_id == min_load_wheel_id
            )

            output_m3_h = underloaded_wheel.estimate_water_output_m3_per_hour(
                underloaded_wheel.get_optimal_speed()
            )
            if output_m3_h <= 0:
                break

            transfer_hours = min(
                (loads[max_load_wheel_id] - avg_load) * 0.5,
                self._wheel_remaining_hours.get(min_load_wheel_id, 0),
                transfer_cand.assigned_hours * 0.5
            )

            if transfer_hours < 0.1:
                break

            transfer_water = output_m3_h * transfer_hours

            self.allocations.append(WheelAllocation(
                wheel_id=min_load_wheel_id,
                zone_id=transfer_cand.zone_id,
                assigned_hours=transfer_hours,
                speed=underloaded_wheel.get_optimal_speed(),
                estimated_water_m3=round(transfer_water, 3),
                efficiency=underloaded_wheel.get_efficiency_at_speed(
                    underloaded_wheel.get_optimal_speed()
                )
            ))

            original_hours = transfer_cand.assigned_hours
            transfer_cand.assigned_hours -= transfer_hours
            remaining_ratio = transfer_cand.assigned_hours / max(original_hours, 0.001)
            transfer_cand.estimated_water_m3 = round(
                transfer_cand.estimated_water_m3 * remaining_ratio, 3
            )

            self._wheel_remaining_hours[max_load_wheel_id] = (
                self._wheel_remaining_hours.get(max_load_wheel_id, 0) + transfer_hours
            )
            self._wheel_remaining_hours[min_load_wheel_id] = (
                self._wheel_remaining_hours.get(min_load_wheel_id, 0) - transfer_hours
            )

        self.allocations = [a for a in self.allocations if a.assigned_hours > 0.01]
        return self.allocations

    def optimize_schedule(
        self, target_water_m3: float, hours_available: float
    ) -> Dict:
        for w in self.wheels:
            if w.is_available():
                w.available_hours_per_day = min(w.available_hours_per_day, hours_available)

        self.greedy_allocate()
        self.balance_load()

        total_allocated = sum(a.estimated_water_m3 for a in self.allocations)
        deficit = max(0, target_water_m3 - total_allocated)

        speed_adjustments = []
        if deficit > 0:
            for w in self.wheels:
                if not w.is_available():
                    continue
                current_allocations = [a for a in self.allocations if a.wheel_id == w.wheel_id]
                for alloc in current_allocations:
                    if alloc.speed < w.max_speed:
                        new_speed = min(alloc.speed * 1.15, w.max_speed)
                        new_output = w.estimate_water_output_m3_per_hour(new_speed)
                        new_water = new_output * alloc.assigned_hours
                        speed_adjustments.append({
                            "wheel_id": w.wheel_id,
                            "zone_id": alloc.zone_id,
                            "old_speed": round(alloc.speed, 2),
                            "new_speed": round(new_speed, 2),
                            "additional_water_m3": round(new_water - alloc.estimated_water_m3, 3)
                        })
                        alloc.speed = new_speed
                        alloc.estimated_water_m3 = round(new_water, 3)
                        alloc.efficiency = w.get_efficiency_at_speed(new_speed)

        revised_total = sum(a.estimated_water_m3 for a in self.allocations)
        remaining_deficit = max(0, target_water_m3 - revised_total)

        comm_delays = self._comm_simulator.simulate_all_pairs(self.wheels)
        coordination_overhead = self._comm_simulator.compute_coordination_overhead_s(self.wheels)
        comm_delay_summary = []
        for wid, delays in comm_delays.items():
            for d in delays:
                comm_delay_summary.append({
                    "from": d.from_wheel_id,
                    "to": d.to_wheel_id,
                    "distance_km": d.distance_km,
                    "effective_delay_s": d.effective_delay_s,
                    "message_lost": d.message_lost,
                })

        return {
            "target_water_m3": target_water_m3,
            "hours_available": hours_available,
            "total_allocated_m3": round(revised_total, 3),
            "deficit_m3": round(remaining_deficit, 3),
            "fulfillment_ratio": round(min(1.0, revised_total / max(target_water_m3, 0.001)), 4),
            "allocations": [
                {
                    "wheel_id": a.wheel_id,
                    "zone_id": a.zone_id,
                    "assigned_hours": round(a.assigned_hours, 2),
                    "speed_rpm": round(a.speed, 2),
                    "estimated_water_m3": a.estimated_water_m3,
                    "efficiency": round(a.efficiency, 4)
                }
                for a in self.allocations
            ],
            "speed_adjustments": speed_adjustments,
            "schedule": self._build_time_slots(),
            "communication_delays": comm_delay_summary,
            "coordination_overhead_s": round(coordination_overhead, 3),
        }

    def estimate_completion_time(self, total_water_m3: float) -> Dict:
        operational = [w for w in self.wheels if w.is_available()]
        if not operational:
            return {
                "total_water_m3": total_water_m3,
                "estimated_hours": float('inf'),
                "feasible": False,
                "total_capacity_m3_per_hour": 0.0
            }

        total_capacity_per_hour = sum(
            w.estimate_water_output_m3_per_hour(w.get_optimal_speed())
            for w in operational
        )

        if total_capacity_per_hour <= 0:
            return {
                "total_water_m3": total_water_m3,
                "estimated_hours": float('inf'),
                "feasible": False,
                "total_capacity_m3_per_hour": 0.0
            }

        estimated_hours = total_water_m3 / total_capacity_per_hour
        max_available = max(w.available_hours_per_day for w in operational)
        days_needed = math.ceil(estimated_hours / max_available) if max_available > 0 else float('inf')
        feasible = estimated_hours <= max_available

        return {
            "total_water_m3": total_water_m3,
            "estimated_hours": round(estimated_hours, 2),
            "estimated_days": days_needed,
            "feasible": feasible,
            "total_capacity_m3_per_hour": round(total_capacity_per_hour, 3),
            "num_operational_wheels": len(operational),
            "per_wheel_breakdown": [
                {
                    "wheel_id": w.wheel_id,
                    "output_m3_per_hour": round(w.estimate_water_output_m3_per_hour(w.get_optimal_speed()), 3),
                    "hours_needed": round(
                        total_water_m3 / max(
                            sum(
                                ww.estimate_water_output_m3_per_hour(ww.get_optimal_speed())
                                for ww in operational
                            ),
                            0.001
                        ), 2
                    )
                }
                for w in operational
            ]
        }

    def generate_schedule(self) -> Dict:
        if not self.allocations:
            self.greedy_allocate()
            self.balance_load()

        time_slots = self._build_time_slots()

        zone_schedule = {}
        for slot in time_slots:
            if slot.zone_id not in zone_schedule:
                zone_schedule[slot.zone_id] = []
            zone_schedule[slot.zone_id].append({
                "wheel_id": slot.wheel_id,
                "start_hour": slot.start_hour,
                "end_hour": slot.end_hour,
                "speed_rpm": round(slot.speed, 2),
                "estimated_water_m3": slot.estimated_water_m3
            })

        wheel_schedule = {}
        for slot in time_slots:
            if slot.wheel_id not in wheel_schedule:
                wheel_schedule[slot.wheel_id] = []
            wheel_schedule[slot.wheel_id].append({
                "zone_id": slot.zone_id,
                "start_hour": slot.start_hour,
                "end_hour": slot.end_hour,
                "speed_rpm": round(slot.speed, 2),
                "estimated_water_m3": slot.estimated_water_m3
            })

        total_water = sum(slot.estimated_water_m3 for slot in time_slots)
        total_operating_hours = sum(
            slot.end_hour - slot.start_hour for slot in time_slots
        )

        zone_water = {}
        for zone in self.zones:
            zone_allocs = [a for a in self.allocations if a.zone_id == zone.zone_id]
            zone_water[zone.zone_id] = {
                "required_m3": zone.adjusted_water_requirement(),
                "allocated_m3": round(sum(a.estimated_water_m3 for a in zone_allocs), 3),
                "fulfillment": round(
                    min(1.0, sum(a.estimated_water_m3 for a in zone_allocs) /
                        max(zone.adjusted_water_requirement(), 0.001)), 4
                ),
                "priority": zone.priority
            }

        return {
            "time_slots": [
                {
                    "start_hour": slot.start_hour,
                    "end_hour": slot.end_hour,
                    "wheel_id": slot.wheel_id,
                    "zone_id": slot.zone_id,
                    "speed_rpm": round(slot.speed, 2),
                    "estimated_water_m3": slot.estimated_water_m3
                }
                for slot in time_slots
            ],
            "zone_schedule": zone_schedule,
            "wheel_schedule": wheel_schedule,
            "total_water_m3": round(total_water, 3),
            "total_operating_hours": round(total_operating_hours, 2),
            "zone_fulfillment": zone_water
        }

    def _build_time_slots(self) -> List[TimeSlot]:
        wheel_time_cursor: Dict[str, float] = {
            w.wheel_id: 0.0 for w in self.wheels if w.is_available()
        }
        slots = []

        wheel_allocs: Dict[str, List[WheelAllocation]] = {}
        for a in self.allocations:
            if a.wheel_id not in wheel_allocs:
                wheel_allocs[a.wheel_id] = []
            wheel_allocs[a.wheel_id].append(a)

        for wheel_id, allocs in wheel_allocs.items():
            allocs_sorted = sorted(allocs, key=lambda a: -a.estimated_water_m3)
            for a in allocs_sorted:
                start = wheel_time_cursor.get(wheel_id, 0)
                end = start + a.assigned_hours
                slots.append(TimeSlot(
                    start_hour=round(start, 2),
                    end_hour=round(end, 2),
                    wheel_id=a.wheel_id,
                    zone_id=a.zone_id,
                    speed=a.speed,
                    estimated_water_m3=a.estimated_water_m3
                ))
                wheel_time_cursor[wheel_id] = end

        return sorted(slots, key=lambda s: (s.start_hour, s.wheel_id))

    def get_recommendations(self) -> List[Dict]:
        recommendations = []
        operational = [w for w in self.wheels if w.is_available()]
        under_repair = [w for w in self.wheels if not w.is_available()]

        if not operational:
            recommendations.append({
                "type": "critical",
                "message": "没有可运行的水车，无法执行灌溉任务",
                "action": "尽快维修水车或调配备用设备"
            })
            return recommendations

        total_cap = self.calculate_total_capacity()
        total_demand = sum(z.adjusted_water_requirement() for z in self.zones)

        if total_cap < total_demand * 0.8:
            deficit_pct = round((1 - total_cap / max(total_demand, 0.001)) * 100, 1)
            recommendations.append({
                "type": "warning",
                "message": f"总容量不足以满足灌溉需求，缺口约 {deficit_pct}%",
                "action": "考虑延长灌溉时间、增加水车数量或调整灌溉优先级"
            })

        comm_delays = self._comm_simulator.simulate_all_pairs(self.wheels)
        max_delay = 0.0
        lost_count = 0
        for wid, delays in comm_delays.items():
            for d in delays:
                if d.effective_delay_s > max_delay:
                    max_delay = d.effective_delay_s
                if d.message_lost:
                    lost_count += 1
        if max_delay > 10.0:
            recommendations.append({
                "type": "warning",
                "message": f"最大通信延迟 {max_delay:.1f}s，协调响应可能不足",
                "action": "考虑缩短水车间距或增加通信中继"
            })
        if lost_count > 0:
            recommendations.append({
                "type": "warning",
                "message": f"{lost_count} 条通信链路丢包，需重试",
                "action": "检查通信设备或增加冗余链路"
            })

        if under_repair:
            recommendations.append({
                "type": "info",
                "message": f"{len(under_repair)} 台水车正在维修中",
                "action": f"优先修复: {', '.join(w.wheel_id for w in under_repair)}"
            })

        for w in operational:
            opt_speed = w.get_optimal_speed()
            current_eff = w.get_efficiency_at_speed(w.current_speed) if w.current_speed > 0 else 0
            optimal_eff = w.get_efficiency_at_speed(opt_speed)
            if w.current_speed > 0 and abs(current_eff - optimal_eff) > 0.05:
                direction = "提高" if opt_speed > w.current_speed else "降低"
                recommendations.append({
                    "type": "optimization",
                    "message": f"水车 {w.wheel_id} 当前效率 {current_eff:.2%}，最优效率 {optimal_eff:.2%}",
                    "action": f"{direction}转速至 {opt_speed:.1f} rpm"
                })

        for w in operational:
            if w.available_hours_per_day < 8:
                recommendations.append({
                    "type": "info",
                    "message": f"水车 {w.wheel_id} 每日可用时间仅 {w.available_hours_per_day:.1f} 小时",
                    "action": "检查是否可延长运行时间或安排轮班"
                })

        high_priority_unmet = []
        for zone in self.zones:
            zone_allocs = [a for a in self.allocations if a.zone_id == zone.zone_id]
            allocated = sum(a.estimated_water_m3 for a in zone_allocs)
            if allocated < zone.adjusted_water_requirement() * 0.9 and zone.priority >= 4:
                high_priority_unmet.append(zone.zone_id)

        if high_priority_unmet:
            recommendations.append({
                "type": "warning",
                "message": f"高优先级区域供水不足: {', '.join(high_priority_unmet)}",
                "action": "重新分配水车优先服务高优先级区域"
            })

        load_imbalance = False
        if operational:
            loads = []
            for w in operational:
                used = w.available_hours_per_day - self._wheel_remaining_hours.get(w.wheel_id, w.available_hours_per_day)
                load_pct = used / max(w.available_hours_per_day, 0.001)
                loads.append(load_pct)
            if loads and (max(loads) - min(loads)) > 0.3:
                load_imbalance = True

        if load_imbalance:
            recommendations.append({
                "type": "optimization",
                "message": "水车负载不均衡，部分水车过载",
                "action": "执行负载均衡以优化水车利用率"
            })

        crop_zone_counts: Dict[CropType, int] = {}
        for z in self.zones:
            crop_zone_counts[z.crop_type] = crop_zone_counts.get(z.crop_type, 0) + 1

        for crop, count in crop_zone_counts.items():
            if count > 2 and crop in (CropType.RICE, CropType.VEGETABLE):
                recommendations.append({
                    "type": "info",
                    "message": f"有 {count} 个{crop.value}区域，需水量较大",
                    "action": "确保高需水作物区域有足够的水车覆盖"
                })

        if not recommendations:
            recommendations.append({
                "type": "info",
                "message": "当前调度状态良好",
                "action": "继续按当前计划运行"
            })

        return recommendations
