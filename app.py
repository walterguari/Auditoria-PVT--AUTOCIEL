import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Auditoría Autociel Pro", layout="wide", page_icon="🚗")
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_todo(url):
    df = conn.read(spreadsheet=url, ttl=0)
    preguntas = df.iloc[:, 5].dropna().unique().tolist()
    df_hist = df.copy()
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
    return df, preguntas, historial

try:
    df_base, lista_preguntas, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Gestión de Calidad")
        # ... (Tu código de dashboard actual aquí)
        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    else:
        # Lógica de Score
        respuestas = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        avance = (respondidas / len(lista_preguntas)) * 100

        # Semáforo
        st.title("📝 Nueva Auditoría Detallada")
        s1, s2, s3 = st.columns([2,1,1])
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
        
        # Diccionario para guardar referencias de fotos
        fotos_por_pregunta = {}

        for i, preg in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {preg}", expanded=respuestas[i]=="Pendiente"):
                col_radio, col_foto = st.columns([2, 2])
                
                with col_radio:
                    res = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                # MEJORA: SUBIR HASTA 4 FOTOS POR PREGUNTA
                with col_foto:
                    archivos = st.file_uploader(f"Evidencia P{i+1} (Máx 4)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key=f"foto_{i}")
                    if archivos:
                        if len(archivos) > 4:
                            st.warning("Solo se guardarán las primeras 4 fotos.")
                        fotos_por_pregunta[i] = [f.name for f in archivos[:4]]
                        # Miniaturas
                        cols_mini = st.columns(4)
                        for idx, f in enumerate(archivos[:4]):
                            cols_mini[idx].image(f, width=60)

        if st.button("💾 Finalizar y Guardar Auditoría", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.warning("⚠️ Checklist incompleto.")
            else:
                with st.spinner("Procesando historial y fotos..."):
                    # Consolidamos nombres de fotos para la Columna J
                    registro_fotos = str(fotos_por_pregunta)
                    
                    nueva_fila = pd.DataFrame([[
                        str(fecha), auditor, f"AUD-{len(df_historial)+1}", 
                        "", "", "", "", "", "", 
                        registro_fotos,                 # J: Registro de todas las fotos
                        str(list(respuestas.values())), # K: Detalle respuestas
                        score_vivo                      # L: Score
                    ]], columns=df_base.columns)
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    
                    st.cache_data.clear()
                    st.success("✅ Auditoría guardada con éxito.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
