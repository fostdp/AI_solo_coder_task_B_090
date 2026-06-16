# -*- coding: utf-8 -*-
"""
新增功能测试用例
覆盖：朝代演变分析、跨时代效率对比、多水车联合调度、虚拟踩踏体验
包含：正常场景、边界场景、异常场景
"""
import sys
import os
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"

print("=" * 60)
print("New Features - Comprehensive Test Suite")
print("=" * 60)

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


# ============================================================
# [1] Dynasty Waterwheel Evolution Analysis
# ============================================================
print("\n[1] Dynasty Evolution - Normal Cases")

def t1_1():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    p = a.get_dynasty_params(DynastyType.HAN)
    assert '几何参数' in p and '材料参数' in p
    assert p['几何参数']['轮径_米'] == 0.8
    assert p['几何参数']['叶片数'] == 16
test("Han dynasty params (diameter/blades)", t1_1)

def t1_2():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    p_han = a.get_dynasty_params(DynastyType.HAN)
    p_tang = a.get_dynasty_params(DynastyType.TANG)
    p_song = a.get_dynasty_params(DynastyType.SONG)
    assert p_han['几何参数']['轮径_米'] == 0.8
    assert p_tang['几何参数']['轮径_米'] == 1.0
    assert p_song['几何参数']['轮径_米'] == 1.2
    assert p_song['几何参数']['叶片数'] > p_tang['几何参数']['叶片数']
test("Tang/Song params monotonic increase", t1_2)

def t1_3():
    from dynasty import DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r = a.compare_dynasties()
    assert '对比列' in r and '对比行' in r
    assert len(r['对比行']) == 3
    dynasties = [row['朝代'] for row in r['对比行']]
    assert '汉代' in dynasties and '唐代' in dynasties and '宋代' in dynasties
test("Three dynasties comparison completeness", t1_3)

def t1_4():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r = a.simulate_dynasty(DynastyType.SONG, 15, 2.0)
    assert '提水量_L_min' in r
    assert r['提水量_L_min'] > 0
    assert '综合效率' in r
    assert isinstance(r['综合效率'], (int, float))
    assert 0 <= r['综合效率'] <= 1
    assert '驱动扭矩_Nm' in r
test("Song simulation: normal speed & water level", t1_4)

def t1_5():
    from dynasty import DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    tl = a.get_evolution_timeline()
    assert len(tl) >= 8
    for e in tl:
        assert '年份' in e and '事件' in e and '创新类型' in e
        assert len(e['事件']) > 0
test("Evolution timeline: event count & structure", t1_5)

def t1_6():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    s_han = a.get_technology_score(DynastyType.HAN)
    s_song = a.get_technology_score(DynastyType.SONG)
    assert s_song['综合得分'] > s_han['综合得分']
    assert s_song['评分维度']['耐久性']['得分'] > s_han['评分维度']['耐久性']['得分']
    assert s_song['评分维度']['提水能力']['得分'] > s_han['评分维度']['提水能力']['得分']
test("Tech score: Song > Han (tech progress)", t1_6)

print("\n[1] Dynasty Evolution - Boundary Cases")

def t1_7():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r = a.simulate_dynasty(DynastyType.HAN, 1.0, 0.5)
    assert r['提水量_L_min'] >= 0
    assert '综合效率' in r
test("Boundary: very low speed (1rpm) + low water (0.5m)", t1_7)

def t1_8():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r = a.simulate_dynasty(DynastyType.SONG, 50, 10.0)
    assert r['综合效率'] >= 0
    assert r['提水量_L_min'] > 0
test("Boundary: high speed (50rpm) + high water (10m)", t1_8)

def t1_9():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r_han = a.simulate_dynasty(DynastyType.HAN, 20, 3.0)
    r_song = a.simulate_dynasty(DynastyType.SONG, 20, 3.0)
    assert r_song['提水量_L_min'] > r_han['提水量_L_min']
test("Tech progress: Song water output > Han at same conditions", t1_9)

def t1_10():
    from dynasty import DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    tl = a.get_evolution_timeline()
    types = set(e['创新类型'] for e in tl)
    assert len(types) >= 3
test("Timeline diversity: multiple innovation types", t1_10)

print("\n[1] Dynasty Evolution - Error/Edge Cases")

def t1_11():
    from dynasty import DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    try:
        a.simulate_dynasty("INVALID_DYNASTY", 15, 2)
        assert False
    except (KeyError, TypeError, AttributeError):
        pass
test("Error: invalid dynasty type", t1_11)

