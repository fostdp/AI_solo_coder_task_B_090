import { DragonBoneWaterwheel3D } from './dragon_bone_waterwheel_3d.js';
import { EfficiencyPanel } from './efficiency_panel.js';
import { DynastyPanel } from './dynasty_panel.js';
import { PumpComparisonPanel } from './pump_comparison_panel.js';
import { SchedulingPanel } from './scheduling_panel.js';
import { TreadingExperience } from './treading_experience.js';

class WaterwheelDashboard {
    constructor() {
        this.SERVICES = {
            dtu: this._resolveServiceUrl(8001),
            mechanics: this._resolveServiceUrl(8002),
            irrigation: this._resolveServiceUrl(8003),
            alarm: this._resolveServiceUrl(8004),
        };
        this.WS_ALARM = this.SERVICES.alarm.replace('http', 'ws');
        this.WS_SENSOR = (wheelId) => this.SERVICES.alarm.replace('http', 'ws') + '/ws/sensor/' + wheelId;

        this.currentWheelId = 'han_dynasty_wheel_001';
        this.sensorData = {
            rotational_speed: 0,
            torque: 0,
            water_lift: 0,
            water_level_diff: 2,
            chain_tension: 0,
            scrape_resistance: 0,
            drive_torque: 0,
            efficiency: 0,
            anomaly: null
        };

        this.wsSensor = null;
        this.wsAlerts = null;

        this.wheel3D = null;
        this.panel = null;
        this.dynastyPanel = null;
        this.pumpPanel = null;
        this.schedulingPanel = null;
        this.treadingExp = null;

        this._dynastyLoaded = false;
        this._comparisonLoaded = false;
        this._schedulingLoaded = false;
        this._treadingLoaded = false;

        this.init();
    }

    _resolveServiceUrl(port) {
        const base = window.location.origin;
        if (window.location.port === '' || window.location.port === '3000' || window.location.port === '5000') {
            return `${window.location.protocol}//${window.location.hostname}:${port}`;
        }
        return base;
    }

    init() {
        this.panel = new EfficiencyPanel();
        this.wheel3D = new DragonBoneWaterwheel3D('waterwheel-canvas').init();
        this.dynastyPanel = new DynastyPanel();
        this.pumpPanel = new PumpComparisonPanel();
        this.schedulingPanel = new SchedulingPanel();
        this.treadingExp = new TreadingExperience(this.wheel3D);
        this.setupUI();
        this.setupTabs();
        this.setupControls();
        this.connectWebSockets();
        this.startClock();
        this.loadHistory();
    }

    setupUI() {
        ['ctrl-speed', 'ctrl-level', 'ctrl-wear'].forEach(id => {
            const el = document.getElementById(id);
            const valEl = document.getElementById(id + '-val');
            if (el && valEl) {
                el.addEventListener('input', () => {
                    if (id === 'ctrl-wear') {
                        valEl.textContent = el.value + '%';
                    } else {
                        valEl.textContent = parseFloat(el.value).toFixed(1);
                    }
                });
            }
        });

        document.getElementById('wheel-select')?.addEventListener('change', (e) => {
            this.currentWheelId = e.target.value;
            this.reconnectWebSockets();
            this.loadHistory();
        });
    }

    setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
                if (btn.dataset.tab === 'history') this.loadHistory();
                if (btn.dataset.tab === 'dynasty') this._initDynastyTab();
                if (btn.dataset.tab === 'comparison') this._initComparisonTab();
                if (btn.dataset.tab === 'scheduling') this._initSchedulingTab();
                if (btn.dataset.tab === 'treading') this._initTreadingTab();
            });
        });
    }

    async _initDynastyTab() {
        if (this._dynastyLoaded) return;
        this._dynastyLoaded = true;
        try {
            const data = await this.dynastyPanel.loadDynastyData();
            this.dynastyPanel.renderComparison(document.getElementById('dynasty-comparison'));
            const timeline = await this.dynastyPanel.loadTimeline();
            this.dynastyPanel.renderTimeline(document.getElementById('dynasty-timeline'));
            const scores = await this.dynastyPanel.loadScores();
            this.dynastyPanel.renderRadarChart('chart-dynasty-radar', scores);
            this.dynastyPanel.renderEvolutionChart('chart-dynasty-evolution');
        } catch (e) {
            console.error('朝代演变数据加载失败:', e);
        }
    }

    async _initComparisonTab() {
        if (this._comparisonLoaded) return;
        this._comparisonLoaded = true;
        try {
            const curves = await this.pumpPanel.loadEfficiencyCurves(5, 30);
            this.pumpPanel.renderEfficiencyChart('chart-comparison-efficiency', curves);
            const env = await this.pumpPanel.loadEnvironmentalImpact();
            this.pumpPanel.renderEnvironmentalCard(document.getElementById('comparison-environmental'), env);
            const summary = await this.pumpPanel.loadSummary();
            this.pumpPanel.renderSummaryCard(document.getElementById('comparison-summary'), summary);
        } catch (e) {
            console.error('跨时代对比数据加载失败:', e);
        }
    }

    async _initSchedulingTab() {
        if (this._schedulingLoaded) return;
        this._schedulingLoaded = true;
        try {
            const wheels = await this.schedulingPanel.loadWheelStatus();
            this.schedulingPanel.renderWheelCards(document.getElementById('scheduling-wheels'), wheels);
            const zones = await this.schedulingPanel.loadZoneList();
            this.schedulingPanel.renderZoneCards(document.getElementById('scheduling-zones'), zones);
        } catch (e) {
            console.error('调度数据加载失败:', e);
        }
    }

    _initTreadingTab() {
        if (this._treadingLoaded) return;
        this._treadingLoaded = true;
        this.treadingExp.renderControls(document.querySelector('.treading-controls-panel'));
        this.treadingExp.renderDashboard(document.getElementById('tread-dashboard'));
        this.treadingExp.loadLeaderboard('water_lifted_liters').then(data => {
            this.treadingExp.renderLeaderboard(document.getElementById('tread-leaderboard'), data);
        }).catch(() => {});
    }

    setupControls() {
        document.getElementById('btn-simulate')?.addEventListener('click', () => this.runMechanicsSimulation());
        document.getElementById('btn-analyze-irrigation')?.addEventListener('click', () => this.runIrrigationAnalysis());
        document.getElementById('btn-refresh-history')?.addEventListener('click', () => this.loadHistory());

        document.getElementById('btn-rotate-toggle')?.addEventListener('click', (e) => {
            const state = this.wheel3D.toggleAutoRotate();
            e.target.style.background = state ? 'rgba(6,182,212,0.3)' : '';
        });
        document.getElementById('btn-wireframe')?.addEventListener('click', (e) => {
            const state = this.wheel3D.toggleWireframe();
            e.target.style.background = state ? 'rgba(6,182,212,0.3)' : '';
        });
        document.getElementById('btn-reset-view')?.addEventListener('click', () => {
            this.wheel3D.resetView();
        });

        document.getElementById('btn-dynasty-simulate')?.addEventListener('click', () => this.runDynastySimulation());
        document.getElementById('btn-dynasty-compare')?.addEventListener('click', () => {
            this._dynastyLoaded = false;
            this._initDynastyTab();
        });

        document.getElementById('btn-comparison-full')?.addEventListener('click', () => this.runFullComparison());

        document.getElementById('btn-sched-add-wheel')?.addEventListener('click', () => this.addSchedulingWheel());
        document.getElementById('btn-sched-add-zone')?.addEventListener('click', () => this.addSchedulingZone());
        document.getElementById('btn-sched-optimize')?.addEventListener('click', () => this.runSchedulingOptimize());
        document.getElementById('btn-sched-reset')?.addEventListener('click', async () => {
            await this.schedulingPanel.resetScheduler();
            this._schedulingLoaded = false;
            this._initSchedulingTab();
        });

        document.getElementById('btn-tread-start')?.addEventListener('click', () => this.startTreading());
        document.getElementById('btn-tread-stop')?.addEventListener('click', () => this.stopTreading());
    }

    async runDynastySimulation() {
        const btn = document.getElementById('btn-dynasty-simulate');
        if (btn) { btn.textContent = '⏳ 仿真中...'; btn.disabled = true; }
        try {
            const dynasty = document.getElementById('dynasty-select')?.value || 'song';
            const speed = parseFloat(document.getElementById('dynasty-speed')?.value || 15);
            const level = parseFloat(document.getElementById('dynasty-level')?.value || 2);
            const result = await this.dynastyPanel.simulateDynasty(dynasty, speed, level);
            const panel = document.getElementById('dynasty-simulation-panel');
            if (panel) panel.style.display = '';
            this.dynastyPanel.renderSimulation(document.getElementById('dynasty-simulation-result'), result);
        } catch (e) {
            console.error('朝代仿真失败:', e);
        } finally {
            if (btn) { btn.textContent = '🏛️ 朝代仿真'; btn.disabled = false; }
        }
    }

    async runFullComparison() {
        const btn = document.getElementById('btn-comparison-full');
        if (btn) { btn.textContent = '⏳ 分析中...'; btn.disabled = true; }
        try {
            const waterLevel = parseFloat(document.getElementById('cmp-water-level')?.value || 2);
            const flowRate = parseFloat(document.getElementById('cmp-flow-rate')?.value || 10);
            const annualHours = parseFloat(document.getElementById('cmp-annual-hours')?.value || 2000);

            const fullResult = await this.pumpPanel.loadFullComparison(waterLevel, flowRate, annualHours);

            this.pumpPanel.renderEfficiencyRings(
                document.getElementById('comparison-efficiency-rings'),
                fullResult?.efficiency_comparison?.waterwheel_overall_efficiency || 0.4,
                fullResult?.efficiency_comparison?.pump_overall_efficiency || 0.69
            );

            const costData = await this.pumpPanel.loadCostComparison(annualHours, flowRate, waterLevel);
            this.pumpPanel.renderCostBreakdown('chart-comparison-cost', costData);
        } catch (e) {
            console.error('跨时代对比失败:', e);
        } finally {
            if (btn) { btn.textContent = '⚡ 综合对比分析'; btn.disabled = false; }
        }
    }

    async addSchedulingWheel() {
        const id = 'wheel_' + Date.now().toString(36);
        await this.schedulingPanel.addWheel({
            wheel_id: id,
            location_x: Math.random() * 100,
            location_y: Math.random() * 100,
            max_speed: 20 + Math.random() * 10,
            available_hours: 8 + Math.floor(Math.random() * 4)
        });
        const wheels = await this.schedulingPanel.loadWheelStatus();
        this.schedulingPanel.renderWheelCards(document.getElementById('scheduling-wheels'), wheels);
    }

    async addSchedulingZone() {
        const id = 'zone_' + Date.now().toString(36);
        const crops = ['wheat', 'rice', 'corn', 'vegetable'];
        const soils = ['loam', 'clay', 'sand', 'silt'];
        await this.schedulingPanel.addZone({
            zone_id: id,
            area_m2: 1000 + Math.random() * 4000,
            crop_type: crops[Math.floor(Math.random() * crops.length)],
            soil_type: soils[Math.floor(Math.random() * soils.length)],
            water_requirement_m3: 30 + Math.random() * 70,
            elevation_m: Math.random() * 10,
            distance_to_source_m: 50 + Math.random() * 200,
            priority: Math.floor(1 + Math.random() * 5)
        });
        const zones = await this.schedulingPanel.loadZoneList();
        this.schedulingPanel.renderZoneCards(document.getElementById('scheduling-zones'), zones);
    }

    async runSchedulingOptimize() {
        const btn = document.getElementById('btn-sched-optimize');
        if (btn) { btn.textContent = '⏳ 优化中...'; btn.disabled = true; }
        try {
            const result = await this.schedulingPanel.optimizeSchedule(100, 8);
            this.schedulingPanel.renderAllocationTable(document.getElementById('scheduling-allocations'), result?.allocations || []);

            const schedule = await this.schedulingPanel.loadSchedule();
            this.schedulingPanel.renderGanttChart('chart-scheduling-gantt', schedule);
            this.schedulingPanel.renderCapacityGauge(
                document.getElementById('scheduling-capacity'),
                schedule?.total_daily_capacity_m3 || 0,
                100
            );

            const recs = await this.schedulingPanel.loadRecommendations();
            this.schedulingPanel.renderRecommendations(document.getElementById('scheduling-recommendations'), recs);
        } catch (e) {
            console.error('调度优化失败:', e);
        } finally {
            if (btn) { btn.textContent = '🔄 优化调度'; btn.disabled = false; }
        }
    }

    async startTreading() {
        const userName = document.getElementById('tread-username')?.value || '体验者';
        const difficulty = parseInt(document.getElementById('tread-difficulty')?.value || '3');
        await this.treadingExp.startSession(userName, difficulty);
        this.treadingExp.startLocalSimulation();

        const dashboard = document.getElementById('tread-dashboard');
        const startBtn = document.getElementById('btn-tread-start');
        const stopBtn = document.getElementById('btn-tread-stop');
        const hint = document.getElementById('tread-hint');
        if (dashboard) dashboard.style.display = '';
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = '';
        if (hint) hint.style.display = '';

        this._treadDashboardInterval = setInterval(() => {
            const state = this.treadingExp.getCurrentState();
            if (!state) return;
            const cadenceEl = document.getElementById('tread-cadence');
            const speedEl = document.getElementById('tread-wheel-speed');
            const waterEl = document.getElementById('tread-water');
            const calEl = document.getElementById('tread-calories');
            const timeEl = document.getElementById('tread-elapsed');
            const fatEl = document.getElementById('tread-fatigue');
            if (cadenceEl) cadenceEl.textContent = Math.round(state.pedal_cadence || 0);
            if (speedEl) speedEl.textContent = (state.wheel_rpm || 0).toFixed(1);
            if (waterEl) waterEl.textContent = (state.water_lifted_liters || 0).toFixed(1);
            if (calEl) calEl.textContent = (state.calories_burned || 0).toFixed(1);
            if (timeEl) {
                const s = Math.floor(state.duration_seconds || 0);
                const m = Math.floor(s / 60);
                timeEl.textContent = `${m}:${(s % 60).toString().padStart(2, '0')}`;
            }
            if (fatEl) {
                const fatigue = Math.max(0, 1 - (state.fatigue_factor || 1));
                fatEl.style.width = (fatigue * 100) + '%';
            }
        }, 200);
    }

    async stopTreading() {
        this.treadingExp.stopLocalSimulation();
        if (this._treadDashboardInterval) {
            clearInterval(this._treadDashboardInterval);
            this._treadDashboardInterval = null;
        }
        const result = await this.treadingExp.endSession();

        const startBtn = document.getElementById('btn-tread-start');
        const stopBtn = document.getElementById('btn-tread-stop');
        if (startBtn) startBtn.style.display = '';
        if (stopBtn) stopBtn.style.display = 'none';

        if (result) {
            this.treadingExp.renderEndSummary(document.getElementById('tread-summary'), result);
            const summaryPanel = document.getElementById('tread-summary-panel');
            if (summaryPanel) summaryPanel.style.display = '';
        }

        this.treadingExp.loadLeaderboard('water_lifted_liters').then(data => {
            this.treadingExp.renderLeaderboard(document.getElementById('tread-leaderboard'), data);
        }).catch(() => {});
    }

    updateSensorDisplay(data) {
        Object.assign(this.sensorData, data);
        this.panel.updateSensorDisplay(data);
        this.wheel3D.updateSensorData(data);

        if (data.anomaly && data.anomaly.includes('CHAIN_BROKEN')) {
            const match = data.anomaly.match(/blade_(\d+)/);
            if (match) this.wheel3D.setBrokenBlade(parseInt(match[1]) % 24);
        }
    }

    connectWebSockets() {
        this.connectSensorWS();
        this.connectAlertsWS();
        this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
    }

    reconnectWebSockets() {
        try { this.wsSensor?.close(); } catch (e) {}
        try { this.wsAlerts?.close(); } catch (e) {}
        this.connectWebSockets();
    }

    connectSensorWS() {
        try {
            const url = this.WS_SENSOR(this.currentWheelId);
            this.wsSensor = new WebSocket(url);

            this.wsSensor.onopen = () => {
                console.log('传感器 WebSocket 已连接');
                this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
            };

            this.wsSensor.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'sensor_data' && msg.data) {
                        this.updateSensorDisplay(msg.data);
                    } else if (msg.data && msg.data.rotational_speed !== undefined) {
                        this.updateSensorDisplay(msg.data);
                    } else if (msg.type !== 'connection_established' && msg.type !== 'pong') {
                        if (msg.rotational_speed !== undefined) this.updateSensorDisplay(msg);
                    }
                } catch (e) {
                    console.warn('消息解析失败:', e);
                }
            };

            this.wsSensor.onerror = () => this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
            this.wsSensor.onclose = () => {
                this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
                setTimeout(() => this.connectSensorWS(), 3000);
            };
        } catch (e) {
            console.error('传感器 WebSocket 连接失败:', e);
        }
    }

    connectAlertsWS() {
        try {
            const url = `${this.WS_ALARM}/ws/alerts`;
            this.wsAlerts = new WebSocket(url);

            this.wsAlerts.onopen = () => {
                console.log('告警 WebSocket 已连接');
                this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
            };

            this.wsAlerts.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'alert' && msg.data) {
                        this.panel.addAlert(msg.data);
                    } else if (msg.type === 'connection_established' && msg.active_alerts) {
                        msg.active_alerts.forEach(a => this.panel.addAlert(a));
                    }
                } catch (e) {
                    console.warn('告警消息解析失败:', e);
                }
            };

            this.wsAlerts.onerror = () => this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
            this.wsAlerts.onclose = () => {
                this.panel.updateConnectionStatus(this.wsSensor, this.wsAlerts);
                setTimeout(() => this.connectAlertsWS(), 3000);
            };
        } catch (e) {
            console.error('告警 WebSocket 连接失败:', e);
        }
    }

    async runMechanicsSimulation() {
        const btn = document.getElementById('btn-simulate');
        if (btn) { btn.textContent = '⏳ 计算中...'; btn.disabled = true; }

        try {
            const payload = {
                rotational_speed: parseFloat(document.getElementById('ctrl-speed')?.value || 15),
                water_level_diff: parseFloat(document.getElementById('ctrl-level')?.value || 2),
                chain_wear_factor: parseFloat(document.getElementById('ctrl-wear')?.value || 10) / 100
            };

            const resp = await fetch(`${this.SERVICES.mechanics}/api/mechanics/simulate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();

            this.panel.displayMechanicsResult(result);

            this.updateSensorDisplay({
                rotational_speed: payload.rotational_speed,
                torque: result.output_torque_Nm || 0,
                water_lift: result.input?.water_lift || 0,
                water_level_diff: payload.water_level_diff,
                chain_tension: result.chain_tension_max_N || 0,
                scrape_resistance: (result.resistance_breakdown || {}).scrape_resistance_N || 0,
                drive_torque: result.drive_torque_Nm || 0,
                efficiency: result.overall_efficiency || 0
            });
        } catch (e) {
            console.error('仿真失败:', e);
            alert('力学仿真请求失败，请检查后端服务');
        } finally {
            if (btn) { btn.textContent = '🔬 运行力学仿真'; btn.disabled = false; }
        }
    }

    async runIrrigationAnalysis() {
        const btn = document.getElementById('btn-analyze-irrigation');
        if (btn) { btn.textContent = '⏳ 分析中...'; btn.disabled = true; }

        try {
            const payload = {
                wheel_id: this.currentWheelId,
                water_lift_lpm: this.sensorData.water_lift || 150,
                rotational_speed: this.sensorData.rotational_speed || parseFloat(document.getElementById('ctrl-speed')?.value || 15),
                overall_efficiency: this.sensorData.efficiency || 0.6,
                water_level_diff: this.sensorData.water_level_diff || parseFloat(document.getElementById('ctrl-level')?.value || 2),
                irrigation_area_m2: parseFloat(document.getElementById('irr-area')?.value || 2000),
                hours_operation: parseFloat(document.getElementById('irr-hours')?.value || 8),
                crop_type: document.getElementById('irr-crop')?.value || 'wheat',
                soil_type: document.getElementById('irr-soil')?.value || 'loam',
                weather_et0_mm_day: parseFloat(document.getElementById('irr-et0')?.value || 5),
                initial_soil_moisture_deficit: parseFloat(document.getElementById('irr-moisture')?.value || 0.3)
            };

            const resp = await fetch(`${this.SERVICES.irrigation}/api/irrigation/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();
            this.panel.displayIrrigationResult(result);
        } catch (e) {
            console.error('灌溉分析失败:', e);
            alert('灌溉效率分析请求失败，请检查后端服务');
        } finally {
            if (btn) { btn.textContent = '📊 分析灌溉效率'; btn.disabled = false; }
        }
    }

    async loadHistory() {
        const tbody = document.querySelector('#history-table tbody');
        const range = document.getElementById('hist-range')?.value || '-24h';
        const agg = document.getElementById('hist-agg')?.value || 'mean';

        try {
            const params = new URLSearchParams({
                wheel_id: this.currentWheelId,
                start_time: range,
                limit: 200
            });
            if (agg) {
                params.append('aggregate', agg);
                params.append('aggregate_window', '10m');
            }

            const resp = await fetch(`${this.SERVICES.dtu}/api/sensor/data?${params}`);
            const result = await resp.json();

            if (!result.data || result.data.length === 0) {
                if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="loading">暂无历史数据（请先启动传感器模拟器）</td></tr>';
                return;
            }

            const rows = result.data.slice(-100).map(r => {
                const time = r._time ? new Date(r._time).toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-';
                const anomaly = r.anomaly || r.has_anomaly ? (r.anomaly || '异常') : '';
                return `<tr><td>${time}</td><td>${(r.rotational_speed ?? 0).toFixed(1)}</td><td>${(r.torque ?? 0).toFixed(1)}</td><td>${(r.water_lift ?? 0).toFixed(1)}</td><td>${(r.water_level_diff ?? 0).toFixed(2)}</td><td>${r.efficiency !== undefined ? (r.efficiency * 100).toFixed(1) + '%' : '-'}</td><td class="${anomaly ? 'anomaly-cell' : 'no-anomaly'}">${anomaly || '正常'}</td></tr>`;
            }).join('');

            if (tbody) tbody.innerHTML = rows;
        } catch (e) {
            console.error('加载历史数据失败:', e);
            if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="loading">加载失败，请检查后端连接</td></tr>';
        }
    }

    startClock() {
        const update = () => {
            const el = document.getElementById('current-time');
            if (el) el.textContent = new Date().toLocaleString('zh-CN', { hour12: false });
        };
        update();
        setInterval(update, 1000);

        setInterval(() => {
            if (!this.wsSensor || this.wsSensor.readyState !== WebSocket.OPEN) {
                const speed = parseFloat(document.getElementById('ctrl-speed')?.value || 15);
                const wear = parseFloat(document.getElementById('ctrl-wear')?.value || 10) / 100;
                const noise = () => 0.95 + Math.random() * 0.1;
                this.updateSensorDisplay({
                    rotational_speed: speed * noise(),
                    torque: (50 + speed * 3) * noise(),
                    water_lift: (80 + speed * 7) * noise() * (1 - wear * 0.3),
                    water_level_diff: parseFloat(document.getElementById('ctrl-level')?.value || 2),
                    chain_tension: 1500 + speed * 100,
                    scrape_resistance: 80 + speed * 8,
                    drive_torque: (60 + speed * 3.5) * noise(),
                    efficiency: Math.max(0.1, 0.7 - Math.abs(speed - 15) * 0.01 - wear * 0.2)
                });
            }
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new WaterwheelDashboard();
});
