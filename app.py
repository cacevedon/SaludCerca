from __future__ import annotations
import datetime as dt
import math
import re
import pandas as pd
import requests
import streamlit as st

try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_DISPONIBLE = True
except Exception:
    GEO_DISPONIBLE = False

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

# Diccionario de tipos acortados
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

REGIONES = {
    1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 6: "O'Higgins", 7: "Maule", 8: "Biobío",
    9: "La Araucanía", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
    13: "Metropolitana", 14: "Los Ríos", 15: "Arica y Parinacota", 16: "Ñuble",
}

st.set_page_config(
    page_title="SaludCerca",
    page_icon="📍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------
# CSS Extremo para forzar legibilidad y botones gigantes
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
      /* Fondo claro forzado */
      .stApp {{ background-color: {PAPEL} !important; }}
      
      /* Textos base grandes y oscuros */
      h1, h2, h3, p, span, div, label {{ 
          font-family: system-ui, -apple-system, sans-serif !important; 
          color: {TINTA} !important; 
      }}
      
      /* Cabecera */
      .cabecera {{ text-align: center; margin-bottom: 2rem; }}
      .cabecera h1 {{ font-size: 2.2rem; line-height: 1.1; color: {AZUL} !important; font-weight: 800; }}
      .cabecera p {{ font-size: 1rem; color: {GRIS} !important; text-transform: uppercase; letter-spacing: 1px; }}

      /* Tarjeta del resultado principal */
      .tarjeta-principal {{ 
          background: #FFFFFF; 
          border: 3px solid {ORO}; 
          border-radius: 16px; 
          padding: 1.5rem; 
          margin-bottom: 1.5rem; 
          box-shadow: 0 8px 20px rgba(0,0,0,0.15); 
          text-align: center;
      }}
      .tarjeta-principal h2 {{ font-size: 1.8rem; margin: 0 0 0.5rem 0; color: {AZUL} !important; line-height: 1.2; }}
      .tarjeta-principal .dir {{ font-size: 1.2rem; color: {TINTA} !important; margin-bottom: 1rem; }}
      .tarjeta-principal .distancia {{ font-size: 1.4rem; font-weight: bold; color: {ORO} !important; margin-bottom: 1rem; }}
      
      /* Botones HTML Gigantes (Llamar y Ruta) */
      .btn-accion {{
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          padding: 1.2rem;
          margin-bottom: 1rem;
          border-radius: 12px;
          font-size: 1.5rem;
          font-weight: bold;
          text-decoration: none !important;
          color: #FFFFFF !important;
          background-color: {AZUL};
          box-shadow: 0 4px 10px rgba(0,0,0,0.2);
          transition: transform 0.1s;
      }}
      .btn-accion:active {{ transform: scale(0.95); }}
      .btn-llamar {{ background-color: #2E7D32 !important; }} /* Verde para llamar */
      .btn-ruta {{ background-color: {AZUL} !important; }} /* Azul para ruta */

      /* Tarjetas secundarias */
      .tarjeta-sec {{ 
          background: #FFFFFF; 
          border: 1px solid #D1D5DB; 
          border-radius: 12px; 
          padding: 1rem; 
          margin-bottom: 1rem; 
      }}
      .tarjeta-sec h4 {{ font-size: 1.2rem; margin: 0 0 0.3rem 0; color: {TINTA} !important; }}
      .tarjeta-sec p {{ font-size: 1rem; margin: 0; color: {GRIS} !important; }}
      
      /* Ocultar menús de Streamlit que estorban */
      #MainMenu {{visibility: hidden;}}
      footer {{visibility: hidden;}}
      header {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Lógica de Datos (Sin cambios mayores)
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
    df["RegionCodigo"] = pd.to_numeric(df["RegionCodigo"], errors="coerce")
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
    df["tipo_corto"] = df["TipoEstablecimientoGlosa"].fillna("").map(_acortar_tipo)
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
except Exception as error:
    st.error(f"Error de conexión. Revisa tu internet.")
    st.stop()

ahora = ahora_en_chile()
df["abierto"] = [esta_abierto(u, ahora) for u in df["urgencia"]]

# --- GEOLOCALIZACIÓN GIGANTE ---
st.markdown("<h3 style='text-align:center;'>1. Toca tu ubicación</h3>", unsafe_allow_html=True)

origen = None
if GEO_DISPONIBLE:
    # Envolvemos el botón del mapa en un contenedor gigante para que sea fácil de tocar
    st.markdown(
        """
        <div style="background-color: #E3F2FD; border: 2px dashed #1B3A5C; border-radius: 16px; padding: 1.5rem; text-align: center; margin-bottom: 1rem;">
            <p style="font-size: 1.2rem; margin-bottom: 1rem; font-weight: bold; color: #1B3A5C !important;">Toca el ícono azul de abajo para usar tu GPS</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    dato = streamlit_geolocation()
    if dato and dato.get("latitude") is not None:
        origen = (float(dato["latitude"]), float(dato["longitude"]), "Tu ubicación GPS")
        st.success("¡Listo! Ubicación encontrada.")
else:
    st.info("Usa el buscador de comunas de abajo.")

if origen is None:
    st.markdown("<p style='text-align:center; font-size: 1.2rem;'>O escribe tu comuna:</p>", unsafe_allow_html=True)
    comunas = sorted(df["comuna"].unique())
    comuna_sel = st.selectbox("Comuna", comunas, index=comunas.index("Santiago") if "Santiago" in comunas else 0, label_visibility="collapsed")
    
    del_lugar = df[df["comuna"] == comuna_sel]
    if not del_lugar.empty:
        origen = (float(del_lugar["lat"].mean()), float(del_lugar["lon"].mean()), f"Comuna de {comuna_sel}")

# --- RESULTADOS ---
if origen is not None:
    lat0, lon0, _ = origen
    
    # Buscamos primero urgencias (lo que un anciano o niño necesita si está asustado)
    candidatos = df[df["abierto"]].copy()
    
    if not candidatos.empty:
        candidatos["km"] = [distancia_km(lat0, lon0, la, lo) for la, lo in zip(candidatos["lat"], candidatos["lon"])]
        # Filtramos a 50 km por defecto para no perdernos
        candidatos = candidatos[candidatos["km"] <= 50].sort_values("km")

    if candidatos.empty:
        st.error("No encontramos centros abiertos cerca. Llama al SAMU (131).")
    else:
        st.markdown("<hr style='margin: 2rem 0; border: 1px solid #E4E1D9;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>2. El más cercano abierto</h3>", unsafe_allow_html=True)
        
        # --- TARJETA GIGANTE DEL PRIMER RESULTADO ---
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
        
        # --- BOTONES GIGANTES CON HTML (Para forzar colores) ---
        # Botón Llamar (Verde)
        if primero["fono"]:
            st.markdown(
                f'<a href="tel:+56{primero["fono"]}" class="btn-accion btn-llamar">📞 LLAMAR AHORA</a>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="btn-accion" style="background-color: #9E9E9E !important;">📞 SIN TELÉFONO</div>', 
                unsafe_allow_html=True
            )

        # Botón Ruta (Azul)
        st.markdown(
            f'<a href="https://www.google.com/maps/dir/?api=1&destination={primero["lat"]},{primero["lon"]}" target="_blank" class="btn-accion btn-ruta">🗺️ CÓMO LLEGAR</a>', 
            unsafe_allow_html=True
        )

        # --- OTRAS OPCIONES OCULTAS ---
        with st.expander("Ver otros centros cercanos"):
            for _, fila in candidatos.iloc[1:6].iterrows():
                st.markdown(
                    f"""
                    <div class="tarjeta-sec">
                      <h4>{fila['nombre']}</h4>
                      <p>📍 {fila['comuna']} · A {formato_km(fila['km'])}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # Botones en fila (usando columnas para que no se vean gigantes)
                c1, c2 = st.columns(2)
                with c1:
                    if fila["fono"]:
                        st.markdown(f'<a href="tel:+56{fila["fono"]}" class="btn-accion btn-llamar" style="font-size: 1rem !important; padding: 0.8rem;">📞 Llamar</a>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="https://www.google.com/maps/dir/?api=1&destination={fila["lat"]},{fila["lon"]}" target="_blank" class="btn-accion btn-ruta" style="font-size: 1rem !important; padding: 0.8rem;">🗺️ Ruta</a>', unsafe_allow_html=True)
                st.write("---")

st.caption(f"Actualizado: {sello} | Fuente: Datos Abiertos MINSAL")
