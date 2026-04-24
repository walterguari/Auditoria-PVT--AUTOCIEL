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
    # 1. Extraer preguntas (Columna E / Índice 4)
    preguntas = df.iloc[:, 4].dropna().unique().tolist()
    
    # 2. Filtrar Historial (Filas que tienen un valor numérico en la Columna G / Índice 6)
    # Convertimos la columna a numérico por si acaso
    df_temp = df.copy()
    df_temp.iloc[:, 6] = pd.to_numeric(df_temp.iloc[:, 6], errors='coerce')
    historial = df_temp[df_temp.iloc[:, 6].notnull()] 
    
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
        
        if total_auditorias > 0:
            ultimo_score = df_historial.iloc[-1, 6]
            cumplimiento_promedio = df_historial.iloc[:, 6].mean()
        else:
            ultimo_score = 0
            cumplimiento_promedio = 0

        # MÉTRICAS PRINCIPALES
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(cumplimiento_promedio)}%", 
                  delta=f"{int(cumplimiento_promedio - objetivo)}% vs Meta")
        m2.metric("Auditorías Realizadas", total_auditorias)
        m3.metric("Último Resultado", f"{int(ultimo_score)}%")

        st.markdown("### Evolución de Resultados")
        
        # GRÁFICO DE TENDENCIA (Líneas)
        fig_evolucion = go.Figure()
        
        # Línea de tendencia
        fig_evolucion.add_trace(go.Scatter(
            x=list(range(1, total_auditorias + 1)),
            y=df_historial.iloc[:, 6] if total_auditorias > 0 else [0],
            mode='lines+markers',
            name='Resultado %',
            line=dict(color='#FF4B4B', width=3),
            marker=dict(size=10)
        ))
        
        # Línea de Meta (90%)
        fig_evolucion.add_shape(
            type="line", x0=1, x1=max(total_auditorias, 1), y0=objetivo, y1=objetivo,
            line=dict(color="Black", width=2, dash="dash")
        )

        fig_evolucion.update_layout(
            yaxis=dict(range=[0, 105], title="Porcentaje %"),
            xaxis=dict(title="Número de Auditoría"),
            height=400,
            template="plotly_white"
        )
        st.plotly_chart(fig_evolucion, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST ---
    else:
        with st.sidebar:
            st.header("📊 Seguimiento")
            
            # Cálculo dinámico de respuestas
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
        c_f1, c_f2 = st.columns(2)
        fecha = c_f1.date_input("Fecha", datetime.now())
        auditor = c_f2.text_input("Nombre del Auditor")

        st.markdown("---")
        for i, preg in enumerate(lista_preguntas):
            st.write(f"**{i+1}. {preg}**")
            st.radio("Opciones:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                     key=f"p_{i}", horizontal=True, label_visibility="collapsed")
            st.markdown("---")

        if st.button("💾 Finalizar y Guardar en Historial", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.warning("⚠️ Completa todas las preguntas y el nombre del auditor.")
            else:
                with st.spinner("Registrando..."):
                    # Preparamos la fila para el historial
                    nueva_data = pd.DataFrame([{
                        df_base.columns[0]: str(fecha),
                        df_base.columns[1]: auditor,
                        df_base.columns[6]: score_vivo, # Guardamos el % en la Col G
                        "Detalle": str(list(respuestas.values()))
                    }])
                    
                    # Añadimos al final del Excel
                    df_final = pd.concat([df_base, nueva_data], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    
                    st.cache_data.clear()
                    st.success("✅ Guardado correctamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
