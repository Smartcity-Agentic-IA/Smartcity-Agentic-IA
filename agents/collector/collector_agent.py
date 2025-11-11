# collector_agent.py
import json
import time
import psycopg2
from kafka import KafkaConsumer
from schemas import SensorMessage

# Configuration Kafka
KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "city-sensors"

# Configuration PostgreSQL
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "smartcitydb",
    "user": "smartcity",
    "password": "smartcity123"
}

# Connexion PostgreSQL
def connect_pg():
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    return conn

def insert_to_db(conn, data):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sensors_data (
                sensor_id, type, value, unit, latitude, longitude, geom, timestamp, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
        """, (
            data["sensor_id"],
            data["type"],
            data["value"],
            data.get("unit"),
            data["latitude"],
            data["longitude"],
            data["longitude"], data["latitude"],  # pour geom
            data["timestamp"],
            data.get("status")
        ))

def start_collector():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='collector-agent-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    conn = connect_pg()
    print("✅ Collector Agent connecté à Kafka et PostgreSQL")

    for message in consumer:
        try:
            msg = message.value
            SensorMessage(**msg)  # validation Pydantic
            insert_to_db(conn, msg)
            print(f"Inserted: {msg['sensor_id']} | {msg['type']} | {msg['value']}")
        except Exception as e:
            print("⚠️ Erreur lors du traitement:", e)

if __name__ == "__main__":
    while True:
        try:
            start_collector()
        except Exception as e:
            print("Erreur collector:", e)
            time.sleep(5)
