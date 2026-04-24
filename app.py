import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Portal Auditoría Autociel", layout="wide")

# --- LÓGICA DE ESTADO DE SESIÓN ---
# Esto sirve para que la app "recuerde" si ya presionaste el botón de iniciar
if 'auditoria_activa' not in st.session_state:
    st.session_state.auditoria_activa = False

st.title("🚗 Auditoría de Gestión Autociel")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = conn.read(spreadsheet=url, ttl=0)
    preguntas_df = df_base.iloc[:, [4, 5]].dropna(subset=[df_base.columns[4]])
    total_preguntas = len(preguntas_df)

    # --- PANTALLA INICIAL: CONFIGURACIÓN ---
    if not st.session_state.auditoria_activa:
        st.subheader("⚙️ Configuración Inicial")
        col1, col2 = st.columns(2)
        with col1:
            sucursal = st.selectbox("Sucursal a Auditar", ["Jujuy", "Salta", "Tartagal"])
            asesor = st.selectbox("Asesor de Servicio", ["Haydeé", "Antonio", "Otro"])
        with col2:
            unidad = st.text_input("VIN / Dominio de la Unidad")
            fecha_auditoria = st.date_input("Fecha", datetime.now())

        st.markdown("---")
        if st.button("🚀 Iniciar Auditoría de Gestión", use_container_width=True):
            if unidad: # Validamos que al menos ponga el VIN
                st.session_state.auditoria_activa = True
                st.rerun()
            else:
                st.warning("Por favor, ingrese el VIN o Dominio antes de iniciar.")

    # --- PANTALLA SECUNDARIA: EL CHECKLIST ---
    else:
        # Botón para volver o cancelar
        if st.sidebar.button("⬅️ Cancelar / Reiniciar"):
            st.session_state.auditoria_activa = False
            st.rerun()

        # Indicadores en el Sidebar
        st.sidebar.header("📊 Seguimiento")
        placeholder_avance = st.sidebar.empty()
        placeholder_cumplimiento = st.sidebar.empty()
        st.sidebar.info(f"📍 **Sucursal:** {sucursal}\n\n👤 **Asesor:** {asesor}\n\n🚘 **Unidad:** {unidad}")

        respuestas = {}
        
        st.subheader(f"📝 Checklist de Evaluación - {sucursal}")
        
        for index, row in preguntas_df.iterrows():
            with st.container():
                pregunta = row.iloc[0]
                descripcion = row.iloc[1]
                
                st.write(f"**{pregunta}**")
                if pd.notnull(descripcion):
                    st.caption(f"ℹ️ {descripcion}")
                
                opcion = st.radio(
                    "Resultado:",
                    ["Pendiente", "Cumple", "No Cumple", "N/A"],
                    key=f"p_{index}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                respuestas[index] = opcion
                st.markdown("---")

        # Cálculos Dinámicos
        cont_respondidas = sum(1 for v in respuestas.values() if v != "Pendiente")
        cont_cumple = sum(1 for v in respuestas.values() if v == "Cumple")
        total_validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])

        porc_avance = (cont_respondidas / total_preguntas) * 100 if total_preguntas > 0 else 0
        porc_cumplimiento = (cont_cumple / total_validas) * 100 if total_validas > 0 else 0

        # Actualizar Sidebar
        placeholder_avance.metric("Avance", f"{int(porc_avance)}%")
        placeholder_avance.progress(porc_avance / 100)
        
        color_delta = "normal" if porc_cumplimiento >= 80 else "inverse"
        placeholder_cumplimiento.metric("Cumplimiento", f"{int(porc_cumplimiento)}%", 
                                       delta=f"{int(porc_cumplimiento)}% Score", delta_color=color_delta)

        if st.button("💾 Finalizar y Enviar Reporte", use_container_width=True):
            if porc_avance < 100:
                st.warning(f"Faltan responder {total_preguntas - cont_respondidas} preguntas.")
            else:
                st.success("Auditoría enviada correctamente a la base de datos.")
                st.balloons()
                # Opcional: st.session_state.auditoria_activa = False (para volver al inicio)

except Exception as e:
    st.error(f"Error técnico: {e}")
