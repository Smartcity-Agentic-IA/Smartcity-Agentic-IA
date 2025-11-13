import os
import json
import uuid
from datetime import datetime, timezone

import psycopg2
from pydantic import BaseModel, ValidationError
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

print("DEBUG: watcher_agent.py is being executed")

# ────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
TOPIC_IN = os.getenv("TOPIC_IN", "city-sensors")
TOPIC_OUT = os.getenv("TOPIC_OUT", "city-alerts")

PG = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "smartcitydb"),
    user=os.getenv("PGUSER", "smartcity"),
    password=os.getenv("PGPASSWORD", "smartcity123"),
)


# ────────────────────────────────────────────────────────────────
# TOPIC AUTO-CREATION
# ────────────────────────────────────────────────────────────────

def ensure_topic(bootstrap: str, topic: str, partitions: int = 1, replication: int = 1):
    try:
        admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="watcher-admin")
        topics = admin.list_topics()

        if topic not in topics:
            admin.create_topics([
                NewTopic(name=topic, num_partitions=partitions, replication_factor=replication)
            ])
            print(f"✅ Created topic: {topic}")
        else:
            print(f"ℹ️ Topic exists: {topic}")

        admin.close()

    except TopicAlreadyExistsError:
        print(f"ℹ️ Topic exists: {topic}")

    except Exception as e:
        print(f"⚠️ ensure_topic error for {topic}: {e}")


# ────────────────────────────────────────────────────────────────
# Pydantic Models
# ────────────────────────────────────────────────────────────────

class SensorMessage(BaseModel):
    sensor_id: str
    type: str
    value: float
    unit: str | None
    latitude: float
    longitude: float
    timestamp: str
    status: str | None


class AlertMessage(BaseModel):
    alert_id: str
    sensor_id: str
    type: str
    severity: str
    reason: str
    value: float
    expected: float | None
    latitude: float
    longitude: float
    ts: datetime


# ────────────────────────────────────────────────────────────────
# Database Utils
# ────────────────────────────────────────────────────────────────

def pg_connect():
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    return conn


def insert_alert(conn, alert: AlertMessage):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts(
                alert_id, sensor_id, type, severity, reason,
                value, expected, ts, geom
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s,%s),4326)
            )
            """,
            (
                alert.alert_id,
                alert.sensor_id,
                alert.type,
                alert.severity,
                alert.reason,
                alert.value,
                alert.expected,
                alert.ts,
                alert.longitude,
                alert.latitude,
            )
        )


# ────────────────────────────────────────────────────────────────
# Dynamic Threshold System
# ────────────────────────────────────────────────────────────────

DEFAULT_THRESHOLDS = {
    "waste": 90.0,
    "traffic": 15.0,
    "light": 10.0,
    "water": 8.0,
}


def load_thresholds(conn):
    thresholds = DEFAULT_THRESHOLDS.copy()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT type, threshold_value FROM thresholds")
            for t, v in cur.fetchall():
                thresholds[t] = float(v)

    except Exception as e:
        print(f"⚠️ Error loading thresholds, using defaults: {e}")

    print("ℹ️ Active thresholds:", thresholds)
    return thresholds


# ────────────────────────────────────────────────────────────────
# Anomaly Rules
# ────────────────────────────────────────────────────────────────

def rule_check(msg: SensorMessage, thr: dict[str, float]):
    waste_thr = thr.get("waste", DEFAULT_THRESHOLDS["waste"])
    traffic_thr = thr.get("traffic", DEFAULT_THRESHOLDS["traffic"])
    light_thr = thr.get("light", DEFAULT_THRESHOLDS["light"])
    water_thr = thr.get("water", DEFAULT_THRESHOLDS["water"])

    # WASTE anomaly
    if msg.type == "waste" and msg.value >= waste_thr:
        return "high", "dynamic_waste_high"

    # TRAFFIC anomaly
    if msg.type == "traffic" and msg.value <= traffic_thr:
        return "medium", "dynamic_traffic_low"

    # LIGHT anomaly
    if msg.type == "light" and msg.value <= light_thr:
        return "low", "dynamic_light_low"

    # WATER anomaly
    if msg.type == "water" and msg.value >= water_thr:
        return "high", "dynamic_water_high"

    return None


# ────────────────────────────────────────────────────────────────
# MAIN LOOP
# ────────────────────────────────────────────────────────────────

def run():
    ensure_topic(KAFKA_BOOTSTRAP, TOPIC_OUT)

    consumer = KafkaConsumer(
        TOPIC_IN,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="watcher-agent",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )

    pg = pg_connect()

    # 🔥 Load thresholds ONCE (dynamic but static until next restart)
    thresholds = load_thresholds(pg)

    print("✅ Watcher connected to Kafka & PostgreSQL")
    print(f"   Listening on topic: {TOPIC_IN}")
    print(f"   Producing alerts to: {TOPIC_OUT}")

    for rec in consumer:
        try:
            sensor = SensorMessage(**rec.value)
        except ValidationError as ve:
            print("⚠️ Invalid sensor message:", ve)
            continue

        rule = rule_check(sensor, thresholds)
        if not rule:
            continue

        severity, reason = rule

        alert = AlertMessage(
            alert_id=str(uuid.uuid4()),
            sensor_id=sensor.sensor_id,
            type=sensor.type,
            severity=severity,
            reason=reason,
            value=sensor.value,
            expected=None,
            latitude=sensor.latitude,
            longitude=sensor.longitude,
            ts=datetime.now(timezone.utc),
        )

        insert_alert(pg, alert)
        producer.send(TOPIC_OUT, alert.dict())

        print(
            f"[ALERT] {alert.severity.upper()} | {alert.reason} | "
            f"sensor={alert.sensor_id} | value={alert.value}"
        )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("🛑 Watcher stopped by user")
