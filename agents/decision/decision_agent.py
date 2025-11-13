# decision_agent.py - VERSION TEMPS RÉEL
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from collections import defaultdict

import psycopg2
from kafka import KafkaProducer, KafkaConsumer
from psycopg2.extras import RealDictCursor

# -------------- Configuration ----------------
KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC_SENSORS = "city-sensors"          # 🆕 CONSOMMER DIRECTEMENT DEPUIS ICI
TOPIC_ACTIONS = "city-actions"
TOPIC_FEEDBACK = "city-actions-feedback"

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "smartcitydb",
    "user": "smartcity",
    "password": "smartcity123"
}

EWMA_ALPHA = 0.2             # smoothing factor pour stats en ligne
DEFAULT_THRESHOLD = 3.0      # threshold initial (z-score)
MIN_THRESHOLD = 1.5
MAX_THRESHOLD = 6.0
ADAPT_STEP = 0.2             # combien ajuster le seuil lors d'un feedback

# -------------- Logging ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# -------------- Utilities ----------------
def now_iso():
    return datetime.now(timezone.utc).isoformat()

# -------------- Persistence simple des seuils ----------------
THRESHOLDS_FILE = "agents/decision/thresholds.json"
try:
    with open(THRESHOLDS_FILE, "r") as f:
        thresholds = json.load(f)
except Exception:
    thresholds = {}

def save_thresholds():
    with open(THRESHOLDS_FILE, "w") as f:
        json.dump(thresholds, f, indent=2)

def get_threshold(key):
    return thresholds.get(key, DEFAULT_THRESHOLD)

def set_threshold(key, value):
    thresholds[key] = max(MIN_THRESHOLD, min(MAX_THRESHOLD, value))
    save_thresholds()

# -------------- Simple online stats (EWMA) ----------------
stats = defaultdict(lambda: defaultdict(lambda: {"mean": None, "var": None, "count": 0}))

def update_ewma(t, sensor, value):
    s = stats[t][sensor]
    if s["mean"] is None:
        s["mean"] = value
        s["var"] = 0.0
        s["count"] = 1
    else:
        alpha = EWMA_ALPHA
        s["mean"] = alpha * value + (1 - alpha) * s["mean"]
        dev = value - s["mean"]
        s["var"] = alpha * (dev * dev) + (1 - alpha) * s["var"]
        s["count"] += 1
    return s

def get_zscore(t, sensor, value):
    s = stats[t][sensor]
    if s["mean"] is None or s["count"] < 2:
        return 0.0
    std = (s["var"] ** 0.5) if s["var"] >= 0 else 0.0
    if std == 0:
        return 0.0
    return abs((value - s["mean"]) / std)

# -------------- DB / Kafka connections ----------------
def connect_pg():
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    return conn

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=5
)

