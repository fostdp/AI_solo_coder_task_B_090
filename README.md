# 古代龙骨水车力学仿真与灌溉效率分析系统

## 系统架构

```
                         ┌─────────────────────────────────────┐
                         │          Nginx (port 80)            │
                         │   Gzip压缩 + 反向代理 + 静态文件     │
                         └──┬──────┬──────┬──────┬─────────────┘
                            │      │      │      │
                  /api/     │      │      │      /ws/
                  sensor/   │      │      │      sensor/,alerts
                            ▼      ▼      ▼      ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ DTU      │ │ Mechanics│ │Irrigation│ │ Alarm &  │
              │ Receiver │ │ Simulator│ │ Analyzer │ │ WebSocket│
              │ :8001    │ │ :8002    │ │ :8003    │ │ :8004    │
              └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
                   │            │            │            │
         ┌─────────┼────────────┼────────────┼────────────┤
         │         ▼            ▼            ▼            ▼
         │   ┌─────────────────────────────────────────┐
         │   │         Redis Pub/Sub 通道               │
         │   │  sensor_data / mechanics_result /        │
         │   │  irrigation_result / alarm               │
         │   └─────────────────────────────────────────┘
         │
         ▼
   ┌───────────┐     ┌──────────────────┐
   │ InfluxDB  │     │ 传感器模拟器      │
   │ :8086     │     │ (可配置转速/水位) │
   │ 3个Bucket │     └──────────────────┘
   │ +降采样   │
   └───────────┘
```

## 微服务分工

| 服务 | 端口 | 职责 | 启动命令 |
|------|------|------|----------|
| **dtu_receiver** | 8001 | 传感器数据采集、校验、写入InfluxDB、发布Redis | `gunicorn dtu_receiver.main:app` |
| **mechanics_simulator** | 8002 | 链传动力学仿真、多边形效应、工况优化 | `gunicorn mechanics_simulator.main:app` |
| **irrigation_analyzer** | 8003 | 灌溉效率分析、作物需水、土壤入渗 | `gunicorn irrigation_analyzer.main:app` |
| **alarm_ws** | 8004 | 告警评估、WebSocket推送、Redis订阅 | `gunicorn alarm_ws.main:app` |
| **frontend** | 80 | Nginx静态文件 + Gzip + 反向代理 | `nginx -g daemon off;` |
| **influxdb** | 8086 | 时序数据存储 + 降采样任务 | 官方镜像 |
| **redis** | 6379 | 微服务间Pub/Sub通信 | 官方镜像 |
| **simulator** | - | 传感器数据模拟上报 | `python sensor_simulator.py` |

## 快速部署

### 前提条件

- Docker 20.10+
- Docker Compose v2+

### 一键启动

```bash
# 克隆项目后进入目录
cd AI_solo_coder_task_A_090

# 启动全部服务（首次会自动构建镜像）
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f dtu_receiver
```

### 分步启动（推荐首次使用）

```bash
# 1. 先启动基础设施
docker compose up -d influxdb redis

# 2. 等待 InfluxDB 就绪后初始化
docker compose up influxdb-init

# 3. 启动后端微服务
docker compose up -d dtu_receiver mechanics_simulator irrigation_analyzer alarm_ws

# 4. 启动前端
docker compose up -d frontend

# 5. 启动传感器模拟器
docker compose up -d simulator
```

### 访问地址

| 服务 | URL |
|------|-----|
| 前端界面 | http://localhost |
| DTU数据接口 | http://localhost/api/sensor/data |
| 力学仿真接口 | http://localhost/api/mechanics/simulate |
| 灌溉分析接口 | http://localhost/api/irrigation/analyze |
| 告警接口 | http://localhost/api/alerts |
| InfluxDB管理台 | http://localhost:8086 |

## 传感器模拟器用法

### Docker 方式（推荐）

