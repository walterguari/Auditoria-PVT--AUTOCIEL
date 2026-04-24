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
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    df_hist = df.copy()
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
    historial.iloc[:, 0] = pd.to_datetime(historial.iloc[:, 0], errors='coerce')
    return df, lista_preguntas, mapa_descripciones, historial

try:
    df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Gestión Autociel")
        with st.expander("🔍 Filtros de Búsqueda"):
            f_col1, f_col2 = st.columns(2)
            audit_unicos = df_historial.iloc[:, 1].unique()
            sel_auditor = f_col1.multiselect("Filtrar por Auditor", options=audit_unicos)
            df_display = df_historial.copy()
            if sel_auditor:
                df_display = df_display[df_display.iloc[:, 1].isin(sel_auditor)]

        meta, total_audits = 90, len(df_display)
        promedio = df_display.iloc[:, 11].mean() if total_audits > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(promedio)}%", f"{int(promedio-meta)}% vs Meta")
        m2.metric("Total Auditorías", total_audits)
        m3.metric("Estatus", "✅ Óptimo" if promedio >= meta else "⚠️ Mejora")

        if total_audits > 0:
            df_m = df_display.copy()
            df_m['Mes'] = df_m.iloc[:, 0].dt.strftime('%Y-%m')
            res_m = df_m.groupby('Mes')[df_m.columns[11]].mean().reset_index()
            fig = go.Figure(go.Scatter(x=res_m['Mes'], y=res_m.iloc[:, 1], mode='lines+markers+text',
                                     text=res_m.iloc[:, 1].astype(int).astype(str) + "%", textposition="top center"))
            fig.update_layout(yaxis=dict(range=[0, 110]), height=300, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- FORMULARIO OPTIMIZADO ---
    else:
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        
        st.title("📝 Auditoría Autociel Pro")
        c_p, c_s, c_x = st.columns([2, 1, 1])
        c_p.progress(contestadas / len(lista_preguntas))
        with c_s:
            if score_vivo >= 90: st.success(f"🟢 {int(score_vivo)}%")
            else: st.warning(f"🟡 {int(score_vivo)}%")
        if c_x.button("⬅️ Salir"):
            st.session_state.auditoria_activa = False
            st.rerun()

        with st.container(border=True):
            f1, f2 = st.columns(2)
            fecha_a = f1.date_input("Fecha", datetime.now())
            auditor_n = f2.text_input("Nombre del Auditor")

        datos_adicionales = {}
        for i, pregunta in enumerate(lista_preguntas):
            # Optimización: El expander solo se abre si está pendiente o no cumple
            is_expanded = resp_actuales[i] in ["Pendiente", "No Cumple"]
            with st.expander(f"{i+1}. {pregunta}", expanded=is_expanded):
                with st.popover("📖 Guía"):
                    st.info(mapa_descripciones.get(pregunta, "Sin descripción."))
                
                c_r, c_f, c_o = st.columns([1, 1, 1])
                res = c_r.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                archivos = c_f.file_uploader(f"Fotos (Máx 6)", type=['jpg','png'], accept_multiple_files=True, key=f"f_{i}")
                obs = c_o.text_area("Observaciones:", key=f"obs_{i}", height=100)
                
                if archivos or obs:
                    datos_adicionales[i] = {'fotos': [f.name for f in archivos[:6]] if archivos else [], 'obs': obs}
                
                if archivos:
                    # Miniaturas más pequeñas para ahorrar memoria
                    m_cols = st.columns(6)
                    for idx, img in enumerate(archivos[:6]):
                        m_cols[idx].image(img, width=50)

        if st.button("💾 Finalizar y Guardar", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_n:
                st.warning("⚠️ Checklist incompleto.")
            else:
                with st.spinner("Guardando..."):
                    nueva_fila = pd.DataFrame([[str(fecha_a), auditor_n, f"AUD-{len(df_historial)+1}", "", "", "", "", "", "", str(datos_adicionales), str(list(resp_actuales.values())), score_vivo]], columns=df_base.columns)
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ Guardado.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()
except Exception as e:
    st.error(f"Error: {e}")
