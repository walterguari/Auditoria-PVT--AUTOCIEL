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
    
    # Mapa de Preguntas y Descripciones (Col F y Col G)
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    
    # Historial para el Dashboard (Col L / Índice 11)
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
        
        with st.expander("🔍 Filtros de Búsqueda"):
            f_col1, f_col2 = st.columns(2)
            auditores_unicos = df_historial.iloc[:, 1].unique()
            sel_auditor = f_col1.multiselect("Filtrar por Auditor", options=auditores_unicos)
            df_display = df_historial.copy()
            if sel_auditor:
                df_display = df_display[df_display.iloc[:, 1].isin(sel_auditor)]

        meta = 90
        total_audits = len(df_display)
        promedio_gral = df_display.iloc[:, 11].mean() if total_audits > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(promedio_gral)}%", f"{int(promedio_gral - meta)}% vs Meta")
        m2.metric("Total Auditorías", total_audits)
        m3.metric("Estatus Global", "✅ Óptimo" if promedio_gral >= meta else "⚠️ En Mejora")

        st.markdown("### 📅 Tendencia Mensual")
        if total_audits > 0:
            df_m = df_display.copy()
            df_m['Mes'] = df_m.iloc[:, 0].dt.strftime('%Y-%m')
            resumen_m = df_m.groupby('Mes')[df_m.columns[11]].mean().reset_index()
            fig_m = go.Figure()
            fig_m.add_trace(go.Scatter(x=resumen_m['Mes'], y=resumen_m.iloc[:, 1], mode='lines+markers+text',
                                     text=resumen_m.iloc[:, 1].astype(int).astype(str) + "%", textposition="top center",
                                     line=dict(color='#1E88E5', width=4)))
            fig_m.add_shape(type="line", x0=-0.5, x1=len(resumen_m)-0.5, y0=meta, y1=meta, line=dict(color="Red", dash="dash"))
            fig_m.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=300)
            st.plotly_chart(fig_m, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: FORMULARIO ---
    else:
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        progreso = (contestadas / len(lista_preguntas)) * 100

        st.title("📝 Auditoría Autociel Pro")
        c_p, c_s, c_x = st.columns([2, 1, 1])
        with c_p: st.progress(progreso / 100)
        with c_s:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            elif score_vivo >= 75: st.warning(f"🟡 Score: {int(score_vivo)}%")
            else: st.error(f"🔴 Score: {int(score_vivo)}%")
        with c_x:
            if st.button("⬅️ Salir"):
                st.session_state.auditoria_activa = False
                st.rerun()

        with st.container(border=True):
            f1, f2 = st.columns(2)
            fecha_a = f1.date_input("Fecha", datetime.now())
            auditor_n = f2.text_input("Nombre del Auditor")

        st.markdown("---")
        
        # Almacenes de datos adicionales
        datos_adicionales = {} # Guardará {índice: {'fotos': [...], 'obs': "..."}}

        for i, pregunta in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {pregunta}", expanded=resp_actuales[i]=="Pendiente"):
                detalle = mapa_descripciones.get(pregunta, "Sin descripción.")
                with st.popover("📖 Guía técnica"):
                    st.info(detalle)
                
                col_r, col_f, col_obs = st.columns([1, 1, 1])
                
                with col_r:
                    st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                with col_f:
                    # CARGA DE HASTA 6 FOTOS
                    archivos = st.file_uploader(f"Fotos (Máx 6)", type=['jpg','jpeg','png'], accept_multiple_files=True, key=f"f_{i}")
                
                with col_obs:
                    # CUADRO DE OBSERVACIONES POR PREGUNTA
                    observacion = st.text_area("Observaciones / Relato:", key=f"obs_{i}", placeholder="Detalle el hallazgo aquí...")
                
                # Guardamos los nombres de archivos si existen
                if archivos or observacion:
                    datos_adicionales[i] = {
                        'fotos': [f.name for f in archivos[:6]] if archivos else [],
                        'comentario': observacion
                    }
                
                if archivos:
                    m_cols = st.columns(6)
                    for idx, img in enumerate(archivos[:6]):
                        m_cols[idx].image(img, width=60)

        if st.button("💾 Finalizar y Guardar", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_n:
                st.warning("⚠️ Checklist incompleto.")
            else:
                with st.spinner("Enviando a Google Sheets..."):
                    # Columna J ahora guarda tanto fotos como observaciones
                    nueva_fila = pd.DataFrame([[
                        str(fecha_a), auditor_n, f"AUD-{len(df_historial)+1}", 
                        "", "", "", "", "", "", 
                        str(datos_adicionales),         # J: Fotos y Observaciones detalladas
                        str(list(resp_actuales.values())), # K: Respuestas
                        score_vivo                      # L: Score
                    ]], columns=df_base.columns)
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Guardado.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
