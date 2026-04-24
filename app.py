import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría Autociel Pro", layout="wide", page_icon="🚗")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_todo(url):
    df = conn.read(spreadsheet=url, ttl=0)
    # Obtenemos preguntas (Col F) y sus descripciones (Col G)
    # Creamos un diccionario para mapear Pregunta -> Descripción
    df_preguntas = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preguntas.iloc[:, 0], df_preguntas.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    
    # Porcentajes en Columna L (índice 11)
    df_hist = df.copy()
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
    historial.iloc[:, 0] = pd.to_datetime(historial.iloc[:, 0], errors='coerce')
    
    return df, lista_preguntas, mapa_descripciones, historial

try:
    df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Gestión Autociel")
        # ... (Mantengo tu lógica de métricas y gráficos igual)
        
        objetivo = 90
        total = len(df_historial)
        promedio = df_historial.iloc[:, 11].mean() if total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        m1 = c1.metric("Cumplimiento Promedio", f"{int(promedio)}%", f"{int(promedio-objetivo)}% vs Meta")
        m2 = c2.metric("Total Auditorías", total)
        m3 = c3.metric("Estatus", "✅ Óptimo" if promedio >= 90 else "⚠️ En Mejora")

        if total > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_historial.iloc[:, 0].dt.strftime('%d/%m/%Y'),
                y=df_historial.iloc[:, 11],
                marker_color=['#28A745' if x >= objetivo else '#FF4B4B' for x in df_historial.iloc[:, 11]],
                text=df_historial.iloc[:, 11].astype(int).astype(str) + "%",
                textposition='outside'
            ))
            fig.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST CON BOTÓN DE DETALLE ---
    else:
        respuestas = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        avance = (respondidas / len(lista_preguntas)) * 100

        st.title("📝 Auditoría Detallada")
        s1, s2, s3 = st.columns([2, 1, 1])
        with s1:
            st.progress(avance / 100)
        with s2:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            elif score_vivo >= 75: st.warning(f"🟡 Score: {int(score_vivo)}%")
            else: st.error(f"🔴 Score: {int(score_vivo)}%")
        with s3:
            if st.button("⬅️ Salir"):
                st.session_state.auditoria_activa = False
                st.rerun()

        with st.container(border=True):
            f1, f2 = st.columns(2)
            fecha = f1.date_input("Fecha", datetime.now())
            auditor = f2.text_input("Nombre del Auditor")

        st.markdown("---")
        
        registro_fotos = {}

        for i, preg in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {preg}", expanded=respuestas[i]=="Pendiente"):
                
                # --- NUEVA MEJORA: BOTÓN DE AYUDA / DESCRIPCIÓN ---
                desc = mapa_descripciones.get(preg, "Sin descripción disponible.")
                with st.popover("📖 Ver qué auditar aquí"):
                    st.info(f"**Criterio de Auditoría:**\n\n{desc}")
                
                st.markdown("---")
                col_resp, col_fotos = st.columns([1, 1])
                
                with col_resp:
                    st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                with col_fotos:
                    archivos = st.file_uploader(f"Fotos (Máx 4)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key=f"f_{i}")
                    if archivos:
                        registro_fotos[i] = [f.name for f in archivos[:4]]
                        m_cols = st.columns(4)
                        for idx, f in enumerate(archivos[:4]):
                            m_cols[idx].image(f, width=70)

        if st.button("💾 Finalizar y Guardar Todo", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.warning("⚠️ Checklist incompleto.")
            else:
                with st.spinner("Guardando en la nube..."):
                    nueva_fila = pd.DataFrame([[
                        str(fecha), auditor, f"AUD-{len(df_historial)+1}", 
                        "", "", "", "", "", "", 
                        str(registro_fotos), 
                        str(list(respuestas.values())), 
                        score_vivo
                    ]], columns=df_base.columns)
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Guardado exitosamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
