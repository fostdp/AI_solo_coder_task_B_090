import math
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from mechanics import WaterWheelSimulator, SimulationInput, WaterWheelGeometry, MaterialProperties


@dataclass
class TreadingSession:
    session_id: str = ""
    user_name: str = ""
    start_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    pedal_speed_rpm: float = 0.0
    water_lifted_liters: float = 0.0
    calories_burned: float = 0.0
    stroke_count: int = 0
    max_speed_rpm: float = 0.0
    avg_speed_rpm: float = 0.0
    difficulty_level: int = 1
    _speed_samples: List[float] = field(default_factory=list)
    _pedal_force_history: List[float] = field(default_factory=list)
    _elapsed_accumulator: float = 0.0

    def record_speed(self, rpm: float):
        self._speed_samples.append(rpm)
        if rpm > self.max_speed_rpm:
            self.max_speed_rpm = rpm
        if self._speed_samples:
            self.avg_speed_rpm = sum(self._speed_samples) / len(self._speed_samples)

    def finalize(self):
        if self._speed_samples:
            self.avg_speed_rpm = sum(self._speed_samples) / len(self._speed_samples)


class TreadingPhysics:
    GEAR_RATIO = 3.5
    BASE_POWER_W = 100.0
    PEAK_POWER_W = 300.0
    SUSTAINED_POWER_LOW_W = 75.0
    SUSTAINED_POWER_HIGH_W = 150.0
    FATIGUUE_TAU_S = 600.0
    CALORIE_RATE_LOW = 5.0
    CALORIE_RATE_HIGH = 8.0
    INERTIA_TIME_CONSTANT_S = 2.0
    WATER_EFFICIENCY_BASE = 0.55
    PUMP_LITERS_PER_JOULE = 0.000102

    def __init__(self, simulator: Optional[WaterWheelSimulator] = None):
        self.simulator = simulator or WaterWheelSimulator()

    def get_difficulty_multiplier(self, level: int) -> float:
        level = max(1, min(5, level))
        multipliers = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.3, 5: 1.6}
        return multipliers[level]

    def _fatigue_factor(self, elapsed_s: float) -> float:
        return math.exp(-elapsed_s / self.FATIGUUE_TAU_S)

    def _effective_power(self, pedal_force_n: float, pedal_cadence_rpm: float, elapsed_s: float) -> float:
        raw_power = pedal_force_n * (2 * math.pi * pedal_cadence_rpm / 60) * 0.15
        fatigue = self._fatigue_factor(elapsed_s)
        sustained_cap = self.SUSTAINED_POWER_LOW_W + (
            self.SUSTAINED_POWER_HIGH_W - self.SUSTAINED_POWER_LOW_W
        ) * fatigue
        peak_cap = self.PEAK_POWER_W * (0.5 + 0.5 * fatigue)
        return max(self.SUSTAINED_POWER_LOW_W * 0.3, min(peak_cap, min(sustained_cap, raw_power)))

    def _speed_with_inertia(self, target_rpm: float, current_rpm: float, dt_s: float) -> float:
        alpha = 1.0 - math.exp(-dt_s / self.INERTIA_TIME_CONSTANT_S)
        return current_rpm + (target_rpm - current_rpm) * alpha

    def get_instantaneous_state(
        self, pedal_force: float, pedal_cadence: float, elapsed: float, current_rpm: float = 0.0, dt: float = 0.1
    ) -> Dict[str, Any]:
        difficulty = 1.0
        effective_power = self._effective_power(pedal_force, pedal_cadence, elapsed)
        wheel_angular_velocity = (2 * math.pi * pedal_cadence / 60) * self.GEAR_RATIO
        torque = effective_power / max(wheel_angular_velocity, 0.01)
        target_rpm = pedal_cadence * self.GEAR_RATIO
        actual_rpm = self._speed_with_inertia(target_rpm, current_rpm, dt)
        fatigue = self._fatigue_factor(elapsed)
        cal_rate = self.CALORIE_RATE_LOW + (self.CALORIE_RATE_HIGH - self.CALORIE_RATE_LOW) * (
            effective_power / self.PEAK_POWER_W
        )
        cal_rate *= (0.7 + 0.3 * fatigue)

        sim_input = SimulationInput(
            rotational_speed=actual_rpm,
            water_level_diff=2.0,
            water_lift=0.0,
            chain_wear_factor=0.05,
        )
        sim_output = self.simulator.simulate(sim_input)

        return {
            "power_w": effective_power,
            "torque_nm": torque,
            "pedal_rpm": pedal_cadence,
            "wheel_rpm": actual_rpm,
            "fatigue_factor": fatigue,
            "calorie_rate_kcal_min": cal_rate,
            "mechanical_efficiency": sim_output.mechanical_efficiency,
            "overall_efficiency": sim_output.overall_efficiency,
            "drive_torque": sim_output.drive_torque,
        }

    def get_water_lifted(self, duration_s: float, avg_power_w: float) -> float:
        if duration_s <= 0 or avg_power_w <= 0:
            return 0.0
        avg_fatigue = (1.0 - math.exp(-duration_s / self.FATIGUUE_TAU_S)) / (duration_s / self.FATIGUUE_TAU_S)
        effective_power = avg_power_w * avg_fatigue
        energy_j = effective_power * duration_s
        useful_energy = energy_j * self.WATER_EFFICIENCY_BASE
        liters = useful_energy * self.PUMP_LITERS_PER_JOULE
        return liters

    def estimate_calories(self, duration_s: float, avg_power_w: float) -> float:
        if duration_s <= 0:
            return 0.0
        intensity_ratio = min(1.0, avg_power_w / self.PEAK_POWER_W)
        rate = self.CALORIE_RATE_LOW + (self.CALORIE_RATE_HIGH - self.CALORIE_RATE_LOW) * intensity_ratio
        return rate * (duration_s / 60.0)


