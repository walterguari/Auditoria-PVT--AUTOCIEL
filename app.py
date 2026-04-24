import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Auditoría Autociel", layout="wide", page_icon="🚗")
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_todo(url):
    df = conn.read(spreadsheet=url, ttl=0)
    # 1. Preguntas en Columna E (Índice 4)
    preguntas = df.iloc[:, 4].dropna().unique().tolist()
    
    # 2. Limpieza de datos para historial (Columna G / Índice 6)
    df_hist = df.copy()
    # Forzamos que la columna de notas sea numérica para el gráfico
    df_hist.iloc[:, 6] = pd.to_numeric(df_hist.iloc[:, 6], errors='coerce')
    # Filtramos solo las que tienen un número real
    historial = df_hist[df_hist.iloc[:, 6].notnull()].reset_index(drop=True)
    
    return df, preguntas, historial

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_base, lista_preguntas, df_historial = cargar_todo(url)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Panel de Control Histórico")
        
        objetivo = 90
        total_auditorias = len(df_historial)
        
        # Valores por defecto si no hay datos
        ultimo_score = 0
        cumplimiento_promedio = 0
        
        if total_auditorias > 0:
            ultimo_score = df_historial.iloc[-1, 6]
            cumplimiento_promedio = df_historial.iloc[:, 6].mean()

        # MÉTRICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(cumplimiento_promedio)}%", 
                  delta=f"{int(cumplimiento_promedio - objetivo)}% vs Meta" if total_auditorias > 0 else None)
        m2.metric("Auditorías Realizadas", total_auditorias)
        m3.metric("Último Resultado", f"{int(ultimo_score)}%")

        st.markdown("### Evolución de Resultados")
        
        if total_auditorias > 0:
            fig = go.Figure()
            # Tendencia
            fig.add_trace(go.Scatter(
                x=list(range(1, total_auditorias + 1)),
                y=df_historial.iloc[:, 6],
                mode='lines+markers',
                name='Cumplimiento %',
                line=dict(color='#FF4B4B', width=3),
                marker=dict(size=10, color='#FF4B4B')
            ))
            # Línea de Meta
            fig.add_shape(type="line", x0=1, x1=total_auditorias, y0=objetivo, y1=objetivo,
                         line=dict(color="Black", width=2, dash="dash"))
            
            fig.update_layout(yaxis=dict(range=[0, 105]), template="plotly_white", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 Aún no hay auditorías registradas. Inicia una para ver el gráfico.")

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST ---
    else:
        with st.sidebar:
            st.header("📊 Seguimiento")
            
            respuestas = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
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

        st.subheader("📝 Nueva Auditoría")
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha", datetime.now())
        auditor = c2.text_input("Nombre del Auditor")

        st.markdown("---")
        for i, preg in enumerate(lista_preguntas):
            st.write(f"**{i+1}. {preg}**")
            st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                     key=f"p_{i}", horizontal=True, label_visibility="collapsed")
            st.markdown("---")

        if st.button("💾 Guardar Auditoría", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.warning("⚠️ Completa todo el checklist y pon tu nombre.")
            else:
                with st.spinner("Guardando en el historial..."):
                    # Creamos la nueva fila asegurando que los nombres de columnas coincidan
                    nueva_fila = pd.DataFrame([{
                        df_base.columns[0]: str(fecha),
                        df_base.columns[1]: auditor,
                        df_base.columns[6]: score_vivo, # Guardar el % en la Col G
                        "Detalles": str(list(respuestas.values()))
                    }])
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    
                    st.cache_data.clear()
                    st.success("✅ Auditoría registrada correctamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error detectado: {e}")