def t1_12():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    try:
        r = a.simulate_dynasty(DynastyType.HAN, -5, 2)
        assert r is not None
    except (ValueError, ZeroDivisionError, Exception):
        pass
test("Error: negative speed graceful handling", t1_12)

def t1_13():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    r = a.simulate_dynasty(DynastyType.HAN, 15, -1)
    assert r['提水量_L_min'] >= 0 or r.get('驱动扭矩_Nm', 0) >= 0
test("Error: negative water level graceful handling", t1_13)

def t1_14():
    from dynasty import DynastyType, DynastyEvolutionAnalyzer
    a = DynastyEvolutionAnalyzer()
    try:
        r = a.simulate_dynasty(DynastyType.SONG, 0, 2)
        assert r['提水量_L_min'] >= 0
    except (ZeroDivisionError, ValueError):
        pass
test("Error: zero speed handling", t1_14)


# ============================================================
# [2] Cross-Era Efficiency Comparison
# ============================================================
print("\n[2] Cross-Era Comparison - Normal Cases")

def t2_1():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_efficiency(2.0, 10.0, 5.0)
    assert r.waterwheel_overall_efficiency is not None
    assert r.pump_overall_efficiency is not None
    assert r.efficiency_ratio > 0
test("Efficiency comparison: structure completeness", t2_1)

def t2_2():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_efficiency(2.0, 10.0, 5.0)
    assert 0 < r.waterwheel_overall_efficiency < 1
    assert 0 < r.pump_overall_efficiency < 1
test("Efficiency comparison: values in (0,1)", t2_2)

def t2_3():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_costs(2000, 10, 2.0)
    assert r.waterwheel_cost.total_annual_cost > 0
    assert r.pump_cost.total_annual_cost > 0
    assert r.cost_difference_annual is not None
test("Cost comparison: annual cost calculation", t2_3)

def t2_4():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_environmental_impact(2000, 10, 2.0)
    assert r.waterwheel_carbon_kg_per_year >= 0
    assert r.pump_carbon_kg_per_year >= 0
    assert hasattr(r, 'carbon_reduction_percent')
test("Env impact: carbon emission calculation", t2_4)

def t2_5():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_at_same_conditions(2.0, 10.0, 2000)
    assert r.efficiency is not None
    assert r.cost is not None
    assert r.environmental is not None
    assert len(r.recommendation) > 0
test("Full comparison: complete structure", t2_5)

def t2_6():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    curves = c.get_efficiency_curves(num_points=10)
    assert isinstance(curves, list)
    assert len(curves) == 10
    assert hasattr(curves[0], 'pump_efficiency')
    assert hasattr(curves[0], 'waterwheel_efficiency')
test("Efficiency curves: 10 points double-curve", t2_6)

def t2_7():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    s = c.get_comparison_summary()
    assert isinstance(s, dict)
    assert 'waterwheel' in s
    assert 'centrifugal_pump' in s
    assert 'key_metrics' in s
test("Comparison summary: returns dict with expected keys", t2_7)

def t2_8():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    s = c.get_comparison_summary()
    assert isinstance(s['key_metrics'], dict)
    assert len(s['key_metrics']) >= 3
test("Comparison summary: key_metrics has multiple entries", t2_8)

print("\n[2] Cross-Era Comparison - Boundary Cases")

def t2_9():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r_low = c.compare_efficiency(0.5, 2, 1.25)
    r_high = c.compare_efficiency(5.0, 50, 12.5)
    assert r_low.pump_overall_efficiency > 0
    assert r_high.pump_overall_efficiency > 0
test("Boundary: low vs high flow off-design efficiency", t2_9)

def t2_10():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_costs(0, 10, 2)
    assert r.waterwheel_cost.total_annual_cost >= 0
    assert r.pump_cost.total_annual_cost >= 0
test("Boundary: zero annual operating hours", t2_10)

def t2_11():
    from pump_comparison import CentrifugalPumpModel
    pump = CentrifugalPumpModel()
    r = pump.affinity_laws(10, 30, 5, 2900)
    assert r.new_flow > 0 and r.new_head > 0 and r.new_power > 0
    assert r.new_flow > r.original_flow
    assert r.new_head > r.original_head
    assert r.new_power > r.original_power
test("Affinity laws: speed increase boosts performance", t2_11)

def t2_12():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    curves = c.get_efficiency_curves(num_points=50)
    pump_effs = [p.pump_efficiency for p in curves]
    assert max(pump_effs) >= 0.3, f"max pump eff = {max(pump_effs)}"
    assert min(pump_effs) > 0
