"""
SaludCerca · versión Streamlit (Diagnóstico de Google Sheets)
"""

from __future__ import annotations
import datetime as dt
import math
import pandas as pd
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------
RESOURCE_ID = "2c44d782-3365-44e3-aefb-2c8b8363a1bc"
API_URL = "https://datos.gob.cl/api/3/action/datastore_search"

AZUL = "#1B3A5C"
TINTA = "#132A42"
ORO = "#C6A15B"
PAPEL = "#F7F5F0"
GRIS = "#5B6B7A"

TIPOS_CORTOS = {
    "Servicio de Atención Primaria de Urgencia (SAPU)": "SAPU",
    "Servicio de Atención Primaria de Urgencia de Alta Resolutividad (SAR)": "SAR",
    "Servicio de Urgencia Rural (SUR)": "SUR",
    "Centro de Salud Familiar (CESFAM)": "CESFAM",
    "Centro Comunitario de Salud Familiar (CECOSF)": "CECOSF",
    "Posta de Salud Rural (PSR)": "Posta rural",
    "Centro de Salud Privado": "Centro privado",
    "Centro  Diagnóstico y Tratamiento Privado": "Centro diagnóstico",
    "Centro Comunitario de Salud Mental  (COSAM)": "COSAM",
    "Sala  Externa de Toma de Muestras (SETM)": "Toma de muestras",
    "Unidad de Procedimientos Móvil": "Unidad móvil",
    "Unidad de Salud Funcionarios": "Unidad de salud",
    "Dirección Servicio de Salud": "Dirección SS",
    "Programa de Reparación y Atención Integral de Salud (PRAIS)": "PRAIS",
    "Centro de Diálisis": "Centro de diálisis",
    "Laboratorio Clínico": "Laboratorio",
    "Clínica Dental": "Clínica dental",
    "Centro de Especialidades": "Especialidades",
    "Centro de Especialidades de Atención Primaria (CEAP)": "Especialidades APS",
    "Centro Corporación para la Nutrición Infantil (CONIN)": "CONIN",
    "Centro de Rehabilitación": "Rehabilitación",
    "Centro de Salud Comunitario para Personas con Demencia": "Demencia",
    "Centro de Regulación Médica de las Urgencias (SAMU)": "Regulador SAMU",
    "Consultorio General Rural (CGR)": "Consultorio rural",
    "Consultorio General Urbano (CGU)": "Consultorio urbano",
    "Centro de Salud Comunitario": "Centro comunitario",
    "Centro de Regulación Médica de las Urgencias": "Regulador SAMU",
}

st.set_page_config(page_title="Centro de Salud con Urgencia más cercano", page_icon="📍", layout="centered")

# --------------------------------------------------------------------------
# LÓGICA DEL CONTADOR CON GOOGLE SHEETS (CON DIAGNÓSTICO)
# --------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Intentamos leer los secretos
    if "gcp_service_account" not in st.secrets:
        st.error("❌ ERROR: No se encontró la sección [gcp_service_account] en los Secretos de Streamlit.")
        return None
        
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def registrar_visita_gspread() -> int:
    if "ya_visito" in st.session_state:
        return st.session_state["contador_actual"]

    try:
        client = get_gspread_client()
        if client is None:
            return 32 # Respaldo

        if "gsheets" not in st.secrets or "spreadsheet_url" not in st.secrets["gsheets"]:
            st.error("❌ ERROR: No se encontró la URL de Google Sheets en los Secretos.")
            return 32

        # Abre la hoja
        sh = client.open_by_url(st.secrets["gsheets"]["spreadsheet_url"])
        worksheet = sh.sheet1
        
        # Lee el valor
        valor_actual_str = worksheet.acell('A1').value
        visitas = int(valor_actual_str) if valor_actual_str else 32
        
        # Incrementa y escribe
        visitas += 1
        worksheet.update('A1', str(visitas))
        
        st.session_state["ya_visito"] = True
        st.session_state["contador_actual"] = visitas
        return visitas
        
    except Exception as e:
        # AQUI ESTÁ LA MAGIA: Mostramos el error exacto en pantalla
        st.error(f"🚨 Error de conexión con Google Sheets: {e}")
        st.session_state["ya_visito"] = True
        st.session_state["contador_actual"] = 32
        return 32

# Ejecutamos el contador
num_visitas = registrar_visita_gspread()
num_visitas_str = f"{num_visitas:,}".replace(",", ".")

# (El resto del CSS y la interfaz de usuario se mantienen exactamente igual que antes)
st.markdown(
    f"""
    <style>
      .stApp {{ background-color: {PAPEL} !important; }}
      h1, h2, h3, p, label {{ font-family: system-ui, -apple-system, sans-serif !important; color: {TINTA} !important; }}
      .contador {{ text-align: center; font-size: 0.9rem; color: {GRIS} !important; margin-bottom: 1rem; font-weight: 600; letter-spacing: 0.5px; }}
      .cabecera {{ text-align: center; margin-bottom: 1.5rem; }}
      .cabecera h1 {{ font-size: 1.8rem; line-height: 1.2; color: {AZUL} !important; font-weight: 800; }}
      div.stButton > button:first-child {{ height: 100px; width: 100%; background-color: #E3F2FD !important; border: 3px dashed {AZUL} !important; border-radius: 16px !important; color: {AZUL} !important; font-size: 1.3rem !important; font-weight: bold !important; }}
      div[data-testid="stToggle"] {{ background-color: #FFF3E0; padding: 1rem; border-radius: 12px; border: 2px solid #F57C00; margin-bottom: 1.5rem; }}
      div[data-testid="stToggle"] label p {{ font-size: 1.2rem !important; font-weight: 800 !important; color: #E65100 !important; }}
      .tarjeta-principal {{ background: #FFFFFF; border: 3px solid {ORO}; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; text-align: center; }}
      .tarjeta-principal h2 {{ font-size: 1.8rem; margin: 0 0 0.5rem 0; color: {AZUL} !important; line-height: 1.2; }}
      .tarjeta-principal .dir {{ font-size: 1.2rem; color: {TINTA} !important; margin-bottom: 1rem; }}
      .tarjeta-principal .distancia {{ font-size: 1.4rem; font-weight: bold; color: {ORO} !important; margin-bottom: 0; }}
      .btn-accion {{ display: flex; align-items: center; justify-content: center; width: 100%; padding: 1.2rem; margin-bottom: 1rem; border-radius: 12px; font-size: 1.5rem; font-weight: bold; text-decoration: none !important; color: #FFFFFF !important; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }}
      .btn-llamar {{ background-color: #2E7D32 !important; }}
      .btn-ruta {{ background-color: {AZUL} !important; }}
      .stCheckbox label {{ font-size: 1.1rem !important; font-weight: bold !important; color: {AZUL} !important; }}
      #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="contador">Eres el usuario número {num_visitas_str} del sistema</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="cabecera">
      <p>Datos Abiertos de Salud · Chile</p>
      <h1>Centro de Salud con servicio de Urgencia más cercano</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ... (El resto de las funciones de datos y la interfaz de la app continúan aquí, igual que antes)
