# simulator.py
import time
import json
import random
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError
from faker import Faker
from agents.collector.schemas import SensorMessage

fake = Faker()

KAFKA_BOOTSTRAP = "localhost:9092"    # change to "kafka:9092" if in container network
TOPIC = "city-sensors"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=5
)

# define a few sensors
SENSOR_TYPES = {
    "light": {"unit": "lux"},
    "waste": {"unit": "%"},
    "traffic": {"unit": "km/h"},
    "water": {"unit": "m3/h"}
}

# create a set of sensors with random positions inside a bbox (Casablanca example)
def random_coord(lat_min=33.55, lat_max=33.60, lon_min=-7.65, lon_max=-7.55):
    return round(random.uniform(lat_min, lat_max), 6), round(random.uniform(lon_min, lon_max), 6)

NUM_SENSORS = 20
sensors = []
for i in range(NUM_SENSORS):
    t = random.choice(list(SENSOR_TYPES.keys()))
    lat, lon = random_coord()
    sensors.append({
        "sensor_id": f"{t.upper()}_{i:03d}",
        "type": t,
        "unit": SENSOR_TYPES[t]["unit"],
        "lat": lat,
        "lon": lon
    })

def generate_value(sensor_type):
    if sensor_type == "light":
        # simulate luminosity in lux
        return round(random.uniform(0, 300), 2)
    if sensor_type == "waste":
        # fill percentage
        return round(random.uniform(0, 100), 1)
    if sensor_type == "traffic":
        # speed km/h
        return round(random.uniform(5, 80), 1)
    if sensor_type == "water":
        return round(random.uniform(0, 10), 3)
    return 0.0

def build_message(s):
    msg = {
        "sensor_id": s["sensor_id"],
        "type": s["type"],
        "value": generate_value(s["type"]),
        "unit": s["unit"],
        "latitude": s["lat"],
        "longitude": s["lon"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "OK"
    }
    # validate with pydantic
    SensorMessage(
        sensor_id=msg["sensor_id"],
        type=msg["type"],
        value=msg["value"],
        unit=msg.get("unit"),
        latitude=msg["latitude"],
        longitude=msg["longitude"],
        timestamp=msg["timestamp"],
        status=msg.get("status")
    )
    return msg

def send_message(msg):
    try:
        future = producer.send(TOPIC, msg)
        record_metadata = future.get(timeout=10)
        # optionally print metadata
        print(f"Sent {msg['sensor_id']} to {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
    except KafkaError as e:
        print("Kafka error:", e)
        # you can implement retries/backoff here

if __name__ == "__main__":
    try:
        print("Starting simulator, producing to topic:", TOPIC)
        while True:
            s = random.choice(sensors)
            msg = build_message(s)
            send_message(msg)
            time.sleep(1.5)   # frequency between messages; adjust as needed
    except KeyboardInterrupt:
        print("Simulator stopped by user")
    finally:
        producer.flush()
        producer.close()
