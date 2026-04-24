import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Checklist Interactivo Autociel", layout="wide")

st.title("📋 Auditoría de Gestión en Tiempo Real")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = conn.read(spreadsheet=url, ttl=0)
    
    # Filtramos las preguntas de la Columna E y descripciones de la F
    preguntas_df = df_base.iloc[:, [4, 5]].dropna(subset=[df_base.columns[4]])
    total_preguntas = len(preguntas_df)

    # --- SIDEBAR DE ESTADÍSTICAS (FIJO) ---
    st.sidebar.header("📊 Indicadores de Auditoría")
    
    # Contenedores para actualizar en tiempo real
    avance_text = st.sidebar.empty()
    avance_bar = st.sidebar.empty()
    cumple_text = st.sidebar.empty()
    
    st.sidebar.markdown("---")
    sucursal = st.sidebar.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
    unidad = st.sidebar.text_input("VIN / Dominio")

    # --- CUERPO DEL CHECKLIST ---
    respuestas = {}
    
    # Recorremos las preguntas
    for index, row in preguntas_df.iterrows():
        with st.container():
            pregunta = row.iloc[0]
            descripcion = row.iloc[1]
            
            st.write(f"**{pregunta}**")
            if pd.notnull(descripcion):
                st.caption(f"ℹ️ {descripcion}")
            
            # Al quitar el form, cada cambio aquí actualiza la página
            opcion = st.radio(
                "Resultado:",
                ["Pendiente", "Cumple", "No Cumple", "N/A"],
                key=f"p_{index}",
                horizontal=True,
                label_visibility="collapsed"
            )
            respuestas[index] = opcion
            st.markdown("---")

    # --- CÁLCULOS DINÁMICOS ---
    cont_respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
    cont_cumple = sum(1 for v in respuestas.values() if v == "Cumple")
    total_validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])

    porc_avance = (cont_respondidas / total_preguntas) * 100 if total_preguntas > 0 else 0
    porc_cumplimiento = (cont_cumple / total_validas) * 100 if total_validas > 0 else 0

    # Actualizar Sidebar en tiempo real
    avance_text.metric("Avance", f"{int(porc_avance)}%")
    avance_bar.progress(porc_avance / 100)
    
    color_delta = "normal" if porc_cumplimiento >= 80 else "inverse"
    cumple_text.metric("Cumplimiento", f"{int(porc_cumplimiento)}%", 
                       delta=f"{int(porc_cumplimiento)}% Score", delta_color=color_delta)

    # Botón final solo para enviar los datos al Sheets
    if st.button("💾 Finalizar y Enviar Reporte"):
        if porc_avance < 100:
            st.warning(f"Faltan responder {total_preguntas - cont_respondidas} preguntas.")
        else:
            st.success("Auditoría enviada correctamente.")
            st.balloons()

except Exception as e:
    st.error(f"Error: {e}")
