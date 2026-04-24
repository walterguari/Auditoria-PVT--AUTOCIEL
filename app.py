import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Checklist Auditoría Autociel", layout="wide")

st.title("📋 Auditoría de Gestión: Checklist Dinámico")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit#gid=1392263871"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = conn.read(spreadsheet=url, ttl=0)
    
    # Extraemos preguntas (Col E) y descripción (Col F)
    # Ajustamos el índice para empezar desde los datos reales
    preguntas_df = df_base.iloc[:, [4, 5]].dropna(subset=[df_base.columns[4]])
    total_preguntas = len(preguntas_df)

    # --- SIDEBAR DE ESTADÍSTICAS ---
    st.sidebar.header("📊 Resumen de Auditoría")
    placeholder_avance = st.sidebar.empty()
    placeholder_cumplimiento = st.sidebar.empty()

    with st.form("checklist_form"):
        st.subheader("⚙️ Información General")
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input("Fecha", datetime.now())
        with c2:
            sucursal = st.selectbox("Sucursal", ["Jujuy", "Salta", "Tartagal"])
        with c3:
            unidad = st.text_input("Dominio / VIN")

        st.markdown("---")
        
        respuestas = {}
        cont_respondidas = 0
        cont_cumple = 0

        # --- GENERACIÓN DEL CHECKLIST ---
        for index, row in preguntas_df.iterrows():
            pregunta = row.iloc[0]
            descripcion = row.iloc[1]
            
            st.write(f"**{pregunta}**")
            if pd.notnull(descripcion):
                st.caption(f"🔍 {descripcion}")
            
            # Usamos un select_slider o radio para la Columna G (Nota)
            opcion = st.radio(
                "Resultado:",
                ["Pendiente", "Cumple", "No Cumple", "N/A"],
                key=f"p_{index}",
                horizontal=True,
                label_visibility="collapsed"
            )
            
            respuestas[index] = opcion
            
            # Cálculos en tiempo real (para el envío)
            if opcion != "Pendiente":
                cont_respondidas += 1
                if opcion == "Cumple":
                    cont_cumple += 1

        # --- CÁLCULO DE PORCENTAJES ---
        porc_avance = (cont_respondidas / total_preguntas) * 100 if total_preguntas > 0 else 0
        
        # Cumplimiento sobre las respondidas (excluyendo N/A para ser justo)
        total_validas = sum(1 for v in respuestas.values() if v in ["Cumple", "No Cumple"])
        porc_cumplimiento = (cont_cumple / total_validas) * 100 if total_validas > 0 else 0

        # Actualizar indicadores en el Sidebar
        placeholder_avance.metric("Avance del Checklist", f"{int(porc_avance)}%")
        placeholder_avance.progress(porc_avance / 100)
        
        color_cumple = "normal" if porc_cumplimiento > 80 else "inverse"
        placeholder_cumplimiento.metric("Índice de Cumplimiento", f"{int(porc_cumplimiento)}%", delta_color=color_cumple)

        st.markdown("---")
        observaciones = st.text_area("Notas adicionales")
        
        enviar = st.form_submit_button("💾 Guardar Auditoría")

        if enviar:
            if porc_avance < 100:
                st.warning(f"Atención: Solo has respondido el {int(porc_avance)}% de las preguntas.")
            else:
                st.success(f"¡Auditoría finalizada! Cumplimiento total: {int(porc_cumplimiento)}%")
                st.balloons()

except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
