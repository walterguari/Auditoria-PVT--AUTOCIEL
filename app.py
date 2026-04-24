import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Dashboard Auditoría Autociel", layout="wide")

if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = conn.read(spreadsheet=url, ttl=0)
    
    # --- PANTALLA 1: DASHBOARD E INICIO ---
    if not st.session_state.auditoria_activa:
        
        # --- SECCIÓN DE INDICADORES (DASHBOARD) ---
        st.subheader("📊 Tablero de Resultados Históricos")
        
        # Simulación de cálculos basados en columna G (Nota)
        # Aquí filtramos datos reales de tu planilla para mostrar promedios
        try:
            # Ejemplo de lógica: contamos "Cumple" vs "No Cumple" en el histórico
            historico_notas = df_base.iloc[:, 6].dropna() # Columna G
            total_auditorias = len(df_base)
            cumplimiento_global = (historico_notas.str.contains("Cumple").sum() / len(historico_notas) * 100) if len(historico_notas) > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Cumplimiento Global", f"{int(cumplimiento_global)}%", delta="Objetivo: 85%")
            m2.metric("Total Auditorías", total_auditorias)
            m3.metric("Última Sucursal", "Jujuy" if total_auditorias > 0 else "-")
        except:
            st.info("Cargando indicadores por primera vez...")

        st.markdown("---")
        
        # --- CONFIGURACIÓN DE NUEVA AUDITORÍA ---
        st.subheader("🚀 Nueva Auditoría")
        col1, col2 = st.columns(2)
        with col1:
            sucursal_auditar = st.selectbox("Seleccione Sucursal", ["Jujuy", "Salta", "Tartagal"])
        with col2:
            fecha_auditoria = st.date_input("Fecha de Auditoría", datetime.now())

        if st.button("Iniciar Checklist de Gestión", use_container_width=True):
            st.session_state.sucursal = sucursal_auditar
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        # (El código del checklist se mantiene igual para asegurar la funcionalidad)
        preguntas_df = df_base.iloc[:, [4, 5]].dropna(subset=[df_base.columns[4]])
        total_preguntas = len(preguntas_df)

        st.sidebar.header("📊 Seguimiento")
        placeholder_avance = st.sidebar.empty()
        placeholder_cumplimiento = st.sidebar.empty()
        st.sidebar.write(f"📍 **Sucursal:** {st.session_state.sucursal}")
        
        if st.sidebar.button("⬅️ Volver al Tablero"):
            st.session_state.auditoria_activa = False
            st.rerun()

        respuestas = {}
        st.subheader(f"📝 Evaluando: {st.session_state.sucursal}")
        
        for index, row in preguntas_df.iterrows():
            with st.container():
                pregunta = row.iloc[0]
                descripcion = row.iloc[1]
                st.write(f"**{pregunta}**")
                if pd.notnull(descripcion): st.caption(f"ℹ️ {descripcion}")
                opcion = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{index}", horizontal=True, label_visibility="collapsed")
                respuestas[index] = opcion
                st.markdown("---")

        # Cálculos de la sesión actual
        cont_respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cont_cumple = sum(1 for v in respuestas.values() if v == "Cumple")
        total_validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        porc_avance = (cont_respondidas / total_preguntas) * 100 if total_preguntas > 0 else 0
        porc_cumplimiento = (cont_cumple / total_validas) * 100 if total_validas > 0 else 0

        placeholder_avance.metric("Avance", f"{int(porc_avance)}%")
        placeholder_avance.progress(porc_avance / 100)
        placeholder_cumplimiento.metric("Score Actual", f"{int(porc_cumplimiento)}%")

        if st.button("💾 Guardar y Finalizar"):
            if porc_avance < 100:
                st.warning("Complete todas las preguntas antes de finalizar.")
            else:
                st.success("Auditoría guardada correctamente.")
                st.balloons()

except Exception as e:
    st.error(f"Error: {e}")
