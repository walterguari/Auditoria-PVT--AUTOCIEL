import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Auditoría Autociel", layout="wide")

# Función con caché para proteger la cuota de lectura de Google
@st.cache_data(ttl=60)
def cargar_datos_base(_conn, url):
    try:
        df = _conn.read(spreadsheet=url, ttl=0)
        # Preguntas en Col E (4) y Descripción en Col F (5)
        preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
        return preguntas, df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    preguntas_df, df_historico = cargar_datos_base(conn, url)

    # --- PANTALLA 1: DASHBOARD ---
    if not st.session_state.auditoria_activa:
        st.subheader("📊 Cumplimiento Mensual vs Objetivo (90%)")
        
        if not df_historico.empty:
            df_plot = df_historico.copy()
            # Limpieza de fechas: Ignora lo que no sea una fecha válida
            df_plot.iloc[:, 0] = pd.to_datetime(df_plot.iloc[:, 0], errors='coerce')
            # Filtra solo filas con nota "Cumple" o "No Cumple" y con fecha válida
            df_plot = df_plot[df_plot.iloc[:, 6].isin(["Cumple", "No Cumple"])].dropna(subset=[df_plot.columns[0]])

            if not df_plot.empty:
                df_plot['Mes'] = df_plot.iloc[:, 0].dt.strftime('%Y-%m')
                resumen = df_plot.groupby('Mes').apply(
                    lambda x: round((x.iloc[:, 6] == "Cumple").sum() / len(x) * 100, 1)
                ).reset_index(name='Cumplimiento')

                # Creación del Gráfico Profesional
                fig = go.Figure()
                # Barras Verticales
                fig.add_trace(go.Bar(
                    x=resumen['Mes'], y=resumen['Cumplimiento'],
                    name='Real', marker_color='#007bff',
                    text=resumen['Cumplimiento'].astype(str) + '%', textposition='auto'
                ))
                # Línea Roja de Objetivo 90%
                fig.add_trace(go.Scatter(
                    x=resumen['Mes'], y=[90]*len(resumen),
                    mode='lines', name='Objetivo 90%',
                    line=dict(color='red', width=3, dash='dash')
                ))
                
                fig.update_layout(
                    xaxis_title="Mes de Auditoría",
                    yaxis_title="% de Cumplimiento",
                    yaxis=dict(range=[0, 110]),
                    template='plotly_white',
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("💡 Aún no hay datos registrados para mostrar el gráfico.")
        
        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría de Gestión", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_score = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Cancelar y Salir"):
            st.session_state.auditoria_activa = False
            st.rerun()

        st.subheader("📝 Nuevo Registro de Auditoría")
        # Selector de fecha obligatorio al inicio
        fecha_auditoria = st.date_input("Seleccione Fecha de Auditoría", datetime.now())
        st.markdown("---")

        respuestas = {}
        for index, row in preguntas_df.iterrows():
            st.write(f"**{row.iloc[0]}**")
            if pd.notnull(row.iloc[1]): st.caption(f"ℹ️ {row.iloc[1]}")
            
            opcion = st.radio("Nota:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                              key=f"p_{index}", horizontal=True, label_visibility="collapsed")
            respuestas[index] = opcion
            st.markdown("---")

        # Cálculos para el panel lateral
        total_p = len(preguntas_df)
        cont_hechas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cont_si = sum(1 for v in respuestas.values() if v == "Cumple")
        cont_validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        
        avance = (cont_hechas / total_p) * 100
        score = (cont_si / cont_validas) * 100 if cont_validas > 0 else 0

        p_avance.metric("Progreso", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_score.metric("Puntaje Actual", f"{int(score)}%", delta=f"{int(score-90)}% vs Obj")

        # BOTÓN DE GUARDADO FINAL
        if st.button("💾 Finalizar y Guardar en Excel", use_container_width=True):
            if avance < 100:
                st.warning("⚠️ Debe completar todas las preguntas del checklist.")
            else:
                with st.spinner("Sincronizando con Google Sheets..."):
                    df_final = df_historico.copy()
                    fecha_str = fecha_auditoria.strftime('%Y-%m-%d')
                    
                    for idx, res in respuestas.items():
                        # Col A (0): Fecha | Col G (6): Nota
                        df_final.iloc[idx, 0] = fecha_str
                        df_final.iloc[idx, 6] = res
                    
                    # Escritura en la nube
                    conn.update(spreadsheet=url, data=df_final)
                    st.cache_data.clear() # Limpia caché para refrescar el gráfico
                    st.success("✅ Auditoría guardada con éxito.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error técnico: {e}")
