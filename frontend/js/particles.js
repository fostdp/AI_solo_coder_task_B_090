import * as THREE from 'three';

export class WaterParticleSystem {
    constructor(scene) {
        this.scene = scene;
        this.liftParticles = [];
        this.spillParticles = [];
        this.flowParticles = [];
        this.splashParticles = [];

        this.maxLiftParticles = 300;
        this.maxSpillParticles = 150;
        this.maxFlowParticles = 500;
        this.maxSplashParticles = 100;

        this.waterLiftRate = 0;
        this.rotationalSpeed = 0;
        this.enabled = true;

        this.initLiftParticles();
        this.initSpillParticles();
        this.initFlowParticles();
        this.initSplashParticles();

        this.clock = new THREE.Clock();
        this.time = 0;
    }

    createWaterTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(100, 200, 255, 1)');
        gradient.addColorStop(0.4, 'rgba(80, 180, 240, 0.8)');
        gradient.addColorStop(0.7, 'rgba(60, 150, 220, 0.4)');
        gradient.addColorStop(1, 'rgba(40, 120, 200, 0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);

        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    }

    initLiftParticles() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxLiftParticles * 3);
        const colors = new Float32Array(this.maxLiftParticles * 3);
        const sizes = new Float32Array(this.maxLiftParticles);
        const velocities = [];
        const lifetimes = [];
        const alives = [];

        for (let i = 0; i < this.maxLiftParticles; i++) {
            positions[i * 3] = -100;
            positions[i * 3 + 1] = -100;
            positions[i * 3 + 2] = 0;

            colors[i * 3] = 0.3 + Math.random() * 0.1;
            colors[i * 3 + 1] = 0.7 + Math.random() * 0.2;
            colors[i * 3 + 2] = 1.0;

            sizes[i] = 0.08 + Math.random() * 0.06;

            velocities.push(new THREE.Vector3(0, 0, 0));
            lifetimes.push(0);
            alives.push(false);
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 0.15,
            vertexColors: true,
            transparent: true,
            opacity: 0.85,
            map: this.createWaterTexture(),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.liftSystem = new THREE.Points(geometry, material);
        this.liftSystem.renderOrder = 2;

        this.liftParticlesData = { velocities, lifetimes, alives };

        this.scene.add(this.liftSystem);
    }

    initSpillParticles() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxSpillParticles * 3);
        const colors = new Float32Array(this.maxSpillParticles * 3);
        const sizes = new Float32Array(this.maxSpillParticles);
        const velocities = [];
        const lifetimes = [];
        const alives = [];

        for (let i = 0; i < this.maxSpillParticles; i++) {
            positions[i * 3] = -100;
            positions[i * 3 + 1] = -100;
            positions[i * 3 + 2] = 0;

            colors[i * 3] = 0.25 + Math.random() * 0.1;
            colors[i * 3 + 1] = 0.7 + Math.random() * 0.15;
            colors[i * 3 + 2] = 0.95 + Math.random() * 0.05;

            sizes[i] = 0.05 + Math.random() * 0.04;

            velocities.push(new THREE.Vector3(0, 0, 0));
            lifetimes.push(0);
            alives.push(false);
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 0.1,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
            map: this.createWaterTexture(),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.spillSystem = new THREE.Points(geometry, material);
        this.scene.add(this.spillSystem);

        this.spillParticlesData = { velocities, lifetimes, alives };
    }

    initFlowParticles() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxFlowParticles * 3);
        const colors = new Float32Array(this.maxFlowParticles * 3);
        const sizes = new Float32Array(this.maxFlowParticles);
        const progress = [];
        const offsets = [];
        const alives = [];

        for (let i = 0; i < this.maxFlowParticles; i++) {
            positions[i * 3] = -100;
            positions[i * 3 + 1] = -100;
            positions[i * 3 + 2] = 0;

            colors[i * 3] = 0.2 + Math.random() * 0.15;
            colors[i * 3 + 1] = 0.65 + Math.random() * 0.2;
            colors[i * 3 + 2] = 0.9 + Math.random() * 0.1;

            sizes[i] = 0.06 + Math.random() * 0.06;

            progress.push(Math.random());
            offsets.push(Math.random() * 0.4 - 0.2);
            alives.push(Math.random() > 0.3);
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 0.12,
            vertexColors: true,
            transparent: true,
            opacity: 0.7,
            map: this.createWaterTexture(),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.flowSystem = new THREE.Points(geometry, material);
        this.scene.add(this.flowSystem);

        this.flowParticlesData = { progress, offsets, alives };
    }

    initSplashParticles() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxSplashParticles * 3);
        const colors = new Float32Array(this.maxSplashParticles * 3);
        const sizes = new Float32Array(this.maxSplashParticles);
        const velocities = [];
        const lifetimes = [];
        const alives = [];

        for (let i = 0; i < this.maxSplashParticles; i++) {
            positions[i * 3] = -100;
            positions[i * 3 + 1] = -100;
            positions[i * 3 + 2] = 0;

            colors[i * 3] = 0.4;
            colors[i * 3 + 1] = 0.8;
            colors[i * 3 + 2] = 1.0;

            sizes[i] = 0.03 + Math.random() * 0.03;

            velocities.push(new THREE.Vector3(0, 0, 0));
            lifetimes.push(0);
            alives.push(false);
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 0.08,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
            map: this.createWaterTexture(),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.splashSystem = new THREE.Points(geometry, material);
        this.scene.add(this.splashSystem);

        this.splashParticlesData = { velocities, lifetimes, alives };
    }

    setWaterFlow(waterLiftLpm, rotationalSpeed) {
        this.waterLiftRate = waterLiftLpm;
        this.rotationalSpeed = rotationalSpeed;
    }

    spawnLiftParticle() {
        const { alives, velocities, lifetimes } = this.liftParticlesData;
        const positions = this.liftSystem.geometry.attributes.position.array;

        for (let i = 0; i < this.maxLiftParticles; i++) {
            if (!alives[i]) {
                const side = Math.random() > 0.5 ? 1 : -1;
                const bladeZ = (Math.random() - 0.5) * 0.4;

                positions[i * 3] = -0.08 + Math.random() * 0.02;
                positions[i * 3 + 1] = 1.8 + Math.random() * 0.3;
                positions[i * 3 + 2] = bladeZ;

                velocities[i].set(
                    0.1 + Math.random() * 0.1,
                    0.5 + Math.random() * 0.3,
                    (Math.random() - 0.5) * 0.05
                );

                lifetimes[i] = 3.5 + Math.random() * 1;
                alives[i] = true;
                return i;
            }
        }
        return -1;
    }

    spawnSpillParticles(count) {
        const { alives, velocities, lifetimes } = this.spillParticlesData;
        const positions = this.spillSystem.geometry.attributes.position.array;
        let spawned = 0;

        for (let i = 0; i < this.maxSpillParticles && spawned < count; i++) {
            if (!alives[i]) {
                positions[i * 3] = 0.4 + Math.random() * 0.3;
                positions[i * 3 + 1] = 5.0 + Math.random() * 0.2;
                positions[i * 3 + 2] = (Math.random() - 0.5) * 0.3;

                velocities[i].set(
                    0.5 + Math.random() * 0.8,
                    -0.5 + Math.random() * 0.3,
                    (Math.random() - 0.5) * 0.4
                );

                lifetimes[i] = 1.5 + Math.random() * 0.8;
                alives[i] = true;
                spawned++;
            }
        }
    }

    spawnSplash(x, y, z, count) {
        const { alives, velocities, lifetimes } = this.splashParticlesData;
        const positions = this.splashSystem.geometry.attributes.position.array;
        let spawned = 0;

        for (let i = 0; i < this.maxSplashParticles && spawned < count; i++) {
            if (!alives[i]) {
                positions[i * 3] = x + (Math.random() - 0.5) * 0.1;
                positions[i * 3 + 1] = y;
                positions[i * 3 + 2] = z + (Math.random() - 0.5) * 0.1;

                const angle = Math.random() * Math.PI * 2;
                const speed = 0.5 + Math.random() * 1.5;
                velocities[i].set(
                    Math.cos(angle) * speed,
                    0.8 + Math.random() * 1.2,
                    Math.sin(angle) * speed
                );

                lifetimes[i] = 0.4 + Math.random() * 0.4;
                alives[i] = true;
                spawned++;
            }
        }
    }

    updateLiftParticles(dt) {
        const { alives, velocities, lifetimes } = this.liftParticlesData;
        const positions = this.liftSystem.geometry.attributes.position.array;
        const liftIntensity = Math.min(1, this.waterLiftRate / 200);

        const spawnRate = liftIntensity * this.rotationalSpeed / 15;
        if (Math.random() < spawnRate * dt * 10) {
            this.spawnLiftParticle();
        }

        for (let i = 0; i < this.maxLiftParticles; i++) {
            if (!alives[i]) continue;

            lifetimes[i] -= dt;
            if (lifetimes[i] <= 0) {
                alives[i] = false;
                positions[i * 3] = -100;
                continue;
            }

            velocities[i].y += -0.3 * dt;
            velocities[i].x += (0.15 - velocities[i].x) * dt;

            positions[i * 3] += velocities[i].x * dt;
            positions[i * 3 + 1] += velocities[i].y * dt;
            positions[i * 3 + 2] += velocities[i].z * dt;

            if (positions[i * 3 + 1] > 4.8 && positions[i * 3] > 0.3) {
                if (Math.random() < 0.1) {
                    this.spawnSplash(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2], 3);
                }
                alives[i] = false;
                positions[i * 3] = -100;
            }

            if (positions[i * 3 + 1] < 0.5) {
                this.spawnSplash(positions[i * 3], 0.5, positions[i * 3 + 2], 2);
                alives[i] = false;
                positions[i * 3] = -100;
            }
        }

        this.liftSystem.geometry.attributes.position.needsUpdate = true;
    }

    updateSpillParticles(dt) {
        const { alives, velocities, lifetimes } = this.spillParticlesData;
        const positions = this.spillSystem.geometry.attributes.position.array;
        const liftIntensity = Math.min(1, this.waterLiftRate / 200);

        if (liftIntensity > 0.1 && Math.random() < liftIntensity * 5 * dt) {
            this.spawnSpillParticles(Math.ceil(liftIntensity * 3));
        }

        for (let i = 0; i < this.maxSpillParticles; i++) {
            if (!alives[i]) continue;

            lifetimes[i] -= dt;
            if (lifetimes[i] <= 0) {
                alives[i] = false;
                positions[i * 3] = -100;
                continue;
            }

            velocities[i].y -= 3 * dt;

            positions[i * 3] += velocities[i].x * dt;
            positions[i * 3 + 1] += velocities[i].y * dt;
            positions[i * 3 + 2] += velocities[i].z * dt;

            if (positions[i * 3 + 1] < 3.2) {
                this.spawnSplash(positions[i * 3], 3.2, positions[i * 3 + 2], 4);
                alives[i] = false;
                positions[i * 3] = -100;
            }
        }

        this.spillSystem.geometry.attributes.position.needsUpdate = true;
    }

    updateFlowParticles(dt) {
        const { progress, offsets, alives } = this.flowParticlesData;
        const positions = this.flowSystem.geometry.attributes.position.array;
        const flowSpeed = Math.max(0.1, this.rotationalSpeed / 30);

        for (let i = 0; i < this.maxFlowParticles; i++) {
            if (!alives[i]) {
                if (Math.random() < flowSpeed * dt * 2) {
                    alives[i] = true;
                    progress[i] = 0;
                    offsets[i] = Math.random() * 0.4 - 0.2;
                }
                continue;
            }

            progress[i] += flowSpeed * dt * 0.15;

            if (progress[i] > 1) {
                alives[i] = false;
                positions[i * 3] = -100;
                continue;
            }

            const t = progress[i];
            const zOffset = offsets[i];

            if (t < 0.4) {
                const p = t / 0.4;
                positions[i * 3] = 3.5 + p * 3;
                positions[i * 3 + 1] = 3.2 + Math.sin(p * Math.PI) * 0.1;
                positions[i * 3 + 2] = zOffset;
            } else {
                const p = (t - 0.4) / 0.6;
                positions[i * 3] = 6.5 - p * 4;
                positions[i * 3 + 1] = 3.2 - p * 2.5;
                positions[i * 3 + 2] = zOffset;
            }
        }

        this.flowSystem.geometry.attributes.position.needsUpdate = true;
    }

    updateSplashParticles(dt) {
        const { alives, velocities, lifetimes } = this.splashParticlesData;
        const positions = this.splashSystem.geometry.attributes.position.array;

        for (let i = 0; i < this.maxSplashParticles; i++) {
            if (!alives[i]) continue;

            lifetimes[i] -= dt;
            if (lifetimes[i] <= 0) {
                alives[i] = false;
                positions[i * 3] = -100;
                continue;
            }

            velocities[i].y -= 6 * dt;

            positions[i * 3] += velocities[i].x * dt;
            positions[i * 3 + 1] += velocities[i].y * dt;
            positions[i * 3 + 2] += velocities[i].z * dt;
        }

        this.splashSystem.geometry.attributes.position.needsUpdate = true;
    }

    update() {
        if (!this.enabled) return;

        const dt = Math.min(this.clock.getDelta(), 0.05);
        this.time += dt;

        this.updateLiftParticles(dt);
        this.updateSpillParticles(dt);
        this.updateFlowParticles(dt);
        this.updateSplashParticles(dt);
    }

    toggle() {
        this.enabled = !this.enabled;
        if (!this.enabled) {
            this.hideAll();
        }
        return this.enabled;
    }

    hideAll() {
        const hide = (system, maxCount) => {
            const pos = system.geometry.attributes.position.array;
            for (let i = 0; i < maxCount; i++) {
                pos[i * 3] = -100;
                pos[i * 3 + 1] = -100;
            }
            system.geometry.attributes.position.needsUpdate = true;
        };

        hide(this.liftSystem, this.maxLiftParticles);
        hide(this.spillSystem, this.maxSpillParticles);
        hide(this.flowSystem, this.maxFlowParticles);
        hide(this.splashSystem, this.maxSplashParticles);
    }

    dispose() {
        [this.liftSystem, this.spillSystem, this.flowSystem, this.splashSystem].forEach(system => {
            system.geometry.dispose();
            if (system.material.map) system.material.map.dispose();
            system.material.dispose();
            this.scene.remove(system);
        });
    }
}

