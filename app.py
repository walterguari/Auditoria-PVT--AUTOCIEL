import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Gestión de Auditoría Autociel", layout="wide")

@st.cache_data(ttl=60)
def cargar_datos_base(_conn, url):
    df = _conn.read(spreadsheet=url, ttl=0)
    preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
    return preguntas, df

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
        st.subheader("📊 Panel de Control de Calidad")
        
        # Procesamiento de datos para el gráfico
        df_plot = df_historico.copy()
        df_plot.iloc[:, 0] = pd.to_datetime(df_plot.iloc[:, 0], errors='coerce')
        df_plot = df_plot[df_plot.iloc[:, 6].isin(["Cumple", "No Cumple"])].dropna(subset=[df_plot.columns[0]])

        if not df_plot.empty:
            df_plot['Mes'] = df_plot.iloc[:, 0].dt.strftime('%Y-%m')
            resumen = df_plot.groupby('Mes').apply(
                lambda x: round((x.iloc[:, 6] == "Cumple").sum() / len(x) * 100, 1)
            ).reset_index(name='Cumplimiento')

            # --- GRÁFICO CON PLOTLY ---
            fig = go.Figure()
            # Barras de cumplimiento
            fig.add_trace(go.Bar(
                x=resumen['Mes'], y=resumen['Cumplimiento'],
                name='Cumplimiento %', marker_color='#007bff'
            ))
            # Línea de Objetivo 90%
            fig.add_trace(go.Scatter(
                x=resumen['Mes'], y=[90]*len(resumen),
                mode='lines', name='Objetivo 90%',
                line=dict(color='red', width=3, dash='dash')
            ))
            
            fig.update_layout(
                title='Cumplimiento Mensual vs Objetivo',
                xaxis_title='Mes de Auditoría',
                yaxis_title='% Cumplimiento',
                yaxis=dict(range=[0, 105]),
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Realiza tu primera auditoría para ver el gráfico de barras.")

        if st.button("🚀 Iniciar Nueva Auditoría de Gestión", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: EL CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_cumplimiento = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Cancelar y Volver"):
            st.session_state.auditoria_activa = False
            st.rerun()

        st.subheader("📝 Nuevo Registro de Auditoría")
        
        # FECHA DENTRO DEL CHECKLIST
        fecha_auditoria = st.date_input("Fecha de la Auditoría", datetime.now())
        st.markdown("---")

        respuestas = {}
        for index, row in preguntas_df.iterrows():
            st.write(f"**{row.iloc[0]}**")
            if pd.notnull(row.iloc[1]): st.caption(f"ℹ️ {row.iloc[1]}")
            opcion = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{index}", horizontal=True, label_visibility="collapsed")
            respuestas[index] = opcion
            st.markdown("---")

        # Cálculos en tiempo real
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        avance = (respondidas / len(preguntas_df)) * 100
        score = (cumplen / validas) * 100 if validas > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_cumplimiento.metric("Score Actual", f"{int(score)}%", delta=f"{int(score-90)}% vs Obj", delta_color="normal" if score >= 90 else "inverse")

        if st.button("💾 Finalizar y Guardar en Sheets", use_container_width=True):
            if avance < 100:
                st.warning("Faltan preguntas por responder.")
            else:
                with st.spinner("Guardando..."):
                    # Guardamos la fecha en la Col A (índice 0) y notas en Col G (índice 6)
                    for idx, res in respuestas.items():
                        df_historico.iat[idx, 0] = fecha_auditoria.strftime('%Y-%m-%d')
                        df_historico.iat[idx, 6] = res
                    
                    conn.update(spreadsheet=url, data=df_historico)
                    st.cache_data.clear()
                    st.success("¡Datos guardados! Revisa el tablero inicial.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error técnico: {e}")
