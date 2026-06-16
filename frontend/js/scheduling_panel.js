import Chart from 'chart.js';

export class SchedulingPanel {
    constructor() {
        this.charts = {};
        this.wheels = [];
        this.zones = [];
        this.schedule = null;
        this.recommendations = [];

        this.WHEEL_COLORS = [
            '#3b82f6', '#8b5cf6', '#06b6d4', '#10b981',
            '#f59e0b', '#ef4444', '#f97316', '#ec4899'
        ];

        this._initChartDefaults();
    }

    _initChartDefaults() {
        Chart.defaults.color = '#8899a8';
        Chart.defaults.borderColor = 'rgba(45, 66, 89, 0.5)';
        Chart.defaults.font.family = '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';
    }

    _resolveBaseUrl() {
        const base = window.location.origin;
        const port = window.location.port;
        if (port === '' || port === '3000' || port === '5000') {
            return `${window.location.protocol}//${window.location.hostname}:8000`;
        }
        return base;
    }

    async _api(method, path, body) {
        const url = `${this._resolveBaseUrl()}${path}`;
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        if (body) opts.body = JSON.stringify(body);
        const resp = await fetch(url, opts);
        return resp.json();
    }

    async addWheel(wheelData) {
        const result = await this._api('POST', '/api/scheduling/wheels', wheelData);
        return result;
    }

    async addZone(zoneData) {
        const result = await this._api('POST', '/api/scheduling/zones', zoneData);
        return result;
    }

    async loadWheelStatus() {
        const result = await this._api('GET', '/api/scheduling/wheels');
        this.wheels = result.wheels || result || [];
        return this.wheels;
    }

    async loadZoneList() {
        const result = await this._api('GET', '/api/scheduling/zones');
        this.zones = result.zones || result || [];
        return this.zones;
    }

    async optimizeSchedule(targetWater, hoursAvailable) {
        const result = await this._api('POST', '/api/scheduling/optimize', {
            target_water: targetWater,
            hours_available: hoursAvailable
        });
        return result;
    }

    async loadSchedule() {
        const result = await this._api('GET', '/api/scheduling/schedule');
        this.schedule = result.schedule || result || null;
        return this.schedule;
    }

    async loadRecommendations() {
        const result = await this._api('GET', '/api/scheduling/recommendations');
        this.recommendations = result.recommendations || result || [];
        return this.recommendations;
    }

    async resetScheduler() {
        const result = await this._api('POST', '/api/scheduling/reset');
        this.wheels = [];
        this.zones = [];
        this.schedule = null;
        this.recommendations = [];
        return result;
    }

    renderWheelCards(container, wheels) {
        if (!container) return;
        if (!wheels || wheels.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px;">暂无水车数据</div>';
            return;
        }

        container.innerHTML = wheels.map((w, i) => {
            const color = this.WHEEL_COLORS[i % this.WHEEL_COLORS.length];
            const statusClass = w.status === 'active' ? 'var(--accent-green)' :
                w.status === 'idle' ? 'var(--accent-yellow)' : 'var(--text-muted)';
            return `<div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:14px;border-left:4px solid ${color};">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${w.wheel_id || w.id || '-'}</span>
                    <span style="font-size:11px;color:${statusClass};text-transform:uppercase;letter-spacing:0.5px;">${w.status || '-'}</span>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">转速</span><span style="font-size:15px;font-weight:700;color:var(--accent-cyan);font-family:Consolas,monospace;">${(w.speed || 0).toFixed(1)}<span style="font-size:10px;color:var(--text-muted);"> rpm</span></span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">效率</span><span style="font-size:15px;font-weight:700;color:var(--accent-green);font-family:Consolas,monospace;">${((w.efficiency || 0) * 100).toFixed(1)}<span style="font-size:10px;color:var(--text-muted);">%</span></span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">容量</span><span style="font-size:15px;font-weight:700;color:var(--accent-blue);font-family:Consolas,monospace;">${(w.capacity || 0).toFixed(0)}<span style="font-size:10px;color:var(--text-muted);"> L/min</span></span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">提水量</span><span style="font-size:15px;font-weight:700;color:var(--accent-purple);font-family:Consolas,monospace;">${(w.water_output || 0).toFixed(0)}<span style="font-size:10px;color:var(--text-muted);"> L/min</span></span></div>
                </div>
            </div>`;
        }).join('');
    }

