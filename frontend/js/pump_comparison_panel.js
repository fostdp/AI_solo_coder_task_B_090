import Chart from 'chart.js';

export class PumpComparisonPanel {
    constructor() {
        this.charts = {};
        this.COLORS = {
            waterwheel: '#c4833f',
            pump: '#3b82f6',
            waterwheelAlpha: 'rgba(196,131,63,0.25)',
            pumpAlpha: 'rgba(59,130,246,0.25)'
        };

        Chart.defaults.color = '#8899a8';
        Chart.defaults.borderColor = 'rgba(45, 66, 89, 0.5)';
        Chart.defaults.font.family = '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';
    }

    _getBaseUrl() {
        const port = window.location.port;
        if (port === '' || port === '3000' || port === '5000') {
            return `${window.location.protocol}//${window.location.hostname}:8000`;
        }
        return window.location.origin;
    }

    async _fetch(endpoint, options = {}) {
        const url = `${this._getBaseUrl()}${endpoint}`;
        const resp = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        return resp.json();
    }

    async loadEfficiencyComparison(waterLevel, flowRate) {
        return this._fetch('/api/comparison/efficiency', {
            method: 'POST',
            body: JSON.stringify({ water_level: waterLevel, flow_rate_m3h: flowRate })
        });
    }

    async loadCostComparison(hours, flowRate, waterLevel) {
        return this._fetch('/api/comparison/costs', {
            method: 'POST',
            body: JSON.stringify({
                annual_operating_hours: hours,
                flow_rate_m3h: flowRate,
                water_level: waterLevel
            })
        });
    }

    async loadEnvironmentalImpact() {
        return this._fetch('/api/comparison/environmental');
    }

    async loadSummary() {
        return this._fetch('/api/comparison/summary');
    }

    async loadEfficiencyCurves(minSpeed, maxSpeed) {
        return this._fetch(`/api/comparison/curves?min_speed=${minSpeed}&max_speed=${maxSpeed}`);
    }

    async loadFullComparison(waterLevel, flowRate, hoursPerYear) {
        return this._fetch('/api/comparison/full', {
            method: 'POST',
            body: JSON.stringify({
                water_level: waterLevel,
                flow_rate_m3h: flowRate,
                hours_per_year: hoursPerYear
            })
        });
    }

    renderEfficiencyChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const chartKey = `efficiency_${canvasId}`;
        if (this.charts[chartKey]) {
            this.charts[chartKey].destroy();
        }

        const curves = data.curves || data || [];
        const labels = curves.map(d => d.speed_ratio?.toFixed(2) || '');

