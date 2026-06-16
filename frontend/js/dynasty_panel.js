import Chart from 'chart.js';

export class DynastyPanel {
    constructor() {
        this.charts = {};
        this.dynastyData = null;
        this.timelineData = null;
        this.scoresData = null;
        this.DYNASTY_COLORS = {
            han: '#c4833f',
            tang: '#f59e0b',
            song: '#06b6d4'
        };
        this.DYNASTY_NAMES = {
            han: '汉',
            tang: '唐',
            song: '宋'
        };
        this.apiUrl = this._resolveApiBase();
    }

    _resolveApiBase() {
        const base = window.location.origin;
        if (window.location.port === '' || window.location.port === '3000' || window.location.port === '5000') {
            return `${window.location.protocol}//${window.location.hostname}:8000`;
        }
        return base;
    }

    async loadDynastyData() {
        try {
            const resp = await fetch(`${this.apiUrl}/api/dynasty/compare`);
            this.dynastyData = await resp.json();
            return this.dynastyData;
        } catch (e) {
            console.error('加载朝代对比数据失败:', e);
            return null;
        }
    }

    async loadTimeline() {
        try {
            const resp = await fetch(`${this.apiUrl}/api/dynasty/timeline`);
            this.timelineData = await resp.json();
            return this.timelineData;
        } catch (e) {
            console.error('加载朝代时间线失败:', e);
            return null;
        }
    }

