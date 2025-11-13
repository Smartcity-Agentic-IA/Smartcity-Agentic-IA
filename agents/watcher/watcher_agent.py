import os
import json
import uuid
from datetime import datetime, timezone

print("DEBUG: watcher_agent.py is being executed")

import psycopg2
from pydantic import BaseModel, ValidationError
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

# On réutilise ton schéma de message capteur
from agents.collector.schemas import SensorMessage



# ------------ Config ------------

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_IN = os.getenv("TOPIC_IN", "city-sensors")
TOPIC_OUT = os.getenv("TOPIC_OUT", "city-alerts")

PG = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "smartcitydb"),
    user=os.getenv("PGUSER", "smartcity"),
    password=os.getenv("PGPASSWORD", "smartcity123"),
)


# ------------ Schéma d'alerte ------------

class AlertMessage(BaseModel):
    alert_id: str
    sensor_id: str
    type: str
    severity: str          # "low","medium","high","critical"
    reason: str            # ex: "threshold_waste_90"
    value: float
    expected: float | None
    latitude: float
    longitude: float
    ts: datetime


# ------------ Utils ------------

def ensure_topic(bootstrap: str, topic: str, partitions: int = 1, replication: int = 1):
    """Crée le topic si nécessaire."""
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


def pg_connect():
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    return conn


def insert_alert(conn, a: AlertMessage):
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
                a.alert_id,
                a.sensor_id,
                a.type,
                a.severity,
                a.reason,
                a.value,
                a.expected,
                a.ts,
                a.longitude,
                a.latitude,
            )
        )


# ------------ Règles simples ------------

def rule_check(msg: SensorMessage):
    """
    Règles simples :
      - Déchets >= 90%  -> HIGH
      - Trafic <= 15 km/h -> MEDIUM
      - Éclairage lux <= 10 -> LOW
    Tu pourras les adapter après.
    """
    if msg.type == "waste" and msg.value >= 90:
        return "high", "threshold_waste_90"

    if msg.type == "traffic" and msg.value <= 15:
        return "medium", "low_speed_threshold"

    if msg.type == "light" and msg.value <= 10:
        return "low", "low_lux_threshold"

    return None


# ------------ Boucle principale ------------

def run():
    ensure_topic(KAFKA_BOOTSTRAP, TOPIC_OUT, partitions=1, replication=1)

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
    print("✅ Watcher connected to Kafka & PostgreSQL")
    print(f"   Listening on topic: {TOPIC_IN}")
    print(f"   Producing alerts to: {TOPIC_OUT}")

    for rec in consumer:
        try:
            sensor = SensorMessage(**rec.value)
        except ValidationError as ve:
            print("⚠️ Invalid sensor message:", ve)
            continue

        rule_result = rule_check(sensor)
        if not rule_result:
            continue  # rien d'anormal

        severity, reason = rule_result
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

        # DB
        insert_alert(pg, alert)

        # Kafka
        producer.send(TOPIC_OUT, alert.dict())

        print(f"[ALERT] {alert.severity.upper()} {alert.reason} "
              f"sensor={alert.sensor_id} value={alert.value}")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("🛑 Watcher stopped by user")
