import os
from datetime import datetime, timezone

import psycopg2
import numpy as np


print("DEBUG: learning_agent.py is being executed")

PG = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "smartcitydb"),
    user=os.getenv("PGUSER", "smartcity"),
    password=os.getenv("PGPASSWORD", "smartcity123"),
)

# Sensors data
SENSOR_TABLE = "sensors_data"   # nom de la table des données capteurs


def pg_connect():
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    return conn


def fetch_values(conn, sensor_type: str, days: int = 3):
    """
    Récupère les valeurs des x derniers jours pour un type donné.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT value
            FROM {SENSOR_TABLE}
            WHERE type = %s
              AND timestamp >= NOW() - INTERVAL '%s days'
            """,
            (sensor_type, days),
        )
        rows = cur.fetchall()
    return [r[0] for r in rows]


def upsert_threshold(conn, sensor_type: str, rule_name: str, thr: float):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO thresholds(type, rule_name, threshold_value, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (type)
            DO UPDATE SET
                rule_name = EXCLUDED.rule_name,
                threshold_value = EXCLUDED.threshold_value,
                updated_at = EXCLUDED.updated_at
            """,
            (sensor_type, rule_name, thr, datetime.now(timezone.utc)),
        )


def compute_dynamic_thresholds():
    conn = pg_connect()

    sensor_types = ["waste", "traffic", "light", "water"]

    for t in sensor_types:
        values = fetch_values(conn, t, days=3)
        if not values or len(values) < 20:
            print(f"⚠️ Not enough data for type={t} to compute statistics")
            continue

        arr = np.array(values)

        # Heuristique simple par type :
        if t == "waste":
            # seuil "poubelle presque pleine" = percentile 90
            thr = float(np.percentile(arr, 90))
            rule_name = "dynamic_waste_high"

        elif t == "traffic":
            # seuil "traffic lent" = percentile 10 (vitesse basse)
            thr = float(np.percentile(arr, 10))
            rule_name = "dynamic_traffic_low"

        elif t == "light":
            # seuil "faible luminosité" = percentile 10
            thr = float(np.percentile(arr, 10))
            rule_name = "dynamic_light_low"

        elif t == "water":
            # seuil "débit élevé" = percentile 95 (suspect fuite)
            thr = float(np.percentile(arr, 95))
            rule_name = "dynamic_water_high"

        else:
            continue

        upsert_threshold(conn, t, rule_name, thr)
        print(f"✅ Updated threshold for {t}: {thr:.3f} ({rule_name})")

    conn.close()


def run():
    print("🚀 LearningAgent started - computing dynamic thresholds")
    compute_dynamic_thresholds()
    print("✅ LearningAgent finished")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("🛑 LearningAgent stopped by user")
