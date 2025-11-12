# decision_agent.py
import time
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import psycopg2
from kafka import KafkaProducer, KafkaConsumer
from psycopg2.extras import RealDictCursor

# -------------- Configuration ----------------
KAFKA_BOOTSTRAP = "localhost:9092"     # ou "kafka:9092" si conteneur
TOPIC_ACTIONS = "city-actions"
TOPIC_FEEDBACK = "city-actions-feedback"

PG_CONFIG = {
    "host": "localhost",   # si running inside docker, mettre "postgres"
    "port": 5432,
    "dbname": "smartcitydb",
    "user": "smartcity",
    "password": "smartcity123"
}

POLL_INTERVAL = 5            # secondes entre les scans DB
WINDOW_SECONDS = 120         # fenêtre de lecture (dernières X sec)
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
    thresholds = {}  # structure: { "<type>|<sensor_id_or_zone>": threshold }
    # will be persisted on changes

def save_thresholds():
    with open(THRESHOLDS_FILE, "w") as f:
        json.dump(thresholds, f, indent=2)

def get_threshold(key):
    return thresholds.get(key, DEFAULT_THRESHOLD)

def set_threshold(key, value):
    thresholds[key] = max(MIN_THRESHOLD, min(MAX_THRESHOLD, value))
    save_thresholds()

# -------------- Simple online stats (EWMA) ----------------
# stats[type][sensor_id] = {"mean":..., "var":..., "count":...}
stats = defaultdict(lambda: defaultdict(lambda: {"mean": None, "var": None, "count": 0}))

def update_ewma(t, sensor, value):
    s = stats[t][sensor]
    if s["mean"] is None:
        s["mean"] = value
        s["var"] = 0.0
        s["count"] = 1
    else:
        prev = s["mean"]
        alpha = EWMA_ALPHA
        s["mean"] = alpha * value + (1 - alpha) * s["mean"]
        # update variance via EWMA of squared deviations
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

