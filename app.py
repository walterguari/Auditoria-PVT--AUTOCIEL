import streamlit as st
from streamlit_gsheets import GSheetsConnection  # <-- Esta es la línea que faltaba
import pandas as pd
from datetime import datetime

# Configuración visual de la página
st.set_page_config(page_title="Portal Auditoría Grupo Cenoa", layout="wide")

st.title("🚗 Portal de Auditoría de Gestión")
st.markdown("---")

# Conexión con tu Google Sheets
# Aquí usamos el nombre del tipo de conexión correctamente
conn = st.connection("gsheets", type=GSheetsConnection)

# URL de tu planilla suministrada
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

# Menú lateral de navegación
menu = st.sidebar.selectbox("Seleccione una opción", ["Dashboard de Control", "Nueva Auditoría"])

if menu == "Dashboard de Control":
    st.header("📈 Indicadores de Calidad")
    
    try:
        # Lectura de datos
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
        df = df.dropna(how="all")

        # Filtros en la barra lateral
        sucursal = st.sidebar.multiselect("Sucursal", options=df["Sucursal"].unique(), default=df["Sucursal"].unique())
        asesor = st.sidebar.multiselect("Asesor de Servicio", options=df["Asesor"].unique(), default=df["Asesor"].unique())

        df_filt = df[(df["Sucursal"].isin(sucursal)) & (df["Asesor"].isin(asesor))]

        # Métricas destacadas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Auditorías", len(df_filt))
        with c2:
            q2_avg = pd.to_numeric(df_filt["Q2 - RECOMENDACIÓN"], errors='coerce').mean()
            st.metric("Promedio Q2 (Recomendación)", f"{q2_avg:.2f}")
        with c3:
            st.metric("Sucursales", len(sucursal))

        st.markdown("---")
        st.subheader("Registros Recientes")
        st.dataframe(df_filt, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar datos: {e}")

elif menu == "Nueva Auditoría":
    st.header("📝 Registro de Nueva Auditoría")
    
    with st.form("form_auditoria", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", datetime.now())
            suc = st.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
            nom_asesor = st.text_input("Nombre del Asesor")
            vin = st.text_input("VIN / Chasis")
        with col2:
            q2 = st.slider("Q2 - Nivel de Recomendación", 0, 10, 8)
            tipo = st.selectbox("Tipo de Intervención", ["Mantenimiento", "Correctivo", "Garantía"])
            estado_v = st.radio("Estado General", ["Aprobado", "Con Observaciones", "Rechazado"])

        obs = st.text_area("Observaciones del Auditor")
        enviar = st.form_submit_button("Guardar Auditoría")

        if enviar:
            st.success("¡Datos listos para enviar! (Para activar el guardado, el Excel debe tener permisos de la cuenta de servicio)")
