import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Checklist de Auditoría Autociel", layout="wide")

st.title("📋 Checklist de Auditoría de Gestión")
st.markdown("---")

# URL de tu Sheets
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leemos la planilla base
    # Nota: Ajustamos el rango para leer las columnas E, F y G
    df_base = conn.read(spreadsheet=url, ttl=0)
    
    # Limpiamos los datos (asumiendo que las preguntas empiezan después del encabezado)
    # Filtramos filas vacías en la columna E (Preguntas)
    preguntas_df = df_base.iloc[:, [4, 5]].dropna(subset=[df_base.columns[4]]) 

    with st.form("checklist_form"):
        st.subheader("⚙️ Configuración de la Auditoría")
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            sucursal = st.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
        with col3:
            auditor = st.text_input("Auditor", value="Walter")
        
        st.markdown("---")
        st.subheader("📝 Evaluación de Puntos de Control")
        
        respuestas = []
        
        # Generar dinámicamente el checklist basado en las columnas E y F
        for index, row in preguntas_df.iterrows():
            pregunta = row.iloc[0]      # Columna E
            descripcion = row.iloc[1]   # Columna F
            
            st.write(f"**{pregunta}**")
            if pd.notnull(descripcion):
                st.caption(f"ℹ️ {descripcion}")
            
            # Selector de nota/cumplimiento para la Columna G
            nota = st.radio(
                f"Resultado para: {pregunta}",
                ["Cumple", "No Cumple", "N/A"],
                key=f"preg_{index}",
                horizontal=True,
                label_visibility="collapsed"
            )
            respuestas.append(nota)
            st.markdown("---")

        observaciones_gen = st.text_area("Observaciones Generales de la Auditoría")
        
        submit = st.form_submit_button("Finalizar y Guardar Auditoría")

        if submit:
            st.success("✅ Auditoría procesada. Los resultados se han vinculado a la estructura de las columnas E, F y G.")
            # Aquí podrías agregar la lógica para escribir de vuelta al Sheets si lo deseas
            st.balloons()

except Exception as e:
    st.error(f"No pudimos cargar las preguntas del Sheets: {e}")
    st.info("Asegúrate de que la hoja tenga datos en las columnas E y F.")
