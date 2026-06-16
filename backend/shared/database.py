"""
InfluxDB 数据库连接与操作模块
提供传感器数据存储、查询和聚合功能
"""
import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass

from influxdb_client import InfluxDBClient, Point, WritePrecision, QueryApi
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "agri-history")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "waterwheel_data")


@dataclass
class SensorRecord:
    wheel_id: str
    location: str
    timestamp: str
    rotational_speed: float
    torque: float
    water_lift: float
    water_level_diff: float
    chain_tension: float
    scrape_resistance: float
    drive_torque: float
    efficiency: float
    anomaly: Optional[str] = None

    def to_point(self) -> Point:
        point = Point("waterwheel_sensor") \
            .tag("wheel_id", self.wheel_id) \
            .tag("location", self.location) \
            .field("rotational_speed", float(self.rotational_speed)) \
            .field("torque", float(self.torque)) \
            .field("water_lift", float(self.water_lift)) \
            .field("water_level_diff", float(self.water_level_diff)) \
            .field("chain_tension", float(self.chain_tension)) \
            .field("scrape_resistance", float(self.scrape_resistance)) \
            .field("drive_torque", float(self.drive_torque)) \
            .field("efficiency", float(self.efficiency))

        if self.anomaly:
            point = point.tag("anomaly", self.anomaly[:50])
            point = point.field("has_anomaly", 1)
        else:
            point = point.field("has_anomaly", 0)

        try:
            dt = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            point = point.time(dt, WritePrecision.MS)
        except Exception:
            point = point.time(datetime.now(timezone.utc), WritePrecision.MS)

        return point


@dataclass
class AlertRecord:
    wheel_id: str
    alert_code: str
    alert_type: str
    alert_level: str
    message: str
    value: float
    threshold: float
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_point(self) -> Point:
        point = Point("waterwheel_alert") \
            .tag("wheel_id", self.wheel_id) \
            .tag("alert_code", self.alert_code) \
            .tag("alert_level", self.alert_level) \
            .tag("alert_type", self.alert_type) \
            .field("message", str(self.message)[:200]) \
            .field("value", float(self.value)) \
            .field("threshold", float(self.threshold))

        try:
            dt = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            point = point.time(dt, WritePrecision.MS)
        except Exception:
            point = point.time(datetime.now(timezone.utc), WritePrecision.MS)

        return point


@dataclass
class IrrigationAnalysisRecord:
    wheel_id: str
    timestamp: Optional[str] = None
    optimal_speed: float = 0.0
    irrigation_area: float = 0.0
    water_used: float = 0.0
    area_efficiency: float = 0.0
    analysis_result: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_point(self) -> Point:
        point = Point("irrigation_analysis") \
            .tag("wheel_id", self.wheel_id) \
            .field("optimal_speed", float(self.optimal_speed)) \
            .field("irrigation_area", float(self.irrigation_area)) \
            .field("water_used", float(self.water_used)) \
            .field("area_efficiency", float(self.area_efficiency))

        if self.analysis_result:
            point = point.field("analysis_json", str(self.analysis_result)[:5000])

        try:
            dt = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            point = point.time(dt, WritePrecision.MS)
        except Exception:
            point = point.time(datetime.now(timezone.utc), WritePrecision.MS)

        return point


