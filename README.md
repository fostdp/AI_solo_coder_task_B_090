# 古代龙骨水车力学仿真与灌溉效率分析系统

## 项目概述

为农业史团队开发的汉代龙骨水车复原研究全栈平台，包含：
- **传感器数据采集**：每分钟上报转速、扭矩、提水量、水位差
- **力学仿真模型**：链传动 + 刮水阻力，计算驱动力矩和效率
- **灌溉效率分析**：基于提水量和灌溉面积的最优工况评估
- **告警系统**：链板断裂、效率过低通过WebSocket实时推送
- **三维可视化**：Three.js水车模型 + 龙骨板链动画 + 水流粒子效果

---

## 项目结构

```
AI_solo_coder_task_A_090/
├── backend/                          # Python FastAPI 后端
│   ├── main.py                       # FastAPI主程序 (REST API + WebSocket)
│   ├── mechanics.py                  # 力学仿真模型
│   ├── irrigation.py                 # 灌溉效率分析模块
│   ├── database.py                   # InfluxDB连接模块
│   ├── alerts.py                     # 告警检测与推送系统
│   └── requirements.txt              # Python依赖
├── frontend/                         # 前端 (Canvas + Three.js)
│   ├── index.html                    # 主页面
│   ├── css/style.css                 # 样式
│   └── js/
│       ├── main.js                   # 主逻辑 (图表/交互/WebSocket)
│       ├── waterwheel.js             # Three.js水车三维模型
│       └── particles.js              # 水流粒子效果
└── scripts/                          # 脚本
    ├── init_influxdb.py              # InfluxDB初始化脚本
    └── sensor_simulator.py           # 水车传感器模拟器
```

---

## 快速启动

### 1. 安装并启动 InfluxDB

**下载 InfluxDB v2.x**：https://portal.influxdb.com/downloads/

启动后设置初始配置（默认配置与系统保持一致）：
- URL: `http://localhost:8086`
- Token: `my-super-secret-auth-token`
- Org: `agri-history`
- Bucket: `waterwheel_data`

或使用Docker快速启动：
```bash
docker run -d \
  --name influxdb \
  -p 8086:8086 \
  -v influxdb-data:/var/lib/influxdb2 \
  influxdb:2.7
```

### 2. 初始化 InfluxDB

```bash
cd scripts
pip install influxdb-client numpy
python init_influxdb.py
```

### 3. 启动 Python 后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端服务将在 http://localhost:8000 启动
- API 文档: http://localhost:8000/docs
- 前端页面: http://localhost:8000/

### 4. 启动传感器模拟器

**交互式模式**（推荐，可手动模拟各种工况）：
```bash
cd scripts
python sensor_simulator.py
```

**自动模式**（每分钟自动上报）：
```bash
python sensor_simulator.py --auto
```

### 5. 访问前端

打开浏览器访问：http://localhost:8000/

---

## 核心功能说明

### 一、力学仿真模型 (`backend/mechanics.py`)

**链传动模型**：
- 链轮啮合几何计算
- 紧边/松边张力分布
- 离心张力计算
- 链板应力分析

**阻力模型**：
1. **刮水阻力** - 粘性阻力 + 摩擦阻力 + 水加速力
2. **链重量阻力** - 链条和携带水的自重
3. **弯曲阻力** - 过链轮弯曲变形
4. **摩擦阻力** - 关节摩擦 + 轴摩擦

**失效分析**：
- 过载断裂 (Overload)
- 疲劳失效 (Fatigue) - Goodman图修正
- 磨损退化 (Wear)
- 屈曲失稳 (Buckling)

### 二、灌溉效率分析 (`backend/irrigation.py`)

**土壤入渗模型** (Horton方程)：
```
f(t) = fc + (f0 - fc) * e^(-kt)
```

**作物需水量** (FAO简化方法)：
```
ETc = Kc * ET0
```

**效率分解**：
- 输水效率 (Conveyance Efficiency)
- 田间效率 (Field Application Efficiency)
- 水分生产率 (Water Productivity)

**工况优化**：在转速区间内扫描，找到：
- 最高效率点
- 最大灌溉面积点
- 综合推荐平衡点

### 三、告警系统 (`backend/alerts.py`)

| 告警类型 | 触发条件 | 级别 |
|---------|---------|------|
| CHAIN_BROKEN | 链板断裂检测 | EMERGENCY |
| CHAIN_OVERLOAD | 张力 > 5000N | CRITICAL |
| LOW_EFFICIENCY | 效率 < 30% (持续5点) | WARNING |
| LOW_WATER_FLOW | 提水量 < 10L/min | WARNING |
| EXCESSIVE_TORQUE | 扭矩 > 200N·m | CRITICAL |
| ABNORMAL_SPEED | 超速/欠速 | WARNING |
| HIGH_WEAR | 磨损 > 70%/90% | WARNING/CRITICAL |
| SENSOR_ANOMALY | 连续异常数据 | INFO |