    renderZoneCards(container, zones) {
        if (!container) return;
        if (!zones || zones.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px;">暂无灌溉区域数据</div>';
            return;
        }

        const priorityColors = {
            high: 'var(--accent-red)',
            medium: 'var(--accent-yellow)',
            low: 'var(--accent-green)'
        };

        container.innerHTML = zones.map(z => {
            const pColor = priorityColors[z.priority] || 'var(--text-secondary)';
            return `<div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${z.zone_id || z.id || '-'}</span>
                    <span style="font-size:11px;color:${pColor};text-transform:uppercase;letter-spacing:0.5px;padding:2px 8px;border-radius:10px;background:rgba(255,255,255,0.05);">${z.priority || '-'}</span>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">面积</span><span style="font-size:15px;font-weight:700;color:var(--accent-cyan);font-family:Consolas,monospace;">${(z.area || 0).toFixed(0)}<span style="font-size:10px;color:var(--text-muted);"> m²</span></span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">作物</span><span style="font-size:13px;font-weight:600;color:var(--text-primary);">${z.crop_type || z.crop || '-'}</span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">需水量</span><span style="font-size:15px;font-weight:700;color:var(--accent-blue);font-family:Consolas,monospace;">${(z.water_requirement || z.water_needed || 0).toFixed(0)}<span style="font-size:10px;color:var(--text-muted);"> m³</span></span></div>
                    <div><span style="font-size:11px;color:var(--text-secondary);display:block;">优先级</span><span style="font-size:13px;font-weight:600;color:${pColor};">${z.priority || '-'}</span></div>
                </div>
            </div>`;
        }).join('');
    }