class InfluxDBManager:
    """InfluxDB 管理器"""

    def __init__(
        self,
        url: str = INFLUXDB_URL,
        token: str = INFLUXDB_TOKEN,
        org: str = INFLUXDB_ORG,
        bucket: str = INFLUXDB_BUCKET
    ):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self._client: Optional[InfluxDBClient] = None
        self._write_api = None
        self._query_api: Optional[QueryApi] = None

    def connect(self) -> bool:
        try:
            self._client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30_000
            )
            health = self._client.health()
            if health.status == "pass":
                self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
                self._query_api = self._client.query_api()
                return True
            return False
        except Exception as e:
            print(f"InfluxDB 连接失败: {e}")
            return False

    def close(self):
        if self._write_api:
            self._write_api.close()
        if self._client:
            self._client.close()
            self._client = None

    def is_connected(self) -> bool:
        if not self._client:
            return False
        try:
            health = self._client.health()
            return health.status == "pass"
        except Exception:
            return False

    def write_sensor_record(self, record: SensorRecord) -> bool:
        try:
            self._ensure_connected()
            point = record.to_point()
            self._write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            print(f"写入传感器数据失败: {e}")
            return False

    def write_sensor_batch(self, records: List[SensorRecord]) -> bool:
        try:
            self._ensure_connected()
            points = [r.to_point() for r in records]
            self._write_api.write(bucket=self.bucket, org=self.org, record=points)
            return True
        except Exception as e:
            print(f"批量写入失败: {e}")
            return False

    def write_alert(self, alert: AlertRecord) -> bool:
        try:
            self._ensure_connected()
            point = alert.to_point()
            self._write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            print(f"写入告警失败: {e}")
            return False

    def write_irrigation_analysis(self, analysis: IrrigationAnalysisRecord) -> bool:
        try:
            self._ensure_connected()
            point = analysis.to_point()
            self._write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as e:
            print(f"写入灌溉分析失败: {e}")
            return False

    def query_sensor_data(
        self,
        wheel_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        aggregate: Optional[str] = None,
        aggregate_window: str = "1m"
    ) -> List[Dict]:
        start = start_time or f"-{limit}m"
        end = end_time or "now()"

        filter_parts = []
        if wheel_id:
            filter_parts.append(f'r["wheel_id"] == "{wheel_id}"')

        filter_str = " and ".join(filter_parts) if filter_parts else "true"

        if aggregate:
            agg_map = {
                "mean": "mean",
                "max": "max",
                "min": "min",
                "sum": "sum",
                "count": "count"
            }
            agg_fn = agg_map.get(aggregate, "mean")
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r["_measurement"] == "waterwheel_sensor")
              |> filter(fn: (r) => {filter_str})
              |> aggregateWindow(every: {aggregate_window}, fn: {agg_fn}, createEmpty: false)
              |> keep(columns: ["_time", "_field", "_value", "wheel_id", "location", "anomaly"])
              |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> limit(n: {limit})
            '''
        else:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r["_measurement"] == "waterwheel_sensor")
              |> filter(fn: (r) => {filter_str})
              |> keep(columns: ["_time", "_field", "_value", "wheel_id", "location", "anomaly"])
              |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> sort(columns: ["_time"], desc: true)
              |> limit(n: {limit})
            '''

        return self._execute_query(query)

    def query_alerts(
        self,
        wheel_id: Optional[str] = None,
        alert_level: Optional[str] = None,
        start_time: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        start = start_time or "-24h"

        filter_parts = []
        if wheel_id:
            filter_parts.append(f'r["wheel_id"] == "{wheel_id}"')
        if alert_level:
            filter_parts.append(f'r["alert_level"] == "{alert_level}"')
        filter_str = " and ".join(filter_parts) if filter_parts else "true"

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "waterwheel_alert")
          |> filter(fn: (r) => {filter_str})
          |> keep(columns: ["_time", "_field", "_value", "wheel_id", "alert_code", "alert_level", "alert_type"])
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        return self._execute_query(query)

    def query_irrigation_analysis(
        self,
        wheel_id: Optional[str] = None,
        start_time: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        start = start_time or "-7d"
        filter_str = f'r["wheel_id"] == "{wheel_id}"' if wheel_id else "true"

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "irrigation_analysis")
          |> filter(fn: (r) => {filter_str})
          |> keep(columns: ["_time", "_field", "_value", "wheel_id"])
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        return self._execute_query(query)

    def query_statistics(
        self,
        wheel_id: str,
        hours: int = 24
    ) -> Dict:
        start = f"-{hours}h"

        query = f'''
        data = from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "waterwheel_sensor")
          |> filter(fn: (r) => r["wheel_id"] == "{wheel_id}")

        stats = data
          |> keep(columns: ["_field", "_value"])
          |> group(columns: ["_field"])
          |> reduce(
              fn: (r, accumulator) => ({{
                  count: accumulator.count + 1,
                  sum: accumulator.sum + r._value,
                  min: if accumulator.count == 0 then r._value else float(v: (accumulator.min < r._value and accumulator.min or r._value)),
                  max: if accumulator.count == 0 then r._value else float(v: (accumulator.max > r._value and accumulator.max or r._value))
              }}),
              identity: {{count: 0, sum: 0.0, min: 0.0, max: 0.0}}
          )
          |> map(fn: (r) => ({{
              _field: r._field,
              count: r.count,
              mean: r.sum / float(v: r.count),
              min: r.min,
              max: r.max
          }}))

        stats
        '''

        results = self._execute_query(query)
        stats_dict = {}
        for row in results:
            field = row.get("_field")
            if field:
                stats_dict[field] = {
                    "count": row.get("count", 0),
                    "mean": row.get("mean", 0),
                    "min": row.get("min", 0),
                    "max": row.get("max", 0)
                }

        anomaly_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "waterwheel_sensor")
          |> filter(fn: (r) => r["wheel_id"] == "{wheel_id}" and exists r.anomaly)
          |> count()
        '''
        anomaly_results = self._execute_query(anomaly_query)
        anomaly_count = sum(int(r.get("_value", 0)) for r in anomaly_results)

        alert_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "waterwheel_alert")
          |> filter(fn: (r) => r["wheel_id"] == "{wheel_id}")
          |> count(column: "_value")
        '''
        alert_results = self._execute_query(alert_query)
        alert_count = sum(int(r.get("count", 0)) for r in alert_results)

        return {
            "wheel_id": wheel_id,
            "period_hours": hours,
            "field_statistics": stats_dict,
            "anomaly_count": anomaly_count,
            "alert_count": alert_count
        }

    def list_wheel_ids(self) -> List[str]:
        query = f'''
        import "influxdata/influxdb/schema"
        schema.tagValues(
            bucket: "{self.bucket}",
            tag: "wheel_id",
            start: -30d
        )
        '''
        try:
            results = self._execute_query(query)
            return list(set(r.get("_value") for r in results if r.get("_value")))
        except Exception:
            return []

    def _ensure_connected(self):
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("无法连接到 InfluxDB")

    def _execute_query(self, query: str) -> List[Dict]:
        try:
            self._ensure_connected()
            if not self._query_api:
                return []
            tables = self._query_api.query(query=query, org=self.org)
            results = []
            for table in tables:
                for record in table.records:
                    row = {"_time": record.get_time().isoformat() if record.get_time() else None}
                    for key in record.values:
                        if not key.startswith("_") or key in ["_field", "_value", "_time"]:
                            row[key] = record.values[key]
                    results.append(row)
            return results
        except ApiException as e:
            print(f"InfluxDB API 错误: {e}")
            return []
        except Exception as e:
            print(f"查询执行失败: {e}")
            return []


_influxdb_manager: Optional[InfluxDBManager] = None


def get_influxdb_manager() -> InfluxDBManager:
    global _influxdb_manager
    if _influxdb_manager is None:
        _influxdb_manager = InfluxDBManager()
        _influxdb_manager.connect()
    return _influxdb_manager