export class SteamMistEffect {
    constructor(scene) {
        this.scene = scene;
        this.steamParticles = [];
        this.maxSteam = 200;
        this.initSteam();
        this.clock = new THREE.Clock();
    }

    initSteam() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxSteam * 3);
        const colors = new Float32Array(this.maxSteam * 3);
        const sizes = new Float32Array(this.maxSteam);
        const alphas = new Float32Array(this.maxSteam);

        for (let i = 0; i < this.maxSteam; i++) {
            positions[i * 3] = -100;
            positions[i * 3 + 1] = -100;
            positions[i * 3 + 2] = 0;

            colors[i * 3] = 0.85;
            colors[i * 3 + 1] = 0.92;
            colors[i * 3 + 2] = 1.0;

            sizes[i] = 0.3 + Math.random() * 0.5;
            alphas[i] = 0;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.8)');
        gradient.addColorStop(0.5, 'rgba(240, 248, 255, 0.3)');
        gradient.addColorStop(1, 'rgba(200, 220, 255, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);

        const material = new THREE.PointsMaterial({
            size: 0.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.4,
            map: new THREE.CanvasTexture(canvas),
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.steamSystem = new THREE.Points(geometry, material);
        this.scene.add(this.steamSystem);

        this.steamData = {
            velocities: Array.from({ length: this.maxSteam }, () => new THREE.Vector3()),
            lifetimes: new Array(this.maxSteam).fill(0),
            alives: new Array(this.maxSteam).fill(false)
        };
    }

    update(rotationalSpeed, waterLiftRate) {
        const dt = Math.min(this.clock.getDelta(), 0.05);
        const intensity = Math.min(1, (rotationalSpeed / 20) * (waterLiftRate / 200));

        const { velocities, lifetimes, alives } = this.steamData;
        const positions = this.steamSystem.geometry.attributes.position.array;

        if (intensity > 0.05 && Math.random() < intensity * dt * 20) {
            for (let attempt = 0; attempt < 5; attempt++) {
                const i = Math.floor(Math.random() * this.maxSteam);
                if (!alives[i]) {
                    positions[i * 3] = (Math.random() - 0.5) * 8;
                    positions[i * 3 + 1] = 0.2 + Math.random() * 0.2;
                    positions[i * 3 + 2] = (Math.random() - 0.5) * 6;

                    velocities[i].set(
                        (Math.random() - 0.5) * 0.3,
                        0.2 + Math.random() * 0.4,
                        (Math.random() - 0.5) * 0.3
                    );

                    lifetimes[i] = 3 + Math.random() * 2;
                    alives[i] = true;
                    break;
                }
            }
        }

        for (let i = 0; i < this.maxSteam; i++) {
            if (!alives[i]) continue;

            lifetimes[i] -= dt;
            if (lifetimes[i] <= 0) {
                alives[i] = false;
                positions[i * 3] = -100;
                continue;
            }

            velocities[i].x += (Math.random() - 0.5) * 0.1 * dt;
            velocities[i].z += (Math.random() - 0.5) * 0.1 * dt;
            velocities[i].y *= 0.995;

            positions[i * 3] += velocities[i].x * dt;
            positions[i * 3 + 1] += velocities[i].y * dt;
            positions[i * 3 + 2] += velocities[i].z * dt;
        }

        this.steamSystem.geometry.attributes.position.needsUpdate = true;
    }
}
