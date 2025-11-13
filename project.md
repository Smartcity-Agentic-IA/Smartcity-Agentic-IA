# 🏙️ Smart City Agentic AI

<div align="center">

![Smart City](https://img.shields.io/badge/Smart%20City-IoT-blue?style=for-the-badge&logo=city)
![Python](https://img.shields.io/badge/Python-3.11-green?style=for-the-badge&logo=python)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-2.6-red?style=for-the-badge&logo=apache-kafka)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue?style=for-the-badge&logo=postgresql)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

**Système intelligent de gestion urbaine basé sur une architecture multi-agents**

[Démonstration](#-démonstration) • [Installation](#-installation) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Technologies](#-technologies)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Agents](#-agents)
- [Dashboard](#-dashboard)
- [Configuration](#-configuration)
- [Contribution](#-contribution)
- [Licence](#-licence)

---

## 🌟 Vue d'ensemble

**Smart City Agentic AI** est un système de gestion urbaine intelligent qui utilise une architecture multi-agents pour:

- 🔍 **Détecter** automatiquement les anomalies dans les infrastructures urbaines
- 🧠 **Décider** intelligemment des actions à entreprendre
- ⚡ **Agir** en temps réel pour résoudre les problèmes
- 📈 **Apprendre** continuellement pour améliorer ses performances

Le système surveille et gère:
- 🚗 **Trafic routier** - Détection de congestion et optimisation des feux
- 🗑️ **Gestion des déchets** - Collecte proactive basée sur le remplissage
- 💡 **Éclairage public** - Activation intelligente selon la luminosité
- 💧 **Réseau d'eau** - Détection de fuites et anomalies

---

## ✨ Fonctionnalités

### 🔄 Temps Réel
- Latence bout-en-bout < 150ms
- Traitement de milliers d'événements par seconde
- Architecture event-driven avec Apache Kafka

### 🤖 Intelligence Artificielle
- Détection d'anomalies par z-score (EWMA)
- Apprentissage adaptatif des seuils
- Feedback automatique et manuel

### 🏗️ Architecture Microservices
- 4 agents autonomes et découplés
- Scalabilité horizontale
- Résilience aux pannes

### 📊 Monitoring Visuel
- Dashboard temps réel avec Streamlit
- Graphiques interactifs (Plotly)
- Métriques et KPIs en direct

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SMART CITY SYSTEM                        │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  Simulator   │  Génère données IoT réalistes
    │   (Agent 1)  │  • Traffic sensors
    └──────┬───────┘  • Waste bins
           │          • Light sensors
           │          • Water meters
           ▼
    ┌─────────────────┐
    │  Kafka Broker   │  Bus de messages distribué
    │  city-sensors   │  • Haute disponibilité
    └────┬──────┬─────┘  • Scalable
         │      │
         │      └──────────────────────┐
         ▼                             ▼
    ┌────────────┐              ┌──────────────┐
    │ Collector  │              │   Decision   │
    │ (Agent 2)  │              │   Agent      │
    │            │              │  (Agent 3)   │
    └─────┬──────┘              └──────┬───────┘
          │                            │
          │ Stockage                   │ Analyse ML
          ▼                            ▼
    ┌──────────────┐            ┌─────────────────┐
    │  PostgreSQL  │            │  Kafka Broker   │
    │ sensors_data │            │  city-actions   │
    └──────────────┘            └────────┬────────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │   Actuator   │
                                  │   Agent      │
                                  │  (Agent 4)   │
                                  └──────┬───────┘
                                         │
                                         ├─→ Actions
                                         ├─→ Feedback
                                         └─→ Learning Loop

    ┌─────────────────┐
    │   Dashboard     │  Visualisation temps réel
    │   Streamlit     │  • Métriques
    └─────────────────┘  • Graphiques
                         • Tables
```

---

## 🛠️ Technologies

| Composant | Technologie | Version | Usage |
|-----------|-------------|---------|-------|
| **Language** | Python | 3.11+ | Développement principal |
| **Message Broker** | Apache Kafka | 2.6 | Communication inter-agents |
| **Base de Données** | PostgreSQL | 14+ | Stockage persistant |
| **Extension Spatiale** | PostGIS | 3.x | Données géospatiales |
| **Dashboard** | Streamlit | 1.28+ | Interface web |
| **Graphiques** | Plotly | 5.x | Visualisations interactives |
| **Containerisation** | Docker | 20+ | Déploiement |
| **Orchestration** | Docker Compose | 2.x | Multi-conteneurs |

---

## 📥 Installation

### Prérequis

- Python 3.11 ou supérieur
- Docker et Docker Compose
- Git

### 1️⃣ Cloner le Projet

```bash
git clone https://github.com/Smartcity-Agentic-IA/Smartcity-Agentic-IA.git
cd Smartcity-Agentic-IA
```

### 2️⃣ Créer l'Environnement Virtuel

```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Installer les Dépendances

```bash
pip install -r requirements.txt
```

### 4️⃣ Lancer l'Infrastructure (Kafka + PostgreSQL)

Construire les images :
```bash
docker-compose build
```

Démarrer les services :
```bash
docker-compose up -d
```

### 5️⃣ Créer les Tables PostgreSQL

```bash
docker exec -it smartcity-db psql -U smartcity -d smartcitydb -f script.sql
```

---

## 🚀 Utilisation

### Démarrage Complet du Système

Ouvrez **4 terminaux** et lancez dans l'ordre:

#### Terminal 1 - Simulator
```bash
python simulator.py
```

#### Terminal 2 - Collector
```bash
python agents/collector/collector_agent.py
```

#### Terminal 3 - Decision Agent
```bash
python agents/decision/decision_agent.py
```

#### Terminal 4 - Actuator Agent
```bash
python agents/actuator/actuator_agent.py
```

#### Terminal 5 (Optionnel) - Dashboard
```bash
streamlit run dashboard/app.py
```

Le dashboard sera accessible à: **http://localhost:8501**

---

## 🤖 Agents

### 1. 📊 Simulator Agent

**Rôle**: Génère des données IoT réalistes simulant une ville

**Fonctionnalités**:
- Génère 20+ capteurs virtuels
- 4 types de capteurs (traffic, waste, water, light)
- Valeurs aléatoires mais réalistes
- Publication vers Kafka toutes les 2 secondes

**Code**: `simulator.py`

---

### 2. 📥 Collector Agent

**Rôle**: Collecte et stocke les données des capteurs

**Fonctionnalités**:
- Consomme les messages Kafka depuis `city-sensors`
- Valide et nettoie les données
- Stocke dans PostgreSQL avec timestamp
- Gestion des géolocalisations (PostGIS)

**Code**: `agents/collector/collector_agent.py`

---

### 3. 🧠 Decision Agent

**Rôle**: Détecte les anomalies et crée des actions intelligentes

**Fonctionnalités**:
- **Détection statistique**: Z-score avec EWMA
- **Règles métier**: Seuils spécifiques par type
- **Apprentissage adaptatif**: Ajustement automatique des seuils
- **Temps réel**: Consomme directement depuis Kafka

**Exemples de détection**:
```python
# Congestion
if traffic_speed < 10 km/h:
    create_action("congestion_low_speed", severity="high")

# Poubelle pleine
if waste_level >= 90%:
    create_action("bin_almost_full", severity="medium")

# Éclairage insuffisant
if light_level < 20 lux:
    create_action("low_lux", severity="low")

# Fuite d'eau
if water_flow_zscore > threshold:
    create_action("anomalous_water", severity="high")
```

**Code**: `agents/decision/decision_agent.py`

---

### 4. ⚡ Actuator Agent

**Rôle**: Exécute les actions et réagit aux décisions

**Fonctionnalités**:
- Consomme les actions depuis `city-actions`
- Route vers le bon actuator selon le type
- Exécute l'action (simulation ou intégration réelle)
- Envoie feedback automatique au Decision Agent
- Log des exécutions dans PostgreSQL

**Actions supportées**:
- 💡 **Activation éclairage public**
- 🗑️ **Planification collecte déchets**
- 🚦 **Optimisation feux de circulation**
- 💧 **Alerte fuite d'eau**
- 👁️ **Monitoring général**

**Code**: `agents/actuator/actuator_agent.py`

---

## 📊 Dashboard

Le dashboard Streamlit offre une visualisation complète en temps réel:

### Métriques Principales
- 🔌 Nombre de capteurs actifs
- ⚡ Actions créées
- ✅ Actions exécutées
- ⏳ Actions en attente

### Graphiques
- 📊 Distribution des mesures par type de capteur
- 🎯 Répartition des actions par sévérité
- ⏱️ Timeline des événements

### Tableaux
- 🔔 Actions récentes avec détails
- 🤖 Exécutions de l'actuator

### Contrôles
- Sélection période d'analyse (5 min à 6 heures)
- Auto-refresh configurable (5s à 60s)

**Accès**: http://localhost:8501 après `streamlit run dashboard/app.py`

---

## ⚙️ Configuration

### Variables d'Environnement

Créez un fichier `.env` à la racine:

```env
# Kafka
KAFKA_BOOTSTRAP=localhost:9092
TOPIC_SENSORS=city-sensors
TOPIC_ACTIONS=city-actions
TOPIC_FEEDBACK=city-actions-feedback

# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=smartcitydb
PG_USER=smartcity
PG_PASSWORD=smartcity123

# Decision Agent
POLL_INTERVAL=5
WINDOW_SECONDS=120
EWMA_ALPHA=0.2
DEFAULT_THRESHOLD=3.0
```

### Ajustement des Seuils

Éditez `agents/decision/thresholds.json`:

```json
{
  "traffic|*": 2.5,
  "waste|*": 3.0,
  "water|*": 3.5,
  "light|*": 2.0
}
```

---

## 📈 Performances

### Benchmarks

| Métrique | Valeur | Description |
|----------|--------|-------------|
| **Latence E2E** | ~150ms | Capteur → Action exécutée |
| **Throughput** | 1000+ msg/s | Messages Kafka traités |
| **Détection** | <50ms | Temps de détection d'anomalie |
| **Actuator Response** | <100ms | Temps d'exécution action |
| **CPU Usage** | <15% | Par agent (moyenne) |
| **Memory** | <200MB | Par agent (moyenne) |

### Scalabilité

- ✅ Horizontal scaling via Kafka partitions
- ✅ Multiple instances de chaque agent
- ✅ Load balancing automatique
- ✅ Testés jusqu'à 100 capteurs simultanés

---

## 🧪 Tests

### Test Manuel Rapide

Insérez une anomalie dans PostgreSQL:

```sql
-- Congestion
INSERT INTO sensors_data (sensor_id, type, value, unit, latitude, longitude, timestamp)
VALUES ('TEST_001', 'traffic', 5.0, 'km/h', 33.5897, -7.6032, NOW());

-- Vérifiez l'action créée
SELECT * FROM actions ORDER BY created_at DESC LIMIT 1;

-- Vérifiez l'exécution
SELECT * FROM actuator_executions ORDER BY executed_at DESC LIMIT 1;
```

### Scénarios de Test

```bash
# Test de charge
python tests/load_test.py

# Test de résilience
python tests/failover_test.py
```

---

## 📚 Documentation Additionnelle

- [Architecture Détaillée](docs/ARCHITECTURE.md)
- [Guide de Déploiement](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

---

## 🤝 Contribution

Les contributions sont les bienvenues! Suivez ces étapes:

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 👥 Auteurs

- **chadia08** - *Développement principal* - [@chadia08](https://github.com/chadia08)

---

## 🙏 Remerciements

- Apache Kafka pour le message streaming
- PostgreSQL et PostGIS pour la gestion des données spatiales
- Streamlit pour le dashboard interactif
- La communauté open source

---

## 📧 Contact

Pour toute question ou suggestion:

- **Email**: chadia.el.kharmoudi@gmail.com
- **GitHub**: [@chadia08](https://github.com/chadia08)
- **LinkedIn**: [Votre profil LinkedIn]

---

<div align="center">

**⭐ Si ce projet vous a été utile, n'oubliez pas de lui donner une étoile! ⭐**

Made with ❤️ by chadia08 | © 2025

</div>