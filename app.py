import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Portal Auditoría Autociel", layout="wide")

st.title("🚗 Control de Gestión y Auditoría")
st.markdown("---")

# URL de tu Sheets (Estandarizada)
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- FORMULARIO DE AUDITORÍA ---
    with st.form("audit_form"):
        st.subheader("📋 Nueva Auditoría de Proceso")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("Fecha de Auditoría", datetime.now())
            sucursal = st.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
            asesor = st.selectbox("Asesor auditado", ["Haydeé", "Antonio", "Otro"])
            vin = st.text_input("Últimos 7 dígitos del VIN")
        
        st.markdown("---")
        
        # SECCIÓN 1: Columna E - GESTIÓN Y DOCUMENTACIÓN
        st.subheader("📂 Sector A: Gestión y Documentación (Col. E)")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            estado_legajo = st.selectbox("Estado del Legajo", ["Completo", "Pendiente Digitalización", "Faltan Firmas"])
        with col_e2:
            cumple_gestoria = st.radio("¿Cumple tiempos de gestoría?", ["Sí", "No"])

        # SECCIÓN 2: Columna F - ESTADO DE UNIDAD / TALLER
        st.subheader("🛠️ Sector B: Estado de Unidad y Taller (Col. F)")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            limpieza = st.select_slider("Calidad de Limpieza / Estética", options=["Mala", "Regular", "Buena", "Excelente"])
            protecciones = st.checkbox("Uso de fundas y protecciones Stellantis/Toyota")
        with col_f2:
            pdi_realizado = st.radio("¿PDI / Control de niveles realizado?", ["Sí", "No"])
            muda_detectada = st.checkbox("¿Se detectó MUDA (tiempo muerto) en el proceso?")

        # SECCIÓN 3: Columna G - CONTROL DE ENTREGA Y Q2
        st.subheader("⭐ Sector C: Control de Entrega y Recomendación (Col. G)")
        q2_score = st.slider("Q2 - ¿Qué tan probable es que el cliente nos recomiende? (1-10)", 1, 10, 8)
        comentarios = st.text_area("Observaciones de la Auditoría")

        submit = st.form_submit_button("Registrar Auditoría")

        if submit:
            # Aquí se crearía el diccionario para enviar al Sheets
            st.success(f"Auditoría registrada para el VIN {vin}. Datos listos para sincronizar con Columnas E, F y G.")

    # --- VISUALIZACIÓN DE DATOS ACTUALES ---
    st.markdown("---")
    st.subheader("📊 Datos en Planilla (Columnas E, F, G)")
    df = conn.read(spreadsheet=url, ttl=0)
    # Mostramos solo las columnas relevantes para este análisis
    columnas_interes = df.iloc[:, [4, 5, 6]] # E, F y G son índices 4, 5 y 6
    st.dataframe(columnas_interes.tail(10))

except Exception as e:
    st.error(f"Error al conectar con el portal: {e}")
