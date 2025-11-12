import time
import json
import random
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from faker import Faker
from agents.collector.schemas import SensorMessage

# ---------------------------------------------
# Configuration
# ---------------------------------------------
fake = Faker()

KAFKA_BOOTSTRAP = "localhost:9092"   # use "kafka:9092" if inside Docker network
TOPIC = "city-sensors"

# ---------------------------------------------
# 1. Ensure topic exists
# ---------------------------------------------
def ensure_topic(bootstrap, topic, partitions=1, replication=1):
    """Create Kafka topic if it does not exist."""
    try:
        admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="sim-admin")
        existing_topics = admin.list_topics()
        if topic not in existing_topics:
            admin.create_topics([NewTopic(name=topic, num_partitions=partitions,
                                          replication_factor=replication)])
            print(f"✅ Created topic: {topic}")
        else:
            print(f"ℹ️ Topic already exists: {topic}")
    except TopicAlreadyExistsError:
        print(f"ℹ️ Topic already exists: {topic}")
    except Exception as e:
        print(f"⚠️ Could not verify or create topic '{topic}': {e}")
    finally:
        try:
            admin.close()
        except:
            pass

ensure_topic(KAFKA_BOOTSTRAP, TOPIC, partitions=1, replication=1)

# ---------------------------------------------
# 2. Initialize Producer
# ---------------------------------------------
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=5
)

# ---------------------------------------------
# 3. Sensor definitions
# ---------------------------------------------
SENSOR_TYPES = {
    "light": {"unit": "lux"},
    "waste": {"unit": "%"},
    "traffic": {"unit": "km/h"},
    "water": {"unit": "m3/h"}
}

def random_coord(lat_min=33.55, lat_max=33.60, lon_min=-7.65, lon_max=-7.55):
    """Generate random latitude/longitude around Casablanca."""
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

# ---------------------------------------------
# 4. Message generator
# ---------------------------------------------
def generate_value(sensor_type):
    """Simulate a sensor reading."""
    if sensor_type == "light":
        return round(random.uniform(0, 300), 2)
    if sensor_type == "waste":
        return round(random.uniform(0, 100), 1)
    if sensor_type == "traffic":
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
    # validate JSON schema with Pydantic
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

# ---------------------------------------------
# 5. Send messages
# ---------------------------------------------
def send_message(msg):
    """Send message to Kafka."""
    try:
        future = producer.send(TOPIC, msg)
        record_metadata = future.get(timeout=10)
        print(f"Sent {msg['sensor_id']} → {record_metadata.topic} "
              f"(partition {record_metadata.partition}, offset {record_metadata.offset})")
    except KafkaError as e:
        print("Kafka error:", e)

# ---------------------------------------------
# 6. Main loop
# ---------------------------------------------
if __name__ == "__main__":
    try:
        print(f"🚀 Starting simulator, producing to topic: {TOPIC}")
        while True:
            s = random.choice(sensors)
            msg = build_message(s)
            send_message(msg)
            time.sleep(1.5)   # adjust frequency as needed
    except KeyboardInterrupt:
        print("🛑 Simulator stopped by user")
    finally:
        producer.flush()
        producer.close()