### 四、三维可视化 (`frontend/js/`)

**水车模型组件**：
- 上下链轮 (12齿木质结构)
- 60节龙骨板链 (沿轨迹运动)
- 24片刮水板 (带固定架)
- U型水槽 (木质 + 静态水)
- 支撑结构 (立柱/横梁/斜撑)
- 上下蓄水池

**动画效果**：
- 板链沿椭圆轨迹循环运动
- 链轮同步旋转
- 刮水板微抖动模拟真实运行
- 链条断裂可视化

**粒子系统**：
- 提水粒子 (从下到上沿水槽运动)
- 溢流水花 (进入上槽时)
- 下游流动 (上槽→田地)
- 飞溅粒子
- 水雾蒸汽效果

---

## API 接口列表

### 传感器数据
| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/sensor/data` | 上报单条传感器数据 |
| POST | `/api/sensor/batch` | 批量上报 |
| GET | `/api/sensor/data` | 查询历史数据 (支持聚合) |
| GET | `/api/sensor/wheels` | 获取水车ID列表 |
| GET | `/api/sensor/statistics` | 获取统计信息 |

### 力学仿真
| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/mechanics/simulate` | 运行单点仿真 |
| POST | `/api/mechanics/optimize` | 转速区间优化扫描 |

### 灌溉分析
| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/irrigation/analyze` | 完整灌溉效率分析 |

### 告警管理
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/alerts` | 查询告警列表 |
| POST | `/api/alerts/{id}/acknowledge` | 确认告警 |
| POST | `/api/alerts/{id}/resolve` | 解决告警 |
| GET | `/api/alerts/thresholds` | 获取阈值配置 |
| PUT | `/api/alerts/thresholds` | 修改阈值 |

### WebSocket
| 路径 | 说明 |
|------|------|
| `/ws/sensor/{wheel_id}` | 实时传感器数据推送 |
| `/ws/alerts` | 告警实时推送 |

---

## 传感器模拟器交互菜单

启动 `python sensor_simulator.py` 后可使用：

1. **自动模拟** - 按设定间隔自动上报，可模拟真实环境波动
2. **单次生成** - 查看单条详细数据
3. **调整工况** - 设置转速倍率 (0.2x~2.0x)、扭矩倍率
4. **模拟链板断裂** - 触发CHAIN_BROKEN告警，前端三维模型同步断裂
5. **修复链板** - 恢复运行
6. **查看数据** - 最近10条历史数据
7. **状态查看** - 运行时长、磨损程度、倍率设置

---

## 环境变量配置（可选）

```bash
# InfluxDB
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="your-token"
export INFLUXDB_ORG="agri-history"
export INFLUXDB_BUCKET="waterwheel_data"

# 后端服务
export HOST="0.0.0.0"
export PORT="8000"

# 模拟器
export BACKEND_URL="http://localhost:8000"
export WS_URL="ws://localhost:8000"
```

---

## 技术栈

**后端**:
- Python 3.10+
- FastAPI 0.109 (高性能异步Web框架)
- InfluxDB 2.x (时序数据库)
- NumPy (数值计算)
- WebSockets (实时推送)

**前端**:
- Three.js 0.160 (3D渲染引擎)
- Chart.js 4.x (数据可视化)
- 原生 ES6 Modules (无构建依赖)
- Canvas API (效率环形图)

---

## 汉代龙骨水车参考参数

系统默认参数基于考古实测数据：

| 参数 | 默认值 | 说明 |
|------|-------|------|
| 上/下轮直径 | 1.2m | 木质链轮 |
| 轮中心距 | 4.0m | 提水高度约2m |
| 链节数 | 60节 | 木链+铁销 |
| 刮水板数量 | 24片 | 木刮板 |
| 刮板尺寸 | 30cm×15cm×2cm | 杨木/榆木 |
| 水槽宽度 | 35cm | 木质槽 |
| 额定转速 | 15rpm | 人力/畜力驱动 |
| 额定提水量 | 180L/min | 实测数据 |
| 综合效率 | 60~70% | 高效工况 |

---

## 故障排查

**前端无法连接WebSocket**：
- 确认后端已启动 (http://localhost:8000/api/health)
- 检查端口是否被占用
- 清除浏览器缓存重新加载

**传感器数据不上报**：
- 确认后端/health返回healthy
- 检查模拟器控制台输出
- 查看后端日志是否有POST记录

**粒子效果卡顿**：
- 浏览器需支持WebGL
- 关闭其他占用GPU的标签页
- 可通过Toggle按钮临时关闭粒子

**InfluxDB连接失败**：
- 确认端口8086可访问
- 验证token/org/bucket三项配置
- 执行 `python scripts/init_influxdb.py` 测试连接
