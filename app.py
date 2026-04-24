import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Dashboard Auditoría Autociel", layout="wide")

# Función para cargar datos con protección de caché
@st.cache_data(ttl=60)
def cargar_datos_base(_conn, url):
    try:
        df = _conn.read(spreadsheet=url, ttl=0)
        # Preguntas en Col E y F (índices 4 y 5)
        preguntas = df.iloc[:, [4, 5]].dropna(subset=[df.columns[4]])
        return preguntas, df
    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
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
        st.subheader("📊 Tablero de Resultados Mensuales")
        
        # Procesamiento para el gráfico
        if not df_historico.empty and df_historico.shape[1] > 6:
            df_plot = df_historico.copy()
            # Convertimos columna A a fecha
            df_plot.iloc[:, 0] = pd.to_datetime(df_plot.iloc[:, 0], errors='coerce')
            # Filtramos solo filas con "Cumple" o "No Cumple" en columna G
            df_plot = df_plot[df_plot.iloc[:, 6].isin(["Cumple", "No Cumple"])].dropna(subset=[df_plot.columns[0]])

            if not df_plot.empty:
                df_plot['Mes'] = df_plot.iloc[:, 0].dt.strftime('%Y-%m')
                resumen = df_plot.groupby('Mes').apply(
                    lambda x: round((x.iloc[:, 6] == "Cumple").sum() / len(x) * 100, 1)
                ).reset_index(name='Cumplimiento')

                # --- GRÁFICO VERTICAL CON LÍNEA OBJETIVO ---
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=resumen['Mes'], y=resumen['Cumplimiento'],
                    name='Cumplimiento %', marker_color='#1f77b4',
                    text=resumen['Cumplimiento'].astype(str) + '%', textposition='auto'
                ))
                # Línea de Objetivo 90%
                fig.add_trace(go.Scatter(
                    x=resumen['Mes'], y=[90]*len(resumen),
                    mode='lines', name='Objetivo 90%',
                    line=dict(color='red', width=3, dash='dash')
                ))
                
                fig.update_layout(
                    xaxis_title="Mes de Auditoría",
                    yaxis_title="% Cumplimiento",
                    yaxis=dict(range=[0, 110]),
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aún no hay datos guardados para mostrar en el gráfico mensual.")
        
        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría de Gestión", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_cumplimiento = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Cancelar"):
            st.session_state.auditoria_activa = False
            st.rerun()

        st.subheader("📝 Registro de Auditoría")
        # FECHA OBLIGATORIA AL INICIO
        fecha_sel = st.date_input("Fecha de la Auditoría", datetime.now())
        st.markdown("---")

        respuestas = {}
        for index, row in preguntas_df.iterrows():
            st.write(f"**{row.iloc[0]}**")
            opcion = st.radio("Nota:", ["Pendiente", "Cumple", "No Cumple", "N/A"], 
                              key=f"p_{index}", horizontal=True, label_visibility="collapsed")
            respuestas[index] = opcion
            st.markdown("---")

        # Cálculos interactivos
        total_p = len(preguntas_df)
        resp_hechas = sum(1 for v in respuestas.values() if v != "Pendiente")
        votos_cumple = sum(1 for v in respuestas.values() if v == "Cumple")
        votos_validos = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        
        avance = (resp_hechas / total_p) * 100
        score = (votos_cumple / votos_validos) * 100 if votos_validos > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_cumplimiento.metric("Cumplimiento Actual", f"{int(score)}%", delta=f"{int(score-90)}% vs Obj")

        if st.button("💾 Finalizar y Guardar en Excel", use_container_width=True):
            if avance < 100:
                st.warning("Debe completar todas las preguntas.")
            else:
                with st.spinner("Sincronizando con Google Sheets..."):
                    # Actualizamos DataFrame: Fecha en Col A, Resultado en Col G
                    for idx, res in respuestas.items():
                        df_historico.iat[idx, 0] = fecha_sel.strftime('%Y-%m-%d')
                        df_historico.iat[idx, 6] = res
                    
                    conn.update(spreadsheet=url, data=df_historico)
                    st.cache_data.clear() # Forzar lectura de nuevos datos
                    st.success("¡Guardado! El tablero inicial se ha actualizado.")
                    st.balloons()
                    st.session_state.auditoria_activa = False
                    st.rerun()

except Exception as e:
    st.error(f"Error técnico detectado: {e}")
