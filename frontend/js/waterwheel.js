import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class WaterwheelScene {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.clock = new THREE.Clock();

        this.wheelGroup = null;
        this.upperWheel = null;
        this.lowerWheel = null;
        this.chainLinks = [];
        this.blades = [];
        this.trough = null;
        this.chainPath = null;
        this.chainLength = 0;
        this.chainProgress = 0;

        this.rotationalSpeed = 15;
        this.waterLevelDiff = 2;
        this.autoRotate = false;
        this.wireframeMode = false;
        this.brokenBladeIndex = -1;

        this.animating = true;
        this.initialized = false;

        this.init();
    }

    init() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0f17);
        this.scene.fog = new THREE.FogExp2(0x0a0f17, 0.015);

        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.camera = new THREE.PerspectiveCamera(50, rect.width / rect.height, 0.1, 1000);
        this.camera.position.set(10, 6, 12);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(rect.width, rect.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 5;
        this.controls.maxDistance = 40;
        this.controls.maxPolarAngle = Math.PI / 2 + 0.2;
        this.controls.target.set(0, 2, 0);

        this.setupLights();
        this.createWaterwheel();
        this.createEnvironment();

        window.addEventListener('resize', () => this.onResize());
        this.initialized = true;
        this.animate();
    }

    setupLights() {
        const ambient = new THREE.AmbientLight(0x404060, 0.5);
        this.scene.add(ambient);

        const sunLight = new THREE.DirectionalLight(0xffeedd, 1.5);
        sunLight.position.set(15, 20, 10);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 60;
        sunLight.shadow.camera.left = -20;
        sunLight.shadow.camera.right = 20;
        sunLight.shadow.camera.top = 20;
        sunLight.shadow.camera.bottom = -20;
        this.scene.add(sunLight);

        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.4);
        fillLight.position.set(-10, 8, -8);
        this.scene.add(fillLight);

        const rimLight = new THREE.PointLight(0x4fc3f7, 0.6, 30);
        rimLight.position.set(0, 3, -8);
        this.scene.add(rimLight);
    }

    createWaterwheel() {
        this.wheelGroup = new THREE.Group();

        const upperWheelY = 5;
        const lowerWheelY = 1.5;
        const wheelZ = 0;

        this.upperWheel = this.createSprocket(0.6, upperWheelY, wheelZ, true);
        this.lowerWheel = this.createSprocket(0.6, lowerWheelY, wheelZ, false);

        this.wheelGroup.add(this.upperWheel);
        this.wheelGroup.add(this.lowerWheel);

        this.createChain(upperWheelY, lowerWheelY);
        this.createBlades(upperWheelY, lowerWheelY);
        this.createTrough(upperWheelY, lowerWheelY);
        this.createSupportStructure(upperWheelY, lowerWheelY);

        this.scene.add(this.wheelGroup);
    }

    createSprocket(radius, y, z, isUpper) {
        const group = new THREE.Group();
        group.position.set(0, y, z);
        group.userData.radius = radius;
        group.userData.isUpper = isUpper;

        const woodTexture = this.createWoodTexture(isUpper ? 0x6b4423 : 0x5c3a21);

        const hubGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.8, 16);
        const hubMat = new THREE.MeshStandardMaterial({
            color: 0x3a2817,
            roughness: 0.7,
            metalness: 0.1
        });
        const hub = new THREE.Mesh(hubGeo, hubMat);
        hub.rotation.x = Math.PI / 2;
        hub.castShadow = true;
        hub.receiveShadow = true;
        group.add(hub);

        const numTeeth = 12;
        const toothGeo = new THREE.BoxGeometry(0.15, 0.25, 0.6);
        const toothMat = new THREE.MeshStandardMaterial({
            map: woodTexture,
            roughness: 0.8,
            metalness: 0.0
        });

        for (let i = 0; i < numTeeth; i++) {
            const angle = (i / numTeeth) * Math.PI * 2;
            const tooth = new THREE.Mesh(toothGeo, toothMat);
            tooth.position.set(
                Math.cos(angle) * radius,
                Math.sin(angle) * radius,
                0
            );
            tooth.rotation.z = angle + Math.PI / 2;
            tooth.castShadow = true;
            tooth.receiveShadow = true;
            group.add(tooth);
        }

        const rimGeo = new THREE.TorusGeometry(radius - 0.1, 0.04, 8, 48);
        const rimMat = new THREE.MeshStandardMaterial({
            map: woodTexture,
            roughness: 0.85,
            metalness: 0.0
        });
        const rim1 = new THREE.Mesh(rimGeo, rimMat);
        rim1.position.z = 0.25;
        rim1.castShadow = true;
        group.add(rim1);

        const rim2 = rim1.clone();
        rim2.position.z = -0.25;
        group.add(rim2);

        for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2;
            const spokeGeo = new THREE.BoxGeometry(radius - 0.1, 0.05, 0.06);
            const spoke = new THREE.Mesh(spokeGeo, toothMat);
            spoke.rotation.z = angle;
            spoke.position.x = Math.cos(angle) * (radius - 0.1) / 2;
            spoke.position.y = Math.sin(angle) * (radius - 0.1) / 2;
            spoke.castShadow = true;
            group.add(spoke);
        }

        const axleGeo = new THREE.CylinderGeometry(0.05, 0.05, 3, 12);
        const axleMat = new THREE.MeshStandardMaterial({
            color: 0x8b8b8b,
            roughness: 0.4,
            metalness: 0.8
        });
        const axle = new THREE.Mesh(axleGeo, axleMat);
        axle.rotation.x = Math.PI / 2;
        axle.castShadow = true;
        group.add(axle);

        return group;
    }

    createWoodTexture(baseColorHex) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext('2d');

        const base = new THREE.Color(baseColorHex);
        ctx.fillStyle = `rgb(${Math.floor(base.r * 255)}, ${Math.floor(base.g * 255)}, ${Math.floor(base.b * 255)})`;
        ctx.fillRect(0, 0, 256, 256);

        for (let i = 0; i < 80; i++) {
            const x = 0;
            const y = Math.random() * 256;
            const w = 256;
            const h = 1 + Math.random() * 3;
            const alpha = 0.05 + Math.random() * 0.12;
            ctx.fillStyle = `rgba(40, 20, 10, ${alpha})`;
            ctx.fillRect(x, y, w, h);
        }

        for (let i = 0; i < 200; i++) {
            const x = Math.random() * 256;
            const y = Math.random() * 256;
            const r = 0.5 + Math.random() * 2;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(60, 30, 15, ${0.08 + Math.random() * 0.1})`;
            ctx.fill();
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        return texture;
    }

    createChain(upperY, lowerY) {
        const radius = 0.6;
        const wheelDist = upperY - lowerY;
        const tangentLen = wheelDist;
        const halfArc = Math.PI * radius;
        this.chainLength = 2 * tangentLen + 2 * halfArc;

        const numLinks = 60;
        const linkSpacing = this.chainLength / numLinks;

        const linkGeo = new THREE.BoxGeometry(0.1, 0.04, 0.08);
        const linkMat = new THREE.MeshStandardMaterial({
            color: 0xd2691e,
            roughness: 0.8,
            metalness: 0.05
        });

        const pinGeo = new THREE.CylinderGeometry(0.015, 0.015, 0.12, 8);
        const pinMat = new THREE.MeshStandardMaterial({
            color: 0x666666,
            roughness: 0.5,
            metalness: 0.7
        });

        this.chainPath = this.createPathPoints(upperY, lowerY, radius);

        for (let i = 0; i < numLinks; i++) {
            const linkGroup = new THREE.Group();
            const link = new THREE.Mesh(linkGeo, linkMat);
            link.castShadow = true;
            linkGroup.add(link);

            const pin1 = new THREE.Mesh(pinGeo, pinMat);
            pin1.rotation.x = Math.PI / 2;
            pin1.position.x = -0.04;
            linkGroup.add(pin1);

            const pin2 = pin1.clone();
            pin2.position.x = 0.04;
            linkGroup.add(pin2);

            const pos = this.getPointOnPath(i * linkSpacing / this.chainLength, upperY, lowerY, radius);
            linkGroup.position.copy(pos.position);
            linkGroup.rotation.z = pos.rotation;

            this.chainLinks.push({
                mesh: linkGroup,
                index: i,
                isBladeHolder: i % 2 === 0
            });
            this.wheelGroup.add(linkGroup);
        }
    }

    createPathPoints(upperY, lowerY, radius) {
        const points = [];
        const segments = 100;
        for (let i = 0; i <= segments; i++) {
            const t = i / segments;
            const pos = this.getPointOnPath(t, upperY, lowerY, radius);
            points.push(pos.position);
        }
        return points;
    }

    getPointOnPath(t, upperY, lowerY, radius) {
        t = ((t % 1) + 1) % 1;

        const tangentLen = upperY - lowerY;
        const halfArc = Math.PI * radius;
        const totalLen = 2 * tangentLen + 2 * halfArc;

        const dist = t * totalLen;
        const position = new THREE.Vector3();
        let rotation = 0;

        if (dist < tangentLen) {
            const p = dist / tangentLen;
            position.set(radius, upperY - p * tangentLen, 0);
            rotation = -Math.PI / 2;
        } else if (dist < tangentLen + halfArc) {
            const p = (dist - tangentLen) / halfArc;
            const angle = Math.PI * (0.5 + p);
            position.set(Math.cos(angle) * radius, lowerY + Math.sin(angle) * radius + radius, 0);
            rotation = -angle + Math.PI / 2;
        } else if (dist < 2 * tangentLen + halfArc) {
            const p = (dist - tangentLen - halfArc) / tangentLen;
            position.set(-radius, lowerY + p * tangentLen, 0);
            rotation = Math.PI / 2;
        } else {
            const p = (dist - 2 * tangentLen - halfArc) / halfArc;
            const angle = Math.PI * (1.5 + p);
            position.set(Math.cos(angle) * radius, upperY - radius + Math.sin(angle) * radius + radius, 0);
            rotation = -angle - Math.PI / 2;
        }

        return { position, rotation };
    }

    createBlades(upperY, lowerY) {
        const radius = 0.6;
        const bladeGeo = new THREE.BoxGeometry(0.08, 0.22, 0.5);
        const woodTexture = this.createWoodTexture(0x8B4513);
        const bladeMat = new THREE.MeshStandardMaterial({
            map: woodTexture,
            roughness: 0.85,
            metalness: 0.0,
            side: THREE.DoubleSide
        });

        const holderGeo = new THREE.BoxGeometry(0.04, 0.18, 0.52);
        const holderMat = new THREE.MeshStandardMaterial({
            color: 0x5c3a21,
            roughness: 0.9,
            metalness: 0.0
        });

        const numBlades = 24;

        for (let i = 0; i < numBlades; i++) {
            const bladeGroup = new THREE.Group();

            const blade = new THREE.Mesh(bladeGeo, bladeMat);
            blade.castShadow = true;
            blade.receiveShadow = true;
            bladeGroup.add(blade);

            const holder1 = new THREE.Mesh(holderGeo, holderMat);
            holder1.position.z = 0.28;
            bladeGroup.add(holder1);

            const holder2 = holder1.clone();
            holder2.position.z = -0.28;
            bladeGroup.add(holder2);

            this.blades.push({
                mesh: bladeGroup,
                index: i,
                bladeObject: blade
            });
            this.wheelGroup.add(bladeGroup);
        }
    }

    createTrough(upperY, lowerY) {
        const troughGroup = new THREE.Group();

        const woodTexture = this.createWoodTexture(0x654321);
        const troughMat = new THREE.MeshStandardMaterial({
            map: woodTexture,
            roughness: 0.9,
            metalness: 0.0,
            side: THREE.DoubleSide
        });

        const troughLength = upperY - lowerY + 0.5;
        const troughWidth = 0.6;
        const troughDepth = 0.18;
        const plankThick = 0.03;

        const bottomGeo = new THREE.BoxGeometry(plankThick, troughLength, troughWidth + plankThick * 2);
        const bottom = new THREE.Mesh(bottomGeo, troughMat);
        bottom.position.set(-troughDepth / 2 + 0.05, (upperY + lowerY) / 2, 0);
        bottom.rotation.z = 0;
        bottom.receiveShadow = true;
        troughGroup.add(bottom);

        const sideGeo = new THREE.BoxGeometry(troughDepth, troughLength, plankThick);
        const side1 = new THREE.Mesh(sideGeo, troughMat);
        side1.position.set(0, (upperY + lowerY) / 2, troughWidth / 2);
        side1.receiveShadow = true;
        troughGroup.add(side1);

        const side2 = side1.clone();
        side2.position.z = -troughWidth / 2;
        troughGroup.add(side2);

        const plankGeo = new THREE.BoxGeometry(troughDepth + plankThick, 0.08, troughWidth + plankThick * 2 + 0.04);
        for (let i = 0; i < 8; i++) {
            const y = lowerY + 0.2 + i * (troughLength / 8);
            const band = new THREE.Mesh(plankGeo, troughMat);
            band.position.set(-troughDepth / 2 + 0.01, y, 0);
            troughGroup.add(band);
        }

        const waterMat = new THREE.MeshStandardMaterial({
            color: 0x4fc3f7,
            roughness: 0.1,
            metalness: 0.1,
            transparent: true,
            opacity: 0.75
        });
        const waterGeo = new THREE.BoxGeometry(0.02, troughLength * 0.9, troughWidth - 0.08);
        const water = new THREE.Mesh(waterGeo, waterMat);
        water.position.set(-0.06, (upperY + lowerY) / 2, 0);
        this.troughWater = water;
        troughGroup.add(water);

        this.trough = troughGroup;
        this.wheelGroup.add(troughGroup);
    }

    createSupportStructure(upperY, lowerY) {
        const supportMat = new THREE.MeshStandardMaterial({
            color: 0x4a3020,
            roughness: 0.85,
            metalness: 0.0
        });

        const pillarGeo = new THREE.BoxGeometry(0.15, upperY + 1, 0.15);
        const pillar1 = new THREE.Mesh(pillarGeo, supportMat);
        pillar1.position.set(1.2, (upperY + 1) / 2, 0.6);
        pillar1.castShadow = true;
        pillar1.receiveShadow = true;
        this.wheelGroup.add(pillar1);

        const pillar2 = pillar1.clone();
        pillar2.position.set(1.2, (upperY + 1) / 2, -0.6);
        this.wheelGroup.add(pillar2);

        const pillar3 = pillar1.clone();
        pillar3.position.set(-1.2, (lowerY + 0.3) / 2, 0.6);
        pillar3.scale.y = lowerY / (upperY + 1);
        pillar3.position.y = (lowerY + 0.1) / 2;
        this.wheelGroup.add(pillar3);

        const pillar4 = pillar3.clone();
        pillar4.position.set(-1.2, (lowerY + 0.3) / 2, -0.6);
        this.wheelGroup.add(pillar4);

        const beamGeo = new THREE.BoxGeometry(2.8, 0.1, 1.6);
        const topBeam = new THREE.Mesh(beamGeo, supportMat);
        topBeam.position.set(0, upperY + 0.8, 0);
        topBeam.castShadow = true;
        this.wheelGroup.add(topBeam);

        const diagGeo = new THREE.BoxGeometry(0.1, 2.5, 0.1);
        const diag1 = new THREE.Mesh(diagGeo, supportMat);
        diag1.position.set(0.7, upperY - 0.5, 0.6);
        diag1.rotation.z = 0.4;
        this.wheelGroup.add(diag1);

        const diag2 = diag1.clone();
        diag2.position.set(0.7, upperY - 0.5, -0.6);
        this.wheelGroup.add(diag2);
    }

    createEnvironment() {
        const groundGeo = new THREE.PlaneGeometry(80, 80, 50, 50);
        const positions = groundGeo.attributes.position;
        for (let i = 0; i < positions.count; i++) {
            const x = positions.getX(i);
            const y = positions.getY(i);
            const z = Math.sin(x * 0.1) * 0.2 + Math.cos(y * 0.15) * 0.15 + (Math.random() - 0.5) * 0.1;
            positions.setZ(i, z);
        }
        groundGeo.computeVertexNormals();

        const groundCanvas = document.createElement('canvas');
        groundCanvas.width = 512;
        groundCanvas.height = 512;
        const gctx = groundCanvas.getContext('2d');
        gctx.fillStyle = '#3d5a3d';
        gctx.fillRect(0, 0, 512, 512);
        for (let i = 0; i < 3000; i++) {
            const x = Math.random() * 512;
            const y = Math.random() * 512;
            const hue = 80 + Math.random() * 40;
            const light = 20 + Math.random() * 25;
            gctx.fillStyle = `hsla(${hue}, 40%, ${light}%, 0.5)`;
            gctx.fillRect(x, y, 2 + Math.random() * 3, 2 + Math.random() * 3);
        }
        const groundTex = new THREE.CanvasTexture(groundCanvas);
        groundTex.wrapS = THREE.RepeatWrapping;
        groundTex.wrapT = THREE.RepeatWrapping;
        groundTex.repeat.set(8, 8);

        const groundMat = new THREE.MeshStandardMaterial({
            map: groundTex,
            roughness: 0.95,
            metalness: 0.0
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);

        const poolGeo = new THREE.BoxGeometry(8, 0.5, 6);
        const poolMat = new THREE.MeshStandardMaterial({
            color: 0x4a90a4,
            roughness: 0.1,
            metalness: 0.0,
            transparent: true,
            opacity: 0.85
        });
        const pool = new THREE.Mesh(poolGeo, poolMat);
        pool.position.set(-4, 0.25, 0);
        this.lowerPool = pool;
        this.scene.add(pool);

        const upperPoolGeo = new THREE.BoxGeometry(6, 0.4, 5);
        const upperPool = new THREE.Mesh(upperPoolGeo, poolMat);
        upperPool.position.set(3.5, 3.2, 0);
        this.upperPool = upperPool;
        this.scene.add(upperPool);

        this.createBank();
    }

    createBank() {
        const bankMat = new THREE.MeshStandardMaterial({
            color: 0x5d4e37,
            roughness: 0.9,
            metalness: 0.0
        });

        const bankShape = new THREE.Shape();
        bankShape.moveTo(0, 0);
        bankShape.lineTo(2, 1.2);
        bankShape.lineTo(5, 1.2);
        bankShape.lineTo(7, 0);
        bankShape.lineTo(0, 0);

        const bankGeo = new THREE.ExtrudeGeometry(bankShape, {
            depth: 12,
            bevelEnabled: false
        });
        const bank1 = new THREE.Mesh(bankGeo, bankMat);
        bank1.position.set(-8, 0, -6);
        bank1.rotation.y = Math.PI / 2;
        bank1.receiveShadow = true;
        bank1.castShadow = true;
        this.scene.add(bank1);

        const bank2 = bank1.clone();
        bank2.position.z = 6;
        this.scene.add(bank2);
    }

    setSpeed(rpm) {
        this.rotationalSpeed = Math.max(0, Math.min(60, rpm));
    }

    setWaterLevel(diff) {
        this.waterLevelDiff = diff;
        if (this.lowerPool) {
            this.lowerPool.scale.y = 0.5 + (diff - 2) * 0.2;
        }
    }

    setBrokenBlade(index) {
        this.brokenBladeIndex = index;
        this.blades.forEach((b, i) => {
            b.mesh.visible = (i !== index);
        });
    }

    toggleAutoRotate() {
        this.autoRotate = !this.autoRotate;
        return this.autoRotate;
    }

    toggleWireframe() {
        this.wireframeMode = !this.wireframeMode;
        this.scene.traverse((obj) => {
            if (obj.isMesh && obj.material) {
                if (Array.isArray(obj.material)) {
                    obj.material.forEach(m => m.wireframe = this.wireframeMode);
                } else {
                    obj.material.wireframe = this.wireframeMode;
                }
            }
        });
        return this.wireframeMode;
    }

    resetView() {
        this.camera.position.set(10, 6, 12);
        this.controls.target.set(0, 2, 0);
        this.controls.update();
    }

    updateChainAndBlades(delta) {
        if (this.chainLength === 0) return;

        const chainSpeed = this.rotationalSpeed / 60;
        this.chainProgress = (this.chainProgress + chainSpeed * delta * 0.5) % 1;

        const numLinks = this.chainLinks.length;
        const numBlades = this.blades.length;
        const radius = 0.6;
        const upperY = 5;
        const lowerY = 1.5;

        for (let i = 0; i < numLinks; i++) {
            const t = ((i / numLinks + this.chainProgress) % 1 + 1) % 1;
            const pos = this.getPointOnPath(t, upperY, lowerY, radius);
            this.chainLinks[i].mesh.position.copy(pos.position);
            this.chainLinks[i].mesh.rotation.z = pos.rotation;
        }

        const bladeSpacing = this.chainLength / numBlades;
        for (let i = 0; i < numBlades; i++) {
            if (i === this.brokenBladeIndex) continue;
            const dist = (i * bladeSpacing + this.chainProgress * this.chainLength) % this.chainLength;
            const t = dist / this.chainLength;
            const pos = this.getPointOnPath(t, upperY, lowerY, radius);
            this.blades[i].mesh.position.copy(pos.position);
            this.blades[i].mesh.rotation.z = pos.rotation;

            const scale = 0.9 + Math.sin(Date.now() * 0.005 + i) * 0.02;
            this.blades[i].mesh.scale.set(scale, scale, scale);
        }

        const wheelOmega = this.rotationalSpeed * 2 * Math.PI / 60;
        if (this.upperWheel) {
            this.upperWheel.rotation.z -= wheelOmega * delta;
        }
        if (this.lowerWheel) {
            this.lowerWheel.rotation.z -= wheelOmega * delta;
        }
    }

    onResize() {
        if (!this.canvas || !this.renderer || !this.camera) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.camera.aspect = rect.width / rect.height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(rect.width, rect.height);
    }

    animate() {
        if (!this.animating) return;
        requestAnimationFrame(() => this.animate());

        const delta = Math.min(this.clock.getDelta(), 0.1);

        if (this.autoRotate) {
            const angle = 0.1 * delta;
            const x = this.camera.position.x;
            const z = this.camera.position.z;
            const cosA = Math.cos(angle);
            const sinA = Math.sin(angle);
            this.camera.position.x = x * cosA - z * sinA;
            this.camera.position.z = x * sinA + z * cosA;
            this.camera.lookAt(0, 3, 0);
        }

        this.updateChainAndBlades(delta);

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    dispose() {
        this.animating = false;
        this.renderer.dispose();
    }
}