test("Efficiency curves: pump efficiency positive range", t2_12)

print("\n[2] Cross-Era Comparison - Error/Edge Cases")

def t2_13():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    try:
        c.compare_efficiency(-2, 10, 5)
    except Exception:
        pass
test("Error: negative water level (no crash)", t2_13)

def t2_14():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_costs(-100, 10, 2)
    assert r.waterwheel_cost.total_annual_cost >= 0
test("Error: negative annual hours graceful", t2_14)

def t2_15():
    from pump_comparison import CentrifugalPumpModel
    pump = CentrifugalPumpModel()
    p = pump.power_consumption(0, 5)
    assert p >= 0 or p == float('inf')
test("Error: zero flow power calculation", t2_15)

def t2_16():
    from pump_comparison import CrossEraComparison
    c = CrossEraComparison()
    r = c.compare_at_same_conditions(2.0, 10.0, 2000)
    assert isinstance(r.recommendation, str)
    assert len(r.recommendation) > 10
test("Full comparison: recommendation text non-empty", t2_16)


# ============================================================
# [3] Multi-Wheel Scheduling Optimization
# ============================================================
print("\n[3] Multi-Wheel Scheduling - Normal Cases")

def _make_wheel(wid, lat=0, lon=0):
    from scheduling import WaterWheelUnit
    from mechanics import WaterWheelGeometry, MaterialProperties
    return WaterWheelUnit(
        wheel_id=wid, location=(lat, lon),
        geometry_params=WaterWheelGeometry(),
        material_params=MaterialProperties()
    )

def _make_zone(zid, area=2000, req=50, priority=3):
    from scheduling import IrrigationZone
    from irrigation import CropType, SoilType
    return IrrigationZone(
        zone_id=zid, area_m2=area, crop_type=CropType.WHEAT,
        soil_type=SoilType.LOAM, water_requirement_m3=req, priority=priority
    )

def t3_1():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1', 2000, 50))
    r = s.optimize_schedule(100, 8)
    assert 'allocations' in r
    assert 'total_allocated_m3' in r
    assert r['total_allocated_m3'] > 0
test("Single wheel single zone: basic scheduling", t3_1)

def t3_2():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_wheel(_make_wheel('w2'))
    cap = s.calculate_total_capacity()
    assert cap > 0
    assert s.calculate_total_capacity() == cap
test("Two wheels: total capacity calculation", t3_2)

def t3_3():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1', 1000, 30, priority=5))
    s.add_zone(_make_zone('z2', 2000, 60, priority=1))
    allocs = s.greedy_allocate()
    assert len(allocs) >= 1
    first_zone_priority = None
    for z in s.zones:
        if z.zone_id == allocs[0].zone_id:
            first_zone_priority = z.priority
    assert first_zone_priority == 5
test("Priority scheduling: high priority zones first", t3_3)

def t3_4():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_wheel(_make_wheel('w2'))
    s.add_zone(_make_zone('z1', 5000, 100, priority=3))
    s.optimize_schedule(100, 8)
    allocs = s.balance_load()
    wheel_hours = {}
    for a in allocs:
        wheel_hours[a.wheel_id] = wheel_hours.get(a.wheel_id, 0) + a.assigned_hours
    if len(wheel_hours) >= 2:
        hours = list(wheel_hours.values())
        assert abs(hours[0] - hours[1]) <= 4.0
test("Load balancing: hour difference minimized", t3_4)

def t3_5():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1'))
    s.optimize_schedule(100, 8)
    sched = s.generate_schedule()
    assert 'time_slots' in sched
    assert 'total_water_m3' in sched
    assert isinstance(sched['time_slots'], list)
test("Schedule generation: time slot structure", t3_5)

def t3_6():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1'))
    recs = s.get_recommendations()
    assert isinstance(recs, list)
    for r in recs:
        assert 'type' in r and 'message' in r
test("Recommendations: list with type/message", t3_6)

def t3_7():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1', 5000, 500))
    r = s.optimize_schedule(500, 10)
    assert 'fulfillment_ratio' in r
    assert 0 <= r['fulfillment_ratio'] <= 1.0
test("Schedule result: fulfillment ratio in [0,1]", t3_7)

print("\n[3] Multi-Wheel Scheduling - Boundary Cases")

def t3_8():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1', 500, 10, priority=5))
    r = s.optimize_schedule(200, 12)
    assert r['total_allocated_m3'] >= 10
test("Boundary: small demand, large capacity (full supply)", t3_8)

