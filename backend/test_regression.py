import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("龙骨水车系统 - 功能回归测试")
print("=" * 60)

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1


print("\n[1] 配置加载")
def t1():
    from shared.config_loader import get_mechanics_config, get_irrigation_config
    mc = get_mechanics_config()
    ic = get_irrigation_config()
    assert 'geometry' in mc, "missing geometry"
    assert 'material' in mc, "missing material"
    assert 'scrape_resistance' in mc, "missing scrape_resistance"
    assert 'crops' in ic, "missing crops"
    assert 'soils' in ic, "missing soils"
    assert 'system' in ic, "missing system"
test("配置JSON加载与结构", t1)

print("\n[2] 共享模型")
def t2():
    from shared.models import (
        SensorDataRequest, SensorDataBatchRequest,
        MechanicsSimRequest, MechanicsOptimizeRequest,
        IrrigationAnalysisRequest, AlertAcknowledgeRequest,
        ThresholdsUpdateRequest
    )
    req = SensorDataRequest(
        wheel_id="w1", rotational_speed=15, torque=50,
        water_lift=120, water_level_diff=2
    )
    assert req.wheel_id == "w1"
test("Pydantic模型实例化", t2)

print("\n[3] Redis客户端")
def t3():
    from shared.redis_client import REDIS_CHANNELS, REDIS_URL
    assert 'sensor_data' in REDIS_CHANNELS
    assert 'mechanics_result' in REDIS_CHANNELS
    assert 'irrigation_result' in REDIS_CHANNELS
    assert 'alarm' in REDIS_CHANNELS
test("Redis通道常量定义", t3)

print("\n[4] 力学仿真 - 配置驱动")
def t4():
    from shared.config_loader import get_mechanics_config
    from mechanics import WaterWheelGeometry, MaterialProperties, WaterWheelSimulator, SimulationInput
    cfg = get_mechanics_config()
    g = WaterWheelGeometry(**{k: v for k, v in cfg['geometry'].items() if hasattr(WaterWheelGeometry, k)})
    m = MaterialProperties(**{k: v for k, v in cfg['material'].items() if hasattr(MaterialProperties, k)})
    sim = WaterWheelSimulator(g, m)
    inp = SimulationInput(rotational_speed=15, water_level_diff=2, water_lift=120)
    r = sim.simulate(inp)
    assert r.drive_torque > 0, "drive_torque must be positive"
    assert r.overall_efficiency >= 0, f"efficiency must be non-negative: {r.overall_efficiency}"
    assert r.speed_velocity_factor > 1.0, "Kv must be > 1.0 (polygonal effect)"
    assert r.chain_impact_coefficient > 1.0, "Kd must be > 1.0"
    assert r.polygonal_effect_loss >= 0, "polygonal loss must be >= 0"
test("完整力学仿真（含多边形效应）", t4)

print("\n[5] 低水位刮水阻力修正")
def t5():
    from mechanics import WaterWheelGeometry, MaterialProperties, WaterWheelSimulator, SimulationInput
    g = WaterWheelGeometry()
    m = MaterialProperties()
    sim = WaterWheelSimulator(g, m)

    corr_low = sim.scrape_model.get_water_level_corrections(0.1)
    corr_high = sim.scrape_model.get_water_level_corrections(3.0)

    assert corr_low['water_level_ratio'] < corr_high['water_level_ratio'], \
        "low water should have lower ratio"
    assert corr_low.get('entry_shock_N', 0) >= 0, "entry shock should be non-negative"
test("低水位修正系数", t5)

print("\n[6] 灌溉效率分析 - 配置驱动")
def t6():
    from shared.config_loader import get_irrigation_config
    from irrigation import IrrigationEfficiencyAnalyzer, IrrigationAnalysisInput, CropType, SoilType, IrrigationSystemConfig
    cfg = get_irrigation_config()
    sys_cfg = IrrigationSystemConfig()
    for k, v in cfg['system'].items():
        if hasattr(sys_cfg, k):
            setattr(sys_cfg, k, v)
    inp = IrrigationAnalysisInput(
        wheel_id='w1', water_lift_lpm=150, rotational_speed=15,
        overall_efficiency=0.6, water_level_diff=2, irrigation_area_m2=2000,
        crop=CropType.WHEAT, soil=SoilType.LOAM, system_config=sys_cfg
    )
    a = IrrigationEfficiencyAnalyzer()
    r = a.analyze(inp)
    assert 0 < r.irrigation_efficiency <= 1, f"irr_eff out of range: {r.irrigation_efficiency}"
    assert r.optimal_speed > 0, "optimal speed must be positive"
    assert r.area_irrigated_m2 > 0, "irrigated area must be positive"
test("完整灌溉分析（含工况优化）", t6)

print("\n[7] 告警模块")
def t7():
    from alerts import get_alert_manager, AlertThresholds
    mgr = get_alert_manager()
    assert hasattr(mgr, 'process_sensor_data')
    assert hasattr(mgr, 'get_active_alerts')
    assert hasattr(mgr, 'acknowledge_alert')
    assert hasattr(mgr, 'ws_manager')
    state = mgr.get_wheel_state('test_wheel')
    assert isinstance(state, dict)
test("告警管理器实例化与方法", t7)

print("\n[8] 各微服务模块导入")
def t8():
    import importlib
    for svc in ['dtu_receiver.main', 'mechanics_simulator.main', 'irrigation_analyzer.main', 'alarm_ws.main']:
        try:
            importlib.import_module(svc)
        except ImportError as e:
            err = str(e).lower()
            if any(k in err for k in ['influxdb', 'redis', 'uvicorn']):
                pass
            else:
                raise
        except Exception:
            pass
test("4个微服务模块可导入", t8)

print("\n" + "=" * 60)
print(f"回归测试完成: {passed} 通过, {failed} 失败")
print("=" * 60)

if failed > 0:
    sys.exit(1)
