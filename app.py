import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría Autociel", layout="wide", page_icon="🚗")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_datos(url):
    df = conn.read(spreadsheet=url, ttl=0)
    # Según tu nueva imagen: Preguntas están en Columna F (índice 5)
    # Usamos unique() para que no repita la lista si ya hay filas de historial
    preguntas = df.iloc[:, 5].dropna().unique().tolist()
    
    # Historial: Leemos la Columna L (índice 11) que tiene los porcentajes
    df_hist = df.copy()
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
    
    return df, preguntas, historial

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_base, lista_preguntas, df_historial = cargar_datos(url)

    # --- PANTALLA 1: DASHBOARD HISTÓRICO ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Historial de Cumplimiento")
        
        objetivo = 90
        total_auditorias = len(df_historial)
        
        # Métricas principales
        promedio = df_historial.iloc[:, 11].mean() if total_auditorias > 0 else 0
        ultimo = df_historial.iloc[-1, 11] if total_auditorias > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Promedio Histórico", f"{int(promedio)}%", delta=f"{int(promedio-objetivo)}% vs Meta")
        c2.metric("Total Auditorías", total_auditorias)
        c3.metric("Último Resultado", f"{int(ultimo)}%")

        # GRÁFICO DE BARRAS VERTICALES
        if total_auditorias > 0:
            fig = go.Figure()
            # Barras de resultados
            fig.add_trace(go.Bar(
                x=[f"Audit {i+1}" for i in range(total_auditorias)],
                y=df_historial.iloc[:, 11],
                marker_color=['#28A745' if x >= objetivo else '#FF4B4B' for x in df_historial.iloc[:, 11]],
                text=[f"{int(x)}%" for x in df_historial.iloc[:, 11]],
                textposition='auto',
            ))
            # Línea de Meta (90%)
            fig.add_shape(type="line", x0=-0.5, x1=total_auditorias-0.5, y0=objetivo, y1=objetivo,
                         line=dict(color="Black", width=3, dash="dash"))
            
            fig.update_layout(yaxis=dict(range=[0, 105], title="Cumplimiento %"), template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay datos. Realiza la primera auditoría para ver el historial.")

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        with st.sidebar:
            st.header("📊 Seguimiento")
            respuestas = {i: st.session_state.get(f"preg_{i}", "Pendiente") for i in range(len(lista_preguntas))}
            
            respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
            cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
            validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
            
            avance = (respondidas / len(lista_preguntas)) * 100 if lista_preguntas else 0
            score_vivo = (cumplen / validas * 100) if validas > 0 else 0

            st.metric("Avance", f"{int(avance)}%")
            st.progress(avance / 100)
            st.metric("Score Actual", f"{int(score_vivo)}%")
            
            if st.button("⬅️ Cancelar"):
                st.session_state.auditoria_activa = False
                st.rerun()

        st.subheader("📝 Nueva Auditoría de Gestión")
        col_f1, col_f2 = st.columns(2)
        fecha_audit = col_f1.date_input("Fecha", datetime.now())
        nombre_auditor = col_f2.text_input("Nombre del Auditor")

        st.markdown("---")
        for i, pregunta in enumerate(lista_preguntas):
            st.write(f"**{i + 1}. {pregunta}**")
            st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                     key=f"preg_{i}", horizontal=True, label_visibility="collapsed")
            st.markdown("---")

        if st.button("💾 Guardar Auditoría en Historial", use_container_width=True, type="primary"):
            if avance < 100 or not nombre_auditor:
                st.warning("⚠️ Completa todas las preguntas y el nombre del auditor.")
            else:
                with st.spinner("Guardando nueva fila en Excel..."):
                    # CREAMOS LA FILA NUEVA PARA TU ESTRUCTURA (A hasta L)
                    nueva_fila = pd.DataFrame([[
                        str(fecha_audit), # A: Fecha
                        nombre_auditor,   # B: Auditor
                        f"ID-{total_auditorias+1}", # C: ID
                        "", "",           # D, E: Vacíos
                        "",               # F: Pregunta (opcional dejar vacío en historial)
                        "", "", "", "",   # G, H, I, J: Vacíos
                        str(list(respuestas.values())), # K: Detalle
                        score_vivo        # L: CUMPLIMIENTO %
                    ]], columns=df_base.columns)
                    
                    # Concatenamos para crear historial
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Auditoría guardada correctamente!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
