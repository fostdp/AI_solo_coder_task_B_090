import Chart from 'chart.js';

export class EfficiencyPanel {
    constructor() {
        this.charts = {};
        this.dataHistory = {
            speed: [],
            torque: [],
            water: [],
            efficiency: [],
            time: []
        };
        this.maxHistoryPoints = 60;
        this.activeAlerts = new Map();

        this.setupCharts();
    }

    setupCharts() {
        Chart.defaults.color = '#8899a8';
        Chart.defaults.borderColor = 'rgba(45, 66, 89, 0.5)';
        Chart.defaults.font.family = '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';

        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 35, 50, 0.95)',
                    borderColor: '#2d4259',
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 6, font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(45, 66, 89, 0.3)' },
                    ticks: { font: { size: 10 } }
                }
            },
            elements: {
                point: { radius: 0, hoverRadius: 4 },
                line: { tension: 0.35, borderWidth: 2 }
            }
        };

        const createAreaGradient = (ctx, color1, color2) => {
            const gradient = ctx.createLinearGradient(0, 0, 0, 150);
            gradient.addColorStop(0, color1);
            gradient.addColorStop(1, color2);
            return gradient;
        };

        const speedCtx = document.getElementById('chart-speed')?.getContext('2d');
        if (speedCtx) {
            this.charts.speed = new Chart(speedCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: (c) => createAreaGradient(c.chart.ctx, 'rgba(59,130,246,0.3)', 'rgba(59,130,246,0)'),
                        fill: true
                    }]
                },
                options: { ...baseOptions }
            });
        }

        const torqueCtx = document.getElementById('chart-torque')?.getContext('2d');
        if (torqueCtx) {
            this.charts.torque = new Chart(torqueCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: (c) => createAreaGradient(c.chart.ctx, 'rgba(139,92,246,0.3)', 'rgba(139,92,246,0)'),
                        fill: true
                    }]
                },
                options: { ...baseOptions }
            });
        }

        const effCtx = document.getElementById('chart-efficiency')?.getContext('2d');
        if (effCtx) {
            this.charts.efficiency = new Chart(effCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: '效率(%)',
                            data: [],
                            borderColor: '#10b981',
                            backgroundColor: (c) => createAreaGradient(c.chart.ctx, 'rgba(16,185,129,0.25)', 'rgba(16,185,129,0)'),
                            fill: true,
                            yAxisID: 'y'
                        },
                        {
                            label: '提水量(L/min)',
                            data: [],
                            borderColor: '#06b6d4',
                            backgroundColor: 'transparent',
                            borderDash: [5, 5],
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    ...baseOptions,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            align: 'end',
                            labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
                        }
                    },
                    scales: {
                        ...baseOptions.scales,
                        y: {
                            type: 'linear', position: 'left',
                            grid: { color: 'rgba(45, 66, 89, 0.3)' },
                            title: { display: true, text: '效率(%)', font: { size: 10 } },
                            min: 0, max: 100
                        },
                        y1: {
                            type: 'linear', position: 'right',
                            grid: { display: false },
                            title: { display: true, text: '提水量', font: { size: 10 } }
                        }
                    }
                }
            });
        }

        this.charts.optimization = null;
    }

    updateSensorDisplay(data) {
        const setText = (id, val, suffix = '') => {
            const el = document.getElementById(id);
            if (el) el.textContent = val + suffix;
        };

        setText('sensor-speed', data.rotational_speed?.toFixed(2) || '0.00');
        setText('sensor-torque', data.torque?.toFixed(2) || '0.00');
        setText('sensor-water', data.water_lift?.toFixed(2) || '0.00');
        setText('sensor-level', data.water_level_diff?.toFixed(2) || '0.00');
        setText('sensor-tension', Math.round(data.chain_tension || 0));
        setText('sensor-efficiency', ((data.efficiency || 0) * 100).toFixed(1) + '%');

        const setBar = (id, value, max) => {
            const bar = document.getElementById(id);
            if (bar) bar.style.width = Math.min(100, (value / max) * 100) + '%';
        };

        setBar('bar-speed', data.rotational_speed || 0, 40);
        setBar('bar-torque', data.torque || 0, 200);
        setBar('bar-water', data.water_lift || 0, 300);
        setBar('bar-level', data.water_level_diff || 0, 4);
        setBar('bar-tension', data.chain_tension || 0, 5000);
        setBar('bar-efficiency', (data.efficiency || 0) * 100, 100);

        const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        this.dataHistory.time.push(time);
        this.dataHistory.speed.push(data.rotational_speed || 0);
        this.dataHistory.torque.push(data.torque || 0);
        this.dataHistory.water.push(data.water_lift || 0);
        this.dataHistory.efficiency.push((data.efficiency || 0) * 100);

        if (this.dataHistory.time.length > this.maxHistoryPoints) {
            this.dataHistory.time.shift();
            this.dataHistory.speed.shift();
            this.dataHistory.torque.shift();
            this.dataHistory.water.shift();
            this.dataHistory.efficiency.shift();
        }

        this.updateCharts();
    }

    updateCharts() {
        const labels = this.dataHistory.time;
        if (this.charts.speed) {
            this.charts.speed.data.labels = labels;
            this.charts.speed.data.datasets[0].data = [...this.dataHistory.speed];
            this.charts.speed.update('none');
        }
        if (this.charts.torque) {
            this.charts.torque.data.labels = labels;
            this.charts.torque.data.datasets[0].data = [...this.dataHistory.torque];
            this.charts.torque.update('none');
        }
        if (this.charts.efficiency) {
            this.charts.efficiency.data.labels = labels;
            this.charts.efficiency.data.datasets[0].data = [...this.dataHistory.efficiency];
            this.charts.efficiency.data.datasets[1].data = [...this.dataHistory.water];
            this.charts.efficiency.update('none');
        }
    }

    drawRing(canvasId, value, colorHex) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const radius = 45;
        const lineWidth = 10;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        const safeValue = Math.max(0, Math.min(1, value));
        const startAngle = -Math.PI / 2;
        const endAngle = startAngle + Math.PI * 2 * safeValue;

        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, endAngle);
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, colorHex);
        gradient.addColorStop(1, this._lightenColor(colorHex, 30));
        ctx.strokeStyle = gradient;
        ctx.lineWidth = lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.fillStyle = '#e8edf2';
        ctx.font = 'bold 22px Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText((safeValue * 100).toFixed(1) + '%', cx, cy);
    }

    _lightenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min(255, (num >> 16) + amt);
        const G = Math.min(255, ((num >> 8) & 0x00FF) + amt);
        const B = Math.min(255, (num & 0x0000FF) + amt);
        return `rgb(${R},${G},${B})`;
    }

    displayMechanicsResult(result) {
        const setText = (id, val, suffix = '') => {
            const el = document.getElementById(id);
            if (el) el.textContent = val + suffix;
        };

        setText('mech-output-torque', result.output_torque_Nm?.toFixed(2) || '0', ' N·m');
        setText('mech-drive-torque', result.drive_torque_Nm?.toFixed(2) || '0', ' N·m');
        setText('mech-input-power', result.input_power_W?.toFixed(1) || '0', ' W');
        setText('mech-output-power', result.output_power_W?.toFixed(1) || '0', ' W');

        const resist = result.resistance_breakdown || {};
        const maxR = Math.max(1,
            resist.scrape_resistance_N || 0,
            resist.chain_weight_resistance_N || 0,
            resist.bending_resistance_N || 0,
            resist.friction_resistance_N || 0,
            resist.water_acceleration_resistance_N || 0
        );

        const setHBar = (barId, valId, val, max) => {
            const bar = document.getElementById(barId);
            const valEl = document.getElementById(valId);
            if (bar) bar.style.width = ((val / max) * 100).toFixed(1) + '%';
            if (valEl) valEl.textContent = val.toFixed(1) + 'N';
        };

        setHBar('bar-scrape', 'val-scrape', resist.scrape_resistance_N || 0, maxR);
        setHBar('bar-weight', 'val-weight', resist.chain_weight_resistance_N || 0, maxR);
        setHBar('bar-bend', 'val-bend', resist.bending_resistance_N || 0, maxR);
        setHBar('bar-friction', 'val-friction', resist.friction_resistance_N || 0, maxR);
        setHBar('bar-accel', 'val-accel', resist.water_acceleration_resistance_N || 0, maxR);

        this.drawRing('ring-mech', result.mechanical_efficiency || 0, '#3b82f6');
        this.drawRing('ring-hyd', result.hydraulic_efficiency || 0, '#06b6d4');
        this.drawRing('ring-overall', result.overall_efficiency || 0, '#10b981');

        setText('health-tmax', result.chain_tension_max_N?.toFixed(0) || '0', ' N');
        setText('health-tmin', result.chain_tension_min_N?.toFixed(0) || '0', ' N');

        const riskEl = document.getElementById('health-risk');
        const riskClasses = {
            'none': ['risk-low', '正常'],
            'fatigue': ['risk-medium', '疲劳风险'],
            'overload': ['risk-critical', '过载危险'],
            'wear': ['risk-high', '磨损严重'],
            'buckling': ['risk-high', '屈曲风险']
        };
        if (riskEl) {
            const [cls, text] = riskClasses[result.chain_failure_risk] || ['risk-low', '正常'];
            riskEl.className = cls;
            riskEl.textContent = text;
        }

        setText('health-life', result.chain_fatigue_life_hours?.toFixed(0) || '0', ' h');
    }

    displayIrrigationResult(result) {
        document.getElementById('irrigation-results').style.display = 'block';

        const wb = result.water_balance || {};
        const losses = result.losses || {};
        const effs = result.efficiencies || {};
        const cost = result.cost_estimate || {};
        const optimal = result.optimal_operation || {};

        const setText = (id, val, suffix = '') => {
            const el = document.getElementById(id);
            if (el) el.textContent = (typeof val === 'number' ? val.toFixed(2) : val) + suffix;
        };

        setText('wb-delivered', wb.delivered_m3 || 0, ' m³');
        setText('wb-required', wb.crop_requirement_m3 || 0, ' m³');
        setText('wb-effective', wb.effective_water_mm || 0, ' mm');
        setText('wb-runoff', losses.runoff_m3 || 0, ' m³');
        setText('wb-percolation', losses.deep_percolation_m3 || 0, ' m³');

        this.drawRing('ring-irrig-overall', effs.overall || 0, '#10b981');
        this.drawRing('ring-irrig-convey', effs.conveyance || 0, '#06b6d4');
        this.drawRing('ring-irrig-field', effs.field_application || 0, '#8b5cf6');

        setText('irrig-area-eff', effs.area_efficiency_m2_per_m3 || 0, ' m²/m³');
        setText('irrig-prod', effs.water_productivity_kg_per_m3 || 0, ' kg/m³');

        const sweep = optimal.speed_analysis || [];
        this.renderOptimizationChart(sweep);

        let bestEff = { speed_rpm: 0, irrigation_efficiency: 0 };
        let bestArea = { speed_rpm: 0, area_served_m2: 0 };
        let bestBal = { speed_rpm: 0 };
        let bestScore = -1;
        sweep.forEach(d => {
            if (d.irrigation_efficiency > bestEff.irrigation_efficiency) bestEff = d;
            if (d.area_served_m2 > bestArea.area_served_m2) bestArea = d;
            const score = (d.irrigation_efficiency || 0) * 0.6 +
                ((d.area_served_m2 || 0) / Math.max(1, d.total_water_m3 || 1)) * 0.01 * 0.4;
            if (score > bestScore) { bestScore = score; bestBal = d; }
        });

        setText('opt-eff-speed', bestEff.speed_rpm || 0, ' rpm');
        setText('opt-eff-val', ((bestEff.irrigation_efficiency || 0) * 100).toFixed(1) + '%');
        setText('opt-area-speed', bestArea.speed_rpm || 0, ' rpm');
        setText('opt-area-val', (bestArea.area_served_m2 || 0).toFixed(0) + ' m²/h');
        setText('opt-bal-speed', (bestBal.speed_rpm || optimal.optimal_speed_rpm || 0), ' rpm');
        setText('opt-bal-val', ((bestBal.irrigation_efficiency || 0) * 100).toFixed(1) + '%');

        const recEl = document.getElementById('irrig-recommendation');
        if (recEl) recEl.textContent = result.recommendation || '';

        setText('cost-labor', cost.labor_cost_rmb || 0, ' 元');
        setText('cost-power', cost.power_cost_rmb || 0, ' 元');
        setText('cost-main', cost.maintenance_cost_rmb || 0, ' 元');
        setText('cost-total', cost.total_cost_rmb || 0, ' 元');
    }

    renderOptimizationChart(data) {
        const canvas = document.getElementById('chart-optimization');
        if (!canvas) return;

        if (this.charts.optimization) {
            this.charts.optimization.destroy();
        }

        const ctx = canvas.getContext('2d');
        this.charts.optimization = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.speed_rpm),
                datasets: [
                    {
                        label: '灌溉效率(%)',
                        data: data.map(d => (d.irrigation_efficiency || 0) * 100),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16,185,129,0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: '灌溉面积(m²/h)',
                        data: data.map(d => d.area_served_m2 || 0),
                        borderColor: '#06b6d4',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', align: 'end', labels: { boxWidth: 12, padding: 15, font: { size: 11 } } },
                    tooltip: { backgroundColor: 'rgba(26, 35, 50, 0.95)', borderColor: '#2d4259', borderWidth: 1 }
                },
                scales: {
                    x: { title: { display: true, text: '转速 (rpm)', font: { size: 11 } }, grid: { color: 'rgba(45, 66, 89, 0.2)' } },
                    y: { type: 'linear', position: 'left', title: { display: true, text: '效率(%)', font: { size: 10 } }, grid: { color: 'rgba(45, 66, 89, 0.2)' }, min: 0, max: 100 },
                    y1: { type: 'linear', position: 'right', title: { display: true, text: '面积(m²/h)', font: { size: 10 } }, grid: { display: false } }
                }
            }
        });
    }

    addAlert(alert) {
        const key = alert.alert_code || alert.alert_id;
        this.activeAlerts.set(key, alert);
        this.renderAlerts();
    }

    renderAlerts() {
        const container = document.getElementById('alert-container');
        if (!container) return;

        if (this.activeAlerts.size === 0) {
            container.innerHTML = '<div class="no-alerts">暂无告警</div>';
            return;
        }

        const alerts = Array.from(this.activeAlerts.values()).sort((a, b) =>
            new Date(b.timestamp) - new Date(a.timestamp)
        );

        container.innerHTML = alerts.map(a => {
            const levelClass = { 'emergency': 'critical', 'critical': 'critical', 'warning': 'warning', 'info': 'info' }[a.alert_level] || '';
            const time = new Date(a.timestamp).toLocaleTimeString('zh-CN', { hour12: false });
            const displayType = a.alert_type?.replace(/_/g, ' ') || a.alert_code || 'ALERT';
            const meta = [
                a.value !== undefined ? `当前: ${typeof a.value === 'number' ? a.value.toFixed(2) : a.value}` : '',
                a.threshold !== undefined ? `阈值: ${typeof a.threshold === 'number' ? a.threshold.toFixed(2) : a.threshold}` : ''
            ].filter(Boolean).join(' | ');

            return `<div class="alert-item ${levelClass}"><div class="alert-header"><span class="alert-type">${displayType}</span><span class="alert-time">${time}</span></div><div class="alert-message">${a.message || ''}</div>${meta ? `<div class="alert-meta">${meta}</div>` : ''}</div>`;
        }).join('');
    }

    updateConnectionStatus(wsSensor, wsAlerts) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        const connected = (wsSensor?.readyState === WebSocket.OPEN) || (wsAlerts?.readyState === WebSocket.OPEN);

        if (dot) {
            dot.classList.toggle('online', connected);
            dot.classList.toggle('offline', !connected);
        }
        if (text) {
            text.textContent = connected ? '已连接' : '未连接';
        }
    }
}
