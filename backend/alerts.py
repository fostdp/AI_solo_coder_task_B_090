"""
告警系统模块
检测链板断裂、效率过低、张力过载等异常，通过WebSocket推送
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Callable, Any
from enum import Enum
from collections import deque

from database import AlertRecord, InfluxDBManager, get_influxdb_manager


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType(Enum):
    CHAIN_BROKEN = "chain_broken"
    CHAIN_OVERLOAD = "chain_overload"
    LOW_EFFICIENCY = "low_efficiency"
    LOW_WATER_FLOW = "low_water_flow"
    EXCESSIVE_TORQUE = "excessive_torque"
    ABNORMAL_SPEED = "abnormal_speed"
    HIGH_WEAR = "high_wear"
    SENSOR_ANOMALY = "sensor_anomaly"


@dataclass
class AlertThresholds:
    max_chain_tension: float = 5000.0
    min_efficiency: float = 0.30
    min_water_lift: float = 10.0
    max_torque: float = 200.0
    min_rotational_speed: float = 1.0
    max_rotational_speed: float = 40.0
    chain_wear_warning: float = 0.7
    chain_wear_critical: float = 0.9
    consecutive_anomaly_count: int = 3
    efficiency_average_window: int = 5


@dataclass
class Alert:
    alert_id: str
    wheel_id: str
    alert_code: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: str
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "wheel_id": self.wheel_id,
            "alert_code": self.alert_code,
            "alert_type": self.alert_type.value,
            "alert_level": self.alert_level.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "metadata": self.metadata
        }


@dataclass
class WheelState:
    wheel_id: str
    recent_efficiencies: deque = field(default_factory=lambda: deque(maxlen=20))
    recent_tensions: deque = field(default_factory=lambda: deque(maxlen=20))
    consecutive_anomalies: int = 0
    last_alert_time: Dict[str, float] = field(default_factory=dict)
    active_alerts: Set[str] = field(default_factory=set)
    estimated_wear: float = 0.0

    def add_efficiency(self, eff: float):
        self.recent_efficiencies.append(eff)

    def add_tension(self, tension: float):
        self.recent_tensions.append(tension)

    def avg_efficiency(self, window: int = 5) -> float:
        if not self.recent_efficiencies:
            return 0.0
        data = list(self.recent_efficiencies)[-window:]
        return sum(data) / len(data)

    def avg_tension(self, window: int = 5) -> float:
        if not self.recent_tensions:
            return 0.0
        data = list(self.recent_tensions)[-window:]
        return sum(data) / len(data)


class AlertWebSocketManager:
    """管理WebSocket连接，推送告警"""

    def __init__(self):
        self._connections: Dict[str, Set[Any]] = {}
        self._broadcast_connections: Set[Any] = set()
        self._callbacks: List[Callable] = []

    async def connect(self, websocket: Any, wheel_id: Optional[str] = None):
        await websocket.accept()
        if wheel_id:
            if wheel_id not in self._connections:
                self._connections[wheel_id] = set()
            self._connections[wheel_id].add(websocket)
        else:
            self._broadcast_connections.add(websocket)
        return websocket

    def disconnect(self, websocket: Any, wheel_id: Optional[str] = None):
        if wheel_id and wheel_id in self._connections:
            self._connections[wheel_id].discard(websocket)
        self._broadcast_connections.discard(websocket)

    async def broadcast_alert(self, alert: Alert):
        message = json.dumps({
            "type": "alert",
            "data": alert.to_dict()
        }, ensure_ascii=False)

        targets = set()
        if alert.wheel_id in self._connections:
            targets.update(self._connections[alert.wheel_id])
        targets.update(self._broadcast_connections)

        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception:
                pass

        dead = set()
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self.disconnect(ws)
            if alert.wheel_id in self._connections:
                self._connections[alert.wheel_id].discard(ws)

    async def broadcast_data(self, wheel_id: str, data: Dict):
        message = json.dumps({
            "type": "sensor_data",
            "wheel_id": wheel_id,
            "data": data
        }, ensure_ascii=False)

        targets = set()
        if wheel_id in self._connections:
            targets.update(self._connections[wheel_id])
        targets.update(self._broadcast_connections)

        dead = set()
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self.disconnect(ws)

    def register_callback(self, callback: Callable[[Alert], None]):
        self._callbacks.append(callback)


class AlertManager:
    """告警检测与管理核心"""

    def __init__(
        self,
        thresholds: Optional[AlertThresholds] = None,
        db_manager: Optional[InfluxDBManager] = None
    ):
        self.thresholds = thresholds or AlertThresholds()
        self.db = db_manager or get_influxdb_manager()
        self.ws_manager = AlertWebSocketManager()
        self._wheel_states: Dict[str, WheelState] = {}
        self._alert_history: deque = deque(maxlen=500)
        self._alert_counter = 0
        self._cooldown_seconds = {
            AlertLevel.INFO: 60,
            AlertLevel.WARNING: 120,
            AlertLevel.CRITICAL: 30,
            AlertLevel.EMERGENCY: 10,
        }

    def _get_wheel_state(self, wheel_id: str) -> WheelState:
        if wheel_id not in self._wheel_states:
            self._wheel_states[wheel_id] = WheelState(wheel_id=wheel_id)
        return self._wheel_states[wheel_id]

    def _generate_alert_id(self) -> str:
        self._alert_counter += 1
        return f"ALT_{int(time.time() * 1000)}_{self._alert_counter:06d}"

    def _should_throttle(self, state: WheelState, alert_code: str, level: AlertLevel) -> bool:
        now = time.time()
        cooldown = self._cooldown_seconds.get(level, 60)
        last = state.last_alert_time.get(alert_code, 0)
        return (now - last) < cooldown

    def _record_alert_time(self, state: WheelState, alert_code: str):
        state.last_alert_time[alert_code] = time.time()

    async def process_sensor_data(self, data: Dict) -> List[Alert]:
        wheel_id = data.get("wheel_id")
        if not wheel_id:
            return []

        state = self._get_wheel_state(wheel_id)
        alerts: List[Alert] = []

        efficiency = float(data.get("efficiency", 0))
        chain_tension = float(data.get("chain_tension", 0))
        torque = float(data.get("torque", 0))
        water_lift = float(data.get("water_lift", 0))
        rotational_speed = float(data.get("rotational_speed", 0))
        anomaly = data.get("anomaly")

        state.add_efficiency(efficiency)
        state.add_tension(chain_tension)

        if efficiency < 0.1 and chain_tension < 50 and rotational_speed < 1:
            state.estimated_wear = min(1.0, state.estimated_wear + 0.001)
        elif efficiency < self.thresholds.min_efficiency:
            state.estimated_wear = min(1.0, state.estimated_wear + 0.0002)

        if anomaly and "CHAIN_BROKEN" in anomaly:
            alert = self._create_alert(
                state, AlertType.CHAIN_BROKEN, AlertLevel.EMERGENCY,
                value=rotational_speed,
                threshold=self.thresholds.min_rotational_speed,
                message=f"链板断裂检测！{anomaly}，请立即停机检修",
                metadata={"anomaly": anomaly}
            )
            if alert:
                alerts.append(alert)
                state.active_alerts.add(alert.alert_code)

        if chain_tension > self.thresholds.max_chain_tension:
            level = AlertLevel.CRITICAL if chain_tension > self.thresholds.max_chain_tension * 1.2 else AlertLevel.WARNING
            alert = self._create_alert(
                state, AlertType.CHAIN_OVERLOAD, level,
                value=chain_tension,
                threshold=self.thresholds.max_chain_tension,
                message=f"链张力过载: {chain_tension:.0f}N > {self.thresholds.max_chain_tension:.0f}N，{('严重超限' if level == AlertLevel.CRITICAL else '请降低负载')}",
                metadata={"avg_tension_5min": state.avg_tension()}
            )
            if alert:
                alerts.append(alert)

        avg_eff = state.avg_efficiency(self.thresholds.efficiency_average_window)
        if avg_eff < self.thresholds.min_efficiency and rotational_speed > 2:
            level = AlertLevel.CRITICAL if avg_eff < self.thresholds.min_efficiency * 0.5 else AlertLevel.WARNING
            alert = self._create_alert(
                state, AlertType.LOW_EFFICIENCY, level,
                value=avg_eff,
                threshold=self.thresholds.min_efficiency,
                message=f"效率过低: {avg_eff:.1%} < {self.thresholds.min_efficiency:.0%}，可能存在磨损或调平问题",
                metadata={"current_efficiency": efficiency, "window_size": self.thresholds.efficiency_average_window}
            )
            if alert:
                alerts.append(alert)

        if water_lift < self.thresholds.min_water_lift and rotational_speed > 3:
            alert = self._create_alert(
                state, AlertType.LOW_WATER_FLOW, AlertLevel.WARNING,
                value=water_lift,
                threshold=self.thresholds.min_water_lift,
                message=f"提水量异常偏低: {water_lift:.1f}L/min，检查水源或刮水板磨损",
                metadata={"rotational_speed": rotational_speed}
            )
            if alert:
                alerts.append(alert)

        if torque > self.thresholds.max_torque:
            level = AlertLevel.CRITICAL if torque > self.thresholds.max_torque * 1.3 else AlertLevel.WARNING
            alert = self._create_alert(
                state, AlertType.EXCESSIVE_TORQUE, level,
                value=torque,
                threshold=self.thresholds.max_torque,
                message=f"扭矩过大: {torque:.1f}N·m，检查是否卡滞或过载",
                metadata={"drive_torque": data.get("drive_torque", 0)}
            )
            if alert:
                alerts.append(alert)

        if rotational_speed < self.thresholds.min_rotational_speed and torque > 5:
            alert = self._create_alert(
                state, AlertType.ABNORMAL_SPEED, AlertLevel.WARNING,
                value=rotational_speed,
                threshold=self.thresholds.min_rotational_speed,
                message=f"转速过低: {rotational_speed:.1f}rpm，检查动力传递系统",
                metadata={"torque": torque}
            )
            if alert:
                alerts.append(alert)

        if rotational_speed > self.thresholds.max_rotational_speed:
            alert = self._create_alert(
                state, AlertType.ABNORMAL_SPEED, AlertLevel.CRITICAL,
                value=rotational_speed,
                threshold=self.thresholds.max_rotational_speed,
                message=f"转速过高: {rotational_speed:.1f}rpm，超速危险！请立即减速",
                metadata={"torque": torque}
            )
            if alert:
                alerts.append(alert)

        if state.estimated_wear > self.thresholds.chain_wear_warning:
            level = AlertLevel.CRITICAL if state.estimated_wear > self.thresholds.chain_wear_critical else AlertLevel.WARNING
            alert = self._create_alert(
                state, AlertType.HIGH_WEAR, level,
                value=state.estimated_wear,
                threshold=self.thresholds.chain_wear_warning,
                message=f"链条磨损严重: {state.estimated_wear:.1%}，{'建议立即更换' if level == AlertLevel.CRITICAL else '安排维护'}",
                metadata={"critical_threshold": self.thresholds.chain_wear_critical}
            )
            if alert:
                alerts.append(alert)

        if anomaly and not any(a.alert_type == AlertType.CHAIN_BROKEN for a in alerts):
            state.consecutive_anomalies += 1
            if state.consecutive_anomalies >= self.thresholds.consecutive_anomaly_count:
                alert = self._create_alert(
                    state, AlertType.SENSOR_ANOMALY, AlertLevel.INFO,
                    value=state.consecutive_anomalies,
                    threshold=self.thresholds.consecutive_anomaly_count,
                    message=f"连续检测到数据异常: {anomaly}",
                    metadata={"raw_anomaly": anomaly, "consecutive_count": state.consecutive_anomalies}
                )
                if alert:
                    alerts.append(alert)
        else:
            state.consecutive_anomalies = max(0, state.consecutive_anomalies - 1)

        for alert in alerts:
            self._persist_alert(alert)
            self._alert_history.append(alert)
            try:
                await self.ws_manager.broadcast_alert(alert)
            except Exception:
                pass

        return alerts

    def _create_alert(
        self,
        state: WheelState,
        alert_type: AlertType,
        alert_level: AlertLevel,
        value: float,
        threshold: float,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Optional[Alert]:
        alert_code = f"{alert_type.value.upper()}_{state.wheel_id}"

        if self._should_throttle(state, alert_code, alert_level):
            return None

        self._record_alert_time(state, alert_code)

        alert = Alert(
            alert_id=self._generate_alert_id(),
            wheel_id=state.wheel_id,
            alert_code=alert_code,
            alert_type=alert_type,
            alert_level=alert_level,
            message=message,
            value=round(float(value), 3),
            threshold=round(float(threshold), 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {}
        )

        state.active_alerts.add(alert_code)

        return alert

    def _persist_alert(self, alert: Alert):
        try:
            record = AlertRecord(
                wheel_id=alert.wheel_id,
                alert_code=alert.alert_code,
                alert_type=alert.alert_type.value,
                alert_level=alert.alert_level.value,
                message=alert.message,
                value=alert.value,
                threshold=alert.threshold,
                timestamp=alert.timestamp
            )
            self.db.write_alert(record)
        except Exception as e:
            print(f"告警持久化失败: {e}")

    def get_active_alerts(self, wheel_id: Optional[str] = None) -> List[Alert]:
        if wheel_id:
            state = self._get_wheel_state(wheel_id)
            return [a for a in self._alert_history
                    if a.wheel_id == wheel_id and
                    a.alert_code in state.active_alerts and
                    not a.resolved]
        return [a for a in self._alert_history if not a.resolved]

    def get_alert_history(
        self,
        wheel_id: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        result = list(self._alert_history)
        if wheel_id:
            result = [a for a in result if a.wheel_id == wheel_id]
        if level:
            result = [a for a in result if a.alert_level == level]
        return result[-limit:]

    def acknowledge_alert(self, alert_id: str, wheel_id: Optional[str] = None) -> bool:
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def resolve_alert(self, alert_id: str, wheel_id: Optional[str] = None) -> bool:
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.resolved = True
                if wheel_id and wheel_id in self._wheel_states:
                    self._wheel_states[wheel_id].active_alerts.discard(alert.alert_code)
                return True
        return False

    def get_wheel_state(self, wheel_id: str) -> Dict:
        state = self._get_wheel_state(wheel_id)
        return {
            "wheel_id": wheel_id,
            "estimated_wear": round(state.estimated_wear, 4),
            "avg_efficiency_5pt": round(state.avg_efficiency(5), 4),
            "avg_tension_5pt": round(state.avg_tension(5), 2),
            "consecutive_anomalies": state.consecutive_anomalies,
            "active_alert_count": len(state.active_alerts),
            "active_alerts": list(state.active_alerts)
        }

    def update_thresholds(self, new_thresholds: AlertThresholds):
        self.thresholds = new_thresholds


_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
