import os
import json
import uuid
from datetime import datetime, timezone

import psycopg2
from pydantic import BaseModel, ValidationError
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

# Import the alert model from the watcher
from agents.watcher.watcher_agent import AlertMessage

print("DEBUG: planner_agent.py is being executed")

# ------------ Config ------------

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
TOPIC_IN = os.getenv("TOPIC_IN", "city-alerts")
TOPIC_OUT = os.getenv("TOPIC_OUT", "city-actions")

PG = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "smartcitydb"),
    user=os.getenv("PGUSER", "smartcity"),
    password=os.getenv("PGPASSWORD", "smartcity123"),
)


# ------------ ensure_topic ------------

def ensure_topic(bootstrap: str, topic: str, partitions: int = 1, replication: int = 1):
    """Creates Kafka topic if it does not exist."""
    try:
        admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="planner-admin")
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


# ------------ Action Schema ------------

class ActionMessage(BaseModel):
    action_id: str
    action_type: str
    priority: str
    sensor_id: str | None
    targets: list[str]
    parameters: dict
    latitude: float | None
    longitude: float | None
    ts: datetime
    reason: str


# ------------ DB Utils ------------

def pg_connect():
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    return conn


def insert_action(conn, a: ActionMessage):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO actions(
                action_id, action_type, priority, sensor_id,
                targets, parameters, ts, geom, reason
            )
            VALUES (
                %s, %s, %s, %s,
                %s::text[], %s::jsonb, %s,
                CASE
                    WHEN %s IS NOT NULL AND %s IS NOT NULL
                    THEN ST_SetSRID(ST_MakePoint(%s,%s),4326)
                    ELSE NULL
                END,
                %s
            )
            """,
            (
                a.action_id,
                a.action_type,
                a.priority,
                a.sensor_id,
                a.targets,
                json.dumps(a.parameters),
                a.ts,
                a.longitude,
                a.latitude,
                a.longitude,
                a.latitude,
                a.reason,
            )
        )


# ------------ Decision Logic ------------

def plan_from_alert(alert: AlertMessage) -> ActionMessage:
    """
    Converts an alert into a concrete action.
    """

    # --- WASTE ---
    if alert.type == "waste":
        return ActionMessage(
            action_id=str(uuid.uuid4()),
            action_type="reroute_collection",
            priority="P1" if alert.severity in ("high", "critical") else "P2",
            sensor_id=alert.sensor_id,
            targets=["truck_03"],
            parameters={"eta_min": 15},
            latitude=alert.latitude,
            longitude=alert.longitude,
            ts=datetime.now(timezone.utc),
            reason=f"policy_waste_{alert.severity}",
        )

    # --- TRAFFIC ---
    if alert.type == "traffic":
        return ActionMessage(
            action_id=str(uuid.uuid4()),
            action_type="traffic_signal_plan",
            priority="P1",
            sensor_id=alert.sensor_id,
            targets=["junction_A12"],
            parameters={"delta_green_sec": 20},
            latitude=alert.latitude,
            longitude=alert.longitude,
            ts=datetime.now(timezone.utc),
            reason=f"policy_traffic_{alert.severity}",
        )

    # --- LIGHT ---
    # --- WATER ---
    if alert.type == "water":
        return ActionMessage(
            action_id=str(uuid.uuid4()),
            action_type="dispatch_water_team",
            priority="P1" if alert.severity == "high" else "P2",
            sensor_id=alert.sensor_id,
            targets=["water_team_01"],
            parameters={"check_for_leak": True},
            latitude=alert.latitude,
            longitude=alert.longitude,
            ts=datetime.now(timezone.utc),
            reason=f"policy_water_{alert.severity}",
        )


    # --- DEFAULT ---


    return ActionMessage(
        action_id=str(uuid.uuid4()),
        action_type="dispatch_crew",
        priority="P3",
        sensor_id=alert.sensor_id,
        targets=[],
        parameters={},
        latitude=alert.latitude,
        longitude=alert.longitude,
        ts=datetime.now(timezone.utc),
        reason=f"default_policy_{alert.type}_{alert.severity}",
    )



# ------------ Main Loop ------------

def run():
    ensure_topic(KAFKA_BOOTSTRAP, TOPIC_OUT)

    consumer = KafkaConsumer(
        TOPIC_IN,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="planner-agent",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )

    pg = pg_connect()

    print("✅ Planner connected to Kafka & PostgreSQL")
    print(f"   Listening on alerts topic: {TOPIC_IN}")
    print(f"   Producing actions to: {TOPIC_OUT}")

    for rec in consumer:
        try:
            alert = AlertMessage(**rec.value)
        except ValidationError as ve:
            print("⚠️ Invalid alert:", ve)
            continue

        action = plan_from_alert(alert)

        # Insert into DB
        insert_action(pg, action)

        # Publish action to Kafka
        producer.send(TOPIC_OUT, action.dict())

        print(
            f"[ACTION] {action.action_type} | {action.priority} | "
            f"sensor={action.sensor_id} | reason={action.reason}"
        )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("🛑 Planner stopped by user")
