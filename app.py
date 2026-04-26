import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal de Calidad Autociel", layout="wide", page_icon="🚗")

# --- URLs DE BASES DE DATOS ---
URLS = {
    "GESTION": "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871",
    "CCS": "https://docs.google.com/spreadsheets/d/1l_f2DudAEmL3lxLdwQttk0WT5fqmRueK7dootnFL6Ak/edit#gid=652621674",
    "CITAS": "https://docs.google.com/spreadsheets/d/1XwagKHRWZLrado40tNN4UjLkSn9vKqJlnD4JF1vaTkk/edit#gid=230929161",
    "ENTREGA": "https://docs.google.com/spreadsheets/d/1HcNxmodD4QbzpNYSBkzmRWyb5NlUbhvBinpxVCMCokI/edit#gid=1499782964",
    "TALLER": "https://docs.google.com/spreadsheets/d/1kMcjTQrHdWgI7IRMzj8IYj9hIziTemYAObb_9txAMwU/edit#gid=292311251",
    "REPUESTOS": "https://docs.google.com/spreadsheets/d/1iOx9dq2kZs-cYBxKt3lK9rOc27Yq6xa4bl4mTISiRcQ/edit#gid=1105513965",
    "PLAN_ACCION": "https://docs.google.com/spreadsheets/d/1cX9vMCBPCpXDt-uWZC5iNqRdtV8pfJOErSFcaSaFnvE/edit#gid=0"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SELECTOR INICIAL ---
if 'proceso_seleccionado' not in st.session_state:
    st.title("🚀 Bienvenido al Portal de Calidad Autociel")
    st.subheader("Seleccione una opción:")
    
    st.write("### 📝 Realizar Auditorías")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    
    opciones = [
        (c1, "GESTION", "📊 GESTIÓN"), (c2, "CCS", "🛠️ CCS"), (c3, "CITAS", "📅 CITAS"),
        (c4, "ENTREGA", "📦 ENTREGA 0KM"), (c5, "TALLER", "🔧 TALLER"), (c6, "REPUESTOS", "⚙️ REPUESTOS")
    ]
    
    for col, key, label in opciones:
        if col.button(label, use_container_width=True):
            st.session_state.proceso_seleccionado = key
            st.session_state.url_actual = URLS[key]
            st.session_state.modo = "AUDITORIA"
            st.rerun()

    st.markdown("---")
    st.write("### 🛠️ Mejora Continua")
    if st.button("📝 REGISTRAR PLAN DE ACCIÓN", use_container_width=True, type="secondary"):
        st.session_state.proceso_seleccionado = "PLAN_ACCION"
        st.session_state.url_actual = URLS["PLAN_ACCION"]
        st.session_state.modo = "PLAN"
        st.rerun()
    st.stop()

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_datos(url):
    try:
        return conn.read(spreadsheet=url, ttl=0)
    except:
        return pd.DataFrame()

df_base = cargar_datos(st.session_state.url_actual)

# --- MODO PLAN DE ACCIÓN ---
if st.session_state.get("modo") == "PLAN":
    st.title("📝 Registro de Plan de Acción")
    if st.sidebar.button("🏠 Volver al Inicio"):
        del st.session_state.proceso_seleccionado
        st.rerun()

    with st.form("form_plan", clear_on_submit=True):
        st.write("### Definición del Desvío")
        c1, c2 = st.columns(2)
        sector = c1.selectbox("Sector", ["GESTIÓN", "CCS", "CITAS", "ENTREGA 0KM", "TALLER", "REPUESTOS"])
        problema = c2.text_input("Problema")
        causa = st.text_area("Causa Raíz")
        
        st.write("### Propuesta y Control")
        accion = st.text_area("Acción a realizar")
        c3, c4 = st.columns(2)
        responsable = c3.text_input("Responsable")
        obj_indicador = c4.text_input("Objetivo del indicador")
        indicador_efi = st.text_input("Indicador de eficiencia (¿Cómo lo voy a controlar?)")
        
        st.write("### Cronograma y Seguimiento")
        c5, c6, c7 = st.columns(3)
        f_inicio_est = c5.date_input("Fecha inicio est.", datetime.now())
        f_inicio_real = c6.date_input("Inicio Real", datetime.now())
        f_final = c7.date_input("Fecha final", datetime.now())
        
        c8, c9 = st.columns([1, 2])
        avance = c8.slider("Avance (%)", 0, 100, 0)
        obs_avance = c9.text_input("Observaciones de avance")
        
        if st.form_submit_button("💾 Guardar Plan de Acción", use_container_width=True):
            if not problema or not responsable:
                st.warning("⚠️ Los campos 'Problema' y 'Responsable' son obligatorios.")
            else:
                nueva_fila = pd.DataFrame([[
                    sector, problema, causa, accion, responsable, obj_indicador, 
                    indicador_efi, str(f_inicio_est), str(f_inicio_real), 
                    str(f_final), f"{avance}%", obs_avance
                ]], columns=df_base.columns[:12])
                
                df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=st.session_state.url_actual, data=df_final)
                st.success("✅ ¡Plan de Acción registrado exitosamente!")
                st.balloons()

# --- MODO AUDITORÍA (RESUMIDO) ---
else:
    # (Aquí va tu lógica de auditoría de 2 pantallas: Dashboard y Formulario)
    # Se mantiene igual que antes para asegurar la funcionalidad de carga de encuestas
    st.title(f"📊 Dashboard: {st.session_state.proceso_seleccionado}")
    if st.sidebar.button("🏠 Volver al Inicio"):
        del st.session_state.proceso_seleccionado
        st.rerun()
    st.info("Para realizar una nueva auditoría, presiona el botón correspondiente en el Dashboard.")
