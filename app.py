import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal de Calidad Autociel", layout="wide", page_icon="🚗")

# --- URLs DE BASES DE DATOS ---
URLS = {
    "GESTION": "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871",
    "CCS": "https://docs.google.com/spreadsheets/d/1l_f2DudAEmL3lxLdwQttk0WT5fqmRueK7dootnFL6Ak/edit#gid=652621674",
    "CITAS": "https://docs.google.com/spreadsheets/d/1XwagKHRWZLrado40tNN4UjLkSn9vKqJlnD4JF1vaTkk/edit#gid=230929161",
    "ENTREGA": "https://docs.google.com/spreadsheets/d/1HcNxmodD4QbzpNYSBkzmRWyb5NlUbhvBinpxVCMCokI/edit#gid=1499782964",
    "TALLER": "https://docs.google.com/spreadsheets/d/1kMcjTQrHdWgI7IRMzj8IYj9hIziTemYAObb_9txAMwU/edit#gid=292311251",
    "REPUESTOS": "https://docs.google.com/spreadsheets/d/1iOx9dq2kZs-cYBxKt3lK9rOc27Yq6xa4bl4mTISiRcQ/edit#gid=1105513965",
    "PLAN_ACCION": "https://docs.google.com/spreadsheets/d/1cX9vMCBPCpXDt-uWZC5iNqRdtV8pfJOErSFcaSaFnvE/edit#gid=0"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=10)
def cargar_todo(url):
    try:
        df = conn.read(spreadsheet=url, ttl=0)
        # Para auditorías: F(5)=Pregunta, G(6)=Desc, L(11)=Score
        if "edit" in url and "1cX9v" not in url:
            df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
            mapa_desc = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
            lista_preg = list(mapa_desc.keys())
            df_hist = df.copy()
            df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
            historial = df_hist[df_hist.iloc[:, 11].notnull()].reset_index(drop=True)
            historial.iloc[:, 0] = pd.to_datetime(historial.iloc[:, 0], errors='coerce')
            return df, lista_preg, mapa_desc, historial
        return df, [], {}, pd.DataFrame()
    except:
        return pd.DataFrame(), [], {}, pd.DataFrame()

# --- SELECTOR INICIAL ---
if 'proceso_seleccionado' not in st.session_state:
    st.title("🚀 Bienvenido al Portal de Calidad Autociel")
    st.subheader("Seleccione una opción:")
    
    st.write("### 📝 Realizar Auditorías")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    
    opciones = [
        (c1, "GESTION", "📊 GESTIÓN"), (c2, "CCS", "🛠️ CCS"), (c3, "CITAS", "📅 CITAS"),
        (c4, "ENTREGA", "📦 ENTREGA 0KM"), (c5, "TALLER", "🔧 TALLER"), (c6, "REPUESTOS", "⚙️ REPUESTOS")
    ]
    for col, key, label in opciones:
        if col.button(label, use_container_width=True):
            st.session_state.proceso_seleccionado = key
            st.session_state.url_actual = URLS[key]
            st.session_state.modo = "AUDITORIA"
            st.rerun()

    st.markdown("---")
    st.write("### 🛠️ Mejora Continua")
    if st.button("📝 REGISTRAR Y SEGUIR PLAN DE ACCIÓN", use_container_width=True, type="secondary"):
        st.session_state.proceso_seleccionado = "PLAN_ACCION"
        st.session_state.url_actual = URLS["PLAN_ACCION"]
        st.session_state.modo = "PLAN"
        st.rerun()
    st.stop()

# --- EJECUCIÓN SEGÚN MODO ---
if st.session_state.modo == "PLAN":
    st.title("📝 Gestión de Planes de Acción")
    if st.sidebar.button("🏠 Inicio"):
        del st.session_state.proceso_seleccionado
        st.rerun()

    with st.expander("➕ Registrar Nuevo Desvío", expanded=True):
        with st.form("form_plan", clear_on_submit=True):
            c1, c2 = st.columns(2)
            sec = c1.selectbox("Sector", ["GESTIÓN", "CCS", "CITAS", "ENTREGA 0KM", "TALLER", "REPUESTOS", "OTROS"])
            prob = c2.text_input("Problema / Desvío")
            causa = st.text_area("Causa Raíz")
            acc = st.text_area("Acción a realizar")
            c3, c4, c5 = st.columns(3)
            resp = c3.text_input("Responsable")
            obj = c4.text_input("Objetivo")
            ctrl = c5.text_input("Modo de Control")
            c6, c7, c8 = st.columns(3)
            fi = c6.date_input("Inicio Est.")
            fr = c7.date_input("Inicio Real")
            ff = c8.date_input("Fecha Final")
            c9, c10 = st.columns([1, 2])
            av = c9.select_slider("Avance", options=["0%", "25%", "50%", "75%", "100%"])
            obs = c10.text_input("Obs. Avance")
            if st.form_submit_button("💾 Guardar"):
                df_p = cargar_todo(st.session_state.url_actual)[0]
                nueva = pd.DataFrame([[sec, prob, causa, acc, resp, obj, ctrl, str(fi), str(fr), str(ff), av, obs]], columns=df_p.columns[:12])
                conn.update(spreadsheet=st.session_state.url_actual, data=pd.concat([df_p, nueva], ignore_index=True))
                st.success("✅ Registrado")
                st.cache_data.clear()
                st.rerun()

    st.write("### 📋 Desvíos por Sector")
    df_v = cargar_todo(st.session_state.url_actual)[0]
    if not df_v.empty:
        filtro = st.selectbox("Filtrar por Sector:", ["TODOS"] + sorted(df_v["Sector"].unique().tolist()))
        st.dataframe(df_v if filtro == "TODOS" else df_v[df_v["Sector"] == filtro], use_container_width=True, hide_index=True)

