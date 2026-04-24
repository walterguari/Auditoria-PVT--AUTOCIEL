import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Auditoría Autociel", layout="wide")

# Caché inteligente: lee el excel una vez por minuto para no saturar
@st.cache_data(ttl=60)
def cargar_datos_base(_conn, url):
    try:
        df = _conn.read(spreadsheet=url, ttl=0)
        # Preguntas en Col E (4) y Descripción en Col F (5)
        preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
        return preguntas, df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    preguntas_df, df_historico = cargar_datos_base(conn, url)

    # --- PANTALLA 1: TABLERO DE RESULTADOS ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Tablero de Cumplimiento Mensual")
        
        if not df_historico.empty:
            # LIMPIEZA EXTREMA PARA EVITAR ERRORES
            df_plot = df_historico.copy()
            
            # 1. Aseguramos que la columna A sea tratada como fecha (errores se vuelven Nulo)
            df_plot.iloc[:, 0] = pd.to_datetime(df_plot.iloc[:, 0], errors='coerce')
            
            # 2. Filtramos: Solo filas que tengan fecha válida Y resultado "Cumple" o "No Cumple"
            df_plot = df_plot.dropna(subset=[df_plot.columns[0]])
            df_plot = df_plot[df_plot.iloc[:, 6].isin(["Cumple", "No Cumple"])]

            if not df_plot.empty:
                # Formateamos mes para agrupar
                df_plot['Mes'] = df_plot.iloc[:, 0].dt.strftime('%Y-%m')
                
                # Agrupamos y calculamos el promedio
                resumen = df_plot.groupby('Mes').apply(
                    lambda x: round((x.iloc[:, 6] == "Cumple").sum() / len(x) * 100, 1)
                ).reset_index(name='Cumplimiento')

                # Gráfico Profesional con Plotly
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=resumen['Mes'], y=resumen['Cumplimiento'],
                    name='Real', marker_color='#007bff',
                    text=resumen['Cumplimiento'].astype(str) + '%', textposition='auto'
                ))
                # Línea roja de Objetivo 90%
                fig.add_trace(go.Scatter(
                    x=resumen['Mes'], y=[90]*len(resumen),
                    mode='lines', name='Objetivo 90%',
                    line=dict(color='red', width=3, dash='dash')
                ))
                fig.update_layout(yaxis=dict(range=[0, 110]), template='plotly_white', height=450)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("💡 No hay datos de auditorías finalizadas para mostrar todavía.")
        
        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría de Gestión", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_score = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Cancelar y Volver"):
            st.session_state.auditoria_activa = False
            st.rerun()

        st.subheader("📝 Evaluación de Gestión")
        fecha_sel = st.date_input("Fecha de Auditoría", datetime.now())
        st.markdown("---")

        respuestas = {}
        for index, row in preguntas_df.iterrows():
            st.write(f"**{row.iloc[0]}**")
            if pd.notnull(row.iloc[1]): st.caption(f"ℹ️ {row.iloc[1]}")
            
            opcion = st.radio("Nota:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                              key=f"p_{index}", horizontal=True, label_visibility="collapsed")
            respuestas[index] = opcion
            st.markdown("---")

        # Cálculos del Sidebar
        hechas = sum(1 for v in respuestas.values() if v != "Pendiente")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        si = sum(1 for v in respuestas.values() if v == "Cumple")
        
        avance = (hechas / len(preguntas_df)) * 100
        score = (si / validas) * 100 if validas > 0 else 0

        p_avance.metric("Progreso", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_score.metric("Cumplimiento", f"{int(score)}%", delta=f"{int(score-90)}% vs Obj")

        if st.button("💾 Finalizar y Guardar en Excel", use_container_width=True):
            if avance < 100:
                st.warning("⚠️ Debés completar todas las preguntas del checklist.")
            else:
                with st.spinner("Actualizando planilla..."):
                    df_final = df_historico.copy()
                    fecha_str = fecha_sel.strftime('%Y-%m-%d')
                    
                    for idx, res in respuestas.items():
                        # Columna A (0) -> Fecha | Columna G (6) -> Resultado
                        df_final.iloc[idx, 0] = fecha_str
                        df_final.iloc[idx, 6] = res
                    
                    # ENVIAR AL SHEETS
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear() # Limpia la memoria para ver los cambios
                    st.success("✅ ¡Guardado con éxito!")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error detectado: {e}")
