# 🌆 SMARTCITY - AGENTIC AI  
A real-time, multi-agent, Kafka-based smart city platform using AI logic, anomaly detection, automated actions, and PostgreSQL/PostGIS.

---

## 👥 TEAM PROJECT
| Name | Role |
|------|------|
| **Rachid Ait Ali** | Lead |
| **Oussama Madioubi** | Lead |
| **Chadia El Kharmoudi** | Lead |

---

# 🧠 What This Project Does

This project simulates a **real smart city** with:
- Real-time sensor streaming  
- Anomaly detection (Watcher Agent)  
- Automated decisions (Planner Agent)  
- PostgreSQL + PostGIS storage  
- Kafka event-driven architecture  
- Virtual IoT sensors (Simulator)  

**Pipeline:**

Simulator → Collector → Watcher → Planner → (city-actions)
→ PostgreSQL (sensor_data, alerts, actions)
→ Kafka UI (monitoring)

yaml
Copy code

---

# 📁 Project Structure

Smartcity-Agentic-IA/
│
├── agents/
│ ├── collector/
│ │ ├── collector_agent.py
│ │ └── schemas.py
│ ├── watcher/
│ │ └── watcher_agent.py
│ ├── planner/
│ │ └── planner_agent.py
│ └── init.py
│
├── simulator.py
├── docker-compose.yml
├── requirements.txt
└── README.md

yaml
Copy code

---

# 🧩 1. Create the Virtual Environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Deactivate:

powershell
Copy code
deactivate
🐳 2. Start Docker Infrastructure
Start:

bash
Copy code
docker-compose up -d
Check:

bash
Copy code
docker ps
You should see:

kafka

zookeeper

postgres

kafka-ui

Stop:

bash
Copy code
docker-compose down
Logs:

bash
Copy code
docker-compose logs -f
🗄️ 3. PostgreSQL / PostGIS Setup
Connect:

bash
Copy code
docker exec -it smartcity-agentic-ia-postgres-1 psql -U smartcity -d smartcitydb
Alerts Table
sql
Copy code
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  sensor_id TEXT,
  type TEXT,
  severity TEXT,
  reason TEXT,
  value DOUBLE PRECISION,
  expected DOUBLE PRECISION,
  ts TIMESTAMP,
  geom GEOGRAPHY(Point,4326)
);

CREATE INDEX IF NOT EXISTS alerts_ts_idx   ON alerts(ts);
CREATE INDEX IF NOT EXISTS alerts_geom_idx ON alerts USING GIST(geom);
Actions Table
sql
Copy code
CREATE TABLE IF NOT EXISTS actions (
  action_id TEXT PRIMARY KEY,
  action_type TEXT,
  priority TEXT,
  sensor_id TEXT,
  targets TEXT[],
  parameters JSONB,
  ts TIMESTAMP,
  geom GEOGRAPHY(Point,4326),
  reason TEXT
);
📡 4. Kafka UI (Web Monitoring)
Open:

👉 http://localhost:8080

You will see topics:

city-sensors

city-alerts

city-actions

Useful for debugging and message inspection.

🚗 5. Run the System Step-by-Step (4 terminals)
Your project uses 4 parallel agents.
Open 4 PowerShell windows (4 terminals):

🟦 Terminal 1 — Collector Agent
powershell
Copy code
cd Smartcity-Agentic-IA
.\.venv\Scripts\Activate.ps1

python -m agents.collector.collector_agent
Expected:

vbnet
Copy code
Collector connected to Kafka & PostgreSQL
Listening on: city-sensors
🟥 Terminal 2 — Watcher Agent (Anomaly Detector)
powershell
Copy code
cd Smartcity-Agentic-IA
.\.venv\Scripts\Activate.ps1

python -m agents.watcher.watcher_agent
Expected:

vbnet
Copy code
DEBUG: watcher_agent.py is being executed
ℹ️ Topic exists: city-alerts
✅ Watcher connected to Kafka & PostgreSQL
Listening on topic: city-sensors
Producing alerts to: city-alerts
🟩 Terminal 3 — Planner Agent (Decision Engine)
powershell
Copy code
cd Smartcity-Agentic-IA
.\.venv\Scripts\Activate.ps1

python -m agents.planner.planner_agent
Expected:

vbnet
Copy code
DEBUG: planner_agent.py is being executed
ℹ️ Topic exists: city-actions
✅ Planner connected to Kafka & PostgreSQL
Listening on city-alerts
Producing actions to: city-actions
🟧 Terminal 4 — Simulator (Fake IoT Sensors)
powershell
Copy code
cd Smartcity-Agentic-IA
.\.venv\Scripts\Activate.ps1

python simulator.py
Expected:

sql
Copy code
Sent TRAFFIC_003 → city-sensors offset 201
Sent WASTE_012 → city-sensors offset 202
Sent WATER_006 → city-sensors offset 203
🔍 6. What You Should See in Real Time
🟦 Collector Terminal
bash
Copy code
[DB] Inserted sensor=WASTE_012 type=waste value=96.3
🟥 Watcher Terminal
csharp
Copy code
[ALERT] HIGH threshold_waste_90 sensor=WASTE_012 value=96.3
[ALERT] MEDIUM low_speed_threshold sensor=TRAFFIC_003 value=12.4
[ALERT] LOW low_lux_threshold sensor=LIGHT_005 value=3.2
[ALERT] HIGH high_flow_possible_leak sensor=WATER_007 value=8.5
🟩 Planner Terminal
csharp
Copy code
[ACTION] reroute_collection | P1 | sensor=WASTE_012 | reason=policy_waste_high
[ACTION] traffic_signal_plan | P1 | sensor=TRAFFIC_003 | reason=policy_traffic_medium
[ACTION] adjust_light | P2 | sensor=LIGHT_005 | reason=policy_light_low
[ACTION] dispatch_water_team | P1 | sensor=WATER_007 | reason=policy_water_high
🗃️ 7. Verify Data in PostgreSQL
Check alerts:
bash
Copy code
docker exec -it smartcity-agentic-ia-postgres-1 psql \
  -U smartcity -d smartcitydb \
  -c "SELECT * FROM alerts ORDER BY ts DESC LIMIT 10;"
Check actions:
bash
Copy code
docker exec -it smartcity-agentic-ia-postgres-1 psql \
  -U smartcity -d smartcitydb \
  -c "SELECT * FROM actions ORDER BY ts DESC LIMIT 10;"
📊 8. Architecture Diagram (Mermaid)
mermaid
Copy code
flowchart LR
    A[Simulator<br>city-sensors] -->|Produces| B(Kafka Broker)
    B --> C[Collector Agent<br>Store in PostgreSQL]
    B --> D[Watcher Agent<br>Anomaly Detection]
    D -->|Publish Alerts| E[Kafka Topic<br>city-alerts]
    D -->|Store Alerts| F[(PostgreSQL Alerts)]
    E --> G[Planner Agent<br>Generate City Actions]
    G --> H[(PostgreSQL Actions)]
    G --> I[Kafka Topic<br>city-actions]