class TreadingLeaderboard:
    def __init__(self):
        self.sessions: List[TreadingSession] = []

    def add_session(self, session: TreadingSession):
        self.sessions.append(session)

    def get_top_n(self, n: int, metric: str = "water_lifted_liters") -> List[TreadingSession]:
        key_map = {
            "water_lifted_liters": lambda s: s.water_lifted_liters,
            "calories_burned": lambda s: s.calories_burned,
            "duration_seconds": lambda s: s.duration_seconds,
            "max_speed_rpm": lambda s: s.max_speed_rpm,
            "avg_speed_rpm": lambda s: s.avg_speed_rpm,
            "stroke_count": lambda s: s.stroke_count,
        }
        key_func = key_map.get(metric, key_map["water_lifted_liters"])
        sorted_sessions = sorted(self.sessions, key=key_func, reverse=True)
        return sorted_sessions[:n]

    def get_user_best(self, user_name: str) -> Optional[TreadingSession]:
        user_sessions = [s for s in self.sessions if s.user_name == user_name]
        if not user_sessions:
            return None
        return max(user_sessions, key=lambda s: s.water_lifted_liters)


class TreadingExperienceManager:
    def __init__(self):
        self.physics = TreadingPhysics()
        self.leaderboard = TreadingLeaderboard()
        self.active_sessions: Dict[str, TreadingSession] = {}
        self._session_rpm: Dict[str, float] = {}

    def create_session(self, user_name: str, difficulty: int = 3) -> TreadingSession:
        session_id = str(uuid.uuid4())
        difficulty = max(1, min(5, difficulty))
        session = TreadingSession(
            session_id=session_id,
            user_name=user_name,
            start_time=datetime.now(),
            difficulty_level=difficulty,
        )
        self.active_sessions[session_id] = session
        self._session_rpm[session_id] = 0.0
        return session

    def update_session(self, session_id: str, pedal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session = self.active_sessions.get(session_id)
        if session is None:
            return None

        pedal_force = pedal_data.get("pedal_force", 50.0)
        pedal_cadence = pedal_data.get("pedal_cadence", 30.0)
        dt = pedal_data.get("dt", 0.1)

        elapsed = session.duration_seconds + dt
        current_rpm = self._session_rpm.get(session_id, 0.0)

        difficulty_mult = self.physics.get_difficulty_multiplier(session.difficulty_level)
        efficiency_factor = 1.0 / difficulty_mult
        adjusted_force = pedal_force * efficiency_factor
        adjusted_cadence = pedal_cadence * efficiency_factor

        state = self.physics.get_instantaneous_state(
            pedal_force=adjusted_force,
            pedal_cadence=adjusted_cadence,
            elapsed=elapsed,
            current_rpm=current_rpm,
            dt=dt,
        )

        session.duration_seconds = elapsed
        session.pedal_speed_rpm = state["wheel_rpm"]
        session.calories_burned += state["calorie_rate_kcal_min"] * (dt / 60.0)
        session.stroke_count += max(1, int(pedal_cadence * dt / 60))
        session.record_speed(state["wheel_rpm"])

        water_increment = self.physics.get_water_lifted(dt, state["power_w"])
        session.water_lifted_liters += water_increment

        self._session_rpm[session_id] = state["wheel_rpm"]

        return state

    def end_session(self, session_id: str) -> Optional[TreadingSession]:
        session = self.active_sessions.pop(session_id, None)
        if session is None:
            return None
        self._session_rpm.pop(session_id, None)
        session.finalize()
        self.leaderboard.add_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[TreadingSession]:
        return self.active_sessions.get(session_id)

    def get_leaderboard(self, metric: str = "water_lifted_liters", n: int = 10) -> List[TreadingSession]:
        return self.leaderboard.get_top_n(n, metric)