# 🆕 Consumer pour les données des capteurs EN TEMPS RÉEL
sensors_consumer = KafkaConsumer(
    TOPIC_SENSORS,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset="latest",  # Commence à partir des nouveaux messages
    enable_auto_commit=True,
    group_id="decision-agent-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

# Consumer pour les feedbacks
feedback_consumer = KafkaConsumer(
    TOPIC_FEEDBACK,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="decision-feedback-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

# -------------- Action creation ----------------
def create_action(sensor_data, reason, severity="medium"):
    action_id = f"act-{uuid.uuid4().hex[:8]}"
    action = {
        "action_id": action_id,
        "sensor_id": sensor_data["sensor_id"],
        "type": sensor_data["type"],
        "value": sensor_data["value"],
        "timestamp": sensor_data.get("timestamp", now_iso()),
        "reason": reason,
        "severity": severity,
        "location": {"lat": sensor_data["latitude"], "lon": sensor_data["longitude"]},
        "created_at": now_iso()
    }
    return action

def persist_action(conn, action):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO actions (action_id, sensor_id, event_type, action_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (action_id) DO NOTHING
        """, (action["action_id"], action["sensor_id"], action["reason"], json.dumps(action)))
    logging.info("✅ Persisted action %s | %s | severity=%s", 
                 action["action_id"], action["reason"], action["severity"])

def publish_action(action):
    producer.send(TOPIC_ACTIONS, action)
    producer.flush()
    logging.info("📤 Published action %s to topic %s", action["action_id"], TOPIC_ACTIONS)

# -------------- Feedback handling ----------------
def handle_feedback_message(msg):
    try:
        action_id = msg["action_id"]
        fb = msg.get("feedback")
        by = msg.get("by", "operator")
        logging.info("📥 Feedback received for %s : %s", action_id, fb)
        
        conn = connect_pg()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT action_json FROM actions WHERE action_id = %s", (action_id,))
            row = cur.fetchone()
            if not row:
                logging.warning("⚠️ Action %s not found in DB", action_id)
                return
            
            action = row["action_json"]
            sensor_id = action["sensor_id"]
            t = action.get("type", "unknown")
            key_sensor = f"{t}|{sensor_id}"
            key_type = f"{t}|*"
            thr = get_threshold(key_sensor) if key_sensor in thresholds else get_threshold(key_type)
            
            if fb == "confirmed":
                new_thr = max(MIN_THRESHOLD, thr - ADAPT_STEP)
                set_threshold(key_sensor, new_thr)
                logging.info("✅ Confirmed -> threshold %s: %.2f → %.2f", key_sensor, thr, new_thr)
            elif fb == "rejected":
                new_thr = min(MAX_THRESHOLD, thr + ADAPT_STEP)
                set_threshold(key_sensor, new_thr)
                logging.info("❌ Rejected -> threshold %s: %.2f → %.2f", key_sensor, thr, new_thr)
            
            cur.execute("""
                UPDATE actions SET status = %s, feedback_by = %s, feedback_at = now()
                WHERE action_id = %s
            """, (fb, by, action_id))
        conn.close()
    except Exception as e:
        logging.exception("Error handling feedback: %s", e)

# -------------- Decision Logic ----------------
def analyze_sensor_data(sensor_data):
    """
    Analyse une donnée de capteur et retourne (action_needed, reason, severity)
    """
    t = sensor_data["type"]
    sid = sensor_data["sensor_id"]
    val = float(sensor_data["value"])
    
    # Update stats et calcul z-score
    update_ewma(t, sid, val)
    z = get_zscore(t, sid, val)
    
    # Threshold
    key_sensor = f"{t}|{sid}"
    key_type = f"{t}|*"
    thr = get_threshold(key_sensor) if key_sensor in thresholds else get_threshold(key_type)
    if key_type not in thresholds:
        set_threshold(key_type, DEFAULT_THRESHOLD)
    
    # Business rules
    action_needed = False
    reason = None
    severity = "medium"
    
    if t == "traffic":
        if val < 10:
            action_needed = True
            reason = "congestion_low_speed"
            severity = "high"
        elif z >= thr:
            action_needed = True
            reason = f"anomalous_traffic_z{z:.2f}"
            severity = "medium"
    
    elif t == "waste":
        if val >= 90:
            action_needed = True
            reason = "bin_almost_full"
            severity = "medium"
        elif z >= thr:
            action_needed = True
            reason = f"anomalous_waste_z{z:.2f}"
    
    elif t == "water":
        if z >= thr:
            action_needed = True
            reason = f"anomalous_water_z{z:.2f}"
            severity = "high"
    
    elif t == "light":
        if val < 20:
            action_needed = True
            reason = "low_lux"
            severity = "low"
        elif z >= thr:
            action_needed = True
            reason = f"anomalous_light_z{z:.2f}"
    
    return action_needed, reason, severity

# -------------- Main loop TEMPS RÉEL ----------------
def run_realtime_loop():
    conn = connect_pg()
    logging.info("🚀 Decision Agent connected - REAL-TIME MODE")
    logging.info("📡 Listening to Kafka topic: %s", TOPIC_SENSORS)
    
    try:
        # 🆕 Consommer les messages en temps réel depuis Kafka
        for message in sensors_consumer:
            sensor_data = message.value
            
            # Log de la donnée reçue
            logging.info("📊 Received: %s | %s | %.2f %s", 
                        sensor_data["sensor_id"], 
                        sensor_data["type"],
                        sensor_data["value"],
                        sensor_data.get("unit", ""))
            
            # Analyse en temps réel
            action_needed, reason, severity = analyze_sensor_data(sensor_data)
            
            # Créer et publier l'action si nécessaire
            if action_needed:
                action = create_action(sensor_data, reason=reason, severity=severity)
                try:
                    persist_action(conn, action)
                    publish_action(action)
                except Exception as e:
                    logging.exception("❌ Error persisting/publishing action: %s", e)
            
            # Check feedback messages (non-blocking)
            try:
                feedback_messages = feedback_consumer.poll(timeout_ms=100, max_records=10)
                for topic_partition, records in feedback_messages.items():
                    for record in records:
                        handle_feedback_message(record.value)
            except Exception:
                pass
    
    except KeyboardInterrupt:
        logging.info("⏹️ Decision agent stopped by user")
    except Exception:
        logging.exception("💥 Fatal error in run loop")
    finally:
        conn.close()
        producer.close()
        sensors_consumer.close()
        feedback_consumer.close()

if __name__ == "__main__":
    run_realtime_loop()