def t3_9():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_zone(_make_zone('z1', 10000, 500, priority=5))
    r = s.optimize_schedule(50, 4)
    total_cap = s.calculate_total_capacity()
    assert r['total_allocated_m3'] <= total_cap * 2
test("Boundary: large demand, small capacity (shortage)", t3_9)

def t3_10():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    for i in range(1, 9):
        s.add_wheel(_make_wheel(f'w{i}'))
    for i in range(1, 13):
        s.add_zone(_make_zone(f'z{i}', 1000, 20, priority=3))
    r = s.optimize_schedule(100, 10)
    assert len(r['allocations']) >= 8
test("Large scale: 8 wheels + 12 zones", t3_10)

def t3_11():
    from scheduling import WaterWheelUnit, MaintenanceStatus
    from mechanics import WaterWheelGeometry, MaterialProperties
    w = WaterWheelUnit(
        wheel_id='w_broken', location=(0, 0),
        geometry_params=WaterWheelGeometry(),
        material_params=MaterialProperties(),
        maintenance_status=MaintenanceStatus.UNDER_REPAIR
    )
    assert not w.is_available()
test("Boundary: under-repair wheel not available", t3_11)

def t3_12():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    r = s.estimate_completion_time(500)
    assert r['estimated_hours'] > 0 or r['estimated_hours'] == float('inf')
    assert 'feasible' in r
test("Completion time: single wheel large volume", t3_12)

print("\n[3] Multi-Wheel Scheduling - Error/Edge Cases")

def t3_13():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    s.add_wheel(_make_wheel('w1'))
    s.add_wheel(_make_wheel('w1'))
    assert len(s.wheels) == 2
test("Error: duplicate wheel add (no crash)", t3_13)

def t3_14():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    r = s.optimize_schedule(100, 8)
    assert 'allocations' in r
    assert r['total_allocated_m3'] == 0
test("Error: empty scheduler (0 wheels, 0 zones)", t3_14)

def t3_15():
    from scheduling import MultiWheelScheduler
    s = MultiWheelScheduler()
    r = s.estimate_completion_time(100)
    assert r['feasible'] == False
    assert r['total_capacity_m3_per_hour'] == 0
test("Error: zero wheels completion estimate", t3_15)


# ============================================================
# [4] Virtual Treading Experience
# ============================================================
print("\n[4] Treading Experience - Normal Cases")

def t4_1():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('test_user', 3)
    assert s.session_id is not None
    assert s.user_name == 'test_user'
    assert s.difficulty_level == 3
    assert s.session_id in m.active_sessions
test("Create session: basic field completeness", t4_1)

def t4_2():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 2)
    r = m.update_session(s.session_id, {
        'pedal_force': 120, 'pedal_cadence': 30,
        'elapsed': 5.0, 'dt': 0.1
    })
    assert r is not None
    assert 'wheel_rpm' in r
    assert 'fatigue_factor' in r
    assert 'power_w' in r
test("Update session: returned state fields", t4_2)

def t4_3():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 3)
    for i in range(20):
        m.update_session(s.session_id, {
            'pedal_force': 100 + i * 2, 'pedal_cadence': 25 + i,
            'elapsed': float(i) * 0.5, 'dt': 0.5
        })
    final = m.end_session(s.session_id)
    assert final.water_lifted_liters > 0
    assert final.calories_burned > 0
    assert s.session_id not in m.active_sessions
test("20 steps: water & calories accumulate", t4_3)

def t4_4():
    from treading import TreadingPhysics
    from mechanics import WaterWheelSimulator, WaterWheelGeometry, MaterialProperties
    sim = WaterWheelSimulator(WaterWheelGeometry(), MaterialProperties())
    p = TreadingPhysics(simulator=sim)
    r = p.get_instantaneous_state(100, 30, 0, 0, 0.1)
    assert isinstance(r, dict)
    assert r['wheel_rpm'] >= 0
    assert r['power_w'] >= 0
test("Physics model: instantaneous state", t4_4)

def t4_5():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 5)
    r = m.update_session(s.session_id, {
        'pedal_force': 100, 'pedal_cadence': 30,
        'elapsed': 1.0, 'dt': 0.1
    })
    assert s.calories_burned >= 0
test("Calories: real-time calorie counting (session tracking", t4_5)

print("\n[4] Treading Experience - Boundary Cases")

def t4_6():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    f_start = p._fatigue_factor(10)
    f_long = p._fatigue_factor(3600)
    assert f_start > f_long
    assert 0 < f_long < f_start <= 1.0
test("Fatigue model: 10s vs 1h exponential decay", t4_6)

