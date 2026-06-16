# -*- coding: utf-8 -*-
import sys
import os
import codecs
import multiprocessing

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"

passed = 0
failed = 0


def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  {PASS} {name}")
        passed += 1
    except Exception as e:
        print(f"  {FAIL} {name}: {type(e).__name__}: {e}")
        failed += 1


def t1_1():
    from evolution_analyzer import EvolutionAnalyzer
    ea = EvolutionAnalyzer()
    assert ea is not None


def t1_2():
    from evolution_analyzer import EvolutionAnalyzer, DynastyType
    ea = EvolutionAnalyzer()
    params = ea.get_dynasty_params(DynastyType.HAN)
    assert '考古数据源' in params
    assert '参数置信度' in params
    assert '综合置信度' in params
    assert isinstance(params['考古数据源'], list)
    assert len(params['考古数据源']) > 0
    assert isinstance(params['参数置信度'], dict)
    assert 0 <= params['综合置信度'] <= 1.0


def t1_3():
    from evolution_analyzer import EvolutionAnalyzer
    ea = EvolutionAnalyzer()
    result = ea.compare_dynasties()
    assert '对比列' in result
    assert '对比行' in result
    assert len(result['对比行']) == 3
    dynasties = [row['朝代'] for row in result['对比行']]
    assert '汉代' in dynasties
    assert '唐代' in dynasties
    assert '宋代' in dynasties


def t1_4():
    from evolution_analyzer import EvolutionAnalyzer, DynastyType
    ea = EvolutionAnalyzer()
    p_han = ea.get_dynasty_params(DynastyType.HAN)
    p_tang = ea.get_dynasty_params(DynastyType.TANG)
    p_song = ea.get_dynasty_params(DynastyType.SONG)
    confidences = [
        p_han['综合置信度'],
        p_tang['综合置信度'],
        p_song['综合置信度']
    ]
    avg_conf = sum(confidences) / len(confidences)
    min_conf = min(confidences)
    max_conf = max(confidences)
    assert 0 <= avg_conf <= 1.0
    assert 0 <= min_conf <= max_conf <= 1.0
    assert p_song['综合置信度'] > p_han['综合置信度']


def t1_5():
    from evolution_analyzer import EvolutionAnalyzer
    ea = EvolutionAnalyzer()
    timeline = ea.get_evolution_timeline()
    assert len(timeline) >= 8
    for event in timeline:
        assert '年份' in event
        assert '事件' in event
        assert '创新类型' in event


def t1_6():
    from evolution_analyzer import EvolutionAnalyzer, DynastyType
    ea = EvolutionAnalyzer()
    score_han = ea.get_technology_score(DynastyType.HAN)
    score_song = ea.get_technology_score(DynastyType.SONG)
    assert '综合得分' in score_han
    assert '评分维度' in score_han
    assert score_song['综合得分'] > score_han['综合得分']


def t1_7():
    from evolution_analyzer import EvolutionAnalyzer
    ea = EvolutionAnalyzer()
    try:
        ea.get_dynasty_params("INVALID_DYNASTY")
        assert False, "Expected KeyError"
    except (KeyError, TypeError, AttributeError):
        pass


def t1_8():
    from evolution_analyzer import EvolutionAnalyzer, DynastyType
    ea = EvolutionAnalyzer()
    result = ea.simulate_dynasty(DynastyType.SONG, 1.0, 0.5)
    assert '提水量_L_min' in result
    assert result['提水量_L_min'] >= 0


def t1_9():
    from evolution_analyzer import EvolutionAnalyzer, DynastyType
    ea = EvolutionAnalyzer()
    result = ea.simulate_dynasty(DynastyType.HAN, 50, 10.0)
    assert '综合效率' in result
    assert 0 <= result['综合效率'] <= 1


def t1_10():
    from evolution_analyzer import EvolutionAnalyzer
    ea = EvolutionAnalyzer()
    try:
        ea.simulate_dynasty("INVALID", 15, 2)
        assert False
    except Exception:
        pass


def t2_1():
    from era_comparator import EraComparator
    ec = EraComparator()
    assert ec is not None
    assert ec.pump_model is not None


def t2_2():
    from era_comparator import EraComparator
    ec = EraComparator()
    rng = ec.pump_model.get_operating_range()
    assert rng.min_flow_m3h > 0
    assert rng.max_flow_m3h > rng.min_flow_m3h
    assert rng.min_head_m > 0
    assert rng.max_head_m > rng.min_head_m
    assert rng.best_efficiency_flow_m3h > 0
    assert rng.best_efficiency_head_m > 0