# consumer for feedback
feedback_consumer = KafkaConsumer(
    TOPIC_FEEDBACK,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="decision-feedback-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

# -------------- Action creation ----------------
def create_action(sensor_row, reason, severity="medium"):
    action_id = f"act-{uuid.uuid4().hex[:8]}"
    action = {
        "action_id": action_id,
        "sensor_id": sensor_row["sensor_id"],
        "type": sensor_row["type"],
        "value": sensor_row["value"],
        "timestamp": sensor_row["timestamp"].isoformat() if hasattr(sensor_row["timestamp"], "isoformat") else str(sensor_row["timestamp"]),
        "reason": reason,
        "severity": severity,
        "location": {"lat": sensor_row["latitude"], "lon": sensor_row["longitude"]},
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
    logging.info("Persisted action %s", action["action_id"])

def publish_action(action):
    producer.send(TOPIC_ACTIONS, action)
    producer.flush()
    logging.info("Published action %s to topic %s", action["action_id"], TOPIC_ACTIONS)

# -------------- Feedback handling ----------------
def handle_feedback_message(msg):
    """
    Expected feedback message structure:
    { "action_id": "act-...", "feedback": "confirmed" | "rejected", "by": "operator_id" }
    """
    try:
        action_id = msg["action_id"]
        fb = msg.get("feedback")
        by = msg.get("by", "operator")
        logging.info("Feedback received for %s : %s", action_id, fb)
        # load action from DB to get sensor/type
        conn = connect_pg()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT action_json FROM actions WHERE action_id = %s", (action_id,))
            row = cur.fetchone()
            if not row:
                logging.warning("Action %s not found in DB", action_id)
                return
            action = row["action_json"]
            sensor_id = action["sensor_id"]
            t = action.get("type", "unknown")
            # key for threshold: try sensor-level then type-level
            key_sensor = f"{t}|{sensor_id}"
            key_type = f"{t}|*"
            # read current threshold
            thr = get_threshold(key_sensor) if key_sensor in thresholds else get_threshold(key_type)
            if fb == "confirmed":
                # if confirmed, we may want to lower threshold (be more sensitive) slightly
                new_thr = max(MIN_THRESHOLD, thr - ADAPT_STEP)
                set_threshold(key_sensor if key_sensor in thresholds or key_sensor in thresholds else key_sensor, new_thr)
                logging.info("Confirmed action -> decreasing threshold %s -> %.2f", key_sensor, new_thr)
            elif fb == "rejected":
                # increase threshold to reduce false positives
                new_thr = min(MAX_THRESHOLD, thr + ADAPT_STEP)
                set_threshold(key_sensor if key_sensor in thresholds or key_sensor in thresholds else key_sensor, new_thr)
                logging.info("Rejected action -> increasing threshold %s -> %.2f", key_sensor, new_thr)
            # update action status
            cur.execute("""
                UPDATE actions SET status = %s, feedback_by = %s, feedback_at = now()
                WHERE action_id = %s
            """, (fb, by, action_id))
        conn.close()
    except Exception as e:
        logging.exception("Error handling feedback: %s", e)

# -------------- Main loop ----------------
def run_loop():
    conn = connect_pg()
    logging.info("Decision Agent connected to Postgres. Starting main loop.")
    last_check = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)

    # start a background poll of feedback topic (simple approach: poll non-blocking each loop)
    feedback_iter = feedback_consumer

    try:
        while True:
            # handle any feedback messages (non-blocking)
            for _ in range(20):
                try:
                    rec = next(iter(feedback_iter))
                except StopIteration:
                    break
                except Exception:
                    break
                if rec:
                    handle_feedback_message(rec.value)

            # fetch recent sensor readings from DB
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT sensor_id, type, value, unit, latitude, longitude, timestamp
                    FROM sensors_data
                    WHERE timestamp > %s
                    ORDER BY timestamp ASC
                """, (last_check,))
                rows = cur.fetchall()

            if rows:
                last_check = max(r["timestamp"] for r in rows)
            else:
                last_check = datetime.now(timezone.utc)

            # process rows
            for r in rows:
                t = r["type"]
                sid = r["sensor_id"]
                val = float(r["value"]) if r["value"] is not None else 0.0

                # update running stats and compute z-score
                s = update_ewma(t, sid, val)
                z = get_zscore(t, sid, val)

                # threshold key: prefer sensor-specific threshold, else type-level
                key_sensor = f"{t}|{sid}"
                key_type = f"{t}|*"
                thr = get_threshold(key_sensor) if key_sensor in thresholds else get_threshold(key_type)
                # default set if absent
                if key_type not in thresholds:
                    set_threshold(key_type, DEFAULT_THRESHOLD)

                # rule-based overrides (example simple business rules)
                action_needed = False
                reason = None
                severity = "medium"

                # sample rule set: type-specific logic
                if t == "traffic":
                    # if very low speed -> congestion
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
                    # spike in flow could indicate leak
                    if z >= thr:
                        action_needed = True
                        reason = f"anomalous_water_z{z:.2f}"
                        severity = "high"

                elif t == "light":
                    # low lux at night -> activate
                    if val < 20:
                        action_needed = True
                        reason = "low_lux"
                        severity = "low"
                    elif z >= thr:
                        action_needed = True
                        reason = f"anomalous_light_z{z:.2f}"

                # if action needed -> create action object, persist and publish
                if action_needed:
                    action = create_action(r, reason=reason, severity=severity)
                    try:
                        persist_action(conn, action)
                        publish_action(action)
                    except Exception as e:
                        logging.exception("Error persisting/publishing action: %s", e)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Decision agent stopped by user")
    except Exception:
        logging.exception("Fatal error in run loop")
    finally:
        conn.close()
        producer.close()
        feedback_consumer.close()

if __name__ == "__main__":
    run_loop()
