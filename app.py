import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Dashboard Auditoría Autociel", layout="wide")

@st.cache_data(ttl=60)
def cargar_datos_base(_conn, url):
    df = _conn.read(spreadsheet=url, ttl=0)
    # Preguntas en Col E y F. Notas en Col G. Fechas en Col A (índice 0).
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

    if not st.session_state.auditoria_activa:
        st.subheader("📊 Tablero de Resultados Mensuales")
        
        # --- PROCESAMIENTO PARA EL GRÁFICO ---
        try:
            # Aseguramos que la columna de fecha sea tipo datetime
            df_historico.iloc[:, 0] = pd.to_datetime(df_historico.iloc[:, 0], errors='coerce')
            df_valido = df_historico.dropna(subset=[df_historico.columns[0]])
            
            # Filtramos solo registros con nota "Cumple" o "No Cumple"
            df_valido = df_valido[df_valido.iloc[:, 6].isin(["Cumple", "No Cumple"])]
            
            if not df_valido.empty:
                # Agrupamos por mes y calculamos cumplimiento
                df_valido['Mes'] = df_valido.iloc[:, 0].dt.strftime('%Y-%m')
                resumen_mes = df_valido.groupby('Mes').apply(
                    lambda x: (x.iloc[:, 6] == "Cumple").sum() / len(x) * 100
                ).reset_index(name='Cumplimiento')

                # Mostramos métricas principales
                m1, m2 = st.columns(2)
                promedio_actual = resumen_mes['Cumplimiento'].iloc[-1] if not resumen_mes.empty else 0
                m1.metric("Cumplimiento Mes Actual", f"{int(promedio_actual)}%", delta=f"{int(promedio_actual - 90)}% vs Objetivo")
                m2.metric("Objetivo de Red", "90%")

                # --- GRÁFICO DE BARRAS CON LÍNEA DE OBJETIVO ---
                st.markdown("#### Evolución de Cumplimiento por Mes")
                
                # Crear el gráfico
                chart_data = resumen_mes.set_index('Mes')
                chart_data['Objetivo'] = 90  # Línea fija del 90%
                
                st.bar_chart(chart_data['Cumplimiento'])
                st.line_chart(chart_data['Objetivo']) 
                # Nota: Streamlit bar_chart es simple; para superponer exactamente la línea 
                # se suele usar librerías como Plotly, pero esto te da la visual rápida.
            else:
                st.info("Aún no hay datos suficientes para generar el gráfico mensual.")
        except Exception as e:
            st.warning("Iniciando visualización de datos...")

        st.markdown("---")
        if st.button("🚀 Iniciar Nueva Auditoría", use_container_width=True):
            st.session_state.auditoria_activa = True
            st.rerun()

    # --- PANTALLA 2: CHECKLIST (Sigue igual para mantener funcionalidad) ---
    else:
        st.sidebar.header("📊 Seguimiento")
        p_avance = st.sidebar.empty()
        p_cumplimiento = st.sidebar.empty()
        
        if st.sidebar.button("⬅️ Volver"):
            st.session_state.auditoria_activa = False
            st.rerun()

        respuestas = {}
        st.subheader("📝 Checklist de Gestión")
        
        for index, row in preguntas_df.iterrows():
            with st.container():
                st.write(f"**{row.iloc[0]}**")
                opcion = st.radio("Resultado:", ["Pendiente", "Cumple", "No Cumple", "N/A"], key=f"p_{index}", horizontal=True, label_visibility="collapsed")
                respuestas[index] = opcion
                st.markdown("---")

        # Cálculos en vivo
        respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cumplen = sum(1 for v in respuestas.values() if v == "Cumple")
        validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        avance = (respondidas / len(preguntas_df)) * 100
        score = (cumplen / validas) * 100 if validas > 0 else 0

        p_avance.metric("Avance", f"{int(avance)}%")
        p_avance.progress(avance / 100)
        p_cumplimiento.metric("Score Actual", f"{int(score)}%")

        if st.button("💾 Finalizar y Guardar"):
            if avance < 100:
                st.warning("Complete todo el checklist.")
            else:
                for idx, res in respuestas.items():
                    df_historico.iat[idx, 6] = res
                conn.update(spreadsheet=url, data=df_historico)
                st.cache_data.clear()
                st.success("¡Guardado correctamente!")
                st.balloons()
                st.session_state.auditoria_activa = False

except Exception as e:
    st.error(f"Error: {e}")
