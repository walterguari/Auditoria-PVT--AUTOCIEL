import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Auditoría Autociel", layout="wide", page_icon="🚗")

# --- CONFIGURACIÓN DE CONEXIÓN ---
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def cargar_preguntas(url):
    # Cargamos solo la lista de preguntas (ajusta el rango según tu Excel)
    df = conn.read(spreadsheet=url, ttl=0)
    # Asumiendo que las preguntas están en la Columna E
    return df.iloc[:, 4].dropna().tolist()

@st.cache_data(ttl=60)
def obtener_historico(url):
    return conn.read(spreadsheet=url, ttl=0)

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    preguntas = cargar_preguntas(url)
    df_completo = obtener_historico(url)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Resumen de Gestión Actual")
        
        # Supongamos que los resultados históricos están en una hoja aparte o después de la col G
        # Aquí una métrica simple basada en los datos actuales
        col_notas = df_completo.iloc[:, 6].dropna()
        real_auditorias = len(col_notas[col_notas.isin(["Cumple", "No Cumple"])])
        cant_cumple = (col_notas == "Cumple").sum()
        cumplimiento_promedio = (cant_cumple / real_auditorias * 100) if real_auditorias > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(cumplimiento_promedio)}%")
        m2.metric("Auditorías Realizadas", real_auditorias)
        m3.metric("Última Actualización", datetime.now().strftime("%H:%M"))

        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        with st.sidebar:
            st.header("⚙️ Opciones")
            auditor = st.text_input("Nombre del Auditor", placeholder="Ej: Juan Pérez")
            if st.button("⬅️ Cancelar y Volver"):
                st.session_state.auditoria_activa = False
                st.rerun()
            
            st.markdown("---")
            p_avance = st.empty()
            p_cumplimiento = st.empty()

        respuestas = {}
        st.subheader("📝 Checklist de Gestión")
        
        # Formulario para agrupar inputs
        with st.form("form_auditoria"):
            for i, pregunta in enumerate(preguntas):
                st.write(f"**{i+1}. {pregunta}**")
                respuestas[i] = st.radio(
                    f"Resultado {i}", 
                    ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                    key=f"p_{i}", 
                    horizontal=True, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            submit = st.form_submit_button("💾 Finalizar y Guardar Auditoría", use_container_width=True)

        # Cálculos de tiempo real (fuera del form para actualizar métricas)
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        avance = (respondidas / len(preguntas)) * 100
        cumplimiento_actual = (cumplen / validas) * 100 if validas > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_cumplimiento.metric("Score Actual", f"{int(cumplimiento_actual)}%")

        if submit:
            if avance < 100:
                st.error("❌ Por favor, responda todas las preguntas antes de guardar.")
            elif not auditor:
                st.error("❌ Por favor, ingrese el nombre del auditor.")
            else:
                with st.spinner("Transmitiendo datos a la central..."):
                    # 1. Crear nueva fila de datos
                    nueva_data = pd.DataFrame([{
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Auditor": auditor,
                        "Resultado %": cumplimiento_actual,
                        # Aquí podrías concatenar las respuestas o guardarlas en columnas
                        "Detalle": str(list(respuestas.values())) 
                    }])
                    
                    # 2. Concatenar con el histórico (o escribir en una hoja específica)
                    # NOTA: Para producción, se recomienda una hoja de "Logs"
                    df_actualizado = pd.concat([df_completo, nueva_data], ignore_index=True)
                    
                    conn.update(spreadsheet=url, data=df_actualizado)
                    
                    st.cache_data.clear()
                    st.success("✅ Auditoría registrada correctamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    # Pequeña pausa antes de recargar
                    st.rerun()

except Exception as e:
    st.error(f"Hubo un problema con la conexión: {e}")
    st.info("Asegúrate de que las credenciales de Google Sheets estén configuradas en .streamlit/secrets.toml")