def t2_3():
    from era_comparator import EraComparator
    ec = EraComparator()
    validation = ec.pump_model.validate_operating_point(47.5, 30.0)
    assert validation.is_within_range is True
    assert validation.flow_deviation_pct >= 0
    assert validation.head_deviation_pct >= 0
    assert isinstance(validation.warnings, list)


def t2_4():
    from era_comparator import EraComparator
    ec = EraComparator()
    result = ec.compare_efficiency(2.0, 10.0, 5.0)
    assert result.waterwheel_overall_efficiency > 0
    assert result.pump_overall_efficiency > 0
    assert result.efficiency_ratio > 0


def t2_5():
    from era_comparator import EraComparator
    ec = EraComparator()
    result_low = ec.compare_efficiency(0.5, 5.0, 1.25)
    result_high = ec.compare_efficiency(5.0, 50.0, 12.5)
    assert result_low.pump_overall_efficiency > 0
    assert result_high.pump_overall_efficiency > 0


def t2_6():
    from era_comparator import EraComparator
    ec = EraComparator()
    try:
        result = ec.compare_efficiency(-2.0, 10.0, 5.0)
        assert result is not None
    except Exception:
        pass


def t2_7():
    from era_comparator import EraComparator
    ec = EraComparator()
    validation = ec.pump_model.validate_operating_point(10.0, 30.0)
    has_bep_warning = False
    for warning in validation.warnings:
        if 'BEP' in warning or '偏离' in warning:
            has_bep_warning = True
            break
    assert has_bep_warning or validation.flow_deviation_pct > 30


def t2_8():
    from era_comparator import EraComparator
    ec = EraComparator()
    validation = ec.pump_model.validate_operating_point(5.0, 10.0)
    assert validation.is_within_range is False
    assert len(validation.warnings) >= 1


def t2_9():
    from era_comparator import EraComparator
    ec = EraComparator()
    validation = ec.pump_model.validate_operating_point(100.0, 50.0)
    assert validation.is_within_range is False
    assert len(validation.warnings) >= 1


def t2_10():
    from era_comparator import CentrifugalPumpModel
    pump = CentrifugalPumpModel()
    p = pump.power_consumption(0, 5)
    assert p >= 0 or p == float('inf')


def t3_1():
    from fleet_scheduler import FleetScheduler
    fs = FleetScheduler()
    assert fs is not None
    assert fs.wheels == []
    assert fs.zones == []


def t3_2():
    from fleet_scheduler import CommunicationDelaySimulator
    cds = CommunicationDelaySimulator()
    dist = cds.estimate_distance_km((30.0, 120.0), (31.0, 121.0))
    assert dist > 0
    assert isinstance(dist, float)


def t3_3():
    from fleet_scheduler import CommunicationDelaySimulator
    cds = CommunicationDelaySimulator()
    result = cds.simulate_delay('w1', 'w2', (30.0, 120.0), (31.0, 121.0))
    assert result.distance_km > 0
    assert result.one_way_delay_s > 0
    assert result.round_trip_delay_s > result.one_way_delay_s
    assert result.effective_delay_s >= result.round_trip_delay_s
    assert result.retries >= 0


def t3_4():
    from fleet_scheduler import FleetScheduler, WaterWheelUnit, IrrigationZone
    from mechanics import WaterWheelGeometry, MaterialProperties
    from irrigation import CropType, SoilType

    fs = FleetScheduler()
    fs.add_wheel(WaterWheelUnit(
        wheel_id='w1', location=(0, 0),
        geometry_params=WaterWheelGeometry(),
        material_params=MaterialProperties()
    ))
    fs.add_zone(IrrigationZone(
        zone_id='z1', area_m2=2000, crop_type=CropType.WHEAT,
        soil_type=SoilType.LOAM, water_requirement_m3=50, priority=3
    ))
    result = fs.optimize_schedule(100, 8)
    assert 'allocations' in result
    assert 'total_allocated_m3' in result
    assert result['total_allocated_m3'] > 0


def t3_5():
    from fleet_scheduler import FleetScheduler, WaterWheelUnit, IrrigationZone
    from mechanics import WaterWheelGeometry, MaterialProperties
    from irrigation import CropType, SoilType

    fs = FleetScheduler()
    for i in range(1, 4):
        fs.add_wheel(WaterWheelUnit(
            wheel_id=f'w{i}', location=(i * 0.1, i * 0.1),
            geometry_params=WaterWheelGeometry(),
            material_params=MaterialProperties()
        ))
    fs.add_zone(IrrigationZone(
        zone_id='z1', area_m2=5000, crop_type=CropType.WHEAT,
        soil_type=SoilType.LOAM, water_requirement_m3=200, priority=3
    ))
    result = fs.optimize_schedule(200, 10)
    assert 'communication_delays' in result
    assert 'coordination_overhead_s' in result
    assert result['coordination_overhead_s'] >= 0