```bash
# 默认参数：转速15rpm，水位差2.0m
docker compose up -d simulator

# 自定义转速和水位
docker compose run --rm simulator \
  --auto --speed 25 --level 1.5

# 模拟低水位工况
docker compose run --rm simulator \
  --auto --speed 10 --level 0.3

# 模拟高转速过载
docker compose run --rm simulator \
  --auto --speed 40 --level 3.0 --speed-factor 2.0

# 指定上报间隔和时长
docker compose run --rm simulator \
  --auto --speed 15 --interval 10 --duration 30
```

### 本地 Python 方式

```bash
cd scripts
pip install requests websockets

# 自动模式
python sensor_simulator.py --auto --speed 15 --level 2.0

# 交互模式（菜单操作）
python sensor_simulator.py

# 查看所有参数
python sensor_simulator.py --help
```

### 模拟器 CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--auto` | 否 | 启用自动模拟模式 |
| `--speed` | 15.0 | 额定转速 (rpm) |
| `--level` | 2.0 | 额定水位差 (m) |
| `--torque` | 80.0 | 额定扭矩 (N·m) |
| `--lift` | 180.0 | 额定提水量 (L/min) |
| `--wheel-id` | han_dynasty_wheel_001 | 水车ID |
| `--interval` | 60 | 上报间隔 (秒) |
| `--duration` | 0 | 模拟时长 (分钟，0=无限) |
| `--speed-factor` | 1.0 | 转速倍率 |
| `--torque-factor` | 1.0 | 扭矩倍率 |

### 典型工况模拟

```bash
# 汉代标准工况：15rpm, 2m水位差
python sensor_simulator.py --auto --speed 15 --level 2.0

# 低水位测试：验证低水位刮水阻力修正
python sensor_simulator.py --auto --speed 10 --level 0.3

# 高速过载测试：触发链条过载告警
python sensor_simulator.py --auto --speed 40 --level 3.0

# 疲劳寿命测试：长期运行 + 磨损累积
python sensor_simulator.py --auto --speed 20 --level 2.5 --duration 120 --interval 10
```

## 配置说明

### 力学参数配置

编辑 `config/mechanics_params.json`：

```json
{
  "geometry": {
    "upper_wheel_diameter": 1.2,
    "num_sprockets_upper": 12,
    "num_blades": 24
  },
  "scrape_resistance": {
    "surface_tension_alpha": 0.18,
    "low_water_level_exponent": 0.65
  }
}
```

### 灌溉参数配置

编辑 `config/irrigation_params.json`：

```json
{
  "crops": {
    "wheat": { "kc_mid": 1.15, "daily_water_requirement_mm": 4.5 }
  },
  "soils": {
    "loam": { "infiltration_k": 20.0, "field_capacity": 0.35 }
  }
}
```

### InfluxDB 降采样

系统自动创建 3 个 Bucket 和 2 个降采样任务：

| Bucket | 保留期 | 用途 |
|--------|--------|------|
| `waterwheel_data` | 30天 | 原始高频数据 |
| `waterwheel_downsampled_1h` | 365天 | 1小时聚合 |
| `waterwheel_downsampled_1d` | 3650天 | 1天聚合（长期趋势） |

降采样任务配置在 `docker/influxdb/config.json`，修改后需重新运行初始化。

### 环境变量

在项目根目录创建 `.env` 文件（可选）：

```env
INFLUXDB_TOKEN=my-super-secret-auth-token
INFLUXDB_ORG=agri-history
INFLUXDB_BUCKET=waterwheel_data
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=adminpassword123
```

## 常用运维命令

```bash
# 停止全部服务
docker compose down

# 停止并清除数据卷
docker compose down -v

# 重建某个服务
docker compose up -d --build dtu_receiver

# 查看某服务日志
docker compose logs -f --tail 100 mechanics_simulator

# 进入后端容器调试
docker compose exec dtu_receiver bash

# 手动触发 InfluxDB 初始化
docker compose run --rm influxdb-init

# 运行回归测试
docker compose exec dtu_receiver python test_regression.py
```
