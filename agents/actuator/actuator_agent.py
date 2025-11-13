# actuator_agent.py
import json
import logging
import time
from datetime import datetime, timezone

import psycopg2
from kafka import KafkaConsumer, KafkaProducer
from psycopg2.extras import RealDictCursor

# -------------- Configuration ----------------
KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC_ACTIONS = "city-actions"
TOPIC_FEEDBACK = "city-actions-feedback"

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "smartcitydb",
    "user": "smartcity",
    "password": "smartcity123"
}

# -------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [ACTUATOR] %(message)s"
)

# -------------- DB Connection ----------------
def connect_pg():
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    return conn

# -------------- Kafka Setup ----------------
# Consumer pour les actions
actions_consumer = KafkaConsumer(
    TOPIC_ACTIONS,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="actuator-agent-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

# Producer pour envoyer feedback
feedback_producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=5
)

# -------------- Actuator Functions ----------------

def activate_street_lights(action):
    """
    Active l'éclairage public dans une zone
    """
    sensor_id = action["sensor_id"]
    location = action["location"]
    value = action["value"]
    
    logging.info("💡 ACTIVATING street lights near sensor %s", sensor_id)
    logging.info("   📍 Location: lat=%.4f, lon=%.4f", location["lat"], location["lon"])
    logging.info("   🔆 Current lux level: %.2f → Target: 200 lux", value)
    
    # Simulation: En production, appeler une API IoT
    # requests.post("https://api.streetlights.io/activate", json={"zone": location})
    
    return {
        "actuator_type": "street_lights",
        "action_taken": "activated",
        "target_lux": 200,
        "estimated_time": "30 seconds"
    }

def schedule_waste_collection(action):
    """
    Planifie la collecte des déchets
    """
    sensor_id = action["sensor_id"]
    location = action["location"]
    value = action["value"]
    
    logging.info("🗑️ SCHEDULING waste collection for bin %s", sensor_id)
    logging.info("   📍 Location: lat=%.4f, lon=%.4f", location["lat"], location["lon"])
    logging.info("   📊 Fill level: %.1f%% (threshold: 90%%)", value)
    
    # Simulation: Envoyer à système de gestion de flotte
    # fleet_api.schedule_pickup(sensor_id, location, priority="medium")
    
    return {
        "actuator_type": "waste_management",
        "action_taken": "collection_scheduled",
        "priority": "medium" if value < 95 else "high",
        "estimated_arrival": "within 2 hours"
    }

def optimize_traffic_lights(action):
    """
    Optimise les feux de circulation pour réduire congestion
    """
    sensor_id = action["sensor_id"]
    location = action["location"]
    value = action["value"]
    
    logging.info("🚦 OPTIMIZING traffic lights near sensor %s", sensor_id)
    logging.info("   📍 Location: lat=%.4f, lon=%.4f", location["lat"], location["lon"])
    logging.info("   🚗 Current speed: %.1f km/h → Target: 30 km/h", value)
    
    # Simulation: Ajuster timing des feux
    # traffic_control.adjust_timing(location, mode="flow_optimization")
    
    return {
        "actuator_type": "traffic_control",
        "action_taken": "signal_timing_adjusted",
        "green_time_increase": "20%",
        "estimated_impact": "congestion reduced by 30%"
    }

def detect_water_leak(action):
    """
    Détecte et isole une fuite d'eau
    """
    sensor_id = action["sensor_id"]
    location = action["location"]
    value = action["value"]
    
    logging.info("💧 DETECTING water leak at sensor %s", sensor_id)
    logging.info("   📍 Location: lat=%.4f, lon=%.4f", location["lat"], location["lon"])
    logging.info("   🌊 Abnormal flow: %.2f m3/h", value)
    
    # Simulation: Alerter équipe maintenance
    # maintenance_api.create_ticket(sensor_id, "water_leak", priority="high")
    
    return {
        "actuator_type": "water_management",
        "action_taken": "maintenance_alert_sent",
        "priority": "high",
        "estimated_response": "within 30 minutes"
    }

