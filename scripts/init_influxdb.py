"""
InfluxDB 初始化脚本
用于创建龙骨水车数据存储所需的Bucket和保留策略
"""
import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "agri-history")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "waterwheel_data")
RETENTION_DAYS = 365


def init_influxdb():
    print(f"连接到 InfluxDB: {INFLUXDB_URL}")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    
    try:
        health = client.health()
        print(f"InfluxDB 状态: {health.status}")
        
        buckets_api = client.buckets_api()
        orgs_api = client.organizations_api()
        
        orgs = orgs_api.find_organizations()
        org_id = None
        for org in orgs:
            if org.name == INFLUXDB_ORG:
                org_id = org.id
                break
        
        if not org_id:
            print(f"创建组织: {INFLUXDB_ORG}")
            org = orgs_api.create_organization(name=INFLUXDB_ORG)
            org_id = org.id
        
        existing_buckets = buckets_api.find_buckets(name=INFLUXDB_BUCKET).buckets
        
        if existing_buckets:
            print(f"Bucket '{INFLUXDB_BUCKET}' 已存在，跳过创建")
            bucket = existing_buckets[0]
        else:
            print(f"创建 Bucket: {INFLUXDB_BUCKET}，保留期: {RETENTION_DAYS} 天")
            retention_rules = [{
                "type": "expire",
                "everySeconds": RETENTION_DAYS * 24 * 3600,
                "shardGroupDurationSeconds": 24 * 3600
            }]
            bucket = buckets_api.create_bucket(
                bucket_name=INFLUXDB_BUCKET,
                org_id=org_id,
                retention_rules=retention_rules
            )
        
        print(f"Bucket ID: {bucket.id}")
        print("InfluxDB 初始化完成！")
        
        write_test_data(client, bucket.id)
        
    except Exception as e:
        print(f"初始化失败: {e}")
        raise
    finally:
        client.close()


def write_test_data(client, bucket_id):
    """写入测试数据验证连接"""
    print("写入测试数据...")
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    test_point = Point("waterwheel_sensor") \
        .tag("wheel_id", "test_wheel_001") \
        .tag("location", "han_dynasty_museum") \
        .field("rotational_speed", 10.0) \
        .field("torque", 50.0) \
        .field("water_lift", 100.0) \
        .field("water_level_diff", 1.5) \
        .field("drive_torque", 60.0) \
        .field("efficiency", 0.75)
    
    write_api.write(bucket=bucket_id, org=INFLUXDB_ORG, record=test_point)
    write_api.close()
    print("测试数据写入成功")


def create_dashboards_config():
    """创建Dashboard配置说明"""
    config = {
        "measurements": [
            {
                "name": "waterwheel_sensor",
                "fields": [
                    "rotational_speed (rpm)",
                    "torque (N·m)",
                    "water_lift (L/min)",
                    "water_level_diff (m)",
                    "drive_torque (N·m)",
                    "efficiency",
                    "chain_tension (N)",
                    "scrape_resistance (N)"
                ],
                "tags": ["wheel_id", "location"]
            },
            {
                "name": "waterwheel_alert",
                "fields": [
                    "alert_type",
                    "alert_level",
                    "message",
                    "value",
                    "threshold"
                ],
                "tags": ["wheel_id", "alert_code"]
            },
            {
                "name": "irrigation_analysis",
                "fields": [
                    "optimal_speed (rpm)",
                    "irrigation_area (m²)",
                    "water_used (L)",
                    "area_efficiency (m²/L)"
                ],
                "tags": ["wheel_id"]
            }
        ]
    }
    
    print("\n推荐Dashboard测量点配置:")
    for m in config["measurements"]:
        print(f"\n测量点: {m['name']}")
        print(f"  字段: {', '.join(m['fields'])}")
        if m["tags"]:
            print(f"  标签: {', '.join(m['tags'])}")


if __name__ == "__main__":
    init_influxdb()
    create_dashboards_config()
    print("\n✅ InfluxDB 初始化脚本执行完成")
