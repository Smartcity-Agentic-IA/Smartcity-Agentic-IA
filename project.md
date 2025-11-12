# 🧠 SMARTCITY — AGENTIC AI

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)]()
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker)]()
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-Streaming-black?logo=apachekafka)]()
[![PostGIS](https://img.shields.io/badge/PostGIS-Geospatial-008000?logo=postgresql)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Status](https://img.shields.io/badge/Status-MVP%20Ready-success)]()

Plateforme intelligente de gestion urbaine basée sur des **Agents AI autonomes**, Kafka, PostGIS et visualisation 3D Smart City.

---

## 👥 Team

| Members | 
|--------|
| **Chadia El Kharmoudi** | 
| **Rachid Ait Ali** | 
| **Oussama Madioubi** | 

---

## 🏗️ Architecture (MVP)

```text
┌──────────┐       ┌──────────┐      ┌────────────┐      ┌──────────────┐
| Simulator | ---> |  Kafka   | ---> |  Collector  | ---> | PostgreSQL + |
| (IoT)     |       | Broker   |      |  Agent      |      | PostGIS DB   |
└──────────┘       └──────────┘      └────────────┘      └──────────────┘
                                                        (Stockage spatial)
````

### 🚀 Vision Finale

* 🤖 AI Decision Agent
* 🚨 Incident / Alert AI
* 📊 Smart City Dashboard (React / Streamlit)
* 🏙️ 3D Digital Twin (CesiumJS / Kepler.gl / QGIS)

---

## ⚙️ Setup

### ▶️ Virtual Environment

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
deactivate
```

### 📦 Install

```bash
pip install -r requirements.txt
```

---

## 🐳 Docker Infrastructure

### Build & Run

```bash
docker-compose build
docker-compose up -d
```

### Check services

```bash
docker ps
```

Expected:

* postgres
* kafka
* zookeeper
* *(optional)* kafka-ui

### Stop

```bash
docker-compose down
```

---

## 📡 Kafka UI (optional)

Add to `docker-compose.yml`:

```yaml
kafka-ui:
  image: provectuslabs/kafka-ui
  ports:
    - "8080:8080"
  environment:
    - KAFKA_CLUSTERS_0_NAME=local
    - KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092
```

➡️ Access : `http://localhost:8080`

Create topic: **city-sensors**

---

## 🛰️ Run Components

### Sensor Simulator

```bash
python simulator.py
```

### Collector Agent (Kafka → PostGIS)

```bash
python agents/collector/collector_agent.py
```

---

## 🗄️ Database Access

```bash
docker exec -it smartcity-agentic-ai-postgres-1 psql -U smartcity -d smartcitydb
```

Check data:

```sql
SELECT * FROM sensor_data LIMIT 10;
```

---

## ✅ Roadmap

| Feature            | Status         |
| ------------------ | -------------- |
| Kafka IoT Pipeline | ✅ Done         |
| AI Alert Agent     | 🔄 In Progress |
| City Dashboard     | 🔜 Next        |
| Digital Twin 3D    | 📅 Planned     |

---

## 📂 Project Structure

```
smartcity-agentic-ai/
│── agents/
│   └── collector/
│── data/
│── docker-compose.yml
│── requirements.txt
│── simulator.py
│── README.md
```

---

## 💡 Key Concepts

* **PostGIS** for geospatial storage
* **Agentic AI** architecture
* **Kafka** as real-time backbone

---

## ⭐ Contribute & Support

If you find this repo useful, please **star ⭐ it** and contribute!

---

### 🔥 Future Smart City Intelligence with Autonomous AI Agents

```

---

Si tu veux, je peux aussi te fournir :

📌 Version avec **diagramme Mermaid** (GitHub compatible)  
📌 Workflow **GitHub Actions CI/CD**  
📌 Architecture PNG / Draw.io  
📌 Badge Docker Hub + CI Status  
📌 Version FR + EN bilingue

Tu veux laquelle ? 😊
```