else:
    # --- MODO AUDITORÍA COMPLETO ---
    df_base, lista_preguntas, mapa_desc, df_hist = cargar_todo(st.session_state.url_actual)
    
    if 'auditoria_activa' not in st.session_state: st.session_state.auditoria_activa = False

    if not st.session_state.auditoria_activa:
        st.title(f"📊 Dashboard: {st.session_state.proceso_seleccionado}")
        if st.sidebar.button("🏠 Inicio"):
            del st.session_state.proceso_seleccionado
            st.rerun()

        m1, m2, m3 = st.columns(3)
        promedio = df_hist.iloc[:, 11].mean() if not df_hist.empty else 0
        m1.metric("Promedio", f"{int(promedio)}%", f"{int(promedio-90)}% vs Meta")
        m2.metric("Total", len(df_hist))
        m3.metric("Estatus", "✅ Óptimo" if promedio >= 90 else "⚠️ Mejora")

        if not df_hist.empty:
            df_hist['Mes'] = df_hist.iloc[:, 0].dt.strftime('%Y-%m')
            res = df_hist.groupby('Mes')[df_hist.columns[11]].mean().reset_index()
            fig = go.Figure(go.Scatter(x=res['Mes'], y=res.iloc[:, 1], mode='lines+markers+text', text=res.iloc[:, 1].astype(int).astype(str) + "%", textposition="top center"))
            fig.update_layout(yaxis=dict(range=[0, 110]), height=300, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 Iniciar Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    else:
        # --- FORMULARIO REAL ---
        resp_act = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        score = (sum(1 for v in resp_act.values() if v == "Cumple") / sum(1 for v in resp_act.values() if v in ["Cumple", "No Cumple"]) * 100) if any(v in ["Cumple", "No Cumple"] for v in resp_act.values()) else 0
        
        st.title(f"📝 Auditoría: {st.session_state.proceso_seleccionado}")
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.progress(sum(1 for v in resp_act.values() if v != "Pendiente") / len(lista_preguntas) if lista_preguntas else 0)
        c2.metric("Score Actual", f"{int(score)}%")
        if c3.button("⬅️ Salir"):
            st.session_state.auditoria_activa = False
            st.rerun()

        with st.container(border=True):
            f1, f2, f3 = st.columns(3)
            fecha = f1.date_input("Fecha", datetime.now())
            auditor = f2.text_input("Auditor")
            persona = f3.text_input("Auditado", placeholder="Nombre...")

        datos_extra = {}
        for i, preg in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {preg}", expanded=resp_act[i] in ["Pendiente", "No Cumple"]):
                with st.popover("📖 Guía"): st.info(mapa_desc.get(preg, "Sin desc."))
                r1, r2, r3 = st.columns([1, 1, 1])
                res = r1.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                fotos = r2.file_uploader(f"Fotos", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"f_{i}")
                obs = r3.text_area("Obs:", key=f"obs_{i}")
                if fotos or obs: datos_extra[i] = {'fotos': [f.name for f in fotos[:6]] if fotos else [], 'obs': obs}

        if st.button("💾 Guardar Auditoría", use_container_width=True, type="primary"):
            if sum(1 for v in resp_act.values() if v != "Pendiente") < len(lista_preguntas) or not auditor:
                st.warning("⚠️ Incompleto")
            else:
                nueva = pd.DataFrame([[str(fecha), auditor, f"AUD-{len(df_hist)+1}", persona, "", "", "", "", "", str(datos_extra), str(list(resp_act.values())), score]], columns=df_base.columns)
                conn.update(spreadsheet=st.session_state.url_actual, data=pd.concat([df_base, nueva], ignore_index=True))
                st.cache_data.clear()
                st.success("✅ Guardado")
                st.session_state.auditoria_activa = False
                st.rerun()
