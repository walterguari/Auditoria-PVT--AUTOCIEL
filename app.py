import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría Autociel Pro", layout="wide", page_icon="🚗")

# URL de tu Google Sheet
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

# --- INICIO DE LÓGICA ---
try:
    df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Calidad Autociel")
        
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

        # Gráfico
        if total_audits > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_display.iloc[:, 0].dt.strftime('%d/%m/%Y'),
                y=df_display.iloc[:, 11],
                marker_color=['#28A745' if x >= meta else '#FF4B4B' for x in df_display.iloc[:, 11]],
                text=df_display.iloc[:, 11].astype(int).astype(str) + "%",
                textposition='outside'
            ))
            fig.add_shape(type="line", x0=-0.5, x1=total_audits-0.5, y0=meta, y1=meta, line=dict(color="Black", dash="dash"))
            fig.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: FORMULARIO DE AUDITORÍA ---
    else:
        # Cálculos de Score en Vivo
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        progreso = (contestadas / len(lista_preguntas)) * 100

        # Cabecera y Semáforo
        st.title("📝 Formulario de Auditoría Detallada")
        c_prog, c_semaf, c_salir = st.columns([2, 1, 1])
        with c_prog:
            st.write(f"**Avance:** {int(progreso)}%")
            st.progress(progreso / 100)
        with c_semaf:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            elif score_vivo >= 75: st.warning(f"🟡 Score: {int(score_vivo)}%")
            else: st.error(f"🔴 Score: {int(score_vivo)}%")
        with c_salir:
            if st.button("⬅️ Volver al Dashboard"):
                st.session_state.auditoria_activa = False
                st.rerun()

        # Datos de cabecera
        with st.container(border=True):
            f_col1, f_col2 = st.columns(2)
            fecha_audit = f_col1.date_input("Fecha de Auditoría", datetime.now())
            auditor_txt = f_col2.text_input("Nombre del Auditor")

        st.markdown("---")
        
        # Diccionario para nombres de fotos
        fotos_data = {}

        # Listado de Preguntas
        for i, pregunta in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {pregunta}", expanded=resp_actuales[i]=="Pendiente"):
                
                # BOTÓN DE AYUDA (Descripción de columna G)
                detalle_ayuda = mapa_descripciones.get(pregunta, "Sin descripción en el archivo.")
                with st.popover("📖 Ver detalle de qué auditar"):
                    st.info(f"**Criterio Técnico:**\n\n{detalle_ayuda}")
                
                st.write("") # Espacio
                col_radio, col_foto = st.columns([1, 1])
                
                with col_radio:
                    st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                with col_foto:
                    imgs = st.file_uploader(f"Subir fotos (Máx 4)", type=['jpg','jpeg','png'], accept_multiple_files=True, key=f"f_{i}")
                    if imgs:
                        fotos_data[i] = [img.name for img in imgs[:4]]
                        # Miniaturas para confirmar carga
                        cols_img = st.columns(4)
                        for idx, img_file in enumerate(imgs[:4]):
                            cols_img[idx].image(img_file, width=65)

        # Botón Final
        if st.button("💾 Finalizar y Guardar Auditoría", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_txt:
                st.warning("⚠️ Por favor completa todas las preguntas y el nombre del auditor.")
            else:
                with st.spinner("Registrando datos en Google Sheets..."):
                    # J=Fotos, K=Detalle Respuestas, L=Score
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
                    st.success("✅ Auditoría guardada correctamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Hubo un error al cargar los datos: {e}")