def handle_anomaly(action):
    """
    Gère les anomalies génériques via z-score
    """
    sensor_id = action["sensor_id"]
    sensor_type = action["type"]
    reason = action["reason"]
    
    logging.info("⚠️ HANDLING anomaly for sensor %s (%s)", sensor_id, sensor_type)
    logging.info("   🔍 Reason: %s", reason)
    
    return {
        "actuator_type": "monitoring",
        "action_taken": "alert_sent",
        "notification": "operators notified"
    }

# -------------- Main Actuator Logic ----------------

def execute_action(action):
    """
    Route l'action vers le bon actuator
    """
    action_id = action["action_id"]
    reason = action["reason"]
    severity = action["severity"]
    
    logging.info("=" * 70)
    logging.info("🎬 NEW ACTION RECEIVED: %s", action_id)
    logging.info("   Type: %s | Severity: %s", reason, severity)
    
    result = None
    
    try:
        # Router selon le type d'action
        if reason == "low_lux":
            result = activate_street_lights(action)
            
        elif reason == "bin_almost_full":
            result = schedule_waste_collection(action)
            
        elif reason == "congestion_low_speed":
            result = optimize_traffic_lights(action)
            
        elif "anomalous_water" in reason:
            result = detect_water_leak(action)
            
        elif "anomalous" in reason:
            # Anomalies génériques
            result = handle_anomaly(action)
            
        else:
            logging.warning("⚠️ Unknown action type: %s", reason)
            result = {"action_taken": "logged_only"}
        
        # Log du résultat
        if result:
            logging.info("✅ ACTION EXECUTED SUCCESSFULLY")
            for key, value in result.items():
                logging.info("   %s: %s", key, value)
        
        # Persister l'exécution dans la DB
        persist_execution(action, result, "success")
        
        # Envoyer feedback automatique (simulation d'un opérateur)
        send_auto_feedback(action, "confirmed")
        
        return result
        
    except Exception as e:
        logging.exception("❌ ERROR executing action %s: %s", action_id, e)
        persist_execution(action, None, "failed")
        return None

def persist_execution(action, result, status):
    """
    Sauvegarde l'exécution dans la DB
    """
    try:
        conn = connect_pg()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO actuator_executions 
                (action_id, sensor_id, result_json, status, executed_at)
                VALUES (%s, %s, %s, %s, now())
            """, (
                action["action_id"],
                action["sensor_id"],
                json.dumps(result) if result else None,
                status
            ))
        conn.close()
        logging.info("💾 Execution logged to database")
    except Exception as e:
        logging.error("Failed to persist execution: %s", e)

def send_auto_feedback(action, feedback_type):
    """
    Envoie un feedback automatique après exécution
    """
    try:
        feedback = {
            "action_id": action["action_id"],
            "feedback": feedback_type,
            "by": "actuator_agent_auto",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        feedback_producer.send(TOPIC_FEEDBACK, feedback)
        feedback_producer.flush()
        
        logging.info("📨 Feedback sent: %s", feedback_type)
    except Exception as e:
        logging.error("Failed to send feedback: %s", e)

# -------------- Main Loop ----------------

def run_actuator_agent():
    """
    Boucle principale - écoute les actions et les exécute
    """
    logging.info("=" * 70)
    logging.info("🤖 ACTUATOR AGENT STARTED - REAL-TIME MODE")
    logging.info("📡 Listening to Kafka topic: %s", TOPIC_ACTIONS)
    logging.info("=" * 70)
    
    try:
        for message in actions_consumer:
            action = message.value
            
            # Exécuter l'action
            execute_action(action)
            
            # Petit délai pour lisibilité des logs
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logging.info("⏹️ Actuator agent stopped by user")
    except Exception:
        logging.exception("💥 Fatal error in actuator loop")
    finally:
        actions_consumer.close()
        feedback_producer.close()

if __name__ == "__main__":
    run_actuator_agent()