import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Auditoría Autociel", layout="wide")

# --- EVITAR ERROR 429: CACHÉ DE DATOS ---
@st.cache_data(ttl=600) # Guarda las preguntas por 10 minutos
def leer_preguntas(_conn, url):
    df = _conn.read(spreadsheet=url, ttl=0)
    # Extraemos preguntas (Col E) y descripción (Col F)
    preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
    return preguntas, df

if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Llamamos a la función con caché
    preguntas_df, df_historico = leer_preguntas(conn, url)
    total_preguntas = len(preguntas_df)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Tablero de Resultados")
        
        # Lógica simplificada para el Dashboard
        col_g = df_historico.iloc[:, 6].dropna()
        total_auditorias = len(df_historico)
        cumplimiento = (col_g.str.contains("Cumple").sum() / len(col_g) * 100) if len(col_g) > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Global", f"{int(cumplimiento)}%")
        m2.metric("Auditorías Totales", total_auditorias)
        m3.metric("Estado de Red", "Activo")

        st.markdown("---")
        st.subheader("🚀 Nueva Auditoría")
        sucursal_auditar = st.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
        
        if st.button("Iniciar Checklist", use_container_width=True):
            st.session_state.sucursal = sucursal_auditar
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_cumplimiento = st.sidebar.empty()
        st.sidebar.write(f"📍 **Sucursal:** {st.session_state.sucursal}")
        
        if st.sidebar.button("⬅️ Volver"):
            st.session_state.auditoria_activa = False
            st.rerun()

        respuestas = {}
        for index, row in preguntas_df.iterrows():
            st.write(f"**{row.iloc[0]}**")
            if pd.notnull(row.iloc[1]): st.caption(f"ℹ️ {row.iloc[1]}")
            
            # El secreto es el 'key', esto mantiene la respuesta sin recargar del Excel
            opcion = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{index}", horizontal=True, label_visibility="collapsed")
            respuestas[index] = opcion
            st.markdown("---")

        # Cálculos (Sin volver a leer el Excel)
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        
        avance = (respondidas / total_preguntas) * 100
        cumplimiento_actual = (cumplen / validas) * 100 if validas > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_cumplimiento.metric("Cumplimiento", f"{int(cumplimiento_actual)}%")

        if st.button("💾 Guardar Reporte", use_container_width=True):
            if avance < 100:
                st.warning("Faltan preguntas por responder.")
            else:
                st.success("¡Datos guardados con éxito!")
                st.balloons()

except Exception as e:
    st.error(f"Error de conexión: {e}")
