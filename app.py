import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal de Auditoría Autociel", layout="wide", page_icon="🚗")

# URLs de las hojas
URL_GESTION = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"
URL_CCS = "https://docs.google.com/spreadsheets/d/1l_f2DudAEmL3lxLdwQttk0WT5fqmRueK7dootnFL6Ak/edit#gid=652621674"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SELECTOR INICIAL ---
if 'proceso_seleccionado' not in st.session_state:
    st.title("🚀 Bienvenido al Portal de Calidad Autociel")
    st.subheader("Seleccione el proceso de auditoría:")
    
    col_a, col_b = st.columns(2)
    with col_a:
        # Se eliminó 'height' para evitar el TypeError
        if st.button("📊 GESTIÓN (Gerente Post Venta)", use_container_width=True):
            st.session_state.proceso_seleccionado = "GESTION"
            st.session_state.url_actual = URL_GESTION
            st.rerun()
    with col_b:
        if st.button("🛠️ CCS (Sector Servicio)", use_container_width=True):
            st.session_state.proceso_seleccionado = "CCS"
            st.session_state.url_actual = URL_CCS
            st.rerun()
    st.stop()

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_todo(url, proceso):
    df = conn.read(spreadsheet=url, ttl=0)
    # Estructura: Col F(5)=Pregunta, Col G(6)=Descripción, Col L(11)=Score
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_desc = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preg = list(mapa_desc.keys())
    
    df_hist = df.copy()
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
    historial.iloc[:, 0] = pd.to_datetime(historial.iloc[:, 0], errors='coerce')
    return df, lista_preg, mapa_desc, historial

try:
    df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(
        st.session_state.url_actual, 
        st.session_state.proceso_seleccionado
    )

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.title(f"📊 Dashboard: {st.session_state.proceso_seleccionado}")
        
        if st.sidebar.button("🔄 Cambiar de Proceso"):
            del st.session_state.proceso_seleccionado
            st.rerun()

        meta, total = 90, len(df_historial)
        promedio = df_historial.iloc[:, 11].mean() if total > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumplimiento Promedio", f"{int(promedio)}%", f"{int(promedio-meta)}% vs Meta")
        m2.metric("Total Auditorías", total)
        m3.metric("Estatus", "✅ Óptimo" if promedio >= meta else "⚠️ Mejora")

        if total > 0:
            st.markdown("### 📅 Tendencia Mensual")
            df_m = df_historial.copy()
            df_m['Mes'] = df_m.iloc[:, 0].dt.strftime('%Y-%m')
            res_m = df_m.groupby('Mes')[df_m.columns[11]].mean().reset_index()
            fig = go.Figure(go.Scatter(x=res_m['Mes'], y=res_m.iloc[:, 1], mode='lines+markers+text',
                                     text=res_m.iloc[:, 1].astype(int).astype(str) + "%", textposition="top center"))
            fig.update_layout(yaxis=dict(range=[0, 110]), height=300, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        if st.button(f"🚀 Iniciar Auditoría {st.session_state.proceso_seleccionado}", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: FORMULARIO ---
    else:
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        
        st.title(f"📝 Auditoría: {st.session_state.proceso_seleccionado}")
        c_p, c_s, c_x = st.columns([2, 1, 1])
        c_p.progress(contestadas / len(lista_preguntas) if lista_preguntas else 0)
        with c_s:
            if score_vivo >= 90: st.success(f"🟢 Score: {int(score_vivo)}%")
            else: st.warning(f"🟡 Score: {int(score_vivo)}%")
        if c_x.button("⬅️ Salir"):
            st.session_state.auditoria_activa = False
            st.rerun()

        with st.container(border=True):
            if st.session_state.proceso_seleccionado == "CCS":
                f1, f2, f3 = st.columns(3)
                fecha_a = f1.date_input("Fecha", datetime.now())
                auditor_n = f2.text_input("Nombre del Auditor")
                asesor_n = f3.selectbox("Asesor Auditado", ["Haydeé", "Antonio"])
            else:
                f1, f2 = st.columns(2)
                fecha_a = f1.date_input("Fecha", datetime.now())
                auditor_n = f2.text_input("Nombre del Auditor")

        datos_adicionales = {}
        for i, preg in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {preg}", expanded=resp_actuales[i] in ["Pendiente", "No Cumple"]):
                # CORREGIDO: Se cerraron correctamente las comillas y paréntesis
                with st.popover("📖 Guía de Auditoría"):
                    st.info(mapa_descripciones.get(preg, "Sin descripción disponible."))
                
                c_r, c_f, c_o = st.columns([1, 1, 1])
                res = c_r.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                archivos = c_f.file_uploader(f"Fotos (Máx 6)", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"f_{i}")
                obs = c_o.text_area("Observaciones / Relato:", key=f"obs_{i}", height=100)
                
                if archivos or obs:
                    datos_adicionales[i] = {'fotos': [f.name for f in archivos[:6]] if archivos else [], 'obs': obs}
                
                if archivos:
                    m_cols = st.columns(6)
                    for idx, img in enumerate(archivos[:6]):
                        m_cols[idx].image(img, width=50)

        if st.button("💾 Finalizar y Guardar", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_n:
                st.warning("⚠️ Checklist incompleto o falta el nombre del auditor.")
            else:
                with st.spinner("Guardando en Google Sheets..."):
                    nueva_fila = pd.DataFrame([[str(fecha_a), auditor_n, f"AUD-{len(df_historial)+1}", "", "", "", "", "", "", str(datos_adicionales), str(list(resp_actuales.values())), score_vivo]], columns=df_base.columns)
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=st.session_state.url_actual, data=df_final)
                    st.cache_data.clear()
                    st.success("✅ ¡Auditoría guardada con éxito!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()
except Exception as e:
    st.error(f"Error en la aplicación: {e}")
