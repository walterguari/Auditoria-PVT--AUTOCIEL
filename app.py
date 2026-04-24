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
    
    # 1. Mapa de Preguntas y Descripciones (Col F y Col G)
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    
    # 2. Historial para el Dashboard (Col L / Índice 11)
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
        
        # Filtros
        with st.expander("🔍 Filtros de Búsqueda"):
            f_col1, f_col2 = st.columns(2)
            auditores_unicos = df_historial.iloc[:, 1].unique()
            sel_auditor = f_col1.multiselect("Filtrar por Auditor", options=auditores_unicos)
            
            df_display = df_historial.copy()
            if sel_auditor:
                df_display = df_display[df_display.iloc[:, 1].isin(sel_auditor)]

        # Métricas principales
        meta = 90
        total_audits = len(df_display)
        promedio_gral = df_display.iloc[:, 11].mean() if total_audits > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(promedio_gral)}%", f"{int(promedio_gral - meta)}% vs Meta")
        m2.metric("Total Auditorías", total_audits)
        m3.metric("Estatus Global", "✅ Óptimo" if promedio_gral >= meta else "⚠️ En Mejora")

        # --- NUEVA MEJORA: HISTORIAL MENSUAL ---
        st.markdown("### 📅 Tendencia de Cumplimiento Mensual")
        if total_audits > 0:
            # Agrupar por mes
            df_mensual = df_display.copy()
            df_mensual['Mes'] = df_mensual.iloc[:, 0].dt.strftime('%Y-%m')
            resumen_mensual = df_mensual.groupby('Mes')[df_mensual.columns[11]].mean().reset_index()
            
            fig_mes = go.Figure()
            fig_mes.add_trace(go.Scatter(
                x=resumen_mensual['Mes'], 
                y=resumen_mensual.iloc[:, 1],
                mode='lines+markers+text',
                text=resumen_mensual.iloc[:, 1].astype(int).astype(str) + "%",
                textposition="top center",
                line=dict(color='#1E88E5', width=4),
                marker=dict(size=10)
            ))
            fig_mes.add_shape(type="line", x0=-0.5, x1=len(resumen_mensual)-0.5, y0=meta, y1=meta, 
                              line=dict(color="Red", dash="dash"))
            fig_mes.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=300)
            st.plotly_chart(fig_mes, use_container_width=True)

        # Gráfico por Auditoría Individual
        st.markdown("### 📈 Detalle por Auditoría")
        if total_audits > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_display.iloc[:, 0].dt.strftime('%d/%m/%Y'),
                y=df_display.iloc[:, 11],
                marker_color=['#28A745' if x >= meta else '#FF4B4B' for x in df_display.iloc[:, 11]],
                text=df_display.iloc[:, 11].astype(int).astype(str) + "%",
                textposition='outside'
            ))
            fig.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=350)
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: FORMULARIO ---
    else:
        # Lógica de Score y Avance
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        progreso = (contestadas / len(lista_preguntas)) * 100

        # Cabecera
        st.title("📝 Nueva Auditoría Detallada")
        c_prog, c_semaf, c_salir = st.columns([2, 1, 1])
        with c_prog:
            st.progress(progreso / 100)
        with c_semaf:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            elif score_vivo >= 75: st.warning(f"🟡 Score: {int(score_vivo)}%")
            else: st.error(f"🔴 Score: {int(score_vivo)}%")
        with c_salir:
            if st.button("⬅️ Salir"):
                st.session_state.auditoria_activa = False
                st.rerun()

        with st.container(border=True):
            f_col1, f_col2 = st.columns(2)
            fecha_audit = f_col1.date_input("Fecha", datetime.now())
            auditor_txt = f_col2.text_input("Nombre del Auditor")

        st.markdown("---")
        
        fotos_data = {}
        for i, pregunta in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {pregunta}", expanded=resp_actuales[i]=="Pendiente"):
                detalle_ayuda = mapa_descripciones.get(pregunta, "Sin descripción.")
                with st.popover("📖 Guía de Auditoría"):
                    st.info(detalle_ayuda)
                
                col_radio, col_foto = st.columns([1, 1])
                with col_radio:
                    st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                with col_foto:
                    imgs = st.file_uploader(f"Fotos (Máx 4)", type=['jpg','jpeg','png'], accept_multiple_files=True, key=f"f_{i}")
                    if imgs:
                        fotos_data[i] = [img.name for img in imgs[:4]]
                        cols_img = st.columns(4)
                        for idx, img_file in enumerate(imgs[:4]):
                            cols_img[idx].image(img_file, width=65)

        if st.button("💾 Guardar Auditoría", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_txt:
                st.warning("⚠️ Completa todo antes de guardar.")
            else:
                with st.spinner("Guardando..."):
                    nueva_entrada = pd.DataFrame([[
                        str(fecha_audit), auditor_txt, f"AUD-{len(df_historial)+1}", 
                        "", "", "", "", "", "", 
                        str(fotos_data), 
                        str(list(resp_actuales.values())), 
                        score_vivo
                    ]], columns=df_base.columns)
                    
                    df_actualizado = pd.concat([df_base, nueva_entrada], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_actualizado)
                    st.cache_data.clear()
                    st.success("✅ Guardado.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
