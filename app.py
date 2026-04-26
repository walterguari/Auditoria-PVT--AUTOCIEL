import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal de Auditoría Autociel", layout="wide", page_icon="🚗")

# --- URLs DE BASES DE DATOS ---
URL_GESTION = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"
URL_CCS = "https://docs.google.com/spreadsheets/d/1l_f2DudAEmL3lxLdwQttk0WT5fqmRueK7dootnFL6Ak/edit#gid=652621674"
URL_CITAS = "https://docs.google.com/spreadsheets/d/1XwagKHRWZLrado40tNN4UjLkSn9vKqJlnD4JF1vaTkk/edit#gid=230929161"
URL_ENTREGA = "https://docs.google.com/spreadsheets/d/1HcNxmodD4QbzpNYSBkzmRWyb5NlUbhvBinpxVCMCokI/edit#gid=1499782964"
URL_TALLER = "https://docs.google.com/spreadsheets/d/1kMcjTQrHdWgI7IRMzj8IYj9hIziTemYAObb_9txAMwU/edit#gid=292311251"
URL_REPUESTOS = "https://docs.google.com/spreadsheets/d/1iOx9dq2kZs-cYBxKt3lK9rOc27Yq6xa4bl4mTISiRcQ/edit#gid=1105513965"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SELECTOR INICIAL (6 OPCIONES) ---
if 'proceso_seleccionado' not in st.session_state:
    st.title("🚀 Bienvenido al Portal de Calidad Autociel")
    st.subheader("Seleccione el proceso de auditoría:")
    
    # Fila 1
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📊 GESTIÓN\n(Gerente Post Venta)", use_container_width=True):
            st.session_state.proceso_seleccionado = "GESTION"
            st.session_state.url_actual = URL_GESTION
            st.rerun()
    with c2:
        if st.button("🛠️ CCS\n(Sector Servicio)", use_container_width=True):
            st.session_state.proceso_seleccionado = "CCS"
            st.session_state.url_actual = URL_CCS
            st.rerun()
    with c3:
        if st.button("📅 CITAS\n(Agendamiento)", use_container_width=True):
            st.session_state.proceso_seleccionado = "CITAS"
            st.session_state.url_actual = URL_CITAS
            st.rerun()
            
    # Fila 2
    c4, c5, c6 = st.columns(3)
    with c4:
        if st.button("📦 ENTREGA 0KM\n(Recepción y Prep.)", use_container_width=True):
            st.session_state.proceso_seleccionado = "ENTREGA"
            st.session_state.url_actual = URL_ENTREGA
            st.rerun()
    with c5:
        if st.button("🔧 TALLER\n(Procesos Técnicos)", use_container_width=True):
            st.session_state.proceso_seleccionado = "TALLER"
            st.session_state.url_actual = URL_TALLER
            st.rerun()
    with c6:
        if st.button("⚙️ REPUESTOS\n(Mostrador y Almacén)", use_container_width=True):
            st.session_state.proceso_seleccionado = "REPUESTOS"
            st.session_state.url_actual = URL_REPUESTOS
            st.rerun()
            
    st.stop()

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_todo(url):
    try:
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
    except:
        return None, [], {}, pd.DataFrame()

df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(st.session_state.url_actual)

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
        f1, f2, f3 = st.columns(3)
        fecha_a = f1.date_input("Fecha", datetime.now())
        auditor_n = f2.text_input("Nombre del Auditor")
        
        persona_final = ""
        if st.session_state.proceso_seleccionado in ["CCS", "CITAS", "ENTREGA", "TALLER", "REPUESTOS"]:
            label_map = {
                "CCS": "Asesor Auditado",
                "CITAS": "Operador Auditado",
                "ENTREGA": "Responsable Entrega",
                "TALLER": "Responsable Taller",
                "REPUESTOS": "Responsable de Repuestos"
            }
            persona_final = f3.text_input(label_map[st.session_state.proceso_seleccionado], placeholder="Escriba el nombre completo...")
        else:
            f3.empty()

    datos_adicionales = {}
    for i, preg in enumerate(lista_preguntas):
        with st.expander(f"{i+1}. {preg}", expanded=resp_actuales[i] in ["Pendiente", "No Cumple"]):
            with st.popover("📖 Guía de Auditoría"):
                st.info(mapa_descripciones.get(preg, "Sin descripción disponible."))
            
            c_r, c_f, c_o = st.columns([1, 1, 1])
            res = c_r.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
            archivos = c_f.file_uploader(f"Fotos (Máx 6)", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"f_{i}")
            obs = c_o.text_area("Observaciones:", key=f"obs_{i}", height=100)
            
            if archivos or obs:
                datos_adicionales[i] = {'fotos': [f.name for f in archivos[:6]] if archivos else [], 'obs': obs}
            if archivos:
                m_cols = st.columns(6)
                for idx, img in enumerate(archivos[:6]):
                    m_cols[idx].image(img, width=50)

    if st.button("💾 Finalizar y Guardar Auditoría", use_container_width=True, type="primary"):
        if contestadas < len(lista_preguntas) or not auditor_n or (st.session_state.proceso_seleccionado != "GESTION" and not persona_final):
            st.warning("⚠️ Checklist incompleto o falta identificar al auditado.")
        else:
            with st.spinner("Guardando en la nube..."):
                nueva_fila = pd.DataFrame([[
                    str(fecha_a), 
                    auditor_n, 
                    f"AUD-{len(df_historial)+1}", 
                    persona_final, 
                    "", "", "", "", "", 
                    str(datos_adicionales), 
                    str(list(resp_actuales.values())), 
                    score_vivo
                ]], columns=df_base.columns)
                
                df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=st.session_state.url_actual, data=df_final)
                st.cache_data.clear()
                st.success(f"✅ Auditoría de {st.session_state.proceso_seleccionado} guardada.")
                st.balloons()
                st.session_state.auditoria_activa = False
                st.rerun()
