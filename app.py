import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Auditoría Autociel", layout="wide")

# --- CACHÉ PARA EVITAR ERRORES DE CUOTA ---
@st.cache_data(ttl=300)
def cargar_datos_base(_conn, url):
    df = _conn.read(spreadsheet=url, ttl=0)
    # Preguntas están en Col E y F (índices 4 y 5)
    preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
    return preguntas, df

if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    preguntas_df, df_historico = cargar_datos_base(conn, url)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Resumen de Gestión Actual")
        
        # Filtramos solo registros reales en Col G (Índice 6)
        col_notas = df_historico.iloc[:, 6].dropna()
        real_auditorias = col_notas[col_notas.isin(["Cumple", "No Cumple"])].count()
        cant_cumple = (col_notas == "Cumple").sum()
        cumplimiento_promedio = (cant_cumple / real_auditorias * 100) if real_auditorias > 0 else 0

        m1, m2 = st.columns(2)
        m1.metric("Cumplimiento Promedio", f"{int(cumplimiento_promedio)}%")
        m2.metric("Auditorías Finalizadas", real_auditorias)

        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_cumplimiento = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Volver al Tablero"):
            st.session_state.auditoria_activa = False
            st.rerun()

        respuestas = {}
        st.subheader("📝 Checklist de Gestión")
        
        for index, row in preguntas_df.iterrows():
            with st.container():
                st.write(f"**{row.iloc[0]}**")
                opcion = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                                  key=f"p_{index}", horizontal=True, label_visibility="collapsed")
                respuestas[index] = opcion
                st.markdown("---")

        # Cálculos
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        avance = (respondidas / len(preguntas_df)) * 100
        cumplimiento_actual = (cumplen / validas) * 100 if validas > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_cumplimiento.metric("Cumplimiento", f"{int(cumplimiento_actual)}%")

        # --- LÓGICA DE GUARDADO REAL ---
        if st.button("💾 Finalizar y Guardar en Excel", use_container_width=True):
            if avance < 100:
                st.warning("Debe completar todo el checklist.")
            else:
                with st.spinner("Guardando en Google Sheets..."):
                    # Preparamos los datos para la columna G
                    # Actualizamos el DataFrame original con las nuevas notas
                    for idx, res in respuestas.items():
                        df_historico.iat[idx, 6] = res
                    
                    # Enviamos los datos al Sheets
                    conn.update(spreadsheet=url, data=df_historico)
                    
                    st.cache_data.clear() # Limpiamos caché para que el tablero se actualice
                    st.success("✅ ¡Guardado con éxito! Ya puedes verlo en el Excel.")
                    st.balloons()
                    st.session_state.auditoria_activa = False # Volver al inicio

except Exception as e:
    st.error(f"Error: {e}")
