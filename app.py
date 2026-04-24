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
    # Lista fija de preguntas (Columna E)
    preguntas = df.iloc[:, 4].dropna().unique().tolist()
    # Asumimos que el historial de auditorías está en la misma hoja o puedes crear una nueva
    # Para este ejemplo, filtramos las filas que ya tienen resultados en la Columna G (Cumplimiento %)
    historial = df[df.iloc[:, 6].notlineal()] # Ajusta según tu estructura de Excel
    return df, preguntas, historial

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_base, lista_preguntas, df_historial = cargar_todo(url)

    # --- PANTALLA 1: DASHBOARD CON HISTORIAL ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Panel de Control Histórico")
        
        # Simulamos que la columna 6 tiene los porcentajes pasados
        # Si tu Excel está vacío, esto mostrará datos iniciales
        if not df_historial.empty:
            ultimo_score = df_historial.iloc[-1, 6] 
            total_auditorias = len(df_historial)
        else:
            ultimo_score = 0
            total_auditorias = 0
            
        objetivo = 90

        # FILA 1: MÉTRICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Último Resultado", f"{int(ultimo_score)}%", delta=f"{int(ultimo_score-objetivo)}% vs Meta")
        m2.metric("Total Auditorías", total_auditorias)
        m3.metric("Objetivo", f"{objetivo}%")

        # FILA 2: GRÁFICOS
        g1, g2 = st.columns(2)
        
        with g1:
            st.write("**Evolución de Cumplimiento (Tendencia)**")
            # Gráfico de líneas para ver Enero, Febrero, etc.
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                y=df_historial.iloc[:, 6] if not df_historial.empty else [0], 
                mode='lines+markers',
                line=dict(color='#FF4B4B', width=4),
                name="Auditoría"
            ))
            fig_line.add_shape(type="line", x0=0, x1=total_auditorias, y0=objetivo, y1=objetivo, line=dict(color="Black", dash="dash"))
            fig_line.update_layout(yaxis=dict(range=[0, 105]), height=300, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig_line, use_container_width=True)

        with g2:
            st.write("**Último Resultado vs Meta**")
            fig_bar = go.Figure(go.Bar(
                x=['Actual'], y=[ultimo_score],
                marker_color='#28A745' if ultimo_score >= objetivo else '#FF4B4B'
            ))
            fig_bar.add_shape(type="line", x0=-0.5, x1=0.5, y0=objetivo, y1=objetivo, line=dict(color="Black", dash="dash"))
            fig_bar.update_layout(yaxis=dict(range=[0, 105]), height=300, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig_bar, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST DINÁMICO ---
    else:
        with st.sidebar:
            st.header("📊 Seguimiento")
            
            # Recálculo en tiempo real
            respuestas = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
            respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
            cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
            validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
            
            avance = (respondidas / len(lista_preguntas)) * 100
            score_vivo = (cumplen / validas * 100) if validas > 0 else 0

            st.metric("Avance", f"{int(avance)}%")
            st.progress(avance / 100)
            st.metric("Score Actual", f"{int(score_vivo)}%")
            
            if st.button("⬅️ Cancelar"):
                st.session_state.auditoria_activa = False
                st.rerun()

        st.subheader("📝 Nueva Auditoría de Gestión")
        col_f1, col_f2 = st.columns(2)
        fecha = col_f1.date_input("Fecha", datetime.now())
        auditor = col_f2.text_input("Auditor", placeholder="Tu nombre")

        st.markdown("---")
        for i, preg in enumerate(lista_preguntas):
            st.write(f"**{i+1}. {preg}**")
            st.radio("Opciones:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True, label_visibility="collapsed")
            st.markdown("---")

        if st.button("💾 Finalizar y Guardar Historial", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.error("Faltan preguntas por responder o el nombre del auditor.")
            else:
                with st.spinner("Guardando registro histórico..."):
                    # CREAMOS LA NUEVA FILA
                    nueva_fila = {
                        "Fecha": str(fecha),
                        "Auditor": auditor,
                        "Cumplimiento %": score_vivo,
                        "Detalles": str(list(respuestas.values())) # Guarda todas las respuestas como texto
                    }
                    
                    # Convertimos a DataFrame y concatenamos al historial existente
                    df_nuevo_registro = pd.DataFrame([nueva_fila])
                    
                    # Importante: Aquí 'update' sube el dataframe completo. 
                    # Asegúrate de que tu hoja de Google Sheets tenga estas columnas preparadas.
                    df_final = pd.concat([df_base, df_nuevo_registro], ignore_index=True)
                    
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("¡Auditoría guardada en el historial!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error de conexión o datos: {e}")
