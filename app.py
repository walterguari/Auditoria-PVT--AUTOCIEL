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
    # Lectura inicial
    df = conn.read(spreadsheet=url, ttl=0)
    
    # 1. Mapa de Preguntas y Descripciones (Col F y Col G)
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    
    # 2. Limpieza del Historial para el Dashboard (Col L / Índice 11)
    df_hist = df.copy()
    
    # Aseguramos tipos de datos correctos desde el inicio
    df_hist.iloc[:, 0] = pd.to_datetime(df_hist.iloc[:, 0], errors='coerce')
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    
    # Filtramos filas sin fecha o sin score para evitar errores en gráficos
    historial = df_hist.dropna(subset=[df_hist.columns[0], df_hist.columns[11]]).reset_index(drop=True)
    
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

        # Métricas principales
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
            # Convertimos a string de mes para agrupar visualmente
            df_m['Mes'] = df_m.iloc[:, 0].dt.strftime('%Y-%m')
            
            # Agrupación asegurando que el resultado sea un DataFrame limpio
            resumen_m = df_m.groupby('Mes')[df_m.columns[11]].mean().reset_index()
            
            fig_m = go.Figure()
            # Forzamos x a string para evitar que Plotly intente interpretarlo como date puro
            fig_m.add_trace(go.Scatter(
                x=resumen_m['Mes'].astype(str), 
                y=resumen_m.iloc[:, 1], 
                mode='lines+markers+text',
                text=resumen_m.iloc[:, 1].round(1).astype(str) + "%", 
                textposition="top center",
                line=dict(color='#1E88E5', width=4)
            ))
            
            fig_m.add_shape(type="line", x0=-0.5, x1=len(resumen_m)-0.5, y0=meta, y1=meta, 
                            line=dict(color="Red", dash="dash"))
            
            fig_m.update_layout(
                yaxis=dict(range=[0, 110], title="Cumplimiento %"),
                xaxis=dict(title="Período Mensual"),
                template="plotly_white", 
                height=350,
                margin=dict(l=20, r=20, t=20, b=20)
            )
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
            fecha_a = f1.date_input("Fecha de Auditoría", datetime.now())
            auditor_n = f2.text_input("Nombre del Auditor", placeholder="Ej: Juan Pérez")

        st.markdown("---")
        
        datos_adicionales = {} 

        for i, pregunta in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {pregunta}", expanded=resp_actuales[i]=="Pendiente"):
                detalle = mapa_descripciones.get(pregunta, "Sin descripción técnica disponible.")
                with st.popover("📖 Guía técnica"):
                    st.info(detalle)
                
                col_r, col_f, col_obs = st.columns([1, 1, 1])
                
                with col_r:
                    st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                with col_f:
                    archivos = st.file_uploader(f"Evidencia (Máx 6)", type=['jpg','jpeg','png'], accept_multiple_files=True, key=f"f_{i}")
                
                with col_obs:
                    observacion = st.text_area("Notas / Hallazgos:", key=f"obs_{i}", placeholder="Describa lo observado...")
                
                if archivos or observacion:
                    datos_adicionales[i] = {
                        'fotos': [f.name for f in archivos[:6]] if archivos else [],
                        'comentario': observacion
                    }
                
                if archivos:
                    m_cols = st.columns(6)
                    for idx, img in enumerate(archivos[:6]):
                        m_cols[idx].image(img, width=60)

        if st.button("💾 Finalizar y Guardar Auditoría", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_n:
                st.warning("⚠️ El checklist no está completo o falta el nombre del auditor.")
            else:
                with st.spinner("Sincronizando con Google Sheets..."):
                    # Formateamos la fecha a string para evitar conflictos de tipo al guardar
                    fecha_str = fecha_a.strftime('%Y-%m-%d')
                    
                    nueva_fila = pd.DataFrame([[
                        fecha_str, 
                        auditor_n, 
                        f"AUD-{len(df_historial)+1}", 
                        "", "", "", "", "", "", 
                        str(datos_adicionales), 
                        str(list(resp_actuales.values())), 
                        score_vivo 
                    ]], columns=df_base.columns)
                    
                    df_final = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_final)
                    
                    # Limpiamos caché para que el dashboard se actualice al instante
                    st.cache_data.clear()
                    st.success("✅ Auditoría guardada correctamente.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Hubo un problema al procesar los datos: {e}")
