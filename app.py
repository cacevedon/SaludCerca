"""
SaludCerca · versión Streamlit
================================
Encuentra el centro de salud más cercano que está abierto ahora.

Los datos se descargan en vivo desde la API de Datos Abiertos del Gobierno de
Chile (catastro de establecimientos de salud) y se limpian en memoria. No hay
base de datos ni almacenamiento de datos personales.

Autoría: Cristian Acevedo, Rodrigo Gómez, Marcelo Araya, Nathaly Donoso
"""

from __future__ import annotations
import datetime as dt
import math
import pandas as pd
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

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

st.set_page_config(page_title="SaludCerca", page_icon="📍", layout="centered")

# --------------------------------------------------------------------------
# CSS: Botones Gigantes y Textos Legibles
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
      .stApp {{ background-color: {PAPEL} !important; }}
      h1, h2, h3, p, label {{ font-family: system-ui, -apple-system, sans-serif !important; color: {TINTA} !important; }}
      
      .cabecera {{ text-align: center; margin-bottom: 1.5rem; }}
      .cabecera h1 {{ font-size: 2.2rem; line-height: 1.1; color: {AZUL} !important; font-weight: 800; }}

      /* Estilo para el botón nativo de Streamlit (GPS) */
      div.stButton > button:first-child {{
          height: 100px;
          width: 100%;
          background-color: #E3F2FD !important;
          border: 3px dashed {AZUL} !important;
          border-radius: 16px !important;
          color: {AZUL} !important;
          font-size: 1.3rem !important;
          font-weight: bold !important;
      }}
      div.stButton > button:first-child:hover {{
          background-color: #BBDEFB !important;
      }}

      /* Tarjeta principal */
      .tarjeta-principal {{ 
          background: #FFFFFF; 
          border: 3px solid {ORO}; 
          border-radius: 16px; 
          padding: 1.5rem; 
          margin-bottom: 1.5rem; 
          text-align: center;
      }}
      .tarjeta-principal h2 {{ font-size: 1.8rem; margin: 0 0 0.5rem 0; color: {AZUL} !important; line-height: 1.2; }}
      .tarjeta-principal .dir {{ font-size: 1.2rem; color: {TINTA} !important; margin-bottom: 1rem; }}
      .tarjeta-principal .distancia {{ font-size: 1.4rem; font-weight: bold; color: {ORO} !important; margin-bottom: 0; }}
      
      /* Botones de acción HTML */
      .btn-accion {{
          display: flex; align-items: center; justify-content: center;
          width: 100%; padding: 1.2rem; margin-bottom: 1rem;
          border-radius: 12px; font-size: 1.5rem; font-weight: bold;
          text-decoration: none !important; color: #FFFFFF !important;
          box-shadow: 0 4px 10px rgba(0,0,0,0.2);
      }}
      .btn-llamar {{ background-color: #2E7D32 !important; }}
      .btn-ruta {{ background-color: {AZUL} !important; }}

      .stCheckbox label {{ font-size: 1.1rem !important; font-weight: bold !important; color: {AZUL} !important; }}
      #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Lógica de Datos
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def cargar_catastro() -> tuple[pd.DataFrame, str]:
    registros: list[dict] = []
    offset = 0
    total = None
    while True:
        respuesta = requests.get(API_URL, params={"resource_id": RESOURCE_ID, "limit": 1000, "offset": offset}, timeout=40)
        respuesta.raise_for_status()
        resultado = respuesta.json()["result"]
        if total is None: total = resultado["total"]
        lote = resultado["records"]
        if not lote: break
        registros.extend(lote)
        offset += len(lote)
        if offset >= total: break
    df = pd.DataFrame(registros)
    df = _normalizar(df)
    sello = ahora_en_chile().strftime("%d-%m-%Y %H:%M")
    return df, sello

def _acortar_tipo(tipo: str) -> str:
    texto = TIPOS_CORTOS.get(tipo, tipo)
    return texto if len(texto) <= 22 else texto[:21].rstrip(" ,.") + "…"

def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df = df.copy()
    df["EstadoFuncionamiento"] = df["EstadoFuncionamiento"].fillna("").str.lower()
    df = df[df["EstadoFuncionamiento"].str.contains("vigente")]
    df["urgencia"] = df["TieneServicioUrgencia"].fillna("").str.strip().str.upper().eq("SI")
    df["lat"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["lon"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df = df[df["lat"].between(-56.9, -17.0) & df["lon"].between(-76.9, -66.0)]
    partes = df["TipoViaGlosa"].fillna("").str.strip() + " " + df["NombreVia"].fillna("").str.strip() + " " + df["Numero"].fillna("").astype(str).str.strip()
    df["direccion"] = partes.str.replace(r"\s+", " ", regex=True).str.strip()
    df["fono"] = df["TelefonoMovil_TelefonoFijo"].fillna("").astype(str).str.replace(r"[^0-9]", "", regex=True)
    df["comuna"] = df["ComunaGlosa"].fillna("").str.strip()
    df["nombre"] = df["EstablecimientoGlosa"].fillna("").str.strip()
    return df[df["nombre"].ne("")].reset_index(drop=True)

def ahora_en_chile() -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Santiago"))
    except Exception:
        return dt.datetime.utcnow() - dt.timedelta(hours=4)

def esta_abierto(urgencia: bool, ahora: dt.datetime) -> bool:
    if urgencia: return True
    return ahora.weekday() < 5 and 8 <= ahora.hour < 17

def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radio = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))

def formato_km(km: float) -> str:
    if km < 1: return f"{round(km * 1000)} m"
    return f"{km:.1f} km".replace(".", ",")

def tiempo_auto(km: float) -> str:
    minutos = round(km / 45 * 60) + 2
    if minutos < 60: return f"≈ {minutos} min en auto"
    return f"≈ {minutos // 60} h {minutos % 60} min"

# --------------------------------------------------------------------------
# INTERFAZ PRINCIPAL
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="cabecera">
      <p>Datos Abiertos de Salud · Chile</p>
      <h1>¿A dónde la llevo?</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    with st.spinner("Buscando centros de salud..."):
        df, sello = cargar_catastro()
except Exception:
    st.error("Error de conexión. Revisa tu internet.")
    st.stop()

origen = None

# 1. Revisamos si el usuario ya tocó el botón del GPS
if "gps_activado" not in st.session_state:
    st.session_state["gps_activado"] = False

# 2. Botón nativo de Streamlit (sin iframes, 100% seguro)
if not st.session_state["gps_activado"]:
    if st.button("📍 TOCA AQUÍ PARA ACTIVAR TU LOCALIZACIÓN", use_container_width=True):
        st.session_state["gps_activado"] = True
        st.rerun()

# 3. Si se activó, pedimos las coordenadas
if st.session_state["gps_activado"]:
    loc = get_geolocation()
    if loc and 'coords' in loc:
        lat = loc['coords']['latitude']
        lon = loc['coords']['longitude']
        origen = (lat, lon, "Tu ubicación actual")
        st.success("¡Ubicación encontrada!")
    else:
        st.info("Buscando señal GPS... Acepta el permiso del navegador.")
        # Botón para cancelar si se demora o falla
        if st.button("Cancelar y buscar por comuna"):
            st.session_state["gps_activado"] = False
            st.rerun()

# 4. Si no hay GPS, mostramos el buscador de comunas
if origen is None and not st.session_state["gps_activado"]:
    st.markdown("<p style='text-align:center; font-size: 1.2rem; margin-top: 1rem;'>O busca por comuna:</p>", unsafe_allow_html=True)
    comunas = sorted(df["comuna"].unique())
    comuna_sel = st.selectbox("Comuna", comunas, index=comunas.index("Santiago") if "Santiago" in comunas else 0, label_visibility="collapsed")
    
    del_lugar = df[df["comuna"] == comuna_sel]
    if not del_lugar.empty:
        origen = (float(del_lugar["lat"].mean()), float(del_lugar["lon"].mean()), f"Comuna de {comuna_sel}")

# --- RESULTADOS ---
if origen is not None:
    lat0, lon0, _ = origen
    ahora = ahora_en_chile()
    df["abierto"] = [esta_abierto(u, ahora) for u in df["urgencia"]]
    
    candidatos = df[df["abierto"]].copy()
    
    if not candidatos.empty:
        candidatos["km"] = [distancia_km(lat0, lon0, la, lo) for la, lo in zip(candidatos["lat"], candidatos["lon"])]
        candidatos = candidatos[candidatos["km"] <= 50].sort_values("km")

    if candidatos.empty:
        st.error("No hay centros abiertos a menos de 50 km. Llama al SAMU (131).")
    else:
        st.markdown("<hr style='margin: 1.5rem 0; border: 1px solid #E4E1D9;'>", unsafe_allow_html=True)
        
        # --- TARJETA GIGANTE ---
        primero = candidatos.iloc[0]
        st.markdown(
            f"""
            <div class="tarjeta-principal">
              <h2>{primero['nombre']}</h2>
              <p class="dir">📍 {primero['direccion'] or 'Sin dirección'} · {primero['comuna']}</p>
              <p class="distancia">A {formato_km(primero['km'])} ({tiempo_auto(primero['km'])})</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # --- BOTONES GIGANTES ---
        if primero["fono"]:
            st.markdown(f'<a href="tel:+56{primero["fono"]}" class="btn-accion btn-llamar">📞 LLAMAR AHORA</a>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="btn-accion" style="background-color: #9E9E9E !important;">📞 SIN TELÉFONO</div>', unsafe_allow_html=True)

        st.markdown(f'<a href="https://www.google.com/maps/dir/?api=1&destination={primero["lat"]},{primero["lon"]}" target="_blank" class="btn-accion btn-ruta">🗺️ CÓMO LLEGAR</a>', unsafe_allow_html=True)

        # --- OTRAS OPCIONES ---
        st.markdown("<br>", unsafe_allow_html=True)
        ver_mas = st.checkbox("👇 Mostrar otros centros cercanos")
        
        if ver_mas:
            for _, fila in candidatos.iloc[1:6].iterrows():
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem; margin-top: 1rem;">
                      <h4 style="margin: 0 0 0.3rem 0; font-size: 1.2rem; color: {TINTA} !important;">{fila['nombre']}</h4>
                      <p style="margin: 0; font-size: 1rem; color: {GRIS} !important;">📍 {fila['comuna']} · A {formato_km(fila['km'])}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                c1, c2 = st.columns(2)
                with c1:
                    if fila["fono"]:
                        st.markdown(f'<a href="tel:+56{fila["fono"]}" class="btn-accion btn-llamar" style="font-size: 1rem !important; padding: 0.8rem; margin-bottom: 0.5rem;">📞 Llamar</a>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="https://www.google.com/maps/dir/?api=1&destination={fila["lat"]},{fila["lon"]}" target="_blank" class="btn-accion btn-ruta" style="font-size: 1rem !important; padding: 0.8rem; margin-bottom: 0.5rem;">🗺️ Ruta</a>', unsafe_allow_html=True)

st.caption(f"Actualizado: {sello} | Fuente: Datos Abiertos MINSAL")