    async simulateDynasty(dynasty, speed, waterLevel) {
        try {
            const resp = await fetch(`${this.apiUrl}/api/dynasty/simulate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dynasty, speed, water_level: waterLevel })
            });
            return await resp.json();
        } catch (e) {
            console.error('朝代仿真失败:', e);
            return null;
        }
    }

    async loadScores() {
        try {
            const resp = await fetch(`${this.apiUrl}/api/dynasty/score`);
            this.scoresData = await resp.json();
            return this.scoresData;
        } catch (e) {
            console.error('加载朝代评分失败:', e);
            return null;
        }
    }

    renderComparison(container) {
        container.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display:grid;grid-template-columns:repeat(3,1fr);gap:16px;';

        const dynasties = ['han', 'tang', 'song'];
        const data = this.dynastyData || {};

        dynasties.forEach(key => {
            const d = data[key] || {};
            const color = this.DYNASTY_COLORS[key];
            const name = this.DYNASTY_NAMES[key];

            const card = document.createElement('div');
            card.style.cssText = `
                background:var(--bg-card);
                border:1px solid var(--border-color);
                border-radius:var(--radius);
                padding:18px;
                border-top:3px solid ${color};
                backdrop-filter:blur(10px);
            `;

            const header = document.createElement('div');
            header.style.cssText = `
                display:flex;align-items:center;gap:10px;
                margin-bottom:16px;padding-bottom:12px;
                border-bottom:1px solid var(--border-color);
            `;

            const dot = document.createElement('span');
            dot.style.cssText = `
                width:12px;height:12px;border-radius:50%;
                background:${color};box-shadow:0 0 8px ${color};
            `;

            const title = document.createElement('h3');
            title.textContent = `${name}朝`;
            title.style.cssText = `
                font-size:16px;font-weight:700;color:var(--text-primary);
                margin:0;
            `;

            header.appendChild(dot);
            header.appendChild(title);
            card.appendChild(header);

            const metrics = [
                { label: '轮径', value: d.wheel_diameter, unit: 'm' },
                { label: '叶片数', value: d.blade_count, unit: '片' },
                { label: '链型', value: d.chain_type, unit: '' },
                { label: '铰接型式', value: d.joint_type, unit: '' },
                { label: '效率', value: d.efficiency, unit: '', isPercent: true },
                { label: '提水量', value: d.water_lift_capacity, unit: 'L/min' },
                { label: '驱动扭矩', value: d.drive_torque, unit: 'N·m' },
                { label: '链张力', value: d.chain_tension, unit: 'N' }
            ];

            metrics.forEach(m => {
                const row = document.createElement('div');
                row.style.cssText = `
                    display:flex;justify-content:space-between;align-items:center;
                    padding:8px 0;border-bottom:1px solid rgba(45,66,89,0.3);
                `;

                const label = document.createElement('span');
                label.textContent = m.label;
                label.style.cssText = 'font-size:12px;color:var(--text-secondary);';

                const val = document.createElement('span');
                if (m.isPercent && typeof m.value === 'number') {
                    val.textContent = (m.value * 100).toFixed(1) + '%';
                } else if (typeof m.value === 'number') {
                    val.textContent = m.value.toFixed ? m.value.toFixed(2) : m.value;
                    if (m.unit) val.textContent += ' ' + m.unit;
                } else {
                    val.textContent = m.value || '-';
                    if (m.unit && m.value) val.textContent += ' ' + m.unit;
                }
                val.style.cssText = `
                    font-size:14px;font-weight:700;color:${color};
                    font-family:'Consolas','Monaco',monospace;
                `;

                row.appendChild(label);
                row.appendChild(val);
                card.appendChild(row);
            });

            wrapper.appendChild(card);
        });

        container.appendChild(wrapper);
    }

    renderTimeline(container) {
        container.innerHTML = '';

        const events = this.timelineData?.events || [];

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            position:relative;padding:30px 20px 20px;
            overflow-x:auto;
        `;

        const line = document.createElement('div');
        line.style.cssText = `
            position:absolute;top:50px;left:40px;right:40px;
            height:3px;
            background:linear-gradient(90deg,${this.DYNASTY_COLORS.han},${this.DYNASTY_COLORS.tang},${this.DYNASTY_COLORS.song});
            border-radius:2px;
        `;
        wrapper.appendChild(line);

        const nodesWrapper = document.createElement('div');
        nodesWrapper.style.cssText = `
            display:flex;justify-content:space-between;
            position:relative;min-height:100px;
        `;

        events.forEach((evt, i) => {
            const dynastyKey = (evt.dynasty || 'han').toLowerCase();
            const color = this.DYNASTY_COLORS[dynastyKey] || this.DYNASTY_COLORS.han;

            const node = document.createElement('div');
            node.style.cssText = `
                display:flex;flex-direction:column;align-items:center;
                flex:1;max-width:140px;position:relative;
            `;

            const dot = document.createElement('div');
            dot.style.cssText = `
                width:16px;height:16px;border-radius:50%;
                background:${color};box-shadow:0 0 10px ${color};
                border:3px solid var(--bg-secondary);
                z-index:1;margin-bottom:10px;
            `;

            const year = document.createElement('div');
            year.textContent = evt.year || '';
            year.style.cssText = `
                font-size:12px;font-weight:700;color:${color};
                font-family:'Consolas','Monaco',monospace;
                margin-bottom:6px;
            `;

            const name = document.createElement('div');
            name.textContent = evt.innovation || evt.name || '';
            name.style.cssText = `
                font-size:11px;color:var(--text-secondary);
                text-align:center;line-height:1.4;
                max-width:120px;
            `;

            const dynastyTag = document.createElement('div');
            dynastyTag.textContent = this.DYNASTY_NAMES[dynastyKey] || '';
            dynastyTag.style.cssText = `
                font-size:10px;color:var(--text-muted);
                margin-top:4px;
            `;

            node.appendChild(dot);
            node.appendChild(year);
            node.appendChild(name);
            node.appendChild(dynastyTag);
            nodesWrapper.appendChild(node);
        });

        wrapper.appendChild(nodesWrapper);
        container.appendChild(wrapper);
    }

    renderSimulation(container, result) {
        container.innerHTML = '';
        if (!result) return;

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display:flex;flex-direction:column;gap:16px;';

        const dynastyKey = (result.dynasty || 'han').toLowerCase();
        const color = this.DYNASTY_COLORS[dynastyKey] || this.DYNASTY_COLORS.han;
        const dynastyName = this.DYNASTY_NAMES[dynastyKey] || dynastyKey;

        const header = document.createElement('div');
        header.style.cssText = `
            font-size:16px;font-weight:700;color:${color};
            padding-bottom:12px;border-bottom:1px solid var(--border-color);
        `;
        header.textContent = `${dynastyName}朝仿真结果`;
        wrapper.appendChild(header);

        const ringsRow = document.createElement('div');
        ringsRow.style.cssText = 'display:flex;justify-content:space-around;align-items:center;gap:12px;';

        const ringMetrics = [
            { key: 'mechanical_efficiency', label: '机械效率', value: result.mechanical_efficiency },
            { key: 'hydraulic_efficiency', label: '水力效率', value: result.hydraulic_efficiency },
            { key: 'overall_efficiency', label: '综合效率', value: result.overall_efficiency }
        ];

        ringMetrics.forEach(m => {
            const item = document.createElement('div');
            item.style.cssText = 'text-align:center;';

            const canvas = document.createElement('canvas');
            canvas.width = 120;
            canvas.height = 120;
            canvas.style.cssText = 'display:block;margin:0 auto 4px;';

            const label = document.createElement('div');
            label.textContent = m.label;
            label.style.cssText = 'font-size:11px;color:var(--text-secondary);';

            item.appendChild(canvas);
            item.appendChild(label);
            ringsRow.appendChild(item);

            this._drawRing(canvas, m.value || 0, color);
        });

        wrapper.appendChild(ringsRow);

        const metricsGrid = document.createElement('div');
        metricsGrid.style.cssText = `
            display:grid;grid-template-columns:1fr 1fr;gap:10px;
        `;

        const detailMetrics = [
            { label: '输出扭矩', value: result.output_torque_Nm, unit: 'N·m' },
            { label: '驱动扭矩', value: result.drive_torque_Nm, unit: 'N·m' },
            { label: '输入功率', value: result.input_power_W, unit: 'W' },
            { label: '输出功率', value: result.output_power_W, unit: 'W' },
            { label: '提水量', value: result.water_lift_lpm, unit: 'L/min' },
            { label: '链张力峰值', value: result.chain_tension_max_N, unit: 'N' }
        ];

        detailMetrics.forEach(m => {
            const item = document.createElement('div');
            item.style.cssText = `
                background:rgba(255,255,255,0.03);
                padding:10px 12px;border-radius:var(--radius-sm);
            `;

            const lbl = document.createElement('div');
            lbl.textContent = m.label;
            lbl.style.cssText = 'font-size:11px;color:var(--text-secondary);margin-bottom:4px;';

            const val = document.createElement('span');
            if (typeof m.value === 'number') {
                val.textContent = m.value.toFixed(2) + (m.unit ? ' ' + m.unit : '');
            } else {
                val.textContent = '-' + (m.unit ? ' ' + m.unit : '');
            }
            val.style.cssText = `
                font-size:16px;font-weight:700;color:${color};
                font-family:'Consolas','Monaco',monospace;
            `;

            item.appendChild(lbl);
            item.appendChild(val);
            metricsGrid.appendChild(item);
        });

        wrapper.appendChild(metricsGrid);
        container.appendChild(wrapper);
    }

    _drawRing(canvas, value, colorHex) {
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

    renderRadarChart(canvasId, scores) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (this.charts.radar) {
            this.charts.radar.destroy();
        }

        const ctx = canvas.getContext('2d');
        const data = scores || this.scoresData || {};

        const datasets = ['han', 'tang', 'song'].map(key => {
            const d = data[key] || {};
            return {
                label: this.DYNASTY_NAMES[key] + '朝',
                data: [
                    d.efficiency || 0,
                    d.durability || 0,
                    d.capacity || 0,
                    d.innovation || 0
                ],
                borderColor: this.DYNASTY_COLORS[key],
                backgroundColor: this.DYNASTY_COLORS[key] + '20',
                pointBackgroundColor: this.DYNASTY_COLORS[key],
                pointBorderColor: this.DYNASTY_COLORS[key],
                pointRadius: 4,
                borderWidth: 2
            };
        });

        this.charts.radar = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['效率', '耐久性', '容量', '创新性'],
                datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#8899a8',
                            boxWidth: 12,
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.95)',
                        borderColor: '#2d4259',
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            stepSize: 0.2,
                            color: '#5c7080',
                            backdropColor: 'transparent',
                            font: { size: 10 }
                        },
                        grid: {
                            color: 'rgba(45, 66, 89, 0.4)'
                        },
                        angleLines: {
                            color: 'rgba(45, 66, 89, 0.4)'
                        },
                        pointLabels: {
                            color: '#8899a8',
                            font: { size: 12, weight: '600' }
                        }
                    }
                },
                animation: { duration: 600 }
            }
        });
    }

    renderEvolutionChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (this.charts.evolution) {
            this.charts.evolution.destroy();
        }

        const ctx = canvas.getContext('2d');
        const data = this.dynastyData || {};
        const labels = ['汉朝', '唐朝', '宋朝'];
        const keys = ['han', 'tang', 'song'];

        const makeDataset = (label, field, color, isPercent) => ({
            label,
            data: keys.map(k => {
                const val = (data[k] || {})[field] || 0;
                return isPercent ? val * 100 : val;
            }),
            borderColor: color,
            backgroundColor: color + '15',
            pointBackgroundColor: color,
            pointBorderColor: color,
            pointRadius: 5,
            pointHoverRadius: 7,
            borderWidth: 2,
            tension: 0.3,
            fill: false
        });

        this.charts.evolution = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    makeDataset('效率(%)', 'efficiency', '#10b981', true),
                    makeDataset('容量(L/min)', 'water_lift_capacity', '#06b6d4', false),
                    makeDataset('叶片数', 'blade_count', '#f59e0b', false)
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: {
                            color: '#8899a8',
                            boxWidth: 12,
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.95)',
                        borderColor: '#2d4259',
                        borderWidth: 1,
                        padding: 10
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(45, 66, 89, 0.3)' },
                        ticks: { color: '#8899a8', font: { size: 12 } }
                    },
                    y: {
                        grid: { color: 'rgba(45, 66, 89, 0.3)' },
                        ticks: { color: '#8899a8', font: { size: 10 } },
                        beginAtZero: true
                    }
                },
                elements: {
                    point: { radius: 5, hoverRadius: 7 },
                    line: { tension: 0.3, borderWidth: 2 }
                },
                animation: { duration: 600 }
            }
        });
    }
}
