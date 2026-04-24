import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import ast 

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
    # Convertir fechas a formato datetime para filtros
    historial.iloc[:, 0] = pd.to_datetime(historial.iloc[:, 0], errors='coerce')
    return df, preguntas, historial

try:
    df_base, lista_preguntas, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- PANTALLA 1: DASHBOARD PRO ---
    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Gestión de Calidad")
        
        with st.expander("🔍 Filtros de Búsqueda"):
            f_col1, f_col2 = st.columns(2)
            auditor_filtro = f_col1.multiselect("Filtrar por Auditor", options=df_historial.iloc[:, 1].unique())
            
            df_filtrado = df_historial.copy()
            if auditor_filtro:
                df_filtrado = df_filtrado[df_filtrado.iloc[:, 1].isin(auditor_filtro)]

        objetivo = 90
        total = len(df_filtrado)
        promedio = df_filtrado.iloc[:, 11].mean() if total > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(promedio)}%", f"{int(promedio-objetivo)}% vs Meta")
        m2.metric("Total Auditorías", total)
        m3.metric("Estatus General", "✅ Óptimo" if promedio >= 90 else "⚠️ En Mejora")

        st.markdown("### 📈 Evolución de Desempeño")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_filtrado.iloc[:, 0].dt.strftime('%d/%m/%Y') if total > 0 else [],
            y=df_filtrado.iloc[:, 11],
            marker_color=['#28A745' if x >= objetivo else '#FF4B4B' for x in df_filtrado.iloc[:, 11]],
            text=df_filtrado.iloc[:, 11].astype(int).astype(str) + "%",
            textposition='outside'
        ))
        fig.add_shape(type="line", x0=-0.5, x1=total-0.5, y0=objetivo, y1=objetivo, line=dict(color="Black", dash="dash"))
        fig.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST CON SEMÁFORO Y FOTO ---
    else:
        respuestas = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        avance = (respondidas / len(lista_preguntas)) * 100

        st.title("📝 Nueva Auditoría")
        s1, s2, s3 = st.columns([2,1,1])
        with s1:
            st.markdown(f"**Progreso:** {int(avance)}%")
            st.progress(avance / 100)
        with s2:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            elif score_vivo >= 75: st.warning(f"🟡 Score: {int(score_vivo)}%")
            else: st.error(f"🔴 Score: {int(score_vivo)}%")
        with s3:
            if st.button("⬅️ Salir"):
                st.session_state.auditoria_activa = False
                st.rerun()

        # Cuerpo del Checklist con CARGA DE FOTO
        with st.container(border=True):
            f1, f2, f3 = st.columns([1, 1, 2])
            fecha = f1.date_input("Fecha", datetime.now())
            auditor = f2.text_input("Nombre del Auditor")
            
            # --- MEJORA: CARGA DE FOTO ---
            foto_evidencia = f3.file_uploader("📸 Adjuntar Evidencia (Foto)", type=['png', 'jpg', 'jpeg'])
            if foto_evidencia:
                st.image(foto_evidencia, caption="Vista previa", width=150)

        for i, preg in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {preg}", expanded=respuestas[i]=="Pendiente"):
                st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True, label_visibility="collapsed")

        if st.button("💾 Finalizar y Guardar", use_container_width=True, type="primary"):
            if avance < 100 or not auditor:
                st.warning("⚠️ Completa todos los campos y el nombre del auditor.")
            else:
                with st.spinner("Guardando registro y evidencia..."):
                    # Nombre para la Columna J
                    nombre_archivo = f"EVID-{datetime.now().strftime('%H%M%S')}.jpg" if foto_evidencia else "Sin Foto"
                    
                    # Estructura A-L (Columna J es el índice 9)
                    nueva_fila = pd.DataFrame([[
                        str(fecha), auditor, f"AUD-{total+1}", 
                        "", "", "", "", "", "", 
                        nombre_archivo,                 # J: Evidencia
                        str(list(respuestas.values())), # K: Detalle
                        score_vivo                      # L: Score
                    ]], columns=df_base.columns)
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Guardado con éxito.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
