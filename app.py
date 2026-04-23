import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Portal Auditoría", layout="wide")
st.title("🚗 Portal de Auditoría de Gestión")

# URL de tu Google Sheets
url = "https://docs.google.com/spreadsheets/d/1JYJrSU9aqdG7OqqBwa67DJjTui2DHqsmy7E8dNyMbok/edit"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url, ttl=0)
    st.write("Datos cargados con éxito:")
    st.dataframe(df)
except Exception as e:
    st.error(f"Error: {e}")
