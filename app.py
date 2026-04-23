import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Portal Auditoría Gestión", layout="wide")

st.title("🚗 Portal de Auditoría de Gestión")
st.markdown("---")

# URL de tu planilla
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# Conexión
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
    df = df.dropna(how="all")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# El resto del código de filtros y formulario que ya tienes...
st.write("Datos cargados correctamente:")
st.dataframe(df.head())
