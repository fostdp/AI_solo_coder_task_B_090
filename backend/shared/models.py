from typing import List, Dict, Optional
from pydantic import BaseModel, Field


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
    water_lift: Optional[float] = Field(None, description="提水量 L/min")
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
    crop_type: str = Field("general", description="作物类型")
    soil_type: str = Field("loam", description="土壤类型")
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
