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

@st.cache_data(ttl=300)
def cargar_datos(url):
    df = conn.read(spreadsheet=url, ttl=0)
    preguntas = df.iloc[:, 4].dropna().tolist()
    return df, preguntas

# --- ESTADO DE LA SESIÓN ---
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

try:
    df_historico, lista_preguntas = cargar_datos(url)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        # (Mantengo tu dashboard anterior igual porque funcionaba bien)
        st.subheader("📊 Resumen de Gestión Actual")
        col_notas = df_historico.iloc[:, 6].dropna()
        real_auditorias = col_notas[col_notas.isin(["Cumple", "No Cumple"])].count()
        cant_cumple = (col_notas == "Cumple").sum()
        cumplimiento_promedio = (cant_cumple / real_auditorias * 100) if real_auditorias > 0 else 0
        objetivo = 90

        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Cumplimiento Promedio", f"{int(cumplimiento_promedio)}%", 
                      delta=f"{int(cumplimiento_promedio - objetivo)}% vs Meta")
            st.metric("Auditorías Finalizadas", real_auditorias)
        
        with c2:
            fig = go.Figure(go.Bar(x=['Estado'], y=[cumplimiento_promedio], 
                                  marker_color='#FF4B4B' if cumplimiento_promedio < objetivo else '#28A745'))
            fig.add_shape(type="line", x0=-0.5, x1=0.5, y0=objetivo, y1=objetivo, line=dict(color="Black", dash="dash"))
            fig.update_layout(yaxis=dict(range=[0, 100]), height=250, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST (AQUÍ ESTÁN LOS CAMBIOS) ---
    else:
        # 1. SIDEBAR CON MÉTRICAS EN TIEMPO REAL
        with st.sidebar:
            st.header("📊 Seguimiento")
            
            # Recolectamos respuestas fuera de un form para que Streamlit detecte el cambio
            respuestas = {}
            for i in range(len(lista_preguntas)):
                # Buscamos si ya existe el valor en el session_state, si no, "Pendiente"
                val_actual = st.session_state.get(f"preg_{i}", "Pendiente")
                respuestas[i] = val_actual

            # Cálculos de seguimiento
            respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
            cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
            validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
            
            avance = (respondidas / len(lista_preguntas)) * 100 if lista_preguntas else 0
            cumplimiento_real = (cumplen / validas * 100) if validas > 0 else 0

            st.metric("Avance del Checklist", f"{int(avance)}%")
            st.progress(avance / 100)
            st.metric("Cumplimiento Actual", f"{int(cumplimiento_real)}%")
            
            st.markdown("---")
            if st.button("⬅️ Cancelar y Volver"):
                st.session_state.auditoria_activa = False
                st.rerun()

        # 2. CUERPO DEL CHECKLIST
        st.subheader("📝 Nuevo Checklist de Gestión")
        
        # Campo de Fecha
        fecha_auditoria = st.date_input("Fecha de la Auditoría", datetime.now())
        st.info("Seleccione los resultados a continuación. El progreso se ve en la barra lateral.")
        st.markdown("---")

        # Renderizamos las preguntas (SIN FORM para que el sidebar sea dinámico)
        for index, pregunta in enumerate(lista_preguntas):
            st.write(f"**{index + 1}. {pregunta}**")
            st.radio(
                "Resultado:", 
                ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                key=f"preg_{index}", # El key actualiza el session_state automáticamente
                horizontal=True, 
                label_visibility="collapsed"
            )
            st.markdown("---")

        # Botón de guardado final
        if st.button("💾 Finalizar y Guardar en Excel", use_container_width=True, type="primary"):
            if avance < 100:
                st.warning("⚠️ Todavía tienes preguntas en 'Pendiente'.")
            else:
                with st.spinner("Guardando..."):
                    # Actualizamos el DataFrame
                    for idx, res in respuestas.items():
                        df_historico.iat[idx, 6] = res
                    
                    # Opcional: Podrías guardar la fecha en una celda específica si quieres
                    # df_historico.iat[0, 0] = str(fecha_auditoria) 

                    conn.update(spreadsheet=url, data=df_historico)
                    st.cache_data.clear()
                    st.success(f"✅ Auditoría del {fecha_auditoria} guardada!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