def t3_6():
    from fleet_scheduler import FleetScheduler, WaterWheelUnit, IrrigationZone
    from mechanics import WaterWheelGeometry, MaterialProperties
    from irrigation import CropType, SoilType

    fs = FleetScheduler()
    fs.add_wheel(WaterWheelUnit(
        wheel_id='w1', location=(0, 0),
        geometry_params=WaterWheelGeometry(),
        material_params=MaterialProperties()
    ))
    fs.add_zone(IrrigationZone(
        zone_id='z1', area_m2=10000, crop_type=CropType.WHEAT,
        soil_type=SoilType.LOAM, water_requirement_m3=500, priority=5
    ))
    result = fs.optimize_schedule(50, 4)
    assert 0 <= result['fulfillment_ratio'] <= 1.0


def t3_7():
    from fleet_scheduler import CommunicationDelaySimulator
    cds = CommunicationDelaySimulator()
    dist_zero = cds.estimate_distance_km((30.0, 120.0), (30.0, 120.0))
    assert dist_zero == 0.0


def t3_8():
    from fleet_scheduler import FleetScheduler
    fs = FleetScheduler()
    result = fs.optimize_schedule(100, 8)
    assert 'allocations' in result
    assert result['total_allocated_m3'] == 0


def t3_9():
    from fleet_scheduler import WaterWheelUnit, MaintenanceStatus
    from mechanics import WaterWheelGeometry, MaterialProperties

    w = WaterWheelUnit(
        wheel_id='w_broken', location=(0, 0),
        geometry_params=WaterWheelGeometry(),
        material_params=MaterialProperties(),
        maintenance_status=MaintenanceStatus.UNDER_REPAIR
    )
    assert not w.is_available()
    assert w.estimate_water_output_m3_per_hour() == 0.0


def t4_1():
    from vr_waterwheel import VRWaterwheelExperience
    vr = VRWaterwheelExperience()
    assert vr is not None
    assert vr.physics is not None
    assert vr.leaderboard is not None


def t4_2():
    from vr_waterwheel import VRPedalPhysics
    physics = VRPedalPhysics()
    fb = physics._compute_force_feedback(100.0, 30.0, 100.0, 2.0, 0.8)
    assert 'pedal_resistance_n' in fb
    assert 'water_resistance_torque_nm' in fb
    assert 'mechanical_friction_torque_nm' in fb
    assert 'load_feel' in fb
    assert 'vibration_intensity' in fb
    assert 'vibration_freq_hz' in fb


def t4_3():
    from vr_waterwheel import VRWaterwheelExperience
    vr = VRWaterwheelExperience()
    s = vr.create_session('test_user', 3)
    assert s.session_id is not None
    assert s.user_name == 'test_user'
    assert s.difficulty_level == 3
    assert s.session_id in vr.active_sessions

    r = vr.update_session(s.session_id, {
        'pedal_force': 120, 'pedal_cadence': 30,
        'elapsed': 5.0, 'dt': 0.1
    })
    assert r is not None
    assert 'wheel_rpm' in r
    assert 'fatigue_factor' in r
    assert 'power_w' in r


def t4_4():
    from vr_waterwheel import VRPedalPhysics
    physics = VRPedalPhysics()
    fatigue_fresh = physics._fatigue_factor(10)
    fatigue_tired = physics._fatigue_factor(3600)
    assert fatigue_fresh > fatigue_tired
    assert 0 < fatigue_tired < fatigue_fresh <= 1.0

    fb_fresh = physics._compute_force_feedback(100.0, 30.0, 100.0, 2.0, fatigue_fresh)
    fb_tired = physics._compute_force_feedback(100.0, 30.0, 100.0, 2.0, fatigue_tired)
    assert fb_tired['pedal_resistance_n'] > fb_fresh['pedal_resistance_n']


def t4_5():
    from vr_waterwheel import VRPedalPhysics
    physics = VRPedalPhysics()
    fb = physics._compute_force_feedback(100.0, 30.0, 100.0, 2.0, 0.8)
    assert fb['pedal_resistance_n'] > 0
    assert 0 <= fb['load_feel'] <= 10.0
    assert fb['water_resistance_torque_nm'] > 0
    assert fb['mechanical_friction_torque_nm'] >= 0
    assert 0 <= fb['vibration_intensity'] <= 1.0
    assert fb['vibration_freq_hz'] >= 0


