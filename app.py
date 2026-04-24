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
    # Extraemos preguntas de la Columna E (Índice 4)
    preguntas = df.iloc[:, 4].dropna().unique().tolist()
    
    # Historial: Filtramos filas que tengan un porcentaje real en la Columna G (Índice 6)
    df_temp = df.copy()
    df_temp.iloc[:, 6] = pd.to_numeric(df_temp.iloc[:, 6], errors='coerce')
    historial = df_temp[df_temp.iloc[:, 6].notnull()].reset_index(drop=True)
    
    return df, preguntas, historial

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_completo, lista_preguntas, df_historial = cargar_datos(url)

    # --- PANTALLA 1: DASHBOARD CON HISTORIAL ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Resumen de Gestión e Historial")
        
        objetivo = 90
        total_auditorias = len(df_historial)
        
        # Valores por defecto si está vacío
        promedio_historico = df_historial.iloc[:, 6].mean() if total_auditorias > 0 else 0
        ultimo_resultado = df_historial.iloc[-1, 6] if total_auditorias > 0 else 0

        # FILA 1: MÉTRICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Promedio General", f"{int(promedio_historico)}%", 
                  delta=f"{int(promedio_historico - objetivo)}% vs Meta")
        m2.metric("Auditorías Registradas", total_auditorias)
        m3.metric("Último Resultado", f"{int(ultimo_resultado)}%")

        # FILA 2: GRÁFICO DE TENDENCIA
        st.markdown("### 📈 Evolución en el Tiempo")
        if total_auditorias > 0:
            fig = go.Figure()
            # Línea de tendencia
            fig.add_trace(go.Scatter(
                x=list(range(1, total_auditorias + 1)),
                y=df_historial.iloc[:, 6],
                mode='lines+markers',
                name='Resultado %',
                line=dict(color='#FF4B4B', width=3),
                marker=dict(size=10)
            ))
            # Línea de Meta (90%)
            fig.add_shape(type="line", x0=1, x1=total_auditorias, y0=objetivo, y1=objetivo,
                         line=dict(color="Black", width=2, dash="dash"))
            
            fig.update_layout(yaxis=dict(range=[0, 105], title="Cumplimiento %"), 
                              xaxis=dict(title="Número de Auditoría"),
                              template="plotly_white", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay registros para mostrar tendencia. Realiza tu primera auditoría.")

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        with st.sidebar:
            st.header("📊 Seguimiento")
            
            # Recolectamos respuestas en tiempo real
            respuestas = {i: st.session_state.get(f"preg_{i}", "Pendiente") for i in range(len(lista_preguntas))}
            respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
            cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
            validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
            
            avance = (respondidas / len(lista_preguntas)) * 100 if lista_preguntas else 0
            score_actual = (cumplen / validas * 100) if validas > 0 else 0

            st.metric("Avance", f"{int(avance)}%")
            st.progress(avance / 100)
            st.metric("Cumplimiento Actual", f"{int(score_actual)}%")
            
            st.markdown("---")
            if st.button("⬅️ Cancelar"):
                st.session_state.auditoria_activa = False
                st.rerun()

        st.subheader("📝 Nuevo Checklist de Gestión")
        
        c1, c2 = st.columns(2)
        fecha_auditoria = c1.date_input("Fecha de la Auditoría", datetime.now())
        nombre_auditor = c2.text_input("Nombre del Auditor", placeholder="Ej: Juan Pérez")

        st.markdown("---")

        for index, pregunta in enumerate(lista_preguntas):
            st.write(f"**{index + 1}. {pregunta}**")
            st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                     key=f"preg_{index}", horizontal=True, label_visibility="collapsed")
            st.markdown("---")

        if st.button("💾 Finalizar y Guardar Historial", use_container_width=True, type="primary"):
            if avance < 100 or not nombre_auditor:
                st.warning("⚠️ Completa todas las preguntas y el nombre del auditor.")
            else:
                with st.spinner("Guardando registro histórico..."):
                    # CREAMOS LA NUEVA FILA
                    nueva_fila = pd.DataFrame([{
                        df_completo.columns[0]: str(fecha_auditoria), # Col A
                        df_completo.columns[1]: nombre_auditor,      # Col B
                        df_completo.columns[6]: score_actual,        # Col G (Porcentaje)
                        "Detalle": str(list(respuestas.values()))    # Col de backup
                    }])
                    
                    # Concatenamos la nueva fila al final del archivo original
                    df_final = pd.concat([df_completo, nueva_fila], ignore_index=True)
                    
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ ¡Auditoría guardada en el historial!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