        const ctx = canvas.getContext('2d');
        this.charts[chartKey] = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: '龙骨水车效率',
                        data: curves.map(d => (d.waterwheel_efficiency || 0) * 100),
                        borderColor: this.COLORS.waterwheel,
                        backgroundColor: this.COLORS.waterwheelAlpha,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2
                    },
                    {
                        label: '离心泵效率',
                        data: curves.map(d => (d.pump_efficiency || 0) * 100),
                        borderColor: this.COLORS.pump,
                        backgroundColor: this.COLORS.pumpAlpha,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
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
                        title: { display: true, text: '速比', font: { size: 11 } },
                        grid: { color: 'rgba(45, 66, 89, 0.2)' },
                        ticks: { maxTicksLimit: 8, font: { size: 10 } }
                    },
                    y: {
                        title: { display: true, text: '效率(%)', font: { size: 10 } },
                        grid: { color: 'rgba(45, 66, 89, 0.3)' },
                        min: 0,
                        max: 100,
                        ticks: { font: { size: 10 } }
                    }
                },
                elements: {
                    point: { radius: 0, hoverRadius: 4 },
                    line: { tension: 0.35, borderWidth: 2 }
                }
            }
        });
    }

    renderCostBreakdown(container, data) {
        const el = document.getElementById(container) || document.querySelector(container);
        if (!el) return;

        const wwCost = data.waterwheel_cost || {};
        const pumpCost = data.pump_cost || {};

        const chartKey = `cost_${container}`;
        if (this.charts[chartKey]) {
            this.charts[chartKey].destroy();
        }

        const canvasId = `canvas-cost-${container.replace(/[^a-zA-Z0-9]/g, '')}`;
        el.innerHTML = `<canvas id="${canvasId}" style="width:100%;height:260px;"></canvas>`;

        const ctx = document.getElementById(canvasId).getContext('2d');
        this.charts[chartKey] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['人工/电费', '维护', '总计'],
                datasets: [
                    {
                        label: '龙骨水车',
                        data: [
                            wwCost.labor_cost_annual || 0,
                            wwCost.maintenance_cost_annual || 0,
                            wwCost.total_annual_cost || 0
                        ],
                        backgroundColor: this.COLORS.waterwheel,
                        borderColor: this.COLORS.waterwheel,
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: '离心泵',
                        data: [
                            pumpCost.electricity_cost_annual || 0,
                            pumpCost.maintenance_cost_annual || 0,
                            pumpCost.total_annual_cost || 0
                        ],
                        backgroundColor: this.COLORS.pump,
                        borderColor: this.COLORS.pump,
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.95)',
                        borderColor: '#2d4259',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ¥${ctx.parsed.y.toFixed(0)}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(45, 66, 89, 0.3)' },
                        title: { display: true, text: '年成本(元)', font: { size: 10 } },
                        ticks: { font: { size: 10 } }
                    }
                }
            }
        });
    }

    renderEnvironmentalCard(container, data) {
        const el = document.getElementById(container) || document.querySelector(container);
        if (!el) return;

        const wwCarbon = data.waterwheel_carbon_kg_per_year || 0;
        const pumpCarbon = data.pump_carbon_kg_per_year || 0;
        const carbonSavings = data.carbon_savings_kg_per_year || 0;
        const carbonReduction = data.carbon_reduction_percent || 0;
        const wwEnergy = data.waterwheel_energy_source || '';
        const pumpEnergy = data.pump_energy_source || '';
        const wwSustain = data.waterwheel_material_sustainability_score || 0;
        const pumpSustain = data.pump_material_sustainability_score || 0;

        const maxCarbon = Math.max(wwCarbon, pumpCarbon, 1);
        const maxSustain = 10;

        el.innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div style="background:var(--bg-card,rgba(30,42,58,0.85));border:1px solid var(--border-color,#2d4259);border-radius:var(--radius-sm,8px);padding:16px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:8px;">🌾</div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">龙骨水车</div>
                    <div style="font-size:22px;font-weight:700;color:${this.COLORS.waterwheel};font-family:Consolas,monospace;">${wwCarbon.toFixed(1)}</div>
                    <div style="font-size:11px;color:var(--text-muted,#5c7080);">kg CO₂/年</div>
                    <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden;">
                        <div style="height:100%;width:${(wwCarbon / maxCarbon * 100).toFixed(1)}%;background:${this.COLORS.waterwheel};border-radius:2px;"></div>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary,#8899a8);margin-top:6px;">能源: ${wwEnergy}</div>
                    <div style="font-size:11px;color:var(--text-secondary,#8899a8);">可持续性: ${wwSustain}/${maxSustain}</div>
                </div>
                <div style="background:var(--bg-card,rgba(30,42,58,0.85));border:1px solid var(--border-color,#2d4259);border-radius:var(--radius-sm,8px);padding:16px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:8px;">⚡</div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">离心泵</div>
                    <div style="font-size:22px;font-weight:700;color:${this.COLORS.pump};font-family:Consolas,monospace;">${pumpCarbon.toFixed(1)}</div>
                    <div style="font-size:11px;color:var(--text-muted,#5c7080);">kg CO₂/年</div>
                    <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden;">
                        <div style="height:100%;width:${(pumpCarbon / maxCarbon * 100).toFixed(1)}%;background:${this.COLORS.pump};border-radius:2px;"></div>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary,#8899a8);margin-top:6px;">能源: ${pumpEnergy}</div>
                    <div style="font-size:11px;color:var(--text-secondary,#8899a8);">可持续性: ${pumpSustain}/${maxSustain}</div>
                </div>
            </div>
            <div style="margin-top:12px;background:linear-gradient(135deg,rgba(16,185,129,0.08),rgba(6,182,212,0.08));border:1px solid rgba(16,185,129,0.2);border-radius:var(--radius-sm,8px);padding:12px;text-align:center;">
                <div style="font-size:11px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">碳减排量</div>
                <div style="font-size:20px;font-weight:700;color:var(--accent-green,#10b981);font-family:Consolas,monospace;">${carbonSavings.toFixed(1)} kg/年</div>
                <div style="font-size:12px;color:var(--accent-cyan,#06b6d4);">减排 ${carbonReduction.toFixed(1)}%</div>
            </div>
        `;
    }

    renderSummaryCard(container, data) {
        const el = document.getElementById(container) || document.querySelector(container);
        if (!el) return;

        const ww = data.waterwheel || {};
        const pump = data.centrifugal_pump || {};
        const metrics = data.key_metrics || {};

        el.innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
                <div style="background:var(--bg-card,rgba(30,42,58,0.85));border:1px solid ${this.COLORS.waterwheel}40;border-radius:var(--radius-sm,8px);padding:14px;">
                    <div style="font-size:14px;font-weight:600;color:${this.COLORS.waterwheel};margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border-color,#2d4259);">🌾 龙骨水车</div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">效率范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${ww.typical_efficiency_range || '-'}</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">流量范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${ww.typical_flow_range_m3h || '-'} m³/h</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">扬程范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${ww.typical_head_range_m || '-'} m</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">能源: <span style="color:var(--text-primary,#e8edf2);">${ww.energy_source || '-'}</span></div>
                    <div style="margin-top:8px;font-size:11px;color:var(--accent-green,#10b981);">✓ ${(ww.advantages || []).slice(0, 2).join(' / ')}</div>
                    <div style="font-size:11px;color:var(--accent-red,#ef4444);">✗ ${(ww.disadvantages || []).slice(0, 2).join(' / ')}</div>
                </div>
                <div style="background:var(--bg-card,rgba(30,42,58,0.85));border:1px solid ${this.COLORS.pump}40;border-radius:var(--radius-sm,8px);padding:14px;">
                    <div style="font-size:14px;font-weight:600;color:${this.COLORS.pump};margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border-color,#2d4259);">⚡ 离心泵</div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">效率范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${pump.typical_efficiency_range || '-'}</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">流量范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${pump.typical_flow_range_m3h || '-'} m³/h</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">扬程范围: <span style="color:var(--text-primary,#e8edf2);font-family:Consolas,monospace;">${pump.typical_head_range_m || '-'} m</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-bottom:4px;">能源: <span style="color:var(--text-primary,#e8edf2);">${pump.energy_source || '-'}</span></div>
                    <div style="margin-top:8px;font-size:11px;color:var(--accent-green,#10b981);">✓ ${(pump.advantages || []).slice(0, 2).join(' / ')}</div>
                    <div style="font-size:11px;color:var(--accent-red,#ef4444);">✗ ${(pump.disadvantages || []).slice(0, 2).join(' / ')}</div>
                </div>
            </div>
            <div style="background:var(--bg-card,rgba(30,42,58,0.85));border:1px solid var(--border-color,#2d4259);border-radius:var(--radius-sm,8px);padding:14px;">
                <div style="font-size:13px;font-weight:600;color:var(--text-primary,#e8edf2);margin-bottom:10px;">关键指标</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);">效率提升: <span style="color:var(--accent-cyan,#06b6d4);font-weight:700;">${metrics.efficiency_improvement_factor || '-'}</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);">流量提升: <span style="color:var(--accent-cyan,#06b6d4);font-weight:700;">${metrics.flow_capacity_improvement || '-'}</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);">扬程提升: <span style="color:var(--accent-cyan,#06b6d4);font-weight:700;">${metrics.head_capacity_improvement || '-'}</span></div>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);">技术差距: <span style="color:var(--accent-yellow,#f59e0b);font-weight:700;">${metrics.technology_gap_years || '-'}</span></div>
                </div>
            </div>
        `;
    }

    renderEfficiencyRings(container, waterEff, pumpEff) {
        const el = document.getElementById(container) || document.querySelector(container);
        if (!el) return;

        const ringId1 = `ring-ww-${Date.now()}`;
        const ringId2 = `ring-pump-${Date.now()}`;

        el.innerHTML = `
            <div style="display:flex;justify-content:space-around;align-items:center;gap:12px;">
                <div style="text-align:center;">
                    <canvas id="${ringId1}" width="120" height="120"></canvas>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-top:4px;">龙骨水车</div>
                </div>
                <div style="text-align:center;">
                    <canvas id="${ringId2}" width="120" height="120"></canvas>
                    <div style="font-size:12px;color:var(--text-secondary,#8899a8);margin-top:4px;">离心泵</div>
                </div>
            </div>
        `;

        this._drawRing(ringId1, waterEff, this.COLORS.waterwheel);
        this._drawRing(ringId2, pumpEff, this.COLORS.pump);
    }

    _drawRing(canvasId, value, colorHex) {
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
}
