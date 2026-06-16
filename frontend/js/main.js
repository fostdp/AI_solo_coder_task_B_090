import { DragonBoneWaterwheel3D } from './dragon_bone_waterwheel_3d.js';
import { EfficiencyPanel } from './efficiency_panel.js';

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
            });
        });
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