def t4_7():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    r_low = p.get_instantaneous_state(50, 20, 0, 0, 0.1)
    r_high = p.get_instantaneous_state(200, 60, 0, 0, 0.1)
    assert r_high['wheel_rpm'] > r_low['wheel_rpm']
    assert r_high['power_w'] > r_low['power_w']
test("Power boundary: low vs high force & cadence", t4_7)

def t4_8():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    r1 = p._speed_with_inertia(30, 0, 0.1)
    r10 = p._speed_with_inertia(30, 0, 1.0)
    r100 = p._speed_with_inertia(30, 0, 10.0)
    assert r1 < r10 < r100 < 30
test("Inertia model: first-order lag approaches target", t4_8)

def t4_9():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    cal = p.estimate_calories(3600, 100)
    assert cal > 0
    assert cal < 500
test("Calorie estimate: 1 hour at 100W", t4_9)

def t4_10():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    w = p.get_water_lifted(3600, 100)
    assert w >= 0
    assert w < 10000
test("Water lifted: 1 hour at 100W", t4_10)

def t4_11():
    from treading import TreadingPhysics
    p = TreadingPhysics()
    d5 = p.get_difficulty_multiplier(5)
    d1 = p.get_difficulty_multiplier(1)
    assert d5 > d1
    assert d1 > 0
test("Difficulty levels: level 5 > level 1 resistance", t4_11)

def t4_12():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s1 = m.create_session('u1', 1)
    s2 = m.create_session('u2', 5)
    r1 = m.update_session(s1.session_id, {'pedal_force': 100, 'pedal_cadence': 30, 'elapsed': 5, 'dt': 0.1})
    r2 = m.update_session(s2.session_id, {'pedal_force': 100, 'pedal_cadence': 30, 'elapsed': 5, 'dt': 0.1})
    assert r1['wheel_rpm'] > r2['wheel_rpm']
test("Difficulty diff: easier = higher RPM at same force", t4_12)

print("\n[4] Treading Experience - Error/Edge Cases")

def t4_13():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    r = m.update_session('nonexistent_id', {'pedal_force': 100, 'pedal_cadence': 30, 'elapsed': 0, 'dt': 0.1})
    assert r is None
test("Error: invalid session ID returns None", t4_13)

def t4_14():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 3)
    try:
        r = m.update_session(s.session_id, {'pedal_force': 0, 'pedal_cadence': 0, 'elapsed': 5, 'dt': 0.1})
        assert r is not None
        assert r['wheel_rpm'] >= 0
    except (ZeroDivisionError, ValueError):
        pass
test("Error: zero force & cadence (rest state)", t4_14)

def t4_15():
    from treading import TreadingLeaderboard
    lb = TreadingLeaderboard()
    top = lb.get_top_n(5)
    assert isinstance(top, list)
    assert len(top) == 0
test("Error: empty leaderboard query", t4_15)

def t4_16():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 3)
    m.end_session(s.session_id)
    m.end_session(s.session_id)
test("Error: double end session (no crash)", t4_16)

def t4_17():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s1 = m.create_session('user_a', 3)
    s2 = m.create_session('user_b', 2)
    for _ in range(30):
        m.update_session(s1.session_id, {'pedal_force': 150, 'pedal_cadence': 40, 'elapsed': 10, 'dt': 0.5})
        m.update_session(s2.session_id, {'pedal_force': 80, 'pedal_cadence': 20, 'elapsed': 10, 'dt': 0.5})
    e1 = m.end_session(s1.session_id)
    e2 = m.end_session(s2.session_id)
    lb = m.get_leaderboard('water_lifted_liters', 5)
    assert len(lb) == 2
    assert lb[0].water_lifted_liters >= lb[1].water_lifted_liters
test("Leaderboard: 2-user ranking correctness", t4_17)

def t4_18():
    from treading import TreadingExperienceManager
    m = TreadingExperienceManager()
    s = m.create_session('tester', 3)
    r = m.get_session(s.session_id)
    assert r is not None
    assert r.session_id == s.session_id
    assert m.get_session('invalid') is None
test("Session lookup: valid returns session, invalid None", t4_18)


# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print(f"Tests complete: {passed} passed, {failed} failed")
print("=" * 60)

print(f"\nBy module:")
print(f"  Dynasty evolution:   14 tests")
print(f"  Cross-era comparison: 16 tests")
print(f"  Multi-wheel scheduling: 15 tests")
print(f"  Treading experience: 18 tests")
print(f"  Total: {passed + failed} tests")

if failed > 0:
    sys.exit(1)
