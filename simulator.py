import os
import time
import json
import random
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError
from faker import Faker
from agents.collector.schemas import SensorMessage

fake = Faker()

# Try addresses in order; override with env KAFKA_BOOTSTRAP if needed
DEFAULT_CANDIDATES = [
    os.getenv("KAFKA_BOOTSTRAP"),               # if user sets it
    "127.0.0.1:9092",
    "localhost:9092",
    "host.docker.internal:9092",
    "kafka:29092",
    "kafka:9092",
]
BOOTSTRAP_CANDIDATES = [c for c in DEFAULT_CANDIDATES if c]

TOPIC = "city-sensors"

def try_admin_connect(bootstrap_list, timeout=5):
    last_exc = None
    for bs in bootstrap_list:
        try:
            admin = KafkaAdminClient(bootstrap_servers=bs, client_id="sim-admin", request_timeout_ms=timeout*1000)
            print(f"✅ Admin connected to {bs}")
            return admin, bs
        except Exception as e:
            last_exc = e
            print(f"⚠️ Admin connect failed {bs}: {e}")
    raise RuntimeError(f"Admin connect failed for all candidates. Last error: {last_exc}")

def ensure_topic(bootstrap_candidates, topic, partitions=1, replication=1):
    try:
        admin, used = try_admin_connect(bootstrap_candidates)
    except Exception as e:
        print(f"⚠️ Could not create/verify topic because admin connection failed: {e}")
        return False
    try:
        existing = admin.list_topics()
        if topic in existing:
            print(f"ℹ️ Topic exists on {used}: {topic}")
            return True
        admin.create_topics([NewTopic(name=topic, num_partitions=partitions, replication_factor=replication)])
        print(f"✅ Created topic {topic} on {used}")
        return True
    except TopicAlreadyExistsError:
        print(f"ℹ️ Topic already exists: {topic}")
        return True
    except Exception as e:
        print(f"⚠️ Topic creation failed on {used}: {e}")
        return False
    finally:
        try:
            admin.close()
        except:
            pass

def create_producer(bootstrap_candidates, retries=3):
    last_exc = None
    for bs in bootstrap_candidates:
        for attempt in range(1, retries+1):
            try:
                p = KafkaProducer(
                    bootstrap_servers=bs,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    retries=5,
                    request_timeout_ms=10000
                )
                # quick metadata request to ensure connectivity
                p.bootstrap_connected()
                print(f"✅ Producer connected to {bs}")
                return p, bs
            except Exception as e:
                last_exc = e
                print(f"⚠️ Producer connect attempt {attempt}/{retries} failed for {bs}: {e}")
                time.sleep(1)
    raise RuntimeError(f"Producer connect failed for all candidates. Last error: {last_exc}")

# prepare sensors
SENSOR_TYPES = {"light": {"unit": "lux"}, "waste": {"unit": "%"}, "traffic": {"unit": "km/h"}, "water": {"unit": "m3/h"}}
def random_coord(lat_min=33.55, lat_max=33.60, lon_min=-7.65, lon_max=-7.55):
    return round(random.uniform(lat_min, lat_max), 6), round(random.uniform(lon_min, lon_max), 6)

NUM_SENSORS = 20
sensors = []
for i in range(NUM_SENSORS):
    t = random.choice(list(SENSOR_TYPES.keys()))
    lat, lon = random_coord()
    sensors.append({"sensor_id": f"{t.upper()}_{i:03d}", "type": t, "unit": SENSOR_TYPES[t]["unit"], "lat": lat, "lon": lon})

# run setup
print("🔎 Candidates for Kafka bootstrap:", BOOTSTRAP_CANDIDATES)
ensure_topic(BOOTSTRAP_CANDIDATES, TOPIC, partitions=1, replication=1)

try:
    producer, used_bs = create_producer(BOOTSTRAP_CANDIDATES, retries=4)
except Exception as e:
    print("❌ Cannot create Kafka producer. Exiting. Error:", e)
    producer = None
    used_bs = None

def generate_value(sensor_type):
    if sensor_type == "light": return round(random.uniform(0,300),2)
    if sensor_type == "waste": return round(random.uniform(0,100),1)
    if sensor_type == "traffic": return round(random.uniform(5,80),1)
    if sensor_type == "water": return round(random.uniform(0,10),3)
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
    # quick Pydantic validation
    try:
        SensorMessage(**msg)
    except Exception as e:
        print(f"⚠️ Validation failed for {msg['sensor_id']}: {e}")
        return None
    return msg

def send_message(msg):
    if producer is None:
        print("⚠️ No producer available, skipping send")
        return False
    try:
        fut = producer.send(TOPIC, msg)
        meta = fut.get(timeout=10)
        print(f"Sent {msg['sensor_id']} → {meta.topic} (p{meta.partition} o{meta.offset})")
        return True
    except KafkaError as e:
        print("Kafka error:", e)
        return False

if __name__ == "__main__":
    if producer is None:
        print("❌ Producer not available. Set KAFKA_BOOTSTRAP env to a working broker (e.g. 127.0.0.1:9092 or kafka:29092) and retry.")
    else:
        print(f"🚀 Starting simulator producing to {TOPIC} via {used_bs}")
    try:
        while True:
            s = random.choice(sensors)
            msg = build_message(s)
            if msg:
                send_message(msg)
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        if producer:
            producer.flush()
            producer.close()