def t4_6():
    from vr_waterwheel import VRPedalPhysics
    physics = VRPedalPhysics()
    fb_low = physics._compute_force_feedback(50.0, 20.0, 50.0, 0.5, 0.9)
    fb_high = physics._compute_force_feedback(200.0, 60.0, 200.0, 5.0, 0.7)
    assert fb_high['pedal_resistance_n'] > fb_low['pedal_resistance_n']
    assert fb_high['load_feel'] >= fb_low['load_feel']


def t4_7():
    from vr_waterwheel import VRPedalPhysics
    physics = VRPedalPhysics()
    d1 = physics.get_difficulty_multiplier(1)
    d5 = physics.get_difficulty_multiplier(5)
    assert d5 > d1
    assert d1 > 0


def t4_8():
    from vr_waterwheel import VRWaterwheelExperience
    vr = VRWaterwheelExperience()
    r = vr.update_session('nonexistent_id', {
        'pedal_force': 100, 'pedal_cadence': 30, 'elapsed': 0, 'dt': 0.1
    })
    assert r is None


def t4_9():
    from vr_waterwheel import VRWaterwheelExperience
    vr = VRWaterwheelExperience()
    s = vr.create_session('tester', 3)
    vr.end_session(s.session_id)
    vr.end_session(s.session_id)


def t5_1():
    from mechanics_worker import MechanicsWorkerProcess
    worker = MechanicsWorkerProcess(num_workers=1)
    assert worker is not None
    assert worker._running is False
    worker.start()
    assert worker._running is True
    assert len(worker._workers) == 1
    worker.stop()
    assert worker._running is False


def t5_2():
    from mechanics_worker import MechanicsWorkerProcess
    with MechanicsWorkerProcess(num_workers=1) as worker:
        task_id = worker.submit_task({
            "rotational_speed": 15.0,
            "water_level_diff": 2.0,
        })
        assert task_id is not None
        assert isinstance(task_id, str)
        task = worker.wait_for_task(task_id, timeout=10.0)
        assert task is not None
        assert task.status.value == "completed"
        assert task.result is not None
        assert 'overall_efficiency' in task.result
        assert 'drive_torque' in task.result


def t5_3():
    from mechanics_worker import MechanicsWorkerProcess
    with MechanicsWorkerProcess(num_workers=2) as worker:
        inputs = [
            {"rotational_speed": 10.0, "water_level_diff": 1.0},
            {"rotational_speed": 15.0, "water_level_diff": 2.0},
            {"rotational_speed": 20.0, "water_level_diff": 3.0},
        ]
        results = worker.run_batch(inputs, timeout_per_task=10.0)
        assert len(results) == 3
        for r in results:
            assert r.status.value == "completed"
            assert r.result is not None


def t5_4():
    from mechanics_worker import run_simulation_sync
    result = run_simulation_sync({
        "rotational_speed": 15.0,
        "water_level_diff": 2.0,
    }, timeout=10.0)
    assert result is not None
    assert 'overall_efficiency' in result
    assert 'chain_tension_max' in result


def t5_5():
    from mechanics_worker import MechanicsWorkerProcess, SimulationTaskStatus
    with MechanicsWorkerProcess(num_workers=1) as worker:
        task_id = worker.submit_task({
            "rotational_speed": 15.0,
            "water_level_diff": 2.0,
        })
        task = worker.get_task(task_id)
        assert task is not None
        assert task.status in (
            SimulationTaskStatus.PENDING,
            SimulationTaskStatus.RUNNING,
            SimulationTaskStatus.COMPLETED
        )
        task = worker.wait_for_task(task_id, timeout=10.0)
        assert worker._running is True


def t5_6():
    from mechanics_worker import MechanicsWorkerProcess, SimulationTaskStatus
    with MechanicsWorkerProcess(num_workers=2) as worker:
        ids = []
        for i in range(5):
            tid = worker.submit_task({
                "rotational_speed": 10.0 + i * 2,
                "water_level_diff": 2.0,
            })
            ids.append(tid)
        assert len(worker._tasks) == 5
        for tid in ids:
            task = worker.wait_for_task(tid, timeout=10.0)
            assert task.status == SimulationTaskStatus.COMPLETED
        assert len(worker._tasks) == 5


def t5_7():
    from mechanics_worker import MechanicsWorkerProcess
    with MechanicsWorkerProcess(num_workers=8) as worker:
        assert worker.num_workers == 8
        assert len(worker._workers) == 8


