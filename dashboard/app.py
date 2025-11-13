# app.py - Smart City Dashboard
import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from config import PG_CONFIG, SENSOR_COLORS, SENSOR_ICONS, SEVERITY_COLORS

# Configuration de la page
st.set_page_config(
    page_title="Smart City Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #2c3e50;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stat-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Connexion PostgreSQL
@st.cache_resource
def get_connection():
    return psycopg2.connect(**PG_CONFIG)

def get_data(query):
    """Exécute une requête et retourne un DataFrame"""
    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Erreur de connexion: {e}")
        return pd.DataFrame()

# ============== HEADER ==============
st.markdown('<div class="main-header">🏙️ Smart City Dashboard</div>', unsafe_allow_html=True)
st.markdown("---")

# ============== SIDEBAR ==============
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/smart-city.png", width=100)
    st.title("⚙️ Contrôles")
    
    # Refresh rate
    refresh_rate = st.selectbox(
        "Taux de rafraîchissement",
        [5, 10, 30, 60],
        index=1,
        help="Rafraîchissement automatique en secondes"
    )
    
    # Time range
    time_range = st.selectbox(
        "Période d'analyse",
        ["5 minutes", "15 minutes", "30 minutes", "1 heure", "6 heures"],
        index=2
    )
    
    time_mapping = {
        "5 minutes": 5,
        "15 minutes": 15,
        "30 minutes": 30,
        "1 heure": 60,
        "6 heures": 360
    }
    minutes = time_mapping[time_range]
    
    st.markdown("---")
    st.info(f"🕐 Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}")
    
    # Auto-refresh
    if st.checkbox("Auto-refresh", value=True):
        time.sleep(refresh_rate)
        st.rerun()

# ============== MÉTRIQUES PRINCIPALES ==============
st.subheader("📊 Vue d'ensemble en temps réel")

col1, col2, col3, col4 = st.columns(4)

# Nombre total de capteurs actifs
query_sensors = f"""
    SELECT COUNT(DISTINCT sensor_id) as count
    FROM sensors_data
    WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
"""
total_sensors = get_data(query_sensors)['count'].iloc[0] if len(get_data(query_sensors)) > 0 else 0

# Nombre d'actions créées
query_actions = f"""
    SELECT COUNT(*) as count
    FROM actions
    WHERE created_at > NOW() - INTERVAL '{minutes} minutes'
"""
total_actions = get_data(query_actions)['count'].iloc[0] if len(get_data(query_actions)) > 0 else 0

# Nombre d'exécutions actuator
query_executions = f"""
    SELECT COUNT(*) as count
    FROM actuator_executions
    WHERE executed_at > NOW() - INTERVAL '{minutes} minutes'
"""
total_executions = get_data(query_executions)['count'].iloc[0] if len(get_data(query_executions)) > 0 else 0

# Actions en attente
query_pending = """
    SELECT COUNT(*) as count
    FROM actions
    WHERE status = 'pending'
"""
pending_actions = get_data(query_pending)['count'].iloc[0] if len(get_data(query_pending)) > 0 else 0

with col1:
    st.metric(
        label="🔌 Capteurs Actifs",
        value=total_sensors,
        delta=None
    )

with col2:
    st.metric(
        label="⚡ Actions Créées",
        value=total_actions,
        delta=None
    )

with col3:
    st.metric(
        label="✅ Actions Exécutées",
        value=total_executions,
        delta=None
    )

with col4:
    st.metric(
        label="⏳ En Attente",
        value=pending_actions,
        delta=None
    )

st.markdown("---")

# ============== GRAPHIQUES ==============
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Données des Capteurs (Dernières mesures)")
    
    query_recent = f"""
        SELECT 
            type,
            COUNT(*) as count,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM sensors_data
        WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
        GROUP BY type
        ORDER BY count DESC
    """
    df_sensors = get_data(query_recent)
    
    if not df_sensors.empty:
        # Graphique en barres
        fig = go.Figure()
        for sensor_type in df_sensors['type'].unique():
            data = df_sensors[df_sensors['type'] == sensor_type]
            fig.add_trace(go.Bar(
                name=f"{SENSOR_ICONS.get(sensor_type, '📊')} {sensor_type.capitalize()}",
                x=['Count'],
                y=[data['count'].iloc[0]],
                marker_color=SENSOR_COLORS.get(sensor_type, '#95a5a6'),
                text=[data['count'].iloc[0]],
                textposition='auto'
            ))
        
        fig.update_layout(
            barmode='group',
            height=300,
            showlegend=True,
            title="Nombre de mesures par type"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aucune donnée de capteurs dans cette période")

with col_right:
    st.subheader("🎯 Actions par Sévérité")
    
    query_severity = f"""
        SELECT 
            action_json->>'severity' as severity,
            COUNT(*) as count
        FROM actions
        WHERE created_at > NOW() - INTERVAL '{minutes} minutes'
        GROUP BY severity
        ORDER BY count DESC
    """
    df_severity = get_data(query_severity)
    
    if not df_severity.empty:
        # Graphique en camembert
        fig = px.pie(
            df_severity,
            values='count',
            names='severity',
            color='severity',
            color_discrete_map=SEVERITY_COLORS,
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune action créée dans cette période")

# ============== TIMELINE ==============
st.markdown("---")
st.subheader("⏱️ Timeline des Événements")

query_timeline = f"""
    SELECT 
        TO_CHAR(created_at, 'HH24:MI:SS') as time,
        COUNT(*) as actions_count
    FROM actions
    WHERE created_at > NOW() - INTERVAL '{minutes} minutes'
    GROUP BY time
    ORDER BY time DESC
    LIMIT 20
"""
df_timeline = get_data(query_timeline)

if not df_timeline.empty:
    fig = px.line(
        df_timeline.sort_values('time'),
        x='time',
        y='actions_count',
        markers=True,
        title="Actions créées au fil du temps"
    )
    fig.update_traces(line_color='#667eea', line_width=3)
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée de timeline disponible")

# ============== ACTIONS RÉCENTES ==============
st.markdown("---")
st.subheader("🔔 Actions Récentes")

query_actions_recent = f"""
    SELECT 
        action_id,
        sensor_id,
        event_type,
        action_json->>'severity' as severity,
        action_json->>'reason' as reason,
        status,
        feedback_by,
        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
    FROM actions
    WHERE created_at > NOW() - INTERVAL '{minutes} minutes'
    ORDER BY created_at DESC
    LIMIT 15
"""
df_actions = get_data(query_actions_recent)

if not df_actions.empty:
    # Ajouter des icônes et couleurs
    def format_severity(severity):
        colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        return f"{colors.get(severity, '⚪')} {severity}"
    
    df_actions['severity'] = df_actions['severity'].apply(format_severity)
    
    st.dataframe(
        df_actions,
        use_container_width=True,
        hide_index=True,
        column_config={
            "action_id": "ID Action",
            "sensor_id": "Capteur",
            "event_type": "Type",
            "severity": "Sévérité",
            "reason": "Raison",
            "status": "Statut",
            "feedback_by": "Feedback",
            "created_at": "Créé le"
        }
    )
else:
    st.warning("Aucune action récente")

# ============== EXÉCUTIONS ACTUATOR ==============
st.markdown("---")
st.subheader("🤖 Exécutions de l'Actuator")

query_executions_recent = f"""
    SELECT 
        ae.action_id,
        ae.sensor_id,
        ae.result_json->>'actuator_type' as actuator_type,
        ae.result_json->>'action_taken' as action_taken,
        ae.status,
        TO_CHAR(ae.executed_at, 'YYYY-MM-DD HH24:MI:SS') as executed_at
    FROM actuator_executions ae
    WHERE ae.executed_at > NOW() - INTERVAL '{minutes} minutes'
    ORDER BY ae.executed_at DESC
    LIMIT 15
"""
df_executions = get_data(query_executions_recent)

if not df_executions.empty:
    # Ajouter des icônes par type d'actuator
    def format_actuator_type(act_type):
        icons = {
            "street_lights": "💡",
            "waste_management": "🗑️",
            "traffic_control": "🚦",
            "water_management": "💧",
            "monitoring": "👁️"
        }
        return f"{icons.get(act_type, '⚙️')} {act_type}"
    
    df_executions['actuator_type'] = df_executions['actuator_type'].apply(format_actuator_type)
    
    st.dataframe(
        df_executions,
        use_container_width=True,
        hide_index=True,
        column_config={
            "action_id": "ID Action",
            "sensor_id": "Capteur",
            "actuator_type": "Type d'Actuator",
            "action_taken": "Action Prise",
            "status": "Statut",
            "executed_at": "Exécuté le"
        }
    )
else:
    st.info("Aucune exécution récente de l'actuator")

# ============== STATISTIQUES DÉTAILLÉES ==============
st.markdown("---")
st.subheader("📊 Statistiques Détaillées")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🚗 Traffic")
    query_traffic = f"""
        SELECT 
            COUNT(*) as total,
            AVG(value) as avg_speed,
            MIN(value) as min_speed
        FROM sensors_data
        WHERE type = 'traffic' 
        AND timestamp > NOW() - INTERVAL '{minutes} minutes'
    """
    df_traffic = get_data(query_traffic)
    if not df_traffic.empty and df_traffic['total'].iloc[0] > 0:
        st.metric("Mesures", int(df_traffic['total'].iloc[0]))
        st.metric("Vitesse Moyenne", f"{df_traffic['avg_speed'].iloc[0]:.1f} km/h")
        st.metric("Vitesse Min", f"{df_traffic['min_speed'].iloc[0]:.1f} km/h")
    else:
        st.info("Pas de données traffic")

with col2:
    st.markdown("### 🗑️ Waste")
    query_waste = f"""
        SELECT 
            COUNT(*) as total,
            AVG(value) as avg_fill,
            MAX(value) as max_fill
        FROM sensors_data
        WHERE type = 'waste' 
        AND timestamp > NOW() - INTERVAL '{minutes} minutes'
    """
    df_waste = get_data(query_waste)
    if not df_waste.empty and df_waste['total'].iloc[0] > 0:
        st.metric("Mesures", int(df_waste['total'].iloc[0]))
        st.metric("Remplissage Moyen", f"{df_waste['avg_fill'].iloc[0]:.1f}%")
        st.metric("Remplissage Max", f"{df_waste['max_fill'].iloc[0]:.1f}%")
    else:
        st.info("Pas de données waste")

with col3:
    st.markdown("### 💡 Light")
    query_light = f"""
        SELECT 
            COUNT(*) as total,
            AVG(value) as avg_lux,
            MIN(value) as min_lux
        FROM sensors_data
        WHERE type = 'light' 
        AND timestamp > NOW() - INTERVAL '{minutes} minutes'
    """
    df_light = get_data(query_light)
    if not df_light.empty and df_light['total'].iloc[0] > 0:
        st.metric("Mesures", int(df_light['total'].iloc[0]))
        st.metric("Luminosité Moyenne", f"{df_light['avg_lux'].iloc[0]:.1f} lux")
        st.metric("Luminosité Min", f"{df_light['min_lux'].iloc[0]:.1f} lux")
    else:
        st.info("Pas de données light")

# ============== FOOTER ==============
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #7f8c8d;'>"
    "🏙️ Smart City Agentic AI Dashboard | Built by chadia08 | "
    f"© {datetime.now().year}"
    "</div>",
    unsafe_allow_html=True
)