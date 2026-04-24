import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría Autociel", layout="wide", page_icon="🚗")

# URL de tu Google Sheet
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# --- CONEXIÓN Y CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def cargar_datos(url):
    df = conn.read(spreadsheet=url, ttl=0)
    # Extraemos preguntas de la Columna E (índice 4)
    preguntas = df.iloc[:, 4].dropna().tolist()
    return df, preguntas

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

# --- TÍTULO PRINCIPAL ---
st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_historico, lista_preguntas = cargar_datos(url)

    # --- PANTALLA 1: DASHBOARD (RESUMEN) ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Resumen de Gestión Actual")
        
        # Cálculos de cumplimiento (Columna G / Índice 6)
        col_notas = df_historico.iloc[:, 6].dropna()
        real_auditorias = col_notas[col_notas.isin(["Cumple", "No Cumple"])].count()
        cant_cumple = (col_notas == "Cumple").sum()
        cumplimiento_promedio = (cant_cumple / real_auditorias * 100) if real_auditorias > 0 else 0
        objetivo = 90

        # Layout del Dashboard: Métricas a la izquierda, Gráfico a la derecha
        c1, c2 = st.columns([1, 2])

        with c1:
            st.metric(
                label="Cumplimiento Promedio", 
                value=f"{int(cumplimiento_promedio)}%",
                delta=f"{int(cumplimiento_promedio - objetivo)}% vs Objetivo (90%)",
                delta_color="normal" if cumplimiento_promedio >= objetivo else "inverse"
            )
            st.metric("Auditorías Finalizadas", real_auditorias)
            st.info(f"Última actualización: {datetime.now().strftime('%H:%M')}")

        with c2:
            # --- GRÁFICO DE BARRAS VERTICAL ---
            fig = go.Figure()

            # Barra de resultado actual
            fig.add_trace(go.Bar(
                x=['Estado Actual'],
                y=[cumplimiento_promedio],
                marker_color='#FF4B4B' if cumplimiento_promedio < objetivo else '#28A745',
                text=[f"{int(cumplimiento_promedio)}%"],
                textposition='auto',
                name='Cumplimiento'
            ))

            # Línea de Objetivo (90%)
            fig.add_shape(
                type="line", x0=-0.5, x1=0.5, y0=objetivo, y1=objetivo,
                line=dict(color="Black", width=3, dash="dash")
            )
            
            # Etiqueta de la línea de objetivo
            fig.add_annotation(
                x=0, y=objetivo + 5, text=f"Meta: {objetivo}%",
                showarrow=False, font=dict(size=14, color="black")
            )

            fig.update_layout(
                yaxis=dict(range=[0, 100], title="Porcentaje"),
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.subheader("📝 Checklist de Gestión")
        
        with st.sidebar:
            st.header("📊 Seguimiento")
            p_avance = st.empty()
            p_cumplimiento = st.empty()
            if st.button("⬅️ Volver al Tablero"):
                st.session_state.auditoria_activa = False
                st.rerun()

        respuestas = {}
        
        # Usamos un formulario para evitar recargas lentas
        with st.form("auditoria_form"):
            for index, pregunta in enumerate(lista_preguntas):
                st.write(f"**{index + 1}. {pregunta}**")
                opcion = st.radio(
                    "Resultado:", 
                    ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                    key=f"preg_{index}", 
                    horizontal=True, 
                    label_visibility="collapsed"
                )
                respuestas[index] = opcion
                st.markdown("---")
            
            boton_guardar = st.form_submit_button("💾 Finalizar y Guardar")

        # Cálculos en tiempo real para la barra lateral
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        avance = (respondidas / len(lista_preguntas)) * 100 if lista_preguntas else 0
        
        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)

        if boton_guardar:
            if avance < 100:
                st.warning("⚠️ Por favor, complete todas las preguntas antes de finalizar.")
            else:
                with st.spinner("Guardando en Google Sheets..."):
                    # Actualizamos el DataFrame original con las nuevas respuestas
                    # Nota: Esto asume que el índice del DF coincide con el orden de las preguntas
                    for idx, res in respuestas.items():
                        df_historico.iat[idx, 6] = res
                    
                    # Subir cambios
                    conn.update(spreadsheet=url, data=df_historico)
                    
                    st.cache_data.clear() 
                    st.success("✅ ¡Auditoría guardada con éxito!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Se produjo un error: {e}")
    st.info("Revisa la conexión con tu Google Sheet y las credenciales en Secrets.")
