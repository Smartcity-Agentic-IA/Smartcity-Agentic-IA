# config.py
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "smartcitydb",
    "user": "smartcity",
    "password": "smartcity123"
}

# Couleurs par type de capteur
SENSOR_COLORS = {
    "traffic": "#3498db",  # Bleu
    "waste": "#e74c3c",    # Rouge
    "water": "#1abc9c",    # Turquoise
    "light": "#f39c12"     # Orange
}

# Icônes par type
SENSOR_ICONS = {
    "traffic": "🚗",
    "waste": "🗑️",
    "water": "💧",
    "light": "💡"
}

# Couleurs par sévérité
SEVERITY_COLORS = {
    "low": "#27ae60",
    "medium": "#f39c12",
    "high": "#e74c3c"
}