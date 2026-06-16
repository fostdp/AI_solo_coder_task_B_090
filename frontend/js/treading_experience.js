class TreadingExperience {
    constructor(wheel3D) {
        this.wheel3D = wheel3D;
        this.sessionId = null;
        this.userName = '';
        this.difficulty = 3;
        this.isRunning = false;
        this._loopId = null;
        this._keysDown = new Set();
        this._strokeTimestamps = [];
        this._elapsed = 0;
        this._lastLoopTime = 0;
        this._currentRpm = 0;
        this._waterLifted = 0;
        this._calories = 0;
        this._fatigueFactor = 1;
        this._localPhysicsState = null;
        this._apiBaseUrl = this._resolveApiBase();
    }

    _resolveApiBase() {
        const origin = window.location.origin;
        const port = window.location.port;
        if (port === '3000' || port === '5000') {
            return `${window.location.protocol}//${window.location.hostname}:8000`;
        }
        return origin;
    }

    async startSession(userName, difficulty) {
        this.userName = userName || '匿名用户';
        this.difficulty = Math.max(1, Math.min(5, difficulty || 3));
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/treading/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: this.userName, difficulty: this.difficulty })
            });
            const data = await resp.json();
            this.sessionId = data.session_id;
            this._resetState();
            return data.session_id;
        } catch (e) {
            console.error('启动踏车会话失败:', e);
            this.sessionId = 'local_' + Date.now();
            this._resetState();
            return this.sessionId;
        }
    }

    _resetState() {
        this._elapsed = 0;
        this._lastLoopTime = 0;
        this._currentRpm = 0;
        this._waterLifted = 0;
        this._calories = 0;
        this._fatigueFactor = 1;
        this._strokeTimestamps = [];
        this._localPhysicsState = null;
    }

    async updateSession(pedalForce, pedalCadence, elapsed) {
        if (!this.sessionId) return null;
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/treading/${this.sessionId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pedal_force: pedalForce,
                    pedal_cadence: pedalCadence,
                    elapsed: elapsed,
                    dt: 0.1
                })
            });
            return await resp.json();
        } catch (e) {
            console.warn('更新踏车会话失败，使用本地物理:', e);
            return this._localPhysicsStep(pedalForce, pedalCadence, 0.1);
        }
    }

    async endSession() {
        if (!this.sessionId) return null;
        this.stopLocalSimulation();
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/treading/${this.sessionId}/end`, {
                method: 'POST'
            });
            const data = await resp.json();
            this.sessionId = null;
            return data;
        } catch (e) {
            console.error('结束踏车会话失败:', e);
            const summary = {
                session_id: this.sessionId,
                user_name: this.userName,
                duration_seconds: this._elapsed,
                water_lifted_liters: this._waterLifted,
                calories_burned: this._calories,
                max_speed_rpm: this._currentRpm,
                avg_speed_rpm: this._currentRpm,
                difficulty_level: this.difficulty
            };
            this.sessionId = null;
            return summary;
        }
    }

    async loadLeaderboard(metric) {
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/treading/leaderboard?metric=${metric || 'water_lifted_liters'}`);
            return await resp.json();
        } catch (e) {
            console.error('加载排行榜失败:', e);
            return { metric: metric || 'water_lifted_liters', leaderboard: [] };
        }
    }

    getCurrentState() {
        return {
            pedal_cadence: this._strokeTimestamps.length > 1 ? this._estimateCadence() : 0,
            wheel_rpm: this._currentRpm,
            water_lifted_liters: this._waterLifted,
            calories_burned: this._calories,
            duration_seconds: this._elapsed,
            fatigue_factor: this._fatigueFactor
        };
    }

    startLocalSimulation() {
        if (this.isRunning) return;
        this.isRunning = true;
        this._lastLoopTime = performance.now();
        this._boundKeyDown = (e) => this.handleKeyDown(e);
        this._boundKeyUp = (e) => this.handleKeyUp(e);
        document.addEventListener('keydown', this._boundKeyDown);
        document.addEventListener('keyup', this._boundKeyUp);
        this._loopId = requestAnimationFrame(() => this._treadLoop());
    }

    stopLocalSimulation() {
        this.isRunning = false;
        if (this._loopId) {
            cancelAnimationFrame(this._loopId);
            this._loopId = null;
        }
        if (this._boundKeyDown) {
            document.removeEventListener('keydown', this._boundKeyDown);
            this._boundKeyDown = null;
        }
        if (this._boundKeyUp) {
            document.removeEventListener('keyup', this._boundKeyUp);
            this._boundKeyUp = null;
        }
        this._keysDown.clear();
        if (this.wheel3D) {
            this.wheel3D.setSpeed(0);
            this.wheel3D.setWaterFlow(0, 0);
        }
    }

    handleKeyDown(e) {
        if (e.code === 'Space' || e.code === 'ArrowUp') {
            e.preventDefault();
            if (!this._keysDown.has(e.code)) {
                this._keysDown.add(e.code);
                this._strokeTimestamps.push(performance.now());
            }
        }
    }

    handleKeyUp(e) {
        if (e.code === 'Space' || e.code === 'ArrowUp') {
            this._keysDown.delete(e.code);
        }
    }

    _estimateCadence() {
        const now = performance.now();
        const windowMs = 2000;
        this._strokeTimestamps = this._strokeTimestamps.filter(t => now - t < windowMs);
        if (this._strokeTimestamps.length < 2) {
            return this._keysDown.size > 0 ? 15 : 0;
        }
        const intervals = [];
        for (let i = 1; i < this._strokeTimestamps.length; i++) {
            intervals.push(this._strokeTimestamps[i] - this._strokeTimestamps[i - 1]);
        }
        const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        if (avgInterval <= 0) return 60;
        return Math.min(120, 60000 / avgInterval);
    }

    _estimateForce(cadence) {
        const baseForce = 80;
        const cadenceFactor = Math.min(cadence / 60, 1.5);
        return baseForce * (0.5 + 0.5 * cadenceFactor);
    }

    _localPhysicsStep(pedalForce, pedalCadence, dt) {
        const FATIGUE_TAU = 600;
        const GEAR_RATIO = 3.5;
        const INERTIA_TAU = 2.0;
        const WATER_EFFICIENCY = 0.55;
        const PUMP_LITERS_PER_JOULE = 0.000102;
        const CALORIE_RATE_LOW = 5.0;
        const CALORIE_RATE_HIGH = 8.0;
        const PEAK_POWER = 300;

        this._fatigueFactor = Math.exp(-this._elapsed / FATIGUE_TAU);
        const rawPower = pedalForce * (2 * Math.PI * pedalCadence / 60) * 0.15;
        const sustainedCap = 75 + (150 - 75) * this._fatigueFactor;
        const peakCap = PEAK_POWER * (0.5 + 0.5 * this._fatigueFactor);
        const effectivePower = Math.max(75 * 0.3, Math.min(peakCap, Math.min(sustainedCap, rawPower)));

        const targetRpm = pedalCadence * GEAR_RATIO;
        const alpha = 1.0 - Math.exp(-dt / INERTIA_TAU);
        this._currentRpm = this._currentRpm + (targetRpm - this._currentRpm) * alpha;

        const energyJ = effectivePower * dt;
        const usefulEnergy = energyJ * WATER_EFFICIENCY;
        this._waterLifted += usefulEnergy * PUMP_LITERS_PER_JOULE;

        const intensityRatio = Math.min(1, effectivePower / PEAK_POWER);
        const calRate = CALORIE_RATE_LOW + (CALORIE_RATE_HIGH - CALORIE_RATE_LOW) * intensityRatio;
        this._calories += calRate * (dt / 60) * (0.7 + 0.3 * this._fatigueFactor);

        return {
            power_w: effectivePower,
            wheel_rpm: this._currentRpm,
            pedal_rpm: pedalCadence,
            fatigue_factor: this._fatigueFactor,
            calorie_rate_kcal_min: calRate * (0.7 + 0.3 * this._fatigueFactor),
            mechanical_efficiency: 0.7,
            overall_efficiency: WATER_EFFICIENCY
        };
    }

    _treadLoop() {
        if (!this.isRunning) return;

        const now = performance.now();
        const dtMs = Math.min(now - this._lastLoopTime, 200);
        this._lastLoopTime = now;
        const dt = dtMs / 1000;
        this._elapsed += dt;

        const isPedaling = this._keysDown.size > 0;
        const cadence = isPedaling ? this._estimateCadence() : 0;
        const force = isPedaling ? this._estimateForce(cadence) : 0;

        let state = null;
        if (this.sessionId && !this.sessionId.startsWith('local_')) {
            state = this.updateSession(force, cadence, this._elapsed);
        } else {
            state = this._localPhysicsStep(force, cadence, dt);
        }

        if (state && !(state instanceof Promise)) {
            this._currentRpm = state.wheel_rpm || this._currentRpm;
            this._update3DScene(state);
            this._updateDashboard(state);
        } else if (isPedaling) {
            this._update3DScene({ wheel_rpm: this._currentRpm });
        }

        if (!isPedaling && this._currentRpm > 0) {
            const decayAlpha = 1.0 - Math.exp(-dt / 3.0);
            this._currentRpm = this._currentRpm * (1 - decayAlpha);
            if (this._currentRpm < 0.5) this._currentRpm = 0;
            this._update3DScene({ wheel_rpm: this._currentRpm });
            this._updateDashboard({ wheel_rpm: this._currentRpm, pedal_rpm: 0, fatigue_factor: this._fatigueFactor });
        }

        this._loopId = requestAnimationFrame(() => this._treadLoop());
    }

    _update3DScene(state) {
        if (!this.wheel3D) return;
        const rpm = state.wheel_rpm || 0;
        this.wheel3D.setSpeed(rpm);
        const waterLpm = rpm * 0.6;
        this.wheel3D.setWaterFlow(waterLpm, rpm);
    }

    _updateDashboard(state) {
        const rpmEl = document.getElementById('tread-rpm');
        if (rpmEl) rpmEl.textContent = (state.pedal_rpm || 0).toFixed(1);

        const waterEl = document.getElementById('tread-water');
        if (waterEl) waterEl.textContent = this._waterLifted.toFixed(2);

        const calEl = document.getElementById('tread-calories');
        if (calEl) calEl.textContent = this._calories.toFixed(2);

        const timeEl = document.getElementById('tread-time');
        if (timeEl) {
            const mins = Math.floor(this._elapsed / 60);
            const secs = Math.floor(this._elapsed % 60);
            timeEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        const fatigueEl = document.getElementById('tread-fatigue');
        if (fatigueEl) {
            const fatiguePct = (1 - (state.fatigue_factor || 1)) * 100;
            fatigueEl.textContent = fatiguePct.toFixed(1) + '%';
            fatigueEl.style.color = fatiguePct > 60 ? '#ef4444' : fatiguePct > 30 ? '#f59e0b' : '#10b981';
        }

        const gaugeEl = document.getElementById('tread-rpm-gauge');
        if (gaugeEl) {
            const rpm = state.pedal_rpm || 0;
            const pct = Math.min(100, (rpm / 120) * 100);
            gaugeEl.style.width = pct + '%';
            gaugeEl.style.background = rpm > 90 ? '#ef4444' : rpm > 60 ? '#f59e0b' : '#3b82f6';
        }
    }

    renderControls(container) {
        container.innerHTML = `
            <div class="tread-controls">
                <div class="tread-control-row">
                    <label for="tread-name">用户名</label>
                    <input type="text" id="tread-name" placeholder="输入用户名" value="匿名用户" />
                </div>
                <div class="tread-control-row">
                    <label for="tread-difficulty">难度</label>
                    <select id="tread-difficulty">
                        <option value="1">1 - 轻松</option>
                        <option value="2">2 - 简单</option>
                        <option value="3" selected>3 - 标准</option>
                        <option value="4">4 - 困难</option>
                        <option value="5">5 - 极限</option>
                    </select>
                </div>
                <div class="tread-control-row">
                    <button id="tread-start-btn">开始踏车</button>
                    <button id="tread-stop-btn" disabled>停止</button>
                </div>
                <div class="tread-hint">按 空格键 或 ↑键 踩踏水车，快速按键提高踏频</div>
            </div>
        `;

        const startBtn = container.querySelector('#tread-start-btn');
        const stopBtn = container.querySelector('#tread-stop-btn');

        startBtn.addEventListener('click', async () => {
            const name = container.querySelector('#tread-name').value || '匿名用户';
            const diff = parseInt(container.querySelector('#tread-difficulty').value) || 3;
            await this.startSession(name, diff);
            this.startLocalSimulation();
            startBtn.disabled = true;
            stopBtn.disabled = false;
        });

        stopBtn.addEventListener('click', async () => {
            const summary = await this.endSession();
            startBtn.disabled = false;
            stopBtn.disabled = true;
            if (summary) {
                const summaryContainer = document.getElementById('tread-summary');
                if (summaryContainer) this.renderEndSummary(summaryContainer, summary);
            }
        });
    }

    renderDashboard(container) {
        container.innerHTML = `
            <div class="tread-dashboard">
                <div class="tread-gauge-section">
                    <div class="tread-gauge-label">踏频 (RPM)</div>
                    <div class="tread-gauge-bar">
                        <div class="tread-gauge-fill" id="tread-rpm-gauge" style="width:0%;background:#3b82f6;"></div>
                    </div>
                    <div class="tread-gauge-value"><span id="tread-rpm">0.0</span> rpm</div>
                </div>
                <div class="tread-stats-grid">
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">提水量</div>
                        <div class="tread-stat-value"><span id="tread-water">0.00</span> L</div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">消耗热量</div>
                        <div class="tread-stat-value"><span id="tread-calories">0.00</span> kcal</div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">持续时间</div>
                        <div class="tread-stat-value"><span id="tread-time">0:00</span></div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">疲劳度</div>
                        <div class="tread-stat-value"><span id="tread-fatigue">0.0%</span></div>
                    </div>
                </div>
            </div>
        `;
    }

    renderLeaderboard(container, data) {
        const items = (data && data.leaderboard) || [];
        if (items.length === 0) {
            container.innerHTML = '<div class="tread-empty">暂无排行榜数据</div>';
            return;
        }
        const rows = items.map(entry => `
            <tr>
                <td class="tread-rank">${entry.rank}</td>
                <td>${entry.user_name}</td>
                <td>${entry.water_lifted_liters.toFixed(2)} L</td>
                <td>${entry.calories_burned.toFixed(2)} kcal</td>
                <td>${(entry.duration_seconds / 60).toFixed(1)} min</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <table class="tread-leaderboard">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>用户</th>
                        <th>提水量</th>
                        <th>消耗热量</th>
                        <th>持续时间</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    renderEndSummary(container, data) {
        const durationMin = (data.duration_seconds / 60).toFixed(1);
        container.innerHTML = `
            <div class="tread-summary-card">
                <div class="tread-summary-title">踏车结束 - 成绩单</div>
                <div class="tread-summary-grid">
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">用户</span>
                        <span class="tread-summary-value">${data.user_name || this.userName}</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">持续时间</span>
                        <span class="tread-summary-value">${durationMin} 分钟</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">提水量</span>
                        <span class="tread-summary-value">${(data.water_lifted_liters || 0).toFixed(2)} L</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">消耗热量</span>
                        <span class="tread-summary-value">${(data.calories_burned || 0).toFixed(2)} kcal</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">最大转速</span>
                        <span class="tread-summary-value">${(data.max_speed_rpm || 0).toFixed(1)} rpm</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">平均转速</span>
                        <span class="tread-summary-value">${(data.avg_speed_rpm || 0).toFixed(1)} rpm</span>
                    </div>
                    <div class="tread-summary-item">
                        <span class="tread-summary-label">难度</span>
                        <span class="tread-summary-value">${data.difficulty_level || this.difficulty}</span>
                    </div>
                </div>
            </div>
        `;
    }
}

export class VRWaterwheelPanel extends TreadingExperience {
    constructor(wheel3D) {
        super(wheel3D);
    }

    async startSession(userName, difficulty) {
        this.userName = userName || '匿名用户';
        this.difficulty = Math.max(1, Math.min(5, difficulty || 3));
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/vr/experience/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: this.userName, difficulty: this.difficulty })
            });
            const data = await resp.json();
            this.sessionId = data.session_id;
            this._resetState();
            return data.session_id;
        } catch (e) {
            console.error('启动VR水车会话失败:', e);
            this.sessionId = 'local_' + Date.now();
            this._resetState();
            return this.sessionId;
        }
    }

    async updateSession(pedalForce, pedalCadence, elapsed) {
        if (!this.sessionId) return null;
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/vr/experience/${this.sessionId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pedal_force: pedalForce,
                    pedal_cadence: pedalCadence,
                    elapsed: elapsed,
                    dt: 0.1
                })
            });
            return await resp.json();
        } catch (e) {
            console.warn('更新VR水车会话失败，使用本地物理:', e);
            return this._localPhysicsStep(pedalForce, pedalCadence, 0.1);
        }
    }

    async endSession() {
        if (!this.sessionId) return null;
        this.stopLocalSimulation();
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/vr/experience/${this.sessionId}/end`, {
                method: 'POST'
            });
            const data = await resp.json();
            this.sessionId = null;
            return data;
        } catch (e) {
            console.error('结束VR水车会话失败:', e);
            const summary = {
                session_id: this.sessionId,
                user_name: this.userName,
                duration_seconds: this._elapsed,
                water_lifted_liters: this._waterLifted,
                calories_burned: this._calories,
                max_speed_rpm: this._currentRpm,
                avg_speed_rpm: this._currentRpm,
                difficulty_level: this.difficulty
            };
            this.sessionId = null;
            return summary;
        }
    }

    async loadLeaderboard(metric) {
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/vr/leaderboard?metric=${metric || 'water_lifted_liters'}`);
            return await resp.json();
        } catch (e) {
            console.error('加载排行榜失败:', e);
            return { metric: metric || 'water_lifted_liters', leaderboard: [] };
        }
    }

    async getForceFeedback(sessionId, pedalForce, cadence, wheelRpm, waterLift, fatigue) {
        if (!sessionId) return null;
        try {
            const resp = await fetch(`${this._apiBaseUrl}/api/vr/experience/${sessionId}/force-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pedal_force: pedalForce,
                    pedal_cadence: cadence,
                    wheel_rpm: wheelRpm,
                    water_lift_m: waterLift,
                    fatigue_factor: fatigue
                })
            });
            return await resp.json();
        } catch (e) {
            console.error('获取力反馈失败:', e);
            return null;
        }
    }

    renderForceFeedback(container, feedback) {
        if (!feedback) {
            container.innerHTML = '<div class="tread-empty">暂无力反馈数据</div>';
            return;
        }
        container.innerHTML = `
            <div class="tread-dashboard">
                <div class="tread-gauge-section">
                    <div class="tread-gauge-label">踏板阻力 (N)</div>
                    <div class="tread-gauge-bar">
                        <div class="tread-gauge-fill" style="width:${Math.min(100, (feedback.pedal_resistance_n / 200) * 100)}%;background:${feedback.pedal_resistance_n > 150 ? '#ef4444' : feedback.pedal_resistance_n > 100 ? '#f59e0b' : '#3b82f6'};"></div>
                    </div>
                    <div class="tread-gauge-value">${(feedback.pedal_resistance_n || 0).toFixed(1)} N</div>
                </div>
                <div class="tread-stats-grid">
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">水阻扭矩</div>
                        <div class="tread-stat-value">${(feedback.water_resistance_torque_nm || 0).toFixed(2)} N·m</div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">负载感受</div>
                        <div class="tread-stat-value">${feedback.load_feel || '正常'}</div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">振动强度</div>
                        <div class="tread-stat-value">${(feedback.vibration_intensity || 0).toFixed(2)}</div>
                    </div>
                    <div class="tread-stat-card">
                        <div class="tread-stat-label">振动频率</div>
                        <div class="tread-stat-value">${(feedback.vibration_freq_hz || 0).toFixed(1)} Hz</div>
                    </div>
                </div>
            </div>
        `;
    }

    addForceHapticEffect(feedback) {
        if (!feedback || !navigator.vibrate) return;
        const intensity = feedback.vibration_intensity || 0;
        const freq = feedback.vibration_freq_hz || 0;
        if (intensity <= 0 || freq <= 0) return;
        const pulseDuration = Math.max(10, Math.min(200, 1000 / freq));
        const pauseDuration = Math.max(10, pulseDuration * (1 / Math.max(0.1, Math.min(1, intensity))) - pulseDuration);
        const pattern = [];
        const totalDuration = 1000;
        let current = 0;
        while (current < totalDuration) {
            pattern.push(Math.min(pulseDuration, totalDuration - current));
            current += pulseDuration;
            if (current < totalDuration) {
                pattern.push(Math.min(pauseDuration, totalDuration - current));
                current += pauseDuration;
            }
        }
        navigator.vibrate(pattern);
    }

    getCurrentState() {
        return super.getCurrentState();
    }

    startLocalSimulation() {
        return super.startLocalSimulation();
    }

    stopLocalSimulation() {
        return super.stopLocalSimulation();
    }

    renderControls(container) {
        return super.renderControls(container);
    }

    renderDashboard(container) {
        return super.renderDashboard(container);
    }

    renderLeaderboard(container, data) {
        return super.renderLeaderboard(container, data);
    }

    renderEndSummary(container, data) {
        return super.renderEndSummary(container, data);
    }
}

export { TreadingExperience };