    renderAllocationTable(container, allocations) {
        if (!container) return;
        if (!allocations || allocations.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px;">暂无分配数据</div>';
            return;
        }

        const header = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr>
                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--border-color);background:var(--bg-tertiary);color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:0.5px;position:sticky;top:0;">水车</th>
                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--border-color);background:var(--bg-tertiary);color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:0.5px;position:sticky;top:0;">灌溉区域</th>
                <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--border-color);background:var(--bg-tertiary);color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:0.5px;position:sticky;top:0;">分配水量(m³)</th>
                <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--border-color);background:var(--bg-tertiary);color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:0.5px;position:sticky;top:0;">时间(h)</th>
            </tr></thead><tbody>`;

        const rows = allocations.map((a, i) => {
            const color = this.WHEEL_COLORS[i % this.WHEEL_COLORS.length];
            return `<tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:10px 12px;color:var(--text-primary);font-weight:600;"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:8px;"></span>${a.wheel_id || '-'}</td>
                <td style="padding:10px 12px;color:var(--text-primary);">${a.zone_id || '-'}</td>
                <td style="padding:10px 12px;text-align:right;color:var(--accent-cyan);font-family:Consolas,monospace;font-weight:700;">${(a.allocated_water || 0).toFixed(1)}</td>
                <td style="padding:10px 12px;text-align:right;color:var(--accent-blue);font-family:Consolas,monospace;font-weight:700;">${(a.allocated_hours || a.hours || 0).toFixed(1)}</td>
            </tr>`;
        }).join('');

        container.innerHTML = header + rows + '</tbody></table>';
    }

    renderGanttChart(canvasId, schedule) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (this.charts.gantt) {
            this.charts.gantt.destroy();
        }

        if (!schedule || !schedule.slots || schedule.slots.length === 0) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            return;
        }

        const wheelIds = [...new Set(schedule.slots.map(s => s.wheel_id))];
        const maxTime = Math.max(...schedule.slots.map(s => (s.end_hour || 0)), 1);

        const datasets = wheelIds.map((wid, i) => {
            const color = this.WHEEL_COLORS[i % this.WHEEL_COLORS.length];
            const slots = schedule.slots.filter(s => s.wheel_id === wid);
            return {
                label: wid,
                data: slots.map(s => [s.start_hour || 0, s.end_hour || 0]),
                backgroundColor: color + '99',
                borderColor: color,
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            };
        });

        const ctx = canvas.getContext('2d');
        this.charts.gantt = new Chart(ctx, {
            type: 'bar',
            data: { labels: wheelIds, datasets },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.95)',
                        borderColor: '#2d4259',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (ctx) => {
                                const [start, end] = ctx.raw;
                                const slot = schedule.slots.find(s =>
                                    s.wheel_id === wheelIds[ctx.dataIndex] &&
                                    s.start_hour === start && s.end_hour === end
                                );
                                const zone = slot?.zone_id || '-';
                                return `${start}h - ${end}h → ${zone}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        min: 0,
                        max: maxTime,
                        grid: { color: 'rgba(45, 66, 89, 0.3)' },
                        ticks: {
                            font: { size: 10 },
                            callback: (v) => v + 'h'
                        },
                        title: { display: true, text: '时间(小时)', font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        });
    }

    renderCapacityGauge(container, totalCapacity, targetWater) {
        if (!container) return;

        const ratio = targetWater > 0 ? totalCapacity / targetWater : 0;
        const pct = Math.min(ratio * 100, 100);
        const overflow = ratio > 1;

        let barColor;
        if (overflow) {
            barColor = 'linear-gradient(90deg, var(--accent-green), var(--accent-cyan))';
        } else if (ratio >= 0.7) {
            barColor = 'linear-gradient(90deg, var(--accent-yellow), var(--accent-green))';
        } else {
            barColor = 'linear-gradient(90deg, var(--accent-red), var(--accent-orange))';
        }

        const statusText = overflow ? '容量充足' : ratio >= 0.7 ? '容量接近' : '容量不足';
        const statusColor = overflow ? 'var(--accent-green)' : ratio >= 0.7 ? 'var(--accent-yellow)' : 'var(--accent-red)';

        container.innerHTML = `<div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:16px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">
                <span style="font-size:14px;font-weight:600;color:var(--text-primary);">容量与需求</span>
                <span style="font-size:12px;color:${statusColor};font-weight:600;">${statusText}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="font-size:12px;color:var(--text-secondary);">总容量: <strong style="color:var(--accent-cyan);font-family:Consolas,monospace;">${totalCapacity.toFixed(0)} m³</strong></span>
                <span style="font-size:12px;color:var(--text-secondary);">目标需水: <strong style="color:var(--accent-blue);font-family:Consolas,monospace;">${targetWater.toFixed(0)} m³</strong></span>
            </div>
            <div style="height:20px;background:rgba(255,255,255,0.05);border-radius:10px;overflow:hidden;">
                <div style="height:100%;width:${pct}%;background:${barColor};border-radius:10px;transition:width 0.6s ease;"></div>
            </div>
            <div style="text-align:center;margin-top:6px;font-size:13px;font-weight:700;color:var(--text-primary);font-family:Consolas,monospace;">
                ${pct.toFixed(1)}%
            </div>
        </div>`;
    }

    renderRecommendations(container, recommendations) {
        if (!container) return;
        if (!recommendations || recommendations.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px;">暂无优化建议</div>';
            return;
        }

        const severityIcons = {
            high: '⚠️',
            medium: '💡',
            low: 'ℹ️'
        };
        const severityColors = {
            high: 'var(--accent-red)',
            medium: 'var(--accent-yellow)',
            low: 'var(--accent-blue)'
        };

        container.innerHTML = recommendations.map((r, i) => {
            const severity = r.severity || r.priority || 'medium';
            const icon = severityIcons[severity] || '💡';
            const color = severityColors[severity] || 'var(--accent-yellow)';
            return `<div style="background:linear-gradient(135deg,rgba(6,182,212,0.05),rgba(59,130,246,0.05));border:1px solid rgba(6,182,212,0.2);border-left:4px solid ${color};border-radius:var(--radius-sm);padding:12px 14px;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="font-size:16px;">${icon}</span>
                    <span style="font-size:13px;font-weight:600;color:var(--text-primary);">${r.title || r.type || `建议 #${i + 1}`}</span>
                    <span style="margin-left:auto;font-size:10px;color:${color};text-transform:uppercase;letter-spacing:0.5px;padding:2px 8px;border-radius:10px;background:rgba(255,255,255,0.05);">${severity}</span>
                </div>
                <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${r.message || r.description || r.content || ''}</div>
            </div>`;
        }).join('');
    }
}
