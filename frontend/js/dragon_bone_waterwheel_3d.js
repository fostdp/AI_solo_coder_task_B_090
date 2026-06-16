import { WaterwheelScene } from './waterwheel.js';
import { WaterParticleSystem, SteamMistEffect } from './particles.js';

export class DragonBoneWaterwheel3D {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.wheelScene = null;
        this.particleSystem = null;
        this.steamEffect = null;
        this._particleTimer = null;
        this._syncTimer = null;
        this._lastSensorData = {
            rotational_speed: 0,
            water_lift: 0,
            water_level_diff: 2
        };
    }

    init() {
        try {
            this.wheelScene = new WaterwheelScene(this.canvasId);
            this.particleSystem = new WaterParticleSystem(this.wheelScene.scene);
            this.steamEffect = new SteamMistEffect(this.wheelScene.scene);

            this._particleTimer = setInterval(() => {
                if (this.particleSystem) {
                    this.particleSystem.update();
                }
                if (this.steamEffect) {
                    this.steamEffect.update(
                        this._lastSensorData.rotational_speed || 15,
                        this._lastSensorData.water_lift || 100
                    );
                }
            }, 16);

            this._syncTimer = setInterval(() => {
                this._syncScene();
            }, 500);
        } catch (e) {
            console.error('龙骨水车3D场景初始化失败:', e);
        }
        return this;
    }

    _syncScene() {
        const d = this._lastSensorData;
        if (this.wheelScene) {
            this.wheelScene.setSpeed(d.rotational_speed || 0);
            this.wheelScene.setWaterLevel(d.water_level_diff || 2);
        }
        if (this.particleSystem) {
            this.particleSystem.setWaterFlow(d.water_lift || 0, d.rotational_speed || 0);
        }
    }

    setSpeed(rpm) {
        if (this.wheelScene) this.wheelScene.setSpeed(rpm);
        this._lastSensorData.rotational_speed = rpm;
    }

    setWaterLevel(diff) {
        if (this.wheelScene) this.wheelScene.setWaterLevel(diff);
        this._lastSensorData.water_level_diff = diff;
    }

    setWaterFlow(liftLpm, rpm) {
        if (this.particleSystem) this.particleSystem.setWaterFlow(liftLpm, rpm);
        this._lastSensorData.water_lift = liftLpm;
        this._lastSensorData.rotational_speed = rpm;
    }

    setBrokenBlade(index) {
        if (this.wheelScene) this.wheelScene.setBrokenBlade(index);
    }

    updateSensorData(data) {
        this._lastSensorData = {
            rotational_speed: data.rotational_speed || this._lastSensorData.rotational_speed,
            water_lift: data.water_lift || this._lastSensorData.water_lift,
            water_level_diff: data.water_level_diff || this._lastSensorData.water_level_diff,
        };
        this._syncScene();
    }

    toggleAutoRotate() {
        if (this.wheelScene) return this.wheelScene.toggleAutoRotate();
        return false;
    }

    toggleWireframe() {
        if (this.wheelScene) return this.wheelScene.toggleWireframe();
        return false;
    }

    resetView() {
        if (this.wheelScene) this.wheelScene.resetView();
    }

    toggleParticles() {
        if (this.particleSystem) return this.particleSystem.toggle();
        return false;
    }

    get scene() {
        return this.wheelScene ? this.wheelScene.scene : null;
    }

    get rotationalSpeed() {
        return this._lastSensorData.rotational_speed;
    }

    set rotationalSpeed(v) {
        this.setSpeed(v);
    }

    get waterLevelDiff() {
        return this._lastSensorData.water_level_diff;
    }

    set waterLevelDiff(v) {
        this.setWaterLevel(v);
    }

    get waterLiftRate() {
        return this._lastSensorData.water_lift;
    }

    dispose() {
        if (this._particleTimer) clearInterval(this._particleTimer);
        if (this._syncTimer) clearInterval(this._syncTimer);
        if (this.particleSystem) this.particleSystem.dispose();
        this.wheelScene = null;
        this.particleSystem = null;
        this.steamEffect = null;
    }
}