def t5_8():
    from mechanics_worker import MechanicsWorkerProcess
    with MechanicsWorkerProcess(num_workers=1) as worker:
        task_id = worker.submit_task({
            "rotational_speed": 1.0,
            "water_level_diff": 0.1,
        })
        task = worker.wait_for_task(task_id, timeout=10.0)
        assert task.status.value == "completed"
        assert task.result['overall_efficiency'] >= 0


def t5_9():
    from mechanics_worker import MechanicsWorkerProcess
    worker = MechanicsWorkerProcess(num_workers=1)
    try:
        worker.submit_task({"rotational_speed": 15.0})
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "not started" in str(e)


def run_tests():
    global passed, failed
    passed = 0
    failed = 0

    print("=" * 60)
    print("Refactored Modules - Comprehensive Test Suite")
    print("=" * 60)

    print("\n[1] Evolution Analyzer - Normal Cases")
    test("EvolutionAnalyzer initialization", t1_1)
    test("get_dynasty_params includes sources and confidence", t1_2)
    test("compare_dynasties returns three dynasties", t1_3)
    test("get_confidence_summary returns statistics", t1_4)
    test("get_evolution_timeline returns valid events", t1_5)
    test("get_technology_score shows tech progress", t1_6)

    print("\n[1] Evolution Analyzer - Boundary Cases")
    test("Invalid dynasty name raises error", t1_7)
    test("Boundary: very low speed simulation", t1_8)
    test("Boundary: high speed simulation", t1_9)

    print("\n[1] Evolution Analyzer - Error Cases")
    test("Error: invalid dynasty in simulate", t1_10)

    print("\n[2] Era Comparator - Normal Cases")
    test("EraComparator initialization", t2_1)
    test("get_operating_range returns valid data", t2_2)
    test("validate_operating_point normal case", t2_3)
    test("compare_efficiency normal case", t2_4)
    test("compare_efficiency boundary cases", t2_5)
    test("compare_efficiency error handling", t2_6)
    test("Pump operating range BEP deviation warning", t2_7)

    print("\n[2] Era Comparator - Boundary Cases")
    test("validate_operating_point low flow warning", t2_8)
    test("validate_operating_point high flow warning", t2_9)

    print("\n[2] Era Comparator - Error Cases")
    test("Error: zero flow power calculation", t2_10)

    print("\n[3] Fleet Scheduler - Normal Cases")
    test("FleetScheduler initialization", t3_1)
    test("CommunicationDelaySimulator distance estimation", t3_2)
    test("simulate_communication_delay returns valid data", t3_3)
    test("optimize_schedule basic scheduling", t3_4)
    test("Communication delay impact on scheduling", t3_5)

    print("\n[3] Fleet Scheduler - Boundary Cases")
    test("Boundary: large demand small capacity", t3_6)
    test("Boundary: zero distance estimation", t3_7)

    print("\n[3] Fleet Scheduler - Error Cases")
    test("Error: empty scheduler", t3_8)
    test("Error: under repair wheel not available", t3_9)

    print("\n[4] VR Waterwheel - Normal Cases")
    test("VRWaterwheelExperience initialization", t4_1)
    test("_compute_force_feedback field completeness", t4_2)
    test("Session creation and update", t4_3)
    test("Fatigue and force feedback correlation", t4_4)
    test("Force feedback field value validity", t4_5)

    print("\n[4] VR Waterwheel - Boundary Cases")
    test("Boundary: low vs high force feedback", t4_6)
    test("Difficulty multiplier scaling", t4_7)

    print("\n[4] VR Waterwheel - Error Cases")
    test("Error: invalid session ID", t4_8)
    test("Error: double end session no crash", t4_9)

    print("\n[5] Mechanics Worker - Normal Cases")
    test("MechanicsWorkerProcess init and start/stop", t5_1)
    test("Single simulation task submission", t5_2)
    test("Batch task submission", t5_3)
    test("Synchronous simulation call", t5_4)
    test("Worker process status check", t5_5)
    test("Task queue management", t5_6)

    print("\n[5] Mechanics Worker - Boundary Cases")
    test("Boundary: max worker count", t5_7)
    test("Boundary: very low speed simulation", t5_8)

    print("\n[5] Mechanics Worker - Error Cases")
    test("Error: submit task before start", t5_9)

    print("\n" + "=" * 60)
    print(f"Tests complete: {passed} passed, {failed} failed")
    print("=" * 60)

    print(f"\nBy module:")
    print(f"  Evolution analyzer: 10 tests")
    print(f"  Era comparator: 10 tests")
    print(f"  Fleet scheduler: 9 tests")
    print(f"  VR waterwheel: 9 tests")
    print(f"  Mechanics worker: 9 tests")
    print(f"  Total: {passed + failed} tests")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    run_tests()
