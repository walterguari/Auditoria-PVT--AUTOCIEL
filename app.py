import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import ast  # Para procesar las listas guardadas como texto

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría Autociel Pro", layout="wide", page_icon="🚗")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_todo(url):
    # Lectura de la base
    df = conn.read(spreadsheet=url, ttl=0)
    
    # 1. Mapa de Preguntas (Col F) y Descripciones (Col G)
    # Filtramos nulos en la columna de preguntas (índice 5)
    df_preg = df.iloc[:, [5, 6]].dropna(subset=[df.columns[5]])
    mapa_descripciones = dict(zip(df_preg.iloc[:, 0], df_preg.iloc[:, 1]))
    lista_preguntas = list(mapa_descripciones.keys())
    
    # 2. Preparación de Historial (Col A: Fecha, Col L: Score)
    df_hist = df.copy()
    df_hist.iloc[:, 0] = pd.to_datetime(df_hist.iloc[:, 0], errors='coerce')
    df_hist.iloc[:, 11] = pd.to_numeric(df_hist.iloc[:, 11], errors='coerce')
    
    # Limpiamos filas vacías en las columnas críticas para el dashboard
    historial = df_hist.dropna(subset=[df_hist.columns[0], df_hist.columns[11]]).reset_index(drop=True)
    
    return df, lista_preguntas, mapa_descripciones, historial

try:
    df_base, lista_preguntas, mapa_descripciones, df_historial = cargar_todo(url)

    if 'auditoria_activa' not in st.session_state:
        st.session_state.auditoria_activa = False

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.title("📊 Dashboard de Calidad Autociel")
        
        with st.expander("🔍 Filtros y Búsqueda"):
            f_col1, f_col2 = st.columns(2)
            auditores_unicos = sorted(df_historial.iloc[:, 1].unique().astype(str))
            sel_auditor = f_col1.multiselect("Filtrar por Auditor", options=auditores_unicos)
            
            df_display = df_historial.copy()
            if sel_auditor:
                df_display = df_display[df_display.iloc[:, 1].isin(sel_auditor)]

        # --- MÉTRICAS ---
        meta = 90
        total_audits = len(df_display)
        promedio_gral = df_display.iloc[:, 11].mean() if total_audits > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        # Mostramos con 1 decimal para mayor precisión
        m1.metric("Cumplimiento Promedio", f"{promedio_gral:.1f}%", f"{promedio_gral - meta:.1f}% vs Meta")
        m2.metric("Total Auditorías", total_audits)
        m3.metric("Estatus Global", "✅ Óptimo" if promedio_gral >= meta else "⚠️ En Mejora")

        # --- GRÁFICO DE TENDENCIA ---
        st.markdown("### 📅 Evolución Mensual")
        if total_audits > 0:
            df_m = df_display.copy()
            df_m['Mes'] = df_m.iloc[:, 0].dt.strftime('%Y-%m')
            resumen_m = df_m.groupby('Mes')[df_m.columns[11]].mean().reset_index()
            
            fig_m = go.Figure()
            fig_m.add_trace(go.Scatter(
                x=resumen_m['Mes'].astype(str), 
                y=resumen_m.iloc[:, 1], 
                mode='lines+markers+text',
                text=resumen_m.iloc[:, 1].round(1).astype(str) + "%", 
                textposition="top center",
                line=dict(color='#004A99', width=3) # Color corporativo sugerido
            ))
            
            # Línea de Meta
            fig_m.add_shape(type="line", x0=-0.5, x1=len(resumen_m)-0.5, y0=meta, y1=meta, 
                            line=dict(color="Red", dash="dash"))
            
            fig_m.update_layout(
                yaxis=dict(range=[0, 110]),
                template="plotly_white", 
                height=350,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig_m, use_container_width=True)

        if st.button("🚀 Nueva Auditoría", use_container_width=True, type="primary"):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: FORMULARIO DE AUDITORÍA ---
    else:
        # Estado de respuestas
        resp_actuales = {i: st.session_state.get(f"p_{i}", "Pendiente") for i in range(len(lista_preguntas))}
        cumplen = sum(1 for v in resp_actuales.values() if v == "Cumple")
        validas = sum(1 for v in resp_actuales.values() if v in ["Cumple", "No Cumple"])
        score_vivo = (cumplen / validas * 100) if validas > 0 else 0
        contestadas = sum(1 for v in resp_actuales.values() if v != "Pendiente")
        progreso = (contestadas / len(lista_preguntas)) if len(lista_preguntas) > 0 else 0

        st.title("📝 Formulario de Auditoría Pro")
        
        c_p, c_s, c_x = st.columns([2, 1, 1])
        with c_p: 
            st.write(f"Progreso: {int(progreso*100)}%")
            st.progress(progreso)
        with c_s:
            if score_vivo >= meta: st.success(f"🟢 Score: {score_vivo:.1f}%")
            else: st.warning(f"🟡 Score: {score_vivo:.1f}%")
        with c_x:
            if st.button("⬅️ Volver"):
                st.session_state.auditoria_activa = False
                st.rerun()

        # Datos de cabecera
        with st.container(border=True):
            col1, col2 = st.columns(2)
            fecha_a = col1.date_input("Fecha", datetime.now())
            auditor_n = col2.text_input("Auditor", placeholder="Nombre completo")

        st.markdown("---")
        
        datos_adicionales = {} 

        # Generación dinámica de preguntas
        for i, pregunta in enumerate(lista_preguntas):
            with st.expander(f"{i+1}. {pregunta}", expanded=(resp_actuales[i]=="Pendiente")):
                desc = mapa_descripciones.get(pregunta, "Sin detalle adicional.")
                
                with st.popover("📖 Ver Criterio Técnico"):
                    st.info(desc)
                
                c1, c2, c3 = st.columns([1.5, 1, 1.5])
                
                with c1:
                    st.radio("Resultado", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{i}", horizontal=True)
                
                with c2:
                    archivos = st.file_uploader("Evidencia", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"f_{i}")
                
                with c3:
                    obs = st.text_area("Observación", key=f"obs_{i}", height=70)
                
                if archivos or obs:
                    datos_adicionales[i] = {
                        'fotos': [f.name for f in archivos[:3]] if archivos else [],
                        'comentario': obs
                    }

        # Guardado final
        if st.button("💾 Finalizar y Guardar en Sheets", use_container_width=True, type="primary"):
            if contestadas < len(lista_preguntas) or not auditor_n:
                st.error("⚠️ Debes completar todas las preguntas y el nombre del auditor.")
            else:
                with st.spinner("Guardando registro..."):
                    # Preparamos la fila (Col K guarda las respuestas como string de lista)
                    nueva_fila = pd.DataFrame([[
                        fecha_a.strftime('%Y-%m-%d'),
                        auditor_n,
                        f"AUD-{len(df_historial)+1}",
                        "", "", "", "", "", "", # Columnas vacías intermedias
                        str(datos_adicionales),
                        str(list(resp_actuales.values())),
                        round(score_vivo, 2)
                    ]], columns=df_base.columns)
                    
                    df_updated = pd.concat([df_base, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_updated)
                    
                    st.cache_data.clear()
                    st.balloons()
                    st.success("Auditoría finalizada con éxito.")
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Se produjo un error: {e}")
